# Scope

What Haiven is for, what it is not for, and the rules any change must keep. Read with [SAFETY.md](SAFETY.md).

## In scope

- **One person living alone**, monitored with their agreement by family or friends.
- **Three sensor roles:** main room (kitchen or living area), bedroom, bathroom. Any motion or presence sensor Home Assistant supports can fill a role.
- **Routine, not events.** Wake time, bedtime, movement between rooms, night bathroom visits, and how each day compares with the person's own usual days.
- **Alerts to named carers** when the routine does not happen: no morning activity, a long silence, an unusually long night bathroom visit.
- **Slow change.** Drift Watch compares a month of nights with a fixed baseline.
- **Running on a hub in the house**, with no subscription and no account.

## Out of scope

- Fall detection, vital signs, medication, or any clinical judgement.
- More than one person living in the home. The sensors cannot tell people apart.
- Emergency response. Haiven tells a carer; the carer decides what to do.
- Cameras. Not supported in this repository.
- Tracking the person outside the home beyond "home" or "away".
- Any cloud service that holds the activity data.

## Rules for every change

These apply to contributors and to anyone adapting Haiven to a house, with or without an AI coding assistant.

1. **Never remove or weaken a safety alert**: the morning activity check, the no-activity alert, the night bathroom alerts, the status-change notification and the fault alerts. Fault alerts are never gated on monitoring being switched on. Holding alerts back (visitor present, calibration) may quieten an alert but must never drop one, must end by itself, and must never apply to fault alerts. Changing a threshold needs evidence from real days.
2. **An alert must send without AI.** Every message goes through `script.haiven_compose_message`, which falls back to plain text. Do not call a conversation agent directly from an automation.
3. **AI wording stays off by default.** No activity data leaves the hub for an AI provider unless the installer switches it on.
4. **No clinical wording.** Describe what the sensors recorded. Do not name a cause, a condition or a diagnosis, and do not reassure.
5. **No names or addresses in any file.** Use roles ("main room", "carer 1") and times.
6. **No hard-coded hours for a household's routine.** Windows come from the helpers on the Settings screen.
7. **Run the tests and read the diff** before anything goes live. Keep a backup of the working config.
