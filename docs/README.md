# Haiven Documentation

Elderly care monitoring system for Home Assistant.

---

## Quick Links

| Fast Path | Full Guide | Problems |
|-----------|------------|----------|
| [30-Min Setup](setup/QUICKSTART.md) | [Complete Setup](setup/COMPLETE_SETUP.md) | [Troubleshooting](reference/TROUBLESHOOTING.md) |

---

## Documentation Index

### Setup Guides

| Guide | Description | Time |
|-------|-------------|------|
| [QUICKSTART](setup/QUICKSTART.md) | Get basic monitoring working fast | 30 min |
| [COMPLETE_SETUP](setup/COMPLETE_SETUP.md) | Full installation with all features | 2 hours |
| [CARE_CIRCLE](setup/CARE_CIRCLE.md) | Add caregivers, notifications, location tracking | 30 min |

### Reference

| Guide | Description |
|-------|-------------|
| [ENTITY_REFERENCE](reference/ENTITY_REFERENCE.md) | All entity IDs (single source of truth) |
| [TROUBLESHOOTING](reference/TROUBLESHOOTING.md) | Common problems and solutions |
| [SENSOR_GUIDES](reference/SENSOR_GUIDES.md) | Hardware setup, configuration, reset procedures |

---

## What Do You Need?

| If you want to... | Go to... |
|-------------------|----------|
| Get started quickly | [QUICKSTART](setup/QUICKSTART.md) |
| Do a full installation | [COMPLETE_SETUP](setup/COMPLETE_SETUP.md) |
| Add people to care circle | [CARE_CIRCLE](setup/CARE_CIRCLE.md) |
| Fix a problem | [TROUBLESHOOTING](reference/TROUBLESHOOTING.md) |
| Look up an entity ID | [ENTITY_REFERENCE](reference/ENTITY_REFERENCE.md) |
| Configure a sensor | [SENSOR_GUIDES](reference/SENSOR_GUIDES.md) |

---

## System Overview

### 3-Sensor Monitoring

```
Kitchen/Living Room (Motion sensor)  -> Morning activity, meals
Bedroom (MMW Presence)   -> Sleep, wake-up, rest
Bathroom (PIR Motion)    -> Routine, bathroom breaks
```

### Status Indicators

Five levels, not three — see [STATUS_SPEC](reference/STATUS_SPEC.md) for the full severity scoring:

- **Normal / Monitoring:** green / teal, no action needed
- **Caution:** orange, worth a look
- **Concern / Critical:** red, needs attention
- **Away:** grey, person isn't home

### Configuration Architecture

- **Config lives in `packages/`:** `haiven_care_circle_inputs.yaml` (contacts), `haiven_monitoring_inputs.yaml` (thresholds), `haiven_comms_inputs.yaml` (alert and summary text)
- **Contact pattern:** `contact_1_*`, `contact_2_*`, etc.
- **Single source of truth:** All scripts/automations read from input helpers

---

## Key Files

| File | Purpose |
|------|---------|
| `packages/haiven_care_circle_inputs.yaml` | Carer/contact input helpers |
| `packages/haiven_monitoring_inputs.yaml` | Thresholds and state machines |
| `packages/haiven_comms_inputs.yaml` | Summary and alert text |
| `packages/haiven_drift.yaml` | Drift Watch: a month of nights against a frozen baseline |
| `packages/haiven_night_insights.yaml` | Nightly bathroom-visit and downstairs-trip stats |
| `packages/haiven_movement.yaml` | Today's all-room movement vs a 7-day average |
| `haiven_sensors_3sensor.yaml` | Core template sensors (status, scoring, timing) |
| `haiven_persons.yaml` | Person entity definitions |
| `scripts.yaml` | Notification scripts |
| `automations.yaml` | Monitoring automations |
| `www-src/haiven-cards.js` | Dashboard card library — deployed to `www/` by `scripts/setup.sh` |
| `lovelace/haiven_default.yaml` | The dashboard itself |

---

## Version

**Haiven** - 3-Sensor Configuration
**Updated:** 2026-09-19
**Home Assistant:** 2024.1+
