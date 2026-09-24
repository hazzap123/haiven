# Haiven Complete Setup Guide

Full installation and configuration guide for the Haiven elderly care monitoring system.

**Updated:** 2026-09-19

---

## What is Haiven?

Haiven monitors daily activity patterns of an elderly person using motion and presence sensors, detects deviations from normal routines, and alerts caregivers when potential issues arise.

### Key Features

- **Five-level status**, not a traffic light — normal, monitoring, caution, concern, critical, plus a separate "away" state. Full scoring: [STATUS_SPEC.md](../reference/STATUS_SPEC.md)

- **Activity Monitoring**
  - Real-time tracking across rooms
  - Wake-up and bedtime detection
  - Extended inactivity alerts
  - Drift Watch: a month of nights against a baseline that doesn't move
  - Sensor coverage screen: what stops working when a sensor goes offline

- **Care Circle Notifications**
  - Mobile alerts to multiple contacts
  - Actionable notifications (Mark Safe, Check In)
  - AI-generated morning, afternoon and evening summaries

---

## Prerequisites

### Hardware
- Home Assistant server (2024.1+)
- Motion or presence sensor (Kitchen or main living area)
- A presence sensor with zone support for the bedroom, if you want in-bed detection (the reference build uses an Everything Presence Lite running a custom LD2450 ESPHome firmware — see [SENSOR_GUIDES.md](../reference/SENSOR_GUIDES.md))
- Motion sensor for the bathroom (the reference build uses a Shelly BLU Motion)
- Mobile devices for notifications

### Software
- Home Assistant 2024.1+
- [kiosk-mode](https://github.com/NemesisRE/kiosk-mode), installed through HACS. `configuration.yaml` loads it from `/hacsfiles/kiosk-mode/`; the dashboard uses it to hide Home Assistant's header and sidebar. The dashboard's own cards are a self-contained library (`www-src/haiven-cards.js`) that `scripts/setup.sh` deploys for you
- The Anthropic Conversation integration, with its agent at `conversation.claude_conversation`. **Required:** the morning, afternoon and evening summaries, the summary refresh, and the deviation and no-activity alerts all call it, and fail without it. About ten calls a day, roughly $1-5 a month on Claude Haiku 4.5 ($1/$5 per million input/output tokens); most of each call is the entity list Assist sends, so expose only what Haiven needs

**Privacy:** each of those calls sends the monitored person's recent activity (rooms, times, bathroom visits, wake and bedtime) to Anthropic's API.

---

## Installation Checklist

### Pre-Installation (Verify)

- [ ] Home Assistant running (2024.1+)
- [ ] Your three sensors are producing state changes in **Developer Tools > States**

### Step 1: Clone, run setup, copy into /config (10 min)

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

The script prompts for your three entity IDs, rewrites every `.yaml` and `.js` file in the clone that references the defaults (the dashboard card reads the same three entities directly, so it has to go through the same substitution), and copies `www-src/haiven-cards.js` and `www-src/haiven-loader.js` into the clone's `www/`. Copying `www/` into `/config` puts them where Home Assistant serves them from.

### Step 2: Verify Configuration Files (5 min)

Files should already be in `/config/`:

```
packages/haiven_care_circle_inputs.yaml   <- Contact/carer helpers
packages/haiven_monitoring_inputs.yaml    <- Thresholds and state machines
packages/haiven_comms_inputs.yaml         <- Summary and alert text
packages/haiven_drift.yaml                <- Drift Watch
packages/haiven_night_insights.yaml       <- Nightly bathroom-visit stats
packages/haiven_movement.yaml             <- Today's movement vs 7-day average
haiven_sensors_3sensor.yaml               <- Core template sensors
scripts.yaml                              <- Notification scripts
automations.yaml                          <- Monitoring automations
```

These are all wired into `configuration.yaml`'s `homeassistant.packages` block already — nothing to hand-edit here unless you're adding your own.

### Step 3: Configure Care Circle (30 min)

See [CARE_CIRCLE.md](CARE_CIRCLE.md) for detailed instructions.

**Quick summary:**

1. Install HA mobile app on each person's phone
2. Find notification service names (Developer Tools > Actions > search "notify")
3. Find device tracker names (Developer Tools > States > filter "device_tracker.")
4. Edit `packages/haiven_care_circle_inputs.yaml` with actual values:

**Required helpers:**

| Helper | Purpose |
|--------|---------|
| `input_text.elderly_person_name` | Name of the person being monitored |
| `input_text.elderly_person_entity` | Person entity ID |
| `input_text.contact_1_name` | Primary contact name |
| `input_text.contact_1_notification` | Notification service |
| ... | See [ENTITY_REFERENCE.md](../reference/ENTITY_REFERENCE.md) for complete list |

### Step 4: Check Your Baselines (5 min)

`packages/haiven_monitoring_inputs.yaml` already defines every threshold helper below — nothing to create by hand. Adjust the values either in **Settings > Helpers**, or on the dashboard's own Settings tab once it's up:

These helpers have **no defaults**: without `initial:` Home Assistant keeps the value you set across restarts. On a fresh install they start at 00:00 or at the slider's minimum, so set them before relying on alerts.

**Time Baselines:**
- `input_datetime.expected_wake_time` - starts at 00:00; set to her usual wake time
- `input_datetime.expected_bedtime` - starts at 00:00; set to her usual bedtime

**Alert Thresholds:**
- `input_number.wake_time_variance_minutes` - starts at 15; 120 (the maximum) is a sensible start
- `input_number.bedtime_variance_minutes` - starts at 15; 60 is a sensible start
- `input_number.no_activity_alert_hours` - starts at 2; 4 is a sensible start

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

### Step 6: Verify the Dashboard (5 min)

Nothing to build here — `setup.sh` already deployed the card in Step 1, and `configuration.yaml` registers the dashboard itself (`lovelace.dashboards.lovelace-haiven`, pointing at `lovelace/haiven_default.yaml`). It should just appear in your sidebar after the restart in Step 5.

**Verify:**
- [ ] "Haiven" shows in the sidebar
- [ ] Home view shows a status card, today's facts, and your three rooms
- [ ] Bottom nav bar shows Home / Activity / Alerts / Circle / More

If the sidebar item is missing, check `lovelace.dashboards` in `configuration.yaml`. If it's there but the page is blank, the card didn't deploy — see [TROUBLESHOOTING.md](../reference/TROUBLESHOOTING.md).

### Step 7: Test System (15 min)

**Test 1: Sensor Detection**
- [ ] Trigger kitchen sensor > Kitchen activity updates
- [ ] Enter bedroom > Bedroom presence updates
- [ ] Use bathroom > Bathroom motion updates
- [ ] `sensor.last_activity_display` shows correct room

**Test 2: Status Calculation**
- [ ] `sensor.elderly_care_status` shows `normal`
- [ ] `sensor.deviation_count` is 0
- [ ] Dashboard status badge reads "All well"

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
Expected Wake Time: 07:00  # Example: when she typically gets out of bed
Expected Bedtime: 22:00    # Example: when she goes to bed
```

### Threshold Tuning

**Conservative (fewer false alarms):**
```yaml
wake_time_variance_minutes: 120  # 2 hours, the maximum
bedtime_variance_minutes: 120    # 2 hours
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

## Week 1: Tune & Optimise

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
- [ ] Status indicator meaning (five levels, plus away)
- [ ] "Check-in" button
- [ ] "Mark Safe" button
- [ ] How to respond to alerts

**Emergency procedures:**
- [ ] What to do if RED alert
- [ ] Who to call first
- [ ] How to open the Haiven dashboard

---

## Status Determination

### How Status is Calculated

A weighted severity score (`sensor.status_severity_score`), not a single rule — late wake, inactivity gaps, and a failed room transition each add points, and the total maps onto the five levels. Full breakdown, exact point values and thresholds: [STATUS_SPEC.md](../reference/STATUS_SPEC.md).

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
Actions: [View Dashboard, Mark Safe]
```

### Daily Summary
```
Title: "Daily Report - [Name]"
Message: "Wake: 06:45, Last activity: Kitchen, Status: All well"
Level: Passive
```

---

## Key Automations

| Automation | Trigger | Action |
|------------|---------|--------|
| Morning Activity Check | Wake time + variance | Alert if no activity |
| No Activity Alert | Every hour | Alert if threshold exceeded |
| Status Change Notification | Status reaches caution or above | Notify care circle |
| Daily Reset | Midnight | Reset tracking flags |
| Bedtime Detection | Bathroom > Bedroom pattern | Record bedtime |
| Drift Alert | 09:00 and 12:30 | One message when a drift chart trips |

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
- [../reference/STATUS_SPEC.md](../reference/STATUS_SPEC.md) - Full severity scoring

---

*Last Updated: 2026-09-19*
