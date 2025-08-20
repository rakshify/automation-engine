"""Workflow execution CLI flow."""

import json
import time
import logging
from typing import Dict, Any, Optional

from .auth import get_current_user
from .utils import display_choices, get_choice, print_header, print_separator, format_dict, ask_yes_no
from ..core.datastore import datastore
from ..core.workflow import Workflow
from ..core.logging_filter import set_logging_context

# Module-level logger
logger = logging.getLogger(__name__)


def get_user_choice() -> Optional[str]:
    """Get user's choice of workflow to execute."""
    user = get_current_user()
    available_workflows = datastore.list_workflows(user.user_id)
    
    if not available_workflows:
        return None
    
    display_choices("Available Workflows", available_workflows)
    choice_idx = get_choice(available_workflows, "Select workflow to execute")
    return available_workflows[choice_idx]


def execute_workflow(workflow_name: str, auto_confirm: bool = False) -> None:
    """Execute a specific workflow by name."""
    logger.info(f"Executing workflow: {workflow_name}")
    print_header("Execute Workflow")
    
    user = get_current_user()
    # Set logging context
    set_logging_context(user_id=user.user_id, workflow_name=workflow_name)
    
    # Load workflow
    workflow_data = datastore.load_workflow(user.user_id, workflow_name)
    if not workflow_data:
        logger.error(f"Workflow '{workflow_name}' not found")
        return
    
    print_separator()
    
    # Check if this is a reactive workflow
    components = workflow_data.get('components', {})
    is_reactive = any(comp.get('is_trigger') for comp in components.values())
    
    # Confirm execution
    if not auto_confirm or not is_reactive:
        if not ask_yes_no("Execute this workflow?", True):
            return
    
    # Execute workflow
    print_separator()
    
    try:
        workflow = Workflow(workflow_data, user.user_id)
        
        if is_reactive:
            _execute_reactive_workflow(workflow, workflow_name)
        else:
            _execute_traditional_workflow(workflow)
            
    except KeyboardInterrupt:
        logger.info("Workflow execution interrupted")
        try:
            workflow.cleanup()
        except:
            pass
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
    
    print_separator()


def interactive_execute_workflow() -> None:
    """Interactive workflow execution - user chooses workflow first."""
    workflow_name = get_user_choice()
    if workflow_name:
        execute_workflow(workflow_name)


def _execute_reactive_workflow(workflow: 'Workflow', workflow_name: str) -> None:
    """Execute a reactive workflow with persistent monitoring."""
    logger.info(f"Starting reactive workflow: {workflow_name}")
    
    # Execute workflow (this sets up the reactive listeners)
    result = workflow.execute()
    
    if not result.get('success'):
        logger.error(f"Failed to start reactive workflow: {result.get('error')}")
        return
    
    try:
        # Keep the main thread alive while the reactive workflow runs
        start_time = time.time()
        last_status_time = start_time
        
        while True:
            time.sleep(1)
            
            # Show periodic status updates
            current_time = time.time()
            if current_time - last_status_time >= 30:
                elapsed = int(current_time - start_time)
                last_status_time = current_time
                
    except KeyboardInterrupt:
        logger.info("Stopping reactive workflow")
        workflow.cleanup()


def _execute_traditional_workflow(workflow: 'Workflow') -> None:
    """Execute a traditional (non-reactive) workflow."""
    result = workflow.execute()
    
    # Display results
    print_separator()
    if result.get('success'):
        logger.info("Workflow executed successfully")
        
        # Show results
        results = result.get('results', {})
        if results:
            for comp_id, comp_result in results.items():
                if isinstance(comp_result, dict):
                    print(format_dict(comp_result, 1))
                else:
                    pass
        
        # Show final context
        context = result.get('context', {})
        if context:
            print(format_dict(context, 1))
    else:
        logger.error(f"Workflow execution failed: {result.get('error')}")
        
        # Show context for debugging
        context = result.get('context', {})
        if context:
            print(format_dict(context, 1))


def show_workflow_details(workflow_name: str, user_id: str) -> None:
    """Display detailed information about a workflow."""
    workflow_data = datastore.load_workflow(user_id, workflow_name)
    if not workflow_data:
        return
    
    print_header(f"Workflow: {workflow_name}")
    
    components = workflow_data.get('components', {})
    
    if components:
        for comp_id, comp_config in components.items():
            action_type = comp_config.get('action_type') or comp_config.get('event_type', 'Unknown')
            
            config = comp_config.get('config', {})
            if config:
                for key, value in config.items():
                    pass
            
            output_mapping = comp_config.get('output_mapping', {})
            if output_mapping:
                pass
    
    print_separator()
