# Diagnosing Haiven on the hub

For you, or an AI assistant, connected to the hub over SSH with the Terminal & SSH add-on. Commands run on the hub unless marked otherwise. Show each command before running it, and change nothing without saying so first.

## What may be read

| What | Command or path | Use |
|---|---|---|
| Config | `/config/configuration.yaml`, `automations.yaml`, `scripts.yaml`, `packages/` | What is installed |
| Config check | `ha core check` | Errors before a restart |
| Logs | `ha core logs` (or `/config/home-assistant.log`) | Errors at runtime; search for `haiven`, `template`, `Error` |
| Versions and network | `ha info`, `ha network info` | Home Assistant version, the hub's address |
| Add-ons | `ha --help`, then the add-on (or app) list command it shows | Whether SSH and Tailscale are running. The command name has changed between versions, so check first |
| Entities | `/config/.storage/core.entity_registry`, `core.device_registry` | Entity IDs, which device each belongs to, clashes, renamed people |
| Activity | `/config/activity.log` | What each sensor logged; the walk test |
| Night statistics | `python3 /config/scripts/night_stats.py` | Bed, wake, visits and trips per night, for stage 6 |

### Live states and templates

From inside the SSH add-on, Home Assistant's API is reachable with the token the add-on is given:

```sh
curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  http://supervisor/core/api/states/binary_sensor.elderly_person_home

curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template": "{{ states(\"sensor.minutes_since_bedroom_activity\") }}"}' \
  http://supervisor/core/api/template
```

If these return 401, the add-on does not have API access on this hub. Use the logs and the dashboard instead. Do not ask for a long-lived access token in a chat.

## Never read or print

- `secrets.yaml`
- `.storage/auth`, `.storage/auth_provider.homeassistant`, `.storage/core.config_entries`: logins and integration tokens
- Home Assistant Cloud and Tailscale credentials
- `go2rtc.yaml`, if a camera is set up: it can hold a camera account login
- backups

Do not copy lines of `activity.log` anywhere outside the session: they are the person's routine.

## Common problems

| Symptom | Check |
|---|---|
| The person always reads as away; morning checks skipped | `person.elderly_person` exists and is `home`. If the person has another entity ID, the names in `haiven_persons.yaml` were changed; see that file |
| No "Kitchen" lines in `activity.log` | `binary_sensor.haiven_kitchen_motion` exists (it comes from Haiven's template block) |
| A room logged as "Unknown" | The sensor's entity ID must contain the room word (`bedroom`, `bathroom`) and `motion`, `presence` or `occupancy` |
| Overnight alerts with a PIR in the bedroom | `input_select.bed_state` should be `in_bed` after bedtime is detected; check `sensor.today_bedtime` is set |
| A sensor never reported as offline | Some battery sensors never go `unavailable`. Check the Sensors screen weekly |
| Config check passes but an alert never fires | `ha core logs` for template errors; render the template with the API call above |
