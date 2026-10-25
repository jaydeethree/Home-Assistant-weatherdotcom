"""
Support for Weather.com weather service.
For more details about this platform, please refer to the documentation at
https://github.com/jaydeethree/Home-Assistant-weatherdotcom
"""

import logging
import time

from homeassistant.components.weather import (
    ATTR_FORECAST_CLOUD_COVERAGE,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_APPARENT_TEMP,
    ATTR_FORECAST_NATIVE_DEW_POINT,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_GUST_SPEED,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_UV_INDEX,
    ATTR_FORECAST_WIND_BEARING,
    ENTITY_ID_FORMAT,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
    Forecast,
    DOMAIN as WEATHER_DOMAIN
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WeatherDotComConfigEntry
from .coordinator import WeatherUpdateCoordinator
from .const import (
    ATTRIBUTION,
    FIELD_CLOUD_COVER,
    FIELD_DEW_POINT,
    FIELD_FEELS_LIKE,
    FIELD_HUMIDITY,
    FIELD_ICONCODE,
    FIELD_PRECIPCHANCE,
    FIELD_PRESSURE,
    FIELD_QPF,
    FIELD_TEMP,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_UV_INDEX,
    FIELD_VALIDTIMEUTC,
    FIELD_VISIBILITY,
    FIELD_WINDDIR,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,

    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE,
    RESULTS_FORECAST_DAILY,
    RESULTS_FORECAST_HOURLY,
)

_LOGGER = logging.getLogger(__name__)

MAX_HIGH_TEMP_AGE_SECONDS = 14 * 60 * 60


async def async_setup_entry(
        hass: HomeAssistant, entry: WeatherDotComConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add weather entity."""
    coordinator = entry.runtime_data
    async_add_entities([
        WeatherDotComForecast(coordinator),
    ])


class WeatherDotComForecast(SingleCoordinatorWeatherEntity):
    """Implementation of a Weather.com weather entity."""

    _attr_attribution = ATTRIBUTION
    # Use the device (location) name as the entity's friendly name.
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(
            self,
            coordinator: WeatherUpdateCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, f"{coordinator.location_name}", hass=coordinator.hass
        )
        self._attr_unique_id = f"{coordinator.location_name},{WEATHER_DOMAIN}".lower()
        self._attr_device_info = coordinator.device_info
        self._attr_native_temperature_unit = coordinator.units.temperature
        self._attr_native_pressure_unit = coordinator.units.pressure
        self._attr_native_wind_speed_unit = coordinator.units.speed
        self._attr_native_visibility_unit = coordinator.units.visibility
        self._attr_native_precipitation_unit = coordinator.units.precipitation
        self._store = coordinator.store

    @property
    def native_temperature(self) -> float | None:
        """
        Return the platform temperature in native units
        (i.e. not converted).
        """
        return self.coordinator.get_current(FIELD_TEMP)

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure in native units."""
        return self.coordinator.get_current(FIELD_PRESSURE)

    @property
    def humidity(self) -> float | None:
        """Return the relative humidity in native units."""
        return self.coordinator.get_current(FIELD_HUMIDITY)

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed in native units."""
        return self.coordinator.get_current(FIELD_WINDSPEED)

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the wind bearing."""
        return self.coordinator.get_current(FIELD_WINDDIR)

    @property
    def native_visibility(self) -> float | None:
        """Return the visibility in native units."""
        return self.coordinator.get_current(FIELD_VISIBILITY)

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        icon = self.coordinator.get_current(FIELD_ICONCODE)
        return self.coordinator.iconcode_to_condition(icon)

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return the 'feels like' temperature."""
        return self.coordinator.get_current(FIELD_FEELS_LIKE)

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point."""
        return self.coordinator.get_current(FIELD_DEW_POINT)

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return the wind gust speed."""
        return self.coordinator.get_current(FIELD_WINDGUST)

    @property
    def uv_index(self) -> float | None:
        """Return the UV index."""
        return self.coordinator.get_current(FIELD_UV_INDEX)

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        if not self.coordinator.data or self.coordinator.data.get(RESULTS_FORECAST_DAILY) is None:
            return []

        stored_data = await self._store.async_load()

        daily_times = self.coordinator.data[RESULTS_FORECAST_DAILY].get(FIELD_VALIDTIMEUTC) or []
        days = list(range(0, len(daily_times) * 2, 2))
        if days and self.coordinator.get_forecast_daily(FIELD_TEMP, 0) is None:
            days[0] += 1

        forecast = []
        for period in days:
            # After 15:00 local time the Weather.com API returns None for the
            # high temperature. When this happens, return the last known high
            # temperature instead of None.
            temperature_max = self.coordinator.get_forecast_daily(FIELD_TEMPERATUREMAX, period)
            if period in [0, 1] and temperature_max is None:
                # If the API returns None, attempt to use the value that's in
                # storage.
                if (
                    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE in stored_data
                    and
                    HIGH_TEMP_TODAY_STORAGE in stored_data
                    and
                    round(time.time()) - stored_data[HIGH_TEMP_TODAY_TIMESTAMP_STORAGE] < MAX_HIGH_TEMP_AGE_SECONDS
                ):
                    temperature_max = stored_data[HIGH_TEMP_TODAY_STORAGE]
                else:
                    _LOGGER.debug(
                        'Stored value for maximum temperature is old or missing'
                        ' and the API is not returning this data - maximum'
                        ' temperature data in the daily forecast will be'
                        ' missing for today for: %s', self.entity_id)

            forecast.append(Forecast({
                ATTR_FORECAST_CLOUD_COVERAGE:
                    self.coordinator.get_forecast_daily(FIELD_CLOUD_COVER, period),
                ATTR_FORECAST_CONDITION:
                    self.coordinator.iconcode_to_condition(
                        self.coordinator.get_forecast_daily(
                            FIELD_ICONCODE, period)
                    ),
                ATTR_FORECAST_HUMIDITY:
                    self.coordinator.get_forecast_daily(FIELD_HUMIDITY, period),
                ATTR_FORECAST_NATIVE_PRECIPITATION:
                    self.coordinator.get_forecast_daily(FIELD_QPF, period),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY:
                    self.coordinator.get_forecast_daily(FIELD_PRECIPCHANCE, period),

                ATTR_FORECAST_NATIVE_TEMP:
                    temperature_max,
                ATTR_FORECAST_NATIVE_TEMP_LOW:
                    self.coordinator.get_forecast_daily(
                        FIELD_TEMPERATUREMIN, period),

                ATTR_FORECAST_TIME:
                    self.coordinator.format_timestamp(
                        self.coordinator.get_forecast_daily(
                            FIELD_VALIDTIMEUTC, period)),
                ATTR_FORECAST_UV_INDEX:
                    self.coordinator.get_forecast_daily(FIELD_UV_INDEX, period),
                ATTR_FORECAST_WIND_BEARING:
                    self.coordinator.get_forecast_daily(
                        FIELD_WINDDIR, period),
                ATTR_FORECAST_NATIVE_WIND_SPEED: self.coordinator.get_forecast_daily(
                    FIELD_WINDSPEED, period)
            }))
        return forecast

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast in native units."""
        if not self.coordinator.data or self.coordinator.data.get(RESULTS_FORECAST_HOURLY) is None:
            return []

        hourly_times = self.coordinator.data[RESULTS_FORECAST_HOURLY].get(FIELD_VALIDTIMEUTC) or []
        forecast = []
        for hour in range(len(hourly_times)):
            forecast.append(Forecast({
                ATTR_FORECAST_CLOUD_COVERAGE:
                    self.coordinator.get_forecast_hourly(FIELD_CLOUD_COVER, hour),
                ATTR_FORECAST_CONDITION:
                    self.coordinator.iconcode_to_condition(
                        self.coordinator.get_forecast_hourly(
                            FIELD_ICONCODE, hour)
                    ),
                ATTR_FORECAST_HUMIDITY:
                    self.coordinator.get_forecast_hourly(FIELD_HUMIDITY, hour),
                ATTR_FORECAST_NATIVE_APPARENT_TEMP:
                    self.coordinator.get_forecast_hourly(FIELD_FEELS_LIKE, hour),
                ATTR_FORECAST_NATIVE_DEW_POINT:
                    self.coordinator.get_forecast_hourly(FIELD_DEW_POINT, hour),
                ATTR_FORECAST_NATIVE_WIND_GUST_SPEED:
                    self.coordinator.get_forecast_hourly(FIELD_WINDGUST, hour),
                ATTR_FORECAST_NATIVE_PRECIPITATION:
                    self.coordinator.get_forecast_hourly(FIELD_QPF, hour),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY:
                    self.coordinator.get_forecast_hourly(FIELD_PRECIPCHANCE, hour),
                ATTR_FORECAST_NATIVE_TEMP:
                    self.coordinator.get_forecast_hourly(FIELD_TEMP, hour),
                ATTR_FORECAST_TIME:
                    self.coordinator.format_timestamp(
                        self.coordinator.get_forecast_hourly(
                            FIELD_VALIDTIMEUTC, hour)),
                ATTR_FORECAST_UV_INDEX:
                    self.coordinator.get_forecast_hourly(FIELD_UV_INDEX, hour),
                ATTR_FORECAST_WIND_BEARING:
                    self.coordinator.get_forecast_hourly(
                        FIELD_WINDDIR, hour),
                ATTR_FORECAST_NATIVE_WIND_SPEED: self.coordinator.get_forecast_hourly(
                    FIELD_WINDSPEED, hour)
            }))
        return forecast
