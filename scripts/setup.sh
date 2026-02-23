#!/usr/bin/env bash
# Haiven Setup Script
# Maps your physical sensors to Haiven's three behavioural roles.
# Only edits haiven_sensor_roles.yaml — all other files use stable alias names.
#
# Usage: bash scripts/setup.sh
#
# You will be prompted for three sensor entity IDs:
#   ACTIVITY — kitchen or living area motion sensor (event or binary)
#   BED      — bedroom presence/occupancy sensor
#   BATH     — bathroom motion sensor

set -euo pipefail

ROLES_FILE="$(dirname "$0")/../haiven_sensor_roles.yaml"

if [ ! -f "$ROLES_FILE" ]; then
  echo "ERROR: haiven_sensor_roles.yaml not found at $ROLES_FILE"
  exit 1
fi

echo ""
echo "Haiven Sensor Setup"
echo "==================="
echo "Enter your physical sensor entity IDs (from Home Assistant > Developer Tools > States)"
echo ""

read -rp "ACTIVITY sensor entity_id (e.g. event.kitchen_motion): " ACTIVITY
read -rp "BED sensor entity_id (e.g. binary_sensor.bedroom_occupancy): " BED
read -rp "BATH sensor entity_id (e.g. binary_sensor.bathroom_motion): " BATH

echo ""
echo "Configuring:"
echo "  activity -> $ACTIVITY"
echo "  bed      -> $BED"
echo "  bath     -> $BATH"
echo ""

# Replace activity sensor (in automation trigger)
sed -i "s|entity_id: event.kitchen_motion|entity_id: ${ACTIVITY}|g" "$ROLES_FILE"

# Replace bed sensor (in template wrapper)
sed -i "s|is_state('binary_sensor.haiven_bedroom_occupancy'|is_state('${BED}'|g" "$ROLES_FILE"

# Replace bath sensor (in template wrapper)
sed -i "s|is_state('binary_sensor.haiven_bathroom_motion'|is_state('${BATH}'|g" "$ROLES_FILE"

echo "Done. Reload Home Assistant configuration to apply changes."
echo ""
echo "Verify in Developer Tools > States that these entities exist:"
echo "  binary_sensor.haiven_activity_sensor"
echo "  binary_sensor.haiven_bed_sensor"
echo "  binary_sensor.haiven_bath_sensor"
