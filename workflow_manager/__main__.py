"""Main entry point for the Workflow Manager application."""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow_manager.cli.utils import display_choices, get_choice, print_header, ask_yes_no
from workflow_manager.cli.create_workflow import create_workflow
from workflow_manager.cli.execute_workflow import execute_workflow, show_workflow_details
from workflow_manager.cli.auth import get_current_user
from workflow_manager.core.datastore import datastore


def setup_logging():
    """Setup logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "workflow_manager.log"),
            logging.StreamHandler()
        ]
    )


def show_main_menu():
    """Display the main menu and handle user choice."""
    while True:
        print_header("Workflow Manager")
        
        user = get_current_user()
        print(f"Welcome, {user.username}!")
        
        # Show user's workflow count
        workflow_count = len(datastore.list_workflows(user.user_id))
        print(f"You have {workflow_count} workflow(s)")
        
        # Main menu options
        options = [
            "Create new workflow",
            "Execute existing workflow",
            "List my workflows",
            "Exit"
        ]
        
        display_choices("What would you like to do?", options)
        
        try:
            choice = get_choice(options, "Select an option")
            
            if choice == 0:  # Create workflow
                create_workflow()
            elif choice == 1:  # Execute workflow
                execute_workflow()
            elif choice == 2:  # List workflows
                list_workflows()
            elif choice == 3:  # Exit
                if ask_yes_no("Are you sure you want to exit?", True):
                    print("Goodbye!")
                    break
            
            # Pause before showing menu again
            if choice != 3:
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            input("Press Enter to continue...")


def list_workflows():
    """List all workflows for the current user."""
    print_header("My Workflows")
    
    user = get_current_user()
    workflows = datastore.list_workflows(user.user_id)
    
    if not workflows:
        print("No workflows found. Create your first workflow!")
        return
    
    print(f"Found {len(workflows)} workflow(s):")
    for i, workflow_name in enumerate(workflows, 1):
        print(f"  {i}. {workflow_name}")
    
    # Ask if user wants to see details of any workflow
    if ask_yes_no("\nView details of a specific workflow?", False):
        display_choices("Select workflow to view", workflows)
        choice = get_choice(workflows, "Select workflow")
        selected_workflow = workflows[choice]
        show_workflow_details(selected_workflow, user.user_id)


def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        
        # Change to the project directory to ensure relative paths work
        project_dir = Path(__file__).parent.parent
        import os
        os.chdir(project_dir)
        
        # Show main menu
        show_main_menu()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
