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
     grep -rn "event.kitchen_motion\|haiven_bedroom_occupancy\|haiven_bathroom_motion"
     should only match my answers.

4. People and carers
   - Ask me for the monitored person's first name, each carer's name, and
     which device_tracker and notify.mobile_app_* service belongs to each.
     List the ones that exist so I can choose.
   - Fill in haiven_persons.yaml and packages/haiven_care_circle_inputs.yaml
     in ~/haiven. Keep the ids elderly_person, contact_1 and contact_2:
     everything else refers to them. Change only names, trackers and
     notify services. Leave the phone fields as placeholders unless I give
     you a number.

5. Copy into /config
   - Copy packages, scripts, www, www-src, lovelace and themes, plus
     haiven_sensors_3sensor.yaml, haiven_persons.yaml and haiven_zones.yaml.
     If any file of the same name already exists in /config, show me the
     difference and ask before replacing it.
   - Never overwrite my configuration.yaml, automations.yaml, scripts.yaml
     or scenes.yaml if they hold anything of mine. Merge instead:
     add Haiven's homeassistant (packages, allowlist_external_dirs,
     media_dirs), frontend, lovelace, shell_command, command_line,
     recorder, sensor and person blocks to my configuration.yaml, and
     append Haiven's automations and scripts to mine. If a key already
     exists in mine, show me both and ask. Show me the full diff of each
     file before saving.
   - If my configuration already loads a packages folder
     (!include_dir_merge_named) or keeps automations in a folder, put
     Haiven's files in their own subfolder or file there instead, and do
     not add a second packages or automation key. Never append to an
     automations.yaml that the UI editor manages.
   - Before copying, check none of Haiven's entity IDs already exist in
     my entity registry (/config/.storage/core.entity_registry), and
     report any clash.
   - Before saving, copy each file of mine you change to
     <name>.pre-haiven and list every file Haiven adds, so it can be
     taken out again without restoring the whole hub.
   - If my files are empty or missing, use Haiven's as they are.

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

To take Haiven out, delete the files the assistant listed and put back the `.pre-haiven` copies of your own files, then restart. If Home Assistant will not start, restore the backup from step 1: Settings, System, Backups, then the `pre-haiven` backup, then Restore. A full restore also undoes everything else changed on the hub since.
