import pytest
from unittest.mock import patch, MagicMock
from src.cli.create_workflow import create_workflow, configure_event_trigger, configure_component, handle_component_setup, configure_action, configure_output_mapping
from src.core.workflow import Workflow
from src.core.component import BaseComponent
from src.core.component import BaseAction, BaseEvent

# Mock User object
class MockUser:
    def __init__(self, user_id="test_user"):
        self.user_id = user_id

# Mock Datastore
class MockDatastore:
    def __init__(self):
        self.workflows = {}
        self.component_setups = {}

    def list_workflows(self, user_id):
        return list(self.workflows.get(user_id, {}).keys())

    def save_workflow(self, user_id, workflow_name, workflow_data):
        if user_id not in self.workflows:
            self.workflows[user_id] = {}
        self.workflows[user_id][workflow_name] = workflow_data

    def list_component_setups(self, user_id, component_name):
        return list(self.component_setups.get(user_id, {}).get(component_name, {}).keys())

    def load_component_setup(self, user_id, component_name, setup_name):
        return self.component_setups.get(user_id, {}).get(component_name, {}).get(setup_name)

    def save_component_setup(self, user_id, component_name, setup_data, setup_name):
        if user_id not in self.component_setups:
            self.component_setups[user_id] = {}
        if component_name not in self.component_setups[user_id]:
            self.component_setups[user_id][component_name] = {}
        self.component_setups[user_id][component_name][setup_name] = setup_data

# Mock Factories
class MockComponentFactory:
    @staticmethod
    def get_available_components():
        return {"mock_component": {"type": "third_party", "setup": {"api_key": {"name": "API Key", "doc": "Your API Key"}}}}

    @staticmethod
    def get_component_info(name):
        return {"type": "third_party", "setup": {"api_key": {"name": "API Key", "doc": "Your API Key"}}}

    @staticmethod
    def create(name, component_id):
        mock_comp = MagicMock(spec=Component)
        mock_comp.name = name
        mock_comp.id = component_id
        mock_comp.setup.return_value = None
        return mock_comp

class MockActionFactory:
    @staticmethod
    def get_actions_for_component(component_name):
        return {"mock_action": {"config": {"param1": {"name": "Parameter 1", "doc": "Doc for param 1"}}, "output_schema": {"output1": "Description"}}}

    @staticmethod
    def get_action_class(action_name):
        mock_action_class = MagicMock(spec=BaseAction)
        mock_action_class.get_field_choices.return_value = []
        return mock_action_class

class MockEventFactory:
    @staticmethod
    def get_available_events():
        return {"mock_component.mock_event": {"config": {"event_param": {"name": "Event Param", "doc": "Doc for event param"}}, "output_schema": {"event_output": "Description"}}}

    @staticmethod
    def get_event_info(event_name):
        return {"config": {"event_param": {"name": "Event Param", "doc": "Doc for event param"}}, "output_schema": {"event_output": "Description"}}

    @staticmethod
    def get_event_class(event_name):
        mock_event_class = MagicMock(spec=Event)
        mock_event_class.get_field_choices.return_value = []
        return mock_event_class

@pytest.fixture
def mock_dependencies():
    with patch('src.cli.create_workflow.get_current_user', return_value=MockUser()), \
         patch('src.cli.create_workflow.datastore', new=MockDatastore()), \
         patch('src.cli.create_workflow.ComponentFactory', new=MockComponentFactory()), \
         patch('src.cli.create_workflow.ActionFactory', new=MockActionFactory()), \
         patch('src.cli.create_workflow.EventFactory', new=MockEventFactory()), \
         patch('src.cli.create_workflow.set_logging_context'), \
         patch('src.cli.create_workflow.print_header'), \
         patch('src.cli.create_workflow.print_separator'), \
         patch('src.cli.create_workflow.logger') as mock_logger:
        yield mock_logger

@pytest.fixture
def mock_user_input():
    with patch('src.cli.utils.ask_question') as mock_ask_question, \
         patch('src.cli.utils.ask_yes_no') as mock_ask_yes_no, \
         patch('src.cli.utils.display_choices') as mock_display_choices, \
         patch('src.cli.utils.get_choice') as mock_get_choice, \
         patch('src.cli.utils.get_valid_workflow_name') as mock_get_valid_workflow_name, \
         patch('builtins.input'):
        yield mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, mock_get_valid_workflow_name

def test_create_workflow_success(mock_dependencies, mock_user_input):
    mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, mock_get_valid_workflow_name = mock_user_input

    mock_get_valid_workflow_name.return_value = "MyTestWorkflow"
    mock_ask_question.side_effect = [
        "My workflow description", # workflow description
        "event_param_value",      # event param
        "api_key_value",          # setup api key
        "action_param_value",     # action param
        ""
    ] # output mapping custom name
    mock_get_choice.side_effect = [
        0, # Select mock_component.mock_event
        0, # Select mock_component for setup
        0, # Select mock_action
    ]
    mock_ask_yes_no.side_effect = [
        False, # Add another component? No
        False, # Customize output key names? No
        True,  # Include 'event_output' in workflow context? Yes
        False, # Customize output key names? No
        True   # Include 'output1' in workflow context? Yes
    ]

    create_workflow()

    mock_dependencies.info.assert_called_with("Starting workflow creation process")
    mock_dependencies.info.assert_called_with("Workflow 'MyTestWorkflow' created successfully")

    # Assert workflow saved
    saved_workflow = mock_dependencies.datastore.workflows["test_user"]["MyTestWorkflow"]
    assert saved_workflow['name'] == "MyTestWorkflow"
    assert saved_workflow['user_id'] == "test_user"
    assert saved_workflow['description'] == "My workflow description"
    assert "trigger_1" in saved_workflow['components']
    assert "mock_component_2" in saved_workflow['components']

    # Assert event trigger configuration
    trigger_config = saved_workflow['components']['trigger_1']
    assert trigger_config['component'] == "mock_component"
    assert trigger_config['event_type'] == "mock_component.mock_event"
    assert trigger_config['config']['event_param'] == "event_param_value"
    assert trigger_config['output_mapping'] == {"event_output": "event_output"}

    # Assert action component configuration
    action_config = saved_workflow['components']['mock_component_2']
    assert action_config['component'] == "mock_component"
    assert action_config['action_type'] == "mock_action"
    assert action_config['config']['param1'] == "action_param_value"
    assert action_config['output_mapping'] == {"output1": "output1"}

    # Assert component setup saved
    saved_setup = mock_dependencies.datastore.component_setups["test_user"]["mock_component"]["default"]
    assert saved_setup['api_key'] == "api_key_value"

def test_configure_event_trigger(mock_dependencies, mock_user_input):
    mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, _ = mock_user_input
    mock_ask_question.return_value = "event_param_value"
    mock_ask_yes_no.return_value = False # Don't customize output

    event_config = configure_event_trigger("mock_component.mock_event", "trigger_id", "test_user")
    assert event_config['component'] == "mock_component"
    assert event_config['event_type'] == "mock_component.mock_event"
    assert event_config['config']['event_param'] == "event_param_value"
    assert event_config['output_mapping'] == {"event_output": "event_output"}

def test_configure_component(mock_dependencies, mock_user_input):
    mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, _ = mock_user_input
    mock_ask_question.side_effect = ["api_key_value", "action_param_value"]
    mock_get_choice.return_value = 0 # Select mock_action
    mock_ask_yes_no.return_value = False # Don't customize output

    comp_config = configure_component("mock_component", "comp_id", "test_user")
    assert comp_config['component'] == "mock_component"
    assert comp_config['action_type'] == "mock_action"
    assert comp_config['config']['param1'] == "action_param_value"
    assert comp_config['output_mapping'] == {"output1": "output1"}

def test_handle_component_setup_new(mock_dependencies, mock_user_input):
    mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, _ = mock_user_input
    mock_ask_question.side_effect = ["new_setup_name", "new_api_key"]
    mock_ask_yes_no.return_value = False # No existing setups

    setup_name = handle_component_setup("mock_component", MockComponentFactory.get_component_info("mock_component"), "test_user")
    assert setup_name == "new_setup_name"
    assert mock_dependencies.datastore.component_setups["test_user"]["mock_component"]["new_setup_name"]['api_key'] == "new_api_key"

def test_handle_component_setup_existing(mock_dependencies, mock_user_input):
    mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, _ = mock_user_input
    mock_dependencies.datastore.save_component_setup("test_user", "mock_component", {"api_key": "existing_key"}, "existing_setup")
    mock_get_choice.return_value = 0 # Select existing setup

    setup_name = handle_component_setup("mock_component", MockComponentFactory.get_component_info("mock_component"), "test_user")
    assert setup_name == "existing_setup"

def test_configure_action(mock_dependencies, mock_user_input):
    mock_ask_question, mock_ask_yes_no, mock_display_choices, mock_get_choice, _ = mock_user_input
    mock_ask_question.return_value = "action_param_value"

    action_info = MockActionFactory.get_actions_for_component("mock_component")["mock_action"]
    config = configure_action("mock_action", action_info)
    assert config['param1'] == "action_param_value"

def test_configure_output_mapping_no_customize(mock_user_input):
    mock_ask_question, mock_ask_yes_no, _, _, _ = mock_user_input
    mock_ask_yes_no.return_value = False # Don't customize

    output_schema = {"key1": "Desc1", "key2": "Desc2"}
    mapping = configure_output_mapping(output_schema)
    assert mapping == {"key1": "key1", "key2": "key2"}

def test_configure_output_mapping_customize(mock_user_input):
    mock_ask_question, mock_ask_yes_no, _, _, _ = mock_user_input
    mock_ask_yes_no.side_effect = [True, True, False] # Customize, Include key1, Don't include key2
    mock_ask_question.side_effect = ["custom_key1"]

    output_schema = {"key1": "Desc1", "key2": "Desc2"}
    mapping = configure_output_mapping(output_schema)
    assert mapping == {"key1": "custom_key1"}