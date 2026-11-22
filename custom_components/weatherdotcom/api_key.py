"""Retrieve and validate the public Weather.com API key."""

from __future__ import annotations

import asyncio
import logging
import re
from http import HTTPStatus

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import HEADERS, RESOURCE_CURRENT, RESOURCE_WUNDERGROUND

_LOGGER = logging.getLogger(__name__)

# Matches "API_KEY":"<32-hex>" (including Angular &q; escaping) or
# api.weather.com?...apiKey=<32-hex> (including &a;, &amp;, & escaping)
API_KEY_PATTERN = re.compile(
    r'(?:(?:["\']|&q;)API_KEY(?:["\']|&q;)\s*:\s*(?:["\']|&q;)'
    r'|api\.weather\.com[^"\'\s<>]*?(?:[?&]|&a;|&amp;|\\u0026)apiKey=)'
    r"([0-9a-fA-F]{32})"
)


async def async_extract_api_key(hass: HomeAssistant) -> str | None:
    """Attempt to extract the public Weather.com API key from Wunderground."""
    session = async_get_clientsession(hass)
    headers = {"User-Agent": HEADERS["user-agent"]}
    try:
        async with (
            asyncio.timeout(10),
            session.get(RESOURCE_WUNDERGROUND, headers=headers) as response,
        ):
            status = response.status
            if status != HTTPStatus.OK:
                _LOGGER.warning(
                    "Could not retrieve API key from Wunderground (HTTP %s)",
                    status,
                )
                return None
            html = await response.text(errors="replace")
    except TimeoutError, aiohttp.ClientError:
        _LOGGER.warning("Error connecting to Wunderground to retrieve API key")
        return None

    if match := API_KEY_PATTERN.search(html):
        return match.group(1)

    _LOGGER.warning("Could not find Weather.com API key in Wunderground page")
    return None


async def async_validate_api_key(
    hass: HomeAssistant, api_key: str | None
) -> str | None:
    """Validate the API key against the Weather.com endpoint.

    Returns None when the key works, otherwise an error key.
    """
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(10):
            # Use hardcoded values for the test API call. User-supplied values
            # are used for the created entities.
            params = {
                "geocode": "37.3355,-121.8930",
                "format": "json",
                "units": "e",
                "apiKey": api_key or "",
                "language": "en-US",
            }
            async with session.get(
                RESOURCE_CURRENT, params=params, headers=HEADERS
            ) as response:
                status = response.status
                reason = response.reason
    except (TimeoutError, aiohttp.ClientError) as err:
        err_msg = str(err).replace(api_key, "REDACTED") if api_key else str(err)
        _LOGGER.error(
            "Error connecting to Weather.com to validate API key: %s", err_msg
        )
        return "cannot_connect"

    if status != HTTPStatus.OK:
        _LOGGER.error(
            "Weather.com responded with HTTP error %s while validating API key: %s",
            status,
            reason,
        )
        if status == HTTPStatus.UNAUTHORIZED:
            return "invalid_api_key"
        return "unknown_error"

    return None
