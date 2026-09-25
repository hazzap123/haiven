# Haiven Quick Start

**Get monitoring working in 30 minutes.**

Everything below is scaffolded for you already — no manual helper creation, no hand-built dashboard. `setup.sh` wires your sensors into the whole system in one pass.

---

## Your 3-Sensor Setup

| Sensor | Location | Default entity |
|--------|----------|--------|
| Motion sensor | Kitchen / main room | `event.kitchen_motion` |
| Presence sensor | Bedroom | `binary_sensor.haiven_bedroom_occupancy` |
| Motion sensor | Bathroom | `binary_sensor.haiven_bathroom_motion` |

You don't need these exact entity IDs — `setup.sh` asks for yours and substitutes them everywhere, including inside the dashboard card.

---

## Before you start

- **kiosk-mode** installed through HACS. The dashboard uses it to hide Home Assistant's header and sidebar.
- **The Anthropic Conversation integration**, with its agent at `conversation.claude_conversation`. This is required: the daily summaries and the deviation and no-activity alerts are written by it. Roughly $1-5 a month on Claude Haiku 4.5.
- **Privacy:** those summaries and alerts send the person's recent activity (rooms, times, bathroom visits) to Anthropic's API.

---

## Step 1: Clone and configure (5 min)

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

`setup.sh` asks for your kitchen, bedroom and bathroom entity IDs, rewrites every `.yaml` and `.js` file in the clone that references the defaults, and deploys the dashboard card into the clone's `www/`, which step 3 copies across.

---

## Step 2: Fill in secrets and people (10 min)

```bash
cp ~/haiven/secrets.yaml.example /config/secrets.yaml   # or merge it into yours
# edit secrets.yaml with your values
```

Then edit:
- `haiven_persons.yaml` — your household members
- `packages/haiven_care_circle_inputs.yaml` — who's being monitored, who the carers are (see [CARE_CIRCLE.md](CARE_CIRCLE.md) for the full contact/notification setup)

---

## Step 3: Restart Home Assistant (2 min)

**Developer Tools > YAML > Restart** (a full restart, not just a YAML reload — the packages and the new frontend module both need it).

---

## Step 4: Verify (5 min)

1. **Developer Tools > States** — search each of your three entities, confirm none show "unknown"
2. **Settings > Dashboards** — a "Haiven" dashboard should now be in your sidebar
3. Open it — Home should show a status card, today's facts, and your three rooms

If the dashboard sidebar item is missing or opens with no cards, see [TROUBLESHOOTING.md](../reference/TROUBLESHOOTING.md).

---

## Step 5: Let it learn (ongoing)

Most of what Haiven does is comparative — today against a rolling average, this month against a frozen baseline. Those numbers need real history before they mean anything:

- **Daily comparisons** (wake time, kitchen activity) — usable within a day or two
- **Drift Watch** (the slow-change layer) — needs 28 nights before it has a baseline to compare against; until then it shows "Learning"

---

## What This Monitors

- **Morning routine** — alert if no activity by expected wake time + variance
- **All-day activity** — alert if nothing's moved for longer than your threshold
- **Overnight bathroom visits** — count, trend, and how it compares to her usual
- **Drift Watch** — a month of nights against a baseline that doesn't move, catching a change too gradual for any single day to flag

Full severity scoring: [STATUS_SPEC.md](../reference/STATUS_SPEC.md)

---

## Tuning Recommendations

In **Settings** on the dashboard. The four status gaps have defaults. The routine helpers have none, so Home Assistant keeps whatever you set across restarts; on a fresh install they start at 00:00 or at the slider's minimum, and the morning check would fire just after midnight. **Set them before relying on alerts.**

| Helper | Default | Suggested start |
|--------|---------|-----------------|
| `status_gap_monitoring_mins` | 60 | |
| `status_gap_caution_mins` | 120 | |
| `status_gap_concern_mins` | 180 | |
| `status_gap_critical_mins` | 240 | |
| `expected_wake_time` | none (00:00) | her usual wake time |
| `expected_bedtime` | none (00:00) | her usual bedtime |
| `wake_time_variance_minutes` | none (15, the minimum) | 120 |
| `bedtime_variance_minutes` | none (15, the minimum) | 60 |
| `no_activity_alert_hours` | none (2, the minimum) | 4 |
| `transition_timeout_mins` | none (30, the minimum) | 90 with a motion-only main-room sensor |

**Too many alerts:** raise the relevant threshold. **Missing real issues:** lower it. Give it a week on the defaults before tuning — you need false alarms to actually see, not guess at.

---

## Next Steps

1. **Run for a week** on the defaults
2. **Tune thresholds** based on real false alarms, not guesses
3. **Set up notifications** — [CARE_CIRCLE.md](CARE_CIRCLE.md)
4. **Full install guide** (what each package does, entity-by-entity) — [COMPLETE_SETUP.md](COMPLETE_SETUP.md)

---

## Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| Sensors show "unknown" | Check entity IDs in Developer Tools > States |
| Dashboard has no sidebar item | Check `configuration.yaml`'s `lovelace.dashboards` block, restart |
| Dashboard sidebar item opens blank | The card wasn't deployed — see TROUBLESHOOTING.md |
| Too many alerts | Increase the relevant threshold |
| Missing real issues | Decrease the relevant threshold |

Full troubleshooting: [../reference/TROUBLESHOOTING.md](../reference/TROUBLESHOOTING.md)

---

## Quick Reference

**Entity IDs:** See [../reference/ENTITY_REFERENCE.md](../reference/ENTITY_REFERENCE.md)

**Key sensors:**
- Status: `sensor.elderly_care_status`
- Deviations: `sensor.deviation_count`
- Sensor health: `sensor.sensor_health_status`

**Config files:**
- Core sensors: `haiven_sensors_3sensor.yaml`
- Contacts: `packages/haiven_care_circle_inputs.yaml`
- Thresholds: `packages/haiven_monitoring_inputs.yaml`
- Scripts: `scripts.yaml`
- Automations: `automations.yaml`

---

**That's it. Basic monitoring is now active.**

---

*Quick Start — Updated 2026-09-19*
