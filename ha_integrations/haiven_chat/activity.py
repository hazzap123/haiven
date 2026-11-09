"""Questions over activity.log and the per-day stats. Pure, no HA imports.

Every figure Ask quotes is computed here, so the model never does its own sums.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from .policy import PolicyError

# Same reading as scripts/night_stats.py: lines before Nov 2025 carry no state
# and each one was an "on".
LINE = re.compile(
    r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \w+ "
    r"(Kitchen Motion|Bedroom Presence|Bathroom Motion)(?: \((on|off)\))?"
)
ROOMS = {"Kitchen Motion": "kitchen", "Bedroom Presence": "bedroom", "Bathroom Motion": "bathroom"}
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# The dates are the model's, and a day-by-day walk from year 1 to 9999 would
# stall the worker. Three years is well past the log's length.
MAX_RANGE_DAYS = 1100

Event = tuple[datetime, str]


def parse_log(lines) -> list[Event]:
    out: list[Event] = []
    for line in lines:
        m = LINE.match(line)
        if m and (m.group(3) or "on") == "on":
            out.append((datetime.fromisoformat(m.group(1)), ROOMS[m.group(2)]))
    out.sort()
    return out


def parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise PolicyError("invalid_date", name) from None


def date_range(start: str, end: str) -> tuple[date, date]:
    a, b = parse_date(start, "start_date"), parse_date(end, "end_date")
    if a > b:
        raise PolicyError("invalid_date", "start_date is after end_date")
    if (b - a).days > MAX_RANGE_DAYS:
        raise PolicyError("invalid_date", f"range is over {MAX_RANGE_DAYS} days")
    return a, b


def _bucket(day: date, group: str) -> str:
    if group == "week":
        return (day - timedelta(days=day.weekday())).isoformat()
    if group == "month":
        return day.strftime("%Y-%m")
    return day.isoformat()


def _buckets(a: date, b: date, group: str) -> list[str]:
    seen: dict[str, None] = {}
    day = a
    while day <= b:
        seen[_bucket(day, group)] = None
        day += timedelta(days=1)
    return list(seen)


def activity_counts(events: list[Event], start: str, end: str, room: str, group: str) -> dict[str, Any]:
    """Motion events per day, week, month, hour of day or weekday.

    Zero rows are kept: a zero can mean she was away or a sensor was down, and
    dropping it would hide that from the reader.
    """
    a, b = date_range(start, end)
    picked = [t for t, r in events if a <= t.date() <= b and (room == "all" or r == room)]
    days = (b - a).days + 1
    if group == "hour":
        keys = [f"{h:02d}" for h in range(24)]
        tally = dict.fromkeys(keys, 0)
        for t in picked:
            tally[f"{t.hour:02d}"] += 1
        rows = [{"key": k, "per_day": round(tally[k] / days, 2)} for k in keys]
    elif group == "weekday":
        tally = dict.fromkeys(WEEKDAYS, 0)
        for t in picked:
            tally[WEEKDAYS[t.weekday()]] += 1
        seen = dict.fromkeys(WEEKDAYS, 0)
        for i in range(days):
            seen[WEEKDAYS[(a + timedelta(days=i)).weekday()]] += 1
        rows = [
            {"key": k, "per_day": round(tally[k] / seen[k], 2) if seen[k] else None} for k in WEEKDAYS
        ]
    else:
        tally = dict.fromkeys(_buckets(a, b, group), 0)
        for t in picked:
            tally[_bucket(t.date(), group)] += 1
        rows = [{"key": k, "count": v} for k, v in tally.items()]
    return {"start": a.isoformat(), "end": b.isoformat(), "room": room, "group": group, "total": len(picked), "rows": rows}


def day_events(events: list[Event], day: str, room: str, limit: int = 400) -> dict[str, Any]:
    d = parse_date(day, "date")
    picked = [(t, r) for t, r in events if t.date() == d and (room == "all" or r == room)]
    out: dict[str, Any] = {
        "date": d.isoformat(),
        "count": len(picked),
        "events": [f"{t:%H:%M} {r}" for t, r in picked[:limit]],
    }
    if len(picked) > limit:
        out["note"] = f"First {limit} shown; narrow by room."
    return out


NUMERIC = ("up_min", "bed_min", "visits", "trips", "movement", "kitchen", "away_min")
TIME_FIELDS = {"up_min": "up", "bed_min": "bed"}


def hhmm(minutes: float | None) -> str | None:
    if minutes is None:
        return None
    m = int(round(minutes)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def _show(row: dict[str, Any]) -> dict[str, Any]:
    """Minutes become clock times for the reader; absent values drop out."""
    out = {}
    for key, value in row.items():
        if key in TIME_FIELDS:
            out[TIME_FIELDS[key]] = hhmm(value)
        elif value is not None:
            out[key] = value
    return out


def daily_history(days: list[dict[str, Any]], start: str, end: str, group: str) -> dict[str, Any]:
    """Per-day stats in the range, or their averages by week or month.

    Days she was out for most of the day or with no kitchen data are left out
    of the averages, so a holiday does not read as a quiet week.
    """
    a, b = date_range(start, end)
    rows = [d for d in days if a.isoformat() <= d["date"] <= b.isoformat()]
    summary = {
        "start": a.isoformat(),
        "end": b.isoformat(),
        "group": group,
        "days_found": len(rows),
        "verdicts": {},
    }
    for d in rows:
        if d.get("verdict"):
            summary["verdicts"][d["verdict"]] = summary["verdicts"].get(d["verdict"], 0) + 1
    if group == "day":
        return {**summary, "raw": rows, "rows": [_show(d) for d in rows]}

    grouped: dict[str, list[dict[str, Any]]] = {}
    for d in rows:
        grouped.setdefault(_bucket(date.fromisoformat(d["date"]), group), []).append(d)
    averaged = []
    for key, members in grouped.items():
        used = [d for d in members if d.get("verdict") not in ("away", "no_data")]
        row: dict[str, Any] = {"date": key, "days": len(members), "days_averaged": len(used)}
        for field in NUMERIC:
            vals = [d[field] for d in used if d.get(field) is not None]
            row[field] = round(sum(vals) / len(vals), 1) if vals else None
        averaged.append(row)
    return {**summary, "raw": averaged, "rows": [_show(r) for r in averaged]}


METRICS = {
    "visits": ("Night bathroom visits", "visits"),
    "trips": ("Downstairs trips at night", "trips"),
    "movement": ("Movement events", "events"),
    "kitchen": ("Kitchen events", "events"),
    "up_min": ("Up at", "time"),
    "bed_min": ("Bedtime", "time"),
}


def metric_series(raw: list[dict[str, Any]], metric: str, period: str) -> dict[str, Any]:
    name, unit = METRICS[metric]
    return {
        "name": name,
        "unit": unit,
        "period": period,
        "points": [{"start": r["date"], "value": r.get(metric)} for r in raw],
    }
