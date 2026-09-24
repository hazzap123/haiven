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
- Drift Watch: catches a routine sliding slowly over a month, the kind of change a day-to-day average can't see
- Sensor coverage screen: shows exactly what stops working when a sensor goes offline, not just that it did

## What you need

**Hardware (3 sensors):** you can add more but will need to configure for that.
- Main room: Motion or presence sensor (MMW radar, Zigbee PIR, etc.)
- Bedroom: Motion or Presence sensor with zone support if want in bed detection
- Bathroom: Motion sensor (Shelly BLU Motion, Zigbee PIR, etc.)

**Software:**
- Home Assistant 2024.1+
- [kiosk-mode](https://github.com/NemesisRE/kiosk-mode), installed through HACS. `configuration.yaml` loads it from `/hacsfiles/kiosk-mode/`, and the dashboard uses it to hide Home Assistant's header and sidebar.
- The Anthropic Conversation integration, with its conversation agent at `conversation.claude_conversation`. **Required, not optional:** the morning, afternoon and evening summaries and the deviation and no-activity alerts are all written by it, and without it those automations fail. Expect roughly $1-5 a month on Claude Haiku 4.5 ($1 per million input tokens, $5 per million output) for about ten calls a day; most of the cost is the entity list Assist sends with each call, so expose only what Haiven needs.

**Privacy:** every AI summary and AI alert sends the monitored person's recent activity (room, time, bathroom visits, wake and bedtime) to Anthropic's API. If that is not acceptable for the person you care for, do not install Haiven as it stands.

## Quick start

```bash
# 1. Clone somewhere OTHER than /config (it already holds your setup)
git clone https://github.com/hazzap123/haiven.git ~/haiven
cd ~/haiven

# 2. Set your sensor entity IDs. This rewrites every .yaml and .js file in
#    the clone, so run it here, never inside /config.
bash scripts/setup.sh

# 3. Copy the Haiven files into /config
cp -r packages scripts www www-src lovelace themes /config/
cp haiven_sensors_3sensor.yaml haiven_persons.yaml haiven_zones.yaml /config/
```

> **Do not overwrite your own `configuration.yaml`, `automations.yaml`, `scripts.yaml` or `scenes.yaml`.** If you have none of your own yet, copy Haiven's. Otherwise merge by hand: add Haiven's `homeassistant.packages`, `frontend`, `lovelace`, `shell_command`, `command_line`, `recorder` and `sensor` blocks to your `configuration.yaml`, and append Haiven's automations and scripts to yours. Copying over them deletes every automation and script you made in the UI.

Then, in `/config`:

1. Copy `~/haiven/secrets.yaml.example` to `/config/secrets.yaml` (or merge it into yours) and fill in your values.
2. Edit `haiven_persons.yaml` with your household members and `packages/haiven_care_circle_inputs.yaml` with carer details.
3. Restart Home Assistant.
4. Set the expected wake time, bedtime and thresholds on the dashboard's Settings screen (see the Quick Start). They have no defaults.

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

An example day (your times will differ):

| Time | Example Pattern | Primary Sensor |
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
├── scripts/                      # Python helpers the packages below shell out to
│   ├── night_stats.py            # Rebuilds each night from the activity log
│   ├── drift_stats.py            # Slow-drift detection over a month of nights
│   └── movement_today.py         # Today's movement vs a 7-day average
├── packages/
│   ├── haiven_care_circle_inputs.yaml   # Contact configuration
│   ├── haiven_monitoring_inputs.yaml    # Thresholds and state machines
│   ├── haiven_comms_inputs.yaml         # Summary and alert text
│   ├── haiven_bathroom_night.yaml       # Night bathroom monitoring
│   ├── haiven_circle_tracking.yaml      # Care circle location sensors
│   ├── haiven_drift.yaml                # Drift Watch: a month of nights vs a frozen baseline
│   ├── haiven_night_insights.yaml       # Nightly bathroom-visit and downstairs-trip stats
│   └── haiven_movement.yaml             # Today's all-room movement vs a 7-day average
├── haiven_persons.yaml           # Person entities
├── haiven_zones.yaml             # Geographic zones
├── www-src/                      # Dashboard card source (deployed to www/ by setup.sh)
│   ├── haiven-cards.js
│   └── haiven-loader.js
└── lovelace/
    └── haiven_default.yaml       # Dashboard
```

## Licence

MIT — see [LICENSE](LICENSE).
