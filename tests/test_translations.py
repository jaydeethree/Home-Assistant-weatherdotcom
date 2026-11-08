"""Tests for Weather.com translation and icon files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.generated.languages import LANGUAGES
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.weatherdotcom.const import DOMAIN
from custom_components.weatherdotcom.sensor_descriptions import (
    current_condition_sensor_descriptions,
)

COMPONENT_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "weatherdotcom"
)
TRANSLATIONS_DIR = COMPONENT_DIR / "translations"


def _load_json(path: Path) -> dict[str, Any]:
    """Load and parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_key_paths(data: dict[str, Any], prefix: str = "") -> set[str]:
    """Recursively collect all dotted key paths in a nested dictionary."""
    paths: set[str] = set()
    for key, value in data.items():
        current = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.update(_collect_key_paths(value, current))
        else:
            paths.add(current)
    return paths


def _collect_leaf_values(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Recursively collect all leaf values by dotted key path."""
    leaves: dict[str, Any] = {}
    for key, value in data.items():
        current = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            leaves.update(_collect_leaf_values(value, current))
        else:
            leaves[current] = value
    return leaves


def test_strings_matches_en_translation() -> None:
    """Test that strings.json and translations/en.json are identical."""
    strings = _load_json(COMPONENT_DIR / "strings.json")
    en_translations = _load_json(TRANSLATIONS_DIR / "en.json")
    assert strings == en_translations


def test_all_translations_match_strings_keys_and_valid_ha_locales() -> None:
    """Test that every translation file is a valid HA locale and matches strings.json keys."""
    strings = _load_json(COMPONENT_DIR / "strings.json")
    expected_keys = _collect_key_paths(strings)

    translation_files = sorted(TRANSLATIONS_DIR.glob("*.json"))
    assert len(translation_files) >= 15

    for translation_file in translation_files:
        assert translation_file.stem in LANGUAGES, (
            f"{translation_file.name} is not a recognized Home Assistant language code "
            f"(stem={translation_file.stem!r})"
        )
        data = _load_json(translation_file)
        actual_keys = _collect_key_paths(data)
        assert actual_keys == expected_keys, (
            f"Key mismatch in {translation_file.name}: "
            f"missing={expected_keys - actual_keys}, "
            f"extra={actual_keys - expected_keys}"
        )
        for key_path, value in _collect_leaf_values(data).items():
            assert isinstance(value, str) and value.strip(), (
                f"Empty translation value at {key_path} in {translation_file.name}"
            )


def test_sensor_translation_keys_and_icons() -> None:
    """Test that all sensor descriptions have matching entries in strings.json and icons.json."""
    strings = _load_json(COMPONENT_DIR / "strings.json")
    icons = _load_json(COMPONENT_DIR / "icons.json")

    description_keys = {
        desc.translation_key
        for desc in current_condition_sensor_descriptions
        if desc.translation_key is not None
    }
    assert len(description_keys) == len(current_condition_sensor_descriptions)

    string_sensor_keys = set(strings["entity"]["sensor"].keys())
    icon_sensor_keys = set(icons["entity"]["sensor"].keys())

    assert description_keys == string_sensor_keys
    assert description_keys == icon_sensor_keys


def test_exception_translation_keys() -> None:
    """Test that translated exception keys exist in strings.json."""
    strings = _load_json(COMPONENT_DIR / "strings.json")
    assert set(strings["exceptions"].keys()) == {
        "cannot_retrieve_coordinates",
        "update_failed",
    }


@pytest.mark.parametrize(
    ("lang", "expected_api_key_label", "expected_temp_name"),
    [
        ("zh-Hans", "API 密钥", "Home 温度"),
        ("zh-Hant", "API 金鑰", "Home 溫度"),
        ("es-419", "Clave de API", "Home Temperatura"),
        ("pt-BR", "Chave de API", "Home Temperatura"),
        ("de", "API-Schlüssel", "Home Temperatur"),
    ],
)
async def test_ha_loads_form_and_sensor_translations(
    hass: HomeAssistant,
    mock_weather_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    lang: str,
    expected_api_key_label: str,
    expected_temp_name: str,
) -> None:
    """Test that Home Assistant loads form and entity translations for regional locales."""
    hass.config.language = lang
    config_translations = await async_get_translations(
        hass, lang, "config", {DOMAIN}, config_flow=True
    )
    assert (
        config_translations[f"component.{DOMAIN}.config.step.user.data.api_key"]
        == expected_api_key_label
    )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    temp_state = hass.states.get("sensor.home_temperature")
    assert temp_state is not None
    assert temp_state.attributes["friendly_name"] == expected_temp_name
