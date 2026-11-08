"""Tests for Weather.com sensor entities and descriptions."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from syrupy.assertion import SnapshotAssertion

from custom_components.weatherdotcom.const import (
    CONF_EXTRA_ATTRIBUTES,
    EXTRA_ATTRIBUTE_KEYS_DAILY,
    EXTRA_ATTRIBUTE_KEYS_DAY,
    EXTRA_ATTRIBUTE_KEYS_DAYPART,
    FIELD_WINDDIRECTIONCARDINAL,
    FIELD_WINDSPEED,
    RESULTS_CURRENT,
    RESULTS_FORECAST_DAILY,
)
from custom_components.weatherdotcom.sensor import _get_sensor_data
from custom_components.weatherdotcom.sensor_descriptions import _get_extra_attributes

from .conftest import URL_CURRENT_PATTERN, URL_DAILY_PATTERN, URL_HOURLY_PATTERN


async def test_sensors_snapshot_metric(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all default-enabled sensor states and attributes with metric units."""
    hass.config.units = METRIC_SYSTEM
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entries = sorted(
        er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id),
        key=lambda e: e.entity_id,
    )
    sensor_states = []
    for entry in entries:
        if entry.domain != "sensor":
            continue
        state = hass.states.get(entry.entity_id)
        sensor_states.append(
            {
                "entity_id": entry.entity_id,
                "unique_id": entry.unique_id,
                "disabled_by": str(entry.disabled_by) if entry.disabled_by else None,
                "state": state.state if state else None,
                "attributes": dict(state.attributes) if state else None,
            }
        )
    assert sensor_states == snapshot


async def test_sensors_units_imperial(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor units when Home Assistant is configured for imperial/US customary."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    temp_state = hass.states.get("sensor.home_temperature")
    assert temp_state is not None
    assert temp_state.attributes["unit_of_measurement"] == "°F"

    wind_state = hass.states.get("sensor.home_wind_speed")
    assert wind_state is not None
    assert wind_state.attributes["unit_of_measurement"] == "mph"

    precip_state = hass.states.get("sensor.home_precipitation_last_24_hours")
    assert precip_state is not None
    assert precip_state.attributes["unit_of_measurement"] == "in"

    snow_state = hass.states.get("sensor.home_snowfall_last_24_hours")
    assert snow_state is not None
    assert snow_state.attributes["unit_of_measurement"] == "in"

    pressure_state = hass.states.get("sensor.home_pressure")
    assert pressure_state is not None
    assert pressure_state.attributes["unit_of_measurement"] == "inHg"


async def test_sensors_availability_when_endpoints_missing(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor availability when current or daily data is None, or coordinator data is None."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_EXTRA_ATTRIBUTES: ["day"]},
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    # 1. When RESULTS_CURRENT is None, current sensors become unavailable,
    #    while latitude, longitude, and forecast_details remain available.
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            RESULTS_CURRENT: None,
        }
    )
    await hass.async_block_till_done()

    temp_state = hass.states.get("sensor.home_temperature")
    assert temp_state is not None
    assert temp_state.state == STATE_UNAVAILABLE

    lat_state = hass.states.get("sensor.home_latitude")
    assert lat_state is not None
    assert lat_state.state == "33.74"

    lon_state = hass.states.get("sensor.home_longitude")
    assert lon_state is not None
    assert lon_state.state == "-84.39"

    forecast_state = hass.states.get("sensor.home_forecast_details")
    assert forecast_state is not None
    assert forecast_state.state != STATE_UNAVAILABLE

    # 2. When RESULTS_FORECAST_DAILY is None, forecast_details becomes unavailable.
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            RESULTS_FORECAST_DAILY: None,
        }
    )
    await hass.async_block_till_done()
    forecast_state = hass.states.get("sensor.home_forecast_details")
    assert forecast_state is not None
    assert forecast_state.state == STATE_UNAVAILABLE

    # 3. When coordinator.last_update_success is False, all sensors become unavailable.
    coordinator.last_update_success = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    lat_state = hass.states.get("sensor.home_latitude")
    assert lat_state is not None
    assert lat_state.state == STATE_UNAVAILABLE


async def test_sensor_wind_direction_calm(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test wind direction degrees sensor returns unknown when wind is calm."""
    current_json[FIELD_WINDSPEED] = 0
    current_json[FIELD_WINDDIRECTIONCARDINAL] = "CALM"
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    wind_deg = hass.states.get("sensor.home_wind_direction_degrees")
    assert wind_deg is not None
    assert wind_deg.state == STATE_UNKNOWN

    wind_cardinal = hass.states.get("sensor.home_wind_direction_cardinal")
    assert wind_cardinal is not None
    assert wind_cardinal.state == "CALM"


async def test_forecast_details_sensor_daytime_and_expired_daypart(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    daily_daypart_expired_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test Forecast Details sensor with all extra attributes in daytime and evening expired-daypart modes."""
    all_attrs = (
        EXTRA_ATTRIBUTE_KEYS_DAILY
        + EXTRA_ATTRIBUTE_KEYS_DAY
        + EXTRA_ATTRIBUTE_KEYS_DAYPART
    )
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)

    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_EXTRA_ATTRIBUTES: all_attrs},
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state_daytime = hass.states.get("sensor.home_forecast_details")
    assert state_daytime is not None
    assert {
        "state": state_daytime.state,
        "attributes": dict(state_daytime.attributes),
    } == snapshot(name="forecast_details_daytime")

    # Switch to evening expired daypart (index 0 is None -> day_* attributes use index 1 for today)
    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            RESULTS_FORECAST_DAILY: daily_daypart_expired_json,
        }
    )
    await hass.async_block_till_done()

    state_expired = hass.states.get("sensor.home_forecast_details")
    assert state_expired is not None
    assert state_expired.attributes["day_icon_code"][0] == 29
    assert state_expired.attributes["day_cloud_cover"][0] == 64
    assert state_expired.attributes["day_relative_humidity"][0] == 92


@pytest.mark.parametrize(
    ("sensors_data", "kind", "expected"),
    [
        (None, "temperature", None),
        ({}, "temperature", None),
        ({RESULTS_CURRENT: None}, "temperature", None),
        ({RESULTS_FORECAST_DAILY: None}, "validTimeUtc", None),
        ({RESULTS_FORECAST_DAILY: {"validTimeUtc": []}}, "validTimeUtc", None),
    ],
)
def test_get_sensor_data_edge_cases(
    sensors_data: dict[str, Any] | None,
    kind: str,
    expected: Any,
) -> None:
    """Test _get_sensor_data edge cases when data or nested keys are missing."""
    assert _get_sensor_data(sensors_data, kind) == expected


@pytest.mark.parametrize(
    ("coordinator_data", "selected_attributes", "expected"),
    [
        (None, ["day"], None),
        ({}, ["day"], None),
        ({RESULTS_FORECAST_DAILY: "not_a_dict"}, ["day"], None),
        ({RESULTS_FORECAST_DAILY: {"dayOfWeek": ["Thursday"]}}, None, None),
        (
            {RESULTS_FORECAST_DAILY: {"dayOfWeek": ["Thursday"]}},
            ["day"],
            {"day": ["Thursday"]},
        ),
        (
            {RESULTS_FORECAST_DAILY: {"daypart": []}},
            ["day_icon_code"],
            {"day_icon_code": [None] * 15},
        ),
    ],
)
def test_get_extra_attributes_edge_cases(
    coordinator_data: dict[str, Any] | None,
    selected_attributes: list[str] | None,
    expected: dict[str, Any] | None,
) -> None:
    """Test _get_extra_attributes edge cases."""
    assert _get_extra_attributes(coordinator_data, selected_attributes) == expected
