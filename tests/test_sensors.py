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


class TestOvernightActivitySummary:
    """A sensor state is capped at 255 characters; HA marks a longer one
    unknown. The AI summaries read this state (Conversation sees states, not
    attributes), so an overnight with many events went to the AI as unknown."""

    @pytest.fixture
    def tpl(self):
        return template_entity('overnight_activity_summary_from_log', ROOT / "configuration.yaml")['state']

    def _log(self, entries):
        return {'sensor.activity_log_48h': {'log': '|'.join(entries)}}

    def test_short_night_is_listed(self, tpl):
        out = render(tpl, attrs=self._log(['20:10 Kitchen (on)', '23:40 Bathroom (on)', '02:15 Bathroom (on)']))
        assert out == '23:40 Bathroom (on), 02:15 Bathroom (on)'

    def test_busy_night_fits_and_keeps_the_latest(self, tpl):
        entries = ['%02d:%02d Bathroom (on)' % (h, m) for h in (22, 23, 0, 1, 2, 3, 4) for m in (5, 20, 40)]
        out = render(tpl, attrs=self._log(entries))
        assert len(out) <= 255
        assert out.endswith(entries[-1])
        assert out.startswith('…')

    def test_no_data(self, tpl):
        assert render(tpl) == 'No data'


# ---------------------------------------------------------------------------
# Configurable detection windows
# ---------------------------------------------------------------------------

class _States:
    """Callable like states('x.y') and browsable like states.x.y, as in HA."""

    class _Obj:
        def __init__(self, state, last_changed):
            self.state, self.last_changed = state, last_changed

    class _Domain:
        def __init__(self, items):
            self.__dict__.update(items)

    def __init__(self, values, changed=None):
        self._values = values
        by_domain = {}
        for entity_id, when in (changed or {}).items():
            domain, name = entity_id.split('.')
            by_domain.setdefault(domain, {})[name] = self._Obj(values.get(entity_id, 'on'), when)
        for domain, items in by_domain.items():
            setattr(self, domain, self._Domain(items))

    def __call__(self, entity_id):
        return self._values.get(entity_id, 'unknown')


def render_ha(template, values=None, attrs=None, now=NOW, changed=None):
    values, attrs = values or {}, attrs or {}
    env = Environment(loader=BaseLoader())
    env.filters['as_local'] = lambda d: d.astimezone(TZ)
    env.globals.update(
        states=_States(values, changed),
        is_state=lambda e, v: values.get(e) == v,
        state_attr=lambda e, a: attrs.get(e, {}).get(a),
        now=lambda: now,
        timedelta=dt.timedelta,
        as_datetime=lambda s: s if isinstance(s, dt.datetime) else dt.datetime.fromisoformat(str(s)),
        today_at=lambda t: dt.datetime.combine(now.date(), dt.time.fromisoformat(t), tzinfo=TZ),
    )
    return env.from_string(template).render().strip()


def at(hour, minute=0, day=1):
    return dt.datetime(2026, 9, day, hour, minute, tzinfo=TZ)


class TestBedtimeWindow:
    """The window bedtime is looked for in. It was fixed at 17:30-21:00, so a
    household that goes to bed at 22:30 never had a bedtime recorded."""

    def window(self, **helpers):
        values = {f'input_datetime.{k}': v for k, v in helpers.items()}
        return render_ha(template_entity('bedtime_window')['state'], values)

    def test_helpers_set_the_window(self):
        assert self.window(bedtime_window_start='20:30:00', bedtime_window_end='23:45:00') == '20:30-23:45'

    def test_unset_helpers_follow_expected_bedtime(self):
        # A fresh install has both helpers at 00:00.
        assert self.window(bedtime_window_start='00:00:00', bedtime_window_end='00:00:00',
                           expected_bedtime='22:00:00') == '19:00-00:00'

    def test_derived_window_can_cross_midnight(self):
        assert self.window(expected_bedtime='23:30:00') == '20:30-01:30'

    def test_nothing_set_at_all_still_gives_a_window(self):
        assert self.window() == '19:00-00:00'

    @pytest.mark.parametrize("window,now,expected", [
        ('19:00-23:00', at(18, 59), 'False'),
        ('19:00-23:00', at(19, 0), 'True'),
        ('19:00-23:00', at(22, 59), 'True'),
        ('19:00-23:00', at(23, 0), 'False'),
        ('21:00-01:30', at(23, 30), 'True'),      # crosses midnight, before it
        ('21:00-01:30', at(0, 45, day=2), 'True'),  # and after it
        ('21:00-01:30', at(1, 30, day=2), 'False'),
        ('21:00-01:30', at(12, 0), 'False'),
        ('unknown', at(20, 0), 'False'),
    ])
    def test_active(self, window, now, expected):
        entity = template_entity('bedtime_window_active')
        assert render_ha(entity['state'], {'sensor.bedtime_window': window}, now=now) == expected

    def test_started_at_is_yesterday_once_past_midnight(self):
        tpl = template_entity('bedtime_window_active')['attributes']['started_at']
        before = render_ha(tpl, {'sensor.bedtime_window': '21:00-01:30'}, now=at(23, 30))
        after = render_ha(tpl, {'sensor.bedtime_window': '21:00-01:30'}, now=at(0, 45, day=2))
        assert dt.datetime.fromisoformat(before) == at(21, 0)
        assert dt.datetime.fromisoformat(after) == at(21, 0)


class TestBedtimePattern:
    def pattern(self, now, active, started, kitchen, bathroom, bedroom):
        values = {'binary_sensor.bedtime_window_active': 'on' if active else 'off'}
        attrs = {'binary_sensor.bedtime_window_active': {'started_at': started.isoformat()}}
        changed = {'event.kitchen_motion': kitchen,
                   'binary_sensor.haiven_bathroom_motion': bathroom,
                   'binary_sensor.haiven_bedroom_occupancy': bedroom}
        return render_ha(template_entity('bedtime_pattern_detected')['state'], values, attrs,
                         now=now, changed=changed).capitalize()

    def test_late_bedtime_is_detected_inside_a_late_window(self):
        # Kitchen quiet since 21:40, bathroom at 22:20, bedroom at 22:25, now 22:45.
        assert self.pattern(at(22, 45), True, at(20, 30),
                            kitchen=at(21, 40), bathroom=at(22, 20), bedroom=at(22, 25)) == 'True'

    def test_nothing_is_detected_outside_the_window(self):
        assert self.pattern(at(22, 45), False, at(17, 30),
                            kitchen=at(21, 40), bathroom=at(22, 20), bedroom=at(22, 25)) == 'False'

    def test_a_bathroom_visit_before_the_window_does_not_count(self):
        assert self.pattern(at(22, 45), True, at(20, 30),
                            kitchen=at(19, 0), bathroom=at(20, 10), bedroom=at(22, 25)) == 'False'

    def test_bathroom_time_is_local_not_utc(self):
        tpl = template_entity('bedtime_pattern_detected')['attributes']['bathroom_time']
        utc = dt.datetime(2026, 9, 1, 21, 20, tzinfo=dt.timezone.utc)      # 22:20 local
        assert render_ha(tpl, changed={'binary_sensor.haiven_bathroom_motion': utc}) == '22:20'


class TestBedtimeMinutes:
    def minutes(self, bedtime, window):
        return render_ha(template_entity('today_bedtime_minutes')['state'],
                         {'sensor.today_bedtime': bedtime, 'sensor.bedtime_window': window})

    def test_inside_the_window(self):
        assert self.minutes('22:30', '20:30-01:30') == '1350'

    def test_after_midnight_counts_on_from_24_hours(self):
        assert self.minutes('00:10', '20:30-01:30') == '1450'

    def test_outside_the_window_is_rejected(self):
        assert self.minutes('15:00', '20:30-01:30') == 'None'

    def test_average_wraps_back_to_a_clock_time(self):
        avg = render_ha(template_entity('average_bedtime_week')['state'],
                        {'sensor.average_bedtime_minutes_week': '1450'})
        assert avg == '00:10'

    def test_average_falls_back_to_expected_bedtime(self):
        avg = render_ha(template_entity('average_bedtime_week')['state'],
                        {'input_datetime.expected_bedtime': '22:15:00'})
        assert avg == '22:15'


class TestWakeWindow:
    """The earliest time first activity counts as getting up. It was fixed at
    04:00."""

    def start(self, **helpers):
        values = {f'input_datetime.{k}': v for k, v in helpers.items()}
        return render_ha(template_entity('wake_window_start')['state'], values)

    def test_helper_sets_it(self):
        assert self.start(wake_window_start='06:30:00', expected_wake_time='08:00:00') == '06:30'

    def test_unset_follows_expected_wake(self):
        assert self.start(wake_window_start='00:00:00', expected_wake_time='09:30:00') == '06:30'

    def test_never_before_midnight(self):
        assert self.start(expected_wake_time='02:00:00') == '00:00'

    def test_nothing_set_keeps_the_old_default(self):
        assert self.start(wake_window_start='00:00:00', expected_wake_time='00:00:00') == '04:00'

    @pytest.mark.parametrize("now,expected", [(at(6, 29), 'False'), (at(6, 30), 'True'),
                                              (at(11, 0), 'True'), (at(11, 1), 'False')])
    def test_morning_window_opens_at_it(self, now, expected):
        entity = template_entity('morning_window_active')
        values = {'sensor.wake_window_start': '06:30', 'input_datetime.expected_wake_time': '08:00:00',
                  'input_number.wake_time_variance_minutes': '60'}
        assert render_ha(entity['state'], values, now=now) == expected


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


@pytest.mark.parametrize("path", [ROOT / "haiven_sensors_3sensor.yaml", ROOT / "configuration.yaml",
                                  *sorted((ROOT / "packages").glob("*.yaml"))], ids=lambda p: p.name)
def test_every_template_parses(path):
    """A template with a syntax error makes its entity unavailable, silently."""
    env = Environment(loader=BaseLoader())
    for text in _strings(_load(path)):
        if '{{' in text or '{%' in text:
            env.parse(text)
