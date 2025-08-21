import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import json
from pathlib import Path

# Mock external dependencies and internal modules
class MockUser:
    def __init__(self, user_id="test_user"):
        self.user_id = user_id

class MockDatastore:
    def __init__(self):
        self.workflows = {"test_user": {"workflow1": {}, "workflow2": {}}}

    def list_workflows(self, user_id):
        return list(self.workflows.get(user_id, {}).keys())

    def load_workflow(self, user_id, workflow_name):
        return self.workflows.get(user_id, {}).get(workflow_name)

@pytest.fixture
def mock_main_dependencies():
    with patch('src.__main__.get_current_user', return_value=MockUser()), \
         patch('src.__main__.datastore', new=MockDatastore()), \
         patch('src.__main__.create_workflow') as mock_create_workflow, \
         patch('src.__main__.execute_workflow') as mock_execute_workflow, \
         patch('src.__main__.interactive_execute_workflow') as mock_interactive_execute_workflow, \
         patch('src.__main__.get_user_choice') as mock_get_user_choice, \
         patch('src.__main__.show_workflow_details') as mock_show_workflow_details, \
         patch('src.__main__.set_logging_context'), \
         patch('src.__main__.setup_context_filter'), \
         patch('src.__main__.print_header'), \
         patch('src.__main__.display_choices'), \
         patch('src.__main__.get_choice') as mock_get_choice, \
         patch('src.__main__.ask_yes_no') as mock_ask_yes_no, \
         patch('src.__main__.input') as mock_input, \
         patch('src.__main__.logger') as mock_logger, \
         patch('os.chdir') as mock_chdir, \
         patch('sys.exit') as mock_sys_exit:
        yield {
            "create_workflow": mock_create_workflow,
            "execute_workflow": mock_execute_workflow,
            "interactive_execute_workflow": mock_interactive_execute_workflow,
            "get_user_choice": mock_get_user_choice,
            "show_workflow_details": mock_show_workflow_details,
            "get_choice": mock_get_choice,
            "ask_yes_no": mock_ask_yes_no,
            "input": mock_input,
            "logger": mock_logger,
            "chdir": mock_chdir,
            "sys_exit": mock_sys_exit,
            "datastore": MockDatastore()
        }

@pytest.fixture(autouse=True)
def mock_logging_config_file(tmp_path):
    # Create a dummy logging config file
    config_data = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simpleFormatter": {"format": "% (message)s"}},
        "handlers": {"consoleHandler": {"class": "logging.StreamHandler", "formatter": "simpleFormatter"}},
        "root": {"level": "INFO", "handlers": ["consoleHandler"]}
    }
    config_file = tmp_path / "configs" / "logging_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    
    with patch('src.__main__.Path', wraps=Path) as mock_path:
        mock_path.return_value = config_file
        yield

def test_setup_logging_success(mock_main_dependencies, mock_logging_config_file):
    from src.__main__ import setup_logging
    setup_logging()
    mock_main_dependencies["logger"].info.assert_not_called() # No warning/error if successful

def test_setup_logging_file_not_found(mock_main_dependencies):
    from src.__main__ import setup_logging
    with patch('src.__main__.Path', side_effect=FileNotFoundError):
        setup_logging()
        mock_main_dependencies["logger"].warning.assert_called_with("Logging config file not found, using basic configuration")

def test_show_main_menu_create_workflow(mock_main_dependencies):
    from src.__main__ import show_main_menu
    mock_main_dependencies["get_choice"].side_effect = [0, 3] # Choose create, then exit
    mock_main_dependencies["ask_yes_no"].return_value = True # Confirm exit
    mock_main_dependencies["input"].return_value = "" # Press Enter

    show_main_menu()
    mock_main_dependencies["create_workflow"].assert_called_once()

def test_show_main_menu_execute_workflow(mock_main_dependencies):
    from src.__main__ import show_main_menu
    mock_main_dependencies["get_choice"].side_effect = [1, 3] # Choose execute, then exit
    mock_main_dependencies["ask_yes_no"].return_value = True # Confirm exit
    mock_main_dependencies["input"].return_value = "" # Press Enter

    show_main_menu()
    mock_main_dependencies["interactive_execute_workflow"].assert_called_once()

def test_show_main_menu_list_workflows(mock_main_dependencies):
    from src.__main__ import show_main_menu
    mock_main_dependencies["get_choice"].side_effect = [2, 3] # Choose list, then exit
    mock_main_dependencies["ask_yes_no"].return_value = True # Confirm exit
    mock_main_dependencies["input"].return_value = "" # Press Enter

    show_main_menu()
    # list_workflows is called internally, so we check its side effects or direct calls if it were mocked
    # For now, we'll rely on the overall flow.

def test_show_main_menu_exit(mock_main_dependencies):
    from src.__main__ import show_main_menu
    mock_main_dependencies["get_choice"].return_value = 3 # Choose exit
    mock_main_dependencies["ask_yes_no"].return_value = True # Confirm exit

    show_main_menu()
    mock_main_dependencies["ask_yes_no"].assert_called_once_with("Are you sure you want to exit?", True)

def test_list_workflows_no_workflows(mock_main_dependencies):
    from src.__main__ import list_workflows
    mock_main_dependencies["datastore"].workflows = {"test_user": {}}
    list_workflows()
    mock_main_dependencies["display_choices"].assert_not_called()
    mock_main_dependencies["show_workflow_details"].assert_not_called()

def test_list_workflows_with_details(mock_main_dependencies):
    from src.__main__ import list_workflows
    mock_main_dependencies["ask_yes_no"].return_value = True # View details
    mock_main_dependencies["get_choice"].return_value = 0 # Select first workflow

    list_workflows()
    mock_main_dependencies["show_workflow_details"].assert_called_once_with("workflow1", "test_user")

def test_handle_command_line_execution_execute_specific(mock_main_dependencies):
    from src.__main__ import handle_command_line_execution
    handle_command_line_execution("execute", "workflow1")
    mock_main_dependencies["execute_workflow"].assert_called_once_with("workflow1")

def test_handle_command_line_execution_execute_not_found(mock_main_dependencies):
    from src.__main__ import handle_command_line_execution
    handle_command_line_execution("execute", "non_existent_workflow")
    mock_main_dependencies["logger"].error.assert_called_once_with("Workflow 'non_existent_workflow' not found")
    mock_main_dependencies["sys_exit"].assert_called_once_with(1)

def test_handle_command_line_execution_execute_interactive(mock_main_dependencies):
    from src.__main__ import handle_command_line_execution
    mock_main_dependencies["get_user_choice"].return_value = "workflow1"
    handle_command_line_execution("execute")
    mock_main_dependencies["get_user_choice"].assert_called_once()
    mock_main_dependencies["execute_workflow"].assert_called_once_with("workflow1")

def test_handle_command_line_execution_create(mock_main_dependencies):
    from src.__main__ import handle_command_line_execution
    handle_command_line_execution("create")
    mock_main_dependencies["create_workflow"].assert_called_once()

def test_handle_command_line_execution_list(mock_main_dependencies):
    from src.__main__ import handle_command_line_execution
    handle_command_line_execution("list")
    # list_workflows is called internally, so we check its side effects or direct calls if it were mocked

def test_handle_command_line_execution_unknown_option(mock_main_dependencies):
    from src.__main__ import handle_command_line_execution
    handle_command_line_execution("unknown_option")
    mock_main_dependencies["logger"].error.assert_called_once_with("Unknown menu option: unknown_option")
    mock_main_dependencies["sys_exit"].assert_called_once_with(1)

def test_main_interactive_mode(mock_main_dependencies):
    from src.__main__ import main
    sys.argv = ["src.__main__"]
    mock_main_dependencies["get_choice"].return_value = 3 # Exit immediately
    mock_main_dependencies["ask_yes_no"].return_value = True

    main()
    mock_main_dependencies["interactive_execute_workflow"].assert_not_called() # Should not be called in interactive mode initially
    mock_main_dependencies["chdir"].assert_called_once()

def test_main_command_line_mode(mock_main_dependencies):
    from src.__main__ import main
    sys.argv = ["src.__main__", "create"]

    main()
    mock_main_dependencies["create_workflow"].assert_called_once()
    mock_main_dependencies["chdir"].assert_called_once()

def test_main_fatal_error(mock_main_dependencies):
    from src.__main__ import main
    with patch('src.__main__.setup_logging', side_effect=Exception("Test Fatal Error")):
        main()
        mock_main_dependencies["logger"].critical.assert_called_once_with("Fatal error: Test Fatal Error", exc_info=True)
        mock_main_dependencies["sys_exit"].assert_called_once_with(1)