"""Tests for Weather.com weather entity and forecasts."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.weather import (
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_WIND_BEARING,
)
from homeassistant.components.weather.const import (
    DOMAIN as WEATHER_DOMAIN,
)
from homeassistant.components.weather.const import (
    SERVICE_GET_FORECASTS,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from syrupy.assertion import SnapshotAssertion

from custom_components.weatherdotcom.const import (
    FIELD_DAYPART,
    FIELD_PRECIPCHANCE,
    FIELD_VALIDTIMEUTC,
    FIELD_WINDDIRECTIONCARDINAL,
    FIELD_WINDSPEED,
    RESULTS_FORECAST_DAILY,
    RESULTS_FORECAST_HOURLY,
)

from .conftest import (
    TEST_NAME,
    URL_CURRENT_PATTERN,
    URL_DAILY_PATTERN,
    URL_HOURLY_PATTERN,
)


async def _async_get_forecasts(
    hass: HomeAssistant, forecast_type: str
) -> list[dict[str, Any]]:
    """Call weather.get_forecasts and return the forecast list for weather.home."""
    resp: Any = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {ATTR_ENTITY_ID: "weather.home", "type": forecast_type},
        blocking=True,
        return_response=True,
    )
    assert isinstance(resp, dict)
    entity_data = resp["weather.home"]
    assert isinstance(entity_data, dict)
    forecast = entity_data["forecast"]
    assert isinstance(forecast, list)
    return forecast


async def test_weather_state_and_forecasts_snapshot(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test weather entity state and daily, twice_daily, and hourly forecasts."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state is not None
    assert {
        "state": state.state,
        "attributes": dict(state.attributes),
    } == snapshot(name="weather_state")

    daily_resp = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {ATTR_ENTITY_ID: "weather.home", "type": "daily"},
        blocking=True,
        return_response=True,
    )
    assert daily_resp == snapshot(name="forecast_daily")

    twice_daily_resp = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {ATTR_ENTITY_ID: "weather.home", "type": "twice_daily"},
        blocking=True,
        return_response=True,
    )
    assert twice_daily_resp == snapshot(name="forecast_twice_daily")

    hourly_forecasts = await _async_get_forecasts(hass, "hourly")
    assert len(hourly_forecasts) == 360
    assert hourly_forecasts[:24] == snapshot(name="forecast_hourly_first_24")


async def test_weather_expired_daypart_restores_stored_high_temp(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    daily_daypart_expired_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test evening expired-daypart restores stored high temp for today when timestamp matches, and logs when stale/missing."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    # 1. Switch to evening expired-daypart fixture (temperatureMax[0] is None, daypart[0] index 0 is None).
    #    Because daytime setup saved 80 with matching validTimeUtc[0], today's high temp is restored to 80.
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_daypart_expired_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    daily_forecast = await _async_get_forecasts(hass, "daily")
    assert len(daily_forecast) == 15
    assert daily_forecast[0][ATTR_FORECAST_TEMP] == 80

    # Twice-daily forecast should start at period 1 (Tonight, is_daytime=False, 29 items total)
    twice_daily_forecast = await _async_get_forecasts(hass, "twice_daily")
    assert len(twice_daily_forecast) == 29
    assert twice_daily_forecast[0]["is_daytime"] is False
    assert twice_daily_forecast[0][ATTR_FORECAST_TEMP] == 55

    # 2. If stored timestamp is from a prior day, high temperature is None and debug message is logged
    await coordinator.store.async_save(99, 1000000000)
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    daily_forecast_stale = await _async_get_forecasts(hass, "daily")
    assert daily_forecast_stale[0].get(ATTR_FORECAST_TEMP) is None
    assert (
        f"Stored value for maximum temperature is old or missing and the API is not returning this data - maximum temperature data in the daily forecast will be missing for today for: weather.{TEST_NAME.lower()}"
        in caplog.text
    )


async def test_weather_calm_wind_and_empty_forecasts(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test calm wind bearing in current/forecasts, precipChance fallback, and empty forecasts when data is None."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    current_json[FIELD_WINDSPEED] = 0
    current_json[FIELD_WINDDIRECTIONCARDINAL] = "CALM"
    # Set daytime precipChance[0] = None and nighttime precipChance[1] = 45 to test fallback on line 231-232
    daily_15day_json[FIELD_DAYPART][0][FIELD_PRECIPCHANCE][0] = None
    daily_15day_json[FIELD_DAYPART][0][FIELD_PRECIPCHANCE][1] = 45
    daily_15day_json[FIELD_DAYPART][0][FIELD_WINDSPEED][0] = 0
    hourly_15day_json[FIELD_WINDSPEED][0] = 0

    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state is not None
    assert state.attributes.get("wind_bearing") is None

    daily_0 = (await _async_get_forecasts(hass, "daily"))[0]
    assert daily_0[ATTR_FORECAST_PRECIPITATION_PROBABILITY] == 45
    assert daily_0.get(ATTR_FORECAST_WIND_BEARING) is None

    twice_daily_0 = (await _async_get_forecasts(hass, "twice_daily"))[0]
    assert twice_daily_0.get(ATTR_FORECAST_WIND_BEARING) is None

    hourly_0 = (await _async_get_forecasts(hass, "hourly"))[0]
    assert hourly_0.get(ATTR_FORECAST_WIND_BEARING) is None

    # If a validTimeUtc entry is None, that entry is skipped rather than failing the forecast
    coordinator = mock_config_entry.runtime_data
    daily_15day_json[FIELD_VALIDTIMEUTC][1] = None
    hourly_15day_json[FIELD_VALIDTIMEUTC][2] = None
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            RESULTS_FORECAST_DAILY: daily_15day_json,
            RESULTS_FORECAST_HOURLY: hourly_15day_json,
        }
    )
    await hass.async_block_till_done()
    assert len(await _async_get_forecasts(hass, "daily")) == 14
    assert len(await _async_get_forecasts(hass, "twice_daily")) == 28
    assert len(await _async_get_forecasts(hass, "hourly")) == 359

    # When daily and hourly forecast data are None, forecast services return an empty list
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            RESULTS_FORECAST_DAILY: None,
            RESULTS_FORECAST_HOURLY: None,
        }
    )
    await hass.async_block_till_done()

    for forecast_type in ("daily", "twice_daily", "hourly"):
        assert await _async_get_forecasts(hass, forecast_type) == []
