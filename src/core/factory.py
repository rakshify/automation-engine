"""Factories for dynamic object creation."""

import json
from pathlib import Path
from typing import Dict, Any, Type, Optional

from .component import BaseComponent, BaseAction, BaseEvent
from ..components.formatter import Formatter, TextAction, NumberAction
from ..components.webhook import Webhook, GetAction, PostAction
from ..components.slack import Slack, SendMessageAction, ReceiveMessageEvent


class ComponentFactory:
    """Factory for creating component instances."""
    
    _components: Dict[str, Type[BaseComponent]] = {
        'formatter': Formatter,
        'webhook': Webhook,
        'slack': Slack,
    }
    
    @classmethod
    def create(cls, component_name: str, config: Dict[str, Any] = None) -> BaseComponent:
        """Create a component instance by name."""
        if component_name not in cls._components:
            raise ValueError(f"Unknown component: {component_name}")
        
        component_class = cls._components[component_name]
        return component_class(component_name, config)
    
    @classmethod
    def get_available_components(cls) -> Dict[str, Any]:
        """Get available components from the components store."""
        config_path = Path("configs/components_store.json")
        if not config_path.exists():
            return {}
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    @classmethod
    def get_component_info(cls, component_name: str) -> Dict[str, Any]:
        """Get component information by name."""
        components = cls.get_available_components()
        return components.get(component_name, {})


class ActionFactory:
    """Factory for creating action instances."""
    
    _actions: Dict[str, Type[BaseAction]] = {
        'formatter.text': TextAction,
        'formatter.number': NumberAction,
        'webhook.get': GetAction,
        'webhook.post': PostAction,
        'slack.send_message': SendMessageAction,
    }
    
    @classmethod
    def create(cls, action_name: str, component: BaseComponent, config: Dict[str, Any] = None) -> BaseAction:
        """Create an action instance by name."""
        if action_name not in cls._actions:
            raise ValueError(f"Unknown action: {action_name}")
        
        action_class = cls._actions[action_name]
        return action_class(component, config)
    
    @classmethod
    def get_action_class(cls, action_name: str):
        """Get the action class for a given action name."""
        return cls._actions.get(action_name)
    
    @classmethod
    def get_action_class(cls, action_name: str):
        """Get the action class for a given action name."""
        return cls._actions.get(action_name)
    
    @classmethod
    def get_available_actions(cls) -> Dict[str, Any]:
        """Get available actions from the action store."""
        config_path = Path("configs/action_store.json")
        if not config_path.exists():
            return {}
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    @classmethod
    def get_actions_for_component(cls, component_name: str) -> Dict[str, Any]:
        """Get available actions for a specific component."""
        all_actions = cls.get_available_actions()
        component_actions = {}
        
        for action_name, action_config in all_actions.items():
            if action_config.get('component') == component_name:
                component_actions[action_name] = action_config
        
        return component_actions


class EventFactory:
    """Factory for creating event instances."""
    
    _events: Dict[str, Type[BaseEvent]] = {
        'slack.receive_message': ReceiveMessageEvent,
    }
    
    @classmethod
    def create(cls, event_name: str, component: BaseComponent, config: Dict[str, Any] = None) -> BaseEvent:
        """Create an event instance by name."""
        if event_name not in cls._events:
            raise ValueError(f"Unknown event: {event_name}")
        
        event_class = cls._events[event_name]
        return event_class(component, config)
    
    @classmethod
    def get_event_class(cls, event_name: str):
        """Get the event class for a given event name."""
        return cls._events.get(event_name)
    
    @classmethod
    def get_event_class(cls, event_name: str):
        """Get the event class for a given event name."""
        return cls._events.get(event_name)
    
    @classmethod
    def get_available_events(cls) -> Dict[str, Any]:
        """Get available events from the event store."""
        config_path = Path("configs/event_store.json")
        if not config_path.exists():
            return {}
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    @classmethod
    def get_event_info(cls, event_name: str) -> Dict[str, Any]:
        """Get event information by name."""
        events = cls.get_available_events()
        return events.get(event_name, {})
