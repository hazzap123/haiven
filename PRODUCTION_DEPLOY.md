# Production Deployment: Mum's House (HA Green)

Branch: `production/mums-house`
Target: Home Assistant Green at Harry's mum's house
Current production repo: `github.com/hazzap123/haivenapp`
Date prepared: 2026-02-23

**This is a safety-critical system. Do not skip steps.**

---

## Pre-Deploy: SSH Verification Checklist

SSH into HA Green before proceeding. Complete all items before any file changes.

```bash
ssh root@<HA_GREEN_IP>
# or via HA CLI if direct SSH not configured
```

### 1. Note current state

```bash
# Save current commit — your rollback point
cd /config && git log -1 --oneline

# Check HA version
ha core info | grep version
```

### 2. Verify activity log path

```bash
grep "LOG_FILE\|mum_activity\|activity.log" /config/scripts/activity_log_json.sh
grep "activity" /config/configuration.yaml | grep -i log
```

**Decision:** If haivenapp uses `/config/mum_activity.log`:
- Option A: Copy to `activity.log` during migration (haiven expects `activity.log`)
- Option B: Update `scripts/activity_log_json.sh` in this branch to use `mum_activity.log`

Option B is safer (preserves log path without renaming 2.5MB history file).
**Current haiven script uses `/config/activity.log`. Update it if haivenapp uses a different path.**

### 3. Verify sensor entity IDs

```bash
# Check what sensors are registered
ha states list | grep -E "binary_sensor|event" | grep -E "motion|occupancy|presence"
```

Known production sensors (from plan):
- **Bedroom (LD2450 radar):** `binary_sensor.everything_presence_lite_bad434_occupancy`
- **Bathroom (Shelly BLU):** `binary_sensor.shelly_blu_motion_a029_motion`
- **Kitchen:** UNKNOWN — find it from states list above

Verify these are active and reporting:
```bash
ha states get binary_sensor.everything_presence_lite_bad434_occupancy
ha states get binary_sensor.shelly_blu_motion_a029_motion
```

### 4. Check if entity aliases already exist in haivenapp

```bash
grep "haiven_bathroom_motion\|haiven_bedroom_occupancy\|haiven_kitchen" /config/haiven_sensors_3sensor.yaml | head -20
```

If haivenapp already defines template aliases (`binary_sensor.haiven_bathroom_motion` etc. wrapping the raw IDs), then the haiven package files will work without running `setup.sh`. If NOT, `setup.sh` must be run to replace aliases with raw sensor IDs.

### 5. Export input helper values (CRITICAL — these reset on fresh load)

In HA frontend: Settings → Devices & Services → Helpers
Or via Developer Tools → Template:

```jinja
Wake time: {{ states('input_datetime.elderly_wake_time') }}
Bedtime: {{ states('input_datetime.elderly_bedtime') }}
Wake variance: {{ states('input_number.wake_time_variance') }} min
No-activity threshold: {{ states('input_number.no_activity_alert_threshold') }} hrs
Kitchen baseline: {{ states('input_number.kitchen_triggers_baseline') }}
Night bathroom baseline: {{ states('input_number.night_bathroom_visits_baseline') }}
Status gap — Monitoring: {{ states('input_number.status_gap_monitoring') }} min
Status gap — Caution: {{ states('input_number.status_gap_caution') }} min
Status gap — Concern: {{ states('input_number.status_gap_concern') }} min
Status gap — Critical: {{ states('input_number.status_gap_critical') }} min
```

**Record all values. You will re-enter them after deploy.**

### 6. Verify notification services

```bash
ha services list | grep notify
```

Confirm `notify.mobile_app_iphone_hp` exists. Find Abby's notification service.

### 7. Collect Abby's details

From existing `/config/` files or HA UI:
```bash
grep -r "abby\|contact_2" /config/ --include="*.yaml" | grep -v ".git"
```

---

## Phase 1: Sensor Setup (local, before deploy)

Once you have the kitchen sensor entity ID from step 3 above, run:

```bash
cd /path/to/haiven  # local clone of haiven repo
git checkout production/mums-house
bash scripts/setup.sh
```

When prompted:
- Activity sensor (kitchen): `<entity_id_from_step_3>`
- Bed sensor (bedroom): `binary_sensor.everything_presence_lite_bad434_occupancy`
- Bath sensor (bathroom): `binary_sensor.shelly_blu_motion_a029_motion`

`setup.sh` writes these values into `haiven_sensor_roles.yaml` only — no other files are touched.

### 1b: Copy files from haivenapp (requires local clone of haivenapp)

```bash
# Clone haivenapp locally if not already done
git clone git@github.com:hazzap123/haivenapp.git /tmp/haivenapp

# Copy evolved Lovelace dashboard (preserve months of UI polish)
cp /tmp/haivenapp/lovelace/haiven_default.yaml lovelace/haiven_default.yaml

# Copy ESPHome device config (device-specific, do NOT modify)
cp -r /tmp/haivenapp/esphome/ esphome/

# Copy themes if present
[ -d /tmp/haivenapp/themes ] && cp -r /tmp/haivenapp/themes/ themes/
```

### 1c: Update activity log path (if needed)

If step 2 confirmed haivenapp uses `mum_activity.log`:

```bash
# Update the script in this branch
sed -i 's|/config/activity.log|/config/mum_activity.log|g' scripts/activity_log_json.sh
sed -i 's|/config/activity.log|/config/mum_activity.log|g' scripts/rotate_activity_log.sh
```

Also update `configuration.yaml` if shell_command references the log file directly.

### 1d: Fill in Abby's contact details

Edit `packages/haiven_care_circle_inputs.yaml`:
- `contact_2_phone` → Abby's real number
- `contact_2_notification` → Abby's notify service (from step 6)

### 1e: Commit and push

```bash
git add haiven_persons.yaml packages/haiven_care_circle_inputs.yaml \
        scripts/activity_log_json.sh scripts/rotate_activity_log.sh \
        lovelace/ esphome/ themes/
git commit -m "production/mums-house: configure Toni/Harry/Abby, sensors, log path"
git push -u origin production/mums-house
```

---

## Phase 2: Deploy to HA Green (SSH)

### Step 1: Take HA backup — DO NOT SKIP

Settings → System → Backups → Create Backup
Wait for completion before proceeding.

### Step 2: Preserve activity log

```bash
cp /config/mum_activity.log /tmp/mum_activity.log.bak
# or if using activity.log:
cp /config/activity.log /tmp/activity.log.bak
```

### Step 3: Clone and checkout production branch

```bash
cd /tmp
git clone https://github.com/hazzap123/haiven.git haiven-new
cd haiven-new
git checkout production/mums-house
```

### Step 4: Preserve .storage/ and existing secrets, then swap config

```bash
# Back up runtime state (input helpers, history)
cp -r /config/.storage /tmp/.storage.bak

# Copy new config files (preserve .storage/, .git/, secrets.yaml)
rsync -av --exclude='.storage' --exclude='.git' --exclude='secrets.yaml' \
  /tmp/haiven-new/ /config/

# Restore secrets if not already present
# (haiven uses secrets.yaml.example — copy your existing secrets.yaml)
```

### Step 5: Verify ESPHome is intact

```bash
ls /config/esphome/
# Should show: everything-presence-lite-bad434.yaml (and any others)
```

### Step 6: Reload HA

```bash
ha core reload-core-config
# Then reload automations, scripts, and templates:
# HA Frontend → Developer Tools → YAML → Reload All
```

Or restart fully:
```bash
ha core restart
```

### Step 7: Verify sensors in Developer Tools → States

```bash
# Check these are NOT 'unknown':
sensor.elderly_care_status
sensor.activity_data
sensor.overnight_bathroom_count
binary_sensor.haiven_activity_sensor
binary_sensor.haiven_bed_sensor
binary_sensor.haiven_bath_sensor
```

### Step 8: Re-enter tuned input helper values

Settings → Devices & Services → Helpers
Re-enter values recorded in Pre-Deploy step 5.

**Note:** `.storage/` is preserved from step 4, so input helpers should retain their values automatically. Re-entry is only needed if `.storage/` was not preserved.

### Step 9: Test notifications

HA Frontend → Developer Tools → Services:
```yaml
service: notify.mobile_app_iphone_hp
data:
  title: "Haiven Test"
  message: "Migration complete — notification service working"
```

---

## Phase 3: Validation Checklist

Do not declare done until all items are green.

- [ ] `sensor.elderly_care_status` shows `normal` (not `unknown`)
- [ ] `sensor.activity_data` updates when kitchen sensor triggers (`binary_sensor.haiven_activity_sensor` shows `on` briefly)
- [ ] `sensor.overnight_bathroom_count` shows a number (not `unknown`)
- [ ] Dashboard loads with hero card showing Toni's status
- [ ] Send test notification to Harry's phone — received OK
- [ ] Abby's notification service confirmed working
- [ ] Morning summary fires at 06:00 next day (or check automation trace)
- [ ] Activity log accumulating entries (`tail -20 /config/activity.log`)
- [ ] No errors in HA logs: Settings → System → Logs

---

## Rollback

If anything breaks:

```bash
# Option A: Git rollback
cd /config
git checkout <previous-commit-from-step-1>
ha core reload-core-config

# Option B: Restore from HA backup
# Settings → System → Backups → restore
```

Activity log backup: `/tmp/mum_activity.log.bak` (copy back if log was moved/renamed)

---

## What This Migration Does NOT Cover

- React frontend (`haivenv2/`) — separate deployment
- Nabu Casa / remote access — unaffected
- HACS components — already installed, no change
- Mobile app on Harry/Abby's phones — no change
- ESPHome device reflash — not required (config copy only)
