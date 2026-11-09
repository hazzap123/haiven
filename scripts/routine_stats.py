#!/usr/bin/env python3
"""Daily routine verdict from activity.log, for the command_line sensor
sensor.routine_stats (packages/haiven_routine.yaml).

Answers "was today like her usual days?" with one of three words and the
reason, for the Home "Routine" row and the Patterns 30-day strip. It
describes days; it never alerts. Slow change is Drift Watch's job
(scripts/drift_stats.py) and nothing here duplicates its accumulator.

Signals, each judged against her own trailing BASE_N days
  up        first stirring (drift_stats.stir: first kitchen motion after
            04:00 with a second within 10 min). Either direction.
            Somewhat off from UP_SLIGHT_MIN minutes, well off from
            UP_WELL_MIN, or 2 / 3 of her spread if that is wider.
  movement  kitchen + bedroom + bathroom events, midnight to 20:00, the
            same events the Movement row counts. Less only: a busy day is
            not off routine. Spread floored at MOVE_SD_FLOOR_FRAC of usual.
            While the day is running it is compared by the same clock time,
            and only from MOVE_FROM_H, when there is enough day to judge.
  bathroom  night_stats visits for the night that ended this morning.
            More only. Poisson spread, floored at 1 visit.

Bedtime is left out: night_stats' bedtime reads 3-5 h late on about one
evening in eight on replayed real data, which would call a normal
day off track. Drift Watch leaves it out for the same reason.

Grades: z under SLIGHT is as usual, SLIGHT to WELL is "somewhat off",
WELL or more is "well off". Verdict:
  on_track      nothing off
  a_little_off  one signal somewhat off
  off_track     one signal well off, or two or more somewhat off
  away          out 4 h or more between 05:00 and 20:00; not judged
  no_data       no kitchen events that day, or too little history

Baselines are rolling rather than frozen: this compares a day with the
weeks around it, which is what "her usual" means on the Home screen.
Drift Watch keeps the frozen baseline because rolling ones hide drift.
"""
import argparse
import datetime as dt
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drift_stats  # noqa: E402
import night_stats  # noqa: E402

LOG_FILE = "/config/activity.log"
BASE_N = 28               # trailing valid days that make "usual"
BASE_MIN = 14             # fewer than this and the signal is not judged
STRIP_N = 30              # completed days the strip shows
SLIGHT, WELL = 2.0, 3.0   # z thresholds
UP_SLIGHT_MIN, UP_WELL_MIN = 60, 120
MOVE_SD_FLOOR_FRAC = 0.2
MOVE_END_H = 20           # movement day runs midnight to 20:00
MOVE_FROM_H = 10          # judge today's movement from 10:00
AWAY_H0, AWAY_H1, AWAY_MAX = 5, 20, 240

VERDICT_WORD = {"on_track": "On track", "a_little_off": "A little off",
                "off_track": "Off track", "away": "Away", "no_data": "Can't tell"}


# ---------------------------------------------------------------- helpers

def _hhmm(m):
    return drift_stats.min_to_hhmm(m)


def _robust(vals, floor):
    mu = statistics.median(vals)
    mad = statistics.median(abs(v - mu) for v in vals) * 1.4826
    return mu, max(mad, floor)


def _grade(z):
    if z is None or z < SLIGHT:
        return "ok"
    return "slight" if z < WELL else "well"


def _about(mins):
    """'about an hour' / 'about 40 min' for a clock difference."""
    mins = abs(int(round(mins)))
    if mins < 50:
        return "about %d min" % (5 * round(mins / 5))
    h = round(mins / 60 * 2) / 2
    if h == 1:
        return "about an hour"
    return "about %s hours" % (("%g" % h).replace(".5", "½"))


def movement_events(K, B, T_ON):
    return sorted(K + B + T_ON)


def count_between(events, day, h0, cut):
    return len(night_stats.between(events, dt.datetime.combine(day, h0), dt.datetime.combine(day, cut)))


# ---------------------------------------------------------------- per-day raw values

def raw_day(day, K, EV, nights_by_date, away, now):
    """Unjudged values for one calendar day. None where not knowable."""
    complete = now.date() > day
    a = dt.datetime.combine(day, dt.time(AWAY_H0))
    b = min(dt.datetime.combine(day, dt.time(AWAY_H1)), now)
    away_min = drift_stats._away_minutes(away, a, b) if b > a else 0.0
    last_night = nights_by_date.get((day - dt.timedelta(1)).isoformat())
    up = drift_stats.stir(K, day - dt.timedelta(1))
    if up is not None and not complete and dt.datetime.combine(day, dt.time()) + dt.timedelta(minutes=up) > now:
        up = None
    return {
        "date": day.isoformat(),
        "complete": complete,
        "away_min": int(round(away_min)),
        "kitchen": len(night_stats.between(K, dt.datetime.combine(day, dt.time(0)),
                                           dt.datetime.combine(day, dt.time(MOVE_END_H)))),
        "up": up,
        "movement": count_between(EV, day, dt.time(0), dt.time(MOVE_END_H)),
        "bathroom": last_night["visits"] if last_night else None,
    }


def usable(r):
    return r["complete"] and r["away_min"] < AWAY_MAX and r["kitchen"] > 0


# ---------------------------------------------------------------- judgement

def judge(r, base, EV, now):
    """Verdict for day r against base (earlier usable raw days, oldest first)."""
    out = {"date": r["date"], "complete": r["complete"], "signals": {}, "reasons": []}
    if r["away_min"] >= AWAY_MAX:
        out.update(verdict="away", reasons=["Out for most of the day, routine not judged"])
        return out
    if r["complete"] and r["kitchen"] == 0:
        out.update(verdict="no_data", reasons=["No kitchen activity recorded, sensor may have been down"])
        return out

    sig = out["signals"]
    day = dt.date.fromisoformat(r["date"])

    ups = [b["up"] for b in base if b["up"] is not None]
    if r["up"] is not None and len(ups) >= BASE_MIN:
        mu, sd = _robust(ups, 1.0)
        diff = r["up"] - mu
        g = ("well" if abs(diff) >= max(WELL * sd, UP_WELL_MIN)
             else "slight" if abs(diff) >= max(SLIGHT * sd, UP_SLIGHT_MIN) else "ok")
        sig["up"] = {"value": _hhmm(r["up"]), "usual": _hhmm(mu), "grade": g,
                     "reason": "Up at %s, %s %s than usual" % (_hhmm(r["up"]), _about(diff),
                                                                "later" if diff > 0 else "earlier")}

    if r["complete"]:
        vals = [b["movement"] for b in base]
        value, when = r["movement"], None
    elif now.hour >= MOVE_FROM_H:
        cut = min(now.time(), dt.time(MOVE_END_H))
        vals = [count_between(EV, dt.date.fromisoformat(b["date"]), dt.time(0), cut) for b in base]
        value, when = count_between(EV, day, dt.time(0), cut), " by now"
    else:
        vals, value, when = [], None, None
    if value is not None and len(vals) >= BASE_MIN:
        mu, _ = _robust(vals, 0)
        sd = max(_robust(vals, 0)[1], MOVE_SD_FLOOR_FRAC * mu, 1.0)
        g = _grade((mu - value) / sd)
        sig["movement"] = {"value": value, "usual": int(round(mu)), "grade": g,
                           "reason": ("Moving much less than usual" if g == "well" else "Moving less than usual")
                           + (when or "")}

    baths = [b["bathroom"] for b in base if b["bathroom"] is not None]
    if r["bathroom"] is not None and len(baths) >= BASE_MIN:
        lam = statistics.mean(baths)
        sd = max(math.sqrt(lam), 1.0)
        v = r["bathroom"]
        sig["bathroom"] = {"value": v, "usual": round(lam, 1), "grade": _grade((v - lam) / sd),
                           "reason": "%d bathroom visit%s overnight (usually %d)"
                                     % (v, "" if v == 1 else "s", int(round(lam)))}

    if not sig:
        # Overnight, before she stirs, there is nothing to judge yet; that is
        # not the same as being short of history.
        waiting = not r["complete"] and r["up"] is None and len(ups) >= BASE_MIN
        out.update(verdict="no_data", reasons=["Not up yet, judged once she stirs" if waiting
                                               else "Not enough history yet to judge"])
        return out

    grades = [s["grade"] for s in sig.values()]
    off = [s["reason"] for s in sig.values() if s["grade"] != "ok"]
    if "well" in grades or grades.count("slight") >= 2:
        verdict = "off_track"
    elif "slight" in grades:
        verdict = "a_little_off"
    else:
        verdict = "on_track"
    if verdict == "on_track":
        if r["complete"]:
            off = ["Up and about as usual"]
        elif "up" in sig:
            off = ["So far: up at %s, as usual" % sig["up"]["value"]]
        else:
            off = ["So far, as usual"]
    out.update(verdict=verdict, reasons=off)
    return out


def reason_text(reasons):
    if not reasons:
        return ""
    if len(reasons) == 1:
        return reasons[0]
    rest = [r[0].lower() + r[1:] for r in reasons[1:]]
    return ", ".join([reasons[0]] + rest[:-1]) + ", and " + rest[-1]


# ---------------------------------------------------------------- build

def build(now, K, B, T_ON, T_OFF, away, strip_n=STRIP_N):
    EV = movement_events(K, B, T_ON)
    if not EV:
        return {"today": None, "days": [], "counts": {}}
    nights = {}
    first = EV[0].date()
    d = first
    while d <= now.date():
        n = night_stats.night(K, B, T_ON, T_OFF, d, now)
        if n and n["complete"]:
            nights[d.isoformat()] = n
        d += dt.timedelta(1)

    raws, d = [], first
    while d <= now.date():
        raws.append(raw_day(d, K, EV, nights, away, now))
        d += dt.timedelta(1)

    judged = []
    for i, r in enumerate(raws):
        if i < len(raws) - strip_n - 1:
            continue                     # only the strip and today are judged
        base = [b for b in raws[:i] if usable(b)][-BASE_N:]
        judged.append(judge(r, base, EV, now))

    today = judged[-1] if judged and judged[-1]["date"] == now.date().isoformat() else None
    days = [j for j in judged if j["complete"]][-strip_n:]
    counts = {v: sum(1 for j in days if j["verdict"] == v) for v in VERDICT_WORD}
    return {"today": today, "days": days, "counts": counts}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=LOG_FILE)
    ap.add_argument("--replay", action="store_true",
                    help="judge every day in the log and print band counts only")
    a = ap.parse_args(argv)

    now = dt.datetime.now().replace(microsecond=0)
    night_stats.LOG = a.log
    K, B, T_ON, T_OFF = night_stats.load()
    away = drift_stats.load_away(a.log)

    if a.replay:
        res = build(now, K, B, T_ON, T_OFF, away, strip_n=100000)
        judged = [d for d in res["days"] if d["verdict"] in ("on_track", "a_little_off", "off_track")]
        by_sig = {}
        for d in judged:
            for k, s in d["signals"].items():
                by_sig.setdefault(k, {"ok": 0, "slight": 0, "well": 0})[s["grade"]] += 1
        print(json.dumps({"counts": res["counts"], "judged": len(judged), "by_signal": by_sig,
                          "first": res["days"][0]["date"] if res["days"] else None}, indent=1))
        return

    res = build(now, K, B, T_ON, T_OFF, away)
    t = res["today"]
    for d in res["days"]:
        d["why"] = reason_text(d["reasons"])
    if t:
        t["why"] = reason_text(t["reasons"])
        t["word"] = VERDICT_WORD[t["verdict"]]
    print(json.dumps({
        "state": t["verdict"] if t else "no_data",
        "today": t,
        "days": res["days"],
        "counts": res["counts"],
        "generated": now.isoformat(),
    }))


if __name__ == "__main__":
    main()
