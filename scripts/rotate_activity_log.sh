#!/bin/bash
#
# Rotate activity.log - keep 90 days, archive older
# Run manually or via cron: 0 3 1 * * /config/scripts/rotate_activity_log.sh
#

LOG_FILE="/config/activity.log"
ARCHIVE_DIR="/config/logs/archive"
DAYS_TO_KEEP=90

# Create archive directory if needed
mkdir -p "$ARCHIVE_DIR"

# Get cutoff date (90 days ago)
CUTOFF_DATE=$(date -d "-${DAYS_TO_KEEP} days" +%Y-%m-%d 2>/dev/null || date -v-${DAYS_TO_KEEP}d +%Y-%m-%d)

# Archive filename with current date
ARCHIVE_FILE="$ARCHIVE_DIR/activity_$(date +%Y%m).log"

echo "Rotating $LOG_FILE"
echo "Cutoff date: $CUTOFF_DATE"
echo "Archive file: $ARCHIVE_FILE"

# Count lines before
BEFORE=$(wc -l < "$LOG_FILE")

# Extract old entries (before cutoff) and append to archive
awk -v cutoff="$CUTOFF_DATE" '$1 < cutoff' "$LOG_FILE" >> "$ARCHIVE_FILE"

# Keep only recent entries (on or after cutoff)
awk -v cutoff="$CUTOFF_DATE" '$1 >= cutoff' "$LOG_FILE" > "${LOG_FILE}.tmp"
mv "${LOG_FILE}.tmp" "$LOG_FILE"

# Count lines after
AFTER=$(wc -l < "$LOG_FILE")
ARCHIVED=$((BEFORE - AFTER))

echo "Lines before: $BEFORE"
echo "Lines after: $AFTER"
echo "Archived: $ARCHIVED"

# Compress old archives (older than current month)
find "$ARCHIVE_DIR" -name "activity_*.log" -mtime +30 -exec gzip -f {} \;

echo "Done"
