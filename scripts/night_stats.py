#!/usr/bin/env python3
"""Night statistics from activity.log, for the command_line sensor
sensor.night_stats (packages/haiven_night_insights.yaml).

Each night is rebuilt from the raw sensor events rather than counted live,
so the numbers are the same whether the night is being read at 07:00 or
fourteen days later, and the baseline is built from exactly the rule that
produces tonight's count.

Rules (all from the log, all local time):
  window   16:00 -> 12:00 next day
  bedtime  first bathroom-on after 16:00 with no kitchen motion in the next
           120 min and bedroom presence within 60 min. Coffee-and-reading
           trips to the bedroom in the evening fail the kitchen test. When
           no bathroom visit qualifies (dogs on the Ring all evening), the
           kitchen motion that opens the longest kitchen silence of the
           night stands in for it, if that silence is at least 120 min.
  skipped  a night with no bathroom or no bedroom events at all is a night
           the sensor was down, not a night with nothing in it.
  wake     first kitchen motion after 03:00 that has at least three kitchen
           events within 30 min. A lone dog trigger at 03:30 does not count.
  visits   bathroom on-events between bedtime and wake, grouped with a 15 min
           gap (the PIR fires several times per visit), minus the settling
           visit (<= 30 min after bedtime) and the rising visit (<= 30 min
           before wake).
  trips    kitchen motion between bedtime+30 and wake-30, grouped with a
           15 min gap. Downstairs trips in the night.

Only "Kitchen Motion (on)" lines are kitchen events. A template reload
writes "Kitchen Motion (off)" with nothing moving.
"""
import bisect
import datetime as dt
import json
import re
import statistics
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "/config/activity.log"
LINE = re.compile(
    r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \w+ "
    r"(Kitchen Motion|Bedroom Presence|Bathroom Motion)(?: \((on|off)\))?"
)   # lines before Nov 2025 carry no state; each one was an "on"
MIN = dt.timedelta(minutes=1)


def load():
    k, b, t_on, t_off = [], [], [], []
    with open(LOG, errors="replace") as fh:
        for line in fh:
            m = LINE.match(line)
            if not m:
                continue
            t = dt.datetime.fromisoformat(m.group(1))
            what, state = m.group(2), m.group(3) or "on"
            if what == "Kitchen Motion" and state == "on":
                k.append(t)
            elif what == "Bedroom Presence" and state == "on":
                b.append(t)
            elif what == "Bathroom Motion":
                (t_on if state == "on" else t_off).append(t)
    for lst in (k, b, t_on, t_off):
        lst.sort()
    return k, b, t_on, t_off


def between(lst, a, b):
    return lst[bisect.bisect_left(lst, a):bisect.bisect_left(lst, b)]


def cluster(times, gap_min):
    """Group sorted times whose gaps are <= gap_min. Returns [(first, last, n)]."""
    out = []
    for t in times:
        if out and (t - out[-1][1]) <= gap_min * MIN:
            out[-1][1] = t
            out[-1][2] += 1
        else:
            out.append([t, t, 1])
    return [tuple(x) for x in out]


def bedtime(K, B, T_ON, day, now):
    """(time, rule) or (None, None)."""
    w0 = dt.datetime.combine(day, dt.time(16))
    w1 = dt.datetime.combine(day + dt.timedelta(1), dt.time(0))
    for t in between(T_ON, w0, w1):
        if t + 120 * MIN > now:
            return None, None                  # too soon to know
        if between(K, t, t + 120 * MIN):
            continue
        if between(B, t, t + 60 * MIN):
            return t, "bathroom"
    w1 = dt.datetime.combine(day + dt.timedelta(1), dt.time(3))
    best, best_gap = None, dt.timedelta(0)
    for t in between(K, w0, w1):
        i = bisect.bisect_right(K, t)
        gap = (K[i] if i < len(K) else now) - t
        if gap > best_gap:
            best, best_gap = t, gap
    if best is not None and best_gap >= 120 * MIN:
        return best, "kitchen"
    return None, None


def wake(K, day, now):
    w0 = dt.datetime.combine(day + dt.timedelta(1), dt.time(3))
    w1 = dt.datetime.combine(day + dt.timedelta(1), dt.time(12))
    ks = between(K, w0, min(w1, now))
    for i, t in enumerate(ks):
        if len([x for x in ks[i:] if x <= t + 30 * MIN]) >= 3:
            return t
    return None


def night(K, B, T_ON, T_OFF, day, now):
    w0 = dt.datetime.combine(day, dt.time(16))
    w1 = min(now, dt.datetime.combine(day + dt.timedelta(1), dt.time(12)))
    if not between(T_ON, w0, w1) or not between(B, w0, w1):
        return None                            # a sensor was down
    bed, rule = bedtime(K, B, T_ON, day, now)
    if bed is None:
        return None
    wk = wake(K, day, now)
    end = wk if wk else min(now, dt.datetime.combine(day + dt.timedelta(1), dt.time(12)))
    visits = []
    for s, e, n in cluster(between(T_ON, bed, end), 15):
        if (s - bed) <= 30 * MIN:
            continue                           # settling
        if wk and (wk - s) <= 30 * MIN:
            continue                           # getting up
        k = bisect.bisect_left(T_OFF, e)
        off = T_OFF[k] if k < len(T_OFF) else e
        visits.append((s, round((off - s).total_seconds() / 60, 1)))
    trip_end = (wk - 30 * MIN) if wk else end
    trips = cluster(between(K, bed + 30 * MIN, trip_end), 15)
    return {
        "date": day.isoformat(),
        "bed": bed.strftime("%H:%M"),
        "bed_rule": rule,
        "wake": wk.strftime("%H:%M") if wk else None,
        "complete": wk is not None,
        "visits": len(visits),
        "visit_times": [s.strftime("%H:%M") for s, _ in visits],
        "visit_mins": [d for _, d in visits],
        "trips": len(trips),
        "trip_times": [s.strftime("%H:%M") for s, _, _ in trips],
    }


def main():
    K, B, T_ON, T_OFF = load()
    now = dt.datetime.now().replace(microsecond=0)
    last_event = max(x[-1] for x in (K, B, T_ON, T_OFF) if x) if any((K, B, T_ON, T_OFF)) else None

    # Tonight (or last night until noon) is the "current" night.
    cur_day = now.date() if now.hour >= 16 else now.date() - dt.timedelta(1)
    current = night(K, B, T_ON, T_OFF, cur_day, now)

    # Walk back until 17 completed nights are in hand: 14 for the baseline,
    # plus the 3 most recent compared against it. Stop after 60 days.
    completed = []
    day = cur_day
    for _ in range(60):
        n = night(K, B, T_ON, T_OFF, day, now)
        if n and n["complete"]:
            completed.append(n)
            if len(completed) >= 17:
                break
        day -= dt.timedelta(1)
    completed.reverse()                        # oldest first

    last14 = completed[-14:]
    avg14 = round(statistics.mean(n["visits"] for n in last14), 1) if last14 else None
    trips14 = round(statistics.mean(n["trips"] for n in last14), 1) if last14 else None

    # Sustained rise: the last three completed nights against the fourteen
    # before them. Fired 4 times in 203 recorded nights (Nov 2025 - Aug 2026).
    last3 = completed[-3:]
    base = completed[-17:-3]
    rising = False
    rise_base = None
    if len(last3) == 3 and len(base) >= 7:
        rise_base = round(statistics.mean(n["visits"] for n in base), 1)
        m3 = statistics.mean(n["visits"] for n in last3)
        rising = m3 >= rise_base + 1.5 and m3 >= 3

    last = completed[-1] if completed else None
    tonight = current if current and not current["complete"] else None
    shown = tonight or last

    state = "{}n {}avg {}v {}t {} @{}".format(
        len(last14), avg14, shown["visits"] if shown else "-",
        shown["trips"] if shown else "-", "rising" if rising else "steady",
        last_event.strftime("%d %H:%M:%S") if last_event else "-",
    )
    print(json.dumps({
        "state": state,
        "avg14": avg14,
        "n14": len(last14),
        "trips_avg14": trips14,
        "rising": rising,
        "rise_base": rise_base,
        "last3": [n["visits"] for n in last3],
        "last": last,
        "tonight": tonight,
        "nights": last14,
        "generated": now.isoformat(),
    }))


if __name__ == "__main__":
    main()
