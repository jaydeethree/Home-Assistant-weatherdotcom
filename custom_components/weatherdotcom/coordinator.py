"""The Weather.com data coordinator."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from .api_key import async_extract_api_key, async_validate_api_key
from .const import (
    API_URL_IMPERIAL,
    API_URL_METRIC,
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DOMAIN,
    FIELD_DAYPART,
    FIELD_QPF,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_VALIDTIMEUTC,
    HEADERS,
    ICON_CODE_MAP,
    LOCATION_TYPE_ENTITY,
    LOCATION_TYPE_LATLONG,
    RESOURCE_CURRENT,
    RESOURCE_FORECAST_DAILY,
    RESOURCE_FORECAST_HOURLY,
    RESULTS_CURRENT,
    RESULTS_FORECAST_DAILY,
    RESULTS_FORECAST_HOURLY,
)
from .store import WeatherDotComStorage

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=20)
MAX_CONSECUTIVE_FAILURES = 3
# Minimum time between attempts to fetch a new API key from Wunderground. Shared
# by all config entries, and kept at module level so it survives setup retries.
API_KEY_REFRESH_COOLDOWN = timedelta(hours=1)
_API_KEY_REFRESH_LOCK = asyncio.Lock()
_last_api_key_refresh: datetime | None = None
_WARNED_ICON_CODES: set[int] = set()


@dataclass(frozen=True, kw_only=True)
class WeatherUnits:
    """Units of measurement for a unit system."""

    temperature: UnitOfTemperature
    precipitation: UnitOfLength
    snow: UnitOfLength
    distance: UnitOfLength
    speed: UnitOfSpeed
    pressure: UnitOfPressure
    visibility: UnitOfLength


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


type WeatherDotComConfigEntry = ConfigEntry[WeatherUpdateCoordinator]


class WeatherUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """The Weather.com update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WeatherDotComConfigEntry,
    ) -> None:
        """Initialize."""
        self._entry = entry
        self._api_key = entry.data[CONF_API_KEY]
        self._location_name = entry.data[CONF_NAME]
        self._unit_system_api = (
            API_URL_METRIC if hass.config.units is METRIC_SYSTEM else API_URL_IMPERIAL
        )
        self._lang = entry.data[CONF_LANG]
        self._consecutive_failures: dict[str, int] = {
            RESULTS_CURRENT: 0,
            RESULTS_FORECAST_DAILY: 0,
            RESULTS_FORECAST_HOURLY: 0,
        }
        self._session = async_get_clientsession(hass)
        self.store = WeatherDotComStorage(hass, self._location_name)

        # Only use the location fields for the configured location source. Entries
        # reconfigured by older versions may contain stale keys from a previous
        # location source. Entries without a location source predate that option
        # and keep the legacy behavior of using whatever is present.
        location_source = entry.data.get(CONF_LOCATION_SOURCE)
        location_entity_id: str | None = entry.data.get(CONF_ENTITY_ID)
        # For legacy services that have not migrated
        latitude: float | None = entry.data.get(CONF_LATITUDE)
        longitude: float | None = entry.data.get(CONF_LONGITUDE)
        if location_source == LOCATION_TYPE_LATLONG:
            location_entity_id = None
        elif location_source == LOCATION_TYPE_ENTITY:
            latitude = longitude = None

        self._location_entity_id = location_entity_id
        self._latitude = latitude
        self._longitude = longitude
        self.current_latitude: float | None = latitude
        self.current_longitude: float | None = longitude

        self.device_info = _get_device_info(self._location_name)
        self.units = (
            METRIC_UNITS if self._unit_system_api == API_URL_METRIC else IMPERIAL_UNITS
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} ({self._location_name})",
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )

    @property
    def location_name(self) -> str:
        """Return the location used for data."""
        return self._location_name

    def _get_coordinates(self) -> tuple[float | None, float | None]:
        """Fetch current latitude and longitude and obfuscate if needed."""
        # New configuration attempt
        if self._location_entity_id and (
            state := self.hass.states.get(self._location_entity_id)
        ):
            raw_lat = state.attributes.get(CONF_LATITUDE)
            raw_long = state.attributes.get(CONF_LONGITUDE)
            if raw_lat is not None and raw_long is not None:
                try:
                    return round(float(raw_lat), 2), round(float(raw_long), 2)
                except TypeError, ValueError:
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

        _LOGGER.error(
            "Could not determine latitude/longitude from entity or prior config"
        )
        return None, None

    async def _async_update_data(self) -> dict[str, Any]:
        """Get weather data."""
        latitude, longitude = self._get_coordinates()
        if latitude is None or longitude is None:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_retrieve_coordinates",
                translation_placeholders={
                    "location_entity_id": self._location_entity_id
                    or self._location_name
                },
            )

        self.current_latitude = latitude
        self.current_longitude = longitude

        # Another config entry may have refreshed the shared API key.
        self._api_key = self._entry.data[CONF_API_KEY]

        fetched = await self._async_fetch_all(latitude, longitude)
        if all(has_error for _, has_error in fetched) and (
            await self._async_refresh_api_key()
        ):
            fetched = await self._async_fetch_all(latitude, longitude)

        (
            (result_current, current_error),
            (result_forecast_daily, daily_error),
            (result_forecast_hourly, hourly_error),
        ) = fetched
        if result_forecast_daily is not None:
            # If the result includes max temperature data for today,
            # update that data in storage; otherwise ensure stored data is loaded.
            temp_max_list = result_forecast_daily.get(FIELD_TEMPERATUREMAX)
            valid_time_list = result_forecast_daily.get(FIELD_VALIDTIMEUTC)
            try:
                if (
                    temp_max_list
                    and temp_max_list[0] is not None
                    and valid_time_list
                    and valid_time_list[0] is not None
                ):
                    await self.store.async_save(temp_max_list[0], valid_time_list[0])
                else:
                    await self.store.async_load()
            except (OSError, HomeAssistantError) as err:
                _LOGGER.warning("Failed to access high temperature storage: %s", err)

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
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="update_failed",
                )
            _LOGGER.warning(
                "Failed to get weather data (failure %s of %s); retaining previous data",
                min_failures,
                MAX_CONSECUTIVE_FAILURES,
            )

        return results

    async def _async_fetch_all(
        self, latitude: float, longitude: float
    ) -> list[tuple[dict[str, Any] | None, bool]]:
        """Fetch current conditions and both forecasts concurrently."""
        return list(
            await asyncio.gather(
                self._async_fetch_data(
                    RESOURCE_CURRENT, latitude, longitude, "current"
                ),
                self._async_fetch_data(
                    RESOURCE_FORECAST_DAILY, latitude, longitude, "daily"
                ),
                self._async_fetch_data(
                    RESOURCE_FORECAST_HOURLY, latitude, longitude, "hourly"
                ),
            )
        )

    async def _async_refresh_api_key(self) -> bool:
        """Try to replace a failing API key with the one Wunderground serves now.

        Called when all Weather.com requests failed. Returns True when a new,
        working key was stored, so the caller can retry the requests.
        """
        global _last_api_key_refresh

        async with _API_KEY_REFRESH_LOCK:
            old_key = self._api_key
            # A concurrent refresh for another entry may already have
            # replaced this key while we were waiting for the lock.
            if (current := self._entry.data[CONF_API_KEY]) != old_key:
                self._api_key = current
                return True

            now = dt_util.utcnow()
            if (
                _last_api_key_refresh is not None
                and now - _last_api_key_refresh < API_KEY_REFRESH_COOLDOWN
            ):
                return False
            _last_api_key_refresh = now

            new_key = await async_extract_api_key(self.hass)
            if not new_key:
                return False
            if new_key == old_key:
                _LOGGER.warning(
                    "Wunderground still serves the configured API key; "
                    "no replacement key available"
                )
                return False
            if error := await async_validate_api_key(self.hass, new_key):
                _LOGGER.warning(
                    "API key retrieved from Wunderground did not validate (%s)",
                    error,
                )
                return False

            _LOGGER.warning(
                "Weather.com API key failed; switched to the key Wunderground "
                "serves now (ending in %s)",
                new_key[-6:],
            )
            # Update every entry that used the failing key, not just this one.
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(CONF_API_KEY) == old_key:
                    self.hass.config_entries.async_update_entry(
                        entry, data={**entry.data, CONF_API_KEY: new_key}
                    )
            self._api_key = new_key
            return True

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
                    async with self._session.get(
                        resource, params=params, headers=HEADERS
                    ) as response:
                        response.raise_for_status()
                        result = await response.json(content_type=None)
                    if not isinstance(result, dict):
                        raise ValueError("No weather data found")
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
                    _LOGGER.error(
                        "Error getting %s weather. Exception: %s. Details: %s",
                        description,
                        type(err),
                        err_msg,
                    )
                    return None, True
                _LOGGER.warning(
                    "Error getting %s weather, will retry. Exception: %s. Details: %s",
                    description,
                    type(err),
                    err_msg,
                )
                await asyncio.sleep(5)
        return None, True

    def _check_errors(self, response: dict[str, Any]) -> None:
        """Raise ValueError if the API response contains errors."""
        if "errors" not in response:
            return
        if errors := response["errors"]:
            messages = "; ".join(
                [
                    e.get("message", str(e)) if isinstance(e, dict) else str(e)
                    for e in errors
                ]
            )
            raise ValueError(f"Weather.com API error: {messages}")

    def get_current(self, field: str) -> Any:
        """Return a field from the current observations data."""
        if not self.data or self.data.get(RESULTS_CURRENT) is None:
            return None
        return self.data[RESULTS_CURRENT].get(field)

    def get_forecast_daily(
        self, field: str, period: int = 0, is_daypart: bool = True
    ) -> Any:
        """Return a field from the daily or daypart forecast data."""
        try:
            if field in [
                FIELD_TEMPERATUREMAX,
                FIELD_TEMPERATUREMIN,
                FIELD_VALIDTIMEUTC,
            ] or (field == FIELD_QPF and not is_daypart):
                # Those fields exist per-day, rather than per dayPart, so the period is halved
                return self.data[RESULTS_FORECAST_DAILY][field][period // 2]
            return self.data[RESULTS_FORECAST_DAILY][FIELD_DAYPART][0][field][period]
        except IndexError, KeyError, TypeError:
            return None

    def get_forecast_hourly(self, field: str, hour: int) -> Any:
        """Return a field from the hourly forecast data for a given hour."""
        try:
            return self.data[RESULTS_FORECAST_HOURLY][field][hour]
        except IndexError, KeyError, TypeError:
            return None

    @staticmethod
    def iconcode_to_condition(icon_code: int | None) -> str | None:
        """Map a Weather.com icon code to a Home Assistant weather condition."""
        if icon_code is None or icon_code == 44:
            return None
        if (condition := ICON_CODE_MAP.get(icon_code)) is not None:
            return condition
        if icon_code not in _WARNED_ICON_CODES:
            _WARNED_ICON_CODES.add(icon_code)
            _LOGGER.warning("Unmapped icon code from Weather.com API: %s", icon_code)
        return None

    @staticmethod
    def format_timestamp(timestamp_secs: int | float) -> str:
        """Format a UTC timestamp in seconds as an ISO 8601 string."""
        return datetime.fromtimestamp(timestamp_secs, tz=UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )


def _get_device_info(name: str) -> DeviceInfo:
    """Get device info."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, name)},
        manufacturer="Weather.com",
        name=name,
    )
