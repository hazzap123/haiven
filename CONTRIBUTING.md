# Contributing to Haiven

Haiven is built by people caring for someone at a distance. Contributions from others doing the same are welcome: bug reports, sensor guides for hardware we have not covered, and fixes.

## Ground rules

1. **This watches a real person.** A change that makes an alert fire less often needs evidence that it still fires when it should. Say what you tested and on how many days of data.
2. **No personal data.** No real names, addresses, phone numbers, device IDs, hostnames, photos or activity logs, in code, tests, docs or commit messages. Use `person.elderly_person`, "Mary Smith" and the placeholder sensor IDs.
3. **Not a medical device.** Do not add wording that diagnoses, reassures or implies clinical accuracy.
4. **Sensor-agnostic.** The three room sensors are `event.kitchen_motion`, `binary_sensor.haiven_bedroom_occupancy` and `binary_sensor.haiven_bathroom_motion`; `scripts/setup.sh` rewrites them for each installer. Do not hard-code a vendor's entity IDs.

## Running the tests

No Home Assistant needed.

```bash
pip install pytest pyyaml
pytest
node --check www-src/haiven-cards.js
```

The tests check, among other things, that every entity the dashboard, automations and docs refer to is defined in this repo (`tests/test_entities.py`) and that the docs match what the repo does (`tests/test_docs.py`). CI runs the same commands on every pull request.

## Making a change

- Branch from `main`, one change per pull request.
- Use the current automation schema: `triggers:` / `trigger:`, `actions:` / `action:`.
- A new entity needs a row in `docs/reference/ENTITY_REFERENCE.md`.
- A new threshold needs a comment saying where the number came from.
- British English in docs.

## Reporting a bug

Open an issue with your Home Assistant version, your three sensor types, what happened and what you expected. Remove names, addresses and entity IDs that identify your home before pasting logs.

## Security and privacy issues

If you find a way Haiven leaks the monitored person's data or a carer's location, do not open a public issue. Use GitHub's private vulnerability reporting on this repository.
