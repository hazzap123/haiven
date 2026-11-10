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
| Ask | The person's name and the activity figures needed to answer each question, to Anthropic | **Not installed** unless you add it. See [docs/setup/ASK.md](docs/setup/ASK.md) |
| Carer locations | Each carer's phone location is read by Home Assistant to work out who is nearest. It stays on the hub, except that an alert may name the nearest carer and their distance | On for carers you add |

The project collects no telemetry and has no accounts. There is no camera support in this repository. The activity log is committed to a local git repository on the hub three times a day and is never pushed.

## Consent

- The person agrees before go-live, including which rooms have sensors.
- Each carer agrees to their phone's location being used.
- Review the setup with the person every six months.
- The family owns the hub, the admin account and the backups.
- Where capacity to consent is in doubt, follow the Mental Capacity Act best-interests process (England and Wales) or your local equivalent.

## Free, as is

Haiven is free software under the MIT licence, provided as is, without warranty of any kind. See [LICENSE](LICENSE).
