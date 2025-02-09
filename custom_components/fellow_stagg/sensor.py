from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors for Fellow Stagg kettle."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FellowStaggPowerSensor(coordinator),
        FellowStaggCurrentTempSensor(coordinator),
        FellowStaggTargetTempSensor(coordinator),
        FellowStaggHoldSensor(coordinator),
        FellowStaggLiftedSensor(coordinator),
        FellowStaggCountdownSensor(coordinator),
    ]
    async_add_entities(entities)


class FellowStaggBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Fellow Stagg kettle."""

    _attr_should_poll = False

    def __init__(self, coordinator, name, icon, unit=None):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._unit = unit

    @property
    def native_unit_of_measurement(self):
        return self._unit


class FellowStaggPowerSensor(FellowStaggBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Fellow Stagg Power", "mdi:power")

    @property
    def native_value(self):
        return "On" if self.coordinator.data.get("power") else "Off"


class FellowStaggCurrentTempSensor(FellowStaggBaseSensor):
    def __init__(self, coordinator):
        # Default to Fahrenheit unit if not provided in data.
        super().__init__(
            coordinator, "Fellow Stagg Current Temperature", "mdi:thermometer", "°F"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("current_temp")


class FellowStaggTargetTempSensor(FellowStaggBaseSensor):
    def __init__(self, coordinator):
        super().__init__(
            coordinator, "Fellow Stagg Target Temperature", "mdi:thermometer", "°F"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("target_temp")


class FellowStaggHoldSensor(FellowStaggBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Fellow Stagg Hold Mode", "mdi:timer")

    @property
    def native_value(self):
        return "Hold" if self.coordinator.data.get("hold") else "Normal"


class FellowStaggLiftedSensor(FellowStaggBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Fellow Stagg Kettle Position", "mdi:cup")

    @property
    def native_value(self):
        return "Lifted" if self.coordinator.data.get("lifted") else "On Base"


class FellowStaggCountdownSensor(FellowStaggBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Fellow Stagg Countdown", "mdi:timer", "s")

    @property
    def native_value(self):
        return self.coordinator.data.get("countdown")
