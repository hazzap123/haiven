#!/bin/sh
# Outputs last 300 lines of activity log as JSON for command_line sensor
# Compressed format: "HH:MM Location" per line, pipe-separated
# Called every 5 minutes by sensor.activity_log_48h

LOG_FILE="/config/activity.log"

if [ ! -f "$LOG_FILE" ]; then
  echo '{"lines": 0, "log": "No activity log found"}'
  exit 0
fi

# Extract time, location, and state. Format: "HH:MM Location (state)"
# e.g. "03:22 Bathroom (on)" or "05:15 Kitchen (on)"
COMPRESSED=$(tail -300 "$LOG_FILE" | awk '{printf "%s %s %s\n", substr($2,1,5), $4, $6}')
LINES=$(echo "$COMPRESSED" | wc -l | tr -d ' ')

# Escape for JSON (replace newlines with \n, escape quotes)
JSON_LOG=$(echo "$COMPRESSED" | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')

# Include last entry so sensor state changes on each update (triggers template recalc)
LAST_ENTRY=$(echo "$COMPRESSED" | tail -1 | tr -d '\n')

printf '{"lines": %s, "log": "%s", "last": "%s"}' "$LINES" "$JSON_LOG" "$LAST_ENTRY"
