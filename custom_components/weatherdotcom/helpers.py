"""Helper functions for the Weather.com integration."""
from __future__ import annotations


def get_sensor_unique_id(location_name: str, key: str) -> str:
    """Build the unique_id for a Weather.com sensor."""
    return f"{location_name},{key}".lower()
