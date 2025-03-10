"""Simple BLE client for the Fellow Stagg EKG Pro kettle."""
import asyncio
import logging
import time
from typing import Callable, Any, Optional, Dict

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak.exc import BleakDeviceNotFoundError

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
