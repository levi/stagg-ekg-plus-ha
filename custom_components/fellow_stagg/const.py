"""Constants for the Fellow Stagg integration."""

DOMAIN = "fellow_stagg"

# BLE UUIDs for the Fellow Stagg kettle's "Serial Port Service"
# This appears to be the same for both EKG+ and EKG Pro models
SERVICE_UUID = "00001820-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "00002A80-0000-1000-8000-00805f9b34fb"

# Custom UUID identified in Wireshark capture
CUSTOM_SERVICE_UUID = "021a9004-0302-4aea-bff4-6b3f1c5adfb4"

# The magic init sequence (in hex) used to authenticate with the kettle:
# ef dd 0b 30 31 32 33 34 35 36 37 38 39 30 31 32 33 34 9a 6d
INIT_SEQUENCE = bytes.fromhex("efdd0b3031323334353637383930313233349a6d")

# Retry settings
MAX_CONNECTION_ATTEMPTS = 3
