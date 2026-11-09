"""Tests for the Ask data layer: ha_integrations/haiven_chat/activity.py and
scripts/ask_days.py.

Run with: pytest tests/test_ask_activity.py -v
"""
import datetime as dt
import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name):
    """Load one pure module without importing the package's HA-bound __init__."""
    if "haiven_chat" not in sys.modules:
        pkg = types.ModuleType("haiven_chat")
        pkg.__path__ = [str(ROOT / "ha_integrations" / "haiven_chat")]
        sys.modules["haiven_chat"] = pkg
    return importlib.import_module(f"haiven_chat.{name}")


activity = _load("activity")
policy = _load("policy")

LOG = """\
2026-01-05 12:00:00 TEST - Manual test entry
2026-01-05 20:00:00 INFO Bedroom Presence | 20:00:00 | Monday
2026-11-02 06:00:00 INFO Kitchen Motion (on) | 06:00:00 | Monday
2026-11-02 06:00:30 INFO Kitchen Motion (off) | 06:00:30 | Monday
2026-11-02 07:10:00 INFO Kitchen Motion (on) | 07:10:00 | Monday
2026-11-02 22:00:00 INFO Bathroom Motion (on) | 22:00:00 | Monday
2026-11-03 06:15:00 INFO Bedroom Presence (on) | 06:15:00 | Tuesday
2026-11-03 06:20:00 INFO Mary Smith Location (left home) | 06:20:00 | Tuesday
"""
EVENTS = activity.parse_log(LOG.splitlines())


def test_parse_counts_on_events_and_stateless_old_lines_only():
    assert [r for _t, r in EVENTS] == ["bedroom", "kitchen", "kitchen", "bathroom", "bedroom"]


def test_counts_by_day_keep_zero_days():
    res = activity.activity_counts(EVENTS, "2026-11-01", "2026-11-03", "all", "day")
    assert res["rows"] == [
        {"key": "2026-11-01", "count": 0},
        {"key": "2026-11-02", "count": 3},
        {"key": "2026-11-03", "count": 1},
    ]


def test_counts_filter_by_room():
    assert activity.activity_counts(EVENTS, "2026-11-02", "2026-11-02", "kitchen", "day")["total"] == 2


def test_hour_group_is_an_average_over_the_whole_range():
    rows = activity.activity_counts(EVENTS, "2026-11-02", "2026-11-03", "all", "hour")["rows"]
    assert {r["key"]: r["per_day"] for r in rows}["06"] == 1.0


def test_week_buckets_start_on_monday():
    rows = activity.activity_counts(EVENTS, "2026-11-01", "2026-11-03", "all", "week")["rows"]
    assert [r["key"] for r in rows] == ["2026-10-26", "2026-11-02"]


def test_weekday_average_divides_by_that_weekday_only():
    rows = activity.activity_counts(EVENTS, "2026-11-02", "2026-11-03", "all", "weekday")["rows"]
    assert {r["key"]: r["per_day"] for r in rows}["Mon"] == 3.0


def test_backwards_range_and_bad_date_are_refused():
    with pytest.raises(policy.PolicyError):
        activity.activity_counts(EVENTS, "2026-11-03", "2026-11-02", "all", "day")
    with pytest.raises(policy.PolicyError):
        activity.day_events(EVENTS, "yesterday", "all")


def test_day_events_lists_times_and_rooms():
    res = activity.day_events(EVENTS, "2026-11-02", "kitchen")
    assert res["events"] == ["06:00 kitchen", "07:10 kitchen"]


def day(date, verdict="on_track", up=300, bed=1100, visits=1):
    return {"date": date, "complete": True, "verdict": verdict, "why": "", "up_min": up, "bed_min": bed,
            "bed_rule": "bathroom", "visits": visits, "trips": 0, "movement": 100, "kitchen": 50, "away_min": 0}


def test_daily_rows_show_clock_times():
    res = activity.daily_history([day("2026-11-02")], "2026-11-02", "2026-11-02", "day")
    assert res["rows"][0]["up"] == "05:00" and res["rows"][0]["bed"] == "18:20"
    assert res["verdicts"] == {"on_track": 1}


def test_bedtime_after_midnight_shows_the_clock_time():
    assert activity.hhmm(1440 + 30) == "00:30"


def test_month_average_leaves_out_away_days():
    days = [day("2026-10-01", visits=1), day("2026-10-02", visits=3),
            day("2026-10-05", verdict="away", visits=9)]
    row = activity.daily_history(days, "2026-10-01", "2026-10-31", "month")["rows"][0]
    assert row["visits"] == 2.0 and row["days"] == 3 and row["days_averaged"] == 2


def test_metric_series_keeps_gaps_as_none():
    series = activity.metric_series([day("2026-10-01", visits=None)], "visits", "day")
    assert series["points"] == [{"start": "2026-10-01", "value": None}]


@pytest.mark.parametrize("entity_id", [
    "person.elderly_person", "device_tracker.iphone", "camera.kitchen", "media_player.bedroom",
    "input_text.carer_1_phone", "sensor.phone_geocoded_location",
    "lock.front_door", "switch.heater", "sensor.router_external_ip",
    "sensor.primary_contact_distance", "sensor.secondary_contact_distance",
    "sensor.professional_carer_distance", "sensor.nearest_care_circle_member",
    "sensor.care_circle_member_present", "binary_sensor.primary_contact_nearby",
    "input_number.care_circle_proximity_threshold",
])
def test_denied_reads(entity_id):
    with pytest.raises(policy.PolicyError):
        policy.check_readable(entity_id)


@pytest.mark.parametrize("entity_id", [
    "sensor.elderly_person_location", "input_text.current_summary", "sensor.routine_stats",
    "sensor.minutes_since_kitchen_activity", "binary_sensor.elderly_person_home",
])
def test_allowed_reads(entity_id):
    policy.check_readable(entity_id)


def test_radar_distance_is_not_caught_by_the_carer_screen():
    policy.check_readable("sensor.haiven_bedroom_target_1_distance")


def test_location_attributes_are_stripped():
    out = policy.clean_attributes({"latitude": 51.0, "gps_accuracy": 5, "Phone": "07", "friendly_name": "x"})
    assert out == {"friendly_name": "x"}


def test_absurd_date_range_is_refused_before_any_walk():
    with pytest.raises(policy.PolicyError):
        activity.activity_counts(EVENTS, "0001-01-01", "9999-12-31", "all", "day")
    with pytest.raises(policy.PolicyError):
        activity.daily_history([], "0001-01-01", "9999-12-31", "day")


def test_series_is_bound_to_the_user_who_asked():
    store = policy.SeriesStore(ttl=60)
    series_id = store.put("user_a", {"a": 1})
    assert store.get("user_a", series_id) == {"a": 1}
    with pytest.raises(policy.PolicyError):
        store.get("someone_else", series_id)


def test_ask_days_row_carries_last_nights_visits_and_this_evenings_bed():
    import ask_days
    import drift_stats

    now = dt.datetime(2026, 9, 21, 9, 0)
    base = dt.date(2026, 9, 1)
    K, B, T_ON, T_OFF = [], [], [], []
    for i in range(20):
        d = base + dt.timedelta(i)
        for minute in (0, 4, 8):
            K.append(dt.datetime.combine(d, dt.time(5, minute)))
        K.append(dt.datetime.combine(d, dt.time(12)))
        T_ON.append(dt.datetime.combine(d, dt.time(18)))
        T_OFF.append(dt.datetime.combine(d, dt.time(18, 2)))
        B.append(dt.datetime.combine(d, dt.time(18, 10)))
        T_ON.append(dt.datetime.combine(d, dt.time(23)))
        T_OFF.append(dt.datetime.combine(d, dt.time(23, 2)))
    rows = {r["date"]: r for r in ask_days.rows(now, K, B, T_ON, T_OFF, [])}
    row = rows["2026-09-10"]
    assert row["up_min"] == 300
    assert row["bed_min"] == 1080
    assert row["visits"] == 1
    night = {n["date"]: n for n in drift_stats.all_nights(now, K, B, T_ON, T_OFF)}
    assert row["visits"] == night["2026-09-09"]["visits"]
