import asyncio
import logging
from bleak import BleakClient
from .const import SERVICE_UUID, CHAR_UUID, INIT_SEQUENCE

_LOGGER = logging.getLogger(__name__)


class KettleBLEClient:
    """BLE client for the Fellow Stagg EKG+ kettle."""

    def __init__(self, address: str):
        self.address = address
        # In a production integration you might allow overriding these.
        self.service_uuid = SERVICE_UUID
        self.char_uuid = CHAR_UUID
        self.init_sequence = INIT_SEQUENCE

    async def async_poll(self, ble_device):
        """Connect to the kettle, send init command, and return parsed state.

        This function uses an active connection (with a timeout of 10 seconds)
        to write the init sequence and then waits for notifications.
        """
        _LOGGER.debug("Connecting to kettle at %s", self.address)
        async with BleakClient(ble_device, timeout=10.0) as client:
            try:
                # Write the init command
                _LOGGER.debug(
                    "Writing init sequence to characteristic %s", self.char_uuid
                )
                await client.write_gatt_char(self.char_uuid, self.init_sequence)
            except Exception as err:
                _LOGGER.error("Error writing init sequence: %s", err)
                return {}

            # Container for notifications
            notifications = []

            def notification_handler(sender, data):
                _LOGGER.debug("Received notification: %s", data.hex())
                notifications.append(data)

            try:
                await client.start_notify(self.char_uuid, notification_handler)
                # Wait a short period to collect notifications.
                await asyncio.sleep(2.0)
                await client.stop_notify(self.char_uuid)
            except Exception as err:
                _LOGGER.error("Error during notifications: %s", err)
                return {}

            # Parse notifications into a single state dictionary.
            state = self.parse_notifications(notifications)
            return state

    def parse_notifications(self, notifications):
        """Parse a list of BLE notification payloads into kettle state.

        Each payload is expected to begin with 0xef 0xdd and then a frame:
          - Byte 0-1: Magic bytes (0xef, 0xdd)
          - Byte 2: Message type
          - Subsequent bytes: payload

        Based on the reverse engineering:
          - Type 0: Power state (payload[0]: 0 for off, 1 for on)
          - Type 1: Hold state (payload[0]: 0 for off, 1 for on)
          - Type 2: Target temperature & unit (payload[0]=temp, payload[1]=unit, 1 = Fahrenheit, else Celsius)
          - Type 3: Current temperature & unit (payload[0]=temp, payload[1]=unit)
          - Type 4: Countdown (payload[0])
          - Type 8: Kettle lifted (payload[0]: 0 means lifted, 1 means on base)
        """
        state = {}
        for data in notifications:
            if len(data) < 3:
                continue
            if data[0] != 0xEF or data[1] != 0xDD:
                continue
            msg_type = data[2]
            # For each type, check the payload length before parsing
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
                # If payload is 0, kettle is lifted; if 1, on base.
                state["lifted"] = data[3] == 0
            else:
                _LOGGER.debug(
                    "Unhandled message type %s with data %s", msg_type, data.hex()
                )
        return state
