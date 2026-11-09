# Adapt Haiven to a house

A prompt for an AI coding assistant such as Claude Code or Codex. Run it in your local copy of your Haiven config, after filling in `HOUSE_PROFILE.local.md`.

AI tools make mistakes. Read every diff before applying it, and keep a backup of the working config.

```
Read SAFETY.md, SCOPE.md and HOUSE_PROFILE.local.md.

Adapt the Haiven package to this house:
- map every sensor in the profile to a role; the three default entity IDs
  are replaced by scripts/setup.sh, so use the IDs already in the files
- add rooms the profile lists, such as a separate living room, as extra
  activity sources alongside the kitchen
- set the expected wake time, bedtime, their variances, the bedtime window
  and the earliest wake time from the profile's routine; these are helpers
  in packages/haiven_monitoring_inputs.yaml, not fixed clock times
- note pets and uncovered rooms in the "Household notes" section of
  ha_integrations/haiven_chat/rules.txt if Ask is installed

Follow every rule in SCOPE.md. In particular:
- never remove or weaken the morning activity check, the no-activity
  alert, the night bathroom alerts or the status-change notification
- every message goes through script.haiven_compose_message so it sends
  without AI
- no clinical wording
- no names or addresses in any file

Run `pytest` and show me the diff before changing anything live.
Tell me which requests in the profile you could not meet and why.
```

## Example follow-up prompts

- "Add a living room sensor and count it towards the morning routine."
- "Treat a smart plug on the kettle drawing power as kitchen activity."
- "The bathroom is on the landing, not en-suite. Check the night bathroom rules still make sense."

## After any change

Repeat the walk test in each room, then run a few nights and compare what Haiven recorded with what happened before relying on it again.

Haiven has no visitor setting yet, so a carer's visit is counted as the person's activity. Do not ask the assistant to invent one that silences alerts; note the visit times in the profile so you can read the data with them in mind.
