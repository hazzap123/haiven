"""
Tests for Haiven Home Assistant automations.

Tests YAML syntax, Jinja2 template logic, and automation structure.
Run with: pytest tests/test_automations.py -v
"""

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
            'haiven_evening_report',
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
            'haiven_evening_report',
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
        """Alert automations should fire only once per day."""
        should_be_once_daily = [
            'haiven_morning_activity_check',
            'haiven_no_activity_alert',
            'haiven_bedtime_confirmation_v2',
            'haiven_evening_report',
        ]

        for auto in automations:
            if auto['id'] in should_be_once_daily:
                conditions = auto.get('conditions', [])
                conditions_text = yaml.dump(conditions)
                has_once_daily = (
                    'last_triggered' in conditions_text or
                    'as_datetime(last).date()' in conditions_text
                )
                assert has_once_daily, f"'{auto['alias']}' should have once-per-day condition"

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
                    'script.notify_care_circle' in actions_text
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
        """Non-urgent notifications should use passive interruption level."""
        passive_ids = [
            'haiven_morning_activity_confirmation',
            'haiven_evening_report',
        ]

        for auto in automations:
            if auto['id'] in passive_ids:
                actions_text = yaml.dump(auto.get('actions', []))
                if 'interruption-level' in actions_text:
                    assert 'passive' in actions_text, \
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
        circle_ids = [a['id'] for a in automations if 'circle' in a['id'].lower() or 'contact' in a['id'].lower()]
        assert len(circle_ids) >= 3, "Should have at least 3 care circle automations"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
