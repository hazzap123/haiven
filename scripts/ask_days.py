#!/usr/bin/env python3
"""One row per day from activity.log, for the Ask tools (haiven_chat).

Every figure comes from the same code the dashboard uses, so Ask and the
Patterns screen cannot disagree: routine_stats judges the day and night_stats
reads the nights. A day's row carries the night that ended that morning
(visits, trips) and the bedtime of that evening.

Read-only. Prints JSON and writes nothing, unlike drift_stats, whose ack
state file this deliberately does not touch.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import drift_stats  # noqa: E402
import night_stats  # noqa: E402
import routine_stats  # noqa: E402


def rows(now, K, B, T_ON, T_OFF, away):
    """Oldest first; the last row is today, partial, if the day has started."""
    EV = routine_stats.movement_events(K, B, T_ON)
    res = routine_stats.build(now, K, B, T_ON, T_OFF, away, strip_n=100000)
    judged = {d["date"]: d for d in res["days"]}
    if res["today"]:
        judged[res["today"]["date"]] = res["today"]
    nights = {n["date"]: n for n in drift_stats.all_nights(now, K, B, T_ON, T_OFF)}

    out = []
    for date in sorted(judged):
        j = judged[date]
        day = dt.date.fromisoformat(date)
        last_night = nights.get((day - dt.timedelta(1)).isoformat())
        evening = nights.get(date)
        raw = routine_stats.raw_day(day, K, EV, nights, away, now)
        out.append({
            "date": date,
            "complete": j["complete"],
            "verdict": j["verdict"],
            "why": routine_stats.reason_text(j["reasons"]),
            "up_min": raw["up"],
            "bed_min": _bed_min(evening),
            "bed_rule": evening.get("bed_rule") if evening else None,
            "visits": last_night["visits"] if last_night else None,
            "trips": last_night["trips"] if last_night else None,
            "movement": raw["movement"],
            "kitchen": raw["kitchen"],
            "away_min": raw["away_min"],
        })
    return out


def _bed_min(n):
    """Minutes after midnight on the evening, so 00:30 sorts after 23:30."""
    if not n or not n.get("bed"):
        return None
    h, m = map(int, n["bed"].split(":"))
    return h * 60 + m + (1440 if h < 12 else 0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=routine_stats.LOG_FILE)
    a = ap.parse_args(argv)
    now = dt.datetime.now().replace(microsecond=0)
    night_stats.LOG = a.log
    K, B, T_ON, T_OFF = night_stats.load()
    print(json.dumps({"generated": now.isoformat(),
                      "days": rows(now, K, B, T_ON, T_OFF, drift_stats.load_away(a.log))}))


if __name__ == "__main__":
    main()
