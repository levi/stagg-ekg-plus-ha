"""Number platform for Fellow Stagg EKG+ kettle."""
from __future__ import annotations

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

from . import FellowStaggDataUpdateCoordinator
from .const import DOMAIN

async def async_setup_entry(
  hass: HomeAssistant,
  entry: ConfigEntry,
  async_add_entities: AddEntitiesCallback,
) -> None:
  """Set up Fellow Stagg number based on a config entry."""
  coordinator: FellowStaggDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
  async_add_entities([FellowStaggTargetTemperature(coordinator)])

class FellowStaggTargetTemperature(NumberEntity):
  """Number class for Fellow Stagg kettle target temperature control."""

  _attr_has_entity_name = True
  _attr_name = "Target Temperature"
  _attr_mode = NumberMode.BOX
  _attr_native_step = 1.0

  def __init__(self, coordinator: FellowStaggDataUpdateCoordinator) -> None:
    """Initialize the number."""
    self.coordinator = coordinator
    self._attr_unique_id = f"{coordinator._address}_target_temp"
    self._attr_device_info = coordinator.device_info
    
    # Set temperature range based on units
    is_fahrenheit = coordinator.data.get("units") == "F"
    if is_fahrenheit:
      self._attr_native_min_value = 104
      self._attr_native_max_value = 212
      self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    else:
      self._attr_native_min_value = 40
      self._attr_native_max_value = 100
      self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

  @property
  def native_value(self) -> float | None:
    """Return the current target temperature."""
    return self.coordinator.data.get("target_temp")

  async def async_set_native_value(self, value: float) -> None:
    """Set new target temperature."""
    is_fahrenheit = self.coordinator.data.get("units") == "F"
    await self.coordinator.kettle.async_set_temperature(
      self.coordinator.ble_device,
      int(value),
      fahrenheit=is_fahrenheit
    )
    await self.coordinator.async_request_refresh() 
