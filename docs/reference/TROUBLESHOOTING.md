# Haiven Troubleshooting Guide

Consolidated troubleshooting for all Haiven components.

**Updated:** 2026-09-19

---

## Quick Checks

Before diving into specific issues, verify these basics:

```yaml
# Check monitoring is enabled
input_boolean.haiven_monitoring_enabled: should be "on"

# Check sensor health
sensor.sensor_health_status: should show "All Sensors Online"

# Check for deviations
sensor.deviation_count: 0 = normal
```

---

## Sensors Not Updating

### Symptoms
- `sensor.last_activity_display` stuck on old time
- Status always "Unknown"
- Dashboard shows stale data

### Solutions

1. **Verify entity IDs are correct**
   - Developer Tools > States > Search for each sensor
   - Check they're not "unknown" or "unavailable"
   - Cross-reference with [ENTITY_REFERENCE.md](ENTITY_REFERENCE.md)

2. **Check  integration**
   - Settings > Integrations > Device
   - Verify device is online
   - May need to re-authenticate

4. **Reload YAML configuration**
   - Developer Tools > YAML > All YAML configuration
   - Alternatively: Settings > System > Restart

---

## Template Sensors Not Created

### Symptoms
- Can't find `sensor.elderly_care_status`
- Template errors in logs
- "Entity not found" errors

### Solutions

1. **Check YAML syntax** (especially indentation)
   ```
   Developer Tools > YAML > Check Configuration
   ```

2. **View logs for errors**
   ```
   Settings > System > Logs
   Filter: "haiven" or "template"
   ```

3. **Verify configuration.yaml includes packages**
   ```yaml
   homeassistant:
     packages:
       haiven_care_circle_inputs: !include packages/haiven_care_circle_inputs.yaml
       haiven_monitoring_inputs: !include packages/haiven_monitoring_inputs.yaml
       haiven_comms_inputs: !include packages/haiven_comms_inputs.yaml
       haiven_sensors_3sensor: !include haiven_sensors_3sensor.yaml
       haiven_bathroom_night: !include packages/haiven_bathroom_night.yaml
       haiven_circle_tracking: !include packages/haiven_circle_tracking.yaml
       haiven_drift: !include packages/haiven_drift.yaml
       haiven_night_insights: !include packages/haiven_night_insights.yaml
       haiven_movement: !include packages/haiven_movement.yaml
   ```
   If yours is shorter than this, `git pull` — a package is missing.

4. **Force reload**
   - Developer Tools > YAML > All YAML configuration

---

## Notifications Not Sending

### Symptoms
- Scripts run but no notification received
- No errors shown
- Notifications missing on phone

### Solutions

1. **Verify notification service name**
   - Developer Tools > Actions > Search "notify"
   - Copy exact service name (case-sensitive)
   - Update `input_text.contact_N_notification`

2. **Test manually**
   ```
   Developer Tools > Actions
   Service: notify.mobile_app_xxxxx
   Message: "Test from Haiven"
   Perform Action
   ```

3. **Check phone notification settings**
   - iOS: Settings > Notifications > Home Assistant > Allow
   - Android: Settings > Apps > Home Assistant > Notifications > Enabled

4. **Check Do Not Disturb**
   - Ensure phone isn't in silent/DND mode

5. **Check battery optimization (Android)**
   - Settings > Apps > Home Assistant > Battery > Unrestricted

---

## Too Many False Alarms

### Symptoms
- Alerts when everything is fine
- Status frequently reaches caution or above for no real reason
- Wake-up alerts even when person is up

### Solutions

1. **Increase thresholds**
   ```yaml
   wake_time_variance_minutes: 180 (try 3 hours)
   no_activity_alert_hours: 6 (try 6 hours)
   ```

2. **Update expected times to match actual routine**
   - Developer Tools > States > `input_datetime.expected_wake_time`
   - Set to actual typical wake time

3. **Check sensor placement**
   - Kitchen sensor placement might not cover all activity areas
   - Bedroom sensor may be detecting hallway
   - Bathroom sensor may have poor coverage

---

## Missing Real Issues

### Symptoms
- No alert when should have triggered
- Status stays green when something's wrong
- Activity not being logged

### Solutions

1. **Decrease thresholds**
   ```yaml
   wake_time_variance_minutes: 60 (1 hour)
   no_activity_alert_hours: 2 (2 hours)
   ```

2. **Verify sensors are triggering**
   - Developer Tools > States > Watch sensor states
   - Walk past each sensor and confirm state changes

3. **Check automation traces**
   - Settings > Automations > Find automation > Traces
   - See why it didn't trigger

---

## Bedtime Not Recording

### Symptoms
- `input_datetime.actual_bedtime_today` stays at 00:00
- Bedtime automation never triggers

### Solutions

1. **Check pattern sensor**
   - Developer Tools > States > `binary_sensor.bedtime_pattern_detected`
   - Should show "on" after bathroom > bedroom sequence

2. **Check window timing**
   - Detection window: 17:30 - 21:30
   - Bedtime must fall within this range

3. **Verify bathroom > bedroom sequence**
   - Bathroom motion triggers first
   - Bedroom occupancy within 30 minutes

4. **Check if already set today**
   - If `actual_bedtime_today` has a value, automation won't fire again
   - Resets at noon daily

5. **Manual reset if stuck**
   ```
   Developer Tools > Actions > input_datetime.set_datetime
   Entity: input_datetime.actual_bedtime_today
   Time: 00:00:00
   ```

---

## Location/Proximity Showing "Unknown"

### Symptoms
- Contact location shows "unknown"
- Person entity shows no location
- Proximity calculations fail

### Solutions

1. **Verify person entity exists**
   - Developer Tools > States > Filter: `person.`
   - Check the entity_id matches what's in `input_text.contact_N_person`

2. **Check device tracker is linked**
   - The person entity needs a device_tracker assigned
   - Check `haiven_persons.yaml` has correct device_tracker

3. **Check location permissions on phone**
   - iOS: Settings > Home Assistant > Location > Always
   - Android: Settings > Apps > Home Assistant > Permissions > Location > Allow all the time

4. **Restart Home Assistant**
   - Required after YAML changes to person entities

5. **Manually set if initial values didn't apply**
   ```
   Developer Tools > Actions > input_text.set_value
   Entity: input_text.contact_1_person
   Value: person.contact_1
   ```

---

## Status Always Shows "Unknown"

### Symptoms
- `sensor.elderly_care_status` shows "Unknown"
- Dashboard status circle empty

### Solutions

1. **Check input helpers exist**
   - Settings > Helpers
   - Verify all required helpers created

2. **Verify template sensors loaded**
   - Developer Tools > States > Filter: "elderly_care"

3. **Check for template errors in logs**
   - Settings > System > Logs
   - Look for Jinja2 template errors

4. **Verify sensor entity IDs**
   - Template sensors reference specific entity IDs
   - If your sensors have different IDs, update `haiven_sensors_3sensor.yaml`

---

## Device Tracker Shows "Unavailable"

### Symptoms
- Phone location not updating
- Device tracker shows "unavailable" state

### Solutions

1. **Check phone location services are ON**

2. **Check HA mobile app has "Always" location permission**

3. **Restart the HA mobile app**

4. **Disable battery optimization for HA app**
   - Android: Settings > Apps > Home Assistant > Battery > Unrestricted
   - iOS: Ensure Low Power Mode is OFF

5. **Check phone has internet connection**

---

## Bathroom Sensor Not Working

### Symptoms
- Bathroom activity not detected
- Sensor shows "unavailable"

### Solutions

1. **Check battery level**
   - Developer Tools > States > `sensor.haiven_bathroom_battery`
   - Replace battery if below 20%

2. **Verify sensor is online**
   - Developer Tools > States > `binary_sensor.haiven_bathroom_motion`
   - State should be "on" or "off", not "unavailable"

3. **Test by walking in bathroom**
   - Sensor should change to "on"
   - May have 2-3 second delay

4. **If entity ID changed**
   - Update `haiven_sensors_3sensor.yaml`
   - Reload YAML

---

## MMW Bedroom Sensor Issues

This is an LD2450 radar on a custom ESPHome build (not the stock firmware, not LD2410) — see [SENSOR_GUIDES.md](SENSOR_GUIDES.md) for the full architecture note and the gap in what this repo currently publishes for it.

### Always Shows "Occupied"

**Causes:**
- A zone boundary extends into a hallway or doorway
- Air vent causing constant movement inside a zone

**Fixes:**
1. Tighten the zone in the [Everything Presence zone configurator](https://github.com/EverythingSmartHome/everything-presence-addons)
2. Reposition the sensor away from vents

### Never Shows "Occupied"

**Causes:**
- Sensor not aimed at the bed
- Zone doesn't cover where the person actually sleeps

**Fixes:**
1. Check sensor physical positioning
2. Redraw the zone in the configurator to actually cover the bed

### False Wake-ups During Sleep

**Causes:**
- A zone extends too far, catching movement outside the bed

**Fixes:**
1. Narrow the zone
2. Check for a fan or AC unit inside the zone boundary

---

## Dashboard Shows No Cards

### Symptoms
- The "Haiven" sidebar item exists and opens, but the page is blank or shows raw card-not-found errors
- Browser console shows a 404 for `/local/haiven-cards.js` or `/local/haiven-loader.js`

### Solutions

1. **Check the files actually deployed**
   - `www-src/haiven-cards.js` and `www-src/haiven-loader.js` are the source; Home Assistant serves from `www/`, which is gitignored and empty on a fresh clone
   - `scripts/setup.sh` copies them across as its last step — if you skipped it or ran it before this deploy step existed, re-run it, or manually: `cp www-src/haiven-cards.js www-src/haiven-loader.js www/`

2. **Check `frontend.extra_module_url` in `configuration.yaml`**
   - Should include `/local/haiven-loader.js?v=2`
   - Restart required after adding it — a YAML reload alone won't pick up a new frontend module

3. **Hard-refresh the browser**
   - The card loader deliberately busts its own cache on every load, but a stale service worker can still serve an old copy once — reload twice if the first load after a deploy looks wrong

---

## Drift Watch / Night Insights / Movement Not Working

### Symptoms
- `sensor.drift_stats`, `sensor.night_stats`, or `sensor.movement_stats` shows "unavailable"
- The dashboard's Drift Watch row shows "Learning" indefinitely

### Solutions

1. **"Learning" is expected, not a bug, for the first 28 nights**
   - Drift Watch needs 28 completed nights before it has a baseline. Night insights and movement need much less history (a few nights, a week respectively) — if those are also stuck, that's a real problem; Drift Watch alone showing "Learning" for under a month is normal.

2. **Check the command_line sensor itself**
   - Developer Tools > States > `sensor.drift_stats` / `sensor.night_stats` / `sensor.movement_stats`
   - "unavailable" means the underlying script failed — check `python3 /config/scripts/drift_stats.py` (or `night_stats.py`, `movement_today.py`) runs cleanly from a terminal on the HA host

3. **Check `activity.log` exists and has entries**
   - All three scripts read from this log; an empty or missing log means no data to build a baseline from

---

## Debugging Commands

### Check Sensor States
```
Developer Tools > States > Search:
- event.kitchen_motion
- binary_sensor.haiven_bedroom_occupancy
- binary_sensor.haiven_bathroom_motion
```

### Check Template Sensors
```
Developer Tools > States > Search: elderly_care
```

### Test Automation
```
Settings > Automations > Find automation > Run
Check "Traces" to see what happened
```

### View Logs
```
Settings > System > Logs
Filter: "haiven" or "elderly"
```

### Check YAML Syntax
```
Developer Tools > YAML > Check Configuration
```

### Restart Home Assistant
```
Settings > System > Restart
```

### Test Notification
```
Developer Tools > Actions
Service: notify.mobile_app_xxxxx
Message: "Test"
Perform Action
```

---

## Reset Timing Reference

| What | Resets At |
|------|-----------|
| Bedtime/bathroom counter | 12:00 noon |
| Wake time/daily flags | 00:00 midnight |
| Manual safe status | 00:00 midnight |
| Deviation alert sent flag | 00:00 midnight |

---

## Getting More Help

1. **Check the logs first** - Most issues leave traces
2. **Review automation traces** - See exactly what happened
3. **Test sensors individually** - Isolate the problem
4. **Verify entity IDs match** - Most common issue

For hardware-specific issues:
- See [SENSOR_GUIDES.md](SENSOR_GUIDES.md) for detailed sensor documentation

---

*Last Updated: 2026-09-19*
