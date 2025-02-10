"""Switch platform for Fellow Stagg EKG+ kettle."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
  """Set up Fellow Stagg switch based on a config entry."""
  coordinator: FellowStaggDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
  async_add_entities([FellowStaggPowerSwitch(coordinator)])

class FellowStaggPowerSwitch(SwitchEntity):
  """Switch class for Fellow Stagg kettle power control."""

  _attr_has_entity_name = True
  _attr_name = "Power"

  def __init__(self, coordinator: FellowStaggDataUpdateCoordinator) -> None:
    """Initialize the switch."""
    self.coordinator = coordinator
    self._attr_unique_id = f"{coordinator._address}_power"
    self._attr_device_info = coordinator.device_info

  @property
  def is_on(self) -> bool | None:
    """Return true if the switch is on."""
    return self.coordinator.data.get("power")

  async def async_turn_on(self, **kwargs: Any) -> None:
    """Turn the switch on."""
    await self.coordinator.kettle.async_set_power(self.coordinator.ble_device, True)
    await self.coordinator.async_request_refresh()

  async def async_turn_off(self, **kwargs: Any) -> None:
    """Turn the switch off."""
    await self.coordinator.kettle.async_set_power(self.coordinator.ble_device, False)
    await self.coordinator.async_request_refresh() 
