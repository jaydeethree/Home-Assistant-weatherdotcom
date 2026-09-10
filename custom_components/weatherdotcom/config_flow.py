"""Config Flow to configure Weather.com Integration."""
from __future__ import annotations
import logging
from http import HTTPStatus
import async_timeout
import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    DOMAIN,
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DEFAULT_LANG,
    LANG_CODES,
    LOCATION_TYPE_ENTITY,
    LOCATION_TYPE_LATLONG
)

_LOGGER = logging.getLogger(__name__)


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid api key."""


class WeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Weather.com config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Handle the first step initiated by the user."""
        errors = {}
        if user_input is not None:
            self._data = user_input
            if user_input.get(CONF_LOCATION_SOURCE) == LOCATION_TYPE_LATLONG:
                return await self.async_step_latlong()
            return await self.async_step_entity()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(
                        CONF_NAME,
                        default=self.hass.config.location_name,
                    ): str,
                    vol.Required(
                        CONF_LANG,
                        default=DEFAULT_LANG,
                    ): vol.All(vol.In(LANG_CODES)),
                    vol.Required(CONF_LOCATION_SOURCE, default=LOCATION_TYPE_LATLONG): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": LOCATION_TYPE_ENTITY, "label": "Entity (zone, device_tracker, or person)"},
                                {"value": LOCATION_TYPE_LATLONG, "label": "Latitude/longitude"},
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_latlong(self, user_input=None):
        """Handle the second step for latitude/longitude."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self._async_validate_and_create()

        default_latitude = self.hass.config.latitude
        default_longitude = self.hass.config.longitude

        if self.source == config_entries.SOURCE_RECONFIGURE:
            conf_entry = self._get_reconfigure_entry()
            default_latitude = conf_entry.data.get(
                CONF_LATITUDE,
                default_latitude,
            )
            default_longitude = conf_entry.data.get(
                CONF_LONGITUDE,
                default_longitude,
            )

        return self.async_show_form(
            step_id=LOCATION_TYPE_LATLONG,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LATITUDE,
                        default=default_latitude,
                    ): float,
                    vol.Required(
                        CONF_LONGITUDE,
                        default=default_longitude,
                    ): float,
                }
            ),
            errors=errors,
        )

    async def async_step_entity(self, user_input=None):
        """Handle the second step for tracking entities."""
        errors = {}

        if user_input is not None:
            state = self.hass.states.get(user_input[CONF_ENTITY_ID])
            if (
                state is None
                or "latitude" not in state.attributes
                or "longitude" not in state.attributes
            ):
                errors["base"] = "invalid_location_entity"
            else:
                self._data.update(user_input)
                return await self._async_validate_and_create()

        default_entity = None

        if self.source == config_entries.SOURCE_RECONFIGURE:
            conf_entry = self._get_reconfigure_entry()
            default_entity = conf_entry.data.get(CONF_ENTITY_ID)

        return self.async_show_form(
            step_id=LOCATION_TYPE_ENTITY,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTITY_ID,
                        default=default_entity,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["zone", "device_tracker", "person"]
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_validate_and_create(self):
        """Validate API key and lat/long, then create the config entry."""
        errors = {}
        session = async_create_clientsession(self.hass)

        api_key = self._data[CONF_API_KEY]
        location_name = self._data[CONF_NAME]
        location_source = self._data.get(CONF_LOCATION_SOURCE)

        if location_source == LOCATION_TYPE_LATLONG:
            latitude = self._data[CONF_LATITUDE]
            longitude = self._data[CONF_LONGITUDE]
        else:
            entity_id = self._data[CONF_ENTITY_ID]
            state = self.hass.states.get(entity_id)
            raw_lat = state.attributes[CONF_LATITUDE]
            raw_lon = state.attributes[CONF_LONGITUDE]
            # Obfuscate location by up to 0.01 degrees (1.1km)
            latitude, longitude = (
                round(float(raw_lat), 2),
                round(float(raw_lon), 2)
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
                _LOGGER.error(
                    "Weather.com config responded with HTTP error %s: %s",
                    response.status,
                    response.reason,
                )
                if response.status == HTTPStatus.UNAUTHORIZED:
                    raise InvalidApiKey
                raise Exception

        except InvalidApiKey:
            errors["base"] = "invalid_api_key"
            return await self._show_appropriate_form(errors)

        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown_error"
            return await self._show_appropriate_form(errors)

        entry_data = {
            CONF_API_KEY: api_key,
            CONF_NAME: location_name,
            CONF_LANG: self._data[CONF_LANG],
            CONF_LOCATION_SOURCE: location_source,
        }

        if location_source == LOCATION_TYPE_LATLONG:
            entry_data[CONF_LATITUDE] = self._data[CONF_LATITUDE]
            entry_data[CONF_LONGITUDE] = self._data[CONF_LONGITUDE]

            unique_id = str(f"{DOMAIN}-{location_name}")
        else:
            entry_data[CONF_ENTITY_ID] = self._data[CONF_ENTITY_ID]

            unique_id = (
                f"{DOMAIN}-entity-{self._data[CONF_ENTITY_ID]}"
            )

        if self.source == config_entries.SOURCE_RECONFIGURE:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                title=location_name,
                data_updates=entry_data,
            )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=location_name,
            data=entry_data,
        )

    async def _show_appropriate_form(self, errors):
        """Return the correct form based on user selection when errors occur."""
        if 'base' in errors and 'invalid_api_key' in errors["base"]:
            return await self.async_step_user()
        if self._data.get(CONF_LOCATION_SOURCE) == LOCATION_TYPE_LATLONG:
            return await self.async_step_latlong()
        return await self.async_step_entity()


    async def async_step_reconfigure(self, user_input=None):
        """Handle a reconfiguration flow initialized by the user."""
        errors = {}
        conf_entry = self._get_reconfigure_entry()

        if user_input is not None:
            self._data = dict(user_input)
            self._data[CONF_NAME] = conf_entry.title

            # Branch based on the selected location source.
            if user_input.get(CONF_LOCATION_SOURCE) == LOCATION_TYPE_LATLONG:
                return await self.async_step_latlong()

            return await self.async_step_entity()

        # Determine default location source from existing config, falling back to entity.
        default_source = conf_entry.data.get(CONF_LOCATION_SOURCE, LOCATION_TYPE_LATLONG)

        if (
            CONF_LATITUDE in conf_entry.data
            and CONF_LONGITUDE in conf_entry.data
            and CONF_ENTITY_ID not in conf_entry.data
        ):
            default_source = LOCATION_TYPE_LATLONG

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=conf_entry.data.get(CONF_API_KEY, ""),
                    ): str,
                    vol.Required(
                        CONF_LANG,
                        default=conf_entry.data.get(
                            CONF_LANG,
                            DEFAULT_LANG,
                        ),
                    ): vol.All(vol.In(LANG_CODES)),
                    vol.Required(
                        CONF_LOCATION_SOURCE,
                        default=default_source,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[LOCATION_TYPE_LATLONG, LOCATION_TYPE_ENTITY],
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key="location_source_options"
                        )
                    ),
                }
            ),
            errors=errors,
        )

