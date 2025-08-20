"""Custom logging filter to add context information to log records."""

import logging
import threading
from typing import Optional, Dict, Any


class ContextFilter(logging.Filter):
    """Filter to add user, workflow, and context information to log records."""
    
    def __init__(self):
        super().__init__()
        self._local = threading.local()
    
    def filter(self, record):
        """Add context information to the log record."""
        # Get context information from thread-local storage with defaults
        user = getattr(self._local, 'user', 'unknown')
        workflow = getattr(self._local, 'workflow', 'none')
        context_keys = getattr(self._local, 'context_keys', '[]')
        
        # Always add these fields to the record
        record.user = user
        record.workflow = workflow
        record.context_keys = context_keys
        
        return True
    
    def set_user(self, user_id: str):
        """Set the current user for this thread."""
        self._local.user = user_id
    
    def set_workflow(self, workflow_name: str):
        """Set the current workflow for this thread."""
        self._local.workflow = workflow_name
    
    def set_context_keys(self, context_keys: list):
        """Set the current context keys for this thread."""
        self._local.context_keys = str(context_keys) if context_keys else '[]'
    
    def clear_context(self):
        """Clear all context information for this thread."""
        self._local.user = 'unknown'
        self._local.workflow = 'none'
        self._local.context_keys = '[]'


# Global context filter instance
context_filter = ContextFilter()


def set_logging_context(user_id: Optional[str] = None, 
                       workflow_name: Optional[str] = None, 
                       context_keys: Optional[list] = None):
    """Set logging context information for the current thread."""
    if user_id is not None:
        context_filter.set_user(user_id)
    if workflow_name is not None:
        context_filter.set_workflow(workflow_name)
    if context_keys is not None:
        context_filter.set_context_keys(context_keys)


def clear_logging_context():
    """Clear logging context information for the current thread."""
    context_filter.clear_context()


def setup_context_filter():
    """Setup the context filter on all workflow_manager handlers."""
    logger = logging.getLogger('workflow_manager')
    
    # Add filter to the logger itself so it applies to all handlers
    logger.addFilter(context_filter)
    
    # Also add to all handlers to ensure it works
    for handler in logger.handlers:
        handler.addFilter(context_filter)
