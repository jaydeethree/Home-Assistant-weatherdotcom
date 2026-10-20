"""
Sensor Support for Weather.com weather service.
For more details about this platform, please refer to the documentation at
https://github.com/jaydeethree/Home-Assistant-weatherdotcom
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.unit_system import METRIC_SYSTEM

from . import WeatherDotComConfigEntry
from .coordinator import WeatherUpdateCoordinator

from .const import (
    CONF_ATTRIBUTION,
    CONF_EXTRA_ATTRIBUTES,
    FIELD_DAYPART,
    FIELD_VALIDTIMEUTC,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,
    RESULTS_CURRENT,
)
from .weather_current_conditions_sensors import (
    WeatherSensorEntityDescription,
    current_condition_sensor_descriptions,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant, entry: WeatherDotComConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Weather.com entities from a config_entry."""
    coordinator = entry.runtime_data
    sensors = [
        WeatherSensor(
            coordinator, 
            description, 
            entry.options.get(CONF_EXTRA_ATTRIBUTES),
            ) for description in current_condition_sensor_descriptions
    ]

    async_add_entities(sensors)


class WeatherSensor(CoordinatorEntity, SensorEntity):
    """Implementing the Weather.com sensor."""
    _attr_has_entity_name = True
    _attr_attribution = CONF_ATTRIBUTION
    entity_description: WeatherSensorEntityDescription

    def __init__(
            self,
            coordinator: WeatherUpdateCoordinator,
            description: WeatherSensorEntityDescription,
            extra_attributes: list[str] | None = None,
    ):
        super().__init__(coordinator)
        self.entity_description = description
        self._extra_attributes = extra_attributes

        # This will cause problems if we ever add another type of entity, but
        # for now all entities are of type 'sensor' so this is okay.
        entity_id_format = "sensor.{}"

        self._attr_unique_id = f"{self.coordinator.location_name},{description.key}".lower()
        self.entity_id = generate_entity_id(
            entity_id_format, f"{self.coordinator.location_name}_{description.name}", hass=coordinator.hass
        )
        self._attr_device_info = coordinator.device_info
        self._attr_native_unit_of_measurement = self.entity_description.unit_fn(
            self.coordinator.hass.config.units is METRIC_SYSTEM)

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the registry."""
        if self.entity_description.key == FIELD_VALIDTIMEUTC:
            return bool(self._extra_attributes)
        return self.entity_description.entity_registry_enabled_default

    @property
    def available(self) -> bool:
        """Return if weather data is available."""
        return super().available and self.coordinator.data is not None

    @property
    def name(self):
        """Return the name of the sensor."""
        if self.entity_description.key in self.coordinator._tranfile:
            return self.coordinator._tranfile[self.entity_description.key]
        if (
            FIELD_DAYPART in self.coordinator._tranfile
            and self.entity_description.key in self.coordinator._tranfile[FIELD_DAYPART]
        ):
            return self.coordinator._tranfile[FIELD_DAYPART][self.entity_description.key]

        return self.entity_description.name

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        if self.entity_description.key == CONF_LATITUDE:
            data = getattr(self.coordinator, "current_latitude", getattr(self.coordinator, "_latitude", None))
        elif self.entity_description.key == CONF_LONGITUDE:
            data = getattr(self.coordinator, "current_longitude", getattr(self.coordinator, "_longitude", None))
        else:
            data = _get_sensor_data(
                self.coordinator.data, self.entity_description.key
            )
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self.entity_description.attr_fn:
            return None
        return self.entity_description.attr_fn(
            self.coordinator.data,
            self._extra_attributes,
        ) or None


def _get_sensor_data(
        sensors: dict[str, Any] | None,
        kind: str,
) -> Any:
    """Get sensor data."""
    # windGust is often null. When it is, set it to windSpeed instead.
    if not sensors or sensors.get(RESULTS_CURRENT) is None:
        return None
    if kind == FIELD_WINDGUST and sensors[RESULTS_CURRENT].get(kind) is None:
        return sensors[RESULTS_CURRENT].get(FIELD_WINDSPEED)
    return sensors[RESULTS_CURRENT].get(kind)