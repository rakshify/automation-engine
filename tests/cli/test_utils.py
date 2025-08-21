import pytest
from unittest.mock import patch, MagicMock
from src.cli.utils import (
    ask_question, ask_yes_no, display_choices, get_choice,
    validate_workflow_name, get_valid_workflow_name, format_dict,
    select_slack_channel, print_separator, print_header
)

# Mock Slack component for select_slack_channel tests
class MockSlackComponent:
    def __init__(self):
        self.channels = [
            {'id': 'C1', 'name': '#general'},
            {'id': 'C2', 'name': '#random'}
        ]

    def get_channels(self):
        return self.channels

@pytest.fixture
def mock_slack_component():
    return MockSlackComponent()

def test_ask_question_with_default():
    with patch('builtins.input', return_value=""):
        assert ask_question("Prompt:", "default_value") == "default_value"

def test_ask_question_with_input():
    with patch('builtins.input', return_value="user_input"):
        assert ask_question("Prompt:") == "user_input"

def test_ask_yes_no_yes():
    with patch('builtins.input', return_value="y"):
        assert ask_yes_no("Confirm?") is True
    with patch('builtins.input', return_value="Y"):
        assert ask_yes_no("Confirm?") is True

def test_ask_yes_no_no():
    with patch('builtins.input', return_value="n"):
        assert ask_yes_no("Confirm?") is False
    with patch('builtins.input', return_value="N"):
        assert ask_yes_no("Confirm?") is False

def test_ask_yes_no_default_true():
    with patch('builtins.input', return_value=""):
        assert ask_yes_no("Confirm?", default=True) is True

def test_ask_yes_no_default_false():
    with patch('builtins.input', return_value=""):
        assert ask_yes_no("Confirm?", default=False) is False

def test_display_choices_numbered(capsys):
    display_choices("Options:", ["opt1", "opt2"])
    captured = capsys.readouterr()
    assert "1. opt1" in captured.out
    assert "2. opt2" in captured.out

def test_display_choices_unnumbered(capsys):
    display_choices("Options:", ["opt1", "opt2"], numbered=False)
    captured = capsys.readouterr()
    assert "- opt1" in captured.out
    assert "- opt2" in captured.out

def test_get_choice_valid():
    with patch('builtins.input', return_value="1"):
        assert get_choice(["opt1", "opt2"]) == 0

def test_get_choice_invalid_then_valid(capsys):
    with patch('builtins.input', side_effect=["invalid", "3", "2"]):
        assert get_choice(["opt1", "opt2"]) == 1
        captured = capsys.readouterr()
        assert "Please enter a valid number" in captured.out
        assert "Please enter a number between 1 and 2" in captured.out

def test_validate_workflow_name():
    assert validate_workflow_name("valid_name") is True
    assert validate_workflow_name("another-name-123") is True
    assert validate_workflow_name("") is False
    assert validate_workflow_name("name with spaces") is False
    assert validate_workflow_name("name!@#") is False
    assert validate_workflow_name("a" * 51) is False

def test_get_valid_workflow_name_new():
    with patch('builtins.input', return_value="new_workflow"):
        with patch('src.cli.utils.ask_question', return_value="new_workflow"):
            assert get_valid_workflow_name([]) == "new_workflow"

def test_get_valid_workflow_name_overwrite():
    with patch('builtins.input', return_value="existing_workflow"):
        with patch('src.cli.utils.ask_question', return_value="existing_workflow"):
            with patch('src.cli.utils.ask_yes_no', return_value=True):
                assert get_valid_workflow_name(["existing_workflow"]) == "existing_workflow"

def test_get_valid_workflow_name_invalid_then_valid():
    with patch('builtins.input', side_effect=["invalid name", "valid_name"]):
        with patch('src.cli.utils.ask_question', side_effect=["invalid name", "valid_name"]):
            assert get_valid_workflow_name([]) == "valid_name"

def test_format_dict_basic():
    data = {"key1": "value1", "key2": 123}
    formatted = format_dict(data)
    assert "key1: value1" in formatted
    assert "key2: 123" in formatted

def test_format_dict_nested():
    data = {"key1": {"nested_key": "nested_value"}, "key2": "value2"}
    formatted = format_dict(data)
    assert "key1:" in formatted
    assert "  nested_key: nested_value" in formatted
    assert "key2: value2" in formatted

def test_format_dict_list():
    data = {"key1": [1, 2, 3]}
    formatted = format_dict(data)
    assert "key1: [1, 2, 3]" in formatted

def test_select_slack_channel_select_existing(mock_slack_component):
    with patch('src.cli.utils.ask_question'), \
         patch('src.cli.utils.display_choices'), \
         patch('src.cli.utils.get_choice', return_value=0):
        channel = select_slack_channel(mock_slack_component)
        assert channel == "C1"

def test_select_slack_channel_manual_entry(mock_slack_component):
    with patch('src.cli.utils.ask_question', side_effect=["manual_channel_id"]) as mock_ask_question, \
         patch('src.cli.utils.display_choices') as mock_display_choices, \
         patch('src.cli.utils.get_choice', return_value=3) as mock_get_choice:
        channel = select_slack_channel(mock_slack_component)
        assert channel == "{{manual_channel_id}}"
        mock_ask_question.assert_called_once_with("Enter channel ID or name")
        mock_display_choices.assert_called_once()
        mock_get_choice.assert_called_once()

def test_select_slack_channel_from_context(mock_slack_component):
    with patch('src.cli.utils.ask_question', side_effect=["my_channel_var"]) as mock_ask_question, \
         patch('src.cli.utils.display_choices') as mock_display_choices, \
         patch('src.cli.utils.get_choice', return_value=len(mock_slack_component.channels)) as mock_get_choice:
        channel = select_slack_channel(mock_slack_component)
        assert channel == "{{my_channel_var}}"
        mock_ask_question.assert_called_once_with("Enter context placeholder (e.g., channel_name, target_channel)")
        mock_display_choices.assert_called_once()
        mock_get_choice.assert_called_once()

def test_print_separator(capsys):
    print_separator("=", 10)
    captured = capsys.readouterr()
    assert captured.out.strip() == "=========="

def test_print_header(capsys):
    print_header("Test Header")
    captured = capsys.readouterr()
    assert "==========" in captured.out
    assert " Test Header " in captured.out
