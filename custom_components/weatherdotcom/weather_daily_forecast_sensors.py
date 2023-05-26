from __future__ import annotations

from typing import cast

from .const import FEATURE_FORECAST, FEATURE_FORECAST_DAYPART
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfSpeed, UnitOfLength, PERCENTAGE
from .weather_current_conditions_sensors import WeatherSensorEntityDescription

forecast_sensor_descriptions = [
    # forecast outside daypart
    # dayOfWeek: expirationTimeUtc: moonPhase: moonPhaseCode:
    # moonPhaseDay: moonriseTimeLocal: moonriseTimeUtc: moonsetTimeLocal: moonsetTimeUtc: *narrative: qpf: *qpfSnow:
    # sunriseTimeLocal: sunriseTimeUtc: sunsetTimeLocal: sunsetTimeUtc: temperatureMax: temperatureMin: validTimeLocal:
    # validTimeUtc:
    WeatherSensorEntityDescription(
        key="narrative",
        name="Weather Summary",
        feature=FEATURE_FORECAST,
        icon="mdi:gauge",
        value_fn=lambda data, _: cast(str, data),
        entity_registry_enabled_default=False,
    ),
    WeatherSensorEntityDescription(
        key="qpfSnow",
        name="Snow Amount",
        feature=FEATURE_FORECAST,
        icon="mdi:snowflake",
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data),
        entity_registry_enabled_default=False,
    ),

    # forecast daypart 5 day
    # cloudCover: dayOrNight: daypartName: iconCode: iconCodeExtend: *narrative: *precipChance: precipType: *qpf:
    # qpfSnow: qualifierCode: qualifierPhrase: relativeHumidity: snowRange: *temperature: temperatureHeatIndex:
    # temperatureWindChill: thunderCategory: thunderIndex: uvDescription: uvIndex: windDirection: windDirectionCardinal:
    # windPhrase: *windSpeed: wxPhraseLong: wxPhraseShort:
    WeatherSensorEntityDescription(
        key="temperature",
        name="Forecast Temperature",
        feature=FEATURE_FORECAST_DAYPART,
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data) if (data is not None) else str('—'),
        entity_registry_enabled_default=False,
    ),
    WeatherSensorEntityDescription(
        key="narrative",
        name="Forecast Summary",
        feature=FEATURE_FORECAST_DAYPART,
        icon="mdi:gauge",
        value_fn=lambda data, _: cast(str, data) if (data is not None) else str('—'),
        entity_registry_enabled_default=False,
    ),
    WeatherSensorEntityDescription(
        key="windSpeed",
        name="Average Wind",
        feature=FEATURE_FORECAST_DAYPART,
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        unit_fn=lambda metric: UnitOfSpeed.KILOMETERS_PER_HOUR if metric else UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda data, _: cast(float, data) if (data is not None) else str('—'),
        entity_registry_enabled_default=False,
    ),
    WeatherSensorEntityDescription(
        key="qpf",
        name="Precipitation Amount",
        feature=FEATURE_FORECAST_DAYPART,
        icon="mdi:umbrella",
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data) if (data is not None) else str('—'),
        entity_registry_enabled_default=False,
    ),
    WeatherSensorEntityDescription(
        key="precipChance",
        name="Precipitation Probability",
        feature=FEATURE_FORECAST_DAYPART,
        icon="mdi:umbrella",
        unit_fn=lambda _: PERCENTAGE,
        value_fn=lambda data, _: cast(float, data) if (data is not None) else str('—'),
        entity_registry_enabled_default=False,
    ),
]
