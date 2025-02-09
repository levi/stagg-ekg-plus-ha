"""Switch platform for Fellow Stagg EKG+ kettle."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fellow Stagg switch based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FellowStaggSwitch(coordinator)])


class FellowStaggSwitch(SwitchEntity):
    """Representation of a Fellow Stagg switch."""

    _attr_has_entity_name = True
    _attr_name = "Power"
    _attr_icon = "mdi:kettle"

    def __init__(self, coordinator):
        """Initialize the switch."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_power"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.last_poll_data:
            return None
        return self.coordinator.last_poll_data.get("power", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        async with self.coordinator.client_session() as client:
            await self.coordinator.kettle_client.async_turn_on(client)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        async with self.coordinator.client_session() as client:
            await self.coordinator.kettle_client.async_turn_off(client)
        await self.coordinator.async_request_refresh() 
