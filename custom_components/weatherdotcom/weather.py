"""
Support for Weather.com weather service.
For more details about this platform, please refer to the documentation at
https://github.com/jaydeethree/Home-Assistant-weatherdotcom
"""

from . import WeatherUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from .const import (
    DOMAIN,

    TEMPUNIT,
    LENGTHUNIT,
    SPEEDUNIT,
    PRESSUREUNIT,

    FIELD_CLOUD_COVER,
    FIELD_HUMIDITY,
    FIELD_ICONCODE,
    FIELD_PRECIPCHANCE,
    FIELD_PRESSURE,
    FIELD_QPF,
    FIELD_TEMP,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_VALIDTIMEUTC,
    FIELD_VISIBILITY,
    FIELD_WINDDIR,
    FIELD_WINDDIRECTIONCARDINAL,
    FIELD_WINDSPEED
)

import logging

from homeassistant.components.weather import (
    ATTR_FORECAST_CLOUD_COVERAGE,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
    Forecast,
    DOMAIN as WEATHER_DOMAIN
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_FORMAT = WEATHER_DOMAIN + ".{}"


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add weather entity."""
    coordinator: WeatherUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WeatherDotComForecast(coordinator),
    ])


class WeatherDotCom(SingleCoordinatorWeatherEntity):

    @property
    def native_temperature(self) -> float:
        """
        Return the platform temperature in native units
        (i.e. not converted).
        """
        return self.coordinator.get_current(FIELD_TEMP)

    @property
    def native_temperature_unit(self) -> str:
        """Return the native unit of measurement for temperature."""
        return self.coordinator.units_of_measurement[TEMPUNIT]

    @property
    def native_pressure(self) -> float:
        """Return the pressure in native units."""
        return self.coordinator.get_current(FIELD_PRESSURE)

    @property
    def native_pressure_unit(self) -> str:
        """Return the native unit of measurement for pressure."""
        return self.coordinator.units_of_measurement[PRESSUREUNIT]

    @property
    def humidity(self) -> float:
        """Return the relative humidity in native units."""
        return self.coordinator.get_current(FIELD_HUMIDITY)

    @property
    def native_wind_speed(self) -> float:
        """Return the wind speed in native units."""
        return self.coordinator.get_current(FIELD_WINDSPEED)

    @property
    def native_wind_speed_unit(self) -> str:
        """Return the native unit of measurement for wind speed."""
        return self.coordinator.units_of_measurement[SPEEDUNIT]

    @property
    def wind_bearing(self) -> str:
        """Return the wind bearing."""
        return self.coordinator.get_current(FIELD_WINDDIR)

    @property
    def native_visibility(self) -> float:
        """Return the visibility in native units."""
        return self.coordinator.get_current(FIELD_VISIBILITY)

    @property
    def native_visibility_unit(self) -> str:
        """Return the native unit of measurement for visibility."""
        return self.coordinator.visibility_unit

    @property
    def native_precipitation_unit(self) -> str:
        """
        Return the native unit of measurement for accumulated precipitation.
        """
        return self.coordinator.units_of_measurement[LENGTHUNIT]

    @property
    def condition(self) -> str:
        """Return the current condition."""
        icon = self.coordinator.get_current(FIELD_ICONCODE)
        return self.coordinator._iconcode_to_condition(icon)


class WeatherDotComForecast(WeatherDotCom):

    def __init__(
            self,
            coordinator: WeatherUpdateCoordinator
    ):
        super().__init__(coordinator)
        """Initialize the sensor."""
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, f"{coordinator.location_name}", hass=coordinator.hass
        )
        self._attr_unique_id = f"{coordinator.location_name},{WEATHER_DOMAIN}".lower()

    @property
    def supported_features(self) -> WeatherEntityFeature:
        return (WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY)

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return self.forecast_daily

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return self.forecast_hourly

    @property
    def forecast_daily(self) -> list[Forecast]:
        """Return the daily forecast in native units."""
        days = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        if self.coordinator.get_forecast_daily('temperature', 0) is None:
            days[0] += 1
        caldaytempmax = FIELD_TEMPERATUREMAX
        caldaytempmin = FIELD_TEMPERATUREMIN

        forecast = []
        for period in days:
            forecast.append(Forecast({
                ATTR_FORECAST_CLOUD_COVERAGE:
                    self.coordinator.get_forecast_daily(FIELD_CLOUD_COVER, period),
                ATTR_FORECAST_CONDITION:
                    self.coordinator._iconcode_to_condition(
                        self.coordinator.get_forecast_daily(
                            FIELD_ICONCODE, period)
                    ),
                ATTR_FORECAST_PRECIPITATION:
                    self.coordinator.get_forecast_daily(FIELD_QPF, period),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY:
                    self.coordinator.get_forecast_daily(FIELD_PRECIPCHANCE, period),

                ATTR_FORECAST_TEMP:
                    self.coordinator.get_forecast_daily(caldaytempmax, period),
                ATTR_FORECAST_TEMP_LOW:
                    self.coordinator.get_forecast_daily(
                        caldaytempmin, period),

                ATTR_FORECAST_TIME:
                    self.coordinator._format_timestamp(
                        self.coordinator.get_forecast_daily(
                            FIELD_VALIDTIMEUTC, period)),

                ATTR_FORECAST_WIND_BEARING:
                    self.coordinator.get_forecast_daily(
                        FIELD_WINDDIRECTIONCARDINAL, period),
                ATTR_FORECAST_WIND_SPEED: self.coordinator.get_forecast_daily(
                    FIELD_WINDSPEED, period)
            }))
        return forecast

    @property
    def forecast_hourly(self) -> list[Forecast]:
        """Return the hourly forecast in native units."""

        forecast = []
        for hour in range(0, 48, 1):
            forecast.append(Forecast({
                ATTR_FORECAST_CLOUD_COVERAGE:
                    self.coordinator.get_forecast_daily(FIELD_CLOUD_COVER, hour),
                ATTR_FORECAST_CONDITION:
                    self.coordinator._iconcode_to_condition(
                        self.coordinator.get_forecast_hourly(
                            FIELD_ICONCODE, hour)
                    ),
                ATTR_FORECAST_PRECIPITATION:
                    self.coordinator.get_forecast_hourly(FIELD_QPF, hour),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY:
                    self.coordinator.get_forecast_hourly(FIELD_PRECIPCHANCE, hour),
                ATTR_FORECAST_TEMP:
                    self.coordinator.get_forecast_hourly(FIELD_TEMP, hour),
                ATTR_FORECAST_TIME:
                    self.coordinator._format_timestamp(
                        self.coordinator.get_forecast_hourly(
                            FIELD_VALIDTIMEUTC, hour)),
                ATTR_FORECAST_WIND_BEARING:
                    self.coordinator.get_forecast_hourly(
                        FIELD_WINDDIRECTIONCARDINAL, hour),
                ATTR_FORECAST_WIND_SPEED: self.coordinator.get_forecast_hourly(
                    FIELD_WINDSPEED, hour)
            }))
        return forecast
