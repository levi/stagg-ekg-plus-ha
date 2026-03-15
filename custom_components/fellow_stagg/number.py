"""Number platform for Fellow Stagg EKG+ kettle."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.number import (
  NumberEntity,
  NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FellowStaggDataUpdateCoordinator
from .const import DOMAIN, CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, MIN_POLLING_INTERVAL, MAX_POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
  hass: HomeAssistant,
  entry: ConfigEntry,
  async_add_entities: AddEntitiesCallback,
) -> None:
  """Set up Fellow Stagg number based on a config entry."""
  coordinator: FellowStaggDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
  async_add_entities([FellowStaggTargetTemperature(coordinator), FellowStaggPollingInterval(coordinator)])

class FellowStaggTargetTemperature(NumberEntity):
  """Number class for Fellow Stagg kettle target temperature control."""

  _attr_has_entity_name = True
  _attr_name = "Target Temperature"
  _attr_mode = NumberMode.BOX
  _attr_native_step = 1.0

  def __init__(self, coordinator: FellowStaggDataUpdateCoordinator) -> None:
    """Initialize the number."""
    super().__init__()
    self.coordinator = coordinator
    self._attr_unique_id = f"{coordinator._address}_target_temp"
    self._attr_device_info = coordinator.device_info
    
    _LOGGER.debug("Initializing target temp with units: %s", coordinator.temperature_unit)
    
    self._attr_native_min_value = coordinator.min_temp
    self._attr_native_max_value = coordinator.max_temp
    self._attr_native_unit_of_measurement = coordinator.temperature_unit
    
    _LOGGER.debug(
      "Target temp range set to: %s°%s - %s°%s",
      self._attr_native_min_value,
      self._attr_native_unit_of_measurement,
      self._attr_native_max_value,
      self._attr_native_unit_of_measurement,
    )

  @property
  def native_value(self) -> float | None:
    """Return the current target temperature."""
    value = self.coordinator.data.get("target_temp")
    _LOGGER.debug("Target temperature read as: %s°%s", value, self.coordinator.temperature_unit)
    return value

  async def async_set_native_value(self, value: float) -> None:
    """Set new target temperature."""
    _LOGGER.debug(
      "Setting target temperature to %s°%s",
      value,
      self.coordinator.temperature_unit
    )
    
    await self.coordinator.kettle.async_set_temperature(
      self.coordinator.ble_device,
      int(value),
      fahrenheit=self.coordinator.temperature_unit == UnitOfTemperature.FAHRENHEIT
    )
    _LOGGER.debug("Target temperature command sent, waiting before refresh")
    # Give the kettle a moment to update its internal state
    await asyncio.sleep(0.5)
    _LOGGER.debug("Requesting refresh after temperature change")
    await self.coordinator.async_request_refresh()


class FellowStaggPollingInterval(CoordinatorEntity, NumberEntity):
  """Number entity to configure the polling interval."""

  _attr_has_entity_name = True
  _attr_name = "Polling Interval"
  _attr_mode = NumberMode.BOX
  _attr_native_step = 1
  _attr_native_min_value = MIN_POLLING_INTERVAL
  _attr_native_max_value = MAX_POLLING_INTERVAL
  _attr_native_unit_of_measurement = "s"
  _attr_icon = "mdi:timer-sync"
  _attr_entity_category = EntityCategory.DIAGNOSTIC
  _attr_entity_registry_enabled_default = False

  def __init__(self, coordinator: FellowStaggDataUpdateCoordinator) -> None:
    """Initialize the polling interval entity."""
    super().__init__(coordinator)
    self._attr_unique_id = f"{coordinator._address}_polling_interval"
    self._attr_device_info = coordinator.device_info

  @property
  def native_value(self) -> int:
    """Return the current polling interval."""
    entry = self.hass.config_entries.async_get_entry(self.coordinator.entry_id)
    if entry is None:
      return DEFAULT_POLLING_INTERVAL
    return int(entry.options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL))

  async def async_set_native_value(self, value: float) -> None:
    """Set a new polling interval."""
    seconds = int(value)
    entry = self.hass.config_entries.async_get_entry(self.coordinator.entry_id)
    if entry is not None:
      self.hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_POLLING_INTERVAL: seconds})
    self.coordinator.update_interval = timedelta(seconds=seconds)
    self.async_write_ha_state()
