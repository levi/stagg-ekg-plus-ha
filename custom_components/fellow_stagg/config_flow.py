import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)

class FellowStaggConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Fellow Stagg integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._discovery_class = "fellow_stagg"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_bluetooth()

    async def async_step_bluetooth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Fellow Stagg ({address})",
                data={"bluetooth_address": address},
            )

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses:
                continue
            if SERVICE_UUID in discovery_info.service_uuids:
                self._discovered_devices[address] = discovery_info

        if not self._discovered_devices:
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="bluetooth",
            data_schema=vol.Schema(
                {
                    vol.Required("address"): vol.In(
                        {
                            service_info.address: f"{service_info.name} ({service_info.address})"
                            for service_info in self._discovered_devices.values()
                        }
                    )
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the manual entry step."""
        errors = {}
        if user_input is not None:
            address = user_input["bluetooth_address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Fellow Stagg ({address})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required("bluetooth_address"): str}),
            errors=errors,
            description_placeholders={
                "discovery_msg": "No Fellow Stagg devices were automatically discovered. Please enter the Bluetooth address manually."
            },
        )
