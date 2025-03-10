"""Constants for the Fellow Stagg integration."""

DOMAIN = "fellow_stagg"

# BLE UUIDs for the Fellow Stagg kettle's "Serial Port Service"
SERVICE_UUID = "00001820-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "00002A80-0000-1000-8000-00805f9b34fb"

# Custom UUID identified in Wireshark capture
CUSTOM_SERVICE_UUID = "021a9004-0302-4aea-bff4-6b3f1c5adfb4"

# The magic init sequence (in hex) used to authenticate with the kettle
INIT_SEQUENCE = bytes.fromhex("efdd0b3031323334353637383930313233349a6d")

# Temperature ranges for the kettle
MIN_TEMP_F = 104
MAX_TEMP_F = 212
MIN_TEMP_C = 40
MAX_TEMP_C = 100

# Polling interval in seconds (increased for better reliability)
POLLING_INTERVAL_SECONDS = 60  # Only poll once per minute to reduce BLE traffic

# Connection timeout in seconds
CONNECTION_TIMEOUT = 15
