"""Persistent storage for the Weather.com component."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,

    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE
)

STORAGE_KEY = '{domain}.{location_name}'
STORAGE_VERSION = 1


class WeatherDotComStorage:
    """Persistent storage for Weather.com data."""

    def __init__(self, hass: HomeAssistant, location_name: str) -> None:
        self._store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY.format(domain=DOMAIN, location_name=location_name.lower()),
        )
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, Any]:
        if self._data is None:
            self._data = await self._store.async_load() or {}
        return self._data

    async def async_save(self, high_temp_today, high_temp_today_timestamp) -> None:
        data_to_save = {
            HIGH_TEMP_TODAY_STORAGE: high_temp_today,
            HIGH_TEMP_TODAY_TIMESTAMP_STORAGE: high_temp_today_timestamp,
        }
        self._data = data_to_save
        await self._store.async_save(data_to_save)

    async def async_remove(self) -> None:
        self._data = None
        await self._store.async_remove()
