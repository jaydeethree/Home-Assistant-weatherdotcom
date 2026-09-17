from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any, cast
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


def _get_extra_attributes(
    coordinator_data: dict[str, Any],
    selected_attributes: list[str] | None = None,
) -> dict[str, Any]:
    daily_data = coordinator_data.get("daily", {})

    dayparts = daily_data.get("daypart", [{}])
    daypart_data = dayparts[0] if dayparts else {}

    # Define base daypart arrays
    daypart_icon_code = daypart_data.get("iconCode", [0] * 30)
    daypart_cloud_cover = daypart_data.get("cloudCover", [0] * 30)
    daypart_relative_humidity = daypart_data.get("relativeHumidity", [0] * 30)

    # Synthetic daily attributes lists to append into
    day_icon = []
    day_cloud_cover = []
    day_relative_humidity = []

    if daypart_icon_code[0] is None:
        # Nighttime pull: replace missing index 0 with index 1
        # Weather.com API workaround
        day_icon.append(daypart_icon_code[1])
        day_cloud_cover.append(
            daypart_cloud_cover[1] if daypart_cloud_cover[1] is not None else 0
        )
        day_relative_humidity.append(
            daypart_relative_humidity[1] if daypart_relative_humidity[1] is not None else 0
        )
        # Then use even indices for the remaining 14 days
        for i in range(2, 29, 2):
            day_icon.append(daypart_icon_code[i])
            day_cloud_cover.append(
                daypart_cloud_cover[i] if daypart_cloud_cover[i] is not None else 0
            )
            day_relative_humidity.append(
                daypart_relative_humidity[i] if daypart_relative_humidity[i] is not None else 0
            )
    else:
        # Daytime pull: use even indices from 0 through 28
        for i in range(0, 29, 2):
            day_icon.append(daypart_icon_code[i])
            day_cloud_cover.append(
                daypart_cloud_cover[i] if daypart_cloud_cover[i] is not None else 0
            )
            day_relative_humidity.append(
                daypart_relative_humidity[i] if daypart_relative_humidity[i] is not None else 0
            )

    daily_attributes = {
        "day": daily_data.get("dayOfWeek", [0] * 15),
        "daily_temp_max": daily_data.get("calendarDayTemperatureMax", [0] * 15),
        "daily_temp_min": daily_data.get("calendarDayTemperatureMin", [0] * 15),
        "daily_precip_qpf": daily_data.get("qpf", [0] * 15),
        "daily_rain_qpf": daily_data.get("qpfRain", [0] * 15),
        "daily_snow_qpf": daily_data.get("qpfSnow", [0] * 15),
        "daily_ice_qpf": daily_data.get("qpfIce", [0] * 15),
        "sunrise": daily_data.get("sunriseTimeLocal", [0] * 15),
        "sunset": daily_data.get("sunsetTimeLocal", [0] * 15),
        "moon_phase": daily_data.get("moonPhase", [0] * 15),
        "moon_phase_code": daily_data.get("moonPhaseCode", [0] * 15),
        "moon_phase_day": daily_data.get("moonPhaseDay", [0] * 15),
        "moonrise": daily_data.get("moonriseTimeLocal", [0] * 15),
        "moonset": daily_data.get("moonsetTimeLocal", [0] * 15),
        "daily_narrative": daily_data.get("narrative", [0] * 15),
    }

    day_attributes = {
        "day_icon_code": day_icon,
        "day_cloud_cover": day_cloud_cover,
        "day_relative_humidity": day_relative_humidity,
    }

    daypart_attributes = {
        "daypart_cloud_cover": daypart_cloud_cover,
        "daypart_name": daypart_data.get(
            "daypartName", [0] * 30
        ),
        "daypart_icon_code": daypart_icon_code,
        "daypart_precip_chance": daypart_data.get(
            "precipChance", [0] * 30
        ),
        "daypart_precip_type": daypart_data.get(
            "precipType", [0] * 30
        ),
        "daypart_total_qpf": daypart_data.get(
            "qpf", [0] * 30
        ),
        "daypart_rain_qpf": daypart_data.get(
            "qpfRain", [0] * 30
        ),
        "daypart_snow_qpf": daypart_data.get(
            "qpfSnow", [0] * 30
        ),
        "daypart_ice_qpf": daypart_data.get(
            "qpfIce", [0] * 30
        ),
        "daypart_snow_range": daypart_data.get(
            "snowRange", [0] * 30
        ),
        "daypart_relative_humidity": daypart_relative_humidity,
        "daypart_heat_index": daypart_data.get(
            "temperatureHeatIndex", [0] * 30
        ),
        "daypart_wind_chill": daypart_data.get(
            "temperatureWindChill", [0] * 30
        ),
        "daypart_thunder_category": daypart_data.get(
            "thunderCategory", [0] * 30
        ),
        "daypart_thunder_index": daypart_data.get(
            "thunderIndex", [0] * 30
        ),
        "daypart_uv_description": daypart_data.get(
            "uvDescription", [0] * 30
        ),
        "daypart_uv_index": daypart_data.get(
            "uvIndex", [0] * 30
        ),
        "daypart_wind_dir": daypart_data.get(
            "windDirection", [0] * 30
        ),
        "daypart_wind_dir_cardinal": daypart_data.get(
            "windDirectionCardinal", [0] * 30
        ),
        "daypart_wind_speed": daypart_data.get(
            "windSpeed", [0] * 30
        ),
        "daypart_wind_phrase": daypart_data.get(
            "windPhrase", [0] * 30
        ),
        "daypart_wx_phrase_long": daypart_data.get(
            "wxPhraseLong", [0] * 30
        ),
        "daypart_wx_phrase_short": daypart_data.get(
            "wxPhraseShort", [0] * 30
        ),
        "daypart_qualifier_phrase": daypart_data.get(
            "qualifierPhrase", [0] * 30
        ),
        "daypart_narrative": daypart_data.get(
            "narrative", [0] * 30
        ),
    }

    attributes = {
        **daily_attributes,
        **day_attributes,
        **daypart_attributes,
    }

    if not selected_attributes:
        return {}

    return {
        key: attributes[key]
        for key in selected_attributes
        if key in attributes
    }


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
        dict[str, StateType],
    ] = lambda _, __: {}
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
        value_fn=lambda data, _: datetime.fromtimestamp(data, UTC),
        attr_fn=lambda coordinator_data, selected_attributes: (
            _get_extra_attributes(
                coordinator_data,
                selected_attributes,
            )
        ),
    )
]
