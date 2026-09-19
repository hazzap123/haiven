# Sensor Hardware Guides

Complete setup and maintenance guides for all Haiven monitoring sensors.

**Updated:** 2026-09-19

---

## Sensor Overview

Haiven uses 3 sensors for triangulated monitoring. The sensor types below are what was used in the original build — any compatible Home Assistant sensor will work.

| Sensor type | Entity (default) | Location |
|-------------|-----------------|----------|
| Motion or presence sensor | `event.kitchen_motion` | Kitchen / main living area |
| MMW radar presence sensor | `binary_sensor.haiven_bedroom_occupancy` | Bedroom |
| PIR motion sensor | `binary_sensor.haiven_bathroom_motion` | Bathroom |

### Coverage Pattern

```
House Layout:
+---------------------------------+
|  Kitchen / Living Room          |
|  Motion Sensor                  |  <- Morning activity, meals
+---------------------------------+
|  Bedroom                        |
|  Presence Sensor (Radar/PIR)    |  <- Sleep, wake-up, rest
+---------------------------------+
|  Bathroom                       |
|  PIR Motion Sensor              |  <- Routine, bathroom breaks
+---------------------------------+
```

---

## Everything Presence Lite (Bedroom)

The millimeter wave radar sensor detects presence through breathing and micro-movements.

**Sensor model matters here.** This is an **LD2450** radar, not LD2410 — they're different chips with different ESPHome components, and mixing them up has broken this exact setup before. The reference build runs a custom ESPHome firmware (esp-idf framework, raw UART parsing of the LD2450 protocol, not the stock `ld2410` component) rather than Everything Smart Home's default firmware — that custom build is what gives bed-vs-room zone detection.

**This repo does not currently include that ESPHome device config.** The instructions below cover what the packages and dashboard expect from the sensor; they don't cover flashing it, because the firmware source isn't published here yet. If you're setting this up, either build your own LD2450-based ESPHome config with zone/occupancy entities matching the names below, or wait for that piece to be published.

### Why Configure It?

Proper configuration ensures:
- Accurate wake-up time detection
- Sleep state monitoring
- Nighttime bathroom trip logging
- Minimal false positives/negatives

### Key Entities

| Entity | Description |
|--------|-------------|
| `binary_sensor.haiven_bedroom_occupancy` | Main presence (on/off) — this is the one the packages and dashboard actually read |
| `binary_sensor.haiven_bedroom_moving_target` | Movement detected |
| `binary_sensor.haiven_bedroom_still_target` | Stationary presence |
| `sensor.haiven_bedroom_detection_distance` | Distance to target (cm) |

### Zone Configuration

Bed-vs-room detection comes from zone coordinates (a bed zone, a bathroom-door/side zone), configured as number entities and typically set up through the [Everything Presence add-ons](https://github.com/EverythingSmartHome/everything-presence-addons) zone configurator, which discovers the device and writes zone coordinates directly. That's a separate tool from a stock LD2410 sensitivity/timeout configurator — don't confuse the two.

### Troubleshooting

**Always shows "Occupied":**
- Zone boundaries too generous — tighten them in the zone configurator
- Air vent or fan causing movement in a monitored zone

**Never shows "Occupied":**
- Sensor not aimed at the bed
- Zone doesn't actually cover where the person sleeps

**False wake-ups during sleep:**
- A zone extends into a doorway or hallway — narrow it

### Firmware

Do not factory-reset this device expecting to just reconnect it to WiFi afterwards. A factory reset returns it to Everything Smart Home's stock firmware, not the custom LD2450 build Haiven needs — recovering from that means reflashing the custom ESPHome config, which (per the gap above) isn't published in this repo yet. If the device is genuinely unresponsive, treat it as a hardware-recovery problem, not a quick reset-and-reconnect.

---

## Shelly BLU Motion (Bathroom)

Battery-powered PIR motion sensor for bathroom activity tracking.

### Key Entities

| Entity | Description |
|--------|-------------|
| `binary_sensor.haiven_bathroom_motion` | Motion detected (on/off) |
| `sensor.haiven_bathroom_battery` | Battery percentage |

### Battery Management

- **Typical life:** 1-2 years (depends on motion frequency)
- **Check monthly:** via Home Assistant entity
- **Plan replacement:** when below 20%
- **Device works** until battery fully depletes

### Hard Reset Procedure

1. **Factory reset:**
   - Locate reset button (recessed hole on back)
   - Press and hold with paperclip for 10 seconds
   - LED flashes rapidly (red/amber)
   - Release and wait 30 seconds

2. **Connect via Shelly App (recommended):**
   - Enable Bluetooth on phone
   - Open Shelly App
   - App detects "Shelly Blu PIR"
   - Follow setup prompts
   - Select WiFi network
   - Device shows "Online"

3. **Re-add to Home Assistant:**
   - Wait 1-2 minutes for device to stabilize
   - Settings > Integrations > should see Shelly discovery
   - Click Configure
   - If not discovered: add manually with device IP

### Bluetooth vs WiFi

- **BLE:** Used for setup and configuration (via Shelly App)
- **WiFi:** Used for continuous monitoring (Home Assistant)
- After setup, Bluetooth is not required

### Troubleshooting

**Device not appearing after reset:**
- Confirm "Online" in Shelly App
- Verify same WiFi network
- Try accessing `http://[device-ip]` in browser
- If Shelly App shows offline, repeat reset

**Motion not detecting:**
- Check battery level
- Verify entity shows on/off (not unavailable)
- Test by walking past sensor
- Check sensor angle covers toilet/sink area

---

## Kitchen Sensor

Any motion or presence sensor that exposes an entity to Home Assistant will work. The original build used a Ring camera — but a Zigbee PIR, MMW radar, or any other HA-compatible sensor is fine.

### Key Entity

| Entity | Description |
|--------|-------------|
| `event.kitchen_motion` | Motion detection event (entity ID is configurable via setup.sh) |

### Sensor Behavior

- **Event-based sensors** (e.g. Ring, some Zigbee PIRs): trigger on motion, no persistent on/off state
- **Binary sensors** (e.g. MMW radar, occupancy sensors): have on/off state; both types are supported

### Notes

Kitchen is **not used for bedtime detection** — evening activity in shared spaces is too ambiguous. Bedroom sensor handles sleep/wake.

### Troubleshooting

**Not updating:**
- Verify the entity ID matches what you configured in setup.sh
- Check sensor is reachable in Settings > Devices

**Missing activity:**
- Check sensor placement covers the areas the person uses
- Bedroom/bathroom sensors provide backup coverage

---

## Adding New Sensors

### Finding Available Sensors

1. **Developer Tools > Template** - Paste this:
   ```jinja
   MOTION & OCCUPANCY SENSORS:
   {%- for state in states.binary_sensor %}
     {%- if 'motion' in state.entity_id or 'occupancy' in state.entity_id %}
       - {{ state.entity_id }} ({{ state.name }})
     {%- endif %}
   {%- endfor %}
   ```

2. **Developer Tools > States** - Filter by:
   - `binary_sensor.` - Motion, door, window
   - `event.` - Event-based sensors
   - `sensor.` - Power sensors

### Integrating a New Sensor

1. **Note entity_id** from Developer Tools

2. **Update haiven_sensors_3sensor.yaml** - Add to last activity logic

3. **Update automations.yaml** - Add triggers if needed

4. **Reload YAML:**
   - Developer Tools > YAML > All YAML configuration

5. **Test:**
   - Trigger sensor
   - Check `sensor.last_activity_display` updates

### Priority Sensors to Add

**High priority:**
- Motion sensors in key rooms
- Door sensors (bedroom/bathroom)
- Presence/occupancy sensors

**Medium priority:**
- Light switches (manual = presence)
- TV power monitoring

**Optional:**
- Kettle/coffee maker (morning routine)
- Bed occupancy sensor

---

## Maintenance Schedule

### Weekly
- [ ] Check sensor states are updating
- [ ] Review false positives in logs
- [ ] Verify wake-up times accurate

### Monthly
- [ ] Check bathroom sensor battery
- [ ] Check for MMW firmware updates
- [ ] Clean sensors (dust affects detection)

### Quarterly
- [ ] Review zone configuration (seasonal changes)
- [ ] Test all detection scenarios
- [ ] Optimize based on patterns

---

*Last Updated: 2026-09-19*
