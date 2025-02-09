import logging
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class FellowStaggConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Fellow Stagg integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step initiated by the user."""
        errors = {}
        if user_input is not None:
            bluetooth_address = user_input.get("bluetooth_address")
            # Set the unique ID to the Bluetooth address and abort if already configured.
            await self.async_set_unique_id(bluetooth_address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Fellow Stagg ({bluetooth_address})",
                data=user_input,
            )

        data_schema = vol.Schema({vol.Required("bluetooth_address"): str})
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
