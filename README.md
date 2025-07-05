# Stagg EKG+ Home Assistant Integration

A Home Assistant integration for the Fellow Stagg EKG+ electric kettle. Control and monitor your kettle directly from Home Assistant.

## Features

- Control kettle power (on/off)
- Set target temperature
- Monitor current temperature
- Automatic temperature updates
- Bluetooth discovery support

## Installation

### Option 1: HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz) installed
2. Add this repository as a custom repository in HACS:
   - Click the menu icon in the top right of HACS
   - Select "Custom repositories"
   - Add `levi/stagg-ekg-plus-ha` with category "Integration"
3. Click "Download" on the Stagg EKG+ integration
4. Restart Home Assistant
5. Go to Settings -> Devices & Services -> Add Integration
6. Search for "Stagg EKG+"
7. Follow the configuration steps

### Option 2: Manual Installation

1. Copy the `custom_components/stagg_ekg` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant
3. Go to Settings -> Devices & Services -> Add Integration
4. Search for "Stagg EKG+"
5. Follow the configuration steps

## Configuration

The integration can be set up in two ways:

1. **Automatic Discovery**: The kettle will be automatically discovered if Bluetooth is enabled in Home Assistant
2. **Manual Configuration**: You can manually add the kettle by providing its MAC address

## Usage

Once configured, the kettle will appear as a climate entity in Home Assistant. You can:

- Turn the kettle on/off using the climate entity
- Set the target temperature using the temperature slider
- Monitor the current temperature
- See the heating status (heating/idle)

## Requirements

- Home Assistant 2024.1.0 or newer
- Home Assistant Community Store (HACS) for easy installation
- Bluetooth support in your Home Assistant instance
- A Fellow Stagg EKG+ kettle

## Troubleshooting

If you experience connection issues:
1. Ensure the kettle is within Bluetooth range of your Home Assistant device
2. Check that Bluetooth is enabled and working in Home Assistant
3. Verify the MAC address if manually configured
4. Check the Home Assistant logs for detailed error messages

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details
