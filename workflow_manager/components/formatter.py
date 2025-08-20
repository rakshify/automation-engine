"""Formatter component for text and number formatting operations."""

import urllib.parse
import random
import logging
from typing import Dict, Any

from ..core.component import BaseComponent, BaseAction
from ..core.context import WorkflowContext


class Formatter(BaseComponent):
    """Component for text and number formatting operations."""
    
    def __init__(self, component_id: str, config: Dict[str, Any] = None):
        super().__init__(component_id, config)
        self.logger = logging.getLogger(__name__)
    
    def setup(self, setup_config: Dict[str, Any]) -> None:
        """Formatter is a built-in component and doesn't require setup."""
        pass


class TextAction(BaseAction):
    """Action for text formatting operations."""
    
    def __init__(self, component: BaseComponent, config: Dict[str, Any] = None):
        super().__init__(component, config)
        self.logger = logging.getLogger(__name__)
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute text formatting operation."""
        operation = self.config.get('operation')
        input_text = self.config.get('input', '')
        
        if operation == 'urlencode':
            result = urllib.parse.quote(input_text)
        elif operation == 'replace':
            old_value = self.config.get('old_value', '')
            new_value = self.config.get('new_value', '')
            result = input_text.replace(old_value, new_value)
        elif operation == 'strip_prefix':
            prefix = self.config.get('prefix', '')
            if input_text.startswith(prefix):
                result = input_text[len(prefix):]
            else:
                result = input_text
        else:
            raise ValueError(f"Unknown text operation: {operation}")

        self.logger.info(f"Formatted text '{input_text}' to '{result}' using operation '{operation}'")
        print(f"🔧 Formatter: '{input_text}' → '{result}' (operation: {operation})", flush=True)  # Force immediate output
        return {
            'formatted_text': result,
            'success': True
        }


class NumberAction(BaseAction):
    """Action for number formatting operations."""
    
    def __init__(self, component: BaseComponent, config: Dict[str, Any] = None):
        super().__init__(component, config)
        self.logger = logging.getLogger(__name__)
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute number formatting operation."""
        operation = self.config.get('operation')
        
        if operation == 'format_currency':
            amount = self.config.get('amount', '0')
            currency = self.config.get('currency', 'USD')
            
            # Convert to float if it's a string
            try:
                amount_float = float(amount)
            except (ValueError, TypeError):
                amount_float = 0.0
            
            # Simple currency formatting
            if currency.upper() == 'USD':
                result = f"${amount_float:,.2f}"
            elif currency.upper() == 'EUR':
                result = f"€{amount_float:,.2f}"
            elif currency.upper() == 'GBP':
                result = f"£{amount_float:,.2f}"
            else:
                result = f"{amount_float:,.2f} {currency.upper()}"
                
        elif operation == 'random_number':
            min_value = self.config.get('min_value', 0)
            max_value = self.config.get('max_value', 100)
            
            try:
                min_val = int(min_value)
                max_val = int(max_value)
                result = str(random.randint(min_val, max_val))
            except (ValueError, TypeError):
                result = str(random.randint(0, 100))
        else:
            raise ValueError(f"Unknown number operation: {operation}")
        
        return {
            'formatted_number': result,
            'success': True
        }
