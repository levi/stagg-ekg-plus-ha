import logging
from contextlib import asynccontextmanager
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator
)
from bleak import BleakClient
from .const import DOMAIN
from .kettle_ble import KettleBLEClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch", "number"]


class FellowStaggCoordinator(ActiveBluetoothProcessorCoordinator):
    """Data coordinator for Fellow Stagg kettle."""

    def __init__(self, hass: HomeAssistant, address: str):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            address=address,
            mode=BluetoothScanningMode.PASSIVE,
            update_method=self._process_update,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll,
            connectable=False,
        )
        self.kettle_client = KettleBLEClient(address)
        self.address = address
        self.last_poll_data = None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.address)},
            "name": f"Fellow Stagg EKG+ ({self.address})",
            "manufacturer": "Fellow",
            "model": "Stagg EKG+",
        }

    @asynccontextmanager
    async def client_session(self):
        """Context manager for BLE client connection."""
        if self.last_service_info and self.last_service_info.connectable:
            device = self.last_service_info.device
        elif device := async_ble_device_from_address(self.hass, self.address, True):
            pass
        else:
            raise RuntimeError(f"No connectable device found for {self.address}")

        async with BleakClient(device, timeout=10.0) as client:
            await self.kettle_client.authenticate(client)
            yield client

    def _needs_poll(
        self,
        service_info: BluetoothServiceInfoBleak,
        last_poll: float | None,
    ) -> bool:
        """Check if we should poll the device."""
        return True

    async def _async_poll(self, service_info: BluetoothServiceInfoBleak):
        """Poll the device for data."""
        _LOGGER.debug("Polling Fellow Stagg kettle %s", service_info.device.address)
        if service_info.connectable:
            device = service_info.device
        elif device := async_ble_device_from_address(self.hass, service_info.device.address, True):
            pass
        else:
            _LOGGER.error("No connectable device found for %s", service_info.device.address)
            return None

        try:
            async with BleakClient(device, timeout=10.0) as client:
                await self.kettle_client.authenticate(client)
                data = await self.kettle_client.async_poll(client)
                _LOGGER.debug("Polled data from kettle %s: %s", service_info.device.address, data)
                self.last_poll_data = data
                return data
        except Exception as e:
            _LOGGER.error(
                "Error polling Fellow Stagg kettle %s: %s",
                service_info.device.address,
                str(e),
            )
            return None

    def _process_update(self, service_info: BluetoothServiceInfoBleak):
        """Process a Bluetooth update."""
        return self.last_poll_data if hasattr(self, "last_poll_data") else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fellow Stagg integration from a config entry."""
    address = entry.unique_id
    if address is None:
        _LOGGER.error("No unique ID provided in config entry")
        return False

    coordinator = FellowStaggCoordinator(hass, address)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Fellow Stagg integration."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
    return unload_ok
