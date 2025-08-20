"""Shared utility functions for the CLI."""

import re
from typing import List, Dict, Any, Optional


def ask_question(question: str, default: str = None) -> str:
    """Ask a question and get user input."""
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    
    response = input(prompt).strip()
    return response if response else (default or "")


def ask_yes_no(question: str, default: bool = None) -> bool:
    """Ask a yes/no question."""
    if default is True:
        prompt = f"{question} [Y/n]: "
    elif default is False:
        prompt = f"{question} [y/N]: "
    else:
        prompt = f"{question} [y/n]: "
    
    while True:
        response = input(prompt).strip().lower()
        
        if not response and default is not None:
            return default
        
        if response in ['y', 'yes']:
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


def get_choice(choices: List[str], prompt: str = "Enter your choice") -> int:
    """Get a choice from a numbered list."""
    while True:
        try:
            choice = int(input(f"{prompt} (1-{len(choices)}): "))
            if 1 <= choice <= len(choices):
                return choice - 1  # Return 0-based index
            else:
                print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number")


def validate_workflow_name(name: str) -> bool:
    """Validate workflow name (alphanumeric, underscores, hyphens only)."""
    if not name:
        return False
    
    # Check if name contains only allowed characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False
    
    # Check length
    if len(name) < 1 or len(name) > 50:
        return False
    
    return True


def get_valid_workflow_name(existing_names: List[str] = None) -> str:
    """Get a valid and unique workflow name from user."""
    existing_names = existing_names or []
    
    while True:
        name = ask_question("Enter workflow name")
        
        if not validate_workflow_name(name):
            print("Invalid workflow name. Use only letters, numbers, underscores, and hyphens (1-50 characters)")
            continue
        
        if name in existing_names:
            print(f"Workflow '{name}' already exists. Please choose a different name.")
            continue
        
        return name


def format_dict(data: Dict[str, Any], indent: int = 0) -> str:
    """Format a dictionary for display."""
    lines = []
    prefix = "  " * indent
    
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(format_dict(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    
    return "\n".join(lines)


def print_separator(char: str = "-", length: int = 50) -> None:
    """Print a separator line."""
    print(char * length)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print_separator("=")
    print(f" {text} ")
    print_separator("=")
