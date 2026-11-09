# Ask

Ask is an optional chat over the data Haiven has recorded. It answers questions such as "have night bathroom visits changed since the summer?" or "what time of day are they most active?", with a chart or a table and the dates each figure covers.

It is read-only. The integration contains no service calls, so it cannot change a setting, send an alert or contact anyone.

## Before you install

- **Admins only.** The websocket commands require a Home Assistant admin, and the Ask tab appears in the bottom bar for admins only. Carers who are not admins never see it.
- **Privacy.** Each question sends the person's name, current status and the activity figures needed to answer it to Anthropic's API. Carer locations, phone numbers, cameras, people and device trackers are screened out and never sent (`ha_integrations/haiven_chat/policy.py`).
- **Cost.** Ask uses Claude Opus 5.5 at $4 per million input tokens and $20 per million output tokens, well above the Haiku used for daily summaries. Spend is capped at $50 a calendar month, with a warning at $40; both are `BUDGET_LIMIT_USD` and `BUDGET_WARN_USD` in `const.py`. Every turn is logged to `/config/haiven_chat_usage.jsonl`.
- **It is not a clinician.** The prompt forbids diagnosis, medical advice and reassurance. "Nothing unusual in the sensors" is as far as it goes.

## Install

Ask needs the Anthropic Conversation integration installed and reuses its API key. It works whether or not AI wording of summaries is switched on. The key is read from that integration and never copied.

```bash
# From your clone, after scripts/setup.sh
mkdir -p /config/custom_components
cp -r ha_integrations/haiven_chat /config/custom_components/
```

1. Restart Home Assistant.
2. Go to Settings > Devices & Services > Add Integration, search for "Haiven Chat", and pick your Anthropic integration.
3. Open the Haiven dashboard as an admin. Ask is in the bottom bar.

`scripts/ask_days.py`, `scripts/routine_stats.py`, `scripts/drift_stats.py` and `scripts/night_stats.py` must be in `/config/scripts/`. The main install copies them.

## Tell it about your home

`custom_components/haiven_chat/rules.txt` is the prompt. The last section, "Household notes", is yours to edit: pets that set off the kitchen sensor, rooms the sensors do not cover, a carer who visits on fixed days. Without these the model cannot know that late evening kitchen motion is the dog.

After editing, reload the integration (Settings > Devices & Services > Haiven Chat > Reload). No restart is needed.

## What it reads

| Tool | Source |
|------|--------|
| Daily history: wake, bedtime, night visits, routine verdict, movement | `scripts/ask_days.py`, the same code as the dashboard |
| Counts by hour, weekday or month | `/config/activity.log` |
| One day's events | `/config/activity.log` |
| Current state of a sensor | Home Assistant, through the screen in `policy.py` |

Figures on charts go from the server straight to the card and never pass through the model, so a number on a chart cannot be one the model invented.

## Troubleshooting

- **"Set up the Anthropic integration first"**: add the Anthropic integration, then add Haiven Chat.
- **No Ask tab**: you are not signed in as an admin, or `www/haiven-cards.js` is an old copy. Re-copy it from `www-src/` and hard-refresh.
- **Answers stop mid-month**: the monthly cap is reached. Raise `BUDGET_LIMIT_USD` in `const.py` and restart, or wait for the month to roll over.
- **"stats_failed" or "stats_timeout"**: run `python3 /config/scripts/ask_days.py | head -c 300` on the box and read the error.
