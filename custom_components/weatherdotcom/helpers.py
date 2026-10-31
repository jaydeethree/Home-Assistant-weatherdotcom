"""Helper functions for the Weather.com integration."""
from __future__ import annotations

from typing import Any

from .const import FIELD_DAYPART, FIELD_TEMP


def get_sensor_unique_id(location_name: str, key: str) -> str:
    """Build the unique_id for a Weather.com sensor."""
    return f"{location_name},{key}".lower()


def get_first_daypart_index(daily_data: dict[str, Any] | None) -> int:
    """Return 1 if today's daytime daypart (index 0) has expired, else 0."""
    if isinstance(daily_data, dict):
        dayparts = daily_data.get(FIELD_DAYPART)
        if isinstance(dayparts, list) and dayparts and isinstance(dayparts[0], dict):
            temps = dayparts[0].get(FIELD_TEMP)
            if isinstance(temps, list) and temps and temps[0] is None:
                return 1
    return 0

