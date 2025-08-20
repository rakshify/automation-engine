"""Webhook component for making HTTP requests."""

import json
import requests
from typing import Dict, Any

from ..core.component import BaseComponent, BaseAction
from ..core.context import WorkflowContext


class Webhook(BaseComponent):
    """Component for making HTTP requests to external APIs."""
    
    def setup(self, setup_config: Dict[str, Any]) -> None:
        """Webhook is a built-in component and doesn't require setup."""
        pass


class GetAction(BaseAction):
    """Action for making HTTP GET requests."""
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute HTTP GET request."""
        url = self.config.get('url', '')
        headers_str = self.config.get('headers', '{}')
        
        if not url:
            raise ValueError("URL is required for GET request")
        
        # Parse headers
        try:
            headers = json.loads(headers_str) if headers_str else {}
        except json.JSONDecodeError:
            headers = {}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            return {
                'status_code': response.status_code,
                'response_body': response.text,
                'headers': dict(response.headers),
                'success': True
            }
            
        except requests.RequestException as e:
            return {
                'status_code': 0,
                'response_body': '',
                'headers': {},
                'success': False,
                'error': str(e)
            }


class PostAction(BaseAction):
    """Action for making HTTP POST requests."""
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute HTTP POST request."""
        url = self.config.get('url', '')
        data = self.config.get('data', '')
        headers_str = self.config.get('headers', '{}')
        
        if not url:
            raise ValueError("URL is required for POST request")
        
        # Parse headers
        try:
            headers = json.loads(headers_str) if headers_str else {}
        except json.JSONDecodeError:
            headers = {}
        
        # Set default content type if not specified
        if 'Content-Type' not in headers and 'content-type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        try:
            # Try to parse data as JSON, otherwise send as string
            try:
                json_data = json.loads(data) if data else {}
                response = requests.post(url, json=json_data, headers=headers, timeout=30)
            except json.JSONDecodeError:
                response = requests.post(url, data=data, headers=headers, timeout=30)
            
            return {
                'status_code': response.status_code,
                'response_body': response.text,
                'headers': dict(response.headers),
                'success': True
            }
            
        except requests.RequestException as e:
            return {
                'status_code': 0,
                'response_body': '',
                'headers': {},
                'success': False,
                'error': str(e)
            }
