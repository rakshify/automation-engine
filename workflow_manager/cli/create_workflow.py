"""Workflow creation CLI flow."""

import json
from typing import Dict, Any, List, Set

from .auth import get_current_user
from .utils import (
    ask_question, ask_yes_no, display_choices, get_choice, 
    get_valid_workflow_name, print_header, print_separator
)
from ..core.datastore import datastore
from ..core.factory import ComponentFactory, ActionFactory


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
    
    component_counter = 1
    while True:
        print(f"\n--- Adding Component {component_counter} ---")
        
        # Show available components
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
        if not ask_yes_no("Add another component?", False):
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
            print(f"  - {comp_id}: {comp_config.get('action_type', 'Unknown')}")
        
    except Exception as e:
        print(f"Error saving workflow: {e}")


def configure_component(component_name: str, component_id: str, user_id: str) -> Dict[str, Any]:
    """Configure a component with its actions and settings."""
    print(f"\nConfiguring {component_name} component...")
    
    # Check if component needs setup
    components_store = ComponentFactory.get_available_components()
    component_info = components_store.get(component_name, {})
    
    if component_info.get('type') == 'third_party':
        setup_component_if_needed(component_name, component_info, user_id)
    
    # Get available actions for this component
    available_actions = ActionFactory.get_actions_for_component(component_name)
    
    if not available_actions:
        print(f"No actions available for component {component_name}")
        return {
            'component': component_name,
            'config': {},
            'output_keys': []
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
    output_keys = get_output_keys(action_info, component_id)
    
    return {
        'component': component_name,
        'action_type': selected_action,
        'config': config,
        'output_keys': output_keys
    }


def setup_component_if_needed(component_name: str, component_info: Dict[str, Any], user_id: str) -> None:
    """Setup a third-party component if not already configured."""
    if datastore.has_component_setup(user_id, component_name):
        print(f"{component_name} is already configured.")
        if not ask_yes_no("Reconfigure?", False):
            return
    
    print(f"\nSetting up {component_name} component...")
    setup_config = component_info.get('setup', {})
    
    setup_data = {}
    for field_key, field_info in setup_config.items():
        value = ask_question(f"{field_info['name']} ({field_info['doc']})")
        setup_data[field_key] = value
    
    # Save setup
    datastore.save_component_setup(user_id, component_name, setup_data)
    print(f"{component_name} setup completed!")


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


def get_output_keys(action_info: Dict[str, Any], component_id: str) -> List[str]:
    """Get output keys for an action."""
    output_schema = action_info.get('output_schema', {})
    
    if not output_schema:
        return []
    
    print(f"\nThis action will output the following keys:")
    for key in output_schema.keys():
        print(f"  - {key}")
    
    # Ask user which keys they want to make available to other components
    selected_keys = []
    for key in output_schema.keys():
        if ask_yes_no(f"Make '{key}' available to other components?", True):
            selected_keys.append(key)
    
    return selected_keys
