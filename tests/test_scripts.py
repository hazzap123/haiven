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
        assert night_stats.LOG == _written_log_path()

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
