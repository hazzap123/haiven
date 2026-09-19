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

## Step 1: Clone and configure (5 min)

```bash
git clone https://github.com/hazzap123/haiven.git /config
cd /config
bash scripts/setup.sh
```

The script asks for your kitchen, bedroom and bathroom entity IDs, rewrites every `.yaml` and `.js` file that references the defaults, and deploys the dashboard card into `www/`.

---

## Step 2: Fill in secrets and people (10 min)

```bash
cp secrets.yaml.example secrets.yaml
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

Defaults, in **Settings** on the dashboard's Thresholds tab:

| Helper | Default |
|--------|---------|
| `status_gap_monitoring_mins` | 60 |
| `status_gap_caution_mins` | 120 |
| `status_gap_concern_mins` | 180 |
| `status_gap_critical_mins` | 240 |
| `no_activity_alert_hours` | 4 |
| `wake_time_variance_minutes` | 120 |

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
