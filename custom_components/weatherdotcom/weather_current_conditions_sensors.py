from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any, cast, Final
from datetime import UTC, datetime

from .const import (
    FIELD_DESCRIPTION,
    FIELD_DEW_POINT,
    FIELD_FEELS_LIKE,
    FIELD_HUMIDITY,
    FIELD_PRESSURE,
    FIELD_TEMP,
    FIELD_UV_INDEX,
    FIELD_WINDDIR,
    FIELD_WINDDIRECTIONCARDINAL,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,
    ICON_SNOWFLAKE,
    ICON_THERMOMETER,
    ICON_UMBRELLA,
    ICON_WIND
)
from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UV_INDEX, DEGREE, UnitOfLength, UnitOfTemperature, \
    UnitOfVolumetricFlux, UnitOfPressure, UnitOfSpeed
from homeassistant.helpers.typing import StateType


# Mapping of daily sensor attributes to Weather.com API names
DAILY_ATTRIBUTE_MAP: Final[dict[str, str]] = {
    "day": "dayOfWeek",
    "daily_temp_max": "calendarDayTemperatureMax",
    "daily_temp_min": "calendarDayTemperatureMin",
    "daily_precip_qpf": "qpf",
    "daily_rain_qpf": "qpfRain",
    "daily_snow_qpf": "qpfSnow",
    "daily_ice_qpf": "qpfIce",
    "sunrise": "sunriseTimeLocal",
    "sunset": "sunsetTimeLocal",
    "moon_phase": "moonPhase",
    "moon_phase_code": "moonPhaseCode",
    "moon_phase_day": "moonPhaseDay",
    "moonrise": "moonriseTimeLocal",
    "moonset": "moonsetTimeLocal",
    "daily_narrative": "narrative",
}

# Mapping of daypart attributes to Weather.com API names
DAYPART_ATTRIBUTE_MAP: Final[dict[str, str]] = {
    "daypart_cloud_cover": "cloudCover",
    "daypart_name": "daypartName",
    "daypart_icon_code": "iconCode",
    "daypart_precip_chance": "precipChance",
    "daypart_precip_type": "precipType",
    "daypart_total_qpf": "qpf",
    "daypart_rain_qpf": "qpfRain",
    "daypart_snow_qpf": "qpfSnow",
    "daypart_ice_qpf": "qpfIce",
    "daypart_snow_range": "snowRange",
    "daypart_relative_humidity": "relativeHumidity",
    "daypart_heat_index": "temperatureHeatIndex",
    "daypart_wind_chill": "temperatureWindChill",
    "daypart_thunder_category": "thunderCategory",
    "daypart_thunder_index": "thunderIndex",
    "daypart_uv_description": "uvDescription",
    "daypart_uv_index": "uvIndex",
    "daypart_wind_dir": "windDirection",
    "daypart_wind_dir_cardinal": "windDirectionCardinal",
    "daypart_wind_speed": "windSpeed",
    "daypart_wind_phrase": "windPhrase",
    "daypart_wx_phrase_long": "wxPhraseLong",
    "daypart_wx_phrase_short": "wxPhraseShort",
    "daypart_qualifier_phrase": "qualifierPhrase",
    "daypart_narrative": "narrative",
}

DAY_KEYS: Final[set[str]] = {
    "day_icon_code",
    "day_cloud_cover",
    "day_relative_humidity",
}


def _get_extra_attributes(
    coordinator_data: dict[str, Any] | None,
    selected_attributes: list[str] | None = None,
) -> dict[str, Any] | None:
    if not selected_attributes or not coordinator_data:
        return None

    daily_data = coordinator_data.get("daily")
    # Everything relies on daily_data, so if it's empty then return early.
    if not isinstance(daily_data, dict):
        return None

    selected_attributes_set = set(selected_attributes)
    result: dict[str, Any] = {}

    for attr_name, api_name in DAILY_ATTRIBUTE_MAP.items():
        if attr_name in selected_attributes_set:
            val = daily_data.get(api_name)
            result[attr_name] = val if val is not None else [0] * 15

    # Check whether any other attributes are needed
    needed_daypart_attrs = selected_attributes_set.intersection(DAYPART_ATTRIBUTE_MAP)
    needed_day_attrs = selected_attributes_set.intersection(DAY_KEYS)
    if not needed_daypart_attrs and not needed_day_attrs:
        return result or None

    dayparts = daily_data.get("daypart")
    daypart_data = (
        dayparts[0]
        if (isinstance(dayparts, list) and dayparts and isinstance(dayparts[0], dict))
        else {}
    )
    for attr_name in needed_daypart_attrs:
        api_name = DAYPART_ATTRIBUTE_MAP[attr_name]
        val = daypart_data.get(api_name)
        result[attr_key] = val if val is not None else [0] * 30

    if needed_day_attrs:
        daypart_icon_code = daypart_data.get("iconCode") or []
        daypart_cloud_cover = daypart_data.get("cloudCover") or []
        daypart_relative_humidity = daypart_data.get("relativeHumidity") or []

        # Weather.com sets index 0 to None after 15:00 local time
        # When None, shift day 0 to index 1 (tonight's forecast)
        first_index = 1 if daypart_icon_code[0] is None else 0
        indices = [first_index, *range(2, 29, 2)]

        def _safe_get(arr: list, idx: int, default: Any = None) -> Any:
            return arr[idx] if idx < len(arr) else default

        if "day_icon_code" in needed_day_attrs:
            result["day_icon_code"] = [
                _safe_get(daypart_icon_code, i, 0) for i in indices
            ]

        if "day_cloud_cover" in needed_day_attrs:
            result["day_cloud_cover"] = [
                _safe_get(daypart_cloud_cover, i, 0) or 0 for i in indices
            ]

        if "day_relative_humidity" in needed_day_attrs:
            result["day_relative_humidity"] = [
                _safe_get(daypart_relative_humidity, i, 0) or 0 for i in indices
            ]

    return result or None


@dataclass
class WeatherRequiredKeysMixin:
    """Mixin for required keys."""
    value_fn: Callable[[dict[str, Any], str], StateType]


@dataclass
class WeatherSensorEntityDescription(
    SensorEntityDescription, WeatherRequiredKeysMixin
):
    attr_fn: Callable[
        [dict[str, Any], list[str] | None],
        dict[str, Any] | None,
    ] | None = None
    unit_fn: Callable[[bool], str | None] = lambda _: None
    """Describes Weather.com Sensor entity."""


current_condition_sensor_descriptions = [
    WeatherSensorEntityDescription(
        key="validTimeLocal",
        name="Local Observation Time",
        icon="mdi:clock",
        value_fn=lambda data, _: cast(str, data),
    ),
    WeatherSensorEntityDescription(
        key=FIELD_DESCRIPTION,
        name="Weather Description",
        icon="mdi:note-text",
        value_fn=lambda data, _: cast(str, data),
    ),
    WeatherSensorEntityDescription(
        key=FIELD_HUMIDITY,
        name="Relative Humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _: PERCENTAGE,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key=FIELD_UV_INDEX,
        name="UV Index",
        icon="mdi:sunglasses",
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _: UV_INDEX,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key=FIELD_WINDDIR,
        name="Wind Direction - Degrees",
        icon=ICON_WIND,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _: DEGREE,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key=FIELD_WINDDIRECTIONCARDINAL,
        name="Wind Direction - Cardinal",
        icon=ICON_WIND,
        unit_fn=lambda _: None,
        value_fn=lambda data, _: cast(str, data) or "",
    ),
    WeatherSensorEntityDescription(
        key=FIELD_DEW_POINT,
        name="Dewpoint",
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key=FIELD_FEELS_LIKE,
        name="Temperature - Feels Like",
        icon=ICON_THERMOMETER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key=FIELD_TEMP,
        name="Temperature",
        icon=ICON_THERMOMETER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="temperatureHeatIndex",
        name="Heat Index",
        icon=ICON_THERMOMETER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="temperatureWindChill",
        name="Wind Chill",
        icon=ICON_THERMOMETER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="precip1Hour",
        name="Precipitation - Last hour",
        icon=ICON_UMBRELLA,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="precip6Hour",
        name="Precipitation - Last 6 hours",
        icon=ICON_UMBRELLA,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="precip24Hour",
        name="Precipitation - Last 24 hours",
        icon=ICON_UMBRELLA,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key=FIELD_PRESSURE,
        name="Pressure",
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRESSURE,
        unit_fn=lambda metric: UnitOfPressure.MBAR if metric else UnitOfPressure.INHG,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key=FIELD_WINDGUST,
        name="Wind Gust",
        icon=ICON_WIND,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.WIND_SPEED,
        unit_fn=lambda metric: UnitOfSpeed.KILOMETERS_PER_HOUR if metric else UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key=FIELD_WINDSPEED,
        name="Wind Speed",
        icon=ICON_WIND,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.WIND_SPEED,
        unit_fn=lambda metric: UnitOfSpeed.KILOMETERS_PER_HOUR if metric else UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="cloudCeiling",
        name="Cloud Ceiling",
        icon="mdi:clouds",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit_fn=lambda metric: UnitOfLength.METERS if metric else UnitOfLength.FEET,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="pressureTendencyTrend",
        name="Pressure Tendency Trend",
        icon="mdi:gauge",
        value_fn=lambda data, _: cast(str, data),
    ),
    WeatherSensorEntityDescription(
        key="cloudCoverPhrase",
        name="Cloud Cover Phrase",
        icon="mdi:clouds",
        value_fn=lambda data, _: cast(str, data),
    ),
    WeatherSensorEntityDescription(
        key="latitude",
        name="Latitude",
        icon="mdi:latitude",
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="longitude",
        name="Longitude",
        icon="mdi:longitude",
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="iconCode",
        name="Icon Code",
        icon="mdi:image",
        entity_registry_enabled_default=False,
        unit_fn=lambda _: None,
        value_fn=lambda data, _: cast(int, data) or 44,
    ),
    WeatherSensorEntityDescription(
        key="snow1Hour",
        name="Snowfall - Last hour",
        icon=ICON_SNOWFLAKE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="snow6Hour",
        name="Snowfall - Last 6 hours",
        icon=ICON_SNOWFLAKE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="snow24Hour",
        name="Snowfall - Last 24 hours",
        icon=ICON_SNOWFLAKE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="validTimeUtc",
        name="Forecast Details",
        icon="mdi:cloud-clock",
        entity_registry_enabled_default=False,
        device_class=SensorDeviceClass.TIMESTAMP,
        unit_fn=lambda _: None,
        value_fn=lambda data, _: datetime.fromtimestamp(data, UTC) if isinstance(data, (int, float)) and data > 0 else None,
        attr_fn=lambda coordinator_data, selected_attributes: (
            _get_extra_attributes(
                coordinator_data,
                selected_attributes,
            )
        ),
    )
]
