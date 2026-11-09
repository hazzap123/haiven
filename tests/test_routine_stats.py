"""Tests for scripts/routine_stats.py: the daily On track / A little off /
Off track verdict behind the Home "Routine" row and the Patterns strip.

Run with: pytest tests/test_routine_stats.py -v
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import routine_stats as rs  # noqa: E402

DAY = dt.date(2026, 9, 20)
LATE = dt.datetime(2026, 9, 21, 9, 0)      # the day is complete


def raw(date, up=300, movement=200, bathroom=1, away=0, kitchen=100, complete=True):
    return {"date": date.isoformat(), "complete": complete, "away_min": away,
            "kitchen": kitchen, "up": up, "movement": movement, "bathroom": bathroom}


def base(n=28):
    """n usual days: up 05:00 give or take 10 min, movement 190-210, 1 visit."""
    return [raw(DAY - dt.timedelta(i + 1), up=300 + (i % 3 - 1) * 10,
                movement=200 + (i % 3 - 1) * 10, bathroom=1 + (i % 2))
            for i in range(n)]


def test_usual_day_is_on_track():
    j = rs.judge(raw(DAY), base(), [], LATE)
    assert j["verdict"] == "on_track"
    assert j["reasons"] == ["Up and about as usual"]


def test_an_hour_late_up_is_a_little_off_and_says_why():
    j = rs.judge(raw(DAY, up=370), base(), [], LATE)
    assert j["verdict"] == "a_little_off"
    assert j["reasons"] == ["Up at 06:10, about an hour later than usual"]


def test_two_hours_late_up_is_off_track():
    j = rs.judge(raw(DAY, up=425), base(), [], LATE)
    assert j["verdict"] == "off_track"


def test_forty_minutes_late_is_still_on_track():
    j = rs.judge(raw(DAY, up=340), base(), [], LATE)
    assert j["verdict"] == "on_track"


def test_much_less_movement_is_off_track():
    j = rs.judge(raw(DAY, movement=60), base(), [], LATE)
    assert j["verdict"] == "off_track"
    assert j["reasons"] == ["Moving much less than usual"]


def test_busier_day_is_not_off_routine():
    j = rs.judge(raw(DAY, movement=400), base(), [], LATE)
    assert j["verdict"] == "on_track"


def test_two_somewhat_off_signals_make_off_track():
    j = rs.judge(raw(DAY, up=370, movement=110), base(), [], LATE)
    assert j["signals"]["up"]["grade"] == "slight"
    assert j["signals"]["movement"]["grade"] == "slight"
    assert j["verdict"] == "off_track"
    assert len(j["reasons"]) == 2


def test_bathroom_visits_well_above_usual_are_named():
    j = rs.judge(raw(DAY, bathroom=6), base(), [], LATE)
    assert j["verdict"] == "off_track"
    assert j["reasons"] == ["6 bathroom visits overnight (usually 2)"]


def test_away_day_is_not_judged():
    j = rs.judge(raw(DAY, movement=10, away=300), base(), [], LATE)
    assert j["verdict"] == "away"


def test_no_kitchen_events_is_no_data_never_on_track():
    j = rs.judge(raw(DAY, kitchen=0), base(), [], LATE)
    assert j["verdict"] == "no_data"


def test_too_little_history_is_no_data():
    j = rs.judge(raw(DAY), base(5), [], LATE)
    assert j["verdict"] == "no_data"


def test_today_before_ten_judges_only_what_has_happened():
    now = dt.datetime.combine(DAY, dt.time(8, 0))
    j = rs.judge(raw(DAY, complete=False, movement=3), base(), [], now)
    assert "movement" not in j["signals"]
    assert j["verdict"] == "on_track"
    assert j["reasons"] == ["So far: up at 05:00, as usual"]


def test_today_after_ten_compares_movement_by_the_same_clock_time():
    now = dt.datetime.combine(DAY, dt.time(12, 0))
    ev = []
    for b in base():
        d = dt.date.fromisoformat(b["date"])
        ev += [dt.datetime.combine(d, dt.time(6)) + dt.timedelta(minutes=5 * i) for i in range(60)]
    ev += [dt.datetime.combine(DAY, dt.time(6)) + dt.timedelta(minutes=5 * i) for i in range(10)]
    ev.sort()
    j = rs.judge(raw(DAY, complete=False), base(), ev, now)
    assert j["signals"]["movement"]["value"] == 10
    assert j["signals"]["movement"]["usual"] == 60
    assert j["verdict"] == "off_track"
    assert j["reasons"] == ["Moving much less than usual by now"]


def test_reason_text_joins_in_plain_words():
    assert rs.reason_text(["Up at 06:10, about an hour later than usual",
                           "4 bathroom visits overnight (usually 1)"]) == \
        "Up at 06:10, about an hour later than usual, and 4 bathroom visits overnight (usually 1)"


def test_about_wording():
    assert rs._about(25) == "about 25 min"
    assert rs._about(-62) == "about an hour"
    assert rs._about(95) == "about 1½ hours"
    assert rs._about(125) == "about 2 hours"


def test_before_she_stirs_says_so_not_short_of_history():
    """From 00:01 until she stirs there is nothing to judge yet. With 28 days
    of history behind it the card said "Not enough history yet to judge"
    every night."""
    now = dt.datetime.combine(DAY, dt.time(2, 30))
    j = rs.judge(raw(DAY, complete=False, up=None, movement=0, bathroom=None), base(), [], now)
    assert j["verdict"] == "no_data"
    assert j["reasons"] == ["Not up yet, judged once she stirs"]


def test_before_she_stirs_with_thin_history_still_says_history():
    now = dt.datetime.combine(DAY, dt.time(2, 30))
    j = rs.judge(raw(DAY, complete=False, up=None, movement=0, bathroom=None), base(5), [], now)
    assert j["reasons"] == ["Not enough history yet to judge"]
