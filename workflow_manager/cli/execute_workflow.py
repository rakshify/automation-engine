"""Workflow execution CLI flow."""

import json
from typing import Dict, Any, Optional

from .auth import get_current_user
from .utils import display_choices, get_choice, print_header, print_separator, format_dict, ask_yes_no
from ..core.datastore import datastore
from ..core.workflow import Workflow


def get_user_choice() -> Optional[str]:
    """Get user's choice of workflow to execute."""
    user = get_current_user()
    
    # Get available workflows
    available_workflows = datastore.list_workflows(user.user_id)
    
    if not available_workflows:
        print("No workflows found. Create a workflow first.")
        return None
    
    # Display available workflows
    print_separator()
    display_choices("Available Workflows", available_workflows)
    
    # Get user choice
    choice_idx = get_choice(available_workflows, "Select workflow to execute")
    selected_workflow = available_workflows[choice_idx]
    
    return selected_workflow


def execute_workflow(workflow_name: str, auto_confirm: bool = False) -> None:
    """Execute a specific workflow by name."""
    print_header("Execute Workflow")
    
    user = get_current_user()
    print(f"Executing workflow for user: {user.username}")
    print(f"Workflow: {workflow_name}")
    
    # Load and display workflow details
    workflow_data = datastore.load_workflow(user.user_id, workflow_name)
    if not workflow_data:
        print(f"Error: Workflow '{workflow_name}' not found")
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
            action_type = comp_config.get('action_type') or comp_config.get('event_type', 'Unknown')
            print(f"  - {comp_id}: {action_type}")
    
    print_separator()
    
    # Check if this is a reactive workflow
    is_reactive = _is_reactive_workflow(workflow_data)
    
    # Confirm execution (skip for reactive workflows when auto_confirm is True)
    if not auto_confirm or not is_reactive:
        if not ask_yes_no("Execute this workflow?", True):
            print("Execution cancelled.")
            return
    elif is_reactive:
        print("🔄 Reactive workflow detected - starting automatically...")
    
    # Execute workflow
    print("Starting workflow execution...")
    print_separator()
    
    try:
        # Create workflow instance
        workflow = Workflow(workflow_data, user.user_id)
        
        # Check if this is a reactive workflow
        is_reactive = _is_reactive_workflow(workflow_data)
        
        if is_reactive:
            _execute_reactive_workflow(workflow, workflow_name)
        else:
            _execute_traditional_workflow(workflow)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Execution interrupted by user")
        try:
            workflow.cleanup()
            print("✅ Workflow cleaned up successfully")
        except:
            pass
    except Exception as e:
        print(f"❌ Workflow execution failed with exception: {e}")
    
    print_separator()


def _is_reactive_workflow(workflow_data: Dict[str, Any]) -> bool:
    """Check if workflow has persistent event triggers (reactive)."""
    components = workflow_data.get('components', {})
    
    for comp_config in components.values():
        if comp_config.get('is_trigger', False):
            # Check if it's a persistent event (no timeout or timeout = -1)
            event_config = comp_config.get('config', {})
            timeout = event_config.get('timeout', -1)
            if timeout == -1:
                return True
    
    return False


def _execute_reactive_workflow(workflow: 'Workflow', workflow_name: str) -> None:
    """Execute a reactive workflow with persistent monitoring."""
    print("🔄 Detected reactive workflow with persistent event listeners")
    print("📱 This workflow will run continuously and react to events")
    print("⚠️  Press Ctrl+C to stop the workflow")
    print_separator()
    
    # Execute workflow (this sets up the reactive listeners)
    result = workflow.execute()
    
    if not result.get('success'):
        print("❌ Failed to start reactive workflow!")
        error = result.get('error', 'Unknown error')
        print(f"Error: {error}")
        return
    
    print("✅ Reactive workflow started successfully!")
    print(f"📊 Persistent triggers: {result.get('persistent_triggers', [])}")
    print(f"⚙️  Action components: {result.get('action_components', [])}")
    print()
    print("🎯 Workflow is now active and waiting for events...")
    print("📝 Live execution logs will appear below:")
    print_separator()
    
    try:
        # Keep the workflow running and show live status
        import time
        start_time = time.time()
        
        while True:
            time.sleep(1)
            
            # Show periodic status (every 30 seconds)
            if int(time.time() - start_time) % 30 == 0:
                elapsed = int(time.time() - start_time)
                print(f"⏰ Workflow '{workflow_name}' has been running for {elapsed} seconds...")
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping reactive workflow...")
        workflow.cleanup()
        print("✅ Reactive workflow stopped successfully")


def _execute_traditional_workflow(workflow: 'Workflow') -> None:
    """Execute a traditional (non-reactive) workflow."""
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


def interactive_execute_workflow() -> None:
    """Interactive workflow execution flow (legacy function for backward compatibility)."""
    workflow_name = get_user_choice()
    if workflow_name:
        execute_workflow(workflow_name)


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
            action_type = comp_config.get('action_type') or comp_config.get('event_type', 'Unknown')
            print(f"    Action/Event: {action_type}")
            
            config = comp_config.get('config', {})
            if config:
                print("    Configuration:")
                for key, value in config.items():
                    print(f"      {key}: {value}")
            
            output_mapping = comp_config.get('output_mapping', {})
            if output_mapping:
                print(f"    Output Mapping: {output_mapping}")
    
    print_separator()
