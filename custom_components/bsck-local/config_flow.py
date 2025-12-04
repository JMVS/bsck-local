"""Config flow for BSCK."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_AC_NAME,
    CONF_IP_ADDRESS,
    CONF_UDP_PORT,
    CONF_LOCAL_PORT,
    DEFAULT_UDP_PORT,
    DEFAULT_LOCAL_PORT,
)

_LOGGER = logging.getLogger(__name__)


class BGHConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BSCK."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validar que no exista otro AC con el mismo nombre
            await self.async_set_unique_id(user_input[CONF_AC_NAME])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_AC_NAME],
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_AC_NAME): str,
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Optional(CONF_UDP_PORT, default=DEFAULT_UDP_PORT): cv.port,
                vol.Optional(CONF_LOCAL_PORT, default=DEFAULT_LOCAL_PORT): cv.port,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return BGHOptionsFlow(config_entry)


class BGHOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for BGH UDP Smart Control."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_IP_ADDRESS,
                    default=self.config_entry.data.get(CONF_IP_ADDRESS),
                ): str,
                vol.Optional(
                    CONF_UDP_PORT,
                    default=self.config_entry.data.get(CONF_UDP_PORT, DEFAULT_UDP_PORT),
                ): cv.port,
                vol.Optional(
                    CONF_LOCAL_PORT,
                    default=self.config_entry.data.get(CONF_LOCAL_PORT, DEFAULT_LOCAL_PORT),
                ): cv.port,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
