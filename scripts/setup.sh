#!/bin/bash
#
# Haiven Setup Script
# Configures sensor entity IDs for your specific hardware
#
# Usage: bash scripts/setup.sh
#

set -e

echo "=============================="
echo "  Haiven Setup"
echo "=============================="
echo ""
echo "This script configures Haiven for your specific sensors."
echo "You'll need the entity IDs of your 3 sensors from Home Assistant."
echo ""
echo "Find them in Settings > Devices & Services > Entities"
echo ""

# Kitchen sensor
echo "--- Kitchen Sensor ---"
echo "This should be a motion sensor in the kitchen/living area."
echo "Examples: event.kitchen_motion, binary_sensor.kitchen_motion"
read -p "Kitchen sensor entity ID [event.kitchen_motion]: " KITCHEN
KITCHEN=${KITCHEN:-event.kitchen_motion}

# Bedroom sensor
echo ""
echo "--- Bedroom Sensor ---"
echo "This should be a presence/occupancy sensor in the bedroom."
echo "Examples: binary_sensor.bedroom_presence, binary_sensor.bedroom_occupancy"
read -p "Bedroom sensor entity ID [binary_sensor.haiven_bedroom_occupancy]: " BEDROOM
BEDROOM=${BEDROOM:-binary_sensor.haiven_bedroom_occupancy}

# Bathroom sensor
echo ""
echo "--- Bathroom Sensor ---"
echo "This should be a motion sensor in the bathroom."
echo "Examples: binary_sensor.bathroom_motion, binary_sensor.bathroom_pir"
read -p "Bathroom sensor entity ID [binary_sensor.haiven_bathroom_motion]: " BATHROOM
BATHROOM=${BATHROOM:-binary_sensor.haiven_bathroom_motion}

echo ""
echo "Configuration:"
echo "  Kitchen:  $KITCHEN"
echo "  Bedroom:  $BEDROOM"
echo "  Bathroom: $BATHROOM"
echo ""
read -p "Apply these settings? [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-Y}

if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
    echo "Cancelled."
    exit 0
fi

# Get the directory where the script lives, then go up one level to config root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "Applying to files in $CONFIG_DIR..."

# Replace kitchen sensor
if [ "$KITCHEN" != "event.kitchen_motion" ]; then
    find "$CONFIG_DIR" -name "*.yaml" -exec sed -i.bak "s|event\.kitchen_motion|${KITCHEN}|g" {} +
    find "$CONFIG_DIR" -name "*.yaml.bak" -delete
    echo "  Kitchen sensor: replaced"
else
    echo "  Kitchen sensor: using default (no changes needed)"
fi

# Replace bedroom sensor
if [ "$BEDROOM" != "binary_sensor.haiven_bedroom_occupancy" ]; then
    find "$CONFIG_DIR" -name "*.yaml" -exec sed -i.bak "s|binary_sensor\.haiven_bedroom_occupancy|${BEDROOM}|g" {} +
    find "$CONFIG_DIR" -name "*.yaml.bak" -delete
    echo "  Bedroom sensor: replaced"
else
    echo "  Bedroom sensor: using default (no changes needed)"
fi

# Replace bathroom sensor
if [ "$BATHROOM" != "binary_sensor.haiven_bathroom_motion" ]; then
    find "$CONFIG_DIR" -name "*.yaml" -exec sed -i.bak "s|binary_sensor\.haiven_bathroom_motion|${BATHROOM}|g" {} +
    find "$CONFIG_DIR" -name "*.yaml.bak" -delete
    echo "  Bathroom sensor: replaced"
else
    echo "  Bathroom sensor: using default (no changes needed)"
fi

echo ""
echo "Done! Next steps:"
echo "  1. Copy secrets.yaml.example to secrets.yaml and fill in values"
echo "  2. Edit haiven_persons.yaml with your household members"
echo "  3. Edit packages/haiven_care_circle_inputs.yaml with contact details"
echo "  4. Restart Home Assistant"
echo ""
