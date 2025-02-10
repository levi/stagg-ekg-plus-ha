"""Support for Fellow Stagg EKG+ kettles."""
import logging
from typing import Any
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_register_callback
)
from homeassistant.components.bluetooth.match import (
    BluetoothCallbackMatcher,
    ADDRESS
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
from .const import DOMAIN, SERVICE_UUID
from .kettle_ble import KettleBLEClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
POLLING_INTERVAL = timedelta(seconds=5)  # Poll every 5 seconds (minimum allowed)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Fellow Stagg integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fellow Stagg integration from a config entry."""
    address = entry.unique_id
    if address is None:
        _LOGGER.error("No unique ID provided in config entry")
        return False

    _LOGGER.debug("Setting up Fellow Stagg integration for device: %s", address)
    kettle_client = KettleBLEClient(address)

    async def _async_update_data() -> dict[str, Any] | None:
        """Fetch data from the kettle."""
        _LOGGER.debug("Starting poll for Fellow Stagg kettle %s", address)
        
        device = async_ble_device_from_address(hass, address, True)
        if not device:
            _LOGGER.debug("No connectable device found")
            return None
            
        try:
            _LOGGER.debug("Attempting to poll kettle data...")
            data = await kettle_client.async_poll(device)
            _LOGGER.debug(
                "Successfully polled data from kettle %s: %s",
                address,
                data,
            )
            return data
        except Exception as e:
            _LOGGER.error(
                "Error polling Fellow Stagg kettle %s: %s",
                address,
                str(e),
            )
            return None

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Fellow Stagg {address}",
        update_method=_async_update_data,
        update_interval=POLLING_INTERVAL,
    )

    _LOGGER.debug("Created DataUpdateCoordinator for device: %s", address)

    # Do first update
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.debug("Setup complete for Fellow Stagg device: %s", address)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Fellow Stagg integration for entry: %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    return True
