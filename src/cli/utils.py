"""Shared utility functions for the CLI."""

import re
import logging
from typing import List, Dict, Any, Optional

# Module-level logger
logger = logging.getLogger(__name__)


def ask_question(question: str, default: str = None) -> str:
    """Ask a question and get user input."""
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    
    response = input(prompt).strip()
    return response if response else (default or "")


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question and return boolean result."""
    default_str = "Y/n" if default else "y/N"
    
    while True:
        response = input(f"{question} [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        elif response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer 'y' or 'n'")


def display_choices(title: str, choices: List[str], numbered: bool = True) -> None:
    """Display a list of choices."""
    print(f"\n{title}:")
    for i, choice in enumerate(choices, 1):
        if numbered:
            print(f"  {i}. {choice}")
        else:
            print(f"  - {choice}")


def get_choice(choices: List[str], prompt: str = "Select an option") -> int:
    """Get user's choice from a list of options."""
    while True:
        try:
            choice = int(input(f"\n{prompt} (1-{len(choices)}): "))
            if 1 <= choice <= len(choices):
                return choice - 1  # Return 0-based index
            else:
                print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number")


def validate_workflow_name(name: str) -> bool:
    """Validate workflow name format."""
    if not name:
        return False
    
    # Check length
    if len(name) < 1 or len(name) > 50:
        return False
    
    # Check characters (letters, numbers, underscores, hyphens)
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False
    
    return True


def get_valid_workflow_name(existing_names: List[str]) -> str:
    """Get a valid workflow name from user input."""
    while True:
        name = ask_question("Enter workflow name")
        
        if not name:
            continue
        
        if not validate_workflow_name(name):
            print("Invalid workflow name. Use only letters, numbers, underscores, and hyphens (1-50 characters)")
            continue
        
        if name in existing_names:
            if ask_yes_no(f"Workflow '{name}' already exists. Overwrite?", False):
                return name
            else:
                continue
        
        return name


def format_dict(data: Dict[Any, Any], indent: int = 0) -> str:
    """Format a dictionary for display."""
    lines = []
    indent_str = "  " * indent
    
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent_str}{key}:")
            lines.append(format_dict(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{indent_str}{key}: {value}")
        else:
            lines.append(f"{indent_str}{key}: {value}")
    
    return "\n".join(lines)


def select_slack_channel(slack_component) -> str:
    """Select a Slack channel from available channels or use context placeholder."""
    try:
        print("\nFetching available Slack channels...")
        channels = slack_component.get_channels()
        
        if not channels:
            print("No channels found or unable to fetch channels.")
            return ask_question("Enter channel ID or name manually")
        
        # Prepare choices
        channel_choices = []
        channel_map = {}
        
        # Add channels
        for i, channel in enumerate(channels):
            choice_text = channel['name']
            channel_choices.append(choice_text)
            channel_map[i] = channel['id']
        
        # Add "From context" option
        channel_choices.append("📝 From context (use placeholder)")
        from_context_index = len(channel_choices) - 1
        
        # Add manual entry option
        channel_choices.append("✏️ Enter manually")
        manual_entry_index = len(channel_choices) - 1
        
        # Display choices
        display_choices("Select Slack Channel", channel_choices)
        
        # Get user choice
        choice_idx = get_choice(channel_choices, "Select channel option")
        
        if choice_idx == from_context_index:
            # User wants to use context placeholder
            placeholder = ask_question("Enter context placeholder (e.g., channel_name, target_channel)")
            return f"{{{{{placeholder}}}}}"
        elif choice_idx == manual_entry_index:
            # User wants to enter manually
            return ask_question("Enter channel ID or name")
        else:
            # User selected a channel
            return channel_map[choice_idx]
            
    except Exception as e:
        print(f"Error fetching channels: {e}")
        return ask_question("Enter channel ID or name manually")


def print_separator(char: str = "-", length: int = 50) -> None:
    """Print a separator line."""
    print(char * length)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print_separator("=")
    print(f" {text} ")
    print_separator("=")
