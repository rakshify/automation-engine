import pytest
from unittest.mock import MagicMock, patch, call
from collections import defaultdict

from src.core.workflow import Workflow
from src.core.context import WorkflowContext
from src.core.component import BaseComponent, BaseAction, BaseEvent

# Mock classes for factories and datastore
class MockComponentFactory:
    @staticmethod
    def create(name, config=None):
        mock_comp = MagicMock(spec=BaseComponent)
        mock_comp.name = name
        mock_comp.setup.return_value = None
        return mock_comp

    @staticmethod
    def get_available_components():
        return {"mock_component": {"type": "third_party", "setup": {"api_key": {"name": "API Key", "doc": "Your API Key"}}}}

class MockActionFactory:
    @staticmethod
    def create(action_name, component, config=None):
        mock_action = MagicMock(spec=BaseAction)
        mock_action.execute.return_value = {"success": True, "output": "action_output"}
        return mock_action

class MockEventFactory:
    @staticmethod
    def create(event_name, component, config=None):
        mock_event = MagicMock(spec=BaseEvent)
        mock_event.execute.return_value = {"success": True, "event_data": "event_output"}
        mock_event.is_running.return_value = False # Default for non-persistent
        mock_event.stop_listening.return_value = None
        return mock_event

class MockDatastore:
    def __init__(self):
        self.workflows = {}
        self.component_setups = {}

    def load_workflow(self, user_id, workflow_name):
        return self.workflows.get(user_id, {}).get(workflow_name)

    def load_component_setup(self, user_id, component_name, setup_name):
        return self.component_setups.get(user_id, {}).get(component_name, {}).get(setup_name)

@pytest.fixture
def mock_workflow_dependencies():
    with patch('src.core.workflow.ComponentFactory', new=MockComponentFactory()), \
         patch('src.core.workflow.ActionFactory', new=MockActionFactory()), \
         patch('src.core.workflow.EventFactory', new=MockEventFactory()), \
         patch('src.core.workflow.datastore', new=MockDatastore()), \
         patch('src.core.workflow.set_logging_context'), \
         patch('src.core.workflow.clear_logging_context'), \
         patch('src.core.workflow.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield {
            "component_factory": MockComponentFactory,
            "action_factory": MockActionFactory,
            "event_factory": MockEventFactory,
            "datastore": MockDatastore(),
            "set_logging_context": MagicMock(),
            "clear_logging_context": MagicMock(),
            "logger": mock_logger
        }

@pytest.fixture
def sample_workflow_data():
    return {
        "name": "Test Workflow",
        "components": {
            "comp1": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "value1"}, "output_mapping": {"output": "comp1_output"}},
            "comp2": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{comp1_output}}"}},
            "comp3": {"component": "mock_component", "event_type": "mock_event", "is_trigger": True, "config": {"channel": "#general"}}
        }
    }

class TestWorkflow:
    def test_init_success(self, sample_workflow_data, mock_workflow_dependencies):
        workflow = Workflow(sample_workflow_data, "test_user")
        assert workflow.name == "Test Workflow"
        assert "comp1" in workflow.components
        mock_workflow_dependencies["set_logging_context"].assert_called_with(user_id="test_user", workflow_name="Test Workflow")

    def test_init_no_components(self, mock_workflow_dependencies):
        with pytest.raises(ValueError, match="Workflow has no components"):
            Workflow({"name": "Empty Workflow", "components": {}}, "test_user")

    def test_build_dependency_graph_basic(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "Dep Workflow",
            "components": {
                "A": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "value"}, "output_mapping": {"out_A": "out_A"}},
                "B": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{out_A}}"}}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        assert workflow.dependencies == {"B": {"A"}}

    def test_build_dependency_graph_no_dependencies(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "No Dep Workflow",
            "components": {
                "A": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "value"}},
                "B": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "value"}}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        assert workflow.dependencies == {}

    def test_topological_sort_basic(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "Sort Workflow",
            "components": {
                "A": {"component": "mock_component", "action_type": "mock_action", "output_mapping": {"out_A": "out_A"}},
                "B": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{out_A}}"}, "output_mapping": {"out_B": "out_B"}},
                "C": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{out_B}}"}}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        order = workflow._topological_sort()
        assert order == ["A", "B", "C"]

    def test_topological_sort_cycle_detection(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "Cycle Workflow",
            "components": {
                "A": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{out_C}}"}, "output_mapping": {"out_A": "out_A"}},
                "B": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{out_A}}"}, "output_mapping": {"out_B": "out_B"}},
                "C": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{out_B}}"}, "output_mapping": {"out_C": "out_C"}}
            }
        }
        with pytest.raises(ValueError, match="Circular dependency detected in workflow"):
            Workflow(workflow_data, "test_user")._topological_sort()

    def test_create_component_instance_no_setup(self, mock_workflow_dependencies):
        component_config = {"component": "mock_component"}
        component = Workflow("wf", "user")._create_component_instance("comp1", component_config)
        assert isinstance(component, MagicMock)
        assert component.name == "mock_component"
        component.setup.assert_not_called()

    def test_create_component_instance_with_setup(self, mock_workflow_dependencies):
        mock_workflow_dependencies["datastore"].component_setups = {
            "test_user": {"mock_component": {"default": {"api_key": "123"}}}}
        component_config = {"component": "mock_component", "setup_name": "default"}
        component = Workflow("wf", "test_user")._create_component_instance("comp1", component_config)
        component.setup.assert_called_once_with({"api_key": "123"})

    def test_execute_component_action(self, mock_workflow_dependencies):
        workflow = Workflow(sample_workflow_data(), "test_user")
        result = workflow._execute_component("comp1", sample_workflow_data()["components"]["comp1"])
        assert result['success'] is True
        assert workflow.context.get("comp1_output") == "action_output"
        mock_workflow_dependencies["action_factory"].create.return_value.execute.assert_called_once()

    def test_execute_component_event_non_persistent(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "Event Workflow",
            "components": {
                "event_comp": {"component": "mock_component", "event_type": "mock_event", "is_trigger": True, "config": {"timeout": 1}}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        mock_workflow_dependencies["event_factory"].create.return_value.is_running.return_value = False
        result = workflow._execute_component("event_comp", workflow_data["components"]["event_comp"])
        assert result['success'] is True
        assert result['persistent_listener'] is True
        mock_workflow_dependencies["event_factory"].create.return_value.execute.assert_called_once()

    def test_execute_component_event_persistent(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "Event Workflow",
            "components": {
                "event_comp": {"component": "mock_component", "event_type": "mock_event", "is_trigger": True, "config": {"timeout": -1}}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        mock_workflow_dependencies["event_factory"].create.return_value.is_running.return_value = True
        result = workflow._execute_component("event_comp", workflow_data["components"]["event_comp"])
        assert result['success'] is True
        assert result['persistent_listener'] is True

    def test_execute_component_error(self, mock_workflow_dependencies):
        workflow = Workflow(sample_workflow_data(), "test_user")
        mock_workflow_dependencies["action_factory"].create.return_value.execute.side_effect = Exception("Action Failed")
        with pytest.raises(Exception, match="Action Failed"):
            workflow._execute_component("comp1", sample_workflow_data()["components"]["comp1"])

    def test_cleanup(self, mock_workflow_dependencies):
        workflow_data = {
            "name": "Cleanup Workflow",
            "components": {
                "trigger_comp": {"component": "mock_component", "event_type": "mock_event", "is_trigger": True, "config": {"timeout": -1}},
                "action_comp": {"component": "mock_component", "action_type": "mock_action"}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        workflow.cleanup()
        mock_workflow_dependencies["event_factory"].create.return_value.stop_listening.assert_called_once()

    def test_execute_traditional_workflow(self, sample_workflow_data, mock_workflow_dependencies):
        workflow_data = {
            "name": "Traditional Workflow",
            "components": {
                "comp1": {"component": "mock_component", "action_type": "mock_action", "output_mapping": {"output": "comp1_output"}},
                "comp2": {"component": "mock_component", "action_type": "mock_action", "config": {"input": "{{comp1_output}}"}}
            }
        }
        workflow = Workflow(workflow_data, "test_user")
        result = workflow.execute()
        assert result['success'] is True
        assert "comp1" in result['results']
        assert "comp2" in result['results']
        assert workflow.context.get("comp1_output") == "action_output"

    def test_execute_reactive_workflow(self, sample_workflow_data, mock_workflow_dependencies):
        workflow = Workflow(sample_workflow_data, "test_user")
        mock_event_instance = mock_workflow_dependencies["event_factory"].create.return_value
        mock_event_instance.is_running.return_value = True
        mock_event_instance.execute.return_value = {"success": True, "event_data": "initial_event"}

        result = workflow.execute()
        assert result['success'] is True
        assert "Reactive workflow started" in result['message']
        mock_event_instance.set_workflow_callback.assert_called_once()

        # Simulate a trigger firing
        callback_func = mock_event_instance.set_workflow_callback.call_args[0][0]
        callback_func({"output": "triggered_data"})

        # Assert action component was executed with updated context
        mock_workflow_dependencies["action_factory"].create.return_value.execute.assert_called_with(workflow.context)
        assert workflow.context.get("output") == "triggered_data"

    def test_load_from_file_success(self, mock_workflow_dependencies):
        mock_workflow_dependencies["datastore"].workflows = {"test_user": {"loaded_wf": {"name": "Loaded WF", "components": {"comp1": {}}}}}
        workflow = Workflow.load_from_file("test_user", "loaded_wf")
        assert workflow.name == "Loaded WF"

    def test_load_from_file_not_found(self, mock_workflow_dependencies):
        workflow = Workflow.load_from_file("test_user", "non_existent_wf")
        assert workflow is None
