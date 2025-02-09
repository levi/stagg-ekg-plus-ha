"""Climate platform for Stagg EKG+ integration."""
from __future__ import annotations

import logging
from typing import Any

from bluepy import btle
from bluepy.btle import BTLEInternalError, BTLEDisconnectError

from homeassistant.components.climate import (
  ClimateEntity,
  ClimateEntityFeature,
  HVACAction,
  HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
  ATTR_TEMPERATURE,
  CONF_NAME,
  UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
  DOMAIN,
  CONF_MAC,
  MIN_TEMP_F,
  MAX_TEMP_F,
)

_LOGGER = logging.getLogger(__name__)

class StaggEKGDelegate(btle.DefaultDelegate):
  """Process notifications from Fellow StaggEKG."""
  def __init__(self):
    btle.DefaultDelegate.__init__(self)
    self.notifications = []

  def handleNotification(self, cHandle, data):
    if (
      (len(data) == 4) and
      (data[0] != 239 and data[1] != 221) and
      (int(data.hex(), base=16) != 0)
    ):
      self.notifications.append(data)
    self.notifications = self.notifications[-100:]

  def reset(self):
    self.notifications = []

async def async_setup_entry(
  hass: HomeAssistant,
  entry: ConfigEntry,
  async_add_entities: AddEntitiesCallback,
) -> None:
  """Set up Stagg EKG+ climate based on config_entry."""
  name = entry.data[CONF_NAME]
  mac = entry.data[CONF_MAC]
  
  async_add_entities([StaggEKGClimate(name, mac)], True)

class StaggEKGClimate(ClimateEntity):
  """Representation of a Stagg EKG+ climate entity."""

  _attr_has_entity_name = True
  _attr_name = None
  _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
  _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
  _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
  _attr_min_temp = MIN_TEMP_F
  _attr_max_temp = MAX_TEMP_F
  
  def __init__(self, name: str, mac: str) -> None:
    """Initialize the climate entity."""
    self._attr_unique_id = mac
    self._name = name
    self._mac = mac
    self._kettle = None
    self._available = False
    self._current_temperature = None
    self._target_temperature = None
    self._hvac_mode = HVACMode.OFF
    self._hvac_action = HVACAction.OFF
    
  def connect(self) -> None:
    """Connect to the kettle."""
    try:
      self._kettle = btle.Peripheral(self._mac)
      self._kettle.setDelegate(StaggEKGDelegate())
      service = self._kettle.getServiceByUUID("00001820-0000-1000-8000-00805f9b34fb")
      self._char = service.getCharacteristics()[0]
      self._authenticate()
      self._available = True
    except (BTLEInternalError, BTLEDisconnectError) as err:
      _LOGGER.error("Failed to connect to kettle: %s", err)
      self._available = False
      
  def _authenticate(self) -> None:
    """Authenticate with the kettle."""
    if self._char:
      self._char.write(bytes.fromhex("efdd0b3031323334353637383930313233349a6d"), withResponse=False)
      
  def update(self) -> None:
    """Update the entity."""
    if not self._kettle:
      self.connect()
      
    if not self._available:
      return
      
    try:
      self._current_temperature = self._get_current_temp()
      self._target_temperature = self._get_target_temp()
      self._hvac_action = (
        HVACAction.HEATING
        if self._current_temperature < self._target_temperature
        else HVACAction.OFF
      )
    except (BTLEInternalError, BTLEDisconnectError) as err:
      _LOGGER.error("Failed to update kettle: %s", err)
      self._available = False
      
  def _get_current_temp(self) -> float:
    """Get current temperature."""
    self._kettle.writeCharacteristic(self._char.valHandle + 1, b"\x01\x00")
    self._authenticate()
    if self._kettle.waitForNotifications(1.0):
      notifications = self._kettle.delegate.notifications
      try:
        i = len(notifications) - 1 - notifications[::-1].index(b"\xff\xff\xff\xff")
        if i > 2:
          return float(notifications[i - 2][0])
      except ValueError:
        pass
    return 32.0
    
  def _get_target_temp(self) -> float:
    """Get target temperature."""
    self._kettle.writeCharacteristic(self._char.valHandle + 1, b"\x01\x00")
    self._authenticate()
    if self._kettle.waitForNotifications(1.0):
      notifications = self._kettle.delegate.notifications
      try:
        i = len(notifications) - 1 - notifications[::-1].index(b"\xff\xff\xff\xff")
        if i > 2:
          return float(notifications[i - 1][0])
      except ValueError:
        pass
    return 212.0
    
  def set_temperature(self, **kwargs: Any) -> None:
    """Set target temperature."""
    temperature = kwargs.get(ATTR_TEMPERATURE)
    if temperature is None:
      return
      
    try:
      temp_hex = hex(int(temperature))[2:]
      self._char.write(
        bytes.fromhex(f"efdd0a0001{temp_hex}{temp_hex}01"),
        withResponse=False
      )
      self._target_temperature = temperature
    except (BTLEInternalError, BTLEDisconnectError) as err:
      _LOGGER.error("Failed to set temperature: %s", err)
      self._available = False
      
  def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
    """Set HVAC mode."""
    if hvac_mode == HVACMode.HEAT:
      try:
        self._char.write(bytes.fromhex("efdd0a0000010100"), withResponse=False)
        self._hvac_mode = HVACMode.HEAT
      except (BTLEInternalError, BTLEDisconnectError) as err:
        _LOGGER.error("Failed to turn on kettle: %s", err)
        self._available = False
    else:
      try:
        self._char.write(bytes.fromhex("efdd0a0400000400"), withResponse=False)
        self._hvac_mode = HVACMode.OFF
      except (BTLEInternalError, BTLEDisconnectError) as err:
        _LOGGER.error("Failed to turn off kettle: %s", err)
        self._available = False 
