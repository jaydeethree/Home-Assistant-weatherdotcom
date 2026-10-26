"""The Weather.com data coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
import time
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfLength,
    UnitOfSpeed,
)
from .const import (
    API_URL_METRIC,
    DOMAIN,
    HEADERS,
    ICON_CODE_MAP,
    FIELD_DAYPART,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_VALIDTIMEUTC,
    RESULTS_CURRENT,
    RESULTS_FORECAST_DAILY,
    RESULTS_FORECAST_HOURLY
)
from .store import WeatherDotComStorage

_LOGGER = logging.getLogger(__name__)

_RESOURCECURRENT = 'https://api.weather.com/v3/wx/observations/current'
_RESOURCEFORECASTDAILY = 'https://api.weather.com/v3/wx/forecast/daily/15day'
_RESOURCEFORECASTHOURLY = 'https://api.weather.com/v3/wx/forecast/hourly/15day'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=20)
MAX_CONSECUTIVE_FAILURES = 3


@dataclass(frozen=True, kw_only=True)
class WeatherUnits:
    """Units of measurement for a unit system."""

    temperature: str
    precipitation: str
    snow: str
    distance: str
    speed: str
    pressure: str
    visibility: str


METRIC_UNITS = WeatherUnits(
    temperature=UnitOfTemperature.CELSIUS,
    precipitation=UnitOfLength.MILLIMETERS,
    snow=UnitOfLength.CENTIMETERS,
    distance=UnitOfLength.METERS,
    speed=UnitOfSpeed.KILOMETERS_PER_HOUR,
    pressure=UnitOfPressure.MBAR,
    visibility=UnitOfLength.KILOMETERS,
)
IMPERIAL_UNITS = WeatherUnits(
    temperature=UnitOfTemperature.FAHRENHEIT,
    precipitation=UnitOfLength.INCHES,
    snow=UnitOfLength.INCHES,
    distance=UnitOfLength.FEET,
    speed=UnitOfSpeed.MILES_PER_HOUR,
    pressure=UnitOfPressure.INHG,
    visibility=UnitOfLength.MILES,
)


@dataclass
class WeatherUpdateCoordinatorConfig:
    """Class representing coordinator configuration."""

    api_key: str
    location_name: str
    unit_system_api: str
    lang: str
    tranfile: dict[str, Any]

    update_interval: timedelta = MIN_TIME_BETWEEN_UPDATES
    location_entity_id: str | None = None
    # For legacy services that have not migrated
    latitude: float | None = None
    longitude: float | None = None

class WeatherUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """The Weather.com update coordinator."""

    def __init__(
            self,
            hass: HomeAssistant,
            config: WeatherUpdateCoordinatorConfig,
            entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self._api_key = config.api_key
        self._location_name = config.location_name
        self._unit_system_api = config.unit_system_api
        self._lang = config.lang
        self._consecutive_failures: dict[str, int] = {
            RESULTS_CURRENT: 0,
            RESULTS_FORECAST_DAILY: 0,
            RESULTS_FORECAST_HOURLY: 0,
        }
        self._session = async_get_clientsession(hass)
        self.tranfile = config.tranfile
        self.store = WeatherDotComStorage(hass, self._location_name)

        self._location_entity_id = config.location_entity_id
        self._latitude = config.latitude
        self._longitude = config.longitude
        self.current_latitude: float | None = config.latitude
        self.current_longitude: float | None = config.longitude

        self.device_info = _get_device_info(self._location_name)
        self.units = (
            METRIC_UNITS if self._unit_system_api == API_URL_METRIC else IMPERIAL_UNITS
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} ({self._location_name})",
            update_interval=config.update_interval,
        )

    @property
    def location_name(self) -> str:
        """Return the location used for data."""
        return self._location_name

    def _get_coordinates(self) -> tuple[float | None, float | None]:
        """Fetch current latitude and longitude and obfuscate if needed."""
        # New configuration attempt
        if self._location_entity_id and (state := self.hass.states.get(self._location_entity_id)):
            raw_lat = state.attributes.get(CONF_LATITUDE)
            raw_long = state.attributes.get(CONF_LONGITUDE)
            if raw_lat is not None and raw_long is not None:
                try:
                    return round(float(raw_lat), 2), round(float(raw_long), 2)
                except (TypeError, ValueError):
                    pass

        # Fallback to legacy config or last known coordinates if entity is missing
        if self._latitude is not None and self._longitude is not None:
            return float(self._latitude), float(self._longitude)
        if self.current_latitude is not None and self.current_longitude is not None:
            _LOGGER.warning(
                "Could not determine latitude/longitude from %s; using last known coordinates",
                self._location_entity_id,
            )
            return self.current_latitude, self.current_longitude

        _LOGGER.error("Could not determine latitude/longitude from entity or prior config")
        return None, None

    async def _async_update_data(self) -> dict[str, Any]:
        return await self.get_weather()

    async def get_weather(self) -> dict[str, Any]:
        """Get weather data."""
        latitude, longitude = self._get_coordinates()
        if latitude is None or longitude is None:
            raise UpdateFailed(f"Could not retrieve location coordinates {self._location_entity_id}")

        self.current_latitude = latitude
        self.current_longitude = longitude

        (
            (result_current, current_error),
            (result_forecast_daily, daily_error),
            (result_forecast_hourly, hourly_error),
        ) = await asyncio.gather(
            self._async_fetch_data(
                _RESOURCECURRENT, latitude, longitude, "current"
            ),
            self._async_fetch_data(
                _RESOURCEFORECASTDAILY, latitude, longitude, "daily"
            ),
            self._async_fetch_data(
                _RESOURCEFORECASTHOURLY, latitude, longitude, "hourly"
            ),
        )
        if result_forecast_daily is not None:
            # If the result includes max temperature data for today,
            # update that data in storage.
            temp_max_list = result_forecast_daily.get(FIELD_TEMPERATUREMAX)
            if temp_max_list and temp_max_list[0] is not None:
                try:
                    await self.store.async_save(temp_max_list[0], round(time.time()))
                except OSError as err:
                    _LOGGER.warning(
                        "Failed to save high temperature to storage: %s", err
                    )

        prev_data = self.data or {}
        results: dict[str, Any] = {}
        for key, result, has_error in (
            (RESULTS_CURRENT, result_current, current_error),
            (RESULTS_FORECAST_DAILY, result_forecast_daily, daily_error),
            (RESULTS_FORECAST_HOURLY, result_forecast_hourly, hourly_error),
        ):
            if has_error:
                self._consecutive_failures[key] += 1
                results[key] = (
                    prev_data.get(key)
                    if self._consecutive_failures[key] < MAX_CONSECUTIVE_FAILURES
                    else None
                )
            else:
                self._consecutive_failures[key] = 0
                results[key] = result

        if current_error and daily_error and hourly_error:
            min_failures = min(self._consecutive_failures.values())
            if min_failures >= MAX_CONSECUTIVE_FAILURES or self.data is None:
                raise UpdateFailed('Failed to get weather data')
            _LOGGER.warning(
                'Failed to get weather data (failure %s of %s); retaining previous data',
                min_failures,
                MAX_CONSECUTIVE_FAILURES,
            )

        return results

    async def _async_fetch_data(
        self, resource: str, latitude: float, longitude: float, description: str
    ) -> tuple[dict[str, Any] | None, bool]:
        """Fetch weather data for a specific resource with retry."""
        params = {
            "geocode": f"{latitude},{longitude}",
            "language": self._lang,
            "format": "json",
            "apiKey": self._api_key,
            "units": self._unit_system_api,
        }
        for attempt in range(2):
            try:
                async with asyncio.timeout(10):
                    async with self._session.get(resource, params=params, headers=HEADERS) as response:
                        response.raise_for_status()
                        result = await response.json(content_type=None)
                    if not isinstance(result, dict):
                        raise ValueError('No weather data found')
                    self._check_errors(result)
                    return result, False
            except (ValueError, TimeoutError, aiohttp.ClientError) as err:
                err_msg = str(err).replace(self._api_key, "REDACTED")
                is_client_error = (
                    isinstance(err, aiohttp.ClientResponseError)
                    and 400 <= err.status < 500
                    and err.status != 429
                )
                if attempt == 1 or is_client_error:
                    _LOGGER.error('Error getting %s weather. Exception: %s. Details: %s', description, type(err), err_msg)
                    return None, True
                _LOGGER.warning('Error getting %s weather, will retry. Exception: %s. Details: %s', description, type(err), err_msg)
                await asyncio.sleep(5)
        return None, True

    def _check_errors(self, response: dict[str, Any]) -> None:
        if 'errors' not in response:
            return
        if errors := response['errors']:
            messages = '; '.join([
                e.get('message', str(e)) if isinstance(e, dict) else str(e)
                for e in errors
            ])
            raise ValueError(f'Weather.com API error: {messages}')

    def get_current(self, field: str) -> Any:
        if not self.data or self.data.get(RESULTS_CURRENT) is None:
            return None
        return self.data[RESULTS_CURRENT].get(field)

    def get_forecast_daily(self, field: str, period: int = 0) -> Any:
        try:
            if field in [
                FIELD_TEMPERATUREMAX,
                FIELD_TEMPERATUREMIN,
                FIELD_VALIDTIMEUTC,
            ]:
                # Those fields exist per-day, rather than per dayPart, so the period is halved
                return self.data[RESULTS_FORECAST_DAILY][field][period // 2]
            return self.data[RESULTS_FORECAST_DAILY][FIELD_DAYPART][0][field][period]
        except (IndexError, KeyError, TypeError):
            return None

    def get_forecast_hourly(self, field: str, hour: int) -> Any:
        try:
            return self.data[RESULTS_FORECAST_HOURLY][field][hour]
        except (IndexError, KeyError, TypeError):
            return None

    @staticmethod
    def iconcode_to_condition(icon_code: int | None) -> str | None:
        if icon_code is None or icon_code == 44:
            return None
        if (condition := ICON_CODE_MAP.get(icon_code)) is not None:
            return condition
        _LOGGER.warning('Unmapped icon code from Weather.com API: %s', icon_code)
        return None

    @staticmethod
    def format_timestamp(timestamp_secs: int | float | None) -> str | None:
        if timestamp_secs is None:
            return None
        return datetime.fromtimestamp(timestamp_secs, tz=UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def _get_device_info(name: str) -> DeviceInfo:
    """Get device info."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, name)},
        manufacturer="Weather.com",
        name=name,
    )
