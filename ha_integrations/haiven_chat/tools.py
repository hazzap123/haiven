"""The read-only tools. There is no service call anywhere in this integration."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from . import activity
from .const import ACTIVITY_LOG, DAYS_SCRIPT, DAYS_TTL_S, SERIES_TTL_S
from .policy import (
    READABLE_DOMAINS,
    PolicyError,
    SeriesStore,
    check_readable,
    clean_attributes,
    domain_of,
    is_denied,
)

ROOM_CHOICES = ["all", "bathroom", "bedroom", "kitchen"]
RANGE = {
    "start_date": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
    "end_date": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
}


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": True,
        "eager_input_streaming": True,
    }


# Sorted, frozen: any change here invalidates the whole prompt cache.
TOOLS: list[dict[str, Any]] = [
    _tool(
        "activity_counts",
        "Motion events from the activity log, which runs from the day Haiven was installed to now. Group by "
        "day, week or month for counts, or by hour or weekday for the average per day across "
        "the range. Returns rows, a total and a series_id for a chart.",
        {
            **RANGE,
            "room": {"type": "string", "enum": ROOM_CHOICES},
            "group": {"type": "string", "enum": ["day", "hour", "month", "week", "weekday"]},
        },
        ["start_date", "end_date", "room", "group"],
    ),
    _tool(
        "daily_history",
        "The per-day record, from the same calculations as the dashboard: routine verdict and "
        "reason, when they got up, bedtime that evening, night bathroom visits and downstairs "
        "trips for the night that ended that morning, movement and kitchen events, minutes "
        "away. Group by week or month for averages, which leave out days they were away. Returns "
        "rows and a series_ids map for charts.",
        {**RANGE, "group": {"type": "string", "enum": ["day", "month", "week"]}},
        ["start_date", "end_date", "group"],
    ),
    _tool(
        "day_events",
        "Every motion event on one date, as 'HH:MM room'. Use it to look closely at one day.",
        {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "room": {"type": "string", "enum": ROOM_CHOICES},
        },
        ["date", "room"],
    ),
    _tool(
        "find_entities",
        "Find sensors and helpers by words in their name, id or room. Every word must match. "
        "Returns up to 20 with entity_id, name, room, state and unit.",
        {
            "query": {"type": "string"},
            "domain": {"type": "string", "enum": ["any", *sorted(READABLE_DOMAINS)]},
        },
        ["query", "domain"],
    ),
    _tool(
        "get_state",
        "Current state and attributes of one entity.",
        {"entity_id": {"type": "string"}},
        ["entity_id"],
    ),
]


def validate_input(schema: dict[str, Any], value: Any) -> None:
    """Minimal check of a tool input against its (flat) schema.

    Eager input streaming disables the API's own validation, so every parsed
    input is checked here before anything runs.
    """
    if not isinstance(value, dict):
        raise PolicyError("invalid_input")
    props = schema["properties"]
    for key in value:
        if key not in props:
            raise PolicyError("invalid_input", f"unexpected {key}")
    for key in schema.get("required", []):
        if key not in value:
            raise PolicyError("invalid_input", f"missing {key}")
    for key, item in value.items():
        spec = props[key]
        if spec["type"] == "string" and not isinstance(item, str):
            raise PolicyError("invalid_input", key)
        if "enum" in spec and item not in spec["enum"]:
            raise PolicyError("invalid_input", key)


class Toolbox:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.series = SeriesStore(ttl=SERIES_TTL_S)
        self._schemas = {t["name"]: t["input_schema"] for t in TOOLS}
        self._events: tuple[tuple[int, int], list[activity.Event]] | None = None
        self._days: tuple[float, list[dict[str, Any]]] | None = None

    async def run(self, name: str, tool_input: Any, user_id: str) -> dict[str, Any]:
        """Run one model-requested tool. Raises PolicyError on any refusal."""
        schema = self._schemas.get(name)
        if schema is None:
            raise PolicyError("unknown_tool")
        validate_input(schema, tool_input)
        if name == "get_state":
            return self._get_state(tool_input["entity_id"])
        if name == "find_entities":
            return self._find_entities(**tool_input)
        if name == "activity_counts":
            return await self._activity_counts(user_id, **tool_input)
        if name == "day_events":
            return await self.hass.async_add_executor_job(
                activity.day_events, await self._load_events(), tool_input["date"], tool_input["room"]
            )
        return await self._daily_history(user_id, **tool_input)

    # -- entities --------------------------------------------------------

    def _get_state(self, entity_id: str) -> dict[str, Any]:
        check_readable(entity_id)
        state = self.hass.states.get(entity_id)
        if state is None:
            raise PolicyError("entity_not_found", entity_id)
        return {
            "entity_id": entity_id,
            "state": state.state,
            "attributes": clean_attributes(dict(state.attributes)),
            "last_changed": state.last_changed.isoformat(),
        }

    def _find_entities(self, query: str, domain: str) -> dict[str, Any]:
        words = [w for w in re.split(r"\W+", query.lower()) if w][:6]
        if not words:
            raise PolicyError("invalid_input", "query")
        ent_reg, dev_reg, area_reg = er.async_get(self.hass), dr.async_get(self.hass), ar.async_get(self.hass)

        def room(entity_id: str) -> str:
            entry = ent_reg.async_get(entity_id)
            area_id = entry.area_id if entry else None
            if not area_id and entry and entry.device_id and (dev := dev_reg.async_get(entry.device_id)):
                area_id = dev.area_id
            area = area_reg.async_get_area(area_id) if area_id else None
            return area.name if area else ""

        hits = []
        for state in self.hass.states.async_all():
            if is_denied(state.entity_id) or (domain != "any" and domain_of(state.entity_id) != domain):
                continue
            where = room(state.entity_id)
            name = str(state.attributes.get("friendly_name", ""))
            hay = f"{state.entity_id} {name} {where}".lower()
            if all(w in hay for w in words):
                hits.append((state.state in ("unavailable", "unknown"), state.entity_id, name, where, state))
        hits.sort(key=lambda h: (h[0], h[1]))
        return {
            "count": len(hits),
            "entities": [
                {
                    "entity_id": eid,
                    "name": name,
                    "room": where,
                    "state": st.state,
                    "unit": st.attributes.get("unit_of_measurement", ""),
                }
                for _u, eid, name, where, st in hits[:20]
            ],
            **({"note": "More than 20 matched; narrow the query."} if len(hits) > 20 else {}),
        }

    # -- the log ---------------------------------------------------------

    def _read_events(self) -> tuple[tuple[int, int], list[activity.Event]]:
        path = self.hass.config.path(ACTIVITY_LOG)
        stat = os.stat(path)
        key = (stat.st_mtime_ns, stat.st_size)
        if self._events and self._events[0] == key:
            return self._events
        with open(path, errors="replace", encoding="utf-8") as handle:
            return key, activity.parse_log(handle)

    async def _load_events(self) -> list[activity.Event]:
        try:
            self._events = await self.hass.async_add_executor_job(self._read_events)
        except OSError:
            raise PolicyError("activity_log_unavailable") from None
        return self._events[1]

    async def _activity_counts(
        self, user_id: str, start_date: str, end_date: str, room: str, group: str
    ) -> dict[str, Any]:
        result = await self.hass.async_add_executor_job(
            activity.activity_counts, await self._load_events(), start_date, end_date, room, group
        )
        value = "per_day" if group in ("hour", "weekday") else "count"
        result["series_id"] = self.series.put(
            user_id,
            {
                "name": f"{room.capitalize()} events by {group}",
                "unit": "events a day" if value == "per_day" else "events",
                "period": group,
                "points": [{"start": r["key"], "value": r[value]} for r in result["rows"]],
            },
        )
        return result

    async def _load_days(self) -> list[dict[str, Any]]:
        """Runs the script the way the dashboard's command_line sensors do, so
        its 2.5 s of parsing stays out of Home Assistant's event loop."""
        if self._days and time.monotonic() - self._days[0] < DAYS_TTL_S:
            return self._days[1]
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            self.hass.config.path(DAYS_SCRIPT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            async with asyncio.timeout(60):
                out, _ = await proc.communicate()
        except TimeoutError:
            proc.kill()
            raise PolicyError("stats_timeout") from None
        if proc.returncode != 0:
            raise PolicyError("stats_failed")
        days = json.loads(out)["days"]
        self._days = (time.monotonic(), days)
        return days

    async def _daily_history(self, user_id: str, start_date: str, end_date: str, group: str) -> dict[str, Any]:
        result = activity.daily_history(await self._load_days(), start_date, end_date, group)
        raw = result.pop("raw")
        result["series_ids"] = {
            metric: self.series.put(user_id, activity.metric_series(raw, metric, group))
            for metric in activity.METRICS
        }
        return result
