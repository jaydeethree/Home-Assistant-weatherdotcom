"""The Weather.com data coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import time
from typing import Any

import aiohttp
import async_timeout
import math
import random

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.unit_system import METRIC_SYSTEM
from homeassistant.const import (
    PERCENTAGE, UnitOfPressure, UnitOfTemperature, UnitOfLength, UnitOfSpeed, UnitOfVolumetricFlux)
from .const import (
    DOMAIN,
    ICON_CONDITION_MAP,
    FIELD_DAYPART,
    FIELD_HUMIDITY,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_VALIDTIMEUTC,
    FIELD_WINDDIR,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,
    RESULTS_CURRENT,
    RESULTS_FORECAST_DAILY,
    RESULTS_FORECAST_HOURLY
)
from .store import WeatherDotComStorage

_LOGGER = logging.getLogger(__name__)

_RESOURCESHARED = '&format=json&apiKey={apiKey}&units={units}'
_RESOURCECURRENT = ('https://api.weather.com/v3/wx/observations/current'
                    '?geocode={latitude},{longitude}')
_RESOURCEFORECASTDAILY = ('https://api.weather.com/v3/wx/forecast/daily/15day'
                          '?geocode={latitude},{longitude}')
_RESOURCEFORECASTHOURLY = ('https://api.weather.com/v3/wx/forecast/hourly/15day'
                           '?geocode={latitude},{longitude}')

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=20)


@dataclass
class WeatherUpdateCoordinatorConfig:
    """Class representing coordinator configuration."""

    api_key: str
    location_name: str
    unit_system_api: str
    unit_system: str
    lang: str
    tranfile: str
    location_entity_id: str | None = None
    # For legacy services that have not migrated
    latitude: str | None = None
    longitude: str | None = None

    update_interval = MIN_TIME_BETWEEN_UPDATES


class WeatherUpdateCoordinator(DataUpdateCoordinator):
    """The Weather.com update coordinator."""

    icon_condition_map = ICON_CONDITION_MAP

    def __init__(
            self, hass: HomeAssistant, config: WeatherUpdateCoordinatorConfig
    ) -> None:
        """Initialize."""
        self._hass = hass
        self._api_key = config.api_key
        self._location_name = config.location_name
        self._unit_system_api = config.unit_system_api
        self.unit_system = config.unit_system
        self._lang = config.lang
        self.data = None
        self._session = async_get_clientsession(self._hass)
        self._tranfile = config.tranfile
        self._store = WeatherDotComStorage(self._hass, self._location_name)

        self._location_entity_id = config.location_entity_id
        # For legacy services that have not migrated
        self._latitude = config.latitude
        self._longitude = config.longitude

        self.device_info = _get_device_info(self._location_name)

        if self._unit_system_api == 'm':
            self.units_of_measurement = (UnitOfTemperature.CELSIUS, UnitOfLength.MILLIMETERS, UnitOfLength.METERS,
                                         UnitOfSpeed.KILOMETERS_PER_HOUR, UnitOfPressure.MBAR,
                                         UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR, PERCENTAGE)
            self.visibility_unit = UnitOfLength.KILOMETERS
        else:
            self.units_of_measurement = (UnitOfTemperature.FAHRENHEIT, UnitOfLength.INCHES, UnitOfLength.FEET,
                                         UnitOfSpeed.MILES_PER_HOUR, UnitOfPressure.INHG,
                                         UnitOfVolumetricFlux.INCHES_PER_HOUR, PERCENTAGE)
            self.visibility_unit = UnitOfLength.MILES

        super().__init__(
            hass,
            _LOGGER,
            name="WeatherUpdateCoordinator",
            update_interval=config.update_interval,
        )

    @property
    def is_metric(self):
        """Determine if this is the metric unit system."""
        return self._hass.config.units is METRIC_SYSTEM

    @property
    def location_name(self):
        """Return the location used for data."""
        return self._location_name

    def _get_coordinates(self) -> tuple[float | None, float | None]:
        """Fetch current latitude and longitude and apply hardcoded obfuscation."""
        lat, lon = None, None

        # New configuration attempt
        if self._location_entity_id and (state := self._hass.states.get(self._location_entity_id)):
            raw_lat = state.attributes.get("latitude")
            raw_lon = state.attributes.get("longitude")
            if raw_lat is not None and raw_lon is not None:
                lat, lon = float(raw_lat), float(raw_lon)

        # Fallback to legacy config if entity is missing
        if lat is None or lon is None:
            if self._latitude is not None and self._longitude is not None:
                lat, lon = float(self._latitude), float(self._longitude)
            else:
                _LOGGER.error("Could not determine latitude/longitude from entity or prior config")
                return None, None

        # Universally apply offset
        obf_lat, obf_lon = self._apply_random_offset(lat, lon)
        
        _LOGGER.debug(
            "Location entity '%s': original=(%s, %s), obfuscated=(%s, %s)",
            self._location_entity_id, lat, lon, obf_lat, obf_lon
        )
        
        return obf_lat, obf_lon

    @staticmethod
    def _apply_random_offset(lat: float, lon: float) -> tuple[float, float]:
        """Apply a random offset between a maxium and minimum radius"""
        max_radius_m = 1000
        min_radius_m = 600
        # Create a unique and permanent seed for the integration (multiple services will use same seed)
        seed_string = f"{lat}_{lon}_{max_radius_m}_weather_secret"
        rng = random.Random(seed_string)

        # Calculate distance
        distance = rng.uniform(min_radius_m, max_radius_m)

        # Calculate direction
        angle = rng.uniform(0, 2 * math.pi)

        # Calculate X and Y offsets
        dx = distance * math.cos(angle)
        dy = distance * math.sin(angle)

        # Convert to decimal degrees
        delta_lat = dy / 111111.0
        delta_lon = dx / (111111.0 * math.cos(math.radians(lat)))

        return round(lat + delta_lat, 6), round(lon + delta_lon, 6)

    async def _async_update_data(self) -> dict[str, Any]:
        return await self.get_weather()

    async def get_weather(self):
        """Get weather data."""
        latitude, longitude = self._get_coordinates()
        if latitude is None or longitude is None:
            raise UpdateFailed(f"Could not retrieve location coordinates {self._location_entity_id}")

        self.current_latitude = latitude
        self.current_longitude = longitude

        # Debug log
        _LOGGER.debug(
            "Weather.com API coordinates: latitude=%s, longitude=%s",
            latitude,
            longitude,
        )

        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        current_error = False
        daily_error = False
        hourly_error = False
        result_current = None
        result_forecast_daily = None
        result_forecast_hourly = None

        for attempt in range(2):
            try:
                async with async_timeout.timeout(10):
                    url = self._build_url(_RESOURCECURRENT, latitude, longitude)
                    response = await self._session.get(url, headers=headers)
                    result_current = await response.json(content_type=None)
                    if result_current is None:
                        raise ValueError('No weather data found')
                    self._check_errors(url, result_current)
                    break
            except (ValueError, asyncio.TimeoutError, aiohttp.ClientError) as err:
                if attempt == 1:
                    _LOGGER.error('Error getting current weather. Exception: %s. Details: %s', type(err), err)
                    current_error = True
                else:
                    _LOGGER.warning('Error getting current weather, will retry. Exception: %s. Details: %s', type(err), err)
                    await asyncio.sleep(5)

        for attempt in range(2):
            try:
                async with async_timeout.timeout(10):
                    url = self._build_url(_RESOURCEFORECASTDAILY, latitude, longitude)
                    response = await self._session.get(url, headers=headers)
                    result_forecast_daily = await response.json(content_type=None)
                    if result_forecast_daily is None:
                        raise ValueError('No weather data found')
                    self._check_errors(url, result_forecast_daily)
                    # If the result includes max temperature data for today,
                    # update that data in storage.
                    temperature_max = result_forecast_daily[FIELD_TEMPERATUREMAX][0]
                    if temperature_max is not None:
                        await self._store.async_save(temperature_max, round(time.time()))
                    break
            except (ValueError, asyncio.TimeoutError, aiohttp.ClientError) as err:
                if attempt == 1:
                    _LOGGER.error('Error getting daily weather. Exception: %s. Details: %s', type(err), err)
                    daily_error = True
                else:
                    _LOGGER.warning('Error getting daily weather, will retry. Exception: %s. Details: %s', type(err), err)
                    await asyncio.sleep(5)

        for attempt in range(2):
            try:
                async with async_timeout.timeout(10):
                    url = self._build_url(_RESOURCEFORECASTHOURLY, latitude, longitude)
                    response = await self._session.get(url, headers=headers)
                    result_forecast_hourly = await response.json(content_type=None)
                    if result_forecast_hourly is None:
                        raise ValueError('No weather data found')
                    self._check_errors(url, result_forecast_hourly)
                    break
            except (ValueError, asyncio.TimeoutError, aiohttp.ClientError) as err:
                if attempt == 1:
                    _LOGGER.error('Error getting hourly weather. Exception: %s. Details: %s', type(err), err)
                    hourly_error = True
                else:
                    _LOGGER.warning('Error getting hourly weather, will retry. Exception: %s. Details: %s', type(err), err)
                    await asyncio.sleep(5)

        if current_error and daily_error and hourly_error:
            raise UpdateFailed('Failed to get weather data')
        else:
            result = {
                RESULTS_CURRENT: result_current,
                RESULTS_FORECAST_DAILY: result_forecast_daily,
                RESULTS_FORECAST_HOURLY: result_forecast_hourly,
            }
            self.data = result
            return result

    def _build_url(self, baseurl: str, latitude: float, longitude: float) -> str:
        baseurl += '&language={language}'
        baseurl += _RESOURCESHARED

        return baseurl.format(
            apiKey=self._api_key,
            language=self._lang,
            latitude=latitude,
            longitude=longitude,
            units=self._unit_system_api
        )

    def _check_errors(self, url: str, response: dict):
        # _LOGGER.debug(f'Checking errors from {url} in {response}')
        if 'errors' not in response:
            return
        if errors := response['errors']:
            raise ValueError(
                f'Error from {url}: '
                '; '.join([
                    e['message']
                    for e in errors
                ])
            )

    def get_current(self, field):
        if self.data[RESULTS_CURRENT] is None:
            return None
        return self.data[RESULTS_CURRENT][field]

    def get_forecast_daily(self, field, period=0):
        try:
            if field in [
                FIELD_TEMPERATUREMAX,
                FIELD_TEMPERATUREMIN,
                FIELD_VALIDTIMEUTC,
            ]:
                # Those fields exist per-day, rather than per dayPart, so the period is halved
                return self.data[RESULTS_FORECAST_DAILY][field][int(period / 2)]
            return self.data[RESULTS_FORECAST_DAILY][FIELD_DAYPART][0][field][period]
        except (IndexError, TypeError):
            return None

    def get_forecast_hourly(self, field, hour):
        try:
            return self.data[RESULTS_FORECAST_HOURLY][field][hour]
        except (IndexError, TypeError):
            return None

    @classmethod
    def _iconcode_to_condition(cls, icon_code):
        for condition, iconcodes in cls.icon_condition_map.items():
            if icon_code in iconcodes:
                return condition
        if icon_code is not None:
            _LOGGER.warning(f'Unmapped icon code from Weather.com API: {icon_code}')
        return None

    @classmethod
    def _format_timestamp(cls, timestamp_secs):
        return datetime.utcfromtimestamp(timestamp_secs).isoformat('T') + 'Z'


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid api key."""


def _get_device_info(name: str) -> DeviceInfo:
    """Get device info."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, name)},
        manufacturer="Weather.com",
        name=name,
    )