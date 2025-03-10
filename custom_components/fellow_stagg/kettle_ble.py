"""BLE client for the Fellow Stagg EKG Pro kettle."""
import logging
from typing import Dict, Any

from bleak.backends.device import BLEDevice

from .const import SERVICE_UUID, CHAR_UUID, INIT_SEQUENCE, CUSTOM_SERVICE_UUID
from .simple_ble_client import SimpleBleClient

_LOGGER = logging.getLogger(__name__)


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
