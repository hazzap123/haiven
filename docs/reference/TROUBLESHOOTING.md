# Haiven Troubleshooting Guide

Consolidated troubleshooting for all Haiven components.

**Updated:** 2026-02-04

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

2. **Check Ring integration**
   - Settings > Integrations > Ring
   - Verify camera is online
   - May need to re-authenticate

3. **Check ESPHome integration (bedroom sensor)**
   - Settings > Integrations > ESPHome
   - Verify device shows connected
   - Check WiFi signal strength

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
       haiven_inputs: !include haiven_inputs.yaml
       haiven_sensors_3sensor: !include haiven_sensors_3sensor.yaml
   ```

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
- Status changes to orange frequently
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
   - Ring camera might not see all kitchen activity
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

### Always Shows "Occupied"

**Causes:**
- Detection distance too far (detecting hallway)
- Far zones enabled (detecting door area)
- Air vent causing constant movement

**Fixes:**
1. Reduce detection distance to 3 meters
2. Disable zones 4-8 (via Everything Presence Configurator)
3. Reposition sensor away from vents

### Never Shows "Occupied"

**Causes:**
- Sensitivity too low
- Sensor not aimed at bed
- Firmware issue

**Fixes:**
1. Increase both sensitivities to 90%
2. Check sensor physical positioning
3. Update firmware via configurator

### False Wake-ups During Sleep

**Causes:**
- Movement sensitivity too high
- Fan/AC movement detected

**Fixes:**
1. Decrease movement sensitivity to 50-60%
2. Disable far zones
3. Adjust sensor angle

---

## Known Quirks (Not Bugs)

### ESPHome "Max Command Length" Warning

```
[W][ld2410:598]: Max command length exceeded; ignoring
```

**This is normal** with LD2410 firmware 2.04.x. The warning is intentionally suppressed in production config. The sensor works fine despite this message.

### Kitchen Evening Activity (Dogs)

Late evening kitchen motion (22:00-23:00) is almost always dogs, not mum. This is why kitchen is ignored for bedtime detection.

### MMW Brief "Off" States

Brief "off" states when lying still are normal (not "left room"). Only sustained gaps (20+ min) indicate actual movement. The presence timeout handles this.

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

*Last Updated: 2026-02-04*
