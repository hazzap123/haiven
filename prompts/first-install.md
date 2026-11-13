# First install with an AI coding assistant

A prompt for Claude Code, Codex or a similar tool that walks through installing Haiven on a Home Assistant hub with you. Use it for Path 1 in [docs/start.md](../docs/start.md): Home Assistant is already running and you can reach it. For the whole job, from planning the house to calibration, use [full-setup.md](full-setup.md).

## Before you start

- **Read [SAFETY.md](../SAFETY.md)** and get the person's agreement.
- **Give the assistant access to the hub.** It needs to read and write the hub's `/config` folder and run `ha` commands. On Home Assistant OS that usually means the Samba share add-on (to see `/config` from your computer) and the Terminal & SSH add-on. Alternatively, run the assistant on your computer and paste its commands into the hub's terminal yourself.
- **Know which three sensors you will use** (main room, bedroom, bathroom), and have the Home Assistant app installed on each carer's phone and on the person's phone if they carry one.

The assistant will ask you questions. It must not guess the answers.

AI tools make mistakes. Read each change before you agree to it.

## The prompt

```
You are helping me install Haiven, a Home Assistant package, on a live
hub that may already hold my own automations. Work step by step, show me
each change before you make it, and stop and ask whenever anything is
unclear. Do not guess entity IDs, names or phone services: ask me.

First read these files from https://github.com/hazzap123/haiven:
SAFETY.md, SCOPE.md, docs/start.md, docs/setup/QUICKSTART.md and
configuration.yaml.

1. Check before touching anything
   - Home Assistant is 2024.10 or later (`ha core info`).
   - kiosk-mode is installed through HACS (/config/www/community/kiosk-mode
     exists). If not, stop and tell me how to install it.
   - Make a full backup: `ha backups new --name pre-haiven`. Wait for it
     to finish and confirm it is listed. Do nothing else until it is.
   - Tell me whether /config already has its own configuration.yaml,
     automations.yaml, scripts.yaml and scenes.yaml, and roughly what is
     in them.

2. Get Haiven
   - Clone the repository to ~/haiven, never into /config.

3. Choose the three sensors
   - List the motion, occupancy and presence entities from
     /config/.storage/core.entity_registry, with their friendly names.
   - Ask me which one is the main room, the bedroom and the bathroom.
   - Run scripts/setup.sh in ~/haiven with my three answers, then confirm
     no default sensor IDs remain:
     grep -rn "event.kitchen_motion\|haiven_bedroom_occupancy\|haiven_bathroom_motion" \
       packages configuration.yaml automations.yaml scripts.yaml \
       haiven_sensors_3sensor.yaml www-src lovelace
     should print nothing. Run pytest before setup.sh, not after:
     some tests name the default sensor IDs.

4. People and carers
   - Ask me for the monitored person's first name, each carer's name, and
     which device_tracker and notify.mobile_app_* service belongs to each.
     List the ones that exist so I can choose.
   - Do not write names, trackers or notify services into ~/haiven: git
     tracks it. Fill them in after step 5, in the copies on the hub:
     route A, /config/haiven_persons.yaml and
     /config/packages/haiven_care_circle_inputs.yaml; route B, the
     haiven_core person list and the haiven_care_circle_inputs package
     in /config/packages/haiven.yaml. Regenerating haiven.yaml overwrites
     them, so keep a note of what you changed in the progress file and
     redo it after any regenerate.
   - Keep the ids elderly_person, contact_1 and contact_2, even if a carer
     already has a person of mine: two automations trigger on
     person.contact_1 and person.contact_2 by name. A second person for
     the same phone is harmless. Change only names, trackers and notify
     services. Leave the phone fields as placeholders unless I give you a
     number.
   - In haiven_persons.yaml, or haiven_core's person list on route B,
     change only the device_trackers, never the
     names "Elderly Person", "Contact 1" and "Contact 2": Home Assistant
     builds person.elderly_person and the others from those names, and
     Haiven treats the person as always away if they change. Real names
     go in the name helpers in haiven_care_circle_inputs.

5. Copy into /config
   Before anything is copied:
   - Check none of Haiven's entity IDs already exist in my entity
     registry (/config/.storage/core.entity_registry) or in my YAML
     (entities without a unique_id are not in the registry). Report any
     clash, never rename my entity, and stop until we agree what to do.
   - Copy each file of mine you will change to <name>.pre-haiven. Record
     in the progress list every file Haiven adds, and only the folders
     that did not exist before (check first: /config/scripts or
     /config/www may already be mine).
   Then take ONE of these two routes, and tell me which and why:
   A. My configuration.yaml, automations.yaml and scripts.yaml are empty
      or only have Home Assistant's defaults: copy Haiven's
      configuration.yaml, automations.yaml, scripts.yaml, scenes.yaml,
      haiven_sensors_3sensor.yaml, haiven_persons.yaml, haiven_zones.yaml,
      packages, lovelace and themes as they are.
   B. Otherwise: run python3 scripts/make_package.py --out haiven.yaml in
      ~/haiven and copy haiven.yaml into the folder my configuration.yaml
      loads with packages: !include_dir_merge_named. If I have no packages
      key, add exactly that one line under homeassistant:, after showing
      me. If my packages are listed by name instead, show me and ask.
      Copy Haiven's lovelace folder, and its themes/haiven*.yaml into my
      themes folder. Change nothing else in my configuration.yaml,
      automations.yaml or scripts.yaml.
   On either route:
   - Copy scripts/*.py and scripts/*.sh, except setup.sh and
     make_package.py, into
     /config/scripts. Never run setup.sh in /config: it rewrites every
     YAML file under the folder it runs in.
   - Copy www/haiven-*.js, made by setup.sh, into /config/www.
   - Route A only: create /config/haiven_snapshots before the check.
     Haiven's configuration.yaml names it, and Home Assistant rejects the
     core config if it is missing. On route B, add it and the
     allowlist_external_dirs and media_dirs lines only if I choose the
     camera later.

6. Check, then restart only when I say so
   - Run `ha core check`. If it reports errors, fix only what Haiven
     caused, show me, and check again.
   - Ask me before running `ha core restart`.

7. After the restart, tell me what to do on the dashboard
   - Set the expected wake time, bedtime and thresholds on the Settings
     screen. They have no defaults.
   - Set up the hub watchdog as SAFETY.md describes, and do the
     pulled-plug test.
   - Send a test alert to each carer.
   - Press "Start calibration" before relying on alerts.

Rules
- Never delete anything, and never remove or edit my own automations,
  scripts, scenes or dashboards.
- Do not switch on AI wording, the camera, or Ask. They are off by
  default and are my decision after reading SAFETY.md.
- Do not change any threshold or time window: those are set on the
  Settings screen.
- Do not put API keys, tokens or passwords in any file or in this chat.
- The names and phones you write go into my hub only. Do not commit them
  to git or paste them anywhere public.
- If something fails, stop, tell me what failed, and tell me how to
  restore the backup from step 1.
```

## If it goes wrong

To take Haiven out: delete the files and folders the assistant listed, put back the `.pre-haiven` copies of your own files and then delete those copies, delete `/config/activity.log`, and restart. Then remove the leftover Haiven entities under Settings, Devices & services, Entities (filter on "haiven" and on "not provided"). Their history ages out of the recorder on its own. If Home Assistant will not start, restore the backup from step 1: Settings, System, Backups, then the `pre-haiven` backup, then Restore. A full restore also undoes everything else changed on the hub since.
