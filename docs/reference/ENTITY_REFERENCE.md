# Haiven Entity Reference

Single source of truth for all entity IDs used in the Haiven monitoring system.

**Updated:** 2026-02-04

---

## Sensors

### Core Monitoring Sensors

Haiven uses three stable role aliases throughout all automations and sensors. Physical hardware is mapped to these roles in `haiven_sensor_roles.yaml` — run `bash scripts/setup.sh` to configure.

| Entity ID | Role | Location | Description |
|-----------|------|----------|-------------|
| `binary_sensor.haiven_activity_sensor` | `activity` | Kitchen / living area | First trigger = wake time; daytime movement baseline |
| `binary_sensor.haiven_bed_sensor` | `bed` | Bedroom | Presence detection; sleep/wake state |
| `binary_sensor.haiven_bath_sensor` | `bath` | Bathroom | Night visit counting; routine tracking |

### MMW Sensor Extended Entities

| Entity ID | Description |
|-----------|-------------|
| `binary_sensor.haiven_bedroom_moving_target` | Movement detected |
| `binary_sensor.haiven_bedroom_still_target` | Stationary presence (breathing) |
| `sensor.haiven_bedroom_detection_distance` | Distance to target (cm) |
| `sensor.haiven_bedroom_moving_energy` | Movement intensity (0-100) |
| `sensor.haiven_bedroom_still_energy` | Stationary intensity (0-100) |

### Bathroom Sensor Extended

| Entity ID | Description |
|-----------|-------------|
| `sensor.haiven_bathroom_battery` | Battery percentage |

---

## Foundational Sensors

These sensors provide centralized logic used by multiple other sensors and automations. **Do not remove them** - many entities depend on them.

| Entity ID | Purpose | Key Attributes |
|-----------|---------|----------------|
| `binary_sensor.elderly_person_home` | Is elderly person at home? | - |
| `sensor.activity_data` | Consolidated 3-sensor activity | `kitchen_last`, `bedroom_last`, `bathroom_last`, `latest_time`, `minutes_since_latest`, `hours_since_latest`, `previous_location`, `transition`, `rooms_active_today` |

**Usage examples:**
```yaml
# Check if person is away
{% if is_state('binary_sensor.elderly_person_home', 'off') %}

# Get minutes since last activity
{{ state_attr('sensor.activity_data', 'minutes_since_latest') }}

# Get current location
{{ states('sensor.activity_data') }}
```

---

## Template Sensors (Haiven-generated)

| Entity ID | Purpose |
|-----------|---------|
| `sensor.elderly_care_status` | Main status: all_good, potential_deviation, alert |
| `sensor.last_activity_location` | Kitchen, Bedroom, or Bathroom |
| `sensor.last_activity_time` | "X minutes ago" format |
| `sensor.last_activity_display` | Combined location and time |
| `sensor.deviation_count` | Current deviation count (0, 1, 2+) |
| `sensor.current_deviation_message` | Text description of issue |
| `sensor.today_wake_time` | First activity time today |
| `sensor.sensor_health_status` | "All Sensors Online" or issues |
| `sensor.room_activity_summary` | Summary of today's activity |
| `binary_sensor.bedtime_pattern_detected` | Triggers bedtime automation |

---

## Input Helpers

### Time Configuration

| Entity ID | Purpose | Default |
|-----------|---------|---------|
| `input_datetime.expected_wake_time` | Expected wake time | 05:30 |
| `input_datetime.expected_bedtime` | Expected bedtime | 21:00 |
| `input_datetime.expected_breakfast_time` | Expected breakfast | 07:00 |
| `input_datetime.next_appointment` | Upcoming appointment | - |
| `input_datetime.actual_bedtime_today` | Recorded bedtime | Resets noon |

### Alert Thresholds

| Entity ID | Purpose | Default |
|-----------|---------|---------|
| `input_number.wake_time_variance_minutes` | Acceptable wake variance | 120 min |
| `input_number.bedtime_variance_minutes` | Acceptable bedtime variance | 60 min |
| `input_number.no_activity_alert_hours` | Hours before alert | 4 hours |

### System Flags

| Entity ID | Purpose | Default |
|-----------|---------|---------|
| `input_boolean.haiven_monitoring_enabled` | Master on/off | ON |
| `input_boolean.manual_safe_status` | Manually marked safe | OFF |
| `input_boolean.deviation_alert_sent` | Alert sent today flag | OFF |

---

## Contact Configuration

### Elderly Person

| Entity ID | Purpose | Example Value |
|-----------|---------|---------------|
| `input_text.elderly_person_name` | Display name | "Your Person" |
| `input_text.elderly_person_entity` | Person entity | `person.elderly_person` |
| `input_text.elderly_person_device_tracker` | Phone tracker | `device_tracker.your_person_phone` |

### Contact Pattern (contact_1, contact_2, etc.)

Each contact follows this pattern:

| Pattern | Purpose | Example (Contact 1) |
|---------|---------|---------------------|
| `input_text.contact_N_name` | Display name | "Carer 1" |
| `input_text.contact_N_type` | primary/secondary | "primary" |
| `input_text.contact_N_person` | Person entity | `person.contact_1` |
| `input_text.contact_N_device_tracker` | Phone tracker | `device_tracker.carer_1_phone` |
| `input_text.contact_N_phone` | Phone number | "+44 0000..." |
| `input_text.contact_N_notification` | Notification service | `notify.mobile_app_your_phone` |

### Current Contacts

| Contact | Name | Person Entity | Device Tracker |
|---------|------|---------------|----------------|
| Contact 1 | Carer 1 | `person.contact_1` | `device_tracker.carer_1_phone` |
| Contact 2 | Carer 2 | `person.contact_2` | `device_tracker.carer_2_phone` |

---

## Person Entities

| Entity ID | Description |
|-----------|-------------|
| `person.elderly_person` | Elderly person being monitored |
| `person.contact_1` | Contact 1 (primary) |
| `person.contact_2` | Contact 2 (primary) |

**Critical:** Always verify actual entity IDs in Developer Tools > States. HA may assign different IDs than expected.

---

## Notification Services

Find your notification service names in **Developer Tools > Actions** (search "notify").

| Service | Description |
|---------|-------------|
| `notify.mobile_app_your_phone` | Carer 1's phone |
| `notify.mobile_app_[device_name]` | Pattern for other devices |

---

## Zone Entities

| Entity ID | Description |
|-----------|-------------|
| `zone.home` | Elderly person's home (primary monitored location) |
| `zone.carer_1_home` | Carer 1's home |
| `zone.carer_1_office` | Carer 1's workplace |

---

## Scripts

| Entity ID | Purpose |
|-----------|---------|
| `script.notify_care_circle` | Send alert to all contacts |
| `script.manual_checkin` | Manual check-in confirmation |
| `script.mark_safe` | Clear alerts, mark safe |
| `script.add_care_note` | Add note to care log |
| `script.reset_daily_flags` | Reset daily tracking (midnight) |

---

## Configuration Files Reference

| File | Contains |
|------|----------|
| `haiven_sensor_roles.yaml` | Physical sensor → role mappings (only file with raw hardware IDs) |
| `haiven_inputs.yaml` | All input helpers (central config) |
| `haiven_sensors_3sensor.yaml` | Template sensors |
| `haiven_persons.yaml` | Person entity definitions |
| `scripts.yaml` | Action scripts |
| `automations.yaml` | Monitoring automations |

---

## Quick Lookup Commands

**Check all Haiven sensors:**
```
Developer Tools > States > Filter: elderly_care
```

**Check all input helpers:**
```
Developer Tools > States > Filter: input_text.contact_
Developer Tools > States > Filter: input_datetime.
Developer Tools > States > Filter: input_boolean.haiven
```

**Check all person entities:**
```
Developer Tools > States > Filter: person.
```

**Find notification services:**
```
Developer Tools > Actions > Search: notify
```

---

*Last Updated: 2026-02-04*
