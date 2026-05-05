"""Support for Fellow Stagg EKG+ kettles."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
    async_scanner_by_source,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
from .kettle_ble import KettleBLEClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.WATER_HEATER]

# Temperature ranges for the kettle
MIN_TEMP_F = 104
MAX_TEMP_F = 212
MIN_TEMP_C = 40
MAX_TEMP_C = 100


class FellowStaggDataUpdateCoordinator(DataUpdateCoordinator):
  """Class to manage fetching Fellow Stagg data."""

  def __init__(self, hass: HomeAssistant, address: str, entry_id: str, polling_interval: timedelta) -> None:
    """Initialize the coordinator."""
    super().__init__(
      hass,
      _LOGGER,
      name=f"Fellow Stagg {address}",
      update_interval=polling_interval,
    )
    self.kettle = KettleBLEClient(address)
    self.ble_device = None
    self._address = address
    self.entry_id = entry_id
    self._last_service_info = None  # cached for idle-kettle directed connect

    self.device_info = DeviceInfo(
      identifiers={(DOMAIN, address)},
      name=f"Fellow Stagg EKG+ {address}",
      manufacturer="Fellow",
      model="Stagg EKG+",
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

  def _inject_cached_ble_device(self) -> None:
    """Re-insert the last known service info into the BLE scanner cache.

    The kettle stops advertising after ~3 min idle but accepts directed connections.
    HA's BLE routing requires a live scanner cache entry to route through the proxy.
    Injecting the cached entry with a current timestamp unblocks routing; the proxy
    then initiates the directed BLE connection by address.
    """
    service_info = self._last_service_info
    if service_info is None:
      return
    try:
      from bluetooth_data_tools import monotonic_time_coarse
      service_info.time = monotonic_time_coarse()
    except Exception:
      pass
    scanner = async_scanner_by_source(self.hass, service_info.source)
    if scanner is not None:
      scanner._previous_service_info[self._address] = service_info
      _LOGGER.debug(
        "Injected cached BLE device for %s via scanner %s for directed connect",
        self._address, service_info.source,
      )

  def get_ble_device_for_connect(self):
    """Return the best available BLEDevice, injecting cached state if needed.

    Returns the live device if present, the cached device after cache injection
    if available, or None if no prior advertisement has ever been seen.
    """
    ble_device = async_ble_device_from_address(self.hass, self._address, True)
    if ble_device is not None:
      return ble_device
    if self._last_service_info is not None:
      self._inject_cached_ble_device()
      return self._last_service_info.device
    return None

  async def _async_update_data(self) -> dict[str, Any] | None:
    """Fetch data from the kettle."""
    _LOGGER.debug("Starting poll for Fellow Stagg kettle %s", self._address)

    self.ble_device = async_ble_device_from_address(self.hass, self._address, True)
    if not self.ble_device:
      if self._last_service_info is not None:
        _LOGGER.debug(
          "No advertisement in cache; injecting cached service info for directed connect to %s",
          self._address,
        )
        self._inject_cached_ble_device()
        self.ble_device = self._last_service_info.device
      else:
        _LOGGER.debug(
          "No advertisement and no cached service info for %s; skipping poll",
          self._address,
        )
        return None

    try:
      _LOGGER.debug("Attempting to poll kettle data...")
      data = await self.kettle.async_poll(self.ble_device)
      _LOGGER.debug(
        "Successfully polled data from kettle %s: %s",
        self._address,
        data,
      )

      # Update cache after a successful poll
      fresh_info = async_last_service_info(self.hass, self._address, True)
      if fresh_info is not None:
        self._last_service_info = fresh_info

      # Log any changes in data compared to previous state
      if self.data is not None:
        changes = {
          k: (self.data.get(k), v)
          for k, v in data.items()
          if k in self.data and self.data.get(k) != v
        }
        if changes:
          _LOGGER.debug("Data changes detected: %s", changes)

      return data
    except Exception as e:
      _LOGGER.error(
        "Error polling Fellow Stagg kettle %s: %s",
        self._address,
        str(e),
      )
      return None


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
  interval_seconds = entry.options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
  coordinator = FellowStaggDataUpdateCoordinator(hass, address, entry.entry_id, timedelta(seconds=interval_seconds))

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
