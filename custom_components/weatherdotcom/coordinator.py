"""The Weather.com data coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import json
from homeassistant.util.unit_system import METRIC_SYSTEM
from homeassistant.const import (
    PERCENTAGE, UnitOfPressure, UnitOfTemperature, UnitOfLength, UnitOfSpeed, UnitOfVolumetricFlux)
from .const import (
    ICON_CONDITION_MAP,
    FIELD_DAYPART,
    FIELD_HUMIDITY,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_VALIDTIMEUTC,
    FIELD_WINDDIR,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,
    DOMAIN,
    RESULTS_CURRENT,
    RESULTS_FORECAST_DAILY,
    RESULTS_FORECAST_HOURLY
)

_LOGGER = logging.getLogger(__name__)

_RESOURCESHARED = '&format=json&apiKey={apiKey}&units={units}'
_RESOURCECURRENT = ('https://api.weather.com/v3/wx/observations/current'
                    '?geocode={latitude},{longitude}')
_RESOURCEFORECASTDAILY = ('https://api.weather.com/v3/wx/forecast/daily/10day'
                          '?geocode={latitude},{longitude}')
_RESOURCEFORECASTHOURLY = ('https://api.weather.com/v3/wx/forecast/hourly/2day'
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
    latitude: str
    longitude: str
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
        self._latitude = config.latitude
        self._longitude = config.longitude
        self.data = None
        self._session = async_get_clientsession(self._hass)
        self._tranfile = self.get_tran_file()

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

    async def _async_update_data(self) -> dict[str, Any]:
        return await self.get_weather()

    async def get_weather(self):
        """Get weather data."""
        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        try:
            with async_timeout.timeout(10):
                url = self._build_url(_RESOURCECURRENT)
                response = await self._session.get(url, headers=headers)
                result_current = await response.json(content_type=None)
                if result_current is None:
                    raise ValueError('NO CURRENT RESULT')
                self._check_errors(url, result_current)

            with async_timeout.timeout(10):
                url = self._build_url(_RESOURCEFORECASTDAILY)
                response = await self._session.get(url, headers=headers)
                result_forecast_daily = await response.json(content_type=None)

                if result_forecast_daily is None:
                    raise ValueError('NO DAILY FORECAST RESULT')
                self._check_errors(url, result_forecast_daily)

            with async_timeout.timeout(10):
                url = self._build_url(_RESOURCEFORECASTHOURLY)
                response = await self._session.get(url, headers=headers)
                result_forecast_hourly = await response.json(content_type=None)

                if result_forecast_hourly is None:
                    raise ValueError('NO HOURLY FORECAST RESULT')
                self._check_errors(url, result_forecast_hourly)

            result = {
                RESULTS_CURRENT: result_current,
                RESULTS_FORECAST_DAILY: result_forecast_daily,
                RESULTS_FORECAST_HOURLY: result_forecast_hourly,
            }

            self.data = result

            return result

        except ValueError as err:
            _LOGGER.error("Check Weather.com API %s", err.args)
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error fetching Weather.com data: %s", repr(err))
        # _LOGGER.debug(f'Weather.com data {self.data}')

    def _build_url(self, baseurl):
        baseurl += '&language={language}'
        baseurl += _RESOURCESHARED

        return baseurl.format(
            apiKey=self._api_key,
            language=self._lang,
            latitude=self._latitude,
            longitude=self._longitude,
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
        except IndexError:
            return None

    def get_forecast_hourly(self, field, hour):
        try:
            return self.data[RESULTS_FORECAST_HOURLY][field][hour]
        except IndexError:
            return None

    @classmethod
    def _iconcode_to_condition(cls, icon_code):
        for condition, iconcodes in cls.icon_condition_map.items():
            if icon_code in iconcodes:
                return condition
        _LOGGER.warning(f'Unmapped iconCode from TWC Api. (44 is Not Available (N/A)) "{icon_code}". ')
        return None

    @classmethod
    def _format_timestamp(cls, timestamp_secs):
        return datetime.utcfromtimestamp(timestamp_secs).isoformat('T') + 'Z'

    def get_tran_file(self):
        """get translation file for Weather.com sensor friendly_name"""
        tfiledir = f'{self._hass.config.config_dir}/custom_components/{DOMAIN}/weather_translations/'
        tfilename = self._lang.split('-', 1)[0]
        try:
            tfiledata = json.load_json(f'{tfiledir}{tfilename}.json')
        except Exception:  # pylint: disable=broad-except
            tfiledata = json.load_json(f'{tfiledir}en.json')
            _LOGGER.warning(f'Sensor translation file {tfilename}.json does not exist. Defaulting to en-US.')
        return tfiledata


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid api key."""
