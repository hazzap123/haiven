# Sensor Hardware Guides

Complete setup and maintenance guides for all Haiven monitoring sensors.

**Updated:** 2026-02-04

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

### Why Configure It?

Proper configuration ensures:
- Accurate wake-up time detection
- Sleep state monitoring (detects breathing)
- Nighttime bathroom trip logging
- Minimal false positives/negatives

### Key Entities

| Entity | Description |
|--------|-------------|
| `binary_sensor.haiven_bedroom_occupancy` | Main presence (on/off) |
| `binary_sensor.haiven_bedroom_moving_target` | Movement detected |
| `binary_sensor.haiven_bedroom_still_target` | Stationary presence |
| `sensor.haiven_bedroom_detection_distance` | Distance to target (cm) |

### Configuration via Add-on

1. **Add repository:**
   - Settings > Add-ons > Add-on Store > ... (menu) > Repositories
   - Add: `https://github.com/EverythingSmartHome/everything-presence-addons`

2. **Install configurator:**
   - Find "Everything Presence Configurator" in Add-on Store
   - Install, Start, Enable "Show in sidebar"

3. **Configure settings:**
   - Open configurator from sidebar
   - Select your device

### Recommended Bedroom Settings

| Setting | Value | Why |
|---------|-------|-----|
| Detection Distance | 3-4 meters | Covers bed area, prevents hallway detection |
| Still Sensitivity | 85% | Detects breathing while sleeping |
| Movement Sensitivity | 65% | Detects getting up without false triggers |
| Presence Timeout | 45 seconds | Balance between responsive and stable |
| Zones 1-3 | Enabled | Bed and immediate area |
| Zones 4-8 | Disabled | Prevents door/hallway detection |
| LED Brightness | 0-10% | Avoid disturbing sleep |

### Room Size Presets

**Small bedroom (< 10 sq m):**
```
Distance: 3m, Still: 85%, Move: 70%, Timeout: 30s, Zones: 1-2
```

**Medium bedroom (10-15 sq m):**
```
Distance: 4m, Still: 85%, Move: 65%, Timeout: 45s, Zones: 1-3
```

**Large bedroom (> 15 sq m):**
```
Distance: 5m, Still: 90%, Move: 60%, Timeout: 60s, Zones: 1-4
```

### Testing Your Configuration

**Test 1: Sleep Detection**
1. Lie still in bed for 2 minutes
2. Check sensor stays "on" (occupied)
3. If fails: Increase still sensitivity

**Test 2: Wake-up Detection**
1. Get out of bed
2. Check sensor detects immediately
3. `last_changed` should update within 1-2 seconds

**Test 3: Room Exit**
1. Leave bedroom
2. Wait for timeout (45 seconds)
3. Sensor should change to "off"

**Test 4: Nighttime Movement**
1. Get up at night
2. Check activity is logged in Haiven

### Troubleshooting

**Always shows "Occupied":**
- Detection distance too far (reduce to 3m)
- Zones 4-8 enabled (disable them)
- Air vent causing movement (reposition sensor)

**Never shows "Occupied":**
- Sensitivity too low (increase to 90%)
- Sensor not aimed at bed (reposition)
- Firmware issue (update via configurator)

**False wake-ups during sleep:**
- Movement sensitivity too high (reduce to 50-60%)
- Fan/AC detected (disable far zones)

### Known Warning (Ignore This)

```
[W][ld2410:598]: Max command length exceeded; ignoring
```

This is **normal** with LD2410 firmware 2.04.x. The warning is intentionally suppressed. The sensor works fine.

### Hard Reset Procedure

If sensor becomes unresponsive:

1. **Factory reset:**
   - Hold reset button (small hole on bottom) for 10-15 seconds
   - LED flashes red, then cycles through colors
   - Wait 30 seconds for boot

2. **Connect to setup WiFi:**
   - Find network "everything-presence-lite" on phone/laptop
   - Connect (no password)

3. **Configure:**
   - Open browser: `http://192.168.4.1`
   - Select your WiFi network
   - Enter password
   - Device restarts and connects

4. **Re-add to Home Assistant:**
   - Settings > Integrations > should auto-discover
   - Or manually add via ESPHome integration

Reference: https://docs.everythingsmart.io/s/products/doc/restore-or-update-your-epl-to-factory-settings-using-a-computer-orj7PBBOJZ

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

## Data Extraction (Advanced)

For detailed MMW sensor analysis, you can enable comprehensive logging.

### Enable Enhanced Entities

Add to ESPHome config to expose all MMW data:
- Gate energy levels (zones 0-8)
- Distance measurements
- Movement vs stillness energy
- WiFi signal strength

### CSV Logging

Create automation to log sensor changes to file:
```yaml
shell_command:
  log_mmw_data: 'echo "{{ timestamp }},{{ entity }},{{ state }}" >> /config/mmw_data.csv'
```

### Analysis

```bash
# Count events by hour
cat mmw_data.csv | cut -d, -f1 | cut -d' ' -f2 | cut -d: -f1 | sort | uniq -c

# Average energy levels
cat mmw_data.csv | grep "moving_energy" | awk -F, '{sum+=$3; count++} END {print sum/count}'
```

See full documentation: `docs/internal/ESP_MMW_DATA_EXTRACTION.md`

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

*Last Updated: 2026-02-04*
