"""Config flow for Stagg EKG+ integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_MAC, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

class StaggEKGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
  """Handle a config flow for Stagg EKG+."""
  
  VERSION = 1
  
  async def async_step_bluetooth(self, discovery_info: async_discovered_service_info) -> FlowResult:
    """Handle the bluetooth discovery step."""
    await self.async_set_unique_id(discovery_info.address)
    self._abort_if_unique_id_configured()
    
    return self.async_create_entry(
      title=DEFAULT_NAME,
      data={
        CONF_MAC: discovery_info.address,
        CONF_NAME: DEFAULT_NAME,
      },
    )
  
  async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    """Handle a flow initiated by the user."""
    if user_input is not None:
      await self.async_set_unique_id(user_input[CONF_MAC])
      self._abort_if_unique_id_configured()
      
      return self.async_create_entry(
        title=user_input.get(CONF_NAME, DEFAULT_NAME),
        data=user_input,
      )
      
    return self.async_show_form(
      step_id="user",
      data_schema=vol.Schema(
        {
          vol.Required(CONF_MAC): str,
          vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        }
      ),
    ) 
