import asyncio
import logging
from bleak import BleakClient
from .const import SERVICE_UUID, CHAR_UUID, INIT_SEQUENCE

_LOGGER = logging.getLogger(__name__)


class KettleBLEClient:
    """BLE client for the Fellow Stagg EKG+ kettle."""

    def __init__(self, address: str):
        self.address = address
        self.service_uuid = SERVICE_UUID
        self.char_uuid = CHAR_UUID
        self.init_sequence = INIT_SEQUENCE

    async def async_poll(self, ble_device):
        """Connect to the kettle, send init command, and return parsed state."""
        _LOGGER.debug("Connecting to kettle at %s", self.address)
        async with BleakClient(ble_device, timeout=10.0) as client:
            try:
                _LOGGER.debug(
                    "Writing init sequence to characteristic %s", self.char_uuid
                )
                await client.write_gatt_char(self.char_uuid, self.init_sequence)
            except Exception as err:
                _LOGGER.error("Error writing init sequence: %s", err)
                return {}

            notifications = []

            def notification_handler(sender, data):
                _LOGGER.debug("Received notification: %s", data.hex())
                notifications.append(data)

            try:
                await client.start_notify(self.char_uuid, notification_handler)
                await asyncio.sleep(2.0)
                await client.stop_notify(self.char_uuid)
            except Exception as err:
                _LOGGER.error("Error during notifications: %s", err)
                return {}

            state = self.parse_notifications(notifications)
            return state

    def parse_notifications(self, notifications):
        """Parse BLE notification payloads into kettle state.

        Expected frame format:
          - Bytes 0-1: Magic (0xef, 0xdd)
          - Byte 2: Message type
          - Subsequent bytes: payload

        Reverse engineered types:
          - Type 0: Power (1 = on, 0 = off)
          - Type 1: Hold (1 = hold, 0 = normal)
          - Type 2: Target temperature (byte 0: temp, byte 1: unit, 1 = F, else C)
          - Type 3: Current temperature (byte 0: temp, byte 1: unit)
          - Type 4: Countdown (byte 0)
          - Type 8: Kettle position (0 = lifted, 1 = on base)
        """
        state = {}
        for data in notifications:
            if len(data) < 3:
                continue
            if data[0] != 0xEF or data[1] != 0xDD:
                continue
            msg_type = data[2]
            if msg_type == 0 and len(data) >= 4:
                state["power"] = data[3] == 1
            elif msg_type == 1 and len(data) >= 4:
                state["hold"] = data[3] == 1
            elif msg_type == 2 and len(data) >= 5:
                state["target_temp"] = data[3]
                state["units"] = "F" if data[4] == 1 else "C"
            elif msg_type == 3 and len(data) >= 5:
                state["current_temp"] = data[3]
                state["units"] = "F" if data[4] == 1 else "C"
            elif msg_type == 4 and len(data) >= 4:
                state["countdown"] = data[3]
            elif msg_type == 8 and len(data) >= 4:
                state["lifted"] = data[3] == 0
            else:
                _LOGGER.debug(
                    "Unhandled message type %s with data %s", msg_type, data.hex()
                )
        return state
