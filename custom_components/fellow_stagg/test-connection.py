import asyncio
from bleak import BleakScanner, BleakClient

# The MAC address of your Fellow Stagg EKG Pro kettle
KETTLE_ADDRESS = "24:DC:C3:2D:25:B2"
# The magic init sequence used to authenticate
INIT_SEQUENCE = bytes.fromhex("efdd0b3031323334353637383930313233349a6d")
# The characteristic UUID we'll use for communication
CHAR_UUID = "00002A80-0000-1000-8000-00805f9b34fb"

async def main():
    """Scan for and connect to the kettle."""
    print(f"Scanning for kettle with address {KETTLE_ADDRESS}...")
    
    # Scan for devices
    device = await BleakScanner.find_device_by_address(KETTLE_ADDRESS)
    
    if not device:
        print(f"Could not find kettle with address {KETTLE_ADDRESS}")
        devices = await BleakScanner.discover()
        print("Available devices:")
        for d in devices:
            print(f"  {d.address} - {d.name}")
        return
    
    print(f"Found kettle: {device.name} - {device.address}")
    
    # Connect to the kettle
    try:
        print("Connecting to kettle...")
        async with BleakClient(device) as client:
            print("Connected!")
            
            # Discover services and characteristics
            print("Services and characteristics:")
            for service in client.services:
                print(f"Service: {service.uuid}")
                for char in service.characteristics:
                    print(f"  Characteristic: {char.uuid}")
                    print(f"    Properties: {char.properties}")
            
            # Send the authentication sequence
            print(f"Sending authentication sequence: {INIT_SEQUENCE.hex()}")
            await client.write_gatt_char(CHAR_UUID, INIT_SEQUENCE)
            
            # Set up notification handler
            notifications = []
            
            def notification_handler(_, data):
                hex_data = data.hex()
                print(f"Received notification: {hex_data}")
                notifications.append(data)
            
            # Subscribe to notifications
            print("Subscribing to notifications...")
            await client.start_notify(CHAR_UUID, notification_handler)
            
            # Wait for notifications
            print("Waiting for notifications...")
            await asyncio.sleep(5)
            
            # Unsubscribe from notifications
            await client.stop_notify(CHAR_UUID)
            
            # Process notifications
            print("Processing notifications...")
            if notifications:
                for i, notif in enumerate(notifications):
                    print(f"Notification {i+1}: {notif.hex()}")
                    
                    # Basic parsing
                    if len(notif) >= 3 and notif[0] == 0xEF and notif[1] == 0xDD:
                        msg_type = notif[2]
                        print(f"  Message type: {msg_type}")
                        
                        if i + 1 < len(notifications):
                            payload = notifications[i+1]
                            print(f"  Payload: {payload.hex()}")
            else:
                print("No notifications received")
                
            print("Disconnecting...")
    except Exception as e:
        print(f"Error during connection: {e}")

if __name__ == "__main__":
    asyncio.run(main())
