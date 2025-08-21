import pytest
from unittest.mock import MagicMock, patch
from src.components.formatter import Formatter, TextAction, NumberAction
from src.core.context import WorkflowContext

@pytest.fixture
def mock_context():
    return MagicMock(spec=WorkflowContext)

@pytest.fixture
def formatter_component():
    return Formatter("test_formatter")

class TestFormatter:
    def test_setup(self, formatter_component):
        # setup method does nothing, so just ensure it runs without error
        formatter_component.setup({"key": "value"})
        assert True

class TestTextAction:
    def test_get_field_choices(self):
        field_config_with_choices = {'choices': ['choice1', 'choice2']}
        assert TextAction.get_field_choices("operation", field_config_with_choices) == ['choice1', 'choice2']

        field_config_no_choices = {}
        assert TextAction.get_field_choices("operation", field_config_no_choices) == []

    def test_execute_urlencode(self, formatter_component, mock_context):
        action = TextAction(formatter_component, {'operation': 'urlencode', 'input': 'hello world'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == 'hello%20world'
        assert result['success'] is True

    def test_execute_replace(self, formatter_component, mock_context):
        action = TextAction(formatter_component, {'operation': 'replace', 'input': 'hello world', 'old_value': 'world', 'new_value': 'there'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == 'hello there'
        assert result['success'] is True

        action = TextAction(formatter_component, {'operation': 'replace', 'input': 'banana', 'old_value': 'a', 'new_value': 'o'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == 'bonono'

        action = TextAction(formatter_component, {'operation': 'replace', 'input': 'test', 'old_value': 'xyz', 'new_value': 'abc'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == 'test'

    def test_execute_strip_prefix(self, formatter_component, mock_context):
        action = TextAction(formatter_component, {'operation': 'strip_prefix', 'input': 'prefix_text', 'prefix': 'prefix_'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == 'text'
        assert result['success'] is True

        action = TextAction(formatter_component, {'operation': 'strip_prefix', 'input': 'no_prefix_text', 'prefix': 'prefix_'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == 'no_prefix_text'

        action = TextAction(formatter_component, {'operation': 'strip_prefix', 'input': 'partial_prefix_text', 'prefix': 'partial'})
        result = action.execute(mock_context)
        assert result['formatted_text'] == '_prefix_text'

    def test_execute_unknown_operation(self, formatter_component, mock_context):
        action = TextAction(formatter_component, {'operation': 'unknown', 'input': 'test'})
        with pytest.raises(ValueError, match="Unknown text operation: unknown"):
            action.execute(mock_context)

class TestNumberAction:
    def test_get_field_choices(self):
        field_config_with_choices = {'choices': ['choice1', 'choice2']}
        assert NumberAction.get_field_choices("operation", field_config_with_choices) == ['choice1', 'choice2']

        field_config_no_choices = {}
        assert NumberAction.get_field_choices("operation", field_config_no_choices) == []

    @pytest.mark.parametrize("amount, currency, expected", [
        ("1234.56", "USD", "$1,234.56"),
        (1234.56, "EUR", "€1,234.56"),
        (1234, "GBP", "£1,234.00"),
        ("100", "JPY", "100.00 JPY"),
        ("invalid", "USD", "$0.00"),
        (None, "USD", "$0.00"),
    ])
    def test_execute_format_currency(self, formatter_component, mock_context, amount, currency, expected):
        action = NumberAction(formatter_component, {'operation': 'format_currency', 'amount': amount, 'currency': currency})
        result = action.execute(mock_context)
        assert result['formatted_number'] == expected
        assert result['success'] is True

    @pytest.mark.parametrize("min_val, max_val, expected_range", [
        (1, 10, (1, 10)),
        (0, 0, (0, 0)),
        ("5", "5", (5, 5)),
        ("invalid", "invalid", (0, 100)),
        (None, None, (0, 100)),
    ])
    def test_execute_random_number(self, formatter_component, mock_context, min_val, max_val, expected_range):
        with patch('random.randint') as mock_randint:
            mock_randint.return_value = expected_range[0] # Always return min for deterministic test
            action = NumberAction(formatter_component, {'operation': 'random_number', 'min_value': min_val, 'max_value': max_val})
            result = action.execute(mock_context)
            assert int(result['formatted_number']) == expected_range[0]
            assert result['success'] is True
            mock_randint.assert_called_once_with(expected_range[0], expected_range[1])

    def test_execute_unknown_operation(self, formatter_component, mock_context):
        action = NumberAction(formatter_component, {'operation': 'unknown'})
        with pytest.raises(ValueError, match="Unknown number operation: unknown"):
            action.execute(mock_context)