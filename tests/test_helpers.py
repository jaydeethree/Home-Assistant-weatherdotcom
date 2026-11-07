"""Tests for Weather.com helper functions and static methods."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
)

from custom_components.weatherdotcom.const import ICON_CODE_MAP
from custom_components.weatherdotcom.coordinator import WeatherUpdateCoordinator
from custom_components.weatherdotcom.helpers import (
    clean_wind_bearing,
    get_first_daypart_index,
    get_sensor_unique_id,
)


@pytest.mark.parametrize(
    ("location_name", "key", "expected"),
    [
        ("Home", "temperature", "home,temperature"),
        ("My Home", "validTimeUtc", "my home,validtimeutc"),
        ("Atlanta", "wxPhraseLong", "atlanta,wxphraselong"),
    ],
)
def test_get_sensor_unique_id(location_name: str, key: str, expected: str) -> None:
    """Test building sensor unique IDs."""
    assert get_sensor_unique_id(location_name, key) == expected


@pytest.mark.parametrize(
    ("daily_data", "expected"),
    [
        (None, 0),
        ({}, 0),
        ({"daypart": None}, 0),
        ({"daypart": []}, 0),
        ({"daypart": ["not_a_dict"]}, 0),
        ({"daypart": [{}]}, 0),
        ({"daypart": [{"temperature": []}]}, 0),
        ({"daypart": [{"temperature": [72, 55]}]}, 0),
        ({"daypart": [{"temperature": [0, 55]}]}, 0),
        ({"daypart": [{"temperature": [None, 55]}]}, 1),
    ],
)
def test_get_first_daypart_index(
    daily_data: dict[str, Any] | None, expected: int
) -> None:
    """Test determining the first valid daypart index."""
    assert get_first_daypart_index(daily_data) == expected


@pytest.mark.parametrize(
    ("direction", "cardinal", "speed", "expected"),
    [
        (180, "S", 10, 180),
        (225.5, "SW", 5.2, 225.5),
        (0, "N", 5, 0),
        (180, None, None, 180),
        (180, "CALM", 5, None),
        (180, "calm", 5, None),
        (180, "Calm", None, None),
        (180, "N", 0, None),
        (180, "N", 0.0, None),
        (0, None, 0, None),
        (None, "N", 10, None),
        ("180", "S", 10, None),
    ],
)
def test_clean_wind_bearing(
    direction: Any,
    cardinal: str | None,
    speed: float | None,
    expected: float | int | None,
) -> None:
    """Test cleaning wind bearing values for calm or invalid conditions."""
    assert clean_wind_bearing(direction, cardinal=cardinal, speed=speed) == expected


@pytest.mark.parametrize(
    ("icon_code", "expected"),
    [
        (None, None),
        (44, None),
        (31, ATTR_CONDITION_CLEAR_NIGHT),
        (26, ATTR_CONDITION_CLOUDY),
        (0, ATTR_CONDITION_EXCEPTIONAL),
        (20, ATTR_CONDITION_FOG),
        (17, ATTR_CONDITION_HAIL),
        (4, ATTR_CONDITION_LIGHTNING_RAINY),
        (29, ATTR_CONDITION_PARTLYCLOUDY),
        (40, ATTR_CONDITION_POURING),
        (11, ATTR_CONDITION_RAINY),
        (16, ATTR_CONDITION_SNOWY),
        (5, ATTR_CONDITION_SNOWY_RAINY),
        (32, ATTR_CONDITION_SUNNY),
        (24, ATTR_CONDITION_WINDY),
    ],
)
def test_iconcode_to_condition(icon_code: int | None, expected: str | None) -> None:
    """Test mapping Weather.com icon codes to Home Assistant conditions."""
    assert WeatherUpdateCoordinator.iconcode_to_condition(icon_code) == expected


def test_all_mapped_icon_codes_resolve() -> None:
    """Test that every icon code in ICON_CODE_MAP resolves to its condition."""
    for code, condition in ICON_CODE_MAP.items():
        assert WeatherUpdateCoordinator.iconcode_to_condition(code) == condition


def test_unmapped_icon_code_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Test that an unknown icon code returns None and logs a warning."""
    assert WeatherUpdateCoordinator.iconcode_to_condition(999) is None
    assert "Unmapped icon code from Weather.com API: 999" in caplog.text


@pytest.mark.parametrize(
    ("timestamp_secs", "expected"),
    [
        (0, "1970-01-01T00:00:00Z"),
        (1700000000, "2023-11-14T22:13:20Z"),
        (1700000000.0, "2023-11-14T22:13:20Z"),
    ],
)
def test_format_timestamp(timestamp_secs: int | float, expected: str) -> None:
    """Test formatting UTC timestamps as ISO 8601 strings."""
    assert WeatherUpdateCoordinator.format_timestamp(timestamp_secs) == expected
