"""Config Flow to configure Weather.com Integration."""
from __future__ import annotations
import logging
from http import HTTPStatus
import async_timeout
import voluptuous as vol
import math
import random
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    DOMAIN,
    CONF_LANG,
    DEFAULT_LANG,
    LANG_CODES
)

_LOGGER = logging.getLogger(__name__)

class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid api key."""

def _apply_random_offset(lat: float, lon: float) -> tuple[float, float]:
    """Apply a random offset between a maximum and minimum radius."""
    max_radius_m = 1000
    min_radius_m = 600
    seed_string = f"{lat}_{lon}_{max_radius_m}_weather_secret"
    rng = random.Random(seed_string)
    distance = rng.uniform(min_radius_m, max_radius_m)
    angle = rng.uniform(0, 2 * math.pi)
    dx = distance * math.cos(angle)
    dy = distance * math.sin(angle)
    delta_lat = dy / 111111.0
    delta_lon = dx / (111111.0 * math.cos(math.radians(lat)))
    return round(lat + delta_lat, 6), round(lon + delta_lon, 6)

class WeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Weather.com config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form()

        errors = {}
        session = async_create_clientsession(self.hass)

        api_key = user_input[CONF_API_KEY]
        location_name = user_input[CONF_NAME]
        entity_id = user_input[CONF_ENTITY_ID]

        # Fetch the entity state to get initial coordinates
        state = self.hass.states.get(entity_id)

        if (
            state is None
            or "latitude" not in state.attributes
            or "longitude" not in state.attributes
        ):
            errors["base"] = "invalid_location_entity"
            return await self._show_setup_form(errors)

        raw_lat = state.attributes["latitude"]
        raw_lon = state.attributes["longitude"]

        latitude, longitude = _apply_random_offset(
            float(raw_lat), float(raw_lon)
        )

        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }

        try:
            if not api_key:
                errors["base"] = "invalid_api_key"
                raise InvalidApiKey

            async with async_timeout.timeout(10):
                # Use English and US units for the initial test API call. User-supplied units and language will be used for
                # the created entities.
                url = f'https://api.weather.com/v3/wx/observations/current?geocode={latitude},{longitude}&format=json&units=e' \
                      f'&apiKey={api_key}&language=en-US'

                response = await session.get(url, headers=headers)

            if response.status != HTTPStatus.OK:
                if response.status == HTTPStatus.UNAUTHORIZED:
                    _LOGGER.error(
                        "Weather.com config responded with HTTP error %s: %s",
                        response.status,
                        response.reason,
                    )
                    raise InvalidApiKey

                _LOGGER.error(
                    "Weather.com config responded with HTTP error %s: %s",
                    response.status,
                    response.reason,
                )
                raise Exception

        except InvalidApiKey:
            errors["base"] = "invalid_api_key"
            return await self._show_setup_form(errors)

        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown_error"
            return await self._show_setup_form(errors)

        result_current = await response.json(content_type=None)

        unique_id = f"{DOMAIN}-{location_name}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=location_name,
            data={
                CONF_API_KEY: api_key,
                CONF_ENTITY_ID: entity_id,
                CONF_NAME: location_name,
                CONF_LANG: user_input[CONF_LANG],
            },
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle a reconfiguration flow initialized by the user."""
        errors = {}
        conf_entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                conf_entry,
                title=user_input.get(CONF_NAME, conf_entry.title),
                data={
                    **conf_entry.data,
                    CONF_API_KEY: user_input[CONF_API_KEY],
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_ENTITY_ID: user_input[CONF_ENTITY_ID],
                    CONF_LANG: user_input[CONF_LANG],
                    CONF_LATITUDE: None,
                    CONF_LONGITUDE: None,
                },
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=conf_entry.data.get(CONF_API_KEY, ""),
                    ): str,

                    vol.Required(
                        CONF_NAME,
                        default=conf_entry.title,
                    ): str,

                    vol.Required(
                        CONF_ENTITY_ID,
                        default=conf_entry.data.get(
                            CONF_ENTITY_ID,
                            vol.UNDEFINED,
                        ),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["zone", "device_tracker", "person"]
                        )
                    ),

                    vol.Required(
                        CONF_LANG,
                        default=conf_entry.data.get(
                            CONF_LANG,
                            DEFAULT_LANG,
                        ),
                    ): vol.All(vol.In(LANG_CODES)),
                }
            ),
            errors=errors,
        )

    async def _show_setup_form(self, errors=None):
        """Show the initial setup form."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,

                    vol.Required(
                        CONF_NAME,
                        default=self.hass.config.location_name,
                    ): str,

                    vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["zone", "device_tracker", "person"]
                        )
                    ),

                    vol.Required(
                        CONF_LANG,
                        default=DEFAULT_LANG,
                    ): vol.All(vol.In(LANG_CODES)),
                }
            ),
            errors=errors or {},
        )
