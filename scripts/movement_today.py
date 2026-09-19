#!/usr/bin/env python3
"""Today's movement across kitchen, bedroom and bathroom against the 7-day
average by the same clock time, for the Home card's "Movement, all rooms"
row (sensor.movement_stats, packages/haiven_movement.yaml).

Independent of scripts/drift_stats.py's kitchen-only CUSUM chart: no state,
no accumulator, no alerting, no frozen baseline. drift_stats.py keeps to
kitchen alone because a combined signal saturates for THAT purpose - see
"activity" in its docstring and docs/planning/DRIFT_WATCH.md. This script
only describes today against a plain rolling average, so that argument does
not apply here.
"""
import argparse
import datetime as dt
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import night_stats  # noqa: E402

LOG_FILE = "/config/activity.log"
BASE_N = 7      # trailing calendar days averaged for "usual by now"


def combined_events(k, b, t_on):
    """Kitchen, bedroom and bathroom "on" events, oldest first."""
    return sorted(k + b + t_on)


def today_count(events, now):
    a = dt.datetime.combine(now.date(), dt.time(0))
    return len(night_stats.between(events, a, now))


def series_by_now(events, now, base_n=BASE_N):
    """[(date_iso, count)] for the base_n calendar days immediately before
    today, each count from that day's midnight to now's clock time. Empty
    with no log history that far back yet. events must be sorted ascending
    (combined_events' contract) - events[0] is read as the earliest."""
    if not events:
        return []
    last = now.date() - dt.timedelta(1)
    first = last - dt.timedelta(base_n - 1)
    if events[0].date() > first:
        return []       # log doesn't go back far enough for a full baseline
    cut = now.time()
    return [(d.isoformat(), len(night_stats.between(events, dt.datetime.combine(d, dt.time(0)),
                                                      dt.datetime.combine(d, cut))))
            for d in (first + dt.timedelta(i) for i in range(base_n))]


def usual_by_now(events, now, base_n=BASE_N):
    """Mean of series_by_now's counts, or None with no full baseline yet."""
    series = series_by_now(events, now, base_n)
    if not series:
        return None
    return round(statistics.mean(v for _, v in series), 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=LOG_FILE)
    a = ap.parse_args(argv)

    now = dt.datetime.now().replace(microsecond=0)
    night_stats.LOG = a.log        # night_stats reads sys.argv[1] at import; ours differs
    k, b, t_on, _t_off = night_stats.load()
    events = combined_events(k, b, t_on)
    today = today_count(events, now)
    series = series_by_now(events, now)
    print(json.dumps({
        "today": today,
        "usual_by_now": usual_by_now(events, now),
        "series": series + [[now.date().isoformat(), today]],
        "generated": now.isoformat(),
    }))


if __name__ == "__main__":
    main()
