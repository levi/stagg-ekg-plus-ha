"""Number platform for Fellow Stagg EKG+ kettle."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fellow Stagg number based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FellowStaggTemperature(coordinator)])


class FellowStaggTemperature(NumberEntity):
    """Representation of a Fellow Stagg temperature control."""

    _attr_has_entity_name = True
    _attr_name = "Target Temperature"
    _attr_icon = "mdi:thermometer"
    _attr_native_min_value = 104
    _attr_native_max_value = 212
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator):
        """Initialize the temperature control."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_target_temp"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current target temperature."""
        if not self.coordinator.last_poll_data:
            return None
        return self.coordinator.last_poll_data.get("target_temp")

    async def async_set_native_value(self, value: float) -> None:
        """Set new target temperature."""
        async with self.coordinator.client_session() as client:
            await self.coordinator.kettle_client.async_set_temperature(client, int(value))
        await self.coordinator.async_request_refresh() 
