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
| A sensor goes offline or its battery dies | That room goes quiet, which can look like inactivity or hide it | The dashboard's Sensors screen and the sensor line in each summary. There is no push alert for this yet |
| The hub loses power or crashes | All monitoring and all alerts stop | Nothing. Home Assistant cannot report that it is itself offline. See "Hub watchdog" below |
| Broadband or Wi-Fi goes down | Alerts cannot leave the house | Nothing from Haiven |
| The carer's phone is off, silenced or out of signal | The alert arrives late or is missed | Nothing |

**Hub watchdog.** Haiven does not include one yet. Until it does, use an outside uptime-monitoring service that expects a regular signal from the hub and warns you when it stops. Test it by unplugging the hub before you rely on it.

## A response plan

An alert is only useful if someone can act on it. Before going live:

- Name a key holder who lives nearby, or fit a key safe.
- Write down who is called, in what order, and what they do if there is no answer.
- Keep that sheet in the house and give a copy to each carer.

## False alarms

Frequent false alarms cause unnecessary call-outs and teach families to ignore alerts. To keep them down:

- Set the expected wake time, bedtime and thresholds on the Settings screen. They have no defaults.
- Run for at least a week and compare what Haiven records with what happened before trusting it.
- Alerts are skipped while the person is recorded as away from home, which depends on their phone's location being shared with Home Assistant.
- Pets and visitors set off the sensors. Haiven cannot tell them from the person.

## What leaves the house

Activity data is stored and processed on the hub. These are the only things that leave it.

| Path | What is sent | Default |
|---|---|---|
| Phone notifications | Alert and summary text, through Apple or Google push | On, to the carers you configure |
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
