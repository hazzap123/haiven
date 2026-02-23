# Haiven Complete Setup Guide

Full installation and configuration guide for the Haiven elderly care monitoring system.

**Version:** 1.0
**Updated:** 2026-02-04

---

## What is Haiven?

Haiven monitors daily activity patterns of an elderly person using motion and presence sensors, detects deviations from normal routines, and alerts caregivers when potential issues arise.

### Key Features

- **Visual Status Indicator**
  - Green: Routine normal
  - Orange: Potential deviation (1-2 hours off schedule)
  - Red: Alert (4+ hours, needs attention)

- **Activity Monitoring**
  - Real-time tracking across rooms
  - Wake-up and bedtime detection
  - Extended inactivity alerts

- **Care Circle Notifications**
  - Mobile alerts to multiple contacts
  - Actionable notifications (Mark Safe, View Dashboard)
  - Daily summary reports

---

## Prerequisites

### Hardware
- Home Assistant server (2024.1+)
- Motion or presence sensor (Kitchen or main living area)
- Everything Presence Lite MMW sensor (Bedroom)
- Shelly BLU Motion PIR sensor (Bathroom)
- Mobile devices for notifications

### Software
- HACS (Home Assistant Community Store)
- File Editor add-on (recommended)

### Custom Cards (via HACS > Frontend)
- [ ] button-card
- [ ] lovelace-card-mod
- [ ] lovelace-multiple-entity-row
- [ ] lovelace-auto-entities
- [ ] lovelace-mushroom (optional)

---

## Installation Checklist

### Pre-Installation (Verify)

- [ ] Home Assistant running (2024.1+)
- [ ] HACS installed
- [ ] File Editor add-on installed
- [ ] 3 physical sensors working — note each entity ID:
  - [ ] Kitchen/living area motion or presence sensor (any type)
  - [ ] Bedroom presence sensor (radar or PIR)
  - [ ] Bathroom motion sensor

### Step 1: Install Custom Cards (10 min)

1. Open **HACS** > **Frontend**
2. Click **+ Explore & Download Repositories**
3. Search and install each card
4. **Restart Home Assistant**

### Step 2: Verify Configuration Files (5 min)

Files should already be in `/config/`:

```
haiven_sensor_roles.yaml  <- Sensor role mappings (configure this first)
haiven_inputs.yaml        <- Input helpers
haiven_sensors_3sensor.yaml <- Template sensors
scripts.yaml              <- Notification scripts
automations.yaml          <- Monitoring automations
```

Check `configuration.yaml` includes:
```yaml
homeassistant:
  packages:
    haiven_inputs: !include haiven_inputs.yaml
    haiven_sensor_roles: !include haiven_sensor_roles.yaml
    haiven_sensors_3sensor: !include haiven_sensors_3sensor.yaml

script: !include scripts.yaml
automation: !include automations.yaml
```

### Step 2b: Map Your Sensors (5 min)

Run the interactive setup script to map your physical sensors to Haiven's three role aliases:

```bash
bash scripts/setup.sh
```

When prompted, enter the entity IDs of your three sensors (noted in Pre-Installation above):
- **Activity sensor** (kitchen/living area) — any motion or presence entity type
- **Bed sensor** (bedroom) — presence/occupancy sensor
- **Bath sensor** (bathroom) — motion sensor

This writes your sensor IDs into `haiven_sensor_roles.yaml` — the only file that contains raw hardware entity IDs. All automations and sensors use the stable aliases (`binary_sensor.haiven_activity_sensor`, `binary_sensor.haiven_bed_sensor`, `binary_sensor.haiven_bath_sensor`).

### Step 3: Configure Care Circle (30 min)

See [CARE_CIRCLE.md](CARE_CIRCLE.md) for detailed instructions.

**Quick summary:**

1. Install HA mobile app on each person's phone
2. Find notification service names (Developer Tools > Actions > search "notify")
3. Find device tracker names (Developer Tools > States > filter "device_tracker.")
4. Edit `haiven_inputs.yaml` with actual values:

**Required helpers:**

| Helper | Purpose |
|--------|---------|
| `input_text.elderly_person_name` | Name of the person being monitored |
| `input_text.elderly_person_entity` | Person entity ID |
| `input_text.contact_1_name` | Primary contact name |
| `input_text.contact_1_notification` | Notification service |
| ... | See [ENTITY_REFERENCE.md](../reference/ENTITY_REFERENCE.md) for complete list |

### Step 4: Create Input Helpers (10 min)

Go to **Settings > Helpers** and create (if not auto-created):

**Time Baselines:**
- `input_datetime.expected_wake_time` - Default: 06:00
- `input_datetime.expected_bedtime` - Default: 22:00

**Alert Thresholds:**
- `input_number.wake_time_variance_minutes` - Default: 120 (2 hours)
- `input_number.bedtime_variance_minutes` - Default: 60 (1 hour)
- `input_number.no_activity_alert_hours` - Default: 4 hours

**System Flags:**
- `input_boolean.haiven_monitoring_enabled` - Default: ON

### Step 5: Reload & Verify Sensors (5 min)

1. **Developer Tools > YAML > "All YAML configuration"**
2. **Developer Tools > States** > Search: `elderly_care`

Should see:
- [ ] `sensor.elderly_care_status`
- [ ] `sensor.last_activity_location`
- [ ] `sensor.last_activity_time`
- [ ] `sensor.last_activity_display`
- [ ] `sensor.deviation_count`
- [ ] `sensor.sensor_health_status`

Also verify the role alias sensors exist (search `haiven_activity`, `haiven_bed`, `haiven_bath`):
- [ ] `binary_sensor.haiven_activity_sensor`
- [ ] `binary_sensor.haiven_bed_sensor`
- [ ] `binary_sensor.haiven_bath_sensor`

### Step 6: Setup Dashboard (15 min)

**Option A: Use existing dashboard**
- Navigate to Settings > Dashboards
- Find "Haiven" dashboard

**Option B: Create new dashboard**
1. Settings > Dashboards > + ADD DASHBOARD
2. Name: "Haiven - [Person's Name] Status"
3. Edit > Raw Config Editor
4. Copy from `lovelace/dashboard_default.yaml`

**Verify:**
- [ ] Status circle displays (green/orange/red)
- [ ] Last activity shows correctly
- [ ] Sensor status displays

### Step 7: Test System (15 min)

**Test 1: Sensor Detection**
- [ ] Trigger kitchen sensor > `binary_sensor.haiven_activity_sensor` briefly shows `on`
- [ ] Enter bedroom > `binary_sensor.haiven_bed_sensor` shows `on`
- [ ] Use bathroom > `binary_sensor.haiven_bath_sensor` shows `on`
- [ ] `sensor.last_activity_display` shows correct room

**Test 2: Status Calculation**
- [ ] `sensor.elderly_care_status` shows "all_good"
- [ ] `sensor.deviation_count` is 0
- [ ] Dashboard status circle is green

**Test 3: Notifications**
- [ ] Developer Tools > Actions > `script.notify_care_circle`
- [ ] All contacts receive notification
- [ ] Action buttons work

**Test 4: Manual Controls**
- [ ] Dashboard "Check-in" button works
- [ ] Care circle receives confirmation

---

## Configuration

### Baseline Settings

Set these to match actual daily routine:

```yaml
Expected Wake Time: 06:00  # When typically gets out of bed
Expected Bedtime: 22:00    # When goes to bed
```

### Threshold Tuning

**Conservative (fewer false alarms):**
```yaml
wake_time_variance_minutes: 180  # 3 hours
bedtime_variance_minutes: 90     # 1.5 hours
no_activity_alert_hours: 6
```
Best for: Variable routines

**Moderate (balanced) - RECOMMENDED:**
```yaml
wake_time_variance_minutes: 120  # 2 hours
bedtime_variance_minutes: 60     # 1 hour
no_activity_alert_hours: 4
```
Best for: Regular routines

**Strict (early detection):**
```yaml
wake_time_variance_minutes: 60   # 1 hour
bedtime_variance_minutes: 30
no_activity_alert_hours: 2
```
Best for: Very consistent routines

---

## Week 1: Tune & Optimize

### Daily Tracking

```
Day 1:
  Actual wake time: ______
  False alerts: Yes/No
  Notes: _______________
```

### Adjustments

**If too many false alarms:**
- Increase `wake_time_variance_minutes` to 180
- Increase `no_activity_alert_hours` to 6
- Update expected times to match routine

**If missing real issues:**
- Decrease thresholds
- Check sensor placement
- Verify sensors triggering correctly

---

## Training Care Circle

### Show Each Person:

**On their phone:**
- [ ] How to access Haiven dashboard
- [ ] Status indicator meaning (green/orange/red)
- [ ] "Check-in" button
- [ ] "Mark Safe" button
- [ ] How to respond to alerts

**Emergency procedures:**
- [ ] What to do if RED alert
- [ ] Who to call first
- [ ] How to access camera views

---

## Status Determination

### How Status is Calculated

```yaml
# Green (All Good)
- Morning activity within expected time + variance
- No extended periods without activity
- All sensors responding

# Orange (Potential Deviation)
- Morning activity 1-2 hours late
- One deviation detected
- Manual monitoring recommended

# Red (Alert)
- No morning activity by expected + variance
- No activity for threshold hours
- Sensor offline
- Immediate attention needed
```

---

## Notification Types

### Morning Confirmation
```
Title: "Morning"
Message: "[Name] is up and about (06:45)"
Level: Passive
```

### Deviation Alert
```
Title: "Haiven Alert - [Name]"
Message: "No morning activity detected by expected time"
Level: Time-sensitive
Actions: [Mark Safe, View Dashboard, View Camera]
```

### Daily Summary
```
Title: "Daily Report - [Name]"
Message: "Wake: 06:45, Last activity: Kitchen, Status: All Good"
Level: Passive
```

---

## Key Automations

| Automation | Trigger | Action |
|------------|---------|--------|
| Morning Activity Check | Wake time + variance | Alert if no activity |
| No Activity Alert | Every hour | Alert if threshold exceeded |
| Status Change Notification | Status to orange/red | Notify care circle |
| Daily Reset | Midnight | Reset tracking flags |
| Bedtime Detection | Bathroom > Bedroom pattern | Record bedtime |

---

## Maintenance

### Daily
- Check dashboard for status
- Review any alerts

### Weekly
- Review false positive count
- Adjust thresholds if needed
- Check sensor battery levels

### Monthly
- Update expected times if routine changed
- Review care circle contacts
- Check automation traces for errors

---

## Related Documentation

- [QUICKSTART.md](QUICKSTART.md) - 30-minute fast path
- [CARE_CIRCLE.md](CARE_CIRCLE.md) - Adding people and phones
- [../reference/ENTITY_REFERENCE.md](../reference/ENTITY_REFERENCE.md) - All entity IDs
- [../reference/TROUBLESHOOTING.md](../reference/TROUBLESHOOTING.md) - Problem solving
- [../reference/SENSOR_GUIDES.md](../reference/SENSOR_GUIDES.md) - Hardware guides

---

*Last Updated: 2026-02-04*
