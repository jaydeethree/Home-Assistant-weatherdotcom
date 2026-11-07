"""Tests for Weather.com config, reconfigure, and options flows."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.weatherdotcom.config_flow import (
    WeatherFlowHandler,
    _get_default_lang,
)
from custom_components.weatherdotcom.const import (
    CONF_EXTRA_ATTRIBUTES,
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DEFAULT_LANG,
    DOMAIN,
    FIELD_VALIDTIMEUTC,
    LOCATION_TYPE_ENTITY,
    LOCATION_TYPE_LATLONG,
)
from custom_components.weatherdotcom.helpers import get_sensor_unique_id

from .conftest import (
    TEST_API_KEY,
    TEST_LATITUDE,
    TEST_LONGITUDE,
    TEST_NAME,
    URL_CURRENT_PATTERN,
)


@pytest.fixture(autouse=True)
def mock_response_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a default reason attribute on AiohttpClientMockResponse."""
    monkeypatch.setattr(AiohttpClientMockResponse, "reason", "OK", raising=False)


@pytest.mark.parametrize(
    ("hass_lang", "hass_country", "expected"),
    [
        (None, None, DEFAULT_LANG),
        ("", None, DEFAULT_LANG),
        ("en-GB", None, "en-GB"),
        ("en-gb", None, "en-GB"),
        ("de-DE", None, "de-DE"),
        ("en", "CA", "en-CA"),
        ("es", "MX", "es-MX"),
        ("en", "ZZ", "en-US"),
        ("zh-Hans", None, "zh-CN"),
        ("zh-Hant", None, "zh-TW"),
        ("nb", None, "no-NO"),
        ("nb-NO", None, "no-NO"),
        ("de", None, "de-DE"),
        ("xx-YY", "ZZ", DEFAULT_LANG),
    ],
)
def test_get_default_lang(
    hass_lang: str | None, hass_country: str | None, expected: str
) -> None:
    """Test resolving the best matching Weather.com language code."""
    assert _get_default_lang(hass_lang, hass_country) == expected


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (33.74, -84.39, True),
        ("33.74", "-84.39", True),
        (0, 0, True),
        (90, 180, True),
        (-90, -180, True),
        (90.1, 0, False),
        (-90.1, 0, False),
        (0, 180.1, False),
        (0, -180.1, False),
        (None, -84.39, False),
        (33.74, None, False),
        ("invalid", -84.39, False),
    ],
)
def test_validate_latlong(lat: Any, lon: Any, expected: bool) -> None:
    """Test validating latitude and longitude bounds and types."""
    assert WeatherFlowHandler._validate_latlong(lat, lon) is expected


async def test_user_flow_latlong_success(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
) -> None:
    """Test full user config flow using latitude/longitude."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == LOCATION_TYPE_LATLONG
    assert result2["errors"] == {}

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
    )
    await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_NAME
    assert result3["data"] == {
        CONF_API_KEY: TEST_API_KEY,
        CONF_NAME: TEST_NAME,
        CONF_LANG: DEFAULT_LANG,
        CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        CONF_LATITUDE: TEST_LATITUDE,
        CONF_LONGITUDE: TEST_LONGITUDE,
    }


async def test_user_flow_entity_success(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
) -> None:
    """Test full user config flow using a location entity."""
    hass.states.async_set(
        "zone.home",
        "zoning",
        {CONF_LATITUDE: TEST_LATITUDE, CONF_LONGITUDE: TEST_LONGITUDE},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == LOCATION_TYPE_ENTITY

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_ENTITY_ID: "zone.home"},
    )
    await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_NAME
    assert result3["data"] == {
        CONF_API_KEY: TEST_API_KEY,
        CONF_NAME: TEST_NAME,
        CONF_LANG: DEFAULT_LANG,
        CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
        CONF_ENTITY_ID: "zone.home",
    }


@pytest.mark.parametrize(
    ("status", "exc", "expected_error"),
    [
        (HTTPStatus.UNAUTHORIZED, None, "invalid_api_key"),
        (HTTPStatus.FORBIDDEN, None, "unknown_error"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, None, "unknown_error"),
        (HTTPStatus.OK, TimeoutError("timed out"), "cannot_connect"),
        (
            HTTPStatus.OK,
            aiohttp.ClientConnectionError(f"failed with key {TEST_API_KEY}"),
            "cannot_connect",
        ),
    ],
)
async def test_user_flow_api_key_validation_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    status: HTTPStatus,
    exc: Exception | None,
    expected_error: str,
) -> None:
    """Test API key validation error handling and API key redaction in logs."""
    aioclient_mock.get(URL_CURRENT_PATTERN, status=status, exc=exc)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": expected_error}
    assert TEST_API_KEY not in caplog.text


@pytest.mark.parametrize(
    ("existing_name", "new_name"),
    [
        ("My Home", "My Home"),
        ("My Home", "my home"),
        ("My Home", "my_home"),
    ],
)
async def test_user_flow_duplicate_name(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    existing_name: str,
    new_name: str,
) -> None:
    """Test duplicate location name detection (exact, case-insensitive, and slug)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=existing_name,
        unique_id=f"{DOMAIN}-{existing_name.lower()}",
        data={
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: existing_name,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: new_name,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {CONF_NAME: "already_configured"}


async def test_latlong_step_invalid_coordinates(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
) -> None:
    """Test invalid coordinates in the latlong step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        },
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_LATITUDE: 95.0,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
    )
    assert result3["type"] is FlowResultType.FORM
    assert result3["step_id"] == LOCATION_TYPE_LATLONG
    assert result3["errors"] == {"base": "invalid_coordinates"}


async def test_entity_step_validation_errors(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
) -> None:
    """Test missing entity, missing attributes, and invalid coordinates on entity step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
        },
    )

    # 1. Entity does not exist
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_ENTITY_ID: "zone.missing"},
    )
    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {"base": "invalid_location_entity"}

    # 2. Entity exists but has no latitude/longitude attributes
    hass.states.async_set("zone.no_coords", "zoning", {})
    result4 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_ENTITY_ID: "zone.no_coords"},
    )
    assert result4["type"] is FlowResultType.FORM
    assert result4["errors"] == {"base": "invalid_location_entity"}

    # 3. Entity has out-of-range coordinates
    hass.states.async_set(
        "zone.bad_coords",
        "zoning",
        {CONF_LATITUDE: 120.0, CONF_LONGITUDE: -84.39},
    )
    result5 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_ENTITY_ID: "zone.bad_coords"},
    )
    assert result5["type"] is FlowResultType.FORM
    assert result5["errors"] == {"base": "invalid_coordinates"}


async def test_reconfigure_flow_entity_to_latlong_and_back(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
) -> None:
    """Test reconfigure flow replaces stale location keys and preserves custom title."""
    hass.states.async_set(
        "zone.home",
        "zoning",
        {CONF_LATITUDE: TEST_LATITUDE, CONF_LONGITUDE: TEST_LONGITUDE},
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Custom Weather Title",
        unique_id=f"{DOMAIN}-{TEST_NAME.lower()}",
        data={
            CONF_API_KEY: "old_key",
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
            CONF_ENTITY_ID: "zone.home",
        },
    )
    entry.add_to_hass(hass)

    # Reconfigure from entity -> latlong
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_LANG: "fr-FR",
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == LOCATION_TYPE_LATLONG

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
    )
    await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reconfigure_successful"
    assert entry.title == "Custom Weather Title"
    assert entry.data == {
        CONF_API_KEY: TEST_API_KEY,
        CONF_NAME: TEST_NAME,
        CONF_LANG: "fr-FR",
        CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        CONF_LATITUDE: TEST_LATITUDE,
        CONF_LONGITUDE: TEST_LONGITUDE,
    }
    assert CONF_ENTITY_ID not in entry.data

    # Reconfigure from latlong -> entity
    result4 = await entry.start_reconfigure_flow(hass)
    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        {
            CONF_API_KEY: TEST_API_KEY,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
        },
    )
    assert result5["type"] is FlowResultType.FORM
    assert result5["step_id"] == LOCATION_TYPE_ENTITY

    result6 = await hass.config_entries.flow.async_configure(
        result5["flow_id"],
        {CONF_ENTITY_ID: "zone.home"},
    )
    await hass.async_block_till_done()

    assert result6["type"] is FlowResultType.ABORT
    assert result6["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_API_KEY: TEST_API_KEY,
        CONF_NAME: TEST_NAME,
        CONF_LANG: DEFAULT_LANG,
        CONF_LOCATION_SOURCE: LOCATION_TYPE_ENTITY,
        CONF_ENTITY_ID: "zone.home",
    }
    assert CONF_LATITUDE not in entry.data
    assert CONF_LONGITUDE not in entry.data


async def test_reconfigure_flow_api_key_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure flow surfaces API key validation error."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(URL_CURRENT_PATTERN, status=HTTPStatus.UNAUTHORIZED)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: "bad_key",
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "reconfigure"
    assert result2["errors"] == {"base": "invalid_api_key"}


async def test_options_flow_auto_enables_and_disables_forecast_details(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test options flow auto-enables and disables the Forecast Details sensor."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    unique_id = get_sensor_unique_id(TEST_NAME, FIELD_VALIDTIMEUTC)
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None

    entry_before = ent_reg.async_get(entity_id)
    assert entry_before is not None
    assert entry_before.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    # Select extra attributes -> entity should be auto-enabled
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_EXTRA_ATTRIBUTES

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "daily_attributes": ["day", "sunrise"],
            "day_attributes": ["day_icon_code"],
            "daypart_attributes": ["daypart_name"],
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_EXTRA_ATTRIBUTES] == [
        "day",
        "sunrise",
        "day_icon_code",
        "daypart_name",
    ]
    entry_enabled = ent_reg.async_get(entity_id)
    assert entry_enabled is not None
    assert entry_enabled.disabled_by is None

    # Clear all extra attributes -> entity should be auto-disabled again
    result3 = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"],
        {
            "daily_attributes": [],
            "day_attributes": [],
            "daypart_attributes": [],
        },
    )
    await hass.async_block_till_done()

    assert result4["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_EXTRA_ATTRIBUTES] == []
    entry_disabled = ent_reg.async_get(entity_id)
    assert entry_disabled is not None
    assert entry_disabled.disabled_by == er.RegistryEntryDisabler.INTEGRATION
