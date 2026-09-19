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

# The dashboard card (www-src/haiven-cards.js) reads these same three entity
# IDs directly, so it has to go through the same substitution as the YAML or
# the Rooms/Devices/Ribbon cards silently show "not reporting" for whichever
# sensor you renamed.
SUBST_FILES=$(find "$CONFIG_DIR" -name "*.yaml" -o -name "*.js")

# Replace kitchen sensor
if [ "$KITCHEN" != "event.kitchen_motion" ]; then
    echo "$SUBST_FILES" | xargs sed -i.bak "s|event\.kitchen_motion|${KITCHEN}|g"
    find "$CONFIG_DIR" \( -name "*.yaml.bak" -o -name "*.js.bak" \) -delete
    echo "  Kitchen sensor: replaced"
else
    echo "  Kitchen sensor: using default (no changes needed)"
fi

# Replace bedroom sensor
if [ "$BEDROOM" != "binary_sensor.haiven_bedroom_occupancy" ]; then
    echo "$SUBST_FILES" | xargs sed -i.bak "s|binary_sensor\.haiven_bedroom_occupancy|${BEDROOM}|g"
    find "$CONFIG_DIR" \( -name "*.yaml.bak" -o -name "*.js.bak" \) -delete
    echo "  Bedroom sensor: replaced"
else
    echo "  Bedroom sensor: using default (no changes needed)"
fi

# Replace bathroom sensor
if [ "$BATHROOM" != "binary_sensor.haiven_bathroom_motion" ]; then
    echo "$SUBST_FILES" | xargs sed -i.bak "s|binary_sensor\.haiven_bathroom_motion|${BATHROOM}|g"
    find "$CONFIG_DIR" \( -name "*.yaml.bak" -o -name "*.js.bak" \) -delete
    echo "  Bathroom sensor: replaced"
else
    echo "  Bathroom sensor: using default (no changes needed)"
fi

# The dashboard card lives in www-src/ so it is reviewable in git; Home
# Assistant only ever serves /config/www, which is gitignored and empty on a
# fresh clone. Without this copy the dashboard loads with no cards at all.
echo ""
echo "Deploying dashboard card to www/..."
mkdir -p "$CONFIG_DIR/www"
cp "$CONFIG_DIR/www-src/haiven-cards.js" "$CONFIG_DIR/www/haiven-cards.js"
cp "$CONFIG_DIR/www-src/haiven-loader.js" "$CONFIG_DIR/www/haiven-loader.js"
echo "  Card deployed to www/haiven-cards.js and www/haiven-loader.js"

echo ""
echo "Done! Next steps:"
echo "  1. Copy secrets.yaml.example to secrets.yaml and fill in values"
echo "  2. Edit haiven_persons.yaml with your household members"
echo "  3. Edit packages/haiven_care_circle_inputs.yaml with contact details"
echo "  4. Restart Home Assistant"
echo ""
echo "After any future change to www-src/haiven-cards.js, re-run:"
echo "  cp www-src/haiven-cards.js www/haiven-cards.js"
echo ""
