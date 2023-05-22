from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any, cast

from .const import FEATURE_OBSERVATIONS, FEATURE_CONDITIONS
from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfIrradiance, UV_INDEX, DEGREE, UnitOfLength, UnitOfTemperature, \
    UnitOfVolumetricFlux, UnitOfPressure, UnitOfSpeed
from homeassistant.helpers.typing import StateType


@dataclass
class WeatherRequiredKeysMixin:
    """Mixin for required keys."""
    value_fn: Callable[[dict[str, Any], str], StateType]
    feature: str


@dataclass
class WeatherSensorEntityDescription(
    SensorEntityDescription, WeatherRequiredKeysMixin
):
    attr_fn: Callable[[dict[str, Any]], dict[str, StateType]] = lambda _: {}
    unit_fn: Callable[[bool], str | None] = lambda _: None
    """Describes Weather.com Sensor entity."""


def degrees_to_cardinal(d):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    ix = round(d / (360. / len(dirs)))
    return dirs[ix % len(dirs)]


obs_sensor_descriptions = [
    # observations
    # 'obsTimeUtc': *'validTimeLocal': 'softwareType': 'country': 'lon':
    # 'realtimeFrequency': 'epoch': 'lat': *'uvIndex': *'windDirection': '*relativeHumidity': 'qcStatus':
    WeatherSensorEntityDescription(
        key="validTimeLocal",
        name="Local Observation Time",
        feature=FEATURE_OBSERVATIONS,
        icon="mdi:clock",
        value_fn=lambda data, _: cast(str, data),
        # value_fn=lambda data, _: cast(str, datetime.strptime(data,  '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y %H:%M:%S')),
    ),
    WeatherSensorEntityDescription(
        key="relativeHumidity",
        name="Relative Humidity",
        feature=FEATURE_OBSERVATIONS,
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _: PERCENTAGE,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="uvIndex",
        name="UV Index",
        feature=FEATURE_OBSERVATIONS,
        icon="mdi:sunglasses",
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _: UV_INDEX,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    WeatherSensorEntityDescription(
        key="windDirection",
        name="Wind Direction - Degrees",
        feature=FEATURE_OBSERVATIONS,
        icon="mdi:weather-windy",
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _: DEGREE,
        value_fn=lambda data, _: cast(int, data) or 0,
    ),
    # computed observations
    WeatherSensorEntityDescription(
        key="windDirectionCardinal",
        name="Wind Direction - Cardinal",
        feature="",
        icon="mdi:weather-windy",
        unit_fn=lambda _: None,
        value_fn=lambda data, _: degrees_to_cardinal(cast(int, data['windDirection'])) or "",
    ),
    # conditions -> unit imperial/metric
    # temperature: temperatureHeatIndex: temperatureDewPoint: temperatureWindChill: windSpeed: windGust: pressureAltimeter: precip1Hour: precip24Hour:
    WeatherSensorEntityDescription(
        key="temperatureDewPoint",
        name="Dewpoint",
        feature=FEATURE_CONDITIONS,
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="temperature",
        name="Temperature",
        feature=FEATURE_CONDITIONS,
        icon="mdi:thermometer",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="temperatureHeatIndex",
        name="Heat Index",
        feature=FEATURE_CONDITIONS,
        icon="mdi:thermometer",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="temperatureWindChill",
        name="Wind Chill",
        feature=FEATURE_CONDITIONS,
        icon="mdi:thermometer",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_fn=lambda metric: UnitOfTemperature.CELSIUS if metric else UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="precip1Hour",
        name="Precipitation Rate",
        feature=FEATURE_CONDITIONS,
        icon="mdi:umbrella",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        unit_fn=lambda
            metric: UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR if metric else UnitOfVolumetricFlux.INCHES_PER_HOUR,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="precip24Hour",
        name="Precipitation Today",
        feature=FEATURE_CONDITIONS,
        icon="mdi:umbrella",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.PRECIPITATION,
        unit_fn=lambda metric: UnitOfLength.MILLIMETERS if metric else UnitOfLength.INCHES,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="pressureAltimeter",
        name="Pressure",
        feature=FEATURE_CONDITIONS,
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRESSURE,
        unit_fn=lambda metric: UnitOfPressure.MBAR if metric else UnitOfPressure.INHG,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="windGust",
        name="Wind Gust",
        feature=FEATURE_CONDITIONS,
        icon="mdi:weather-windy",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.WIND_SPEED,
        unit_fn=lambda metric: UnitOfSpeed.KILOMETERS_PER_HOUR if metric else UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda data, _: cast(float, data),
    ),
    WeatherSensorEntityDescription(
        key="windSpeed",
        name="Wind Speed",
        feature=FEATURE_CONDITIONS,
        icon="mdi:weather-windy",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.WIND_SPEED,
        unit_fn=lambda metric: UnitOfSpeed.KILOMETERS_PER_HOUR if metric else UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda data, _: cast(float, data),
    ),
]
