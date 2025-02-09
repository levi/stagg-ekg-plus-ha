DOMAIN = "fellow_stagg"

# BLE UUIDs for the Fellow Stagg kettle’s “Serial Port Service”
SERVICE_UUID = "00001820-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "00002A80-0000-1000-8000-00805f9b34fb"

# The magic init sequence (in hex) used to authenticate with the kettle:
# ef dd 0b 30 31 32 33 34 35 36 37 38 39 30 31 32 33 34 9a 6d
INIT_SEQUENCE = bytes.fromhex("efdd0b3031323334353637383930313233349a6d")
