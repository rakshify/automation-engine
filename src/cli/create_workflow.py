"""Workflow creation CLI flow."""

import json
import logging
from typing import Dict, Any, List, Set

from .auth import get_current_user
from .utils import (
    ask_question, ask_yes_no, display_choices, get_choice, 
    get_valid_workflow_name, print_header, print_separator
)
from ..core.datastore import datastore
from ..core.factory import ComponentFactory, ActionFactory, EventFactory
from ..core.logging_filter import set_logging_context

# Module-level logger
logger = logging.getLogger(__name__)


def create_workflow() -> None:
    """Interactive workflow creation flow."""
    logger.info("Starting workflow creation process")
    print_header("Create New Workflow")
    
    user = get_current_user()
    # Set logging context
    set_logging_context(user_id=user.user_id)
    
    # Get existing workflow names to ensure uniqueness
    existing_workflows = datastore.list_workflows(user.user_id)
    
    # Get workflow name
    workflow_name = get_valid_workflow_name(existing_workflows)
    
    # Initialize workflow data
    workflow_data = {
        'name': workflow_name,
        'user_id': user.user_id,
        'components': {},
        'description': ask_question("Enter workflow description (optional)", "")
    }
    
    # Add components
    print_separator()
    
    # First, add the required event trigger
    available_events = EventFactory.get_available_events()
    if not available_events:
        logger.error("No event triggers available")
        return
    
    event_names = list(available_events.keys())
    display_choices("Available Event Triggers", event_names)
    
    event_choice = get_choice(event_names, "Select an event trigger")
    selected_event = event_names[event_choice]
    
    # Configure the event trigger
    trigger_id = "trigger_1"
    trigger_config = configure_event_trigger(selected_event, trigger_id, user.user_id)
    trigger_config['is_trigger'] = True
    
    # Add to workflow
    workflow_data['components'][trigger_id] = trigger_config
    
    # Now add action components
    component_counter = 2
    while True:
        available_components = ComponentFactory.get_available_components()
        if not available_components:
            break
        
        component_names = list(available_components.keys())
        display_choices("Available Components", component_names)
        
        component_choice = get_choice(component_names, "Select a component")
        selected_component = component_names[component_choice]
        
        # Configure the component
        component_id = f"{selected_component}_{component_counter}"
        component_config = configure_component(selected_component, component_id, user.user_id)
        
        # Add to workflow
        workflow_data['components'][component_id] = component_config
        
        # Ask if user wants to add more components
        if not ask_yes_no("Add another component?", False):
            break
        
        component_counter += 1
    
    # Save workflow
    print_separator()
    
    try:
        datastore.save_workflow(user.user_id, workflow_name, workflow_data)
        logger.info(f"Workflow '{workflow_name}' created successfully")
        
        # Display summary
        print_separator()
        for comp_id, comp_config in workflow_data['components'].items():
            component_type = comp_config.get('action_type') or comp_config.get('event_type', 'Unknown')
        
    except Exception as e:
        logger.error(f"Error saving workflow: {e}", exc_info=True)


def configure_event_trigger(event_name: str, component_id: str, user_id: str) -> Dict[str, Any]:
    """Configure an event trigger."""
    # Get event info
    event_info = EventFactory.get_event_info(event_name)
    if not event_info:
        return {}
    
    # Get component name from event name
    component_name = event_name.split('.')[0]
    
    # Check if component needs setup
    component_info = ComponentFactory.get_component_info(component_name)
    setup_name = None
    
    if component_info and component_info.get('requires_setup', False):
        setup_name = handle_component_setup(component_name, component_info, user_id)
    
    # Configure event parameters
    config = {}
    event_config = event_info.get('config', {})
    
    for param_key, param_info in event_config.items():
        value = ask_question(f"{param_info['name']} ({param_info['doc']})", param_info.get('default', ''))
        config[param_key] = value
    
    # Get output mapping
    output_mapping = configure_output_mapping(event_info.get('output_schema', {}))
    
    return {
        'component': component_name,
        'setup_name': setup_name,
        'event_type': event_name,
        'config': config,
        'output_mapping': output_mapping
    }


def configure_component(component_name: str, component_id: str, user_id: str) -> Dict[str, Any]:
    """Configure a component with its actions and settings."""
    # Check if component needs setup
    component_info = ComponentFactory.get_component_info(component_name)
    setup_name = None
    
    if component_info and component_info.get('requires_setup', False):
        setup_name = handle_component_setup(component_name, component_info, user_id)
    
    # Get available actions for this component
    available_actions = ActionFactory.get_actions_for_component(component_name)
    
    if not available_actions:
        return {
            'component': component_name,
            'setup_name': setup_name,
            'action_type': None,
            'config': {},
            'output_mapping': {}
        }
    
    # Let user choose action
    action_names = list(available_actions.keys())
    display_choices(f"Available Actions for {component_name}", action_names)
    
    action_choice = get_choice(action_names, "Select an action")
    selected_action = action_names[action_choice]
    
    # Configure the action
    action_info = available_actions[selected_action]
    action_config = configure_action(selected_action, action_info)
    
    # Get output mapping
    output_mapping = configure_output_mapping(action_info.get('output_schema', {}))
    
    return {
        'component': component_name,
        'setup_name': setup_name,
        'action_type': selected_action,
        'config': action_config,
        'output_mapping': output_mapping
    }


def handle_component_setup(component_name: str, component_info: Dict[str, Any], user_id: str) -> str:
    """Handle component setup configuration."""
    # Check for existing setups
    existing_setups = datastore.list_component_setups(user_id, component_name)
    
    if existing_setups:
        display_choices("Available Setups", existing_setups)
        
        # Add option to create new setup
        choices = existing_setups + ["Create new setup"]
        display_choices("Choose Setup Option", choices)
        
        choice_idx = get_choice(choices, "Select setup option")
        
        if choice_idx < len(existing_setups):
            # Use existing setup
            selected_setup = existing_setups[choice_idx]
            return selected_setup
        else:
            # Create new setup
            setup_name = ask_question("Enter name for new setup", "default")
            while setup_name in existing_setups:
                setup_name = ask_question("Enter a different name for new setup")
    else:
        # No existing setups, create new one
        setup_name = ask_question("Enter name for this setup", "default")
    
    setup_config = component_info.get('setup', {})
    
    setup_data = {}
    for param_key, param_info in setup_config.items():
        value = ask_question(f"{param_info['name']} ({param_info['doc']})", param_info.get('default', ''))
        setup_data[param_key] = value
    
    # Save setup
    datastore.save_component_setup(user_id, component_name, setup_data, setup_name)
    return setup_name


def configure_action(action_name: str, action_info: Dict[str, Any]) -> Dict[str, Any]:
    """Configure an action with its parameters."""
    config = {}
    action_config = action_info.get('config', {})
    
    # Configure basic parameters
    for param_key, param_info in action_config.items():
        if param_key != 'conditional':  # Skip conditional config for now
            value = ask_question(f"{param_info['name']} ({param_info['doc']})", param_info.get('default', ''))
            config[param_key] = value
    
    # Handle conditional configuration
    conditional_config = action_config.get('conditional', {})
    if conditional_config:
        # Check if any condition is met and configure additional parameters
        for condition, fields in conditional_config.items():
            if config.get('operation') == condition or config.get('action') == condition:
                for field_key, field_info in fields.items():
                    value = ask_question(f"{field_info['name']} ({field_info['doc']})")
                    config[field_key] = value
    
    return config


def configure_output_mapping(output_schema: Dict[str, Any]) -> Dict[str, str]:
    """Configure output key mapping for a component."""
    if not output_schema:
        return {}
    
    # Ask user which keys they want to make available and get custom aliases
    output_mapping = {}
    
    if ask_yes_no("Customize output key names?", False):
        for key, info in output_schema.items():
            if ask_yes_no(f"Include '{key}' in workflow context?", True):
                custom_name = ask_question(f"Custom name for '{key}' (press Enter to keep original)", key)
                output_mapping[key] = custom_name or key
    else:
        # Use all keys with original names
        output_mapping = {key: key for key in output_schema.keys()}
    
    return output_mapping
