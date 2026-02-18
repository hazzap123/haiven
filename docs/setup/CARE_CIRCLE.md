# Care Circle Setup Guide

Complete guide for configuring caregivers, the elderly person, and location tracking.

**Updated:** 2026-02-04
**Architecture:** Numbered Contact System (contact_1, contact_2, etc.)

---

## Overview

The care circle is your network of people who monitor and receive alerts about the elderly person. Haiven uses a centralized configuration file for all contact settings.

**Key concepts:**
- **Elderly Person:** The person being monitored
- **Contacts:** Caregivers numbered as contact_1, contact_2, etc.
- **Contact Types:** "primary" (full data) or "secondary" (limited data)
- **Central Config:** All settings in `haiven_inputs.yaml`

**Time required:** ~10 minutes per person

---

## Architecture

```
HAIVEN CARE CIRCLE
------------------

ELDERLY PERSON (being cared for)
  input_text.elderly_person_name        -> "Your Person"
  input_text.elderly_person_entity      -> person.elderly_person
  input_text.elderly_person_device_tracker -> device_tracker.your_person_phone

CONTACT 1 (Carer 1 - primary)
  input_text.contact_1_name             -> "Carer 1"
  input_text.contact_1_type             -> "primary"
  input_text.contact_1_person           -> person.contact_1
  input_text.contact_1_device_tracker   -> device_tracker.carer_1_phone
  input_text.contact_1_phone            -> "+44 0000..."
  input_text.contact_1_notification     -> notify.mobile_app_your_phone

CONTACT 2 (Carer 2 - primary)
  input_text.contact_2_name             -> "Carer 2"
  input_text.contact_2_type             -> "primary"
  input_text.contact_2_person           -> person.contact_2
  input_text.contact_2_device_tracker   -> device_tracker.carer_2_phone
  input_text.contact_2_phone            -> "+44 0000..."
  input_text.contact_2_notification     -> notify.mobile_app_your_phone
```

All scripts, automations, and sensors automatically read from these values.

---

## Step 1: Install Home Assistant Mobile App

For each person who will receive notifications or be tracked:

### iPhone/iPad
1. Open **App Store**
2. Search for **"Home Assistant"**
3. Install the official app (by Home Assistant)
4. Open the app

### Android
1. Open **Google Play Store**
2. Search for **"Home Assistant"**
3. Install the official app
4. Open the app

---

## Step 2: Connect App to Home Assistant

On each person's phone:

1. **Connect to your server**
   - App will auto-discover (if on same network)
   - Or enter URL: `http://homeassistant.local:8123`
   - Or use Nabu Casa URL for remote access

2. **Log in**
   - **Recommended:** Create a separate user account for each person
     - Settings > People > Add Person
     - Create username and password
   - **Or:** Use a shared account (simpler but less secure)

3. **Allow notifications** when prompted
   - Tap "Allow" for notification permission

4. **Allow location** (optional but useful)
   - iOS: Allow "Always" for best tracking
   - Android: Allow "all the time"

---

## Step 3: Find Entity Names

### A. Find Notification Service

1. Go to **Developer Tools > Actions** (formerly Services)
2. Search for `notify`
3. Look for entries like:
   ```
   notify.mobile_app_your_phone        <- Carer 1's phone
   notify.mobile_app_iphone_se_2      <- Another iPhone
   notify.mobile_app_sm_g991b         <- Android device
   ```
4. **Copy the exact service name**

**Quick test:**
1. Click the notification service
2. Enter message: `Test from Haiven`
3. Click "Call Service"
4. Phone should receive notification

### B. Find Device Tracker

1. Go to **Developer Tools > States**
2. Filter for: `device_tracker.`
3. Look for entries like:
   ```
   device_tracker.carer_1_phone           <- Carer 1's phone
   device_tracker.carer_2_phone         <- Carer 2's phone
   ```
4. **Copy the exact entity ID**

### C. Find Person Entity

1. Go to **Developer Tools > States**
2. Filter for: `person.`
3. Find the person entity (e.g., `person.contact_1`)
4. **Important:** This may not match the name exactly!

---

## Step 4: Edit Central Configuration

**Edit ONE file:** `haiven_inputs.yaml`

Find the `initial:` values and update them:

```yaml
input_text:
  # ELDERLY PERSON
  elderly_person_name:
    initial: "Your Person"                    # <- UPDATE

  elderly_person_entity:
    initial: "person.elderly_person"             # <- CHECK ACTUAL ENTITY ID

  elderly_person_device_tracker:
    initial: "device_tracker.your_person_phone"  # <- UPDATE

  # CONTACT 1
  contact_1_name:
    initial: "Carer 1"             # <- UPDATE

  contact_1_type:
    initial: "primary"                 # primary or secondary

  contact_1_person:
    initial: "person.contact_1"            # <- CHECK ACTUAL ENTITY ID

  contact_1_device_tracker:
    initial: "device_tracker.carer_1_phone"     # <- UPDATE

  contact_1_phone:
    initial: "+44 0000 000 000"         # <- UPDATE

  contact_1_notification:
    initial: "notify.mobile_app_your_phone"  # <- UPDATE

  # CONTACT 2 (optional)
  contact_2_name:
    initial: "Carer 2"                    # <- UPDATE or leave blank
  # ... etc
```

**Important:** `initial:` only applies when the entity is first created. If it already exists, manually set via Developer Tools > Actions.

---

## Step 5: Update Person Entities (if using YAML)

**Edit:** `haiven_persons.yaml`

Ensure device trackers match:

```yaml
- name: "Your Person"
  id: your_person
  device_trackers:
    - device_tracker.your_person_phone

- name: "Carer 1"
  id: carer_1
  device_trackers:
    - device_tracker.carer_1_phone

- name: "Carer 2"
  id: carer_2
  device_trackers:
    - device_tracker.carer_2_phone
```

**Critical:** Check Developer Tools > States for actual entity IDs. HA may not use the `id:` field if the entity already exists!

---

## Step 6: Restart and Verify

1. **Check YAML syntax**
   - Developer Tools > YAML > Check Configuration

2. **Restart Home Assistant**
   - Settings > System > Restart

3. **Verify values**
   - Developer Tools > States > Filter: `input_text.contact_`
   - If wrong, manually set via Developer Tools > Actions

4. **Test notifications**
   - Developer Tools > Actions > `script.notify_care_circle`
   - All phones should receive alert

---

## Location Tracking Setup

Enable location tracking to see where each contact is and their proximity to the elderly person's home.

### Enable Location on Each Phone

**iOS:**
- Settings > Home Assistant > Location > **Always**

**Android:**
- Settings > Apps > Home Assistant > Permissions > Location > **Allow all the time**

### Configure Mobile App Sensors

In the HA Mobile App on each phone:
1. Settings (gear icon)
2. Companion App
3. Manage Sensors
4. Enable:
   - Location
   - Zone
   - Background Location

### Configure Zones (Optional)

Edit `/config/haiven_zones.yaml`:

```yaml
zone:
  - name: "Home"
    latitude: 51.5074      # <- UPDATE with actual coordinates
    longitude: -0.1278
    radius: 100
    icon: mdi:home-heart

  - name: "Carer 1 Home"
    latitude: 51.5145
    longitude: -0.1421
    radius: 100
    icon: mdi:home-account
```

**Get coordinates:** Right-click on Google Maps > Copy coordinates

### Verify Location Tracking

1. Developer Tools > States > Filter: `person.`
2. Each person should show:
   - State: "home", "away", or zone name
   - Attributes: latitude, longitude

---

## Adding More Contacts

### Adding Contact 3

1. **Create person entity in HA UI**
   - Settings > People > Add Person
   - Note the actual entity_id created

2. **Add input_text helpers to `haiven_inputs.yaml`**
   ```yaml
   contact_3_name:
     name: Contact 3 Name
     max: 100
     icon: mdi:account
     initial: "Jane (Niece)"

   contact_3_type:
     initial: "secondary"

   contact_3_person:
     initial: "person.jane"  # <- ACTUAL entity_id

   contact_3_device_tracker:
     initial: "device_tracker.janes_iphone"

   contact_3_phone:
     initial: "+44 0000..."

   contact_3_notification:
     initial: "notify.mobile_app_janes_phone"
   ```

3. **Add sensors to `packages/haiven_circle_tracking.yaml`**
   - Copy Contact 2 sensor block
   - Replace `contact_2` with `contact_3`

4. **Update notification scripts if needed**

5. **Restart HA and verify**

---

## Modifying Existing Contacts

### Update Phone Number
1. Edit `haiven_inputs.yaml` > `contact_N_phone`
2. Restart HA
3. If value doesn't update, manually set via Developer Tools > Actions

### Change Device (New Phone)
1. Install HA mobile app on new phone
2. Find new device_tracker and notification service names
3. Edit `haiven_inputs.yaml`:
   - Update `contact_N_device_tracker`
   - Update `contact_N_notification`
4. Edit `haiven_persons.yaml`:
   - Update device_tracker to match
5. Restart HA
6. Verify values; manually set if needed

---

## Mobile App Features to Show Users

### For the Elderly Person
- How to open Haiven dashboard
- "Check-in" button (confirms they're OK)
- "Mark Safe" button (clears alerts)
- Status indicator meaning (green/orange/red)

### For Primary/Secondary Contacts
- How to view current status
- How to see last activity
- How to mark person as safe remotely
- How to add care notes
- How to respond to alerts

---

## Configuration Files Summary

| File | Purpose | What to Edit |
|------|---------|--------------|
| `haiven_inputs.yaml` | **Central config** | **All contact details** |
| `haiven_persons.yaml` | Person entities | Device tracker links |
| `scripts.yaml` | Notifications | Auto-reads from haiven_inputs.yaml |
| `automations.yaml` | Automations | Auto-reads from haiven_inputs.yaml |
| `packages/haiven_circle_tracking.yaml` | Location sensors | Add new contact sensors |

---

## Troubleshooting

### Can't find notification service
- Ensure phone is connected to HA (Settings > People)
- Log out and back in on mobile app
- Wait 5 minutes after first login
- Restart Home Assistant

### Notifications not arriving
- Check phone notification settings are enabled
- Check Do Not Disturb is off
- Test with simple message in Developer Tools
- Check battery optimization (Android)

### Location showing "Unknown"
- Verify person entity exists
- Check `input_text.contact_N_person` has correct entity ID
- Device tracker must be linked to person
- Location permissions enabled on phone
- Restart HA after YAML changes

### Values don't update after editing YAML
- `initial:` only applies on first creation
- Manually set via Developer Tools > Actions > `input_text.set_value`

---

## Quick Commands Reference

**Check YAML syntax:**
```
Developer Tools > YAML > Check Configuration
```

**Restart Home Assistant:**
```
Settings > System > Restart
```

**Test notification:**
```
Developer Tools > Actions > notify.mobile_app_xxxxx
Message: "Test"
Perform Action
```

**Manually set input_text value:**
```
Developer Tools > Actions > input_text.set_value
entity_id: input_text.contact_1_person
value: person.contact_1
```

---

*Last Updated: 2026-02-04*
