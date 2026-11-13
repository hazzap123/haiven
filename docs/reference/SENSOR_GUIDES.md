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

### Choosing where each sensor goes

Decide this from the layout and the routine, not from the kit. Each role does a different job in Haiven, so the wrong sensor in a room breaks a specific alert.

| Role | What Haiven uses it for | What it must see | Best sensor |
|---|---|---|---|
| Bedroom | Bedtime, in bed, night trips out of bed | The person going to bed and getting up | Presence (mmWave) sees them lying still; a PIR works, with in bed taken from the bedtime routine |
| Main room | The morning check, wake time, daytime silence alerts | The person moving about where they first go on waking and where they spend the day | Motion (PIR) where they move about; presence (mmWave) only if they sit still for long spells and no pet uses the room |
| Bathroom | Night visits, long visits, no return to bed | Someone coming in | Motion (PIR, battery is fine), inside the door, pointing in |

### PIR or mmWave

A PIR sees movement and turns off a minute or so after someone stops moving. An mmWave (radar) sensor sees a person who is still, and stays on.

| Room | With a PIR | With mmWave |
|---|---|---|
| Bathroom | Works fully: night visits, long visits and no return only need it to fire on the way in | Works, but usually needs mains, which bathrooms rarely have |
| Main room | Works for the morning check and wake time. Long spells sitting still look like quiet: set the room transition timeout to 90 minutes | Sees them sitting still, but also sees pets |
| Bedroom | Works. It goes off while they sleep, so Haiven treats them as in bed from the bedtime routine (bathroom, then bedroom) until their first morning activity, and does not count the night as quiet | Best: it stays on while they are in bed. An Everything Presence Lite also gives the bed itself (in bed, asleep) |

Neither can tell sleep from someone lying still after a fall. Haiven does not detect falls with any sensor.

Rules, in order:

1. **Bedroom prefers presence.** If you have one mmWave sensor and no pet sleeps in the bedroom, it goes here. A PIR works too (see the table above). Aim it at the bed from the side or the foot, not through the doorway.
2. **Main room goes where the day starts.** Cover the spot they reach first on getting up (the kettle, the chair, the curtains), and where they spend most of the day. Open plan: one sensor covering both. Separate kitchen and living room: cover the kitchen if the day starts with the kettle; add the living room as an extra activity source only if they sit there for hours.
3. **Pets decide the main room.** mmWave sees any moving body, including a dog or cat, so a pet in the room makes a silence look like activity and hides it. Where a pet uses the main room, use a PIR (not camera motion, which also fires on pets) mounted high (about 2 m) and angled down and away from the floor, ideally pet-immune, and test it with the pet alone in the room. Where the pet sleeps in the bedroom, the bedroom sensor will see it too: say so, and test.
4. **No sensor sees into another role's room.** mmWave passes through doors and thin walls. Do not aim it at a wall shared with the bathroom or landing: set its zone or maximum distance to stop short of that wall, and test from the other side. Keep the bathroom PIR pointing away from the door to the landing.
5. **Power and radio.** mmWave usually needs mains: check there is a socket where it must go. A Home Assistant Green has no Zigbee or Bluetooth radio, so Zigbee and Bluetooth sensors need a dongle, a Bluetooth proxy or a gateway.
6. **Kit already bought.** Allocate it by these rules, not by what it was bought for. If it does not fit (two mmWave sensors and a dog downstairs, say), say what will not work and what one extra sensor would fix. Give an owned battery PIR to the bathroom first, since the bathroom usually has no socket and the fewest options.

Write the plan as a table, room by room: sensor, where it is mounted and what it points at, why, what could go wrong (pet, a neighbouring room, no socket), and how stage 5 will test it.

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

The millimetre wave radar sensor detects presence through breathing and micro-movements.

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

Do not factory-reset this device expecting to just reconnect it to WiFi afterwards. A factory reset returns it to Everything Smart Home's stock firmware, which works with Haiven; only the reference bed-vs-room zones need the custom build — recovering from that means reflashing the custom ESPHome config, which (per the gap above) isn't published in this repo yet. If the device is genuinely unresponsive, treat it as a hardware-recovery problem, not a quick reset-and-reconnect.

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

2. **Re-add it to Home Assistant.** The BLU Motion talks Bluetooth Low Energy only; it has no Wi-Fi. Home Assistant receives it through one of:
   - a Bluetooth adapter on the hub. A Home Assistant Green has no Bluetooth radio, so it needs a USB Bluetooth adapter or one of the options below;
   - an ESPHome Bluetooth proxy within range of the bathroom;
   - a mains-powered Shelly Gen2 or later device nearby, acting as a BLU gateway over Wi-Fi.

   It then appears through the BTHome integration (Settings > Devices & services). The Shelly app, over your phone's Bluetooth, is only for setting it up. If you turn on encryption in the Shelly app, Home Assistant asks for the device's bindkey, shown in the app.

### Range

Bluetooth reaches roughly one room through walls. Put the adapter, proxy or gateway close enough that the sensor's readings arrive reliably, then do the walk test in docs/start.md.

### Troubleshooting

**Device not appearing after reset:**
- Check the adapter, proxy or gateway is online and within range
- Check the BTHome integration in Home Assistant lists it
- If the Shelly app cannot see it over Bluetooth, repeat the reset

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

### Sensor Behaviour

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
- [ ] Optimise based on patterns

---

*Last Updated: 2026-09-19*
