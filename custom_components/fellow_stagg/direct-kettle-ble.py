"""Direct BLE client for the Fellow Stagg EKG Pro kettle."""
import logging
import asyncio
from typing import Dict, Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .const import SERVICE_UUID, CHAR_UUID, INIT_SEQUENCE

_LOGGER = logging.getLogger(__name__)


class DirectKettleBLEClient:
    """Direct BLE client for the Fellow Stagg EKG Pro kettle."""

    def __init__(self, address: str):
        """Initialize the client."""
        self.address = address
        self.service_uuid = SERVICE_UUID
        self.char_uuid = CHAR_UUID
        self.init_sequence = INIT_SEQUENCE
        self._sequence = 0  # For command sequence numbering

    async def async_poll(self, ble_device: BLEDevice) -> Dict[str, Any]:
        """Connect to the kettle, send init command, and return parsed state."""
        client = None
        try:
            _LOGGER.debug("Connecting to %s", self.address)
            client = BleakClient(ble_device, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                _LOGGER.error("Failed to connect to device %s", self.address)
                return {}
                
            _LOGGER.debug("Successfully connected, authenticating")
            
            # Send authentication sequence
            await client.write_gatt_char(self.char_uuid, self.init_sequence)
            
            # Read notifications
            notifications = []
            
            def notification_handler(_, data):
                _LOGGER.debug("Received notification: %s", data.hex())
                notifications.append(data)
            
            await client.start_notify(self.char_uuid, notification_handler)
            await asyncio.sleep(2.0)  # Wait for notifications to arrive
            await client.stop_notify(self.char_uuid)
            
            # Parse notifications into state
            state = self._parse_notifications(notifications)
            
            return state
            
        except asyncio.TimeoutError:
            _LOGGER.error("Connection to %s timed out", self.address)
            return {}
        except BleakError as err:
            _LOGGER.error("BleakError during connection to %s: %s", self.address, str(err))
            return {}
        except Exception as err:
            _LOGGER.error("Error during operation on %s: %s", self.address, str(err), exc_info=True)
            return {}
        finally:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except Exception as err:
                    _LOGGER.warning("Error during disconnect: %s", str(err))

    async def async_set_power(self, ble_device: BLEDevice, power_on: bool) -> bool:
        """Turn the kettle on or off."""
        client = None
        try:
            _LOGGER.debug("Connecting to %s", self.address)
            client = BleakClient(ble_device, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                _LOGGER.error("Failed to connect to device %s", self.address)
                return False
                
            _LOGGER.debug("Successfully connected, authenticating")
            
            # Send authentication sequence
            await client.write_gatt_char(self.char_uuid, self.init_sequence)
            
            # Create and send power command
            command = self._create_command(0, 1 if power_on else 0)
            await client.write_gatt_char(self.char_uuid, command)
            
            return True
            
        except asyncio.TimeoutError:
            _LOGGER.error("Connection to %s timed out", self.address)
            return False
        except BleakError as err:
            _LOGGER.error("BleakError during connection to %s: %s", self.address, str(err))
            return False
        except Exception as err:
            _LOGGER.error("Error during operation on %s: %s", self.address, str(err), exc_info=True)
            return False
        finally:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except Exception as err:
                    _LOGGER.warning("Error during disconnect: %s", str(err))

    async def async_set_temperature(self, ble_device: BLEDevice, temp: int, fahrenheit: bool = True) -> bool:
        """Set target temperature."""
        # Temperature validation
        if fahrenheit:
            if temp > 212:
                temp = 212
            if temp < 104:
                temp = 104
        else:
            if temp > 100:
                temp = 100
            if temp < 40:
                temp = 40

        client = None
        try:
            _LOGGER.debug("Connecting to %s", self.address)
            client = BleakClient(ble_device, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                _LOGGER.error("Failed to connect to device %s", self.address)
                return False
                
            _LOGGER.debug("Successfully connected, authenticating")
            
            # Send authentication sequence
            await client.write_gatt_char(self.char_uuid, self.init_sequence)
            
            # Create and send temperature command
            command = self._create_command(1, temp)  # Type 1 = temperature command
            await client.write_gatt_char(self.char_uuid, command)
            
            return True
            
        except asyncio.TimeoutError:
            _LOGGER.error("Connection to %s timed out", self.address)
            return False
        except BleakError as err:
            _LOGGER.error("BleakError during connection to %s: %s", self.address, str(err))
            return False
        except Exception as err:
            _LOGGER.error("Error during operation on %s: %s", self.address, str(err), exc_info=True)
            return False
        finally:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except Exception as err:
                    _LOGGER.warning("Error during disconnect: %s", str(err))

    def _create_command(self, command_type: int, value: int) -> bytes:
        """Create a command with proper sequence number and checksum."""
        command = bytearray([
            0xef, 0xdd,  # Magic
            0x0a,        # Command flag
            self._sequence,  # Sequence number
            command_type,    # Command type
            value,          # Value
            (self._sequence + value) & 0xFF,  # Checksum 1
            command_type    # Checksum 2
        ])
        self._sequence = (self._sequence + 1) & 0xFF
        return bytes(command)
        
    def _parse_notifications(self, notifications: list) -> Dict[str, Any]:
        """Parse BLE notification payloads into kettle state."""
        state = {}
        
        if not notifications:
            return state
            
        # Log all notifications for debugging
        for i, notif in enumerate(notifications):
            _LOGGER.debug("Processing notification %d: %s", i, notif.hex())
        
        i = 0
        while i < len(notifications) - 1:  # Process pairs of notifications
            header = notifications[i]
            if i + 1 >= len(notifications):
                break
                
            payload = notifications[i + 1]
            
            if len(header) < 3 or header[0] != 0xEF or header[1] != 0xDD:
                i += 1
                continue
                
            msg_type = header[2]
            _LOGGER.debug("Processing message type %d with payload %s", msg_type, payload.hex())
            
            if msg_type == 0:
                # Power state
                if len(payload) >= 1:
                    state["power"] = payload[0] == 1
                    _LOGGER.debug("Power state: %s", state["power"])
            elif msg_type == 1:
                # Hold state
                if len(payload) >= 1:
                    state["hold"] = payload[0] == 1
                    _LOGGER.debug("Hold state: %s", state["hold"])
            elif msg_type == 2:
                # Target temperature
                if len(payload) >= 2:
                    temp = payload[0]  # Single byte temperature
                    is_fahrenheit = payload[1] == 1
                    state["target_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
                    _LOGGER.debug("Target temp: %d°%s", temp, state["units"])
            elif msg_type == 3:
                # Current temperature
                if len(payload) >= 2:
                    temp = payload[0]  # Single byte temperature
                    is_fahrenheit = payload[1] == 1
                    state["current_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
                    _LOGGER.debug("Current temp: %d°%s", temp, state["units"])
            elif msg_type == 4:
                # Countdown
                if len(payload) >= 1:
                    state["countdown"] = payload[0]
                    _LOGGER.debug("Countdown: %d", state["countdown"])
            elif msg_type == 8:
                # Kettle position
                if len(payload) >= 1:
                    state["lifted"] = payload[0] == 0
                    _LOGGER.debug("Lifted: %s", state["lifted"])
            else:
                _LOGGER.debug("Unknown message type: %d", msg_type)
            
            i += 2  # Move to next pair of notifications
            
        return state

    async def disconnect(self):
        """No persistent connection to disconnect in this implementation."""
        pass  # This is a no-op since we don't maintain a persistent connection
