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

### Planning

| Document | Description |
|----------|-------------|
| [PRD_AI_AGENT](planning/PRD_AI_AGENT.md) | Product requirements for AI agent features |
| [STRATEGIC_ANALYSIS](planning/STRATEGIC_ANALYSIS.md) | System analysis and roadmap |

### Internal

| Document | Description |
|----------|-------------|
| [BEDTIME_DETECTION_V4](internal/BEDTIME_DETECTION_V4.md) | Technical notes on bedtime algorithm |

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
Kitchen (Ring Camera)    -> Morning activity, meals
Bedroom (MMW Presence)   -> Sleep, wake-up, rest
Bathroom (PIR Motion)    -> Routine, bathroom breaks
```

### Status Indicators

- **Green:** Routine normal
- **Orange:** Potential deviation (1-2 hours off)
- **Red:** Alert (4+ hours, needs attention)

### Configuration Architecture

- **Central config:** `haiven_inputs.yaml`
- **Contact pattern:** `contact_1_*`, `contact_2_*`, etc.
- **Single source of truth:** All scripts/automations read from input helpers

---

## Key Files

| File | Purpose |
|------|---------|
| `haiven_inputs.yaml` | All input helpers (central config) |
| `haiven_sensors_3sensor.yaml` | Template sensors |
| `haiven_persons.yaml` | Person entity definitions |
| `scripts.yaml` | Notification scripts |
| `automations.yaml` | Monitoring automations |
| `CLAUDE.md` | Development instructions |

---

## Version

**Haiven v1.0** - 3-Sensor Configuration
**Updated:** 2026-02-04
**Home Assistant:** 2024.1+

---

*For development instructions, see `/CLAUDE.md` in the project root.*
