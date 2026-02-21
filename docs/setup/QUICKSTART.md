# Haiven Quick Start

**Get monitoring working in 30 minutes.**

---

## Your 3-Sensor Setup

| Sensor | Location | Entity |
|--------|----------|--------|
| Motion sensor | Kitchen | `event.kitchen_motion` |
| MMW Presence | Bedroom | `binary_sensor.haiven_bedroom_occupancy` |
| Shelly BLU Motion | Bathroom | `binary_sensor.haiven_bathroom_motion` |

---

## Step 1: Verify Sensors (2 min)

1. **Developer Tools > States**
2. Search for each entity above
3. Verify all show as available (not "unknown")

---

## Step 2: Verify Configuration (2 min)

Your `configuration.yaml` should have:

```yaml
homeassistant:
  packages:
    haiven_inputs: !include haiven_inputs.yaml
    haiven_sensors_3sensor: !include haiven_sensors_3sensor.yaml

script: !include scripts.yaml
automation: !include automations.yaml
```

Files should already be in place.

---

## Step 3: Create Essential Helpers (10 min)

**Settings > Helpers > + Create Helper**

| Helper | Type | Default |
|--------|------|---------|
| Expected Wake Time | Date/Time (time only) | 06:00 |
| Wake Variance | Number (15-120, step 15) | 120 min |
| No Activity Alert | Number (2-8, step 0.5) | 4 hours |
| Person Name | Text | "Margaret" (whatever name you use) |

---

## Step 4: Reload & Verify (5 min)

1. **Developer Tools > YAML > "All YAML configuration"**
2. **Developer Tools > States > Search: `elderly_care`**

Should see:
- `sensor.elderly_care_status`
- `sensor.last_activity_display`
- `sensor.deviation_count`
- `sensor.sensor_health_status`

---

## Step 5: Test (5 min)

1. Trigger your kitchen sensor
2. Check `sensor.last_activity_display` updates to "Kitchen"
3. Enter bedroom > Check updates to "Bedroom"
4. Use bathroom > Check updates to "Bathroom"

---

## Simple Dashboard

**Settings > Dashboards > + Add Dashboard**

Paste this minimal view:

```yaml
title: Haiven - [Person Name]
views:
  - title: Status
    cards:
      - type: entities
        title: Current Status
        entities:
          - sensor.elderly_care_status
          - sensor.last_activity_display
          - sensor.deviation_count
          - sensor.sensor_health_status

      - type: entities
        title: Room Activity
        entities:
          - entity: event.kitchen_motion
            name: Kitchen
            secondary_info: last-changed
          - entity: binary_sensor.haiven_bedroom_occupancy
            name: Bedroom
            secondary_info: last-changed
          - entity: binary_sensor.haiven_bathroom_motion
            name: Bathroom
            secondary_info: last-changed
```

---

## What This Monitors

### Morning Routine
- Alert if no activity by expected wake + variance
- Example: Wake 06:00, variance 2hr = Alert at 08:00

### All-Day Activity
- Alert if no sensor activity for X hours
- Example: 4hr threshold = Alert after 4 hours silence

### Status Meaning
- **Green:** All good, routine normal
- **Orange:** Potential deviation, monitor closely
- **Red:** Alert, immediate attention needed

---

## Tuning Recommendations

**Start with (fewer false alarms):**
```
wake_time_variance_minutes: 120 (2 hours)
no_activity_alert_hours: 4
```

**If too many alerts:** Increase variance to 180 (3 hours)

**If missing issues:** Decrease variance to 60 (1 hour)

---

## Add Notifications (Optional)

1. Find your notification service:
   - Developer Tools > Actions > Search "notify"
   - Copy service name (e.g., `notify.mobile_app_your_phone`)

2. Update `haiven_inputs.yaml`:
   ```yaml
   contact_1_notification:
     initial: "notify.mobile_app_your_phone"
   ```

3. Restart Home Assistant

---

## Daily Use

**Morning:** Check status is green

**Throughout Day:** Dashboard shows last activity

**Evening:** Verify daytime was normal

---

## Next Steps

1. **Run for 1 week** with current settings
2. **Track false alarms** - adjust thresholds
3. **Tune wake time** - match actual routine
4. **Add notifications** - See [CARE_CIRCLE.md](CARE_CIRCLE.md)
5. **Full guide** - See [COMPLETE_SETUP.md](COMPLETE_SETUP.md)

---

## Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| Sensors not updating | Check entity IDs, reload YAML |
| Status "Unknown" | Create input helpers |
| Too many alerts | Increase variance |
| Missing issues | Decrease variance |

Full troubleshooting: [../reference/TROUBLESHOOTING.md](../reference/TROUBLESHOOTING.md)

---

## Quick Reference

**Entity IDs:** See [../reference/ENTITY_REFERENCE.md](../reference/ENTITY_REFERENCE.md)

**Key Sensors:**
- Status: `sensor.elderly_care_status`
- Last Activity: `sensor.last_activity_display`
- Deviations: `sensor.deviation_count`

**Config Files:**
- Sensors: `haiven_sensors_3sensor.yaml`
- Inputs: `haiven_inputs.yaml`
- Scripts: `scripts.yaml`
- Automations: `automations.yaml`

---

**That's it! Basic monitoring is now active.**

---

*Quick Start v1.0 - Updated 2026-02-04*
