"""Tests for Weather.com WeatherUpdateCoordinator."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.unit_system import METRIC_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.weatherdotcom.const import (
    API_URL_IMPERIAL,
    API_URL_METRIC,
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DEFAULT_LANG,
    DOMAIN,
    FIELD_QPF,
    FIELD_TEMP,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_VALIDTIMEUTC,
    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE,
    LOCATION_TYPE_ENTITY,
    RESULTS_CURRENT,
)
from custom_components.weatherdotcom.coordinator import (
    IMPERIAL_UNITS,
    MAX_CONSECUTIVE_FAILURES,
    METRIC_UNITS,
    WeatherUpdateCoordinator,
)

from .conftest import (
    TEST_API_KEY,
    TEST_LATITUDE,
    TEST_LONGITUDE,
    TEST_NAME,
    URL_CURRENT_PATTERN,
    URL_DAILY_PATTERN,
    URL_HOURLY_PATTERN,
)


async def test_coordinator_units_metric_and_imperial(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator selects metric or imperial units based on Home Assistant config."""
    hass.config.units = METRIC_SYSTEM
    coord_metric = WeatherUpdateCoordinator(hass, mock_config_entry)
    assert coord_metric.units == METRIC_UNITS
    assert coord_metric._unit_system_api == API_URL_METRIC
    assert coord_metric.location_name == TEST_NAME

    from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

    hass.config.units = US_CUSTOMARY_SYSTEM
    coord_imperial = WeatherUpdateCoordinator(hass, mock_config_entry)
    assert coord_imperial.units == IMPERIAL_UNITS
    assert coord_imperial._unit_system_api == API_URL_IMPERIAL


async def test_coordinator_coordinates_from_entity_rounded(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
) -> None:
    """Test coordinator fetches and rounds coordinates to 2 decimals from an entity."""
    hass.states.async_set(
        "person.alice",
        "home",
        {CONF_LATITUDE: 33.748995, CONF_LONGITUDE: -84.387982},
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TEST_NAME,
        data={
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
            CONF_ENTITY_ID: "person.alice",
            # Stale lat/long keys should be ignored when source is entity
            CONF_LATITUDE: 10.0,
            CONF_LONGITUDE: 20.0,
        },
    )
    entry.add_to_hass(hass)
    coordinator = WeatherUpdateCoordinator(hass, entry)
    await coordinator.async_refresh()

    assert coordinator.current_latitude == 33.75
    assert coordinator.current_longitude == -84.39


async def test_coordinator_coordinates_fallback_to_last_known_and_failure(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test fallback to last known coordinates when entity becomes unavailable, and failure when none exist."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TEST_NAME,
        data={
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
            CONF_ENTITY_ID: "person.missing",
        },
    )
    entry.add_to_hass(hass)
    coordinator = WeatherUpdateCoordinator(hass, entry)

    # Initially entity does not exist and no last known coordinates -> UpdateFailed
    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()
    assert exc_info.value.translation_key == "cannot_retrieve_coordinates"

    # Now set entity state with non-numeric coordinates -> falls through to error
    hass.states.async_set(
        "person.missing",
        "home",
        {CONF_LATITUDE: "bad", CONF_LONGITUDE: "coords"},
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Now set valid entity state -> succeeds and stores current_latitude / current_longitude
    hass.states.async_set(
        "person.missing",
        "home",
        {CONF_LATITUDE: TEST_LATITUDE, CONF_LONGITUDE: TEST_LONGITUDE},
    )
    await coordinator._async_update_data()
    assert coordinator.current_latitude == TEST_LATITUDE
    assert coordinator.current_longitude == TEST_LONGITUDE

    # Remove entity state -> falls back to last known coordinates with warning
    hass.states.async_remove("person.missing")
    await coordinator._async_update_data()
    assert "using last known coordinates" in caplog.text


async def test_coordinator_partial_endpoint_failure_and_recovery(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test partial endpoint failure retains previous data until MAX_CONSECUTIVE_FAILURES, then clears and recovers."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    coordinator = WeatherUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    assert coordinator.data[RESULTS_CURRENT] == current_json

    # Make current endpoint fail while daily & hourly succeed
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    # Failures 1 and 2 (< MAX_CONSECUTIVE_FAILURES=3) retain previous current data
    for expected_failures in range(1, MAX_CONSECUTIVE_FAILURES):
        data = await coordinator._async_update_data()
        coordinator.async_set_updated_data(data)
        assert coordinator._consecutive_failures[RESULTS_CURRENT] == expected_failures
        assert coordinator.data[RESULTS_CURRENT] == current_json

    # Failure 3 (== MAX_CONSECUTIVE_FAILURES) sets current data to None
    data = await coordinator._async_update_data()
    coordinator.async_set_updated_data(data)
    assert (
        coordinator._consecutive_failures[RESULTS_CURRENT] == MAX_CONSECUTIVE_FAILURES
    )
    assert coordinator.data[RESULTS_CURRENT] is None
    assert coordinator.get_current(FIELD_TEMP) is None

    # Recovery on next poll resets consecutive failures to 0
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    data = await coordinator._async_update_data()
    coordinator.async_set_updated_data(data)
    assert coordinator._consecutive_failures[RESULTS_CURRENT] == 0
    assert coordinator.data[RESULTS_CURRENT] == current_json


async def test_coordinator_total_failure_first_refresh_and_subsequent(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test total failure raises ConfigEntryNotReady on first refresh and UpdateFailed at threshold on subsequent refreshes."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(URL_CURRENT_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    aioclient_mock.get(URL_DAILY_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    aioclient_mock.get(URL_HOURLY_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id) is False
    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY

    # Now succeed on first refresh
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)
    coordinator = WeatherUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()

    # Now all 3 endpoints fail on subsequent refreshes
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    aioclient_mock.get(URL_DAILY_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    aioclient_mock.get(URL_HOURLY_PATTERN, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # First 2 total failures retain previous data without raising UpdateFailed
    for _ in range(1, MAX_CONSECUTIVE_FAILURES):
        data = await coordinator._async_update_data()
        coordinator.async_set_updated_data(data)
        assert coordinator.data[RESULTS_CURRENT] == current_json

    # 3rd total failure raises UpdateFailed
    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()
    assert exc_info.value.translation_key == "update_failed"


@pytest.mark.parametrize(
    ("status", "should_retry"),
    [
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.UNAUTHORIZED, False),
        (HTTPStatus.FORBIDDEN, False),
        (HTTPStatus.NOT_FOUND, False),
    ],
)
async def test_coordinator_retry_behavior_by_http_status(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    fast_retry_sleep: AsyncMock,
    mock_config_entry: MockConfigEntry,
    status: HTTPStatus,
    should_retry: bool,
) -> None:
    """Test that 5xx and 429 retry once, while 4xx (except 429) do not retry."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(URL_CURRENT_PATTERN, status=status)
    coordinator = WeatherUpdateCoordinator(hass, mock_config_entry)

    result, has_error = await coordinator._async_fetch_data(
        "https://api.weather.com/v3/wx/observations/current",
        TEST_LATITUDE,
        TEST_LONGITUDE,
        "current",
    )
    assert result is None
    assert has_error is True
    assert fast_retry_sleep.call_count == (1 if should_retry else 0)


async def test_coordinator_api_errors_and_redaction(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test handling non-dict JSON, API 'errors' payload, and API key redaction in logs."""
    mock_config_entry.add_to_hass(hass)
    coordinator = WeatherUpdateCoordinator(hass, mock_config_entry)

    # 1. Non-dict JSON response
    aioclient_mock.get(URL_CURRENT_PATTERN, json=["not", "a", "dict"])
    result, has_error = await coordinator._async_fetch_data(
        "https://api.weather.com/v3/wx/observations/current",
        TEST_LATITUDE,
        TEST_LONGITUDE,
        "current",
    )
    assert result is None
    assert has_error is True
    assert "No weather data found" in caplog.text

    # 2. Dict with "errors": [] (empty list -> no error)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, json={"errors": [], "temperature": 70})
    result, has_error = await coordinator._async_fetch_data(
        "https://api.weather.com/v3/wx/observations/current",
        TEST_LATITUDE,
        TEST_LONGITUDE,
        "current",
    )
    assert has_error is False
    assert result == {"errors": [], "temperature": 70}

    # 3. Dict with "errors" containing message & string, including the API key -> redacted
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        URL_CURRENT_PATTERN,
        json={
            "errors": [
                {"message": f"Invalid key {TEST_API_KEY}"},
                "Secondary error",
            ]
        },
    )
    result, has_error = await coordinator._async_fetch_data(
        "https://api.weather.com/v3/wx/observations/current",
        TEST_LATITUDE,
        TEST_LONGITUDE,
        "current",
    )
    assert result is None
    assert has_error is True
    assert "REDACTED" in caplog.text
    assert TEST_API_KEY not in caplog.text


async def test_coordinator_high_temperature_storage_and_oserror(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    daily_daypart_expired_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test saving daytime high temperature to storage, loading when expired, and handling OSError."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    coordinator = WeatherUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()

    # Daytime fixture has temperatureMax[0] == 80, so it is saved in storage
    assert coordinator.store.data == {
        HIGH_TEMP_TODAY_STORAGE: 80,
        HIGH_TEMP_TODAY_TIMESTAMP_STORAGE: daily_15day_json[FIELD_VALIDTIMEUTC][0],
    }

    # Evening fixture has temperatureMax[0] == None -> calls store.async_load()
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_daypart_expired_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)
    await coordinator._async_update_data()
    assert coordinator.store.data[HIGH_TEMP_TODAY_STORAGE] == 80

    # Simulate OSError when saving high temperature
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)
    with patch.object(
        coordinator.store, "async_save", side_effect=OSError("disk full")
    ):
        await coordinator._async_update_data()
    assert "Failed to save high temperature to storage: disk full" in caplog.text


async def test_coordinator_data_accessors(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test get_current, get_forecast_daily, and get_forecast_hourly accessors and bounds."""
    mock_config_entry.add_to_hass(hass)
    coordinator = WeatherUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()

    # Current observations
    assert coordinator.get_current(FIELD_TEMP) == 66

    # Daily per-day fields (period // 2) vs per-daypart fields (period)
    assert coordinator.get_forecast_daily(FIELD_TEMPERATUREMAX, period=0) == 80
    assert coordinator.get_forecast_daily(FIELD_TEMPERATUREMAX, period=1) == 80
    assert coordinator.get_forecast_daily(FIELD_TEMPERATUREMIN, period=2) == 47
    assert (
        coordinator.get_forecast_daily(FIELD_QPF, period=28, is_daypart=False) == 0.07
    )
    assert coordinator.get_forecast_daily(FIELD_QPF, period=29, is_daypart=True) == 0.07
    assert coordinator.get_forecast_daily(FIELD_TEMP, period=0) == 80
    assert coordinator.get_forecast_daily(FIELD_TEMP, period=1) == 55

    # Out-of-range or missing keys return None gracefully
    assert coordinator.get_forecast_daily(FIELD_TEMP, period=999) is None
    assert coordinator.get_forecast_daily("nonexistent", period=0) is None
    assert coordinator.get_forecast_hourly(FIELD_TEMP, hour=0) == 65
    assert coordinator.get_forecast_hourly(FIELD_TEMP, hour=999) is None
    assert coordinator.get_forecast_hourly("nonexistent", hour=0) is None
