"""Abstract base classes for components, actions, and events."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseComponent(ABC):
    """Abstract base class for all workflow components."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    def setup(self, setup_config: Dict[str, Any]) -> None:
        """Setup the component with third-party configuration."""
        pass


class BaseAction(ABC):
    """Abstract base class for all actions."""
    
    @staticmethod
    @abstractmethod
    def get_field_choices(field_name: str, field_config: Dict[str, Any], component_instance=None) -> List[str]:
        """Get available choices for a specific field."""
        pass
    
    def __init__(self, component: 'BaseComponent', config: Dict[str, Any] = None):
        self.component = component
        self.config = config or {}
    
    @abstractmethod
    def execute(self, context: 'WorkflowContext') -> Dict[str, Any]:
        """Execute the action and return results."""
        pass


class BaseEvent(ABC):
    """Abstract base class for all events."""
    
    @staticmethod
    @abstractmethod
    def get_field_choices(field_name: str, field_config: Dict[str, Any], component_instance=None) -> List[str]:
        """Get available choices for a specific field."""
        pass
    """Abstract base class for all workflow actions."""
    
    def __init__(self, component: BaseComponent, config: Dict[str, Any] = None):
        self.component = component
        self.config = config or {}
    
    @abstractmethod
    def execute(self, context: 'WorkflowContext') -> Dict[str, Any]:
        """Execute the action and return results."""
        pass


class BaseEvent(ABC):
    """Abstract base class for all workflow events."""
    
    def __init__(self, component: BaseComponent, config: Dict[str, Any] = None):
        self.component = component
        self.config = config or {}
    
    @abstractmethod
    def execute(self, context: 'WorkflowContext') -> Dict[str, Any]:
        """Execute the event trigger and return results."""
        pass
