"""Thread-safe context manager for workflow data sharing."""

import threading
from typing import Dict, Any, Optional
import re


class WorkflowContext:
    """Thread-safe context manager for sharing data between workflow components."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        with self._lock:
            self._data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        with self._lock:
            return self._data.get(key, default)
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple values in the context."""
        with self._lock:
            self._data.update(data)
    
    def get_all(self) -> Dict[str, Any]:
        """Get a copy of all context data."""
        with self._lock:
            return self._data.copy()
    
    def clear(self) -> None:
        """Clear all context data."""
        with self._lock:
            self._data.clear()
    
    def resolve_placeholders(self, text: str) -> str:
        """Resolve context placeholders in text (e.g., {{key}} -> value)."""
        if not isinstance(text, str):
            return text
        
        def replace_placeholder(match):
            key = match.group(1)
            value = self.get(key)
            return str(value) if value is not None else match.group(0)
        
        with self._lock:
            return re.sub(r'\{\{([^}]+)\}\}', replace_placeholder, text)
    
    def resolve_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve placeholders in a configuration dictionary."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str):
                resolved[key] = self.resolve_placeholders(value)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_config(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_placeholders(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved
