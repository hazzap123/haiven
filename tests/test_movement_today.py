"""Tests for scripts/movement_today.py: today's cumulative kitchen +
bedroom + bathroom count against a plain 7-day average by the same clock
time.

Run with: pytest tests/test_movement_today.py -v
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import movement_today as mt  # noqa: E402


def times(day, *hhmm):
    d = dt.date.fromisoformat(day)
    return [dt.datetime.combine(d, dt.time.fromisoformat(t)) for t in hhmm]


def test_combined_events_merges_and_sorts_all_three_rooms():
    k = times("2026-09-10", "08:00", "12:00")
    b = times("2026-09-10", "07:00")
    t_on = times("2026-09-10", "09:00")
    ev = mt.combined_events(k, b, t_on)
    assert [e.time().isoformat() for e in ev] == ["07:00:00", "08:00:00", "09:00:00", "12:00:00"]


def test_today_count_only_counts_up_to_now():
    ev = times("2026-09-17", "05:00", "09:00", "14:00", "18:00")
    now = dt.datetime(2026, 9, 17, 10, 0)
    assert mt.today_count(ev, now) == 2


def test_usual_by_now_averages_the_prior_7_days_up_to_same_clock_time():
    now = dt.datetime(2026, 9, 17, 10, 0)
    ev = []
    for i in range(1, 8):
        day = (now.date() - dt.timedelta(i)).isoformat()
        ev += times(day, "08:00", "09:30")     # 2 events before 10:00 every day
        ev += times(day, "15:00")               # after the cutoff, must not count
    assert mt.usual_by_now(sorted(ev), now) == 2.0


def test_usual_by_now_none_without_a_full_baseline_window():
    now = dt.datetime(2026, 9, 17, 10, 0)
    ev = times("2026-09-15", "08:00")     # only 2 days of history
    assert mt.usual_by_now(ev, now) is None


def test_usual_by_now_none_with_no_events():
    assert mt.usual_by_now([], dt.datetime(2026, 9, 17, 10, 0)) is None


def test_series_by_now_has_one_point_per_baseline_day_oldest_first():
    now = dt.datetime(2026, 9, 17, 10, 0)
    ev = sorted(t for i in range(1, 8) for t in times((now.date() - dt.timedelta(i)).isoformat(), "08:00"))
    series = mt.series_by_now(ev, now)
    assert [d for d, _ in series] == [(now.date() - dt.timedelta(i)).isoformat() for i in range(7, 0, -1)]
    assert [v for _, v in series] == [1] * 7


def test_series_by_now_empty_without_a_full_baseline_window():
    ev = times("2026-09-15", "08:00")
    assert mt.series_by_now(ev, dt.datetime(2026, 9, 17, 10, 0)) == []


def test_usual_by_now_uses_same_clock_cutoff_each_day():
    now = dt.datetime(2026, 9, 17, 6, 0)     # early cutoff
    ev = []
    for i in range(1, 8):
        day = (now.date() - dt.timedelta(i)).isoformat()
        ev += times(day, "05:30")       # before 06:00 cutoff
        ev += times(day, "12:00")       # after cutoff, excluded
    assert mt.usual_by_now(sorted(ev), now) == 1.0
