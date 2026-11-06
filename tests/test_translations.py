"""Tests for Weather.com translation and icon files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def test_all_translations_match_strings_keys() -> None:
    """Test that every translation file has the exact same key set as strings.json."""
    strings = _load_json(COMPONENT_DIR / "strings.json")
    expected_keys = _collect_key_paths(strings)

    translation_files = sorted(TRANSLATIONS_DIR.glob("*.json"))
    assert len(translation_files) >= 12

    for translation_file in translation_files:
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
