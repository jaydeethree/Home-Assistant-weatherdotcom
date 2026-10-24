"""The weather.com component."""
import logging
from pathlib import Path
from typing import Final
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    Platform
)
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import METRIC_SYSTEM
from homeassistant.util import json
from .coordinator import WeatherUpdateCoordinator, WeatherUpdateCoordinatorConfig
from .store import WeatherDotComStorage
from .const import (
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    LOCATION_TYPE_ENTITY,
    LOCATION_TYPE_LATLONG,
    API_URL_METRIC,
    API_URL_IMPERIAL
)

PLATFORMS: Final = [Platform.WEATHER, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


type WeatherDotComConfigEntry = ConfigEntry[WeatherUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: WeatherDotComConfigEntry) -> bool:
    """Set up the Weather.com component."""
    if hass.config.units is METRIC_SYSTEM:
        unit_system_api = API_URL_METRIC
    else:
        unit_system_api = API_URL_IMPERIAL

    lang = entry.data[CONF_LANG]

    def _load_translation_file() -> dict:
        tfiledir = Path(__file__).parent / "weather_translations"
        tfilename = lang.split('-', 1)[0]
        tfilepath = tfiledir / f"{tfilename}.json"
        if tfilepath.is_file():
            return json.load_json(tfilepath)
        _LOGGER.warning(
            'Sensor translation file %s.json does not exist. Defaulting to en-US.',
            tfilename,
        )
        return json.load_json(tfiledir / "en.json")

    tranfile = await hass.async_add_executor_job(_load_translation_file)

    # Only pass the location fields for the configured location source. Entries
    # reconfigured by older versions may contain stale keys from a previous
    # location source. Entries without a location source predate that option
    # and keep the legacy behavior of passing whatever is present.
    location_source = entry.data.get(CONF_LOCATION_SOURCE)
    location_entity_id = entry.data.get(CONF_ENTITY_ID)
    latitude = entry.data.get(CONF_LATITUDE)
    longitude = entry.data.get(CONF_LONGITUDE)
    if location_source == LOCATION_TYPE_LATLONG:
        location_entity_id = None
    elif location_source == LOCATION_TYPE_ENTITY:
        latitude = longitude = None

    # Initialize legacy and new instances
    config = WeatherUpdateCoordinatorConfig(
        api_key=entry.data[CONF_API_KEY],
        location_name=entry.data[CONF_NAME],
        unit_system_api=unit_system_api,
        lang=lang,
        location_entity_id=location_entity_id,
        latitude=latitude,
        longitude=longitude,
        tranfile=tranfile,
    )

    weathercoordinator = WeatherUpdateCoordinator(hass, config, entry)
    await weathercoordinator.async_config_entry_first_refresh()

    entry.runtime_data = weathercoordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeatherDotComConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: WeatherDotComConfigEntry) -> None:
    """Remove a config entry and clean up persistent storage."""
    if location_name := entry.data.get(CONF_NAME):
        await WeatherDotComStorage(hass, location_name).async_remove()
