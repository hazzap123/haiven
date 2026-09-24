"""
Tests for the template sensors in haiven_sensors_3sensor.yaml and packages/.

Templates are rendered with a small stand-in for Home Assistant's helpers
(states, state_attr, now, as_datetime) that keeps HA's types: an
input_datetime state is a naive local string and now() is tz-aware.

Run with: pytest tests/test_sensors.py -v
"""

import datetime as dt
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, BaseLoader

ROOT = Path(__file__).parent.parent
TZ = dt.timezone(dt.timedelta(hours=1))
NOW = dt.datetime(2026, 9, 1, 23, 0, tzinfo=TZ)


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_multi_constructor('!', lambda loader, suffix, node: None)


def _load(path):
    with open(path) as f:
        return yaml.load(f, Loader=_Loader)


def _template_entities(doc):
    """Every modern-syntax template entity in a package, any platform."""
    for block in (doc or {}).get('template', []) or []:
        for platform, items in block.items():
            if isinstance(items, list):
                for item in items:
                    yield item


def template_entity(unique_id, path=ROOT / "haiven_sensors_3sensor.yaml"):
    return next(e for e in _template_entities(_load(path)) if e.get('unique_id') == unique_id)


def render(template, states=None, attrs=None, now=NOW, objects=None):
    states, attrs, objects = states or {}, attrs or {}, objects or {}
    env = Environment(loader=BaseLoader())
    env.globals.update(
        states=lambda e: states.get(e, 'unknown'),
        is_state=lambda e, v: states.get(e) == v,
        state_attr=lambda e, a: attrs.get(e, {}).get(a),
        now=lambda: now,
        as_datetime=lambda s: dt.datetime.fromisoformat(str(s)),
        expand=lambda e: [objects[e]] if e in objects else [],
    )
    return env.from_string(template).render().strip()


class TestTimeInBed:
    """as_datetime() of an input_datetime state is naive and now() is aware,
    so subtracting them raised TypeError every minute she was in bed."""

    def test_minutes_in_bed(self):
        tpl = template_entity('time_in_bed_minutes')['state']
        entered = dt.datetime(2026, 9, 1, 21, 30, tzinfo=TZ)
        out = render(
            tpl,
            states={'input_select.bed_state': 'sleeping',
                    'input_datetime.zone1_entered_time': '2026-09-01 21:30:00'},
            attrs={'input_datetime.zone1_entered_time': {'timestamp': entered.timestamp()}},
        )
        assert float(out) == 90

    def test_zero_when_out_of_bed(self):
        tpl = template_entity('time_in_bed_minutes')['state']
        out = render(tpl, states={'input_select.bed_state': 'awake'})
        assert out == '0'


class TestCircleFreshness:
    """The card ages a contact from the location sensor's last_updated
    attribute. It read state_attr(person, 'last_changed'), which is not an
    attribute, so it was always None and the card fell back to the moment
    the "Away" label last changed: a phone that had reported an hour ago
    showed as "last known 20h"."""

    @pytest.mark.parametrize('uid,person_input', [
        ('primary_contact_location_display', 'input_text.contact_1_person'),
        ('secondary_contact_location_display', 'input_text.contact_2_person'),
    ])
    def test_last_updated_is_the_last_position_fix(self, uid, person_input):
        path = ROOT / "packages" / "haiven_circle_tracking.yaml"
        tpl = template_entity(uid, path)['attributes']['last_updated']
        fix = dt.datetime(2026, 9, 1, 22, 50, 12, tzinfo=TZ)

        class Person:
            last_updated = fix
            last_changed = dt.datetime(2026, 8, 31, 2, 0, tzinfo=TZ)

        out = render(tpl, states={person_input: 'person.contact'},
                     objects={'person.contact': Person()})
        assert dt.datetime.fromisoformat(out) == fix


class TestRoomTransitionTimeout:
    """A motion-only main-room sensor does not fire on someone sitting still,
    so a 30-minute timeout asserted "left a room and never arrived" most
    afternoons. The helper also carried `initial:`, which HA reapplies on
    every restart, silently undoing any tuning from the Settings screen."""

    @pytest.fixture
    def helper(self):
        doc = _load(ROOT / "packages" / "haiven_monitoring_inputs.yaml")
        return doc['input_number']['transition_timeout_mins']

    def test_not_reset_on_restart(self, helper):
        assert 'initial' not in helper

    def test_ninety_is_settable(self, helper):
        assert helper['min'] <= 90 <= helper['max']

    def test_fresh_install_does_not_start_at_five(self, helper):
        # With no initial and nothing to restore, HA starts an input_number
        # at its minimum.
        assert helper['min'] >= 30

    def test_template_fallback_is_ninety(self):
        text = (ROOT / "haiven_sensors_3sensor.yaml").read_text()
        uses = [l for l in text.splitlines() if "input_number.transition_timeout_mins" in l]
        assert uses and all("| int(90)" in l for l in uses), uses
