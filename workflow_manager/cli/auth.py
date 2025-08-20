"""Authentication logic for the CLI."""

from typing import Dict, Any
import os
import getpass


class User:
    """User object representing the current user."""
    
    def __init__(self, user_id: str, username: str, email: str = None):
        self.user_id = user_id
        self.username = username
        self.email = email or f"{username}@example.com"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email
        }


def get_current_user() -> User:
    """Get the current user (mock implementation)."""
    # In a real implementation, this would handle actual authentication
    # For now, we'll use the system username
    
    try:
        username = getpass.getuser()
    except Exception:
        username = os.environ.get('USER', os.environ.get('USERNAME', 'anonymous'))
    
    # Create a simple user ID based on username
    user_id = f"user_{username.lower().replace(' ', '_')}"
    
    return User(user_id, username)
