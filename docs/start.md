# Install Haiven

Read [SAFETY.md](../SAFETY.md) first. Get the person's agreement before installing, including which rooms have sensors.

Needs Home Assistant 2024.10 or later.

## Path 1: already running Home Assistant

1. **Add the Haiven package to your config.** Clone the repository somewhere other than `/config`, run `scripts/setup.sh` to enter your three sensor entity IDs, and copy the files across. Step by step: [setup/QUICKSTART.md](setup/QUICKSTART.md).
2. **Assign sensors to three roles:** main room, bedroom, bathroom. `setup.sh` does this. Hardware notes: [reference/SENSOR_GUIDES.md](reference/SENSOR_GUIDES.md).
3. **Set their usual wake and bed times** on the dashboard's Settings screen. They have no defaults, and alerts are unreliable until they are set.
4. **Add the carers who should get alerts.** [setup/CARE_CIRCLE.md](setup/CARE_CIRCLE.md).
5. **Set up the hub watchdog** as described in [SAFETY.md](../SAFETY.md), then unplug the hub and confirm you are told.
6. **Fire a test alert** and confirm it reaches each carer's phone.

## Path 2: new to Home Assistant

**At home, before the visit**

1. Set up the hub and create the admin account.
2. Pair every sensor on the table and label each one with its role.
3. Follow Path 1 above.
4. Set up remote access so you can reach the dashboard from your own home.
5. Send a test alert.

**One visit**

1. Plug the hub into their router by ethernet, so a Wi-Fi password change cannot take it offline.
2. Place the sensors. Walk each room and confirm it registers on the dashboard.
3. Label the hub's plug "do not unplug".
4. **Pulled-plug test:** unplug the hub and confirm the watchdog alert arrives. Plug it back in.
5. Agree the response plan with them: who is called, in what order, and who holds a key. Write it down and leave a copy in the house.

**The first week**

Press "Start calibration" on the Settings screen before you leave. For seven nights alerts arrive quietly, to the first contact only, marked "[Calibrating]". Compare each one, and each day's wake time and bedtime, with what happened. Adjust the times and thresholds until they match. Calibration ends by itself and tells you; press "Start calibration" again if you need longer.

## Adapt it to their house

Every house and routine is different. Fill in a copy of [HOUSE_PROFILE.md](../HOUSE_PROFILE.md), then use [prompts/adapt-to-house.md](../prompts/adapt-to-house.md) with an AI coding assistant to adapt the rules. The limits any change must keep are in [SCOPE.md](../SCOPE.md).

## Before you go live

- They have agreed, and know which rooms have sensors.
- Each carer has agreed to their phone's location being used.
- A nearby key holder or key safe is named.
- The call order is written down and in the house.
- The hub watchdog is set up, and you were alerted when you unplugged the hub.
- Calibration has ended and the alerts you saw during it made sense.
- They still have a monitored pendant.

## Optional extras

- **AI wording of summaries.** Off by default. See the privacy note in the [README](../README.md).
- **Ask**, a read-only chat over the recorded data. [setup/ASK.md](setup/ASK.md).

## Help

Post in GitHub Discussions with your Home Assistant version and logs. Remove names, addresses and entity IDs that identify the home first.
