import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from .const import DOMAIN
from .kettle_ble import KettleBLEClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fellow Stagg integration from a config entry."""
    address = entry.unique_id
    if address is None:
        _LOGGER.error("No unique ID provided in config entry")
        return False

    kettle_client = KettleBLEClient(address)

    def needs_poll(service_info, last_poll):
        # For simplicity, always poll
        return True

    async def poll_method(service_info):
        ble_device = async_ble_device_from_address(
            hass, service_info.device.address, connectable=True
        )
        if ble_device is None:
            raise RuntimeError(
                f"No connectable BLE device found for {service_info.device.address}"
            )
        return await kettle_client.async_poll(ble_device)

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=lambda update: update,  # In this simple example we do not process advertisements
        needs_poll_method=needs_poll,
        poll_method=poll_method,
        connectable=False,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Fellow Stagg integration."""
    coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_stop()
    return True
