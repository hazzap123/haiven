# Haiven

**Elderly care monitoring for Home Assistant.** Tracks daily activity patterns using motion and presence sensors, detects routine deviations, and alerts caregivers.

THIS IS NOT A MEDICAL SYSTEM - it was built as a personal project, it's at best a wellness / wellbeing support aid. No warranties and doesn't replace human care, love and decency, but can take the edge off some of the anxiety of caring for someone at a distance.

## What it does

- Tracks wake time, bedtime, and room-to-room movement using 3 sensors
- Calculates a daily activity score and 5-level status (normal to critical)
- Sends AI-generated morning, afternoon, and evening summaries to carers
- Alerts on missed wake times, prolonged inactivity, unusual bathroom visits, and more
- Care circle tracking — knows which carer is nearest during an alert
- Dashboard with live status, activity timeline, and weekly trends

## What you need

**Hardware (3 sensors):** you can add more but will need to configure for that.
- Kitchen: Motion or presence sensor (Ring camera with motion, MMW Zigbee PIR, etc.)
- Bedroom: Motion or Presence sensor with zone support if want in bed detection
- Bathroom: Motion sensor (Shelly BLU Motion, Zigbee PIR, etc.)

**Software:**
- Home Assistant 2024.1+
- HACS (for dashboard card dependencies)
- Optional: Anthropic API key (for AI-generated summaries via Claude) or any other llm you like

## Quick start

```bash
# 1. Clone into your HA config directory
git clone https://github.com/hazzap123/haiven.git /config

# 2. Run the setup script to configure your sensor entity IDs
bash scripts/setup.sh

# 3. Copy and configure secrets
cp secrets.yaml.example secrets.yaml
# Edit secrets.yaml with your values

# 4. Edit person and contact configuration
# Edit haiven_persons.yaml with your household members
# Edit packages/haiven_care_circle_inputs.yaml with carer details

# 5. Restart Home Assistant
```

See [docs/setup/QUICKSTART.md](docs/setup/QUICKSTART.md) for the full 30-minute setup guide.

## Documentation

| Guide | Description |
|-------|-------------|
| [Quick Start](docs/setup/QUICKSTART.md) | 30-minute fast path |
| [Complete Setup](docs/setup/COMPLETE_SETUP.md) | Full installation guide |
| [Care Circle](docs/setup/CARE_CIRCLE.md) | Contact and notification setup |
| [Entity Reference](docs/reference/ENTITY_REFERENCE.md) | All entity IDs |
| [Sensor Guides](docs/reference/SENSOR_GUIDES.md) | Hardware configuration |
| [Troubleshooting](docs/reference/TROUBLESHOOTING.md) | Problem solving |

## How it works

Haiven triangulates location from 3 sensors to build a picture of daily activity:

| Time | Typical Pattern | Primary Sensor |
|------|----------------|----------------|
| 04:30-05:30 | Wake — first kitchen motion | Kitchen |
| Daytime | Kitchen/living room activity | Kitchen |
| 17:30-19:30 | Bedtime routine | Bathroom then Bedroom |
| Night | Occasional bathroom visits | Bathroom |

Deviations from this pattern trigger escalating alerts — from a gentle "check in" to urgent notifications to the nearest carer.

## Architecture

```
configuration.yaml               # Main config — includes all packages
├── automations.yaml              # All automation logic
├── haiven_sensors_3sensor.yaml   # Template sensors (status, scoring, timing)
├── scripts.yaml                  # Notification and utility scripts
├── packages/
│   ├── haiven_care_circle_inputs.yaml   # Contact configuration
│   ├── haiven_monitoring_inputs.yaml    # Thresholds and state machines
│   ├── haiven_comms_inputs.yaml         # Summary and alert text
│   ├── haiven_bathroom_night.yaml       # Night bathroom monitoring
│   └── haiven_circle_tracking.yaml      # Care circle location sensors
├── haiven_persons.yaml           # Person entities
├── haiven_zones.yaml             # Geographic zones
└── lovelace/
    └── haiven_default.yaml       # Dashboard
```

## Licence

MIT — see [LICENSE](LICENSE).
