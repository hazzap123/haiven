#!/usr/bin/env python3
"""Slow-drift detection over the nights night_stats.py builds from
activity.log, for the command_line sensor sensor.drift_stats
(packages/haiven_drift.yaml).

Everything else in Haiven judges one day against a rolling average. A
rolling average absorbs a gradual change inside a week, so a routine that
slides over a month is never flagged. This runs a CUSUM per metric: each
completed night adds (value - usual - allowance) to an accumulator that
cannot go below zero, and the chart trips when the accumulator passes h.
One odd night barely moves it; a run of slightly-off nights climbs.

Charts
  visits  bathroom visits a night (night_stats "visits"). Poisson CUSUM,
          designed to notice a rise to 1.5x usual, h = 5. Across real
          nights (Nov 2025 - Sep 2026) this never tripped; the current
          "5+ in one night" flag fired on two single nights.
  wake    first stirring: the first kitchen motion after 04:00 with a
          second within 10 min, minutes after midnight. Not night_stats'
          "wake" (three events in 30 min), which reads 07:15 on a third of
          mornings because an early kitchen visit is often two events and
          then quiet until she comes down properly; that flips modes for a
          week at a time and looks like a change when nothing changed. On
          the same log first-stirring is 05:01 with a 9-minute spread.
          One-sided Gaussian CUSUM for LATER stirring, k = 0.5, h = 5,
          sigma floored at 15 min. Each morning's z is capped at 3, so one
          06:30 cannot trip it on its own; the acute morning check already
          covers a single very late start.
  activity
          kitchen motion events between 05:00 and 20:00, the count the
          "Kitchen activity" row is built on. Ring motion re-arms every few
          minutes while someone is in the room, so the count is closer to
          "minutes on her feet downstairs" than to trips. One-sided Gaussian
          CUSUM for LESS activity, k = 0.5, h = 5, sigma floored at 20% of
          usual, per-day z capped at 3. A day counts only if she was away
          under 4 h inside the window (the person's "Location" log lines) and
          the Ring logged at least one event. On the log (Nov 2025 - Sep 2026,
          234 complete days, usual 138, sd 26) this trips three times, each
          a week at 20-33% below usual. The Home card also carries today's
          count so far against the baseline days' count by the same clock
          time.

Baseline
  Frozen: the 28 completed nights from state[chart]["frozen_from"]. Not a
  rolling window, so a drift cannot hide inside its own baseline. With no
  state the latest 28 nights become the baseline, so the chart is live
  from the first run rather than learning for a month.

State (/config/haiven_drift_state.json, written only by --ack/--notified)
  frozen_from  baseline starts at the first completed night on/after this
  resume_from  "Noted, keep watching": accumulate again from this night
  notified     trip date already sent, so the 07:30 alert does not repeat

The accumulator itself is never stored: it is replayed from the log on
every run, so a reboot or a lost state file cannot leave it stale.
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import night_stats  # noqa: E402

STATE_FILE = "/config/haiven_drift_state.json"
LOG_FILE = "/config/activity.log"
BASE_N = 28
H = 5.0
WAKE_K = 0.5
WAKE_SD_FLOOR = 15.0
WAKE_Z_CAP = 3.0          # one morning can add at most 2.5; a trip needs a run
VISITS_RISE = 1.5
ACT_H0, ACT_H1 = 5, 20    # the activity day, local clock
ACT_AWAY_MAX = 240        # minutes away inside the window before the day is skipped
ACT_K = 0.5
ACT_SD_FLOOR_FRAC = 0.2
ACT_Z_CAP = 3.0
EWMA = 0.1
SERIES_N = 28             # nights the card draws
CHARTS = ("visits", "wake", "activity")
LOC_LINE = re.compile(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \w+ .+? Location \((left home|arrived home)\)")


# ---------------------------------------------------------------- helpers

def hhmm_to_min(s):
    if not s:
        return None
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def min_to_hhmm(m):
    if m is None:
        return None
    m = int(round(m))
    return "%02d:%02d" % (m // 60, m % 60)


def value_of(chart, n):
    if chart == "visits":
        return n.get("visits")
    if chart == "wake":
        return n.get("stir")
    return n.get("activity")


def stir(K, day, confirm_min=10):
    """First kitchen motion after 04:00 on the morning after `day` that has a
    second event within confirm_min, as minutes after midnight. The second
    event keeps a lone dog trigger from counting."""
    w0 = dt.datetime.combine(day + dt.timedelta(1), dt.time(4))
    w1 = dt.datetime.combine(day + dt.timedelta(1), dt.time(12))
    ks = night_stats.between(K, w0, w1)
    for i, t in enumerate(ks):
        if any(t < x <= t + confirm_min * night_stats.MIN for x in ks[i + 1:i + 4]):
            return t.hour * 60 + t.minute
    return None


def _baseline(chart, vals):
    """(usual, sd, k) for the chart from its 28 baseline values."""
    if chart == "visits":
        lam0 = max(statistics.mean(vals), 0.2)
        lam1 = VISITS_RISE * lam0
        k = (lam1 - lam0) / math.log(lam1 / lam0)
        return round(lam0, 2), round(math.sqrt(lam0), 2), round(k, 3)
    mu = statistics.median(vals)
    mad = statistics.median(abs(v - mu) for v in vals) * 1.4826
    if chart == "activity":
        return round(mu, 1), round(max(mad, ACT_SD_FLOOR_FRAC * mu), 1), ACT_K
    return round(mu, 1), round(max(mad, WAKE_SD_FLOOR), 1), WAKE_K


def _increment(chart, v, usual, sd, k):
    if chart == "visits":
        return v - k
    if chart == "activity":
        return min((usual - v) / sd, ACT_Z_CAP) - k     # less activity climbs
    return min((v - usual) / sd, WAKE_Z_CAP) - k


# ---------------------------------------------------------------- core

def compute_chart(chart, nights, state, today):
    """Replay one chart over completed nights (oldest first).

    nights: dicts with date, visits, wake, complete (night_stats.night()).
    state:  this chart's entry from the state file ({} when none).
    """
    pts = [(n["date"], value_of(chart, n)) for n in nights
           if n.get("complete") and value_of(chart, n) is not None]
    frozen_from = state.get("frozen_from")
    if frozen_from is None and len(pts) >= BASE_N:
        frozen_from = pts[-BASE_N][0]           # latest 28 nights, live at once
    base = [p for p in pts if frozen_from is None or p[0] >= frozen_from][:BASE_N]

    out = {
        "chart": chart, "h": H, "state": "learning", "days_learned": len(base),
        "series": [[d, v] for d, v in pts[-SERIES_N:]], "S_series": [],
        "usual": None, "sd": None, "k": None, "S": 0.0, "run": 0, "since": None,
        "recent": None, "trip_date": None, "notify": False,
        "n_base": len(base), "base_from": base[0][0] if base else None,
        "base_to": base[-1][0] if base else None,
        "last_night": pts[-1][0] if pts else None, "level": None,
        "resume_from": state.get("resume_from"), "notified": state.get("notified"),
    }
    if len(base) < BASE_N:
        return out

    usual, sd, k = _baseline(chart, [v for _, v in base])
    out.update(usual=usual, sd=sd, k=k)

    resume = state.get("resume_from")
    after = [p for p in pts if p[0] > base[-1][0] and (resume is None or p[0] >= resume)]

    S, run, trip, S_series = 0.0, 0, None, []
    for d, v in after:
        S = max(0.0, S + _increment(chart, v, usual, sd, k))
        run = run + 1 if S > 0 else 0
        S_series.append([d, round(S, 2)])
        if S > H:
            trip = d
            break
    counted = after[:len(after)] if trip is None else after[:[p[0] for p in after].index(trip) + 1]
    seg = counted[-run:] if run else []

    out["S"] = round(S, 2)
    out["S_series"] = S_series[-SERIES_N:]
    out["run"] = run
    out["since"] = seg[0][0] if seg else None
    out["recent"] = round(statistics.mean(v for _, v in seg), 2) if seg else None
    if trip:
        out["state"] = "changed"
        out["trip_date"] = trip
        out["notify"] = state.get("notified") != trip
    elif S > H / 2:
        out["state"] = "watching"
    else:
        out["state"] = "steady"

    # Displayed level: EWMA over everything after the baseline, seeded at usual.
    lvl = float(usual)
    for _, v in (p for p in pts if p[0] > base[-1][0]):
        lvl = EWMA * v + (1 - EWMA) * lvl
    out["level"] = round(lvl, 2)

    if chart == "wake":
        out["usual_text"] = min_to_hhmm(usual)
        out["recent_text"] = min_to_hhmm(out["recent"])
        out["level_text"] = min_to_hhmm(out["level"])
    return out


# ---------------------------------------------------------------- activity days

def load_away(log):
    """(left, arrived) intervals from the Location lines, oldest first. A
    repeat "left" keeps the first; an "arrived" with nothing open is ignored;
    an interval still open at the end of the log has arrived = None."""
    out, left = [], None
    with open(log, errors="replace") as fh:
        for line in fh:
            m = LOC_LINE.match(line)
            if not m:
                continue
            t = dt.datetime.fromisoformat(m.group(1))
            if m.group(2) == "left home":
                if left is None:
                    left = t
            elif left is not None:
                out.append((left, t))
                left = None
    if left is not None:
        out.append((left, None))
    return out


def _away_minutes(away, a, b):
    m = 0.0
    for x, y in away:
        lo, hi = max(x, a), min(y or b, b)
        if hi > lo:
            m += (hi - lo).total_seconds() / 60
    return m


def day_activity(K, away, day):
    """Kitchen events in the day's window, and whether the day counts."""
    a = dt.datetime.combine(day, dt.time(ACT_H0))
    b = dt.datetime.combine(day, dt.time(ACT_H1))
    n = len(night_stats.between(K, a, b))
    away_min = _away_minutes(away, a, b)
    return {"date": day.isoformat(), "activity": n, "away_min": int(round(away_min)),
            "complete": n > 0 and away_min < ACT_AWAY_MAX}


def all_days(now, K, away):
    """Every finished day in the log, oldest first. Today joins once the
    window has closed."""
    if not K:
        return []
    last = now.date() if now.hour >= ACT_H1 else now.date() - dt.timedelta(1)
    day, out = K[0].date(), []
    while day <= last:
        out.append(day_activity(K, away, day))
        day += dt.timedelta(1)
    return out


def _clock_cut(now):
    """now's clock time clamped to the window, so a 09:00 read compares
    today's 05:00-09:00 with the baseline days' 05:00-09:00."""
    return min(max(now.time(), dt.time(ACT_H0)), dt.time(ACT_H1))


def today_count(K, now):
    a = dt.datetime.combine(now.date(), dt.time(ACT_H0))
    return len(night_stats.between(K, a, dt.datetime.combine(now.date(), _clock_cut(now))))


def by_now(K, base_dates, now):
    """Mean over the baseline days of kitchen events up to now's clock time."""
    if not base_dates:
        return None
    cut = _clock_cut(now)
    vals = [len(night_stats.between(K, dt.datetime.combine(d, dt.time(ACT_H0)), dt.datetime.combine(d, cut)))
            for d in (dt.date.fromisoformat(x) for x in base_dates)]
    return round(statistics.mean(vals), 1)


# ---------------------------------------------------------------- state file

def load_state(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_state(path, st):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, path)


def ack(path, chart, kind, day):
    """noted: keep the baseline, accumulate again from tonight.
    reset:  refreeze the baseline from tonight (learning for 28 nights)."""
    st = load_state(path)
    if kind == "reset":
        st[chart] = {"frozen_from": day.isoformat()}
    else:
        st.setdefault(chart, {})["resume_from"] = day.isoformat()
    _save_state(path, st)


def mark_notified(path, chart, trip_date):
    st = load_state(path)
    st.setdefault(chart, {})["notified"] = trip_date
    _save_state(path, st)


# ---------------------------------------------------------------- main

def all_nights(now, K, B, T_ON, T_OFF):
    """Every completed night in the log, oldest first."""
    first = min(x[0] for x in (K, B, T_ON, T_OFF) if x).date()
    cur_day = now.date() if now.hour >= 16 else now.date() - dt.timedelta(1)
    out = []
    day = first
    while day <= cur_day:
        n = night_stats.night(K, B, T_ON, T_OFF, day, now)
        if n and n["complete"]:
            n["stir"] = stir(K, day)
            out.append(n)
        day += dt.timedelta(1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=STATE_FILE)
    ap.add_argument("--log", default=LOG_FILE)
    ap.add_argument("--ack", nargs=2, metavar=("CHART", "KIND"),
                    help="CHART in visits|wake|activity, KIND in noted|reset")
    ap.add_argument("--notified", nargs=2, metavar=("CHART", "TRIP_DATE"))
    a = ap.parse_args(argv)
    today = dt.date.today()
    if a.ack:
        ack(a.state, a.ack[0], a.ack[1], today)
        return
    if a.notified:
        mark_notified(a.state, a.notified[0], a.notified[1])
        return

    now = dt.datetime.now().replace(microsecond=0)
    night_stats.LOG = a.log        # night_stats reads sys.argv[1] at import; ours differ
    K, B, T_ON, T_OFF = night_stats.load()
    nights = all_nights(now, K, B, T_ON, T_OFF)
    days = all_days(now, K, load_away(a.log))
    st = load_state(a.state)
    charts = {c: compute_chart(c, days if c == "activity" else nights, st.get(c, {}), today)
              for c in CHARTS}
    act = charts["activity"]
    base_dates = [d["date"] for d in days
                  if d["complete"] and act["usual"] is not None and act["base_from"] <= d["date"] <= act["base_to"]]
    act["today"] = today_count(K, now)
    act["usual_by_now"] = by_now(K, base_dates, now)     # None while learning, like usual
    state = " ".join("%s:%s" % (c[0], r["state"]) for c, r in charts.items())
    print(json.dumps({
        "state": state,
        "visits": charts["visits"],
        "wake": charts["wake"],
        "activity": act,
        "nights": len(nights),
        "days": len(days),
        "generated": now.isoformat(),
    }))


if __name__ == "__main__":
    main()
