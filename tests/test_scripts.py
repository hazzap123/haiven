"""
Tests for the Python helpers in scripts/ that read the activity log.

Run with: pytest tests/test_scripts.py -v
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.argv = sys.argv[:1]     # night_stats reads its log path from argv[1] at import

import drift_stats  # noqa: E402
import movement_today  # noqa: E402
import night_stats  # noqa: E402

# Read from the source, not the module: night_stats takes its log path from
# argv[1] at import and the other scripts' main() repoints it, so the live
# value depends on which test file imported it first and what ran before.
NIGHT_STATS_DEFAULT_LOG = re.search(
    r'^LOG = .* else "([^"]+)"$', (ROOT / "scripts" / "night_stats.py").read_text(), re.M).group(1)


def _written_log_path():
    """The file shell_command.log_activity appends to."""
    with open(ROOT / "configuration.yaml") as f:
        text = f.read()
    return re.search(r"log_activity:.*>> (\S+?)\\?\"'", text).group(1)


class TestLogPath:
    """The scripts must read the log the automations write."""

    def test_writer_path(self):
        assert _written_log_path() == "/config/activity.log"

    def test_night_stats_reads_it(self):
        assert NIGHT_STATS_DEFAULT_LOG == _written_log_path()

    def test_drift_stats_reads_it(self):
        assert drift_stats.LOG_FILE == _written_log_path()

    def test_movement_today_reads_it(self):
        assert movement_today.LOG_FILE == _written_log_path()


class TestLocationLines:
    """haiven_log_person_location logs the person's name, which can have a
    space in it (the default is "Your Person")."""

    def _default_name(self):
        with open(ROOT / "packages" / "haiven_care_circle_inputs.yaml") as f:
            return yaml.safe_load(f)["input_text"]["elderly_person_name"]["initial"]

    def test_default_name_is_parsed(self):
        name = self._default_name()
        line = f"2026-09-01 08:00:00 INFO {name} Location (left home) | 08:00:00 | Tuesday"
        m = drift_stats.LOC_LINE.match(line)
        assert m and m.group(2) == "left home"

    def test_single_word_name_is_parsed(self):
        line = "2026-09-01 09:30:00 INFO Jean Location (arrived home) | 09:30:00 | Tuesday"
        m = drift_stats.LOC_LINE.match(line)
        assert m and m.group(2) == "arrived home"

    def test_load_away_pairs_left_and_arrived(self, tmp_path):
        log = tmp_path / "activity.log"
        log.write_text(
            "2026-09-01 08:00:00 INFO Your Person Location (left home) | 08:00:00 | Tuesday\n"
            "2026-09-01 09:00:00 INFO Kitchen Motion (on) | 09:00:00 | Tuesday\n"
            "2026-09-01 10:00:00 INFO Your Person Location (arrived home) | 10:00:00 | Tuesday\n"
        )
        away = drift_stats.load_away(str(log))
        assert [(a.hour, b.hour) for a, b in away] == [(8, 10)]


class TestNightStatsEdges:
    """From the stage 6 calibration dry run: a bedtime after midnight was
    only found by the kitchen fallback, so stage 6 set those nights aside,
    and a cat in the kitchen at 04:10 was read as getting up."""

    D = __import__('datetime')

    def t(self, s):
        return self.D.datetime.fromisoformat(s)

    def night(self, K, B, T_ON, day='2026-11-06'):
        d = self.D.date.fromisoformat(day)
        now = self.t('2026-11-08 12:00:00')
        return night_stats.night(sorted(K), sorted(B), sorted(T_ON), [], d, now)

    def test_bedtime_after_midnight_found_by_bathroom_rule(self):
        n = self.night(
            K=[self.t('2026-11-06 23:42:00'), self.t('2026-11-07 08:24:00'),
               self.t('2026-11-07 08:26:00'), self.t('2026-11-07 08:30:00')],
            B=[self.t('2026-11-07 00:17:00')],
            T_ON=[self.t('2026-11-07 00:10:00'), self.t('2026-11-07 08:15:00')])
        assert (n['bed'], n['bed_rule']) == ('00:10', 'bathroom')

    def test_night_visit_after_midnight_is_not_bedtime(self):
        # Real bedtime 22:30 without a bathroom visit; 02:40 is a night visit.
        n = self.night(
            K=[self.t('2026-11-06 22:28:00'), self.t('2026-11-07 07:00:00'),
               self.t('2026-11-07 07:03:00'), self.t('2026-11-07 07:06:00')],
            B=[self.t('2026-11-06 22:33:00'), self.t('2026-11-07 02:45:00')],
            T_ON=[self.t('2026-11-07 02:40:00'), self.t('2026-11-07 06:50:00')])
        assert n['bed_rule'] == 'kitchen'

    def test_pet_run_before_dawn_is_not_wake(self):
        n = self.night(
            K=[self.t('2026-11-06 22:10:00')] + [self.t(f'2026-11-07 04:{m}:00') for m in (10, 13, 16, 19)]
              + [self.t(f'2026-11-07 06:{m}:00') for m in (53, 56, 59)],
            B=[self.t('2026-11-06 22:20:00')],
            T_ON=[self.t('2026-11-06 22:15:00'), self.t('2026-11-07 06:45:00')])
        assert n['wake'] == '06:53'

    def test_morning_without_bathroom_still_found(self):
        n = self.night(
            K=[self.t('2026-11-06 22:10:00')] + [self.t(f'2026-11-07 07:{m:02d}:00') for m in (0, 3, 6)],
            B=[self.t('2026-11-06 22:20:00')],
            T_ON=[self.t('2026-11-06 22:15:00')])
        assert n['wake'] == '07:00'


class TestMakePackage:
    """An expert config that loads a packages folder cannot take Haiven's
    configuration.yaml merged in by hand: the dry run gave about 30 errors.
    make_package.py writes one file of named packages instead; Home
    Assistant 2026.2.3's check_config passed it beside a user's own
    packages, split automations and a binary_sensor.kitchen_motion."""

    def build(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import make_package
        return make_package.build()

    def test_every_top_level_key_is_a_haiven_package(self):
        data = self.build()
        assert all(k.startswith("haiven_") and isinstance(v, dict) for k, v in data.items())

    def test_no_core_config_inside_a_package(self):
        for name, pkg in self.build().items():
            assert "homeassistant" not in pkg, name
            assert "default_config" not in pkg and "http" not in pkg, name

    def test_carries_all_automations_and_scripts(self):
        core = self.build()["haiven_core"]
        autos = yaml.safe_load((ROOT / "automations.yaml").read_text())
        scripts = yaml.safe_load((ROOT / "scripts.yaml").read_text())
        assert len(core["automation"]) == len(autos)
        assert set(core["script"]) == set(scripts)

    def test_every_configuration_package_is_included(self):
        cfg = (ROOT / "configuration.yaml").read_text()
        names = set(re.findall(r"^    (haiven_\w+): !include", cfg, re.M))
        assert names and names <= set(self.build())


def test_night_visit_then_pet_run_is_not_wake():
    """Round 2 dry run: a 04:55 bathroom visit, back to bed, then a cat in
    the kitchen at 05:15 was taken as getting up."""
    import datetime as D
    t = D.datetime.fromisoformat
    K = [t('2026-11-06 22:10:00')] + [t(f'2026-11-07 05:{m}:00') for m in (15, 16, 18, 20)] \
        + [t(f'2026-11-07 07:{m:02d}:00') for m in (5, 8, 11)]
    B = [t('2026-11-06 22:20:00'), t('2026-11-07 05:00:00')]
    T_ON = [t('2026-11-06 22:15:00'), t('2026-11-07 04:55:00'), t('2026-11-07 06:58:00')]
    n = night_stats.night(K, B, T_ON, [], D.date(2026, 11, 6), t('2026-11-08 12:00:00'))
    assert n['wake'] == '07:05'


def test_one_pet_trigger_after_bedtime_keeps_bathroom_rule():
    """Round 2 dry run: one cat trigger at 23:45 turned a 23:05 bedtime into
    a 02:15 kitchen-rule guess, and stage 6 then threw the night away."""
    import datetime as D
    t = D.datetime.fromisoformat
    K = [t('2026-11-11 22:58:00'), t('2026-11-11 23:45:00')] \
        + [t(f'2026-11-12 07:{m:02d}:00') for m in (0, 3, 6)]
    B = [t('2026-11-11 23:10:00')]
    T_ON = [t('2026-11-11 23:05:00'), t('2026-11-12 06:52:00')]
    n = night_stats.night(K, B, T_ON, [], D.date(2026, 11, 11), t('2026-11-13 12:00:00'))
    assert (n['bed'], n['bed_rule']) == ('23:05', 'bathroom')
