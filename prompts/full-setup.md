# Full setup with an AI coding assistant

A prompt for Claude Code, Codex or a similar tool that takes a family from nothing to a tuned, handed-over Haiven install. It covers planning the home and routine, buying and pairing sensors, installing, testing, a week of calibration against real data, and handover.

It runs in seven stages over about ten days, most of it waiting for the calibration nights. The assistant stops at the end of each stage and waits for you to say go on. Start it again any time with "We are at stage N".

Already running Home Assistant and only want the software installed? [first-install.md](first-install.md) is shorter. This prompt uses it for stage 3.

## Before you start

- **Read [SAFETY.md](../SAFETY.md)** and get the person's agreement, including which rooms will have sensors.
- **Decide where the assistant runs.** It needs to read and write the hub's `/config` folder and run `ha` commands from stage 3 on. On Home Assistant OS that usually means the Samba share add-on and the Terminal & SSH add-on. You can instead run it on your computer and paste its commands into the hub's terminal yourself.
- **Have about an hour for stage 1.** It is a conversation about the person's home and day. Ask them, or someone who knows their routine well; the answers matter more than anything else here.

AI tools make mistakes. Read each change before you agree to it.

## The prompt

```
You are helping me set up Haiven, an open source Home Assistant package
that watches a person's daily routine at home with three sensors and
alerts their family when something looks wrong. Work in the stages below.
At the end of each stage, show me what was done and what is next, then
stop and wait for me to say go on. If I say "we are at stage N", read
the files you need and continue from there.

First read these files from https://github.com/hazzap123/haiven:
SAFETY.md, SCOPE.md, HOUSE_PROFILE.md, docs/start.md,
docs/reference/SENSOR_GUIDES.md, docs/setup/CARE_CIRCLE.md,
prompts/first-install.md and prompts/adapt-to-house.md.

Never guess an entity ID, a name, a time or a phone service: ask me.

STAGE 1. The home and the routine
Interview me to fill in HOUSE_PROFILE.local.md, a copy of
HOUSE_PROFILE.md. Ask one short group of questions at a time, in this
order, and wait for each answer:
  a. Rooms: floors, stairs, open-plan or separate kitchen and living
     room, where the bathroom is and how many there are, rooms they use
     most days.
  b. A normal weekday, from waking to bed: when they get up and how much
     that varies, the first room they go to, meals, any afternoon nap and
     where, the evening, when they go to bed and how much that varies.
  c. The week: days that differ (a day centre, church, shopping, a
     regular visitor), and paid carer visits by day and time.
  d. Nights: how often they usually get up, to where, and whether that
     has changed recently.
  e. Household: pets and which rooms they use at night, anything else
     that moves (fans, curtains, a robot vacuum), who else stays over.
  f. Alerts: who the carers are by role (carer 1, carer 2), who gets
     woken at night, a nearby key holder or key safe, and the call order.
  g. What would worry me: in my own words, what should make my phone
     ring, and what I do NOT want to hear about.
If I am unsure of a time, write "unsure" rather than a guess: stage 6
measures it.

Then show me the profile back and tell me plainly, for each answer:
  - what Haiven will use (wake time, bedtime and their variances, the
    bedtime window, earliest wake time, extra rooms as activity sources,
    the no-activity hours, the carers and their order);
  - what Haiven records but cannot act on, and why. In particular it
    cannot quieten alerts on a schedule, such as every Tuesday, because
    SCOPE.md forbids it: for visits there is the "Visitor here" button,
    and an away day is covered by their phone's location;
  - anything in "what would worry me" that Haiven does not do. Say so.
    Do not promise falls detection, health judgements or a response.
Write only roles and times in the file. No names, addresses or phone
numbers. It stays on my machine; it is in .gitignore.

STAGE 2. Hardware and the hub
  - From the profile and SENSOR_GUIDES.md, propose one sensor per role
    (main room, bedroom, bathroom), and any extra room sensor the layout
    needs, with the reason for each and whether it is mains or battery.
    Note anything the profile makes awkward, such as pets in the main
    room at night or a bathroom shared with a lodger. I choose.
  - Ask whether I already have Home Assistant. If not, walk me through
    the hub (a Home Assistant Green or similar), creating the admin
    account, HACS and kiosk-mode, one step at a time. I do the clicking;
    you tell me what to look for.
  - Help me pair each sensor and confirm it appears in Home Assistant.
    Ask me to label each one with its role.
  - Help each carer install the Home Assistant app, sign in, allow
    notifications and location, and confirm their notify.mobile_app_*
    service and device_tracker exist. The same for the person's phone
    if they carry one, for home and away.

STAGE 3. Install
Follow prompts/first-install.md, steps 1 to 6, exactly as written,
including the backup first and asking before the restart. Use the
three sensors and the carers from stages 1 and 2.

STAGE 4. Fit it to the house
Follow prompts/adapt-to-house.md with the profile. Start loose; stage 6
tightens it with real data:
  - Expected wake time and bedtime from the profile, or my best guess.
  - Wake and bedtime variance at 60 minutes, or 90 where I said "unsure"
    or that it varies a lot.
  - Leave Bedtime Window Start and End and Earliest Wake Time at 00:00,
    so they follow from the expected times, unless the profile shows a
    reason not to, such as a regular early start.
  - Add extra rooms as activity sources only, never as a replacement for
    the three roles.
Show me each setting and where it is on the Settings screen. Run pytest
and show me any config diff before applying it.

STAGE 5. Prove it works
Walk me through each test, one at a time, and record pass or fail:
  - Walk test: I go into each room; you confirm the right sensor fires
    and the dashboard shows it. Then I sit still for two minutes in the
    bedroom and you confirm presence holds.
  - A test alert reaches each carer's phone.
  - Fault alert: I unplug or remove the battery from one sensor; every
    carer is told within about 15 minutes, and again when it is back.
  - Hub watchdog: set up as SAFETY.md describes, then I unplug the hub
    and the alert arrives. Plug it back in.
  - Home and away, if the person carries a phone: a real trip out of 15
    minutes or more gives "gone out" and "back".
  - Optional features: tell me what AI wording, the camera and Ask each
    send outside the house, from SAFETY.md, and leave each off unless I
    say otherwise after reading it. If I turn the camera on, the camera
    fault alert must pass the same test as the sensors.
Then press "Start calibration" on the Settings screen. For seven nights
alerts arrive quietly, to the first contact only, marked [Calibrating].
Tell me to write down, each day, anything unusual: a late night, a
visitor, a day out. Stop here until the seven nights have passed.

STAGE 6. Calibrate against real data
After at least seven nights:
  - Run python3 /config/scripts/night_stats.py and read the "nights"
    list: for each night its bed time, wake time, bathroom visits and
    downstairs trips.
  - Ask me for my notes from the week, and set aside any night I say was
    unusual. Also flag any night whose bed time is more than three hours
    from the others: the bed time rule can misread an evening.
  - Show me a table: what I said in stage 1, what was measured (earliest,
    middle and latest), and what you propose. Propose:
      Expected wake time and bedtime: the middle measured value.
      Variances: the larger of 30 minutes and the furthest a normal
        night was from the middle, rounded up to the next 15 minutes.
      Bedtime Window: from an hour before the earliest measured bed time
        to an hour after the latest, only if 00:00 would not cover them.
      Earliest Wake Time: 30 minutes before the earliest measured wake,
        only if 00:00 would not cover it.
  - Go through every alert from the calibration week with me: was it
    real, or a false alarm, and which setting caused it.
  - Where what I said and what was measured disagree by more than 30
    minutes, say so plainly and ask which to trust. Do not quietly pick.
  - Propose a change to the no-activity hours only with evidence from
    the week, and say what it is. Never propose turning off the morning
    check, the no-activity alert, the night bathroom alerts, the
    status-change notification or the fault alerts. SCOPE.md rule 1
    forbids it.
I change the settings on the Settings screen myself. Then I may press
"Start calibration" again for a second week if the false alarms were
more than about one a day.

STAGE 7. Hand over
  - Write a one-page response plan from the profile: who is called, in
    what order, who holds a key, the hub's location and "do not unplug".
    Roles only in anything saved; I add names and numbers on paper.
  - Check every item in "Before you go live" in docs/start.md with me.
  - Remind me to review the setup with the person every six months. At
    each review, run stage 6 again with all the nights since, and update
    HOUSE_PROFILE.local.md.
  - Finish with a checklist of every stage and test, marked done, failed
    or skipped, with the reason for anything not done.

Rules
- Never delete anything, and never remove or edit my own automations,
  scripts, scenes or dashboards.
- Do not switch on AI wording, the camera or Ask yourself.
- Follow SCOPE.md in every change. No clinical wording, no claims of
  fall detection, nothing that silences or drops an alert on a schedule.
- Do not put API keys, tokens or passwords in any file or in this chat.
- Names, phones and addresses go into my hub only. Do not commit them
  to git or paste them anywhere public.
- If something fails, stop, tell me what failed, and tell me how to
  restore the backup from stage 3.
```

## If it goes wrong

Restore the backup from stage 3: Settings, System, Backups, then the `pre-haiven` backup, then Restore. Nothing Haiven adds survives a restore.

## Why stage 6 matters

A family's estimate of wake and bed times can be well out, and a variance set tighter than the person's real routine produces false alarms. SCOPE.md asks for evidence from real days before any threshold changes. Measuring a week before tightening anything does that, and keeps the early alerts worth answering.
