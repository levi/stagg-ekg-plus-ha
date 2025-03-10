"""Support for Fellow Stagg EKG+ kettles."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.device_registry import DeviceInfo
import async_timeout

from .const import DOMAIN
from .kettle_ble import KettleBLEClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.WATER_HEATER]
POLLING_INTERVAL = timedelta(seconds=30)  # Increased poll time to reduce BLE traffic
CONNECTION_TIMEOUT = 15  # Timeout for BLE operations in seconds

# Temperature ranges for the kettle
MIN_TEMP_F = 104
MAX_TEMP_F = 212
MIN_TEMP_C = 40
MAX_TEMP_C = 100


class FellowStaggDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Fellow Stagg data."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Fellow Stagg {address}",
            update_interval=POLLING_INTERVAL,
        )
        self.kettle = KettleBLEClient(address)
        self.ble_device = None
        self._address = address
        self._last_update_success = False
        self._connection_retries = 0
        self._max_retries = 3

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=f"Fellow Stagg EKG+ {address}",
            manufacturer="Fellow",
            model="Stagg EKG+ Pro",  # Updated for Pro model
        )

    @property
    def temperature_unit(self) -> str:
        """Get the current temperature unit."""
        return UnitOfTemperature.FAHRENHEIT if self.data and self.data.get("units") == "F" else UnitOfTemperature.CELSIUS

    @property
    def min_temp(self) -> float:
        """Get the minimum temperature based on current units."""
        return MIN_TEMP_F if self.temperature_unit == UnitOfTemperature.FAHRENHEIT else MIN_TEMP_C

    @property
    def max_temp(self) -> float:
        """Get the maximum temperature based on current units."""
        return MAX_TEMP_F if self.temperature_unit == UnitOfTemperature.FAHRENHEIT else MAX_TEMP_C

    async def _async_update_data(self) -> dict[str, Any] | None:
        """Fetch data from the kettle."""
        _LOGGER.debug("Attempting to update data for %s", self._address)

        # Get the BLE device
        self.ble_device = async_ble_device_from_address(self.hass, self._address, True)
        if not self.ble_device:
            _LOGGER.debug("No connectable device found for %s", self._address)
            self._connection_retries += 1
            if self._connection_retries > self._max_retries:
                _LOGGER.warning("Reached max connection attempts for %s", self._address)
                self._connection_retries = 0
            return self.data  # Return last known data

        try:
            # Use a timeout to prevent hanging
            async with async_timeout.timeout(CONNECTION_TIMEOUT):
                data = await self.kettle.async_poll(self.ble_device)

            if data:
                self._connection_retries = 0
                self._last_update_success = True

                # Log any changes in data compared to previous state
                if self.data is not None:
                    changes = {
                        k: (self.data.get(k), v)
                        for k, v in data.items()
                        if k in self.data and self.data.get(k) != v
                    }
                    if changes:
                        _LOGGER.debug("Data changes detected: %s", changes)

                _LOGGER.debug(
                    "Successfully polled data from kettle %s: %s",
                    self._address,
                    data,
                )
                return data
            else:
                self._connection_retries += 1
                _LOGGER.warning("No new data retrieved. Using last known data.")
                return self.data  # Return last known data

        except Exception as e:
            self._connection_retries += 1
            _LOGGER.error(
                "Error polling Fellow Stagg kettle %s: %s",
                self._address,
                str(e),
            )
            # Only raise UpdateFailed if we don't have any previous data
            if self.data is None:
                raise UpdateFailed(f"Failed to update kettle status: {e}")
            return self.data  # Return last known data
        finally:
            _LOGGER.debug(
                "Finished fetching Fellow Stagg %s data in %.3f seconds (success: %s)",
                self._address,
                0.0,  # Placeholder
                bool(data) if 'data' in locals() else False,
            )


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
    coordinator = FellowStaggDataUpdateCoordinator(hass, address)

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
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.kettle.disconnect()
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    return True
