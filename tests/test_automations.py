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
        'input_text.elderly_person_name': 'Mum',
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
    the extended-visit alert nor the possible-fall alert could ever fire."""

    def _trigger_entities(self, automations, auto_id):
        a = next(a for a in automations if a['id'] == auto_id)
        return [t.get('entity_id') for t in a['triggers']]

    def test_extended_visit_alert_watches_the_real_entity(self, automations):
        assert self._trigger_entities(automations, 'haiven_bathroom_night_extended_alert') == \
            ['binary_sensor.extended_night_bathroom_visit']

    def test_possible_fall_alert_watches_the_real_entity(self, automations):
        assert self._trigger_entities(automations, 'haiven_bathroom_night_no_return_alert') == \
            ['binary_sensor.no_return_from_bathroom_possible_fall']

    def test_possible_fall_alert_is_critical(self, automations):
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
                ai_response={'response': {'speech': {'plain': {'speech': speech}}}})
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
