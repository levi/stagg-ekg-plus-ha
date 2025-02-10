"""Water heater platform for Fellow Stagg EKG+ kettle."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.water_heater import (
  WaterHeaterEntity,
  WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
  ATTR_TEMPERATURE,
  UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FellowStaggDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
  hass: HomeAssistant,
  entry: ConfigEntry,
  async_add_entities: AddEntitiesCallback,
) -> None:
  """Set up Fellow Stagg water heater based on a config entry."""
  coordinator: FellowStaggDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
  async_add_entities([FellowStaggWaterHeater(coordinator)])

class FellowStaggWaterHeater(WaterHeaterEntity):
  """Water heater entity for Fellow Stagg kettle."""

  _attr_has_entity_name = True
  _attr_name = "Water Heater"
  _attr_supported_features = (
    WaterHeaterEntityFeature.TARGET_TEMPERATURE |
    WaterHeaterEntityFeature.ON_OFF
  )
  _attr_operation_list = ["off", "on"]

  def __init__(self, coordinator: FellowStaggDataUpdateCoordinator) -> None:
    """Initialize the water heater."""
    super().__init__()
    self.coordinator = coordinator
    self._attr_unique_id = f"{coordinator._address}_water_heater"
    self._attr_device_info = coordinator.device_info

    _LOGGER.debug("Initializing water heater with units: %s", coordinator.temperature_unit)
    
    self._attr_min_temp = coordinator.min_temp
    self._attr_max_temp = coordinator.max_temp
    self._attr_temperature_unit = coordinator.temperature_unit
    
    _LOGGER.debug(
      "Water heater temperature range set to: %s°%s - %s°%s",
      self._attr_min_temp,
      self._attr_temperature_unit,
      self._attr_max_temp,
      self._attr_temperature_unit,
    )

  @property
  def current_temperature(self) -> float | None:
    """Return the current temperature."""
    value = self.coordinator.data.get("current_temp") if self.coordinator.data else None
    _LOGGER.debug("Water heater current temperature read as: %s°%s", value, self.coordinator.temperature_unit)
    return value

  @property
  def target_temperature(self) -> float | None:
    """Return the target temperature."""
    value = self.coordinator.data.get("target_temp") if self.coordinator.data else None
    _LOGGER.debug("Water heater target temperature read as: %s°%s", value, self.coordinator.temperature_unit)
    return value

  @property
  def current_operation(self) -> str | None:
    """Return current operation."""
    if not self.coordinator.data:
      return None
    value = "on" if self.coordinator.data.get("power") else "off"
    _LOGGER.debug("Water heater operation state read as: %s", value)
    return value

  async def async_set_temperature(self, **kwargs: Any) -> None:
    """Set new target temperature."""
    temperature = kwargs.get(ATTR_TEMPERATURE)
    if temperature is None:
      return

    _LOGGER.debug(
      "Setting water heater target temperature to %s°%s",
      temperature,
      self.coordinator.temperature_unit
    )
    
    await self.coordinator.kettle.async_set_temperature(
      self.coordinator.ble_device,
      int(temperature),
      fahrenheit=self.coordinator.temperature_unit == UnitOfTemperature.FAHRENHEIT
    )
    _LOGGER.debug("Target temperature command sent, waiting before refresh")
    # Give the kettle a moment to update its internal state
    await asyncio.sleep(0.5)
    _LOGGER.debug("Requesting refresh after temperature change")
    await self.coordinator.async_request_refresh()

  async def async_turn_on(self, **kwargs: Any) -> None:
    """Turn the water heater on."""
    _LOGGER.debug("Turning water heater ON")
    await self.coordinator.kettle.async_set_power(self.coordinator.ble_device, True)
    _LOGGER.debug("Power ON command sent, waiting before refresh")
    # Give the kettle a moment to update its internal state
    await asyncio.sleep(0.5)
    _LOGGER.debug("Requesting refresh after power change")
    await self.coordinator.async_request_refresh()

  async def async_turn_off(self, **kwargs: Any) -> None:
    """Turn the water heater off."""
    _LOGGER.debug("Turning water heater OFF")
    await self.coordinator.kettle.async_set_power(self.coordinator.ble_device, False)
    _LOGGER.debug("Power OFF command sent, waiting before refresh")
    # Give the kettle a moment to update its internal state
    await asyncio.sleep(0.5)
    _LOGGER.debug("Requesting refresh after power change")
    await self.coordinator.async_request_refresh() 
