from dataclasses import dataclass
from typing import Any, TypeVar, Callable

from homeassistant import config_entries
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


@dataclass
class FellowStaggSensorEntityDescription(SensorEntityDescription):
    """Description of a Fellow Stagg sensor."""


# Define value functions separately to avoid serialization issues
VALUE_FUNCTIONS: dict[str, Callable[[dict[str, Any] | None], Any | None]] = {
    "power": lambda data: "On" if data and data.get("power") else "Off",
    "current_temp": lambda data: data.get("current_temp") if data else None,
    "target_temp": lambda data: data.get("target_temp") if data else None,
    "hold": lambda data: "Hold" if data and data.get("hold") else "Normal",
    "lifted": lambda data: "Lifted" if data and data.get("lifted") else "On Base",
    "countdown": lambda data: data.get("countdown") if data else None,
}


def get_sensor_descriptions() -> list[FellowStaggSensorEntityDescription]:
    """Get sensor descriptions."""
    return [
        FellowStaggSensorEntityDescription(
            key="power",
            name="Power",
            icon="mdi:power",
        ),
        FellowStaggSensorEntityDescription(
            key="current_temp",
            name="Current Temperature",
            icon="mdi:thermometer",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        ),
        FellowStaggSensorEntityDescription(
            key="target_temp",
            name="Target Temperature",
            icon="mdi:thermometer",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        ),
        FellowStaggSensorEntityDescription(
            key="hold",
            name="Hold Mode",
            icon="mdi:timer",
        ),
        FellowStaggSensorEntityDescription(
            key="lifted",
            name="Kettle Position",
            icon="mdi:cup",
        ),
        FellowStaggSensorEntityDescription(
            key="countdown",
            name="Countdown",
            icon="mdi:timer",
            native_unit_of_measurement="s",
        ),
    ]


# Get sensor descriptions once at module load
SENSOR_DESCRIPTIONS = get_sensor_descriptions()


def sensor_update_to_bluetooth_data_update(
    data: dict[str, Any] | None,
) -> PassiveBluetoothDataUpdate:
    """Convert sensor update to Bluetooth data update."""
    entity_descriptions = {}
    entity_data = {}
    entity_names = {}

    for description in SENSOR_DESCRIPTIONS:
        key = PassiveBluetoothEntityKey(key=description.key, device_id=None)
        entity_descriptions[key] = description
        entity_names[key] = description.name
        if value_fn := VALUE_FUNCTIONS.get(description.key):
            entity_data[key] = value_fn(data)

    return PassiveBluetoothDataUpdate(
        devices={},
        entity_descriptions=entity_descriptions,
        entity_data=entity_data,
        entity_names=entity_names,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fellow Stagg BLE sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    processor = PassiveBluetoothDataProcessor[float | int | str | None, None](
        sensor_update_to_bluetooth_data_update
    )
    entry.async_on_unload(
        processor.async_add_entities_listener(
            FellowStaggBluetoothSensorEntity,
            async_add_entities,
        )
    )
    entry.async_on_unload(coordinator.async_register_processor(processor))


class FellowStaggBluetoothSensorEntity(
    PassiveBluetoothProcessorEntity[
        PassiveBluetoothDataProcessor[float | int | str | None, None]
    ],
    SensorEntity,
):
    """Representation of a Fellow Stagg Bluetooth sensor."""

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)
