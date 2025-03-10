"""Binary sensor platform for Fellow Stagg EKG Pro kettle."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FellowStaggDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fellow Stagg binary sensor based on a config entry."""
    coordinator: FellowStaggDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FellowStaggConnectionSensor(coordinator)])


class FellowStaggConnectionSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Fellow Stagg kettle connection status."""

    _attr_has_entity_name = True
    _attr_name = "Connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: FellowStaggDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._address}_connection"
        self._attr_device_info = coordinator.device_info
        _LOGGER.debug("Initialized connection sensor for %s", coordinator._address)

    @property
    def is_on(self) -> bool:
        """Return true if the kettle is connected."""
        return self.coordinator.last_update_success
