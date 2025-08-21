import pytest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

from src.core.factory import ComponentFactory, ActionFactory, EventFactory
from src.core.component import BaseComponent, BaseAction, BaseEvent
from src.components.formatter import Formatter, TextAction, NumberAction
from src.components.webhook import Webhook, GetAction, PostAction
from src.components.slack import Slack, SendMessageAction, ReceiveMessageEvent

# Mock config file contents
MOCK_COMPONENTS_STORE = {
    "formatter": {"name": "Formatter", "type": "built_in"},
    "webhook": {"name": "Webhook", "type": "built_in"},
    "slack": {"name": "Slack", "type": "third_party"}
}
MOCK_ACTION_STORE = {
    "formatter.text": {"name": "Text Action", "component": "formatter"},
    "formatter.number": {"name": "Number Action", "component": "formatter"},
    "webhook.get": {"name": "GET Request", "component": "webhook"},
    "slack.send_message": {"name": "Send Message", "component": "slack"}
}
MOCK_EVENT_STORE = {
    "slack.receive_message": {"name": "Receive Message", "component": "slack"}
}

@pytest.fixture(autouse=True)
def mock_config_files():
    with patch('src.core.factory.Path') as MockPath:
        # Mock Path.exists()
        MockPath.return_value.exists.side_effect = lambda: True

        # Mock open for each config file
        def mock_open(file_path, mode='r'):
            if "components_store.json" in str(file_path):
                return MagicMock(spec=open, **{"__enter__.return_value": MagicMock(spec=json.load, read=lambda: json.dumps(MOCK_COMPONENTS_STORE))})
            elif "action_store.json" in str(file_path):
                return MagicMock(spec=open, **{"__enter__.return_value": MagicMock(spec=json.load, read=lambda: json.dumps(MOCK_ACTION_STORE))})
            elif "event_store.json" in str(file_path):
                return MagicMock(spec=open, **{"__enter__.return_value": MagicMock(spec=json.load, read=lambda: json.dumps(MOCK_EVENT_STORE))})
            else:
                return MagicMock(spec=open)

        with patch('builtins.open', side_effect=mock_open):
            yield

class TestComponentFactory:
    def test_create_known_component(self):
        component = ComponentFactory.create("formatter")
        assert isinstance(component, Formatter)
        assert component.name == "formatter"

    def test_create_unknown_component(self):
        with pytest.raises(ValueError, match="Unknown component: non_existent_component"):
            ComponentFactory.create("non_existent_component")

    def test_get_available_components(self):
        components = ComponentFactory.get_available_components()
        assert components == MOCK_COMPONENTS_STORE

    def test_get_available_components_file_not_found(self):
        with patch('src.core.factory.Path') as MockPath:
            MockPath.return_value.exists.return_value = False
            components = ComponentFactory.get_available_components()
            assert components == {}

    def test_get_component_info_known(self):
        info = ComponentFactory.get_component_info("webhook")
        assert info == MOCK_COMPONENTS_STORE["webhook"]

    def test_get_component_info_unknown(self):
        info = ComponentFactory.get_component_info("non_existent")
        assert info == {}

class TestActionFactory:
    def test_create_known_action(self):
        mock_component = MagicMock(spec=BaseComponent)
        action = ActionFactory.create("formatter.text", mock_component)
        assert isinstance(action, TextAction)
        assert action.component == mock_component

    def test_create_unknown_action(self):
        mock_component = MagicMock(spec=BaseComponent)
        with pytest.raises(ValueError, match="Unknown action: non_existent_action"):
            ActionFactory.create("non_existent_action", mock_component)

    def test_get_action_class_known(self):
        action_class = ActionFactory.get_action_class("webhook.get")
        assert action_class == GetAction

    def test_get_action_class_unknown(self):
        action_class = ActionFactory.get_action_class("non_existent")
        assert action_class is None

    def test_get_available_actions(self):
        actions = ActionFactory.get_available_actions()
        assert actions == MOCK_ACTION_STORE

    def test_get_available_actions_file_not_found(self):
        with patch('src.core.factory.Path') as MockPath:
            MockPath.return_value.exists.return_value = False
            actions = ActionFactory.get_available_actions()
            assert actions == {}

    def test_get_actions_for_component(self):
        formatter_actions = ActionFactory.get_actions_for_component("formatter")
        assert formatter_actions == {
            "formatter.text": {"name": "Text Action", "component": "formatter"},
            "formatter.number": {"name": "Number Action", "component": "formatter"}
        }

    def test_get_actions_for_component_no_actions(self):
        no_actions = ActionFactory.get_actions_for_component("non_existent_component")
        assert no_actions == {}

class TestEventFactory:
    def test_create_known_event(self):
        mock_component = MagicMock(spec=BaseComponent)
        event = EventFactory.create("slack.receive_message", mock_component)
        assert isinstance(event, ReceiveMessageEvent)
        assert event.component == mock_component

    def test_create_unknown_event(self):
        mock_component = MagicMock(spec=BaseComponent)
        with pytest.raises(ValueError, match="Unknown event: non_existent_event"):
            EventFactory.create("non_existent_event", mock_component)

    def test_get_event_class_known(self):
        event_class = EventFactory.get_event_class("slack.receive_message")
        assert event_class == ReceiveMessageEvent

    def test_get_event_class_unknown(self):
        event_class = EventFactory.get_event_class("non_existent")
        assert event_class is None

    def test_get_available_events(self):
        events = EventFactory.get_available_events()
        assert events == MOCK_EVENT_STORE

    def test_get_available_events_file_not_found(self):
        with patch('src.core.factory.Path') as MockPath:
            MockPath.return_value.exists.return_value = False
            events = EventFactory.get_available_events()
            assert events == {}

    def test_get_event_info_known(self):
        info = EventFactory.get_event_info("slack.receive_message")
        assert info == MOCK_EVENT_STORE["slack.receive_message"]

    def test_get_event_info_unknown(self):
        info = EventFactory.get_event_info("non_existent")
        assert info == {}
