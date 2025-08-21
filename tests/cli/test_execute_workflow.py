import pytest
from unittest.mock import patch, MagicMock
from src.cli.execute_workflow import (
    get_user_choice, execute_workflow, interactive_execute_workflow,
    _execute_reactive_workflow, _execute_traditional_workflow, show_workflow_details
)
from src.core.workflow import Workflow

# Mock User object
class MockUser:
    def __init__(self, user_id="test_user"):
        self.user_id = user_id

# Mock Datastore
class MockDatastore:
    def __init__(self):
        self.workflows = {"test_user": {"workflow1": {"name": "workflow1", "components": {}},
                                      "workflow2": {"name": "workflow2", "components": {"trigger_1": {"is_trigger": True}}}}}

    def list_workflows(self, user_id):
        return list(self.workflows.get(user_id, {}).keys())

    def load_workflow(self, user_id, workflow_name):
        return self.workflows.get(user_id, {}).get(workflow_name)

@pytest.fixture
def mock_dependencies():
    with patch('src.cli.execute_workflow.get_current_user', return_value=MockUser()), \
         patch('src.cli.execute_workflow.datastore', new=MockDatastore()), \
         patch('src.cli.execute_workflow.Workflow') as MockWorkflow, \
         patch('src.cli.execute_workflow.set_logging_context'), \
         patch('src.cli.execute_workflow.print_header'), \
         patch('src.cli.execute_workflow.print_separator'), \
         patch('src.cli.execute_workflow.format_dict'), \
         patch('src.cli.execute_workflow.logger') as mock_logger:
        yield MockWorkflow, mock_logger

@pytest.fixture
def mock_user_input():
    with patch('src.cli.utils.display_choices') as mock_display_choices, \
         patch('src.cli.utils.get_choice') as mock_get_choice, \
         patch('src.cli.utils.ask_yes_no') as mock_ask_yes_no, \
         patch('builtins.input'):
        yield mock_display_choices, mock_get_choice, mock_ask_yes_no

def test_get_user_choice_success(mock_dependencies, mock_user_input):
    _, mock_logger = mock_dependencies
    mock_display_choices, mock_get_choice, _ = mock_user_input
    mock_get_choice.return_value = 0

    choice = get_user_choice()
    assert choice == "workflow1"
    mock_display_choices.assert_called_once_with("Available Workflows", ["workflow1", "workflow2"])

def test_get_user_choice_no_workflows(mock_dependencies, mock_user_input):
    mock_dependencies[1].datastore.workflows = {"test_user": {}}
    choice = get_user_choice()
    assert choice is None

def test_execute_workflow_traditional_success(mock_dependencies, mock_user_input):
    MockWorkflow, mock_logger = mock_dependencies
    _, _, mock_ask_yes_no = mock_user_input
    mock_ask_yes_no.return_value = True

    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": True, "results": {"comp1": {"output": "data"}}, "context": {"var1": "val1"}}

    execute_workflow("workflow1")

    mock_logger.info.assert_any_call("Executing workflow: workflow1")
    mock_logger.info.assert_any_call("Workflow executed successfully")
    MockWorkflow.assert_called_once_with(MockDatastore().load_workflow("test_user", "workflow1"), "test_user")
    mock_workflow_instance.execute.assert_called_once()

def test_execute_workflow_reactive_success(mock_dependencies, mock_user_input):
    MockWorkflow, mock_logger = mock_dependencies
    _, _, mock_ask_yes_no = mock_user_input
    mock_ask_yes_no.return_value = True

    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": True}

    with patch('time.sleep') as mock_sleep:
        mock_sleep.side_effect = KeyboardInterrupt # Simulate interruption after one sleep
        execute_workflow("workflow2")

    mock_logger.info.assert_any_call("Starting reactive workflow: workflow2")
    mock_logger.info.assert_any_call("Stopping reactive workflow")
    mock_workflow_instance.execute.assert_called_once()
    mock_workflow_instance.cleanup.assert_called_once()

def test_execute_workflow_not_found(mock_dependencies):
    _, mock_logger = mock_dependencies
    execute_workflow("non_existent_workflow")
    mock_logger.error.assert_called_once_with("Workflow 'non_existent_workflow' not found")

def test_execute_workflow_execution_failed(mock_dependencies, mock_user_input):
    MockWorkflow, mock_logger = mock_dependencies
    _, _, mock_ask_yes_no = mock_user_input
    mock_ask_yes_no.return_value = True

    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": False, "error": "Test Error", "context": {"var1": "val1"}}

    execute_workflow("workflow1")
    mock_logger.error.assert_called_once_with("Workflow execution failed: Test Error")

def test_interactive_execute_workflow_success(mock_dependencies, mock_user_input):
    mock_display_choices, mock_get_choice, mock_ask_yes_no = mock_user_input
    mock_get_choice.return_value = 0
    mock_ask_yes_no.return_value = True

    mock_workflow_instance = mock_dependencies[0].return_value
    mock_workflow_instance.execute.return_value = {"success": True}

    interactive_execute_workflow()
    mock_get_choice.assert_called_once()
    mock_workflow_instance.execute.assert_called_once()

def test_interactive_execute_workflow_no_choice(mock_dependencies, mock_user_input):
    mock_dependencies[1].datastore.workflows = {"test_user": {}}
    interactive_execute_workflow()
    # No workflow selected, so execute_workflow should not be called
    mock_dependencies[0].assert_not_called()

def test_execute_reactive_workflow_failure(mock_dependencies):
    MockWorkflow, mock_logger = mock_dependencies
    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": False, "error": "Failed to start"}

    _execute_reactive_workflow(mock_workflow_instance, "workflow_reactive")
    mock_logger.error.assert_called_once_with("Failed to start reactive workflow: Failed to start")

def test_execute_traditional_workflow_no_results(mock_dependencies):
    MockWorkflow, mock_logger = mock_dependencies
    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": True, "results": {}, "context": {}}

    _execute_traditional_workflow(mock_workflow_instance)
    mock_logger.info.assert_called_once_with("Workflow executed successfully")

def test_show_workflow_details(mock_dependencies):
    _, mock_logger = mock_dependencies
    show_workflow_details("workflow1", "test_user")
    mock_logger.info.assert_not_called() # show_workflow_details does not log info

def test_execute_workflow_auto_confirm_traditional(mock_dependencies, mock_user_input):
    MockWorkflow, mock_logger = mock_dependencies
    _, _, mock_ask_yes_no = mock_user_input
    mock_ask_yes_no.return_value = False # Should not be called due to auto_confirm

    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": True}

    execute_workflow("workflow1", auto_confirm=True)
    mock_ask_yes_no.assert_not_called()
    mock_workflow_instance.execute.assert_called_once()

def test_execute_workflow_auto_confirm_reactive(mock_dependencies, mock_user_input):
    MockWorkflow, mock_logger = mock_dependencies
    _, _, mock_ask_yes_no = mock_user_input
    mock_ask_yes_no.return_value = False # Should be called for reactive workflow even with auto_confirm

    mock_workflow_instance = MockWorkflow.return_value
    mock_workflow_instance.execute.return_value = {"success": True}

    with patch('time.sleep') as mock_sleep:
        mock_sleep.side_effect = KeyboardInterrupt
        execute_workflow("workflow2", auto_confirm=True)

    mock_ask_yes_no.assert_not_called()
    mock_workflow_instance.execute.assert_called_once()