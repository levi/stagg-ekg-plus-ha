"""BLE client for the Fellow Stagg EKG+ kettle."""
import asyncio
import logging
import time

from bleak.backends.device import BLEDevice

from .const import SERVICE_UUID, CHAR_UUID, INIT_SEQUENCE
from .reliable_ble_client import EnhancedKettleBLEClient

_LOGGER = logging.getLogger(__name__)


class KettleBLEClient:
    """BLE client for the Fellow Stagg EKG+ kettle."""

    def __init__(self, address: str):
        """Initialize the client."""
        self.address = address
        self.service_uuid = SERVICE_UUID
        self.char_uuid = CHAR_UUID
        self.init_sequence = INIT_SEQUENCE
        self._client = EnhancedKettleBLEClient(address, SERVICE_UUID, CHAR_UUID)
        self._sequence = 0  # For command sequence numbering
        self._last_command_time = 0  # For debouncing commands

    async def _ensure_connected(self, ble_device: BLEDevice) -> bool:
        """Ensure BLE connection is established."""
        if not self._client.is_connected():
            _LOGGER.debug("Connecting to kettle at %s", self.address)
            if not await self._client.connect(ble_device):
                _LOGGER.error("Failed to connect to kettle at %s", self.address)
                return False
            await self._authenticate()
        return True

    async def _ensure_debounce(self):
        """Ensure we don't send commands too frequently."""
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        if current_time - self._last_command_time < 200:  # 200ms debounce
            await asyncio.sleep(0.2)  # Wait 200ms
        self._last_command_time = current_time

    async def _authenticate(self):
        """Send authentication sequence to kettle."""
        try:
            _LOGGER.debug("Writing init sequence to characteristic %s", self.char_uuid)
            await self._ensure_debounce()
            await self._client.write_gatt_char(self.char_uuid, self.init_sequence)
        except Exception as err:
            _LOGGER.error("Error writing init sequence: %s", err)
            raise

    def _create_command(self, command_type: int, value: int) -> bytes:
        """Create a command with proper sequence number and checksum.

        Command format:
        - Bytes 0-1: Magic (0xef, 0xdd)
        - Byte 2: Command flag (0x0a)
        - Byte 3: Sequence number
        - Byte 4: Command type (0=power, 1=temp)
        - Byte 5: Value
        - Byte 6: Checksum 1 (sequence + value)
        - Byte 7: Checksum 2 (command type)
        """
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

    async def async_poll(self, ble_device: BLEDevice):
        """Connect to the kettle, send init command, and return parsed state."""
        try:
            if not await self._ensure_connected(ble_device):
                return {}

            notifications = []

            def notification_handler(sender, data):
                notifications.append(data)

            # Start notifications
            if not await self._client.start_notify(self.char_uuid, notification_handler):
                return {}

            # Wait for notifications to come in
            await asyncio.sleep(2.0)

            # Stop notifications
            await self._client.stop_notify(self.char_uuid)

            # Parse notifications into state
            state = self.parse_notifications(notifications)
            return state

        except Exception as err:
            _LOGGER.error("Error polling kettle: %s", err)
            await self._client.disconnect()
            return {}

    async def async_set_power(self, ble_device: BLEDevice, power_on: bool):
        """Turn the kettle on or off."""
        try:
            if not await self._ensure_connected(ble_device):
                _LOGGER.error("Failed to connect for power setting")
                return

            await self._ensure_debounce()
            command = self._create_command(0, 1 if power_on else 0)
            await self._client.write_gatt_char(self.char_uuid, command)
        except Exception as err:
            _LOGGER.error("Error setting power state: %s", err)
            await self._client.disconnect()
            raise

    async def async_set_temperature(self, ble_device: BLEDevice, temp: int, fahrenheit: bool = True):
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

        try:
            if not await self._ensure_connected(ble_device):
                _LOGGER.error("Failed to connect for temperature setting")
                return

            await self._ensure_debounce()
            command = self._create_command(1, temp)  # Type 1 = temperature command
            await self._client.write_gatt_char(self.char_uuid, command)
        except Exception as err:
            _LOGGER.error("Error setting temperature: %s", err)
            await self._client.disconnect()
            raise

    async def disconnect(self):
        """Disconnect from the kettle."""
        await self._client.disconnect()

    def parse_notifications(self, notifications):
        """Parse BLE notification payloads into kettle state.

        Expected frame format comes in two notifications:
          First notification:
            - Bytes 0-1: Magic (0xef, 0xdd)
            - Byte 2: Message type
          Second notification:
            - Payload data

        Reverse engineered types:
          - Type 0: Power (1 = on, 0 = off)
          - Type 1: Hold (1 = hold, 0 = normal)
          - Type 2: Target temperature (byte 0: temp, byte 1: unit, 1 = F, else C)
          - Type 3: Current temperature (byte 0: temp, byte 1: unit, 1 = F, else C)
          - Type 4: Countdown
          - Type 8: Kettle position (0 = lifted, 1 = on base)
        """
        state = {}
        i = 0
        while i < len(notifications) - 1:  # Process pairs of notifications
            header = notifications[i]
            payload = notifications[i + 1]

            if len(header) < 3 or header[0] != 0xEF or header[1] != 0xDD:
                i += 1
                continue

            msg_type = header[2]

            if msg_type == 0:
                # Power state
                if len(payload) >= 1:
                    state["power"] = payload[0] == 1
            elif msg_type == 1:
                # Hold state
                if len(payload) >= 1:
                    state["hold"] = payload[0] == 1
            elif msg_type == 2:
                # Target temperature
                if len(payload) >= 2:
                    temp = payload[0]  # Single byte temperature
                    is_fahrenheit = payload[1] == 1
                    state["target_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
            elif msg_type == 3:
                # Current temperature
                if len(payload) >= 2:
                    temp = payload[0]  # Single byte temperature
                    is_fahrenheit = payload[1] == 1
                    state["current_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
            elif msg_type == 4:
                # Countdown
                if len(payload) >= 1:
                    state["countdown"] = payload[0]
            elif msg_type == 8:
                # Kettle position
                if len(payload) >= 1:
                    state["lifted"] = payload[0] == 0

            i += 2  # Move to next pair of notifications

        return state
