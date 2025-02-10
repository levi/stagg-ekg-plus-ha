"""Support for Fellow Stagg EKG+ kettles."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator
)
from .const import DOMAIN
from .kettle_ble import KettleBLEClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Fellow Stagg integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fellow Stagg integration from a config entry."""
    address = entry.unique_id
    if address is None:
        _LOGGER.error("No unique ID provided in config entry")
        return False

    kettle_client = KettleBLEClient(address)

    def _needs_poll(
        service_info: BluetoothServiceInfoBleak, last_poll: float | None
    ) -> bool:
        """Check if we should poll the device.
        
        We only poll when:
        1. Home Assistant is fully started
        2. We receive an advertisement
        """
        return hass.state == CoreState.running

    async def _async_poll(service_info: BluetoothServiceInfoBleak) -> dict[str, Any] | None:
        """Poll the device for data."""
        _LOGGER.debug(
            "Polling Fellow Stagg kettle %s",
            service_info.device.address,
        )
        if service_info.connectable:
            connectable_device = service_info.device
        elif device := async_ble_device_from_address(
            hass, service_info.device.address, True
        ):
            connectable_device = device
        else:
            _LOGGER.error(
                "No connectable device found for %s",
                service_info.device.address,
            )
            return None
        try:
            data = await kettle_client.async_poll(connectable_device)
            _LOGGER.debug(
                "Polled data from kettle %s: %s",
                service_info.device.address,
                data,
            )
            return data
        except Exception as e:
            _LOGGER.error(
                "Error polling Fellow Stagg kettle %s: %s",
                service_info.device.address,
                str(e),
            )
            return None

    def _process_update(service_info: BluetoothServiceInfoBleak) -> dict[str, Any] | None:
        """Process a Bluetooth update."""
        return coordinator.last_poll_data if hasattr(coordinator, "last_poll_data") else None

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=_process_update,
        needs_poll_method=_needs_poll,
        poll_method=_async_poll,
        connectable=False,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Fellow Stagg integration."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)
    return True
