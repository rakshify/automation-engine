"""Workflow execution CLI flow."""

import json
from typing import Dict, Any

from .auth import get_current_user
from .utils import display_choices, get_choice, print_header, print_separator, format_dict
from ..core.datastore import datastore
from ..core.workflow import Workflow


def execute_workflow() -> None:
    """Interactive workflow execution flow."""
    print_header("Execute Workflow")
    
    user = get_current_user()
    print(f"Executing workflow for user: {user.username}")
    
    # Get available workflows
    available_workflows = datastore.list_workflows(user.user_id)
    
    if not available_workflows:
        print("No workflows found. Create a workflow first.")
        return
    
    # Display available workflows
    print_separator()
    display_choices("Available Workflows", available_workflows)
    
    # Get user choice
    choice_idx = get_choice(available_workflows, "Select workflow to execute")
    selected_workflow = available_workflows[choice_idx]
    
    print(f"\nSelected workflow: {selected_workflow}")
    
    # Load and display workflow details
    workflow_data = datastore.load_workflow(user.user_id, selected_workflow)
    if not workflow_data:
        print("Error: Could not load workflow data")
        return
    
    print_separator()
    print("Workflow Details:")
    print(f"Name: {workflow_data.get('name', 'Unknown')}")
    print(f"Description: {workflow_data.get('description', 'No description')}")
    print(f"Components: {len(workflow_data.get('components', {}))}")
    
    # Show component details
    components = workflow_data.get('components', {})
    if components:
        print("\nComponents:")
        for comp_id, comp_config in components.items():
            action_type = comp_config.get('action_type', 'Unknown')
            print(f"  - {comp_id}: {action_type}")
    
    print_separator()
    
    # Confirm execution
    from .utils import ask_yes_no
    if not ask_yes_no("Execute this workflow?", True):
        print("Execution cancelled.")
        return
    
    # Execute workflow
    print("Starting workflow execution...")
    print_separator()
    
    try:
        # Create workflow instance
        workflow = Workflow(workflow_data, user.user_id)
        
        # Execute
        result = workflow.execute()
        
        # Display results
        print_separator()
        if result.get('success'):
            print("✅ Workflow executed successfully!")
            
            # Show results
            results = result.get('results', {})
            if results:
                print("\nExecution Results:")
                for comp_id, comp_result in results.items():
                    print(f"\n{comp_id}:")
                    if isinstance(comp_result, dict):
                        print(format_dict(comp_result, 1))
                    else:
                        print(f"  {comp_result}")
            
            # Show final context
            context = result.get('context', {})
            if context:
                print("\nFinal Context:")
                print(format_dict(context, 1))
        else:
            print("❌ Workflow execution failed!")
            error = result.get('error', 'Unknown error')
            print(f"Error: {error}")
            
            # Show context for debugging
            context = result.get('context', {})
            if context:
                print("\nContext at failure:")
                print(format_dict(context, 1))
    
    except Exception as e:
        print(f"❌ Workflow execution failed with exception: {e}")
    
    print_separator()


def show_workflow_details(workflow_name: str, user_id: str) -> None:
    """Show detailed information about a workflow."""
    workflow_data = datastore.load_workflow(user_id, workflow_name)
    if not workflow_data:
        print("Workflow not found")
        return
    
    print_header(f"Workflow: {workflow_name}")
    
    print(f"Description: {workflow_data.get('description', 'No description')}")
    print(f"User: {workflow_data.get('user_id', 'Unknown')}")
    
    components = workflow_data.get('components', {})
    print(f"Components: {len(components)}")
    
    if components:
        print("\nComponent Details:")
        for comp_id, comp_config in components.items():
            print(f"\n  {comp_id}:")
            print(f"    Component: {comp_config.get('component', 'Unknown')}")
            print(f"    Action: {comp_config.get('action_type', 'Unknown')}")
            
            config = comp_config.get('config', {})
            if config:
                print("    Configuration:")
                for key, value in config.items():
                    print(f"      {key}: {value}")
            
            output_keys = comp_config.get('output_keys', [])
            if output_keys:
                print(f"    Output Keys: {', '.join(output_keys)}")
    
    print_separator()
