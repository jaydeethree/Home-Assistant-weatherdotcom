"""
Sensor Support for Weather.com weather service.
For more details about this platform, please refer to the documentation at
https://github.com/jaydeethree/Home-Assistant-weatherdotcom
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WeatherDotComConfigEntry
from .coordinator import WeatherUpdateCoordinator

from .const import (
    ATTRIBUTION,
    CONF_EXTRA_ATTRIBUTES,
    EXTRA_ATTRIBUTE_KEYS_DAILY,
    EXTRA_ATTRIBUTE_KEYS_DAY,
    EXTRA_ATTRIBUTE_KEYS_DAYPART,
    FIELD_DAYPART,
    FIELD_VALIDTIMEUTC,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,
    RESULTS_CURRENT,
    RESULTS_FORECAST_DAILY,
)
from .helpers import get_sensor_unique_id
from .weather_current_conditions_sensors import (
    WeatherSensorEntityDescription,
    current_condition_sensor_descriptions,
)


async def async_setup_entry(
        hass: HomeAssistant, entry: WeatherDotComConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
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


class WeatherSensor(CoordinatorEntity[WeatherUpdateCoordinator], SensorEntity):
    """Implementing the Weather.com sensor."""
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset(
        EXTRA_ATTRIBUTE_KEYS_DAILY + EXTRA_ATTRIBUTE_KEYS_DAY + EXTRA_ATTRIBUTE_KEYS_DAYPART
    )
    entity_description: WeatherSensorEntityDescription

    def __init__(
            self,
            coordinator: WeatherUpdateCoordinator,
            description: WeatherSensorEntityDescription,
            extra_attributes: list[str] | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._extra_attributes = extra_attributes

        self._attr_unique_id = get_sensor_unique_id(
            self.coordinator.location_name, description.key
        )
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, f"{self.coordinator.location_name}_{description.name}", hass=coordinator.hass
        )
        self._attr_device_info = coordinator.device_info
        self._attr_native_unit_of_measurement = self.entity_description.unit_fn(
            self.coordinator.units
        )
        if description.key == FIELD_VALIDTIMEUTC:
            self._attr_entity_registry_enabled_default = bool(extra_attributes)

        if description.key in coordinator.tranfile:
            self._attr_name = coordinator.tranfile[description.key]
        elif (
            FIELD_DAYPART in coordinator.tranfile
            and description.key in coordinator.tranfile[FIELD_DAYPART]
        ):
            self._attr_name = coordinator.tranfile[FIELD_DAYPART][description.key]
        else:
            self._attr_name = description.name

    @property
    def available(self) -> bool:
        """Return if weather data is available."""
        if not super().available or self.coordinator.data is None:
            return False
        if self.entity_description.key in (CONF_LATITUDE, CONF_LONGITUDE):
            return True
        if self.entity_description.key == FIELD_VALIDTIMEUTC:
            return self.coordinator.data.get(RESULTS_FORECAST_DAILY) is not None
        return self.coordinator.data.get(RESULTS_CURRENT) is not None

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        if self.entity_description.key == CONF_LATITUDE:
            data = self.coordinator.current_latitude
        elif self.entity_description.key == CONF_LONGITUDE:
            data = self.coordinator.current_longitude
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
    if not sensors:
        return None
    if kind == FIELD_VALIDTIMEUTC:
        daily = sensors.get(RESULTS_FORECAST_DAILY)
        if not daily or not (valid_times := daily.get(FIELD_VALIDTIMEUTC)):
            return None
        return valid_times[0]
    # windGust is often null. When it is, set it to windSpeed instead.
    if sensors.get(RESULTS_CURRENT) is None:
        return None
    if kind == FIELD_WINDGUST and sensors[RESULTS_CURRENT].get(kind) is None:
        return sensors[RESULTS_CURRENT].get(FIELD_WINDSPEED)
    return sensors[RESULTS_CURRENT].get(kind)