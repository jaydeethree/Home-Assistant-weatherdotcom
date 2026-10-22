"""Config Flow to configure Weather.com Integration."""
from __future__ import annotations
import asyncio
import logging
import random
from http import HTTPStatus
from typing import Any
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ENTITY_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_LANG,
    CONF_LOCATION_SOURCE,
    DEFAULT_LANG,
    LANG_CODES,
    LOCATION_TYPE_ENTITY,
    LOCATION_TYPE_LATLONG,
    EXTRA_ATTRIBUTE_KEYS_DAILY,
    EXTRA_ATTRIBUTE_KEYS_DAY,
    EXTRA_ATTRIBUTE_KEYS_DAYPART,
    CONF_EXTRA_ATTRIBUTES
)

_LOGGER = logging.getLogger(__name__)


class WeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Weather.com config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return WeatherDotComOptionsFlow()

    async def _async_validate_api_key(self, api_key: str | None) -> str | None:
        """Validate the API key against the Weather.com endpoint."""
        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
        }
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(10):
                # Use hardcoded values for the initial test API call. User-supplied values will be used for the created entities.
                url = "https://api.weather.com/v3/wx/observations/current"
                random_latitude = round(random.uniform(36.0, 41.0), 6)
                random_longitude = round(random.uniform(-120.0, -78.0), 6)
                random_latlong = f"{random_latitude},{random_longitude}"
                params = {
                    "geocode": random_latlong,
                    "format": "json",
                    "units": "e",
                    "apiKey": api_key or "",
                    "language": "en-US",
                }
                async with session.get(url, params=params, headers=headers) as response:
                    status = response.status
                    reason = response.reason
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            err_msg = str(err).replace(api_key, "REDACTED") if api_key else str(err)
            _LOGGER.error("Error connecting to Weather.com during config: %s", err_msg)
            return "unknown_error"

        if status != HTTPStatus.OK:
            _LOGGER.error("Weather.com config responded with HTTP error %s: %s",
                          status, reason,)
            if status == HTTPStatus.UNAUTHORIZED:
                return "invalid_api_key"
            return "unknown_error"

        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the first step initiated by the user."""
        errors = {}
        if user_input is not None:
            self._data = user_input
            if error := await self._async_validate_api_key(user_input.get(CONF_API_KEY)):
                errors["base"] = error
            else:
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
                            options=[LOCATION_TYPE_LATLONG, LOCATION_TYPE_ENTITY],
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key="location_source_options"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_latlong(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step for latitude/longitude."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            if self._validate_latlong(lat=user_input.get(CONF_LATITUDE), long=user_input.get(CONF_LONGITUDE)):
                return await self._async_validate_and_create()
            else:
                errors["base"] = "unknown_error"
                _LOGGER.error("Invalid latitude/longitude: %s, %s",
                              user_input.get(CONF_LATITUDE), user_input.get(CONF_LONGITUDE),)

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

    async def async_step_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step for tracking entities."""
        errors = {}

        if user_input is not None:
            state = self.hass.states.get(user_input[CONF_ENTITY_ID])
            if (
                state is None
                or CONF_LATITUDE not in state.attributes
                or CONF_LONGITUDE not in state.attributes
            ):
                errors["base"] = "invalid_location_entity"
            else:
                self._data.update(user_input)
                if self._validate_latlong(entity=state):
                    return await self._async_validate_and_create()
                else:
                    errors["base"] = "unknown_error"
                    _LOGGER.error("Invalid latitude/longitude: %s, %s",
                                  state.attributes.get(CONF_LATITUDE), state.attributes.get(CONF_LONGITUDE),)

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

    @staticmethod
    def _validate_latlong(lat=None, long=None, entity=None) -> bool:
        """Check if the provided lat/long is valid."""
        if entity:
            lat = entity.attributes[CONF_LATITUDE]
            long = entity.attributes[CONF_LONGITUDE]
        if lat is not None and long is not None:
            if -90 <= lat <= 90 and -180 <= long <= 180:
                return True
        return False

    async def _async_validate_and_create(self) -> ConfigFlowResult:
        """Validate API key and lat/long, then create the config entry."""
        api_key = self._data[CONF_API_KEY]
        location_name = self._data[CONF_NAME]
        location_source = self._data.get(CONF_LOCATION_SOURCE)

        entry_data = {
            CONF_API_KEY: api_key,
            CONF_NAME: location_name,
            CONF_LANG: self._data[CONF_LANG],
            CONF_LOCATION_SOURCE: location_source,
        }

        if location_source == LOCATION_TYPE_LATLONG:
            entry_data[CONF_LATITUDE] = self._data[CONF_LATITUDE]
            entry_data[CONF_LONGITUDE] = self._data[CONF_LONGITUDE]
        else:
            entry_data[CONF_ENTITY_ID] = self._data[CONF_ENTITY_ID]

        unique_id = str(f"{DOMAIN}-{location_name}")

        if self.source == config_entries.SOURCE_RECONFIGURE:
            # Replace (rather than merge) the entry data so that keys from the
            # previous location source (e.g. a stale entity_id after switching
            # to lat/long) do not linger and take precedence. The title is left
            # unchanged so that a user-customized title is preserved.
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data=entry_data,
            )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=location_name,
            data=entry_data,
        )


    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        errors = {}
        conf_entry = self._get_reconfigure_entry()

        if user_input is not None:
            self._data = dict(user_input)
            # Use the stored location name, not the entry title. The title can
            # be renamed by the user, but the location name is used for unique
            # IDs, the device identifier, and the storage key, so it must not
            # change.
            self._data[CONF_NAME] = conf_entry.data[CONF_NAME]

            if error := await self._async_validate_api_key(user_input.get(CONF_API_KEY)):
                errors["base"] = error
            else:
                # Branch based on the selected location source.
                if user_input.get(CONF_LOCATION_SOURCE) == LOCATION_TYPE_LATLONG:
                    return await self.async_step_latlong()
                return await self.async_step_entity()

        # Determine default location source from existing config, falling back to lat/long.
        default_source = conf_entry.data.get(CONF_LOCATION_SOURCE, LOCATION_TYPE_LATLONG)

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

class WeatherDotComOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle Weather.com options for sensor.forecast_details attribute."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options flow."""
        return await self.async_step_extra_attributes(user_input)

    async def async_step_extra_attributes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the extra weather attributes options."""
        if user_input is not None:
            selected_attributes = (
                user_input.get("daily_attributes", [])
                + user_input.get("day_attributes", [])
                + user_input.get("daypart_attributes", [])
            )

            # Auto-enable / disable Forecast Details sensor based on whether attributes are selected
            ent_reg = er.async_get(self.hass)
            location_name = self.config_entry.data.get(CONF_NAME, "")
            unique_id = f"{location_name},validtimeutc".lower()
            if entity_id := ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id):
                entity_entry = ent_reg.async_get(entity_id)
                if entity_entry:
                    if selected_attributes and entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                        ent_reg.async_update_entity(entity_id, disabled_by=None)
                    elif not selected_attributes and not entity_entry.disabled_by:
                        ent_reg.async_update_entity(
                            entity_id,
                            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                        )
            return self.async_create_entry(
                title="",
                data={
                    **self.config_entry.options,
                    CONF_EXTRA_ATTRIBUTES: selected_attributes,
                },
            )

        default_attributes = self.config_entry.options.get(
            CONF_EXTRA_ATTRIBUTES,
            [],
        )

        return self.async_show_form(
            step_id=CONF_EXTRA_ATTRIBUTES,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "daily_attributes",
                        default=[
                            attribute
                            for attribute in default_attributes
                            if attribute in EXTRA_ATTRIBUTE_KEYS_DAILY
                        ],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=EXTRA_ATTRIBUTE_KEYS_DAILY,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                    vol.Optional(
                        "day_attributes",
                        default=[
                            attribute
                            for attribute in default_attributes
                            if attribute in EXTRA_ATTRIBUTE_KEYS_DAY
                        ],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=EXTRA_ATTRIBUTE_KEYS_DAY,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                    vol.Optional(
                        "daypart_attributes",
                        default=[
                            attribute
                            for attribute in default_attributes
                            if attribute in EXTRA_ATTRIBUTE_KEYS_DAYPART
                        ],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=EXTRA_ATTRIBUTE_KEYS_DAYPART,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )