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
        
        # Debug logging
        self.logger.info(f"Initializing workflow: {self.name}")
        self.logger.info(f"Components: {list(self.components.keys()) if self.components else 'None'}")
        
        if not self.components:
            raise ValueError("Workflow has no components")
        
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
                        # Find which component outputs this key (using custom aliases)
                        for other_id, other_config in self.components.items():
                            if other_id != component_id:
                                output_mapping = other_config.get('output_mapping', {})
                                # Check if placeholder matches any custom alias
                                if placeholder in output_mapping.values():
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
            setup_name = component_config.get('setup_name', 'default')
            setup_data = datastore.load_component_setup(self.user_id, component_name, setup_name)
            if setup_data:
                component.setup(setup_data)
        
        return component
    
    def _execute_component(self, component_id: str, component_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single component."""
        self.logger.info(f"Executing component: {component_id}")
        
        try:
            # Create component instance
            self.logger.info(f"🔧 Creating component instance for {component_id}")
            component = self._create_component_instance(component_id, component_config)
            self.logger.info(f"✅ Component instance created: {type(component)}")
            
            # Resolve configuration with context (lock-free for reactive workflows)
            self.logger.info(f"🔧 Resolving config for {component_id}")
            try:
                config = component_config.get('config', {})
                resolved_config = {}
                
                # Manual resolution to avoid threading lock issues
                for key, value in config.items():
                    if isinstance(value, str) and '{{' in value and '}}' in value:
                        # Extract placeholder
                        import re
                        placeholders = re.findall(r'\{\{([^}]+)\}\}', value)
                        resolved_value = value
                        for placeholder in placeholders:
                            # Get value directly without lock
                            context_value = self.context._data.get(placeholder)
                            if context_value is not None:
                                resolved_value = resolved_value.replace(f'{{{{{placeholder}}}}}', str(context_value))
                        resolved_config[key] = resolved_value
                    else:
                        resolved_config[key] = value
                        
            except Exception as e:
                self.logger.error(f"❌ Config resolution failed for {component_id}: {str(e)}")
                return {'success': False, 'error': f'Config resolution failed: {str(e)}'}
                
            self.logger.info(f"✅ Config resolved: {resolved_config}")
            
            # Determine if this is an action or event
            action_type = component_config.get('action_type')
            event_type = component_config.get('event_type')
            is_trigger = component_config.get('is_trigger', False)
            
            if action_type:
                # Create and execute action
                self.logger.info(f"🔧 Creating action: {action_type}")
                action = ActionFactory.create(action_type, component, resolved_config)
                self.logger.info(f"✅ Action created: {type(action)}")
                
                self.logger.info(f"🚀 Executing action...")
                result = action.execute(self.context)
                self.logger.info(f"✅ Action execution completed")
                
            elif event_type:
                # Create and execute event
                event = EventFactory.create(event_type, component, resolved_config)
                result = event.execute(self.context)
                
                # For persistent event listeners, log that they're running
                if is_trigger and hasattr(event, 'is_running') and event.is_running():
                    self.logger.info(f"Event listener {component_id} is running persistently in background")
                    result['persistent_listener'] = True
            else:
                # This might be a legacy component (for backward compatibility)
                result = {'success': True, 'message': 'Component executed successfully'}
            
            # Store output in context using custom aliases
            output_mapping = component_config.get('output_mapping', {})
            for original_key, custom_key in output_mapping.items():
                if original_key in result:
                    self.context.set(custom_key, result[original_key])
            
            self.logger.info(f"Component {component_id} executed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing component {component_id}: {str(e)}")
            raise
    
    def cleanup(self) -> None:
        """Clean up any persistent listeners or resources."""
        self.logger.info("Cleaning up workflow resources...")
        
        for component_id, component_config in self.components.items():
            event_type = component_config.get('event_type')
            if event_type and component_config.get('is_trigger', False):
                try:
                    # Create component instance to access the event
                    component = self._create_component_instance(component_id, component_config)
                    resolved_config = self.context.resolve_config(component_config.get('config', {}))
                    event = EventFactory.create(event_type, component, resolved_config)
                    
                    # Stop persistent listeners
                    if hasattr(event, 'stop_listening'):
                        event.stop_listening()
                        self.logger.info(f"Stopped persistent listener for {component_id}")
                        
                except Exception as e:
                    self.logger.error(f"Error cleaning up component {component_id}: {str(e)}")
    
    def execute(self) -> Dict[str, Any]:
        """Execute the entire workflow."""
        self.logger.info(f"Starting workflow execution: {self.name}")
        
        try:
            # Get execution order
            execution_order = self._topological_sort()
            
            # Check if we have persistent event triggers
            persistent_triggers = []
            action_components = []
            
            for component_id in execution_order:
                component_config = self.components[component_id]
                if component_config.get('is_trigger', False):
                    # Check if it's a persistent event (no timeout or timeout = -1)
                    event_config = component_config.get('config', {})
                    timeout = event_config.get('timeout', -1)
                    if timeout == -1:
                        persistent_triggers.append(component_id)
                    else:
                        # Non-persistent trigger, execute once
                        result = self._execute_component(component_id, component_config)
                        if not result.get('success', False):
                            return {
                                'success': False,
                                'error': f"Trigger {component_id} failed: {result.get('error', 'Unknown error')}",
                                'context': self.context.get_all()
                            }
                else:
                    action_components.append(component_id)
            
            # Handle persistent triggers with reactive execution
            if persistent_triggers:
                return self._execute_reactive_workflow(persistent_triggers, action_components)
            else:
                # Execute all components once (traditional workflow)
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
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'context': self.context.get_all()
            }
    
    def _execute_reactive_workflow(self, persistent_triggers: List[str], action_components: List[str]) -> Dict[str, Any]:
        """Execute workflow with reactive persistent event triggers."""
        self.logger.info(f"Starting reactive workflow with triggers: {persistent_triggers}")
        
        # Set up persistent event listeners with callbacks
        for trigger_id in persistent_triggers:
            component_config = self.components[trigger_id]
            
            # Set up callback for reactive execution BEFORE creating the event
            def create_callback(trigger_id, trigger_config, action_components):
                def workflow_callback(message_data):
                    self.logger.info(f"🔥 Trigger {trigger_id} fired! Executing action components...")
                    
                    # Update context with trigger data
                    output_mapping = trigger_config.get('output_mapping', {})
                    for original_key, custom_key in output_mapping.items():
                        if original_key in message_data:
                            self.context.set(custom_key, message_data[original_key])
                    
                    # Execute all action components using proper workflow execution
                    for component_id in action_components:
                        component_config = self.components[component_id]
                        try:
                            self.logger.info(f"🔧 Executing action component: {component_id}")
                            self.logger.info(f"📋 Component config: {component_config}")
                            result = self._execute_component(component_id, component_config)
                            success = result.get('success', False)
                            self.logger.info(f"✅ Action component {component_id} executed: {success}")
                            self.logger.info(f"📊 Result: {result}")
                            if not success:
                                self.logger.error(f"❌ Action component {component_id} failed: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            self.logger.error(f"❌ Action component {component_id} failed with exception: {str(e)}")
                            import traceback
                            self.logger.error(f"📋 Traceback: {traceback.format_exc()}")
                    self.logger.info(f"🎯 Workflow cycle completed for trigger {trigger_id}")
                
                return workflow_callback
            
            # Create the callback
            callback = create_callback(trigger_id, component_config, action_components)
            
            # Create component instance and event ONCE
            component = self._create_component_instance(trigger_id, component_config)
            resolved_config = self.context.resolve_config(component_config.get('config', {}))
            
            from .factory import EventFactory
            event = EventFactory.create(component_config['event_type'], component, resolved_config)
            
            # Set the callback on the event
            if hasattr(event, 'set_workflow_callback'):
                event.set_workflow_callback(callback)
                self.logger.info(f"✅ Callback set for trigger {trigger_id}")
            
            # Execute the event to start listening
            self.logger.info(f"🚀 Starting persistent listener for {trigger_id}")
            result = event.execute(self.context)
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'error': f"Failed to start persistent trigger {trigger_id}: {result.get('error', 'Unknown error')}",
                    'context': self.context.get_all()
                }
        
        # Return success - the workflow is now reactive
        self.logger.info("🎉 Reactive workflow started successfully! Listeners are active and will execute actions on events.")
        return {
            'success': True,
            'message': 'Reactive workflow started. Event listeners are active and will execute actions on each trigger.',
            'persistent_triggers': persistent_triggers,
            'action_components': action_components,
            'context': self.context.get_all()
        }
    
    @classmethod
    def load_from_file(cls, user_id: str, workflow_name: str) -> Optional['Workflow']:
        """Load a workflow from file."""
        workflow_data = datastore.load_workflow(user_id, workflow_name)
        if not workflow_data:
            return None
        
        return cls(workflow_data, user_id)
