"""Diagnostics support for Weather.com."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from homeassistant.core import HomeAssistant

from .coordinator import WeatherDotComConfigEntry

TO_REDACT = {
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    "lat",
    "lon",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: WeatherDotComConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "options": async_redact_data(entry.options, TO_REDACT),
        "coordinator_data": async_redact_data(coordinator.data, TO_REDACT),
        "stored_data": async_redact_data(coordinator.store.data, TO_REDACT),
    }
