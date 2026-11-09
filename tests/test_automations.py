"""
Tests for Haiven Home Assistant automations.

Tests YAML syntax, Jinja2 template logic, and automation structure.
Run with: pytest tests/test_automations.py -v
"""

import re

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from jinja2 import Environment, BaseLoader, TemplateSyntaxError


# Path to automations file
AUTOMATIONS_PATH = Path(__file__).parent.parent / "automations.yaml"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def automations():
    """Load automations.yaml and return parsed content."""
    with open(AUTOMATIONS_PATH, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def jinja_env():
    """Create a Jinja2 environment with Home Assistant-like functions."""
    env = Environment(loader=BaseLoader())
    return env


@pytest.fixture
def mock_states():
    """Create mock state objects for template testing."""
    return {
        'input_datetime.expected_wake_time': '07:00:00',
        'input_datetime.expected_bedtime': '22:00:00',
        'input_datetime.actual_bedtime_today': 'unknown',
        'input_datetime.actual_wake_time_today': 'unknown',
        'input_number.wake_time_variance_minutes': '60',
        'input_number.bedtime_variance_minutes': '30',
        'input_number.no_activity_alert_hours': '4',
        'input_boolean.haiven_monitoring_enabled': 'on',
        'input_boolean.manual_safe_status': 'off',
        'input_boolean.bathroom_occupied_night': 'off',
        'input_text.elderly_person_name': 'Mary',
        'sensor.deviation_count': '0',
        'sensor.last_activity_display': 'Kitchen 10 mins ago',
    }


# =============================================================================
# YAML SYNTAX AND STRUCTURE TESTS
# =============================================================================

class TestYamlValidity:
    """Test YAML file syntax and structure."""

    def test_yaml_loads_successfully(self, automations):
        """Verify automations.yaml is valid YAML."""
        assert automations is not None
        assert isinstance(automations, list)

    def test_all_automations_have_required_fields(self, automations):
        """Each automation must have id, alias, triggers, and actions."""
        required_fields = ['id', 'alias', 'triggers', 'actions']

        for auto in automations:
            for field in required_fields:
                assert field in auto, f"Automation '{auto.get('alias', 'unknown')}' missing '{field}'"

    def test_automation_ids_are_unique(self, automations):
        """All automation IDs must be unique."""
        ids = [a['id'] for a in automations]
        duplicates = [id for id in ids if ids.count(id) > 1]
        assert len(duplicates) == 0, f"Duplicate automation IDs: {set(duplicates)}"

    def test_automation_aliases_are_unique(self, automations):
        """All automation aliases should be unique."""
        aliases = [a['alias'] for a in automations]
        duplicates = [alias for alias in aliases if aliases.count(alias) > 1]
        assert len(duplicates) == 0, f"Duplicate automation aliases: {set(duplicates)}"

    def test_triggers_are_lists(self, automations):
        """Triggers must be a list."""
        for auto in automations:
            triggers = auto.get('triggers')
            assert isinstance(triggers, list), f"'{auto['alias']}' triggers must be a list"

    def test_actions_are_lists(self, automations):
        """Actions must be a list."""
        for auto in automations:
            actions = auto.get('actions')
            assert isinstance(actions, list), f"'{auto['alias']}' actions must be a list"

    def test_conditions_are_lists_when_present(self, automations):
        """Conditions must be a list when present."""
        for auto in automations:
            conditions = auto.get('conditions')
            if conditions is not None:
                assert isinstance(conditions, list), f"'{auto['alias']}' conditions must be a list"


class TestAutomationModes:
    """Test automation mode configurations."""

    def test_all_automations_have_mode(self, automations):
        """Each automation should specify a mode."""
        for auto in automations:
            assert 'mode' in auto, f"Automation '{auto['alias']}' missing 'mode'"

    def test_valid_automation_modes(self, automations):
        """Automation modes must be valid Home Assistant modes."""
        valid_modes = ['single', 'restart', 'queued', 'parallel']

        for auto in automations:
            mode = auto.get('mode')
            assert mode in valid_modes, f"'{auto['alias']}' has invalid mode: {mode}"

    def test_queued_automations_have_max(self, automations):
        """Queued automations should have max specified."""
        for auto in automations:
            if auto.get('mode') == 'queued':
                # Not strictly required but recommended
                if 'max' not in auto:
                    print(f"Warning: queued automation '{auto['alias']}' has no max")


# =============================================================================
# HAIVEN-SPECIFIC AUTOMATION TESTS
# =============================================================================

class TestHaivenAutomations:
    """Test Haiven-specific automation requirements."""

    def test_expected_automations_exist(self, automations):
        """Verify critical Haiven automations are present."""
        expected_ids = [
            'haiven_morning_activity_check',
            'haiven_no_activity_alert',
            'haiven_bedtime_confirmation_v2',
            'haiven_daily_reset',
            'haiven_evening_summary',
            'haiven_bathroom_night_entry',
            'haiven_bathroom_night_exit',
        ]

        actual_ids = [a['id'] for a in automations]
        for expected in expected_ids:
            assert expected in actual_ids, f"Missing critical automation: {expected}"

    def test_monitoring_automations_check_enabled(self, automations):
        """Automations that should respect monitoring toggle do so."""
        should_check_monitoring = [
            'haiven_morning_activity_check',
            'haiven_no_activity_alert',
            'haiven_bedtime_confirmation_v2',
            'haiven_evening_summary',
            'haiven_bathroom_night_extended_alert',
        ]

        for auto in automations:
            if auto['id'] in should_check_monitoring:
                conditions = auto.get('conditions', [])
                has_monitoring_check = any(
                    c.get('entity_id') == 'input_boolean.haiven_monitoring_enabled'
                    for c in conditions if isinstance(c, dict)
                )
                assert has_monitoring_check, f"'{auto['alias']}' should check monitoring_enabled"

    def test_alert_automations_have_once_per_day(self, automations):
        """Alert automations should fire only once per day. Each one has the
        guard that fits how it triggers."""
        by_id = {a['id']: a for a in automations}

        # Polled: a last_triggered guard on the local date.
        conditions_text = yaml.dump(by_id['haiven_morning_activity_check'].get('conditions', []), width=1000)
        assert 'last_triggered' in conditions_text and 'now().date()' in conditions_text, \
            "'haiven_morning_activity_check' should have a last_triggered once-per-day condition"

        # A long silence can outlast a day, so this one re-alerts, but no
        # sooner than 4 hours after the last alert.
        conditions_text = yaml.dump(by_id['haiven_no_activity_alert'].get('conditions', []), width=1000)
        assert 'last_triggered' in conditions_text and '14400' in conditions_text, \
            "'haiven_no_activity_alert' should wait 4 hours before re-alerting"

        # Bedtime is recorded once; the guard is "not already recorded today".
        conditions_text = yaml.dump(by_id['haiven_bedtime_confirmation_v2'].get('conditions', []), width=1000)
        assert 'actual_bedtime_today' in conditions_text and '00:00:00' in conditions_text

        # A single fixed-time trigger fires once a day by construction.
        triggers = by_id['haiven_evening_summary']['triggers']
        assert len(triggers) == 1 and triggers[0].get('trigger') == 'time', \
            "'haiven_evening_summary' should fire from one daily time trigger"

    def test_bedtime_v2_checks_not_already_recorded(self, automations):
        """Bedtime V2 should check if bedtime was already recorded today."""
        bedtime_v2 = next((a for a in automations if a['id'] == 'haiven_bedtime_confirmation_v2'), None)
        assert bedtime_v2 is not None

        conditions_text = yaml.dump(bedtime_v2.get('conditions', []))
        assert 'actual_bedtime_today' in conditions_text, "Bedtime V2 should check actual_bedtime_today"


class TestTriggerConfigurations:
    """Test trigger configurations are correct."""

    def test_time_pattern_triggers(self, automations):
        """Time pattern triggers should have valid patterns."""
        for auto in automations:
            for trigger in auto.get('triggers', []):
                if trigger.get('trigger') == 'time_pattern':
                    # Must have at least one of: hours, minutes, seconds
                    has_pattern = any(k in trigger for k in ['hours', 'minutes', 'seconds'])
                    assert has_pattern, f"'{auto['alias']}' time_pattern missing pattern"

    def test_state_triggers_have_entity(self, automations):
        """State triggers must specify entity_id."""
        for auto in automations:
            for trigger in auto.get('triggers', []):
                if trigger.get('trigger') == 'state':
                    assert 'entity_id' in trigger, f"'{auto['alias']}' state trigger missing entity_id"

    def test_bathroom_triggers_use_correct_sensor(self, automations):
        """Bathroom-related automations use the correct sensor."""
        bathroom_auto_ids = [
            'haiven_bathroom_night_entry',
            'haiven_bathroom_unusual',
        ]

        for auto in automations:
            if auto['id'] in bathroom_auto_ids:
                triggers = auto.get('triggers', [])
                trigger_entities = [t.get('entity_id', '') for t in triggers]
                # Flatten if list
                flat_entities = []
                for e in trigger_entities:
                    if isinstance(e, list):
                        flat_entities.extend(e)
                    else:
                        flat_entities.append(e)

                has_bathroom_sensor = any(
                    'haiven_bathroom' in e or 'bathroom' in e.lower() or 'bathroom' in e.lower()
                    for e in flat_entities
                )
                assert has_bathroom_sensor, f"'{auto['alias']}' should trigger on bathroom sensor"


# =============================================================================
# JINJA2 TEMPLATE TESTS
# =============================================================================

class TestJinjaTemplateSyntax:
    """Test that all Jinja2 templates have valid syntax."""

    def test_all_value_templates_parse(self, automations, jinja_env):
        """All value_template fields should be valid Jinja2."""
        errors = []

        for auto in automations:
            # Check conditions
            for condition in auto.get('conditions', []):
                if isinstance(condition, dict):
                    template = condition.get('value_template', '')
                    if template:
                        try:
                            # Strip Home Assistant's > multiline indicator
                            clean_template = str(template).lstrip('>-').strip()
                            jinja_env.parse(clean_template)
                        except TemplateSyntaxError as e:
                            errors.append(f"{auto['alias']}: {e}")

            # Check actions
            for action in auto.get('actions', []):
                if isinstance(action, dict):
                    for key, value in action.items():
                        if isinstance(value, str) and '{{' in value:
                            try:
                                jinja_env.parse(value)
                            except TemplateSyntaxError as e:
                                errors.append(f"{auto['alias']} action: {e}")

        assert len(errors) == 0, f"Template syntax errors:\n" + "\n".join(errors)

    def test_night_window_template_logic(self):
        """Test the night monitoring window calculation template."""
        # This is a simplified test of the template logic
        # In real HA, this uses today_at() and timedelta()

        # Test case: bedtime 22:00 + 30min variance = 22:30 start
        # wake 07:00 - 30min variance = 06:30 end
        bedtime_base = "22:00:00"
        bedtime_var = 30
        wake_base = "07:00:00"
        wake_var = 30

        # Parse times
        bedtime_time = datetime.strptime(bedtime_base, "%H:%M:%S")
        wake_time = datetime.strptime(wake_base, "%H:%M:%S")

        monitor_start = bedtime_time + timedelta(minutes=bedtime_var)  # 22:30
        monitor_end = wake_time - timedelta(minutes=wake_var)  # 06:30

        # Verify the window spans midnight (start > end on same day)
        assert monitor_start.time() > monitor_end.time(), "Night window should span midnight"

        # Test a time at 23:00 should be in window
        test_time = datetime.strptime("23:00:00", "%H:%M:%S")
        in_window = test_time.time() >= monitor_start.time() or test_time.time() < monitor_end.time()
        assert in_window, "23:00 should be in night window"

        # Test a time at 12:00 should NOT be in window
        test_time_noon = datetime.strptime("12:00:00", "%H:%M:%S")
        in_window_noon = test_time_noon.time() >= monitor_start.time() or test_time_noon.time() < monitor_end.time()
        assert not in_window_noon, "12:00 should NOT be in night window"


# =============================================================================
# NOTIFICATION TESTS
# =============================================================================

class TestNotificationActions:
    """Test notification action configurations."""

    def test_alert_automations_send_notifications(self, automations):
        """Alert automations should send notifications."""
        alert_ids = [
            'haiven_morning_activity_check',
            'haiven_no_activity_alert',
            'haiven_bathroom_unusual',
            'haiven_bathroom_night_extended_alert',
            'haiven_bathroom_night_no_return_alert',
        ]

        for auto in automations:
            if auto['id'] in alert_ids:
                actions = auto.get('actions', [])
                actions_text = yaml.dump(actions)
                has_notification = (
                    'notify.' in actions_text or
                    'primary_contact_notification' in actions_text or
                    'script.notify_care_circle' in actions_text or
                    'script.send_haiven_notification' in actions_text
                )
                assert has_notification, f"'{auto['alias']}' should send notification"

    def test_critical_alerts_have_high_priority(self, automations):
        """Critical alerts should have high/critical priority."""
        critical_ids = [
            'haiven_bathroom_night_no_return_alert',
        ]

        for auto in automations:
            if auto['id'] in critical_ids:
                actions_text = yaml.dump(auto.get('actions', []))
                assert 'critical' in actions_text.lower() or 'priority' in actions_text.lower(), \
                    f"'{auto['alias']}' should have high/critical priority"

    def test_passive_notifications_marked_correctly(self, automations):
        """Non-urgent notifications should use passive interruption level.
        Only unconditional steps are checked: the morning confirmation also
        has a late-wake branch that is time-sensitive on purpose."""
        passive_ids = [
            'haiven_morning_activity_confirmation',
            'haiven_evening_summary',
        ]

        for auto in automations:
            if auto['id'] in passive_ids:
                sends = [s for s in auto.get('actions', [])
                         if s.get('action') == 'script.send_haiven_notification']
                assert sends, f"'{auto['alias']}' should send a notification"
                for s in sends:
                    assert s['data'].get('level') == 'passive', \
                        f"'{auto['alias']}' should use passive interruption"


# =============================================================================
# ENTITY REFERENCE TESTS
# =============================================================================

class TestEntityReferences:
    """Test that entity references are consistent."""

    def test_sensor_entities_exist_in_triggers(self, automations):
        """Core sensors should be referenced correctly in triggers."""
        expected_sensors = [
            'event.kitchen_motion',
            'binary_sensor.haiven_bedroom_occupancy',
            'binary_sensor.haiven_bathroom_motion',
        ]

        all_trigger_entities = []
        for auto in automations:
            for trigger in auto.get('triggers', []):
                entity = trigger.get('entity_id')
                if entity:
                    if isinstance(entity, list):
                        all_trigger_entities.extend(entity)
                    else:
                        all_trigger_entities.append(entity)

        for sensor in expected_sensors:
            assert sensor in all_trigger_entities, f"Sensor {sensor} should be used in triggers"

    def test_input_helpers_referenced(self, automations):
        """Key input helpers should be referenced in automations."""
        all_content = yaml.dump(automations)

        expected_inputs = [
            'input_boolean.haiven_monitoring_enabled',
            'input_datetime.expected_wake_time',
            'input_datetime.expected_bedtime',
            'input_number.wake_time_variance_minutes',
        ]

        for input_entity in expected_inputs:
            assert input_entity in all_content, f"Input helper {input_entity} should be referenced"


# =============================================================================
# AUTOMATION COUNT AND COMPLETENESS
# =============================================================================

class TestAutomationCompleteness:
    """Test that the automation set is complete."""

    def test_minimum_automation_count(self, automations):
        """Should have at least 20 automations for Haiven system."""
        assert len(automations) >= 20, f"Expected at least 20 automations, got {len(automations)}"

    def test_has_morning_monitoring(self, automations):
        """Should have morning activity monitoring."""
        morning_ids = [a['id'] for a in automations if 'morning' in a['id'].lower()]
        assert len(morning_ids) >= 2, "Should have at least 2 morning-related automations"

    def test_has_bedtime_monitoring(self, automations):
        """Should have bedtime monitoring."""
        bedtime_ids = [a['id'] for a in automations if 'bedtime' in a['id'].lower()]
        assert len(bedtime_ids) >= 2, "Should have at least 2 bedtime-related automations"

    def test_has_bathroom_monitoring(self, automations):
        """Should have bathroom night monitoring."""
        bathroom_ids = [a['id'] for a in automations if 'bathroom' in a['id'].lower()]
        assert len(bathroom_ids) >= 4, "Should have at least 4 bathroom-related automations"

    def test_has_care_circle_tracking(self, automations):
        """Should have care circle location tracking."""
        circle_ids = [a['id'] for a in automations if a['alias'].startswith('Circle Tracking:')]
        assert len(circle_ids) >= 3, "Should have at least 3 care circle automations"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# =============================================================================
# BATHROOM ALERT TRIGGERS
# =============================================================================

SCRIPTS_PATH = Path(__file__).parent.parent / "scripts.yaml"


class TestBathroomAlertTriggers:
    """HA names a template entity from its `name`, not its unique_id. Both
    alerts triggered on the unique_id form, which never exists, so neither
    the extended-visit alert nor the no-return alert could ever fire."""

    def _trigger_entities(self, automations, auto_id):
        a = next(a for a in automations if a['id'] == auto_id)
        return [t.get('entity_id') for t in a['triggers']]

    def test_extended_visit_alert_watches_the_real_entity(self, automations):
        assert self._trigger_entities(automations, 'haiven_bathroom_night_extended_alert') == \
            ['binary_sensor.extended_night_bathroom_visit']

    def test_no_return_alert_watches_the_real_entity(self, automations):
        assert self._trigger_entities(automations, 'haiven_bathroom_night_no_return_alert') == \
            ['binary_sensor.no_return_from_bathroom']

    def test_no_return_alert_is_critical(self, automations):
        a = next(a for a in automations if a['id'] == 'haiven_bathroom_night_no_return_alert')
        notify = next(s for s in a['actions'] if s.get('action') == 'script.notify_care_circle')
        assert notify['data'].get('priority') == 'critical'

    def test_notify_script_uses_the_priority_it_is_given(self):
        with open(SCRIPTS_PATH) as f:
            script = yaml.safe_load(f)['notify_care_circle']
        assert 'priority' in script['fields']
        text = yaml.dump(script['sequence'])
        assert 'interruption-level: time-sensitive' not in text, \
            "interruption level is hardcoded, so a critical alert goes out as time-sensitive"


# =============================================================================
# SUMMARY LENGTH
# =============================================================================

class TestSummaryLength:
    """input_text.current_summary holds 255 characters. HA rejects a longer
    value with only a warning, so a summary that notified by reading the
    helper back sent the previous summary instead of the new one."""

    def _walk(self, node):
        if isinstance(node, dict):
            yield node
            for v in node.values():
                yield from self._walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from self._walk(v)

    def test_no_notification_reads_the_summary_helper(self, automations):
        for a in automations:
            for step in self._walk(a.get('actions', [])):
                msg = step.get('data', {}).get('message', '') if isinstance(step.get('data'), dict) else ''
                assert "states('input_text.current_summary')" not in str(msg), a['id']

    def test_summary_writes_fit_the_helper(self, automations, jinja_env):
        writes = [s['data']['value'] for a in automations for s in self._walk(a.get('actions', []))
                  if s.get('action') == 'input_text.set_value'
                  and s.get('target', {}).get('entity_id') == 'input_text.current_summary']
        assert len(writes) >= 4, "morning, afternoon, evening and refresh all write the summary"
        speech = ("word " * 80).strip()  # 399 characters
        for tpl in writes:
            out = jinja_env.from_string(tpl).render(
                composed={'text': speech})
            assert len(out) <= 255


# =============================================================================
# LOCAL-TIME COMPARISONS
# =============================================================================

class TestLocalTimeComparisons:
    """last_triggered and last_changed are UTC; now() is local. Comparing an
    unconverted UTC date against now().date() reads "yesterday" for anything
    that happened in the first hour after local midnight during summer time,
    so a restart re-ran the daily reset and wiped that day's wake time."""

    @pytest.fixture
    def text(self):
        return AUTOMATIONS_PATH.read_text()

    def test_no_utc_calendar_reads(self, text):
        bad = re.findall(r"as_datetime\(\w+\)\.(?:date\(\)|hour|strftime)", text)
        assert not bad, f"read the local date/hour: (as_datetime(x) | as_local) - {bad}"

    def test_no_utc_last_changed_formatting(self, text):
        bad = re.findall(r"last_changed\.strftime", text)
        assert not bad, "last_changed is UTC; format (x | as_local)"

    def test_once_a_day_guards_are_local(self, automations):
        guards = [c['value_template'] for a in automations for c in a.get('conditions', [])
                  if isinstance(c, dict) and 'last_triggered' in str(c.get('value_template', ''))
                  and '.date()' in str(c.get('value_template', ''))]
        assert len(guards) >= 10
        for g in guards:
            assert 'as_local' in g, g


# =============================================================================
# RESTART AND RELOAD ARTEFACTS
# =============================================================================

class TestKitchenRestartArtefacts:
    """An entity goes unavailable -> value on every restart and a template
    sensor unknown -> value on every reload. Kitchen-triggered automations
    that checked only to_state counted each restart as kitchen activity:
    a block on the timeline, a bump to the daily counter, the manual safe
    flag cleared, and inside the morning window a wake time."""

    GUARD = ("trigger.from_state is not none", "trigger.from_state.state not in",
             "trigger.to_state.state != trigger.from_state.state")

    def test_kitchen_triggers_need_a_real_change(self, automations):
        kitchen = [a for a in automations
                   if any('event.kitchen_motion' in str(t.get('entity_id', '')) for t in a['triggers'])]
        assert len(kitchen) >= 6
        for a in kitchen:
            text = yaml.dump(a.get('conditions', []), width=1000)
            for part in self.GUARD:
                assert part in text, f"{a['id']} lacks '{part}'"


# =============================================================================
# OVERNIGHT ALERT NOISE
# =============================================================================

class TestOvernightNoise:
    """Overnight pushes that carried nothing true: a one-second reload
    artefact scored critical, a normal night's sleep climbed the inactivity
    ladder to "Needs Attention", and a restart self-test pushed a green tick
    at time-sensitive."""

    def _auto(self, automations, auto_id):
        return next(a for a in automations if a['id'] == auto_id)

    def test_status_change_must_hold(self, automations):
        trig = self._auto(automations, 'haiven_status_change')['triggers'][0]
        h, m, s = (int(x) for x in str(trig.get('for', '0:0:0')).split(':'))
        assert h * 3600 + m * 60 + s >= 120

    def test_status_change_quiet_while_asleep(self, automations):
        conds = yaml.dump(self._auto(automations, 'haiven_status_change')['conditions'], width=1000)
        assert 'binary_sensor.night_window_active' in conds
        assert 'input_number.no_activity_alert_hours' in conds

    def test_status_change_reads_the_triggering_state(self, automations):
        msg = self._auto(automations, 'haiven_status_change')['actions'][0]['data']['message']
        assert "state_attr('sensor.elderly_care_status'" not in msg
        assert 'trigger.to_state' in msg

    def test_passing_health_check_does_not_push(self, automations):
        choose = next(s for s in self._auto(automations, 'haiven_new_sensors_health_check')['actions']
                      if 'choose' in s)
        assert all(s.get('action') != 'script.send_haiven_notification' for s in choose['default'])


class TestArrivalCountsAsActivity:
    """Coming home is activity. Without it, a two-hour trip out reads as two
    hours of silence the moment the person walks back in, scores as an
    inactivity gap plus a room transition timeout, and pushes "Needs
    Attention" while they are standing in the kitchen."""

    SENSORS_PATH = Path(__file__).parent.parent / "haiven_sensors_3sensor.yaml"

    def _sensors(self):
        with open(self.SENSORS_PATH) as f:
            text = f.read()
        return text, yaml.safe_load(text)

    def test_arrival_records_the_time(self, automations):
        auto = next(a for a in automations if a['id'] == 'haiven_log_person_location')
        steps = auto['actions'] + [s for a in auto['actions'] for s in a.get('then', [])]
        sets = [s for s in steps
                if s.get('action') == 'input_datetime.set_datetime'
                and s.get('target', {}).get('entity_id') == 'input_datetime.arrived_home']
        assert len(sets) == 1
        assert "trigger.to_state.state == 'home'" in str(auto['actions'])

    def test_every_inactivity_gap_includes_arrival(self):
        text, _ = self._sensors()
        gaps = text.count("{% set bathroom_mins = states('sensor.minutes_since_bathroom_activity') | int(9999) %}")
        arrivals = text.count("{% set arrived_mins = states('sensor.minutes_since_arrived_home') | int(9999) %}")
        assert gaps == 4
        assert arrivals == gaps
        assert text.count("[kitchen_mins, bedroom_mins, bathroom_mins, arrived_mins] | min") == gaps

    def test_minutes_since_arrival_renders(self, jinja_env):
        _, data = self._sensors()
        sensor = next(s for block in data['template'] for s in block.get('sensor', [])
                      if s.get('unique_id') == 'minutes_since_arrived_home')
        now_ts = 1_000_000.0
        now = MagicMock(); now.timestamp.return_value = now_ts
        render = lambda ts: jinja_env.from_string(sensor['state']).render(
            state_attr=lambda e, a: ts if e == 'input_datetime.arrived_home' else None,
            now=lambda: now).strip()
        assert render(now_ts - 120) == '2'
        assert render(None) == 'unknown'

    def test_no_activity_alert_counts_arrival(self, automations, jinja_env):
        auto = next(a for a in automations if a['id'] == 'haiven_no_activity_alert')
        tpl = next(c['value_template'] for c in auto['conditions']
                   if c.get('alias') == 'No activity for threshold hours')
        def render(hours, arrived_mins):
            vals = {'input_number.no_activity_alert_hours': '3',
                    'sensor.minutes_since_arrived_home': arrived_mins}
            return jinja_env.from_string(tpl).render(
                states=lambda e: vals.get(e, 'unknown'),
                state_attr=lambda e, a: hours).strip()
        assert render(4.0, '5') == 'False'
        assert render(4.0, '300') == 'True'
        assert render(4.0, 'unknown') == 'True'

    def test_phone_flap_is_not_an_arrival(self, automations, jinja_env):
        """A GPS flap while the person is indoors must not reset the silence clock."""
        auto = next(a for a in automations if a['id'] == 'haiven_log_person_location')
        tpl = next(a for a in auto['actions'] if 'if' in a)['if'][0]['value_template']
        t0 = datetime(2026, 1, 1, 10, 0)
        def render(away_mins, frm='not_home'):
            trig = {'from_state': MagicMock(state=frm, last_changed=t0),
                    'to_state': MagicMock(state='home', last_changed=t0 + timedelta(minutes=away_mins))}
            return jinja_env.from_string(tpl).render(trigger=trig).strip()
        assert render(120) == 'True'
        assert render(3) == 'False'
        assert render(120, frm='unavailable') == 'False'


class TestConfigurableWindows:
    """Bedtime and wake detection read their windows from helpers."""

    def test_no_hard_coded_evening_hours_remain(self, automations):
        auto = next(a for a in automations if a['id'] == 'haiven_bedtime_confirmation_v2')
        text = str(auto)
        assert 'hour >= 17' not in text
        assert 'sensor.bedtime_window' in text

    def test_bedtime_condition_follows_the_window(self, automations, jinja_env):
        auto = next(a for a in automations if a['id'] == 'haiven_bedtime_confirmation_v2')
        tpl = next(c['value_template'] for c in auto['conditions']
                   if c.get('alias') == 'Bathroom time is inside the bedtime window')
        def render(bath_time, window):
            return jinja_env.from_string(tpl).render(
                states=lambda e: window,
                state_attr=lambda e, a: bath_time).strip()
        assert render('22:20', '20:30-01:30') == 'True'
        assert render('00:40', '20:30-01:30') == 'True'
        assert render('18:00', '20:30-01:30') == 'False'
        assert render('18:00', '17:30-21:00') == 'True'

    def test_catchup_also_runs_when_the_morning_window_closes(self, automations):
        auto = next(a for a in automations if a['id'] == 'haiven_wake_time_catchup')
        assert any(t.get('entity_id') == 'binary_sensor.morning_window_active' and t.get('to') == 'off'
                   for t in auto['triggers'])
        assert 'sensor.wake_window_start' in str(auto['conditions'])


class TestAiIsOptional:
    """AI wording is off by default. Every summary and alert must be a
    complete message without it, and must still send if the AI call fails:
    before this, a failed call meant the no-activity alert never went out."""

    SCRIPTS_PATH = Path(__file__).parent.parent / "scripts.yaml"
    AI_AUTOMATIONS = ['haiven_morning_summary', 'haiven_afternoon_summary', 'haiven_evening_summary',
                      'haiven_refresh_summary', 'haiven_morning_activity_check', 'haiven_no_activity_alert']

    def _walk(self, node):
        if isinstance(node, dict):
            yield node
            for v in node.values():
                yield from self._walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from self._walk(v)

    def _script(self):
        with open(self.SCRIPTS_PATH) as f:
            return yaml.safe_load(f)['haiven_compose_message']

    def test_no_automation_calls_the_ai_agent_directly(self, automations):
        for a in automations:
            for step in self._walk(a.get('actions', [])):
                assert step.get('action') != 'conversation.process', a['id']

    @pytest.mark.parametrize("auto_id", AI_AUTOMATIONS)
    def test_each_message_has_a_plain_version(self, automations, jinja_env, auto_id):
        auto = next(a for a in automations if a['id'] == auto_id)
        calls = [s for s in self._walk(auto['actions']) if s.get('action') == 'script.haiven_compose_message']
        assert len(calls) == 1
        assert calls[0]['response_variable'] == 'composed'
        plain = jinja_env.from_string(calls[0]['data']['plain']).render(
            states=lambda e: {'sensor.today_wake_time': '07:10', 'sensor.last_activity_time': '09:40',
                              'sensor.activity_data': 'Kitchen', 'sensor.sensor_health_status': 'All online',
                              'input_text.elderly_person_name': 'Mary',
                              'input_datetime.expected_wake_time': '07:00:00'}.get(e, '2'),
            state_attr=lambda e, a: 4.2,
            is_state=lambda e, v: False).strip()
        assert len(plain) > 20 and '{' not in plain
        assert 'unknown' not in plain

    def test_away_is_said_plainly(self, automations, jinja_env):
        auto = next(a for a in automations if a['id'] == 'haiven_morning_summary')
        call = next(s for s in self._walk(auto['actions']) if s.get('action') == 'script.haiven_compose_message')
        plain = jinja_env.from_string(call['data']['plain']).render(
            states=lambda e: 'Mary', state_attr=lambda e, a: None,
            is_state=lambda e, v: e == 'binary_sensor.elderly_person_home' and v == 'off').strip()
        assert plain == 'Mary is away from home.'

    def test_ai_is_only_called_behind_the_switch(self):
        seq = self._script()['sequence']
        gate = next(s for s in seq if 'if' in s)
        assert {'condition': 'state', 'entity_id': 'input_boolean.haiven_ai_summaries', 'state': 'on'} in gate['if']
        ai_calls = [s for s in self._walk(seq) if s.get('action') == 'conversation.process']
        assert len(ai_calls) == 1
        assert ai_calls[0] in gate['then'], "the AI call must sit inside the switch"

    def test_a_failed_ai_call_cannot_stop_the_message(self):
        seq = self._script()['sequence']
        call = next(s for s in self._walk(seq) if s.get('action') == 'conversation.process')
        assert call.get('continue_on_error') is True
        assert seq[-1].get('response_variable') == 'result', "falls through to the plain text"
        assert seq[0]['variables']['result']['text'] == "{{ plain | trim }}"

    def test_the_switch_has_no_initial_so_it_starts_off(self):
        path = Path(__file__).parent.parent / "packages" / "haiven_comms_inputs.yaml"
        with open(path) as f:
            helper = yaml.safe_load(f)['input_boolean']['haiven_ai_summaries']
        assert 'initial' not in helper


class TestNoFallOrClinicalClaims:
    """Haiven measures time and movement. It does not detect falls and does
    not suggest causes."""

    FILES = ["automations.yaml", "configuration.yaml", "scripts.yaml", "lovelace/haiven_default.yaml",
             "packages/haiven_drift.yaml", "packages/haiven_bathroom_night.yaml",
             "packages/haiven_night_insights.yaml"]

    @pytest.mark.parametrize("name", FILES)
    def test_wording(self, name):
        text = (Path(__file__).parent.parent / name).read_text().lower()
        for phrase in ("possible fall", "possible_fall", "medical emergency", "water infection",
                       "gp call", "under the weather", "steady on her feet"):
            assert phrase not in text, phrase


class TestFaultAlerts:
    """A sensor, a battery or the hub stopping must reach the carers, and
    must not depend on monitoring being switched on."""

    ROOT = Path(__file__).parent.parent
    FAULTS = ['haiven_fault_sensor_offline', 'haiven_fault_low_battery']

    def _scripts(self):
        with open(self.ROOT / "scripts.yaml") as f:
            return yaml.safe_load(f)

    @pytest.mark.parametrize("auto_id", FAULTS + ['haiven_hub_heartbeat'])
    def test_not_gated_on_monitoring(self, automations, auto_id):
        auto = next(a for a in automations if a['id'] == auto_id)
        assert 'haiven_monitoring_enabled' not in str(auto)

    @pytest.mark.parametrize("auto_id", FAULTS)
    def test_repeats_each_morning_while_the_fault_lasts(self, automations, auto_id):
        auto = next(a for a in automations if a['id'] == auto_id)
        assert any(t.get('trigger') == 'time' for t in auto['triggers'])
        assert auto['conditions'], "the morning repeat must re-check the fault"

    @pytest.mark.parametrize("auto_id", FAULTS + ['haiven_fault_sensor_back'])
    def test_uses_the_fault_notifier(self, automations, auto_id):
        auto = next(a for a in automations if a['id'] == auto_id)
        assert [a['action'] for a in auto['actions']] == ['script.haiven_notify_fault']

    def test_fault_notifier_cannot_silence_a_routine_alert(self):
        """notify_care_circle sets deviation_alert_sent and offers Mark Safe.
        A fault alert doing either would suppress the next real alert."""
        text = str(self._scripts()['haiven_notify_fault'])
        assert 'deviation_alert_sent' not in text
        assert 'MARK_SAFE' not in text
        assert 'contact_1_notification' in text and 'contact_2_notification' in text

    def test_heartbeat_needs_a_url_and_survives_a_failed_request(self, automations):
        auto = next(a for a in automations if a['id'] == 'haiven_hub_heartbeat')
        assert "startswith('http')" in str(auto['conditions'])
        call = auto['actions'][0]
        assert call['action'] == 'rest_command.haiven_heartbeat'
        assert call.get('continue_on_error') is True

    def test_heartbeat_sends_no_data(self):
        with open(self.ROOT / "packages" / "haiven_faults.yaml") as f:
            cmd = yaml.safe_load(f)['rest_command']['haiven_heartbeat']
        assert cmd['method'] == 'get'
        assert 'payload' not in cmd and 'headers' not in cmd

    def test_watchdog_url_is_kept_out_of_the_recorder(self):
        text = (self.ROOT / "configuration.yaml").read_text()
        assert '- input_text.haiven_heartbeat_url' in text


class TestHoldingAlertsBack:
    """Visitor present and calibration quieten alerts; they never drop one,
    never touch fault alerts, and cannot be left on."""

    ROOT = Path(__file__).parent.parent

    def _pkg(self):
        with open(self.ROOT / "packages" / "haiven_pause.yaml") as f:
            return yaml.safe_load(f)

    def _scripts(self):
        with open(self.ROOT / "scripts.yaml") as f:
            return yaml.safe_load(f)

    def test_held_alerts_are_still_sent(self):
        for name in ('send_haiven_notification', 'notify_care_circle'):
            text = str(self._scripts()[name])
            assert 'haiven_alerts_held' in text
            assert "'passive' if held" in text, f"{name} must downgrade, not skip"
        # the first contact is always notified: no `held` in its condition
        seq = self._scripts()['send_haiven_notification']['sequence']
        assert seq[-1]['action'] == "{{ states('input_text.contact_1_notification') }}"

    def test_a_held_alert_is_not_marked_as_sent(self):
        seq = self._scripts()['notify_care_circle']['sequence']
        flag = next(s for s in seq if 'if' in s and 'deviation_alert_sent' in str(s))
        assert 'not held' in str(flag['if'])

    def test_critical_alerts_are_only_held_while_calibrating(self):
        held = self._scripts()['notify_care_circle']['sequence'][0]['variables']['held']
        assert "'calibrating') == true" in held and "!= 'critical'" in held

    def test_fault_alerts_are_never_held(self):
        assert 'haiven_alerts_held' not in str(self._scripts()['haiven_notify_fault'])

    def test_the_pause_ends_on_the_clock(self):
        sensor = self._pkg()['template'][0]['binary_sensor'][0]
        assert sensor['unique_id'] == 'haiven_alerts_held'
        assert 'haiven_visitor_until' in sensor['state'] and 'haiven_calibration_until' in sensor['state']
        assert 'as_timestamp(now())' in sensor['state']

    def test_visitor_time_is_bounded(self):
        hours = self._pkg()['input_number']['haiven_visitor_hours']
        assert hours['min'] >= 1 and hours['max'] <= 12
        assert '7 * 86400' in str(self._pkg()['script']['haiven_start_calibration'])

    def test_helpers_have_no_initial_so_nothing_is_held_on_a_fresh_install(self):
        pkg = self._pkg()
        for group in ('input_boolean', 'input_datetime'):
            for name, helper in pkg[group].items():
                assert 'initial' not in helper, name

    def test_visits_are_logged(self, automations):
        auto = next(a for a in automations if a['id'] == 'haiven_visitor_log')
        assert any(a.get('action') == 'shell_command.log_haiven_event' for a in auto['actions'])
