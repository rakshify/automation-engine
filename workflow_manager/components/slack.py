"""Slack component for Slack integration."""

import json
import requests
from typing import Dict, Any

from ..core.component import BaseComponent, BaseAction, BaseEvent
from ..core.context import WorkflowContext


class Slack(BaseComponent):
    """Component for Slack integration."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.bot_token = None
        self.default_channel = None
    
    def setup(self, setup_config: Dict[str, Any]) -> None:
        """Setup Slack component with bot token and default channel."""
        self.bot_token = setup_config.get('bot_token')
        self.default_channel = setup_config.get('channel')
        
        if not self.bot_token:
            raise ValueError("Slack bot token is required for setup")


class SendMessageAction(BaseAction):
    """Action for sending messages to Slack."""
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Send a message to Slack."""
        if not self.component.bot_token:
            raise ValueError("Slack component not properly configured")
        
        message = self.config.get('message', '')
        channel = self.config.get('channel', self.component.default_channel)
        
        if not message:
            raise ValueError("Message is required")
        
        if not channel:
            raise ValueError("Channel is required (either in config or component setup)")
        
        # Slack API endpoint
        url = "https://slack.com/api/chat.postMessage"
        
        headers = {
            'Authorization': f'Bearer {self.component.bot_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'channel': channel,
            'text': message
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            if response_data.get('ok'):
                return {
                    'message_ts': response_data.get('ts', ''),
                    'channel': response_data.get('channel', channel),
                    'success': True
                }
            else:
                return {
                    'message_ts': '',
                    'channel': channel,
                    'success': False,
                    'error': response_data.get('error', 'Unknown error')
                }
                
        except requests.RequestException as e:
            return {
                'message_ts': '',
                'channel': channel,
                'success': False,
                'error': str(e)
            }


class ReceiveMessageEvent(BaseEvent):
    """Event for receiving messages from Slack."""
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Simulate receiving a message from Slack."""
        # In a real implementation, this would set up a webhook or polling mechanism
        # For now, we'll return a mock event
        
        channel = self.config.get('channel', self.component.default_channel)
        keyword = self.config.get('keyword')
        
        # Mock event data
        return {
            'message_text': f'Mock message containing {keyword}' if keyword else 'Mock message',
            'user_id': 'U1234567890',
            'channel': channel or '#general',
            'timestamp': '1234567890.123456',
            'success': True,
            'note': 'This is a mock event. In production, this would listen for real Slack events.'
        }
