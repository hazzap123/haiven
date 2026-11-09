"""Tests for scripts/drift_stats.py: the CUSUM drift layer over night_stats nights.

Run with: pytest tests/test_drift_stats.py -v
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import drift_stats as ds  # noqa: E402


def nights(values, start="2026-01-01", wake="05:00"):
    """Build completed-night dicts, one per day from start."""
    d0 = dt.date.fromisoformat(start)
    out = []
    for i, v in enumerate(values):
        w = wake[i] if isinstance(wake, list) else wake
        out.append({"date": (d0 + dt.timedelta(i)).isoformat(), "visits": v, "wake": w,
                    "stir": ds.hhmm_to_min(w), "complete": True})
    return out


TODAY = dt.date(2026, 9, 14)


# ---------------------------------------------------------------- learning

def test_fewer_than_28_nights_is_learning():
    r = ds.compute_chart("visits", nights([2] * 10), {}, TODAY)
    assert r["state"] == "learning"
    assert r["days_learned"] == 10
    assert r["usual"] is None


def test_default_baseline_is_latest_28_nights_when_no_state():
    # 40 nights, no frozen_from: baseline = last 28, nothing to accumulate yet
    r = ds.compute_chart("visits", nights([2] * 40), {}, TODAY)
    assert r["state"] == "steady"
    assert r["base_from"] == "2026-01-13"      # 40 - 28 = 12 -> 13th day
    assert r["base_to"] == "2026-02-09"
    assert r["usual"] == 2.0
    assert r["S"] == 0


# ---------------------------------------------------------------- visits (Poisson)

def test_visits_steady_on_flat_series():
    r = ds.compute_chart("visits", nights([2, 3, 2, 2, 1, 3, 2] * 8), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "steady"
    assert r["n_base"] == 28
    assert abs(r["usual"] - 2.14) < 0.01


def test_visits_k_is_poisson_reference_value():
    r = ds.compute_chart("visits", nights([2] * 28), {"frozen_from": "2026-01-01"}, TODAY)
    lam0, lam1 = 2.0, 3.0
    import math
    assert abs(r["k"] - (lam1 - lam0) / math.log(lam1 / lam0)) < 1e-3


def test_visits_sustained_rise_trips_and_latches():
    vals = [2] * 28 + [4] * 20
    r = ds.compute_chart("visits", nights(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "changed"
    # k = 2.466, +1.534/night -> S > 5 on the 4th night
    assert r["trip_date"] == "2026-02-01"
    assert r["run"] == 4
    assert r["since"] == "2026-01-29"
    assert r["recent"] == 4.0
    assert r["notify"] is True


def test_single_bad_night_does_not_trip():
    vals = [2] * 28 + [2, 2, 6, 2, 2, 2]
    r = ds.compute_chart("visits", nights(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] in ("steady", "watching")
    assert r["trip_date"] is None


def test_watching_when_above_half_threshold():
    vals = [2] * 28 + [4, 4]                   # S = 2*1.534 = 3.07 > 2.5
    r = ds.compute_chart("visits", nights(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "watching"


def test_notified_trip_does_not_notify_again():
    vals = [2] * 28 + [4] * 20
    st = {"frozen_from": "2026-01-01", "notified": "2026-02-01"}
    r = ds.compute_chart("visits", nights(vals), st, TODAY)
    assert r["state"] == "changed"
    assert r["notify"] is False


def test_noted_ack_resumes_accumulation_after_ack_date():
    vals = [2] * 28 + [4] * 20
    st = {"frozen_from": "2026-01-01", "resume_from": "2026-02-05", "notified": "2026-02-01"}
    r = ds.compute_chart("visits", nights(vals), st, TODAY)
    # restarted from the night of 5 Feb; still shifted, so it trips again on 8 Feb
    assert r["state"] == "changed"
    assert r["trip_date"] == "2026-02-08"
    assert r["notify"] is True                 # a new trip date


def test_reset_refreezes_baseline_and_goes_learning():
    vals = [2] * 28 + [4] * 10
    st = {"frozen_from": "2026-02-05"}         # "Seen GP, reset usual" on 5 Feb
    r = ds.compute_chart("visits", nights(vals), st, TODAY)
    assert r["state"] == "learning"
    assert r["days_learned"] == 3              # nights of 5, 6, 7 Feb


def test_visits_does_not_trip_on_real_replay_shape():
    # Realistic: mean 2.3, occasional 4s and 0s, 120 nights
    import random
    random.seed(1)
    vals = [min(6, max(0, round(random.gauss(2.3, 0.9)))) for _ in range(120)]
    r = ds.compute_chart("visits", nights(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] != "changed"


# ---------------------------------------------------------------- wake (Gaussian, upper)

def test_wake_sigma_floor_15_minutes():
    r = ds.compute_chart("wake", nights([2] * 28, wake="05:00"), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["sd"] == 15.0
    assert r["usual"] == 300
    assert r["usual_text"] == "05:00"


def test_wake_thirty_minute_shift_trips_in_about_a_week():
    wakes = ["05:00"] * 28 + ["05:30"] * 14
    r = ds.compute_chart("wake", nights([2] * 42, wake=wakes), {"frozen_from": "2026-01-01"}, TODAY)
    # z = 2 per day, minus k 0.5 -> +1.5/day -> S > 5 on the 4th day
    assert r["state"] == "changed"
    assert r["trip_date"] == "2026-02-01"
    assert r["recent_text"] == "05:30"


def test_wake_earlier_does_not_trip():
    wakes = ["05:00"] * 28 + ["04:15"] * 14
    r = ds.compute_chart("wake", nights([2] * 42, wake=wakes), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "steady"


def test_wake_single_late_morning_does_not_trip():
    wakes = ["05:00"] * 28 + ["05:00", "06:30", "05:00", "05:00"]
    r = ds.compute_chart("wake", nights([2] * 32, wake=wakes), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] != "changed"


def test_wake_very_late_mornings_need_a_run_to_trip():
    two = ["05:00"] * 28 + ["06:30", "06:30"]      # 2.5 + 2.5 = 5.0, not past h
    r = ds.compute_chart("wake", nights([2] * 30, wake=two), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "watching"
    three = two + ["06:30"]
    r = ds.compute_chart("wake", nights([2] * 31, wake=three), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "changed"
    assert r["run"] == 3


def test_wake_nights_without_wake_are_skipped():
    ns = nights([2] * 30, wake="05:00")
    ns[29]["stir"] = None
    r = ds.compute_chart("wake", ns, {"frozen_from": "2026-01-01"}, TODAY)
    assert r["last_night"] == "2026-01-29"


# ---------------------------------------------------------------- level (EWMA) and output shape

def test_level_is_ewma_seeded_at_usual():
    vals = [2] * 28 + [4] * 5
    r = ds.compute_chart("visits", nights(vals), {"frozen_from": "2026-01-01"}, TODAY)
    lvl = 2.0
    for v in [4] * 5:
        lvl = 0.1 * v + 0.9 * lvl
    assert abs(r["level"] - round(lvl, 2)) < 0.01


def test_state_file_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    st = ds.load_state(p)
    assert st == {}
    ds.ack(p, "visits", "noted", dt.date(2026, 2, 5))
    ds.ack(p, "wake", "reset", dt.date(2026, 2, 6))
    ds.mark_notified(p, "visits", "2026-02-01")
    st = json.loads(p.read_text())
    assert st["visits"]["resume_from"] == "2026-02-05"
    assert st["visits"]["notified"] == "2026-02-01"
    assert st["wake"]["frozen_from"] == "2026-02-06"
    assert st["wake"].get("resume_from") is None


def test_reset_clears_resume_and_notified(tmp_path):
    p = tmp_path / "state.json"
    ds.ack(p, "visits", "noted", dt.date(2026, 2, 5))
    ds.mark_notified(p, "visits", "2026-02-01")
    ds.ack(p, "visits", "reset", dt.date(2026, 3, 1))
    st = json.loads(p.read_text())
    assert st["visits"] == {"frozen_from": "2026-03-01"}


def test_cli_state_flag_does_not_leak_into_night_stats_log(tmp_path, capsys):
    # night_stats reads sys.argv[1] as its log path at import time; our own
    # flags must not end up there.
    log = tmp_path / "log"
    log.write_text("2026-01-01 05:00:00 INFO Kitchen Motion (on) | 05:00:00 | Thursday\n")
    ds.main(["--state", str(tmp_path / "s.json"), "--log", str(log)])
    out = json.loads(capsys.readouterr().out)
    assert out["visits"]["state"] == "learning"
    assert out["nights"] == 0


def test_series_carries_last_28_nights_and_accumulator():
    vals = [2] * 28 + [4] * 6
    r = ds.compute_chart("visits", nights(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert len(r["series"]) == 28
    assert r["series"][-1] == ["2026-02-03", 4]
    assert r["series"][0] == ["2026-01-07", 2]
    assert [d for d, _ in r["S_series"]] == ["2026-01-29", "2026-01-30", "2026-01-31", "2026-02-01"]
    assert r["S_series"][-1][1] > 5                # the trip night is the last point


def test_series_present_while_learning():
    r = ds.compute_chart("wake", nights([2] * 10), {}, TODAY)
    assert len(r["series"]) == 10
    assert r["S_series"] == []


def test_stir_is_first_kitchen_motion_with_a_second_within_ten_minutes():
    day = dt.date(2026, 3, 24)
    t = lambda h, m: dt.datetime(2026, 3, 25, h, m)
    K = [t(3, 30), t(5, 3), t(5, 5), t(7, 10), t(7, 16), t(7, 36)]
    assert ds.stir(K, day) == 5 * 60 + 3           # 03:30 is a lone trigger; 05:03 has 05:05
    K = [t(4, 28), t(6, 29), t(6, 37), t(6, 41)]
    assert ds.stir(K, day) == 6 * 60 + 29          # 04:28 alone does not count
    assert ds.stir([t(5, 0)], day) is None


# ---------------------------------------------------------------- activity (Gaussian, lower)

def days(values, start="2026-01-01"):
    """Build completed-day dicts, one per day from start."""
    d0 = dt.date.fromisoformat(start)
    return [{"date": (d0 + dt.timedelta(i)).isoformat(), "activity": v, "away_min": 0, "complete": True}
            for i, v in enumerate(values)]


def test_activity_sigma_floor_is_a_fifth_of_usual():
    r = ds.compute_chart("activity", days([140] * 28), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["usual"] == 140
    assert r["sd"] == 28.0
    assert r["k"] == 0.5


def test_activity_sustained_fall_trips_in_a_few_days():
    vals = [140] * 28 + [90] * 10
    r = ds.compute_chart("activity", days(vals), {"frozen_from": "2026-01-01"}, TODAY)
    # z = 50/28 = 1.79 a day, minus k 0.5 -> +1.29/day -> S > 5 on the 4th day
    assert r["state"] == "changed"
    assert r["trip_date"] == "2026-02-01"
    assert r["run"] == 4
    assert r["recent"] == 90.0


def test_activity_rise_does_not_trip():
    vals = [140] * 28 + [220] * 14
    r = ds.compute_chart("activity", days(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] == "steady"
    assert r["S"] == 0


def test_activity_single_dead_day_only_watches():
    vals = [140] * 28 + [140, 10, 140, 140]      # z capped at 3 -> +2.5, then pulled back
    r = ds.compute_chart("activity", days(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] != "changed"


def test_activity_replay_shape_from_the_real_log_does_not_trip():
    import random
    random.seed(3)
    vals = [max(0, round(random.gauss(138, 26))) for _ in range(120)]
    r = ds.compute_chart("activity", days(vals), {"frozen_from": "2026-01-01"}, TODAY)
    assert r["state"] != "changed"


def test_load_away_pairs_left_with_the_next_arrival(tmp_path):
    log = tmp_path / "log"
    log.write_text(
        "2026-09-16 09:37:51 INFO Mary Smith Location (arrived home) | 09:37:51 | Wednesday\n"   # no open left: ignored
        "2026-09-16 13:29:28 INFO Mary Smith Location (left home) | 13:29:28 | Wednesday\n"
        "2026-09-16 13:31:07 INFO Mary Smith Location (arrived home) | 13:31:07 | Wednesday\n"
        "2026-09-16 13:31:47 INFO Mary Smith Location (left home) | 13:31:47 | Wednesday\n"
        "2026-09-16 13:40:00 INFO Mary Smith Location (left home) | 13:40:00 | Wednesday\n"      # repeat left: first stands
        "2026-09-16 15:23:49 INFO Mary Smith Location (arrived home) | 15:23:49 | Wednesday\n"
        "2026-09-16 18:00:00 INFO Mary Smith Location (left home) | 18:00:00 | Wednesday\n"      # still out
        "2026-09-16 18:05:00 INFO Kitchen Motion (on) | 18:05:00 | Wednesday\n"
    )
    away = ds.load_away(str(log))
    t = lambda h, m, s=0: dt.datetime(2026, 9, 16, h, m, s)
    assert away == [(t(13, 29, 28), t(13, 31, 7)), (t(13, 31, 47), t(15, 23, 49)), (t(18, 0), None)]


def test_day_activity_counts_the_window_and_marks_away_days_incomplete():
    d = dt.date(2026, 9, 15)
    t = lambda h, m: dt.datetime(2026, 9, 15, h, m)
    K = [t(4, 50), t(5, 10), t(9, 0), t(12, 30), t(19, 59), t(20, 0), t(21, 0)]
    r = ds.day_activity(K, [], d)
    assert r == {"date": "2026-09-15", "activity": 4, "away_min": 0, "complete": True}
    # 4 h 10 min out inside the window: the day does not count
    r = ds.day_activity(K, [(t(9, 30), t(13, 40))], d)
    assert r["away_min"] == 250
    assert r["complete"] is False
    # a shopping trip does
    r = ds.day_activity(K, [(t(9, 30), t(11, 0))], d)
    assert r["away_min"] == 90
    assert r["complete"] is True
    # an open interval (still out) runs to the end of the window
    r = ds.day_activity(K, [(t(14, 0), None)], d)
    assert r["away_min"] == 360
    assert r["complete"] is False
    # nothing logged at all is the sensor down, not a quiet day
    r = ds.day_activity([t(4, 0)], [], d)
    assert r["activity"] == 0
    assert r["complete"] is False


def test_today_and_usual_by_now_use_the_same_clock_time():
    K = []
    for day in (1, 2, 3):                                    # baseline days: 2 events by 09:00, 5 by 20:00
        K += [dt.datetime(2026, 9, day, h, 0) for h in (6, 8, 10, 14, 18)]
    K += [dt.datetime(2026, 9, 16, 6, 30), dt.datetime(2026, 9, 16, 8, 45)]   # today
    K.sort()
    base = ["2026-09-01", "2026-09-02", "2026-09-03"]
    now = dt.datetime(2026, 9, 16, 9, 0)
    assert ds.today_count(K, now) == 2
    assert ds.by_now(K, base, now) == 2.0
    assert ds.by_now(K, base, dt.datetime(2026, 9, 16, 4, 0)) == 0.0       # before the window
    assert ds.by_now(K, base, dt.datetime(2026, 9, 16, 23, 0)) == 5.0      # after it: the whole day
    assert ds.today_count(K, dt.datetime(2026, 9, 16, 4, 0)) == 0
    assert ds.by_now(K, [], now) is None


def test_all_days_stops_at_the_last_finished_day():
    K = [dt.datetime(2026, 9, d, 9, 0) for d in (13, 14, 15, 16)]
    out = ds.all_days(dt.datetime(2026, 9, 16, 12, 0), K, [])
    assert [d["date"] for d in out] == ["2026-09-13", "2026-09-14", "2026-09-15"]
    out = ds.all_days(dt.datetime(2026, 9, 16, 20, 30), K, [])
    assert out[-1]["date"] == "2026-09-16"


def test_cli_output_carries_the_activity_chart(tmp_path, capsys):
    log = tmp_path / "log"
    log.write_text("2026-01-01 05:00:00 INFO Kitchen Motion (on) | 05:00:00 | Thursday\n"
                   "2026-01-01 09:00:00 INFO Kitchen Motion (on) | 09:00:00 | Thursday\n")
    ds.main(["--state", str(tmp_path / "s.json"), "--log", str(log)])
    out = json.loads(capsys.readouterr().out)
    assert out["activity"]["state"] == "learning"
    assert out["activity"]["days_learned"] == 1
    assert out["activity"]["today"] == 0
    assert out["activity"]["usual_by_now"] is None
    assert out["state"].split()[2].startswith("a:")
