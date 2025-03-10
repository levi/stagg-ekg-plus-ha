"""BLE client for the Fellow Stagg EKG Pro kettle."""
import asyncio
import logging
import time
from typing import Dict, Any, Callable, Optional

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakDeviceNotFoundError, BleakError

from .const import SERVICE_UUID, CHAR_UUID, INIT_SEQUENCE, CUSTOM_SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class SimpleBleClient:
    """A simple BLE client without any complex connection management."""

    def __init__(self, address: str, service_uuid: str, char_uuid: str) -> None:
        """Initialize the client."""
        self.address = address
        self.service_uuid = service_uuid
        self.char_uuid = char_uuid
        self._sequence = 0  # For command sequence numbering
        self._last_command_time = 0  # For debouncing commands

    async def connect_and_execute(
        self,
        ble_device: BLEDevice,
        operation: Callable[[BleakClient], Any],
        timeout: float = 10.0
    ) -> Any:
        """Connect to device, perform operation, and disconnect."""
        client = None
        try:
            _LOGGER.debug("Connecting to %s", self.address)
            client = BleakClient(ble_device, timeout=timeout)

            # Try to connect with timeout
            connect_task = asyncio.create_task(client.connect())
            await asyncio.wait_for(connect_task, timeout=timeout)

            if not client.is_connected:
                _LOGGER.error("Failed to connect to device %s", self.address)
                return None

            _LOGGER.debug("Successfully connected, executing operation")
            result = await operation(client)
            return result

        except asyncio.TimeoutError:
            _LOGGER.error("Connection to %s timed out", self.address)
            return None
        except BleakDeviceNotFoundError:
            _LOGGER.error("Device %s not found", self.address)
            return None
        except BleakError as err:
            _LOGGER.error("BleakError during connection to %s: %s", self.address, str(err))
            return None
        except Exception as err:
            _LOGGER.error("Error during operation on %s: %s", self.address, str(err), exc_info=True)
            return None
        finally:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except Exception as err:
                    _LOGGER.warning("Error during disconnect: %s", str(err))

    async def ensure_debounce(self):
        """Ensure we don't send commands too frequently."""
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        if current_time - self._last_command_time < 200:  # 200ms debounce
            await asyncio.sleep(0.2)  # Wait 200ms
        self._last_command_time = current_time

    def create_command(self, command_type: int, value: int) -> bytes:
        """Create a command with proper sequence number and checksum."""
        command = bytearray([
            0xef, 0xdd,  # Magic
            0x0a,        # Command flag
            self._sequence,  # Sequence number
            command_type,    # Command type
            value,          # Value
            (self._sequence + value) & 0xFF,  # Checksum 1
            command_type    # Checksum 2
        ])
        self._sequence = (self._sequence + 1) & 0xFF
        return bytes(command)

    async def write_auth_sequence(self, client: BleakClient, auth_sequence: bytes) -> bool:
        """Write the authentication sequence to the device."""
        try:
            await self.ensure_debounce()
            _LOGGER.debug("Writing auth sequence to %s: %s", self.char_uuid, auth_sequence.hex())
            await client.write_gatt_char(self.char_uuid, auth_sequence)
            _LOGGER.debug("Auth sequence written successfully")
            return True
        except Exception as err:
            _LOGGER.error("Error writing auth sequence: %s", str(err))
            return False

    async def write_command(self, client: BleakClient, command: bytes) -> bool:
        """Write a command to the device."""
        try:
            await self.ensure_debounce()
            _LOGGER.debug("Writing command to %s: %s", self.char_uuid, command.hex())
            await client.write_gatt_char(self.char_uuid, command)
            _LOGGER.debug("Command written successfully")
            return True
        except Exception as err:
            _LOGGER.error("Error writing command: %s", str(err))
            return False

    async def read_notifications(self, client: BleakClient, duration: float = 2.0) -> list:
        """Read notifications from the device for a specified duration."""
        notifications = []

        def notification_handler(_, data):
            _LOGGER.debug("Received notification: %s", data.hex())
            notifications.append(data)

        try:
            # Start notifications
            await client.start_notify(self.char_uuid, notification_handler)

            # Wait for notifications to arrive
            await asyncio.sleep(duration)

            # Stop notifications
            await client.stop_notify(self.char_uuid)

            return notifications
        except Exception as err:
            _LOGGER.error("Error during notifications: %s", str(err))
            return []

    def parse_notifications(self, notifications: list) -> Dict[str, Any]:
        """Parse BLE notification payloads into kettle state."""
        state = {}

        if not notifications:
            return state

        # Log all notifications for debugging
        for i, notif in enumerate(notifications):
            _LOGGER.debug("Processing notification %d: %s", i, notif.hex())

        i = 0
        while i < len(notifications) - 1:  # Process pairs of notifications
            header = notifications[i]
            if i + 1 >= len(notifications):
                break

            payload = notifications[i + 1]

            if len(header) < 3 or header[0] != 0xEF or header[1] != 0xDD:
                i += 1
                continue

            msg_type = header[2]
            _LOGGER.debug("Processing message type %d with payload %s", msg_type, payload.hex())

            if msg_type == 0:
                # Power state
                if len(payload) >= 1:
                    state["power"] = payload[0] == 1
                    _LOGGER.debug("Power state: %s", state["power"])
            elif msg_type == 1:
                # Hold state
                if len(payload) >= 1:
                    state["hold"] = payload[0] == 1
                    _LOGGER.debug("Hold state: %s", state["hold"])
            elif msg_type == 2:
                # Target temperature
                if len(payload) >= 2:
                    temp = payload[0]  # Single byte temperature
                    is_fahrenheit = payload[1] == 1
                    state["target_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
                    _LOGGER.debug("Target temp: %d°%s", temp, state["units"])
            elif msg_type == 3:
                # Current temperature
                if len(payload) >= 2:
                    temp = payload[0]  # Single byte temperature
                    is_fahrenheit = payload[1] == 1
                    state["current_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
                    _LOGGER.debug("Current temp: %d°%s", temp, state["units"])
            elif msg_type == 4:
                # Countdown
                if len(payload) >= 1:
                    state["countdown"] = payload[0]
                    _LOGGER.debug("Countdown: %d", state["countdown"])
            elif msg_type == 8:
                # Kettle position
                if len(payload) >= 1:
                    state["lifted"] = payload[0] == 0
                    _LOGGER.debug("Lifted: %s", state["lifted"])
            else:
                _LOGGER.debug("Unknown message type: %d", msg_type)

            i += 2  # Move to next pair of notifications

        return state


class KettleBLEClient:
    """BLE client for the Fellow Stagg EKG Pro kettle."""

    def __init__(self, address: str):
        """Initialize the client."""
        self.address = address
        self.service_uuid = SERVICE_UUID
        self.char_uuid = CHAR_UUID
        self.custom_service_uuid = CUSTOM_SERVICE_UUID
        self.init_sequence = INIT_SEQUENCE
        self._client = SimpleBleClient(address, SERVICE_UUID, CHAR_UUID)

    async def async_poll(self, ble_device: BLEDevice) -> Dict[str, Any]:
        """Connect to the kettle, send init command, and return parsed state."""
        async def poll_operation(client):
            # First authenticate
            success = await self._client.write_auth_sequence(client, self.init_sequence)
            if not success:
                _LOGGER.error("Failed to authenticate with kettle")
                return {}

            # Read notifications to get current state
            notifications = await self._client.read_notifications(client)
            if not notifications:
                _LOGGER.warning("No notifications received from kettle")
                return {}

            # Parse notifications into state
            return self._client.parse_notifications(notifications)

        # Execute the poll operation
        return await self._client.connect_and_execute(ble_device, poll_operation)

    async def async_set_power(self, ble_device: BLEDevice, power_on: bool) -> bool:
        """Turn the kettle on or off."""
        async def power_operation(client):
            # First authenticate
            success = await self._client.write_auth_sequence(client, self.init_sequence)
            if not success:
                _LOGGER.error("Failed to authenticate with kettle during power operation")
                return False

            # Create and send power command
            command = self._client.create_command(0, 1 if power_on else 0)
            success = await self._client.write_command(client, command)
            if not success:
                _LOGGER.error("Failed to send power command")
                return False

            return True

        # Execute the power operation
        success = await self._client.connect_and_execute(ble_device, power_operation)
        return success or False

    async def async_set_temperature(self, ble_device: BLEDevice, temp: int, fahrenheit: bool = True) -> bool:
        """Set target temperature."""
        # Temperature validation
        if fahrenheit:
            if temp > 212:
                temp = 212
            if temp < 104:
                temp = 104
        else:
            if temp > 100:
                temp = 100
            if temp < 40:
                temp = 40

        async def temp_operation(client):
            # First authenticate
            success = await self._client.write_auth_sequence(client, self.init_sequence)
            if not success:
                _LOGGER.error("Failed to authenticate with kettle during temperature operation")
                return False

            # Create and send temperature command
            command = self._client.create_command(1, temp)  # Type 1 = temperature command
            success = await self._client.write_command(client, command)
            if not success:
                _LOGGER.error("Failed to send temperature command")
                return False

            return True

        # Execute the temperature operation
        success = await self._client.connect_and_execute(ble_device, temp_operation)
        return success or False

    async def disconnect(self):
        """No persistent connection to disconnect in this implementation."""
        pass  # This is a no-op since we don't maintain a persistent connection
