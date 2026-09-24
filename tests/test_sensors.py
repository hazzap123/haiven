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


def render(template, states=None, attrs=None, now=NOW):
    states, attrs = states or {}, attrs or {}
    env = Environment(loader=BaseLoader())
    env.globals.update(
        states=lambda e: states.get(e, 'unknown'),
        is_state=lambda e, v: states.get(e) == v,
        state_attr=lambda e, a: attrs.get(e, {}).get(a),
        now=lambda: now,
        as_datetime=lambda s: dt.datetime.fromisoformat(str(s)),
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
