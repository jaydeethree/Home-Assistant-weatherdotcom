"""Config Flow to configure Weather.com Integration."""
from __future__ import annotations
import logging
from http import HTTPStatus
import async_timeout
import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from .coordinator import InvalidApiKey

from .const import (
    DOMAIN, CONF_LANG,
    DEFAULT_LANG, LANG_CODES, FIELD_LONGITUDE, FIELD_LATITUDE,
    CONF_FORECAST_SENSORS, DEFAULT_FORECAST_SENSORS
)

_LOGGER = logging.getLogger(__name__)


class WeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Weather.com config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}
        session = async_create_clientsession(self.hass)

        api_key = user_input[CONF_API_KEY]
        latitude = user_input[CONF_LATITUDE]
        longitude = user_input[CONF_LONGITUDE]
        location_name = user_input[CONF_NAME]
        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        try:
            if user_input[CONF_API_KEY] is None or user_input[CONF_API_KEY] == "":
                errors["base"] = "invalid_api_key"
                raise InvalidApiKey

            with async_timeout.timeout(10):
                url = f'https://api.weather.com/v3/wx/observations/current?geocode={latitude},{longitude}&format=json&units=e' \
                      f'&apiKey={api_key}&language=en-US'
                response = await session.get(url, headers=headers)
            # _LOGGER.debug(response.status)
            if response.status != HTTPStatus.OK:
                # 401 status is most likely bad api_key or api usage limit exceeded
                if response.status == HTTPStatus.UNAUTHORIZED:
                    _LOGGER.error(
                        "Weather.com config responded with HTTP error %s: %s",
                        response.status,
                        response.reason,
                    )
                    raise InvalidApiKey
                else:
                    _LOGGER.error(
                        "Weather.com config responded with HTTP error %s: %s",
                        response.status,
                        response.reason,
                    )
                    raise Exception

        except InvalidApiKey:
            errors["base"] = "invalid_api_key"
            return await self._show_setup_form(errors=errors)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown_error"
            return await self._show_setup_form(errors=errors)

        if not errors:
            result_current = await response.json()

            unique_id = str(f"{DOMAIN}-{location_name}")
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=location_name,
                data={
                    CONF_API_KEY: user_input[CONF_API_KEY],
                },
                options={
                    CONF_LATITUDE: latitude,
                    CONF_LONGITUDE: longitude,
                    CONF_NAME: location_name,
                    CONF_LANG: DEFAULT_LANG,
                    CONF_FORECAST_SENSORS: DEFAULT_FORECAST_SENSORS
                },
            )

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(
                        CONF_LATITUDE, default=self.hass.config.latitude
                    ): cv.latitude,
                    vol.Required(
                        CONF_LONGITUDE, default=self.hass.config.longitude
                    ): cv.longitude,
                    vol.Required(
                        CONF_NAME, default=self.hass.config.location_name
                    ): str,
                }
            ),
            errors=errors or {},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_FORECAST_SENSORS,
                                 default=self.config_entry.options.get(CONF_FORECAST_SENSORS,
                                                                       DEFAULT_FORECAST_SENSORS)): bool,
                    vol.Optional(CONF_LANG, default=self.config_entry.options.get(CONF_LANG, DEFAULT_LANG)):
                        vol.All(vol.In(LANG_CODES)),
                    vol.Inclusive(CONF_LATITUDE, 'coordinates',
                                  'Latitude and longitude must exist together',
                                  default=self.config_entry.options.get(CONF_LATITUDE)): cv.latitude,
                    vol.Inclusive(CONF_LONGITUDE, 'coordinates',
                                  'Latitude and longitude must exist together',
                                  default=self.config_entry.options.get(CONF_LONGITUDE)): cv.longitude,

                }
            ),
        )
