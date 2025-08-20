"""Workflow and DAG execution engine."""

from typing import Dict, Any, List, Set, Optional
from collections import defaultdict, deque
import logging

from .context import WorkflowContext
from .factory import ComponentFactory, ActionFactory, EventFactory
from .datastore import datastore


class Workflow:
    """Workflow execution engine with DAG support."""
    
    def __init__(self, workflow_data: Dict[str, Any], user_id: str):
        self.workflow_data = workflow_data
        self.user_id = user_id
        self.context = WorkflowContext()
        self.logger = logging.getLogger(__name__)
        
        # Parse workflow structure
        self.name = workflow_data.get('name', 'Unnamed Workflow')
        self.components = workflow_data.get('components', {})
        self.dependencies = self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build dependency graph from component configurations."""
        dependencies = defaultdict(set)
        
        for component_id, component_config in self.components.items():
            # Check for context placeholders in configuration
            config = component_config.get('config', {})
            for key, value in config.items():
                if isinstance(value, str) and '{{' in value and '}}' in value:
                    # Extract referenced keys
                    import re
                    placeholders = re.findall(r'\{\{([^}]+)\}\}', value)
                    for placeholder in placeholders:
                        # Find which component outputs this key
                        for other_id, other_config in self.components.items():
                            if other_id != component_id:
                                output_keys = other_config.get('output_keys', [])
                                if placeholder in output_keys:
                                    dependencies[component_id].add(other_id)
        
        return dict(dependencies)
    
    def _topological_sort(self) -> List[str]:
        """Perform topological sort to determine execution order."""
        # Kahn's algorithm
        in_degree = defaultdict(int)
        
        # Calculate in-degrees
        for component_id in self.components:
            in_degree[component_id] = 0
        
        for component_id, deps in self.dependencies.items():
            in_degree[component_id] = len(deps)
        
        # Queue for components with no dependencies
        queue = deque([comp_id for comp_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Update in-degrees for dependent components
            for component_id, deps in self.dependencies.items():
                if current in deps:
                    in_degree[component_id] -= 1
                    if in_degree[component_id] == 0:
                        queue.append(component_id)
        
        # Check for cycles
        if len(result) != len(self.components):
            raise ValueError("Circular dependency detected in workflow")
        
        return result
    
    def _create_component_instance(self, component_id: str, component_config: Dict[str, Any]):
        """Create and setup a component instance."""
        component_name = component_config['component']
        
        # Create component
        component = ComponentFactory.create(component_name)
        
        # Load and apply setup if it's a third-party component
        components_store = ComponentFactory.get_available_components()
        if components_store.get(component_name, {}).get('type') == 'third_party':
            setup_data = datastore.load_component_setup(self.user_id, component_name)
            if setup_data:
                component.setup(setup_data)
        
        return component
    
    def _execute_component(self, component_id: str, component_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single component."""
        self.logger.info(f"Executing component: {component_id}")
        
        try:
            # Create component instance
            component = self._create_component_instance(component_id, component_config)
            
            # Resolve configuration with context
            resolved_config = self.context.resolve_config(component_config.get('config', {}))
            
            # Determine if this is an action or event
            action_type = component_config.get('action_type')
            if action_type:
                # Create and execute action
                action = ActionFactory.create(action_type, component, resolved_config)
                result = action.execute(self.context)
            else:
                # This might be an event trigger (for future implementation)
                result = {'success': True, 'message': 'Component executed successfully'}
            
            # Store output in context
            output_keys = component_config.get('output_keys', [])
            for key in output_keys:
                if key in result:
                    self.context.set(key, result[key])
            
            self.logger.info(f"Component {component_id} executed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing component {component_id}: {str(e)}")
            raise
    
    def execute(self) -> Dict[str, Any]:
        """Execute the entire workflow."""
        self.logger.info(f"Starting workflow execution: {self.name}")
        
        try:
            # Get execution order
            execution_order = self._topological_sort()
            
            # Execute components in order
            results = {}
            for component_id in execution_order:
                component_config = self.components[component_id]
                result = self._execute_component(component_id, component_config)
                results[component_id] = result
            
            self.logger.info(f"Workflow {self.name} completed successfully")
            return {
                'success': True,
                'results': results,
                'context': self.context.get_all()
            }
            
        except Exception as e:
            self.logger.error(f"Workflow {self.name} failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'context': self.context.get_all()
            }
    
    @classmethod
    def load_from_file(cls, user_id: str, workflow_name: str) -> Optional['Workflow']:
        """Load a workflow from file."""
        workflow_data = datastore.load_workflow(user_id, workflow_name)
        if not workflow_data:
            return None
        
        return cls(workflow_data, user_id)
