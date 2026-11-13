# Safety and limits

Read this before installing Haiven for someone.

**In an emergency, call 999. For urgent advice, call NHS 111.** Outside the UK, use your local emergency number.

## What Haiven is not

- Not a medical device, not telecare and not an emergency service.
- It does not detect falls. It measures time and movement in three rooms.
- It does not diagnose anything or tell you why a pattern changed.
- No one monitors alerts on your behalf, and there is no guaranteed response time.

Keep a monitored pendant or telecare service. Haiven is an addition to it, never a replacement.

## What can fail without warning

| Failure | What happens | What tells you |
|---|---|---|
| A sensor stops reporting | That room goes quiet, which can look like inactivity or hide it | A fault alert to every carer after 15 minutes, repeated each morning until it is back |
| A sensor's battery runs low | The sensor will stop soon | A fault alert at 15% or below, repeated each morning. Only for sensors that report a battery level to Home Assistant |
| A sensor keeps reporting "no motion" when it is in fact dead | The same as going offline, but Home Assistant cannot tell | Nothing automatic. The dashboard's Sensors screen shows how long each has been quiet |
| The camera, if you use one, stops reporting | No picture can follow an alert. The alerts themselves still work | A fault alert to every carer after 15 minutes, repeated each morning, and a message when it is back. A camera that reports but returns no picture is only found when an alert asks for one |
| A pet moves in the bedroom while the person is in the bathroom at night | It is taken as their return to bed, so the long-visit and no-return alerts may not fire | Nothing. Keep pets out of the bedroom at night if you rely on those alerts |
| The hub loses power or crashes | All monitoring and all alerts stop | The hub watchdog, if you set it up. See below |
| Broadband or Wi-Fi goes down | Alerts cannot leave the house | Nothing from Haiven |
| The carer's phone is off, silenced or out of signal | The alert arrives late or is missed | Nothing |

**Hub watchdog.** Home Assistant cannot report that it is itself offline, so the alert has to come from outside the house. Haiven sends a heartbeat every five minutes to an address you give it; an uptime service on the other end warns you when the heartbeats stop. It is off until you set it up:

1. Create a check with an uptime service that expects a regular signal, for example Healthchecks.io, which is open source and can be self-hosted. Set it to expect a signal every 5 minutes and to alert after 15.
2. Paste the check's address into "Hub Watchdog URL" (`input_text.haiven_heartbeat_url`, under Settings > Helpers).
3. Unplug the hub and confirm the service alerts you. Do not rely on it until you have seen this work.

Fault alerts are sent whether or not monitoring is switched on.

## A response plan

An alert is only useful if someone can act on it. Before going live:

- Name a key holder who lives nearby, or fit a key safe.
- Write down who is called, in what order, and what they do if there is no answer.
- Keep that sheet in the house and give a copy to each carer.

## False alarms

Frequent false alarms cause unnecessary call-outs and teach families to ignore alerts. To keep them down:

- Set the expected wake time, bedtime and thresholds on the Settings screen. They have no defaults.
- **Calibrate for the first seven nights.** Press "Start calibration" on the Settings screen. Until it ends, alerts still arrive, but quietly: to the first contact only, without sound, marked "[Calibrating]". Compare them with what happened and adjust. This applies to critical alerts too, so do not treat Haiven as live until calibration is over.
- **Tell it when a visitor is there.** Press "Visitor here" when a carer, cleaner or relative arrives. Alerts are quietened in the same way, marked "[Visitor present]", and it switches itself off after the number of hours you set (1 to 12). Critical alerts are not quietened during a visit.
- Fault alerts are never quietened.
- Alerts are skipped while the person is recorded as away from home, which depends on their phone's location being shared with Home Assistant.
- Pets and visitors set off the sensors. Haiven cannot tell them from the person, so movement during a visit is still counted in the day's figures. Visits are written to the activity log so you can read a day with them in mind.

## What leaves the house

Activity data is stored and processed on the hub. These are the only things that leave it.

| Path | What is sent | Default |
|---|---|---|
| Phone notifications | Alert and summary text, through Apple or Google push | On, to the carers you configure |
| Hub watchdog | A request to the address you set, with no data in it | Off until you set it up |
| Remote access | Your connection to the dashboard, through whichever method you set up | Off until you set it up |
| AI wording of summaries | The person's name and recent activity (rooms, times, bathroom visits, wake and bedtime) to the AI provider you choose | **Off.** Switch: `input_boolean.haiven_ai_summaries` |
| Camera snapshot | One still, taken only when an alert fires, kept on the hub for 14 days. If the camera is a cloud camera such as Ring, the picture passes through its maker's servers | **Off.** Switch: `input_boolean.haiven_camera_snapshots` |
| Camera AI description | That still, to the AI provider you choose, which returns one sentence describing it | **Off.** Separate switch: `input_boolean.haiven_camera_ai` |
| Ask | The person's name and the activity figures needed to answer each question, to Anthropic | **Not installed** unless you add it. See [docs/setup/ASK.md](docs/setup/ASK.md) |
| Carer locations | Each carer's phone location is read by Home Assistant to work out who is nearest. It stays on the hub, except that an alert may name the nearest carer and their distance | On for carers you add |

The project collects no telemetry and has no accounts. The activity log is committed to a local git repository on the hub three times a day and is never pushed.

## Camera (optional)

A camera is never required. Any motion-capable camera, including a Ring camera, can be the main-room sensor without pictures being taken. Snapshots are a separate choice:

- Only with the person's explicit agreement to a camera in that room, and to pictures being taken.
- A picture is taken only when an alert fires. Never on a schedule, and there is no button to look in.
- The alert is sent first and never waits for the camera. The picture follows as a second message to the first contact.
- The picture is stored on the hub, outside the folder Home Assistant serves without a login, and deleted after 14 days. View it in Home Assistant under Media, Local media, haiven.
- The AI description says what is in the frame. It can be wrong. An empty room means only that no one is in that room.
- Prefer a camera that works locally. Pictures from cloud cameras such as Ring pass through the maker's servers. Some cameras, including Ring cameras that offer live view only, cannot give Home Assistant a still at all; Haiven tells you when that happens.

## Consent

- The person agrees before go-live, including which rooms have sensors and whether a camera may take pictures.
- Each carer agrees to their phone's location being used.
- Review the setup with the person every six months.
- The family owns the hub, the admin account and the backups.
- Where capacity to consent is in doubt, follow the Mental Capacity Act best-interests process (England and Wales) or your local equivalent.

## Free, as is

Haiven is free software under the MIT licence, provided as is, without warranty of any kind. See [LICENSE](LICENSE).
