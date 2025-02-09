"""Constants for the Stagg EKG+ integration."""
DOMAIN = "stagg_ekg"

# Configuration
CONF_MAC = "mac_address"

# Defaults
DEFAULT_NAME = "Stagg EKG+"
MIN_TEMP_F = 104  # 40°C
MAX_TEMP_F = 212  # 100°C

# Services
SERVICE_START_HEATING = "start_heating"
SERVICE_STOP_HEATING = "stop_heating"

# Attributes
ATTR_CURRENT_TEMPERATURE = "current_temperature"
ATTR_TARGET_TEMPERATURE = "target_temperature" 
