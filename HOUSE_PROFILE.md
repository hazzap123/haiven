# House profile

A description of one home and one routine, used to adapt Haiven's rules to it. See [docs/start.md](docs/start.md) and [prompts/adapt-to-house.md](prompts/adapt-to-house.md). [prompts/full-setup.md](prompts/full-setup.md) fills it in with you as an interview.

**Copy this file to `HOUSE_PROFILE.local.md` and fill in the copy.** That name is in `.gitignore`, so it stays on your machine. Do not paste it into public issues.

Use roles and times. Do not write names, addresses, phone numbers or anything that identifies the person.

## Fit

- Does anyone else live there or stay most nights? If so, Haiven is not suitable: the sensors cannot tell two people apart.
- Has the person agreed, including which rooms have sensors?
- Do they have a monitored pendant?
- Do they carry a mobile phone every time they go out?
- Broadband, and a spare socket on the router:

## Layout

Each answer decides where a sensor goes.

- One storey, or stairs? Which floor are the bedroom and the night-time toilet on?
- Kitchen and living room: one open space, or separate?
- Where they spend most of the day (room and chair):
- What they do first on getting up, and where:
- Night route from bed to toilet (en-suite, landing, downstairs); which toilet at night:
- Bed position relative to the bedroom door; door open or shut; shared wall with the bathroom?
- Each pet: rooms by day, rooms at night, upstairs or not:
- Room passed through to leave the house:
- Mains sockets near the bed, the chair or kettle, the bathroom door:
- Wi-Fi in every room?

## Sensors

| Role | Entity ID | Type (PIR, mmWave, camera motion) | Room | Power (mains, battery) |
|---|---|---|---|---|
| Main room | | | | |
| Bedroom | | | | |
| Bathroom | | | | |
| Extra | | | | |

## Routine

- Usual wake time, and how much it varies:
- First room after waking:
- Usual bedtime, and how much it varies:
- Meal times:
- Afternoon nap? Where and roughly when:
- Night-time trips (bathroom, kitchen), and whether that has changed recently:

Write "unsure" rather than guess. A week of calibration measures it.

## The week

- Days that differ from a normal weekday, and how:

## Visitors

- Paid carer visits: days and times
- Family or friends who visit regularly:
- Regular days out (these are covered by their phone's location, not by a schedule):

## Household

- Pets, and which rooms they use, including at night:
- Anything that moves and could trigger a sensor (fans, curtains by open windows, robot vacuum):

## Alerts

- Up to two carers. Carer 1 gets every alert; carer 2 gets night bathroom, concern and critical, fault and gone-out alerts. Haiven cannot route by time of day:
- Nearby key holder or key safe: yes or no
- Call order:
- What should make a carer's phone ring, in your own words:
- What you do not want to hear about:
