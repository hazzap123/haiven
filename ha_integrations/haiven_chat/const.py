"""Constants for Haiven Chat."""

from __future__ import annotations

DOMAIN = "haiven_chat"

CONF_ANTHROPIC_ENTRY_ID = "anthropic_entry_id"

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 2048
# Exploring a year of data takes a few lookups.
MAX_TOOL_ROUNDS = 6

# USD per million tokens, claude-opus-5-5.
PRICE_INPUT = 4.0
PRICE_OUTPUT = 20.0
PRICE_CACHE_READ = 0.20
PRICE_CACHE_WRITE = 5.0  # 5-minute TTL, 1.25x input

BUDGET_LIMIT_USD = 50.0
BUDGET_WARN_USD = 40.0

MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_CHARS = 8000

MAX_STREAMS_PER_USER = 1
MAX_STREAMS_TOTAL = 2
MAX_TURNS_PER_MINUTE = 6

SERIES_TTL_S = 30 * 60
DAYS_TTL_S = 15 * 60

FLUSH_INTERVAL_S = 0.075
FLUSH_CHARS = 256

USAGE_LOG = "haiven_chat_usage.jsonl"
STORE_KEY = "haiven_chat.usage"
STORE_VERSION = 1

ACTIVITY_LOG = "activity.log"
DAYS_SCRIPT = "scripts/ask_days.py"

# Read each turn so "how are they now" needs no tool call.
KEY_SENSORS = {
    "input_text.current_summary": "Latest AI summary",
    "input_text.elderly_person_name": "Name of the person being monitored",
    "sensor.elderly_person_location": "Where they are now",
    "binary_sensor.elderly_person_home": "Home",
    "sensor.today_wake_time": "Woke today",
    "sensor.activity_data": "Last seen",
    "sensor.routine_stats": "Routine verdict today",
    "sensor.drift_stats": "Drift Watch",
}
