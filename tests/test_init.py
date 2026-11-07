"""Tests for Weather.com component setup, unload, removal, and storage."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.weatherdotcom import async_remove_entry
from custom_components.weatherdotcom.const import (
    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE,
)
from custom_components.weatherdotcom.store import WeatherDotComStorage

from .conftest import TEST_NAME


async def test_setup_unload_and_remove_entry(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting up, unloading, and removing a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state.value == ConfigEntryState.LOADED.value
    assert mock_config_entry.runtime_data is not None

    # Verify high temperature was persisted during initial setup
    store = WeatherDotComStorage(hass, TEST_NAME)
    loaded = await store.async_load()
    assert loaded[HIGH_TEMP_TODAY_STORAGE] == 80

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state.value == ConfigEntryState.NOT_LOADED.value

    # Removing the entry should remove the persistent storage file
    await async_remove_entry(hass, mock_config_entry)
    store_after = WeatherDotComStorage(hass, TEST_NAME)
    assert await store_after.async_load() == {}


async def test_storage_load_save_deduplicate_and_remove(
    hass: HomeAssistant,
) -> None:
    """Test WeatherDotComStorage load, save, deduplication, and remove."""
    store = WeatherDotComStorage(hass, "My Home")

    # Before loading, .data returns an empty dict
    assert store.data == {}
    assert await store.async_load() == {}

    # Save initial value
    await store.async_save(78, 1793880000)
    assert store.data == {
        HIGH_TEMP_TODAY_STORAGE: 78,
        HIGH_TEMP_TODAY_TIMESTAMP_STORAGE: 1793880000,
    }

    # Saving identical values is a no-op
    await store.async_save(78, 1793880000)
    assert store.data == {
        HIGH_TEMP_TODAY_STORAGE: 78,
        HIGH_TEMP_TODAY_TIMESTAMP_STORAGE: 1793880000,
    }

    # Saving updated value persists to disk and is readable by a fresh instance
    await store.async_save(82, 1793880000)
    fresh_store = WeatherDotComStorage(hass, "My Home")
    assert await fresh_store.async_load() == {
        HIGH_TEMP_TODAY_STORAGE: 82,
        HIGH_TEMP_TODAY_TIMESTAMP_STORAGE: 1793880000,
    }

    # Removing clears both cached and stored data
    await fresh_store.async_remove()
    assert fresh_store.data == {}
    deleted_store = WeatherDotComStorage(hass, "My Home")
    assert await deleted_store.async_load() == {}
