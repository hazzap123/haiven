# Haiven Entity Reference

Single source of truth for all entity IDs used in the Haiven monitoring system.

**Updated:** 2026-09-19

---

## Sensors

### Core Monitoring Sensors

| Entity ID | Type | Location | Description |
|-----------|------|----------|-------------|
| `event.kitchen_motion` | Event | Kitchen | Kitchen motion detection |
| `binary_sensor.haiven_bedroom_occupancy` | Binary | Bedroom | MMW presence (LD2450 radar — not LD2410, a different sensor with a different ESPHome component) |
| `binary_sensor.haiven_bathroom_motion` | Binary | Bathroom | Shelly BLU PIR motion |

### MMW Sensor Extended Entities

| Entity ID | Description |
|-----------|-------------|
| `binary_sensor.haiven_bedroom_moving_target` | Movement detected |
| `binary_sensor.haiven_bedroom_still_target` | Stationary presence (breathing) |
| `binary_sensor.haiven_bedroom_zone_1_occupancy` | Someone in zone 1 (the bed) |
| `binary_sensor.haiven_bedroom_zone_2_occupancy` | Someone in zone 2 (the rest of the room) |
| `binary_sensor.haiven_bedroom_target_1_active` | Target 1 is being tracked |
| `sensor.haiven_bedroom_target_1_speed` | Target 1 speed |

### Bathroom Sensor Extended

| Entity ID | Description |
|-----------|-------------|
| `sensor.haiven_bathroom_battery` | Battery percentage |

---

## Foundational Sensors

These sensors provide centralised logic used by multiple other sensors and automations. **Do not remove them** - many entities depend on them.

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
| `sensor.elderly_care_status` | Main status: `normal`, `monitoring`, `caution`, `concern`, `critical`, or `away` — see [STATUS_SPEC.md](STATUS_SPEC.md) |
| `sensor.status_severity_score` | The weighted score behind the status above (0-100+) |
| `sensor.last_activity_location` | Kitchen, Bedroom, or Bathroom |
| `sensor.last_activity_time` | "X minutes ago" format |
| `sensor.last_activity_display` | Combined location and time |
| `sensor.deviation_count` | Current deviation count (0, 1, 2+) |
| `sensor.current_deviation_message` | Text description of issue |
| `sensor.today_wake_time` | First activity time today |
| `sensor.sensor_health_status` | "All online", or which sensors are offline |
| `sensor.room_activity_summary` | Summary of today's activity |
| `binary_sensor.bedtime_pattern_detected` | Triggers bedtime automation |
| `sensor.elderly_person_location` | Human-readable location ("At Home", "Away", a zone name, or "Not Configured") for the dashboard's presence word and the Circles screen. Built by `packages/haiven_circle_tracking.yaml` from the person entity named in `input_text.elderly_person_entity`. |

### Drift Watch (`packages/haiven_drift.yaml`)

Raw stats come from `sensor.drift_stats` (excluded from the recorder — read its attributes, not its state). Everything else is derived from it:

| Entity ID | Purpose |
|-----------|---------|
| `sensor.drift_night_bathroom` / `_usual` / `_state` | Smoothed level, usual, and Learning/Steady/Watching/Changed state — bathroom visits |
| `sensor.drift_wake` / `_usual` / `_state` | Same, for first stirring |
| `sensor.drift_activity` / `_usual` / `_state` | Same, for daytime kitchen activity |
| `binary_sensor.drift_night_bathroom_changed` | On when the bathroom chart has tripped |
| `binary_sensor.drift_wake_changed` | On when the wake chart has tripped |
| `binary_sensor.drift_activity_changed` | On when the activity chart has tripped |

### Night Insights (`packages/haiven_night_insights.yaml`)

Raw stats come from `sensor.night_stats` (also excluded from the recorder):

| Entity ID | Purpose |
|-----------|---------|
| `sensor.bathroom_night_visits_avg` | 14-night baseline |
| `sensor.bathroom_night_visits_3n` | Average of the last 3 completed nights |
| `sensor.night_downstairs_trips` / `_avg` | Tonight's (or last night's) downstairs trips, and the 14-night average |
| `sensor.bathroom_night_trend` | "Rising" or "Steady" |
| `sensor.night_bathroom_visits` | Tonight's (or last night's) bathroom visits. The one count the dashboard, the AI summary, the visits-high flag and Ask all read |

### Movement (`packages/haiven_movement.yaml`)

| Entity ID | Purpose |
|-----------|---------|
| `sensor.movement_stats` | Raw stats (excluded from the recorder); `today` and `usual_by_now` attributes power the Home card's "Movement, all rooms" row |

### Routine (`packages/haiven_routine.yaml`)

Describes days; it never alerts. Needs 14 days of history before it judges a signal.

| Entity ID | Purpose |
|-----------|---------|
| `sensor.routine` | Today's verdict: "On track", "A little off", "Off track", "Away" or "Can't tell". The `why` attribute carries the reason |
| `sensor.routine_stats` | Raw stats (excluded from the recorder); `today`, `days` and `counts` attributes power the Home "Routine" row and the Patterns 30-day strip |

### Arrival (`haiven_sensors_3sensor.yaml`, `packages/haiven_comms_inputs.yaml`)

| Entity ID | Purpose |
|-----------|---------|
| `input_datetime.arrived_home` | When the person's phone last arrived home after 15 minutes or more away |
| `sensor.minutes_since_arrived_home` | Minutes since then. Counts as activity in every inactivity gap, so a trip out does not read as silence on return |

---

## Input Helpers

### Time Configuration

| Entity ID | Purpose | Default |
|-----------|---------|---------|
| `input_datetime.expected_wake_time` | Expected wake time | None: set it (starts 00:00) |
| `input_datetime.expected_bedtime` | Expected bedtime | None: set it (starts 00:00) |
| `input_datetime.bedtime_window_start` | Earliest time bedtime is looked for | 00:00 = not set: 3 hours before expected bedtime |
| `input_datetime.bedtime_window_end` | Latest time bedtime is looked for; may be after midnight | 00:00 = not set: 2 hours after expected bedtime |
| `input_datetime.wake_window_start` | Earliest time first activity counts as getting up | 00:00 = not set: 3 hours before expected wake |
| `sensor.bedtime_window` | The bedtime window in use, as `HH:MM-HH:MM`; `source` says whether it came from the helpers or expected bedtime | - |
| `sensor.wake_window_start` | The earliest wake time in use, as `HH:MM` | - |
| `binary_sensor.bedtime_window_active` | On while the bedtime window is open | - |
| `input_datetime.next_appointment` | Upcoming appointment | - |
| `input_boolean.haiven_ai_summaries` | AI wording of summaries and alerts. While off, nothing is sent to an AI provider | Off |
| `input_text.haiven_ai_agent` | Conversation agent used when AI wording is on | Empty: `conversation.claude_conversation` |
| `script.haiven_compose_message` | Returns the plain text, or the agent's wording of it when AI wording is on and the call succeeds | - |
| `input_datetime.actual_bedtime_today` | Recorded bedtime | Resets noon |

### Alert Thresholds

| Entity ID | Purpose | Default |
|-----------|---------|---------|
| `input_number.wake_time_variance_minutes` | Acceptable wake variance | None: starts at 15 min; 120 suggested |
| `input_number.bedtime_variance_minutes` | Acceptable bedtime variance | None: starts at 15 min; 60 suggested |
| `input_number.no_activity_alert_hours` | Hours before alert | None: starts at 2 h; 4 suggested |

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

`haiven_zones.yaml` has commented-out examples (a contact's home and work, GP surgery, pharmacy). Uncomment and edit the ones you want; they are not created by default.

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
| `packages/haiven_care_circle_inputs.yaml` | Carer/contact input helpers |
| `packages/haiven_monitoring_inputs.yaml` | Thresholds and state machines |
| `packages/haiven_comms_inputs.yaml` | Summary and alert text |
| `packages/haiven_drift.yaml` | Drift Watch sensors and alert |
| `packages/haiven_night_insights.yaml` | Nightly bathroom-visit and downstairs-trip stats |
| `packages/haiven_movement.yaml` | Today's all-room movement vs a 7-day average |
| `packages/haiven_routine.yaml` | Daily routine verdict against the last 28 days |
| `haiven_sensors_3sensor.yaml` | Core template sensors |
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

*Last Updated: 2026-09-19*
