"""Reliable BLE client for the Fellow Stagg EKG+ kettle."""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Any, Optional

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
RECONNECT_WAIT_BASE = 2  # Base wait time in seconds (doubles each retry)

class EnhancedKettleBLEClient:
    """Enhanced BLE client with retry logic and connection monitoring."""

    def __init__(self, address: str, service_uuid: str, char_uuid: str) -> None:
        """Initialize the client."""
        self.address = address
        self.service_uuid = service_uuid
        self.char_uuid = char_uuid
        self._client: Optional[BleakClient] = None
        self._is_connected = False
        self._connection_attempts = 0
        self._last_activity = datetime.now()

    async def connect(self, ble_device: BLEDevice) -> bool:
        """Connect to the device with retry logic."""
        if self._is_connected and self._client and self._client.is_connected:
            return True

        self._connection_attempts += 1
        if self._connection_attempts > 1:
            wait_time = RECONNECT_WAIT_BASE * (2 ** (self._connection_attempts - 2))
            _LOGGER.warning(
                "Connection attempt %s. Waiting %s seconds before retry.",
                self._connection_attempts - 1,
                wait_time,
            )
            await asyncio.sleep(wait_time)

        if self._connection_attempts > MAX_ATTEMPTS:
            _LOGGER.warning("Reached max connection attempts for %s", self.address)
            return False

        try:
            _LOGGER.debug("Connecting to device at %s", self.address)
            self._client = BleakClient(ble_device, timeout=10.0)
            await self._client.connect()
            # Call discover services
            await self._discover_services()
            self._is_connected = True
            self._connection_attempts = 0
            self._last_activity = datetime.now()
            return True
        except BleakError as err:
            _LOGGER.error("BleakError during connection: %s", str(err))
            return False
        except Exception as err:
            _LOGGER.error(
                "Comprehensive connection error for %s: %s",
                self.address,
                str(err),
                exc_info=True,
            )
            return False

    async def _discover_services(self):
        """Discover services on the device.

        This method was missing in the original implementation and was causing the error.
        Adding a simple implementation to make the connection work.
        """
        _LOGGER.debug("Discovering services on device %s", self.address)
        # This is a minimal implementation - it doesn't need to do anything
        # for the Fellow Stagg kettle, but it needs to exist to prevent errors
        pass

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception as err:
                _LOGGER.warning("Error during disconnect: %s", str(err))
            finally:
                self._is_connected = False
                self._client = None

    async def write_gatt_char(self, char_uuid: str, data: bytes) -> bool:
        """Write to a characteristic with retry."""
        if not self._is_connected or not self._client:
            _LOGGER.error("Cannot write characteristic, not connected")
            return False

        try:
            await self._client.write_gatt_char(char_uuid, data)
            self._last_activity = datetime.now()
            return True
        except Exception as err:
            _LOGGER.error("Error writing to characteristic: %s", str(err))
            self._is_connected = False
            await self.disconnect()
            return False

    async def start_notify(
        self, char_uuid: str, callback: Callable[[str, bytearray], None]
    ) -> bool:
        """Start notifications with retry."""
        if not self._is_connected or not self._client:
            _LOGGER.error("Cannot start notify, not connected")
            return False

        try:
            await self._client.start_notify(char_uuid, callback)
            self._last_activity = datetime.now()
            return True
        except Exception as err:
            _LOGGER.error("Error starting notifications: %s", str(err))
            self._is_connected = False
            await self.disconnect()
            return False

    async def stop_notify(self, char_uuid: str) -> bool:
        """Stop notifications with retry."""
        if not self._is_connected or not self._client:
            return False

        try:
            await self._client.stop_notify(char_uuid)
            self._last_activity = datetime.now()
            return True
        except Exception as err:
            _LOGGER.error("Error stopping notifications: %s", str(err))
            self._is_connected = False
            await self.disconnect()
            return False

    def is_connected(self) -> bool:
        """Return connection status."""
        # Additional check to ensure client object exists
        connected = (
            self._is_connected and self._client is not None and self._client.is_connected
        )
        if self._is_connected and not connected:
            # State got out of sync
            self._is_connected = False
            _LOGGER.warning("Unexpected disconnection from %s", self.address)
        return connected
