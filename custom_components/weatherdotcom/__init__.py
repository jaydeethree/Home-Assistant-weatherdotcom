"""The weather.com component."""

from typing import Final

from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .coordinator import (
    WeatherDotComConfigEntry,
    WeatherUpdateCoordinator,
)
from .store import WeatherDotComStorage

PLATFORMS: Final = [Platform.WEATHER, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: WeatherDotComConfigEntry
) -> bool:
    """Set up the Weather.com component."""
    weathercoordinator = WeatherUpdateCoordinator(hass, entry)
    await weathercoordinator.async_config_entry_first_refresh()

    entry.runtime_data = weathercoordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WeatherDotComConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, entry: WeatherDotComConfigEntry
) -> None:
    """Remove a config entry and clean up persistent storage."""
    if location_name := entry.data.get(CONF_NAME):
        await WeatherDotComStorage(hass, location_name).async_remove()
