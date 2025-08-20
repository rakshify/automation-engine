"""Main entry point for the Workflow Manager application."""

import sys
import argparse
import logging
import logging.config
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cli.utils import display_choices, get_choice, print_header, ask_yes_no
from src.cli.create_workflow import create_workflow
from src.cli.execute_workflow import execute_workflow, interactive_execute_workflow, get_user_choice, show_workflow_details
from src.cli.auth import get_current_user
from src.core.datastore import datastore
from src.core.logging_filter import set_logging_context, setup_context_filter

# Module-level logger
logger = logging.getLogger(__name__)


def setup_logging():
    """Setup logging configuration from centralized config file."""
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Load logging configuration from JSON file
    config_path = Path("configs/logging_config.json")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Configure logging using dictConfig
        logging.config.dictConfig(config)
        
        # Setup context filter
        setup_context_filter()
        
    except FileNotFoundError:
        # Fallback to basic configuration if config file not found
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "src.log"),
                logging.StreamHandler()
            ]
        )
        logger.warning("Logging config file not found, using basic configuration")
    except Exception as e:
        # Fallback to basic configuration on any error
        logging.basicConfig(level=logging.INFO)
        logger.error(f"Failed to load logging configuration: {e}")


def show_main_menu():
    """Display the main menu and handle user choice."""
    while True:
        print_header("Workflow Manager")
        
        user = get_current_user()
        # Set user context for logging
        set_logging_context(user_id=user.user_id)
        
        # Show user's workflow count
        workflow_count = len(datastore.list_workflows(user.user_id))
        
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
                interactive_execute_workflow()
            elif choice == 2:  # List workflows
                list_workflows()
            elif choice == 3:  # Exit
                if ask_yes_no("Are you sure you want to exit?", True):
                    break
            
            # Pause before showing menu again
            if choice != 3:
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main menu: {e}")
            input("Press Enter to continue...")


def list_workflows():
    """List all workflows for the current user."""
    print_header("My Workflows")
    
    user = get_current_user()
    workflows = datastore.list_workflows(user.user_id)
    
    if not workflows:
        return
    
    for i, workflow_name in enumerate(workflows, 1):
        pass
    
    # Ask if user wants to see details of any workflow
    if ask_yes_no("\nView details of a specific workflow?", False):
        display_choices("Select workflow to view", workflows)
        choice = get_choice(workflows, "Select workflow")
        selected_workflow = workflows[choice]
        show_workflow_details(selected_workflow, user.user_id)


def handle_command_line_execution(menu_option: str, workflow_name: str = None):
    """Handle command-line execution based on provided arguments."""
    if menu_option.lower() in ['execute', 'exec', '2']:
        if workflow_name:
            # Direct execution with provided workflow name
            user = get_current_user()
            available_workflows = datastore.list_workflows(user.user_id)
            
            if workflow_name not in available_workflows:
                logger.error(f"Workflow '{workflow_name}' not found")
                sys.exit(1)
            
            execute_workflow(workflow_name)
        else:
            # Get user choice first, then execute
            workflow_name = get_user_choice()
            if workflow_name:
                execute_workflow(workflow_name)
    
    elif menu_option.lower() in ['create', '1']:
        create_workflow()
    
    elif menu_option.lower() in ['list', '3']:
        list_workflows()
    
    else:
        logger.error(f"Unknown menu option: {menu_option}")
        sys.exit(1)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Workflow Manager - Create and execute automated workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src                           # Interactive mode
  python -m src execute                   # Choose workflow to execute
  python -m src execute my_workflow       # Execute specific workflow
  python -m src create                    # Create new workflow
  python -m src list                      # List all workflows
        """
    )
    
    parser.add_argument(
        'menu_option',
        nargs='?',
        help='Menu option: create, execute, or list'
    )
    
    parser.add_argument(
        'workflow_name',
        nargs='?',
        help='Workflow name (required when menu_option is execute)'
    )
    
    return parser.parse_args()


def main():
    """Main application entry point."""
    try:
        # Setup logging first
        setup_logging()
        logger.info("Workflow Manager starting")
        
        # Change to the project directory to ensure relative paths work
        project_dir = Path(__file__).parent.parent
        import os
        os.chdir(project_dir)
        
        # Parse command-line arguments
        args = parse_arguments()
        
        if args.menu_option:
            # Command-line mode
            handle_command_line_execution(args.menu_option, args.workflow_name)
        else:
            # Interactive mode
            show_main_menu()
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
