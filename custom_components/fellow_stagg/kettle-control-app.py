#!/usr/bin/env python3
"""
Fellow Stagg EKG Pro Kettle Control Application

This script allows you to control your Fellow Stagg EKG Pro kettle via BLE.
"""

import asyncio
import argparse
import logging
from bleak import BleakScanner, BleakClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

# Constants for the Fellow Stagg EKG Pro kettle
KETTLE_ADDRESS = "24:DC:C3:2D:25:B2"  # Change this to your kettle's address if different
SERVICE_UUID = "00001820-0000-1000-8000-00805f9b34fb"  # Serial Port Service
CHAR_UUID = "00002A80-0000-1000-8000-00805f9b34fb"     # Serial Port Characteristic
INIT_SEQUENCE = bytes.fromhex("efdd0b3031323334353637383930313233349a6d")  # Authentication sequence

class KettleController:
    """Controller for the Fellow Stagg EKG Pro kettle."""
    
    def __init__(self, address=KETTLE_ADDRESS):
        """Initialize the controller with the kettle's address."""
        self.address = address
        self._sequence = 0
        
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
    
    def _parse_notifications(self, notifications: list) -> dict:
        """Parse BLE notification payloads into kettle state."""
        state = {}
        
        if not notifications:
            return state
            
        # Process notifications
        i = 0
        while i < len(notifications):
            notif = notifications[i]
            
            # Check if it's a valid header
            if len(notif) >= 3 and notif[0] == 0xEF and notif[1] == 0xDD:
                msg_type = notif[2]
                
                # Get the payload if available
                payload = None
                if i + 1 < len(notifications):
                    payload = notifications[i + 1]
                    i += 1  # Skip the payload in the next iteration
                
                # Parse based on message type
                if msg_type == 0 and payload and len(payload) >= 1:
                    # Power state
                    state["power"] = payload[0] == 1
                elif msg_type == 1 and payload and len(payload) >= 1:
                    # Hold state
                    state["hold"] = payload[0] == 1
                elif msg_type == 2 and payload and len(payload) >= 2:
                    # Target temperature
                    temp = payload[0]
                    is_fahrenheit = payload[1] == 1
                    state["target_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
                elif msg_type == 3 and payload and len(payload) >= 2:
                    # Current temperature
                    temp = payload[0]
                    is_fahrenheit = payload[1] == 1
                    state["current_temp"] = temp
                    state["units"] = "F" if is_fahrenheit else "C"
                elif msg_type == 4 and payload and len(payload) >= 1:
                    # Countdown
                    state["countdown"] = payload[0]
                elif msg_type == 8 and payload and len(payload) >= 1:
                    # Kettle position
                    state["lifted"] = payload[0] == 0
            
            i += 1
            
        return state
    
    async def find_kettle(self):
        """Find the kettle device."""
        device = await BleakScanner.find_device_by_address(self.address)
        if not device:
            _LOGGER.error(f"Could not find kettle with address {self.address}")
            return None
        return device
    
    async def get_state(self):
        """Get the current state of the kettle."""
        device = await self.find_kettle()
        if not device:
            return None
        
        async with BleakClient(device) as client:
            _LOGGER.info("Connected to kettle")
            
            # Send authentication sequence
            await client.write_gatt_char(CHAR_UUID, INIT_SEQUENCE)
            
            # Collect notifications
            notifications = []
            
            def notification_handler(_, data):
                notifications.append(data)
            
            # Subscribe to notifications
            await client.start_notify(CHAR_UUID, notification_handler)
            
            # Wait for notifications
            await asyncio.sleep(2)
            
            # Unsubscribe from notifications
            await client.stop_notify(CHAR_UUID)
            
            # Parse notifications
            state = self._parse_notifications(notifications)
            return state
    
    async def set_power(self, power_on: bool):
        """Turn the kettle on or off."""
        device = await self.find_kettle()
        if not device:
            return False
        
        async with BleakClient(device) as client:
            _LOGGER.info(f"Setting power to: {'ON' if power_on else 'OFF'}")
            
            # Send authentication sequence
            await client.write_gatt_char(CHAR_UUID, INIT_SEQUENCE)
            
            # Send power command
            command = self._create_command(0, 1 if power_on else 0)
            await client.write_gatt_char(CHAR_UUID, command)
            
            return True
    
    async def set_temperature(self, temp: int, fahrenheit: bool = True):
        """Set the target temperature."""
        # Validate temperature
        if fahrenheit:
            if temp < 104:
                temp = 104
                _LOGGER.warning("Temperature too low, setting to minimum (104°F)")
            elif temp > 212:
                temp = 212
                _LOGGER.warning("Temperature too high, setting to maximum (212°F)")
        else:
            if temp < 40:
                temp = 40
                _LOGGER.warning("Temperature too low, setting to minimum (40°C)")
            elif temp > 100:
                temp = 100
                _LOGGER.warning("Temperature too high, setting to maximum (100°C)")
        
        device = await self.find_kettle()
        if not device:
            return False
        
        async with BleakClient(device) as client:
            _LOGGER.info(f"Setting temperature to: {temp}°{'F' if fahrenheit else 'C'}")
            
            # Send authentication sequence
            await client.write_gatt_char(CHAR_UUID, INIT_SEQUENCE)
            
            # Send temperature command
            command = self._create_command(1, temp)
            await client.write_gatt_char(CHAR_UUID, command)
            
            return True

async def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description='Control a Fellow Stagg EKG Pro kettle.')
    parser.add_argument('--address', '-a', default=KETTLE_ADDRESS, help='The Bluetooth address of the kettle')
    parser.add_argument('--scan', '-s', action='store_true', help='Scan for BLE devices')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # State command
    subparsers.add_parser('state', help='Get the current state of the kettle')
    
    # Power command
    power_parser = subparsers.add_parser('power', help='Turn the kettle on or off')
    power_parser.add_argument('setting', choices=['on', 'off'], help='Power setting')
    
    # Temperature command
    temp_parser = subparsers.add_parser('temp', help='Set the target temperature')
    temp_parser.add_argument('temperature', type=int, help='Temperature value')
    temp_parser.add_argument('--fahrenheit', '-f', action='store_true', help='Use Fahrenheit (default)')
    temp_parser.add_argument('--celsius', '-c', action='store_true', help='Use Celsius')
    
    args = parser.parse_args()
    
    # Scan for devices if requested
    if args.scan:
        _LOGGER.info("Scanning for BLE devices...")
        devices = await BleakScanner.discover()
        _LOGGER.info("Found devices:")
        for device in devices:
            _LOGGER.info(f"  {device.address} - {device.name}")
        return
    
    # Initialize the controller
    controller = KettleController(args.address)
    
    # Process commands
    if args.command == 'state':
        _LOGGER.info("Getting kettle state...")
        state = await controller.get_state()
        if state:
            _LOGGER.info("Kettle state:")
            for key, value in state.items():
                _LOGGER.info(f"  {key}: {value}")
        else:
            _LOGGER.error("Failed to get kettle state")
    
    elif args.command == 'power':
        power_on = args.setting == 'on'
        success = await controller.set_power(power_on)
        if success:
            _LOGGER.info(f"Successfully set power to {args.setting}")
        else:
            _LOGGER.error(f"Failed to set power to {args.setting}")
    
    elif args.command == 'temp':
        # Determine units
        fahrenheit = not args.celsius  # Default to Fahrenheit unless Celsius is specified
        success = await controller.set_temperature(args.temperature, fahrenheit)
        if success:
            _LOGGER.info(f"Successfully set temperature to {args.temperature}°{'F' if fahrenheit else 'C'}")
        else:
            _LOGGER.error(f"Failed to set temperature to {args.temperature}°{'F' if fahrenheit else 'C'}")
    
    else:
        # No command specified, show state by default
        _LOGGER.info("Getting kettle state...")
        state = await controller.get_state()
        if state:
            _LOGGER.info("Kettle state:")
            for key, value in state.items():
                _LOGGER.info(f"  {key}: {value}")
        else:
            _LOGGER.error("Failed to get kettle state")

if __name__ == "__main__":
    asyncio.run(main())
