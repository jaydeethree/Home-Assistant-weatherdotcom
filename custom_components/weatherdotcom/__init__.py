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
from .const import (
    CONF_LANG,
    API_METRIC,
    API_IMPERIAL,
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
        unit_system = API_METRIC
    else:
        unit_system_api = API_URL_IMPERIAL
        unit_system = API_IMPERIAL

# Initialize legacy and new instances
    config = WeatherUpdateCoordinatorConfig(
        api_key=entry.data[CONF_API_KEY],
        location_name=entry.data[CONF_NAME],
        unit_system_api=unit_system_api,
        unit_system=unit_system,
        lang=entry.data[CONF_LANG],
        location_entity_id=entry.data.get(CONF_ENTITY_ID),
        latitude=entry.data.get(CONF_LATITUDE),
        longitude=entry.data.get(CONF_LONGITUDE),
        tranfile='',
    )

    def _load_translation_file() -> dict:
        tfiledir = Path(__file__).parent / "weather_translations"
        tfilename = config.lang.split('-', 1)[0]
        tfilepath = tfiledir / f"{tfilename}.json"
        if tfilepath.is_file():
            return json.load_json(tfilepath)
        _LOGGER.warning(
            'Sensor translation file %s.json does not exist. Defaulting to en-US.',
            tfilename,
        )
        return json.load_json(tfiledir / "en.json")

    config.tranfile = await hass.async_add_executor_job(_load_translation_file)

    weathercoordinator = WeatherUpdateCoordinator(hass, config)
    await weathercoordinator.async_config_entry_first_refresh()

    entry.runtime_data = weathercoordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeatherDotComConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
