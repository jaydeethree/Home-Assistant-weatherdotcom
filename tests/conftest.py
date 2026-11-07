"""Common fixtures for Weather.com integration tests."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.weatherdotcom.const import (
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DEFAULT_LANG,
    DOMAIN,
    LOCATION_TYPE_LATLONG,
    RESOURCE_CURRENT,
    RESOURCE_FORECAST_DAILY,
    RESOURCE_FORECAST_HOURLY,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TEST_API_KEY = "test_api_key_12345"
TEST_NAME = "Home"
TEST_LATITUDE = 33.74
TEST_LONGITUDE = -84.39

URL_CURRENT_PATTERN = re.compile(rf"^{re.escape(RESOURCE_CURRENT)}\b")
URL_DAILY_PATTERN = re.compile(rf"^{re.escape(RESOURCE_FORECAST_DAILY)}\b")
URL_HOURLY_PATTERN = re.compile(rf"^{re.escape(RESOURCE_FORECAST_HOURLY)}\b")


def _load_json_fixture(filename: str) -> dict[str, Any]:
    """Load and parse a JSON fixture file."""
    return json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))


_RAW_CURRENT = _load_json_fixture("current.json")
_RAW_DAILY_15DAY = _load_json_fixture("daily_15day.json")
_RAW_DAILY_DAYPART_EXPIRED = _load_json_fixture("daily_daypart_expired.json")
_RAW_HOURLY_15DAY = _load_json_fixture("hourly_15day.json")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def fast_retry_sleep() -> Generator[AsyncMock]:
    """Patch coordinator retry sleep so error/retry tests run instantly."""
    with patch(
        "custom_components.weatherdotcom.coordinator.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        yield mock_sleep


@pytest.fixture
def current_json() -> dict[str, Any]:
    """Return a fresh copy of the current observations fixture."""
    return copy.deepcopy(_RAW_CURRENT)


@pytest.fixture
def daily_15day_json() -> dict[str, Any]:
    """Return a fresh copy of the 15-day daily forecast fixture."""
    return copy.deepcopy(_RAW_DAILY_15DAY)


@pytest.fixture
def daily_daypart_expired_json() -> dict[str, Any]:
    """Return a fresh copy of the evening (expired daypart 0) daily fixture."""
    return copy.deepcopy(_RAW_DAILY_DAYPART_EXPIRED)


@pytest.fixture
def hourly_15day_json() -> dict[str, Any]:
    """Return a fresh copy of the 15-day hourly forecast fixture."""
    return copy.deepcopy(_RAW_HOURLY_15DAY)


@pytest.fixture
def mock_weather_api(
    aioclient_mock: AiohttpClientMocker,
    current_json: dict[str, Any],
    daily_15day_json: dict[str, Any],
    hourly_15day_json: dict[str, Any],
) -> AiohttpClientMocker:
    """Mock all three Weather.com API endpoints with valid fixture responses."""
    aioclient_mock.get(URL_CURRENT_PATTERN, json=current_json)
    aioclient_mock.get(URL_DAILY_PATTERN, json=daily_15day_json)
    aioclient_mock.get(URL_HOURLY_PATTERN, json=hourly_15day_json)
    return aioclient_mock


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a default MockConfigEntry for the Weather.com integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_NAME,
        unique_id="home",
        data={
            CONF_API_KEY: TEST_API_KEY,
            CONF_NAME: TEST_NAME,
            CONF_LANG: DEFAULT_LANG,
            CONF_LOCATION_SOURCE: LOCATION_TYPE_LATLONG,
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
        options={},
    )
