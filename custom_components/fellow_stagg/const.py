"""Constants for the Fellow Stagg integration."""

DOMAIN = "fellow_stagg"

# BLE UUIDs for the Fellow Stagg kettle's "Serial Port Service"
# From the Wireshark capture we can see the UUID in the scan
SERVICE_UUID = "00001820-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "00002A80-0000-1000-8000-00805f9b34fb"

# Custom UUID identified in Wireshark capture (021a9004-0302-4aea-bff4-6b3f1c5adfb4)
CUSTOM_SERVICE_UUID = "021a9004-0302-4aea-bff4-6b3f1c5adfb4"

# The magic init sequence (in hex) used to authenticate with the kettle
# Based on the original EKG+ sequence, might need adjustment for Pro
INIT_SEQUENCE = bytes.fromhex("efdd0b3031323334353637383930313233349a6d")

# Retry settings
MAX_CONNECTION_ATTEMPTS = 3

# Temperature ranges for the kettle
MIN_TEMP_F = 104
MAX_TEMP_F = 212
MIN_TEMP_C = 40
MAX_TEMP_C = 100

# Polling interval in seconds (increased for better reliability)
POLLING_INTERVAL_SECONDS = 30

# Connection timeout in seconds
CONNECTION_TIMEOUT = 15
