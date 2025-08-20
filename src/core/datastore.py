"""Data storage and retrieval logic for user profiles, setups, and workflows."""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


class DataStore:
    """Handles data storage and retrieval for the workflow manager."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "users").mkdir(exist_ok=True)
        (self.data_dir / "workflows").mkdir(exist_ok=True)
        (self.data_dir / "setups").mkdir(exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get the file path for a user's data."""
        return self.data_dir / "users" / f"{user_id}.json"
    
    def _get_workflow_file(self, user_id: str, workflow_name: str) -> Path:
        """Get the file path for a workflow."""
        return self.data_dir / "workflows" / f"{user_id}_{workflow_name}.json"
    
    def _get_setup_file(self, user_id: str, component_name: str, setup_name: str = "default") -> Path:
        """Get the file path for a component setup."""
        return self.data_dir / "setups" / f"{user_id}_{component_name}_{setup_name}.json"
    
    def _get_setup_dir(self, user_id: str, component_name: str) -> Path:
        """Get the directory path for component setups."""
        return self.data_dir / "setups"
    
    def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Save a user profile."""
        user_file = self._get_user_file(user_id)
        with open(user_file, 'w') as f:
            json.dump(profile, f, indent=2)
    
    def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load a user profile."""
        user_file = self._get_user_file(user_id)
        if not user_file.exists():
            return None
        
        with open(user_file, 'r') as f:
            return json.load(f)
    
    def save_workflow(self, user_id: str, workflow_name: str, workflow_data: Dict[str, Any]) -> None:
        """Save a workflow definition."""
        workflow_file = self._get_workflow_file(user_id, workflow_name)
        with open(workflow_file, 'w') as f:
            json.dump(workflow_data, f, indent=2)
    
    def load_workflow(self, user_id: str, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Load a workflow definition."""
        workflow_file = self._get_workflow_file(user_id, workflow_name)
        if not workflow_file.exists():
            return None
        
        with open(workflow_file, 'r') as f:
            return json.load(f)
    
    def list_workflows(self, user_id: str) -> List[str]:
        """List all workflows for a user."""
        workflows = []
        workflow_dir = self.data_dir / "workflows"
        prefix = f"{user_id}_"
        
        for file_path in workflow_dir.glob(f"{prefix}*.json"):
            workflow_name = file_path.stem[len(prefix):]
            workflows.append(workflow_name)
        
        return sorted(workflows)
    
    def workflow_exists(self, user_id: str, workflow_name: str) -> bool:
        """Check if a workflow exists."""
        workflow_file = self._get_workflow_file(user_id, workflow_name)
        return workflow_file.exists()
    
    def save_component_setup(self, user_id: str, component_name: str, setup_data: Dict[str, Any], setup_name: str = "default") -> None:
        """Save component setup configuration with a name."""
        setup_file = self._get_setup_file(user_id, component_name, setup_name)
        with open(setup_file, 'w') as f:
            json.dump(setup_data, f, indent=2)
    
    def load_component_setup(self, user_id: str, component_name: str, setup_name: str = "default") -> Optional[Dict[str, Any]]:
        """Load component setup configuration by name."""
        setup_file = self._get_setup_file(user_id, component_name, setup_name)
        if not setup_file.exists():
            return None
        
        with open(setup_file, 'r') as f:
            return json.load(f)
    
    def has_component_setup(self, user_id: str, component_name: str, setup_name: str = "default") -> bool:
        """Check if component setup exists by name."""
        setup_file = self._get_setup_file(user_id, component_name, setup_name)
        return setup_file.exists()
    
    def list_component_setups(self, user_id: str, component_name: str) -> List[str]:
        """List all setup names for a component."""
        setup_names = []
        setup_dir = self._get_setup_dir(user_id, component_name)
        prefix = f"{user_id}_{component_name}_"
        suffix = ".json"
        
        for file_path in setup_dir.glob(f"{prefix}*.json"):
            filename = file_path.name
            if filename.startswith(prefix) and filename.endswith(suffix):
                setup_name = filename[len(prefix):-len(suffix)]
                setup_names.append(setup_name)
        
        return sorted(setup_names)
    
    def delete_component_setup(self, user_id: str, component_name: str, setup_name: str) -> bool:
        """Delete a component setup configuration."""
        setup_file = self._get_setup_file(user_id, component_name, setup_name)
        if setup_file.exists():
            setup_file.unlink()
            return True
        return False


# Global datastore instance
datastore = DataStore()
