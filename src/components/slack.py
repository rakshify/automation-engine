"""Slack component for Slack integration."""

import json
import requests
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from queue import Queue, Empty

from ..core.component import BaseComponent, BaseAction, BaseEvent
from ..core.context import WorkflowContext

try:
    from slack_sdk import WebClient
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest
    from slack_sdk.socket_mode.response import SocketModeResponse
    SLACK_SDK_AVAILABLE = True
except ImportError:
    # Create dummy classes for type hints when SDK is not available
    class WebClient: pass
    class SocketModeClient: pass
    class SocketModeRequest: pass
    class SocketModeResponse: pass
    SLACK_SDK_AVAILABLE = False


class Slack(BaseComponent):
    """Component for Slack integration."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.bot_token = None
        self.signing_secret = None
        self.app_token = None
        self.web_client = None
        self.socket_client = None
        self.logger = logging.getLogger(__name__)
    
    def setup(self, setup_config: Dict[str, Any]) -> None:
        """Setup Slack component with bot token, signing secret, and app token."""
        if not SLACK_SDK_AVAILABLE:
            raise ValueError("Slack SDK not available. Install with: pip install slack-sdk slack-bolt")
        
        self.bot_token = setup_config.get('bot_token')
        self.signing_secret = setup_config.get('signing_secret')
        self.app_token = setup_config.get('app_token')
        
        if not self.bot_token:
            raise ValueError("Slack bot token is required for setup")
        if not self.app_token:
            raise ValueError("Slack app token is required for Socket Mode")
        
        # Initialize Slack clients with optimized settings for minimal latency
        self.web_client = WebClient(token=self.bot_token)
        self.socket_client = SocketModeClient(
            app_token=self.app_token,
            web_client=self.web_client,
            # Optimize for minimal latency
            ping_interval=1,  # Reduce ping interval for faster connection health checks
            receive_buffer_size=4096,  # Increase buffer size to reduce batching delays
            concurrency=20,  # Increase concurrency for faster parallel processing
            trace_enabled=False,  # Disable tracing for better performance
            all_message_trace_enabled=False,  # Disable message tracing
            ping_pong_trace_enabled=False,  # Disable ping/pong tracing
        )
        
        # Test the connection
        try:
            auth_response = self.web_client.auth_test()
            if not auth_response["ok"]:
                raise ValueError(f"Slack authentication failed: {auth_response.get('error', 'Unknown error')}")
            
            self.logger.info(f"Slack setup successful for bot: {auth_response['user']}")
        except Exception as e:
            raise ValueError(f"Failed to authenticate with Slack: {str(e)}")

    def get_channels(self):
        """Get list of available channels."""
        if not self.web_client:
            return []
        
        try:
            channels = []
            
            # Get public channels
            response = self.web_client.conversations_list(types="public_channel")
            for channel in response.get('channels', []):
                channels.append({
                    'key': channel['id'],
                    'name': f"#{channel['name']}"
                })
            
            # Get private channels (only if bot is a member)
            try:
                response = self.web_client.conversations_list(types="private_channel")
                for channel in response.get('channels', []):
                    channels.append({
                        'key': channel['id'],
                        'name': f"#{channel['name']} (private)"
                    })
            except Exception as e:
                self.logger.debug(f"Could not fetch private channels: {e}")
            
            return channels
            
        except Exception as e:
            self.logger.error(f"Failed to get channels: {e}")
            return []


class SendMessageAction(BaseAction):
    """Action for sending messages to Slack."""
    
    @staticmethod
    def get_field_choices(field_name: str, field_config: Dict[str, Any], component_instance=None) -> List[str]:
        """Get available choices for a specific field."""
        # If field has choices in config, return empty (use config choices)
        if 'choices' in field_config:
            return []
        
        # If field is channel and we have component instance, get dynamic choices
        if field_name == 'channel' and component_instance:
            try:
                channels = component_instance.get_channels()
                if channels:
                    choices = channels
                    choices.extend([
                        {'key': 'context', 'name': "📝 From context (use placeholder)"},
                        {'key': 'manual', 'name': "✏️ Enter manually"}
                    ])
                    return choices
            except Exception:
                pass
        return []
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Send a message to Slack."""
        if not self.component.web_client:
            raise ValueError("Slack component not properly configured")
        
        message = self.config.get('message', '')
        channel = self.config.get('channel')
        
        if not message:
            raise ValueError("Message is required")
        
        if not channel:
            raise ValueError("Channel is required in action configuration")
        
        try:
            response = self.component.web_client.chat_postMessage(
                channel=channel,
                text=message
            )
            
            if response["ok"]:
                return {
                    'message_ts': response.get('ts', ''),
                    'channel': response.get('channel', channel),
                    'success': True
                }
            else:
                return {
                    'message_ts': '',
                    'channel': channel,
                    'success': False,
                    'error': response.get('error', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'message_ts': '',
                'channel': channel,
                'success': False,
                'error': str(e)
            }


class ReceiveMessageEvent(BaseEvent):
    """Event for receiving messages from Slack using Socket Mode."""
    
    @staticmethod
    def get_field_choices(field_name: str, field_config: Dict[str, Any], component_instance=None) -> List[str]:
        """Get available choices for a specific field."""
        # If field has choices in config, return empty (use config choices)
        if 'choices' in field_config:
            return []
        
        # If field is channel and we have component instance, get dynamic choices
        if field_name == 'channel' and component_instance:
            try:
                channels = component_instance.get_channels()
                if channels:
                    choices = channels
                    choices.extend([
                        {'key': 'context', 'name': "📝 From context (use placeholder)"},
                        {'key': 'manual', 'name': "✏️ Enter manually"}
                    ])
                    return choices
            except Exception:
                pass
        return []
    
    def __init__(self, component: BaseComponent, config: Dict[str, Any] = None):
        super().__init__(component, config)
        self.message_queue = Queue()
        self.is_listening = False
        self.listener_thread = None
        self.logger = logging.getLogger(__name__)
        self.stop_event = threading.Event()
        self.workflow_callback = None  # Callback for reactive workflow execution
    
    def set_workflow_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function to execute when message is received."""
        self.workflow_callback = callback
    
    def _handle_message(self, client: SocketModeClient, req: SocketModeRequest) -> None:
        """Handle incoming Slack messages."""
        if req.type == "events_api":
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Process the event
            event = req.payload.get("event", {})
            self.logger.info(f"Received event: type={event.get('type')}, subtype={event.get('subtype')}")
            
            if event.get("type") == "message" and event.get("subtype") is None:
                # Filter by channel if specified
                target_channel = self.config.get('channel')
                event_channel = event.get('channel')
                
                self.logger.info(f"Message received - target_channel: {target_channel}, event_channel: {event_channel}")
                
                # Channel filtering: handle both channel names and IDs
                if target_channel and event_channel:
                    # If target_channel starts with #, it's a channel name - need to resolve to ID
                    if target_channel.startswith('#'):
                        # For now, skip channel filtering if target is a name and event is an ID
                        # This allows messages from any channel that matches the name pattern
                        channel_name = target_channel.split(' ')[0]  # Remove "(private)" suffix
                        self.logger.info(f"Channel name filtering: looking for {channel_name}")
                        # We'll accept the message and let it through for now
                    elif target_channel != event_channel:
                        self.logger.info(f"Channel ID mismatch - ignoring message")
                        return
                
                # Filter by keyword if specified
                keyword = self.config.get('keyword')
                message_text = event.get('text', '')
                
                self.logger.info(f"Keyword filter - keyword: {keyword}, message: {message_text}")
                
                if keyword and keyword.lower() not in message_text.lower():
                    self.logger.info(f"Keyword mismatch - ignoring message")
                    return
                
                # Don't process bot messages (temporarily commented for testing)
                # if event.get('bot_id'):
                #     return
                
                self.logger.info(f"Processing message: {message_text}")
                
                # Create message data
                message_data = {
                    'message_text': message_text,
                    'user_id': event.get('user', ''),
                    'channel': event_channel,
                    'timestamp': event.get('ts', ''),
                    'success': True
                }
                
                # Queue the message for traditional workflow
                self.message_queue.put(message_data)
                self.logger.info(f"Received message from {event.get('user')} in {event_channel}: {message_text[:50]}...")
                
                # Execute workflow callback for reactive workflow
                if self.workflow_callback:
                    self.logger.info(f"Executing workflow callback for reactive execution...")
                    try:
                        self.workflow_callback(message_data)
                        self.logger.info(f"Workflow callback executed successfully")
                    except Exception as e:
                        self.logger.error(f"Error in workflow callback: {str(e)}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                else:
                    self.logger.warning(f"No workflow callback set - message queued only")
    
    def _start_listening(self) -> None:
        """Start listening for Slack messages in a separate thread."""
        if not self.component.socket_client:
            raise ValueError("Slack Socket Mode client not initialized")
        
        # Register message handler
        self.component.socket_client.socket_mode_request_listeners.append(self._handle_message)
        
        try:
            # Start the Socket Mode client
            self.component.socket_client.connect()
            self.is_listening = True
            self.logger.info("Started persistent Slack message listener")
            
            # Keep the connection alive until stopped
            while self.is_listening and not self.stop_event.is_set():
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in Slack listener: {str(e)}")
            self.is_listening = False
        finally:
            try:
                self.component.socket_client.disconnect()
                self.logger.info("Disconnected from Slack")
            except:
                pass
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Start listening for Slack messages. By default, runs persistently until stopped."""
        channel = self.config.get('channel')
        keyword = self.config.get('keyword')
        timeout = self.config.get('timeout', -1)  # Default to persistent listening
        
        if not channel:
            raise ValueError("Channel is required in event configuration")
        
        if not self.component.socket_client:
            raise ValueError("Slack component not properly configured for Socket Mode")
        
        self.logger.info(f"Starting Slack listener for channel {channel}" + 
                        (f" with keyword '{keyword}'" if keyword else "") +
                        (" (persistent)" if timeout == -1 else f" (timeout: {timeout}s)"))
        
        # Start listening in a separate thread if not already listening
        if not self.is_listening:
            self.stop_event.clear()
            self.listener_thread = threading.Thread(target=self._start_listening, daemon=True)
            self.listener_thread.start()
            
            # Give the listener a moment to start
            time.sleep(2)
        
        # Handle different timeout scenarios
        if timeout == -1:
            # For persistent listening with reactive workflows, check if we have a callback
            if self.workflow_callback:
                # Reactive workflow - just return success, callback will handle all messages
                self.logger.info("Persistent listener started for reactive workflow. Callback will handle all messages.")
                return {
                    'message_text': '',
                    'user_id': '',
                    'channel': channel,
                    'timestamp': '',
                    'success': True,
                    'reactive_listener': True
                }
            else:
                # Traditional workflow - wait for first message but keep listener running
                self.logger.info("Persistent listener started. Waiting for first message...")
                try:
                    message_data = self.message_queue.get(timeout=None)  # Wait indefinitely for first message
                    self.logger.info("First message received, listener continues running in background")
                    return message_data
                except Exception as e:
                    return {
                        'message_text': '',
                        'user_id': '',
                        'channel': channel,
                        'timestamp': '',
                        'success': False,
                        'error': str(e)
                    }
        else:
            # Timeout-based listening (for testing or specific use cases)
            self.logger.info(f"Waiting for message with {timeout} second timeout...")
            try:
                message_data = self.message_queue.get(timeout=timeout)
                self.logger.info(f"Message received within timeout: {message_data.get('message_text', '')[:50]}...")
                return message_data
            except Empty:
                return {
                    'message_text': '',
                    'user_id': '',
                    'channel': channel,
                    'timestamp': '',
                    'success': False,
                    'error': f'No matching message received within {timeout} seconds'
                }
            except Exception as e:
                return {
                    'message_text': '',
                    'user_id': '',
                    'channel': channel,
                    'timestamp': '',
                    'success': False,
                    'error': str(e)
                }
    
    def stop_listening(self) -> None:
        """Stop the persistent listener."""
        self.logger.info("Stopping Slack message listener...")
        self.is_listening = False
        self.stop_event.set()
        
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=5)
        
        self.logger.info("Slack message listener stopped")
    
    def is_running(self) -> bool:
        """Check if the listener is currently running."""
        return self.is_listening and (self.listener_thread and self.listener_thread.is_alive())
