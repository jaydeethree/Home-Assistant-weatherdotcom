"""Tests for Weather.com diagnostics."""

from __future__ import annotations

from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.weatherdotcom.const import (
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DEFAULT_LANG,
    HIGH_TEMP_TODAY_STORAGE,
    LOCATION_TYPE_LATLONG,
    RESULTS_CURRENT,
)
from custom_components.weatherdotcom.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import TEST_NAME


async def test_config_entry_diagnostics(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test config entry diagnostics redacts sensitive fields and includes coordinator/store data."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["entry_data"] == {
        CONF_API_KEY: REDACTED,
        CONF_NAME: TEST_NAME,
        CONF_LANG: DEFAULT_LANG,
        CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        CONF_LATITUDE: REDACTED,
        CONF_LONGITUDE: REDACTED,
    }
    assert diagnostics["options"] == {}
    assert diagnostics["coordinator_data"][RESULTS_CURRENT]["temperature"] == 66
    assert diagnostics["stored_data"][HIGH_TEMP_TODAY_STORAGE] == 80
