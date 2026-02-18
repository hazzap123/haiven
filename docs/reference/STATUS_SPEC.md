# Haiven Status Levels Specification

5-level severity-weighted status system for elderly care monitoring.

---

## Status Hierarchy

| Level | State | Triggers | Color | Icon |
|-------|-------|----------|-------|------|
| 0 | `normal` | No deviations, activity within bounds | Green (#6BBD6B) | mdi:check-circle |
| 1 | `monitoring` | Minor variance (1hr gap, wake slightly late) | Teal (#26A69A) | mdi:information |
| 2 | `caution` | Notable deviation (2hr gap, wake >60min late) | Orange (#F5A647) | mdi:alert |
| 3 | `concern` | Significant issues (3hr+ gap, room transition failed) | Red (#E74C3C) | mdi:alert-circle |
| 4 | `critical` | Emergency (4hr+ gap, multiple concerns) | Dark Red (#B71C1C) | mdi:alert-octagon |
| - | `away` | Person not home (device tracker) | Grey (#9E9E9E) | mdi:home-export-outline |

---

## Severity Scoring

The status is determined by a weighted severity score calculated by `sensor.status_severity_score`.

### Score Thresholds

| Score Range | Status |
|-------------|--------|
| 0-9 | `normal` |
| 10-24 | `monitoring` |
| 25-49 | `caution` |
| 50-74 | `concern` |
| 75+ | `critical` |

### Scoring Rules

| Condition | Score | Configurable Via |
|-----------|-------|------------------|
| Wake 30-60min late | +10 | `input_number.wake_time_variance_minutes` |
| Wake >60min late | +25 | `input_number.wake_time_variance_minutes` |
| No activity 1hr (60min) | +10 | `input_number.status_gap_monitoring_mins` |
| No activity 2hr (120min) | +25 | `input_number.status_gap_caution_mins` |
| No activity 3hr (180min) | +50 | `input_number.status_gap_concern_mins` |
| No activity 4hr+ (240min) | +75 | `input_number.status_gap_critical_mins` |
| Room transition timeout | +30 | `input_number.transition_timeout_mins` |

### Score Bypass

Score returns `0` when:
- `input_boolean.manual_safe_status` is ON
- `binary_sensor.elderly_person_home` is OFF (person away)

---

## Configurable Thresholds

All thresholds are configurable via input_number helpers in Settings.

| Helper | Default | Range | Purpose |
|--------|---------|-------|---------|
| `status_gap_monitoring_mins` | 60 | 30-180 | Minutes of inactivity → monitoring |
| `status_gap_caution_mins` | 120 | 60-300 | Minutes of inactivity → caution |
| `status_gap_concern_mins` | 180 | 90-360 | Minutes of inactivity → concern |
| `status_gap_critical_mins` | 240 | 120-480 | Minutes of inactivity → critical |
| `transition_timeout_mins` | 15 | 5-60 | Minutes to wait for arrival in another room |
| `safe_status_duration_hours` | 2 | 1-8 | Hours before "Mark Safe" auto-expires |

---

## Room Transition Detection

**Sensor:** `binary_sensor.room_transition_timeout`

Detects the "fell between rooms" scenario - person left one room but didn't appear in another.

### Logic

1. Check `binary_sensor.elderly_person_home` is ON (device tracker confirms home)
2. Track minutes since activity in each room
3. If ALL rooms quiet > `transition_timeout_mins` → sensor turns ON
4. Adds +30 to severity score when ON

### Prerequisites

- Device tracker must be configured (`input_text.elderly_person_entity`)
- Device tracker must show "home" state
- If device tracker unavailable/unknown/not configured, check is skipped entirely

---

## Notification Behavior

### Trigger Levels

| Status | Notification | Interruption Level |
|--------|--------------|-------------------|
| `normal` | None | - |
| `monitoring` | None (logged only) | - |
| `caution` | Yes | active |
| `concern` | Yes | time-sensitive |
| `critical` | Yes | time-sensitive |

### Notification Format

```
Title: [Icon] Haiven - [Status Text]
Body: [Status Text]. [Reason]. Last: [Room] at [Time]

Example:
Title: ⚠️ Haiven - Needs Attention
Body: Needs Attention. No activity detected in any room for over 2.1 hours. Last: Kitchen at 3 hours ago
```

---

## Manual Safe Status ("Mark Safe")

**Helper:** `input_boolean.manual_safe_status`

When enabled:
- Severity score returns 0
- Status shows `normal`
- Auto-expires after `safe_status_duration_hours`
- Can be triggered from dashboard status card (tap)
- Cleared automatically when new activity detected (after 15 min delay)

---

## Key Entities

### Sensors

| Entity | Purpose |
|--------|---------|
| `sensor.elderly_care_status` | Main status (normal/monitoring/caution/concern/critical/away) |
| `sensor.status_severity_score` | Calculated severity score (0-100+) |
| `binary_sensor.room_transition_timeout` | True when all rooms quiet beyond timeout |

### Attributes

**sensor.elderly_care_status:**
- `status_text` - Human-readable status label
- `severity_score` - Current score value
- `color` - Hex color for UI
- `level` - Numeric level (0-4)

**sensor.status_severity_score:**
- `gap_thresholds` - Current threshold settings
- `transition_timeout_active` - Whether room transition timeout is firing
- `manual_safe_active` - Whether manual safe is enabled
- `minutes_since_activity` - Minutes since any room had activity

---

## Dashboard Integration

### Header Card

Icon color changes based on status:
- normal → green
- monitoring → teal
- caution → orange
- concern/critical → red
- away → grey

### Status Detail Card

Shows when status is not normal/away:
- Primary: Status text
- Secondary: Reason + last activity
- Tap action: Mark Safe with confirmation
- Background color indicates severity

### Severity Score Chip

Shows current score with color-coded icon.

---

## Future Enhancements (Phase 2)

- Time-based escalation (re-alert after 15min if not resolved)
- Contact priority routing based on proximity
- Actionable notification buttons (Mark Safe, Call Now)

---

*Last updated: 2026-02-05*
