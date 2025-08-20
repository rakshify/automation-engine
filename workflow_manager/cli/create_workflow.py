"""Workflow creation CLI flow."""

import json
from typing import Dict, Any, List, Set

from .auth import get_current_user
from .utils import (
    ask_question, ask_yes_no, display_choices, get_choice, 
    get_valid_workflow_name, print_header, print_separator
)
from ..core.datastore import datastore
from ..core.factory import ComponentFactory, ActionFactory, EventFactory


def create_workflow() -> None:
    """Interactive workflow creation flow."""
    print_header("Create New Workflow")
    
    user = get_current_user()
    print(f"Creating workflow for user: {user.username}")
    
    # Get existing workflow names to ensure uniqueness
    existing_workflows = datastore.list_workflows(user.user_id)
    
    # Get workflow name
    workflow_name = get_valid_workflow_name(existing_workflows)
    print(f"Creating workflow: {workflow_name}")
    
    # Initialize workflow data
    workflow_data = {
        'name': workflow_name,
        'user_id': user.user_id,
        'components': {},
        'description': ask_question("Enter workflow description (optional)", "")
    }
    
    # Add components
    print_separator()
    print("Now let's add components to your workflow...")
    
    # First, add the required event trigger
    print("\n--- Adding Event Trigger ---")
    print("Every workflow must start with an event trigger.")
    
    available_events = EventFactory.get_available_events()
    if not available_events:
        print("No event triggers available. Cannot create workflow.")
        return
    
    event_names = list(available_events.keys())
    display_choices("Available Event Triggers", [
        f"{name} - {info['doc']}" for name, info in available_events.items()
    ])
    
    choice_idx = get_choice(event_names, "Select event trigger")
    selected_event = event_names[choice_idx]
    
    # Create component ID for trigger
    trigger_id = "trigger_1"
    
    # Configure event trigger
    trigger_config = configure_event_trigger(selected_event, trigger_id, user.user_id)
    workflow_data['components'][trigger_id] = trigger_config
    
    print(f"Event trigger '{trigger_id}' added successfully!")
    
    # Now add action components
    component_counter = 2
    while True:
        print(f"\n--- Adding Action Component {component_counter} ---")
        
        available_components = ComponentFactory.get_available_components()
        component_names = list(available_components.keys())
        
        display_choices("Available Components", [
            f"{name} - {info['doc']}" for name, info in available_components.items()
        ])
        
        choice_idx = get_choice(component_names, "Select component")
        selected_component = component_names[choice_idx]
        
        # Create component ID
        component_id = f"{selected_component}_{component_counter}"
        
        # Configure component
        component_config = configure_component(selected_component, component_id, user.user_id)
        workflow_data['components'][component_id] = component_config
        
        print(f"Component '{component_id}' added successfully!")
        
        # Ask if user wants to add more components
        if not ask_yes_no("Add another action component?", False):
            break
        
        component_counter += 1
    
    # Save workflow
    print_separator()
    print("Saving workflow...")
    
    try:
        datastore.save_workflow(user.user_id, workflow_name, workflow_data)
        print(f"Workflow '{workflow_name}' created successfully!")
        
        # Display summary
        print_separator()
        print("Workflow Summary:")
        print(f"Name: {workflow_name}")
        print(f"Components: {len(workflow_data['components'])}")
        for comp_id, comp_config in workflow_data['components'].items():
            component_type = comp_config.get('action_type') or comp_config.get('event_type', 'Unknown')
            print(f"  - {comp_id}: {component_type}")
        
    except Exception as e:
        print(f"Error saving workflow: {e}")


def configure_event_trigger(event_name: str, component_id: str, user_id: str) -> Dict[str, Any]:
    """Configure an event trigger."""
    print(f"\nConfiguring {event_name} event trigger...")
    
    # Get event info
    available_events = EventFactory.get_available_events()
    event_info = available_events.get(event_name, {})
    
    # Get component name from event
    component_name = event_info.get('component', '')
    
    # Check if component needs setup
    components_store = ComponentFactory.get_available_components()
    component_info = components_store.get(component_name, {})
    
    setup_name = None
    if component_info.get('type') == 'third_party':
        setup_name = setup_component_if_needed(component_name, component_info, user_id)
    
    # Configure event
    config = configure_action(event_name, event_info)  # Reuse action configuration logic
    
    # Get output keys
    output_mapping = get_output_keys(event_info, component_id)
    
    return {
        'component': component_name,
        'setup_name': setup_name,
        'event_type': event_name,
        'config': config,
        'output_mapping': output_mapping,
        'is_trigger': True
    }


def configure_component(component_name: str, component_id: str, user_id: str) -> Dict[str, Any]:
    """Configure a component with its actions and settings."""
    print(f"\nConfiguring {component_name} component...")
    
    # Check if component needs setup
    components_store = ComponentFactory.get_available_components()
    component_info = components_store.get(component_name, {})
    
    setup_name = None
    if component_info.get('type') == 'third_party':
        setup_name = setup_component_if_needed(component_name, component_info, user_id)
    
    # Get available actions for this component
    available_actions = ActionFactory.get_actions_for_component(component_name)
    
    if not available_actions:
        print(f"No actions available for component {component_name}")
        return {
            'component': component_name,
            'setup_name': setup_name,
            'config': {},
            'output_mapping': {}
        }
    
    # Select action
    action_names = list(available_actions.keys())
    display_choices("Available Actions", [
        f"{name.split('.')[-1]} - {info['doc']}" for name, info in available_actions.items()
    ])
    
    action_idx = get_choice(action_names, "Select action")
    selected_action = action_names[action_idx]
    action_info = available_actions[selected_action]
    
    # Configure action
    config = configure_action(selected_action, action_info)
    
    # Get output keys
    output_mapping = get_output_keys(action_info, component_id)
    
    return {
        'component': component_name,
        'setup_name': setup_name,
        'action_type': selected_action,
        'config': config,
        'output_mapping': output_mapping
    }


def setup_component_if_needed(component_name: str, component_info: Dict[str, Any], user_id: str) -> str:
    """Setup a third-party component if not already configured. Returns the setup name used."""
    existing_setups = datastore.list_component_setups(user_id, component_name)
    
    if existing_setups:
        print(f"\nExisting {component_name} configurations:")
        display_choices("Available Setups", existing_setups)
        
        choices = existing_setups + ["Create new setup"]
        display_choices("Options", choices)
        
        choice_idx = get_choice(choices, "Select an option")
        
        if choice_idx < len(existing_setups):
            # Use existing setup
            selected_setup = existing_setups[choice_idx]
            print(f"Using existing setup: {selected_setup}")
            return selected_setup
        else:
            # Create new setup
            setup_name = ask_question("Enter name for new setup", "default")
            while setup_name in existing_setups:
                print(f"Setup '{setup_name}' already exists.")
                setup_name = ask_question("Enter a different name for new setup")
    else:
        # No existing setups, create first one
        setup_name = ask_question("Enter name for this setup", "default")
    
    print(f"\nSetting up {component_name} component ('{setup_name}')...")
    setup_config = component_info.get('setup', {})
    
    setup_data = {}
    for field_key, field_info in setup_config.items():
        value = ask_question(f"{field_info['name']} ({field_info['doc']})")
        setup_data[field_key] = value
    
    # Save setup
    datastore.save_component_setup(user_id, component_name, setup_data, setup_name)
    print(f"{component_name} setup '{setup_name}' completed!")
    return setup_name


def configure_action(action_name: str, action_info: Dict[str, Any]) -> Dict[str, Any]:
    """Configure an action with its parameters."""
    print(f"\nConfiguring action: {action_name}")
    
    config = {}
    
    # Configure basic parameters
    basic_config = action_info.get('config', {})
    for field_key, field_info in basic_config.items():
        if field_info.get('optional', False):
            if not ask_yes_no(f"Configure {field_info['name']}?", False):
                continue
        
        if field_info.get('type') == 'choice':
            choices = field_info.get('choices', [])
            display_choices(f"Choose {field_info['name']}", choices)
            choice_idx = get_choice(choices, f"Select {field_info['name']}")
            config[field_key] = choices[choice_idx]
        else:
            value = ask_question(f"{field_info['name']} ({field_info['doc']})")
            config[field_key] = value
    
    # Configure conditional parameters
    conditional_config = action_info.get('conditional_config', {})
    for condition, fields in conditional_config.items():
        if config.get('operation') == condition or config.get('action') == condition:
            print(f"\nConfiguring {condition} specific parameters...")
            for field_key, field_info in fields.items():
                value = ask_question(f"{field_info['name']} ({field_info['doc']})")
                config[field_key] = value
    
    return config


def get_output_keys(action_info: Dict[str, Any], component_id: str) -> Dict[str, str]:
    """Get output keys for an action with custom aliases."""
    output_schema = action_info.get('output_schema', {})
    
    if not output_schema:
        return {}
    
    print(f"\nThis action will output the following keys:")
    for key in output_schema.keys():
        print(f"  - {key}")
    
    # Ask user which keys they want to make available and get custom aliases
    output_mapping = {}
    for key in output_schema.keys():
        if ask_yes_no(f"Make '{key}' available to other components?", True):
            custom_key = ask_question(f"Enter custom alias for '{key}' (or press Enter to use '{key}')", key)
            if not custom_key:
                custom_key = key
            output_mapping[key] = custom_key
    
    return output_mapping
