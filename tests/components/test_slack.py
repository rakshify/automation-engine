import pytest
from unittest.mock import MagicMock, patch, call
import threading
import time
from queue import Queue, Empty

from src.components.slack import Slack, SendMessageAction, ReceiveMessageEvent, SLACK_SDK_AVAILABLE
from src.core.context import WorkflowContext

# Mock the slack_sdk if not available
if not SLACK_SDK_AVAILABLE:
    class WebClient: pass
    class SocketModeClient: pass
    class SocketModeRequest: pass
    class SocketModeResponse: pass

@pytest.fixture
def mock_context():
    return MagicMock(spec=WorkflowContext)

@pytest.fixture
def mock_slack_sdk():
    with patch('src.components.slack.WebClient') as MockWebClient, \
         patch('src.components.slack.SocketModeClient') as MockSocketModeClient, \
         patch('src.components.slack.SocketModeRequest') as MockSocketModeRequest, \
         patch('src.components.slack.SocketModeResponse') as MockSocketModeResponse:
        yield MockWebClient, MockSocketModeClient, MockSocketModeRequest, MockSocketModeResponse

@pytest.fixture
def slack_component(mock_slack_sdk):
    return Slack("test_slack")

class TestSlackComponent:
    def test_setup_success(self, slack_component, mock_slack_sdk):
        MockWebClient, MockSocketModeClient, _, _ = mock_slack_sdk
        mock_web_client_instance = MockWebClient.return_value
        mock_web_client_instance.auth_test.return_value = {"ok": True, "user": "test_bot"}

        slack_component.setup({'bot_token': 'xoxb-test', 'app_token': 'xapp-test'})

        assert slack_component.bot_token == 'xoxb-test'
        assert slack_component.app_token == 'xapp-test'
        MockWebClient.assert_called_once_with(token='xoxb-test')
        MockSocketModeClient.assert_called_once_with(
            app_token='xapp-test',
            web_client=mock_web_client_instance,
            ping_interval=1,
            receive_buffer_size=4096,
            concurrency=20,
            trace_enabled=False,
            all_message_trace_enabled=False,
            ping_pong_trace_enabled=False,
        )
        mock_web_client_instance.auth_test.assert_called_once()

    def test_setup_missing_bot_token(self, slack_component):
        with pytest.raises(ValueError, match="Slack bot token is required for setup"):
            slack_component.setup({'app_token': 'xapp-test'})

    def test_setup_missing_app_token(self, slack_component):
        with pytest.raises(ValueError, match="Slack app token is required for Socket Mode"):
            slack_component.setup({'bot_token': 'xoxb-test'})

    def test_setup_auth_failure(self, slack_component, mock_slack_sdk):
        MockWebClient, _, _, _ = mock_slack_sdk
        mock_web_client_instance = MockWebClient.return_value
        mock_web_client_instance.auth_test.return_value = {"ok": False, "error": "invalid_auth"}

        with pytest.raises(ValueError, match="Slack authentication failed: invalid_auth"):
            slack_component.setup({'bot_token': 'xoxb-test', 'app_token': 'xapp-test'})

    def test_get_channels_success(self, slack_component, mock_slack_sdk):
        MockWebClient, _, _, _ = mock_slack_sdk
        mock_web_client_instance = MockWebClient.return_value
        mock_web_client_instance.conversations_list.side_effect = [
            {"ok": True, "channels": [{'id': 'C1', 'name': 'general'}]},
            {"ok": True, "channels": [{'id': 'C2', 'name': 'private'}]}
        ]
        slack_component.web_client = mock_web_client_instance # Manually set client after setup

        channels = slack_component.get_channels()
        assert channels == [
            {'key': 'C1', 'name': '#general'},
            {'key': 'C2', 'name': '#private (private)'}
        ]
        mock_web_client_instance.conversations_list.assert_has_calls([
            call(types="public_channel"),
            call(types="private_channel")
        ])

    def test_get_channels_no_client(self, slack_component):
        assert slack_component.get_channels() == []

    def test_get_channels_api_error(self, slack_component, mock_slack_sdk):
        MockWebClient, _, _, _ = mock_slack_sdk
        mock_web_client_instance = MockWebClient.return_value
        mock_web_client_instance.conversations_list.side_effect = Exception("API Error")
        slack_component.web_client = mock_web_client_instance

        channels = slack_component.get_channels()
        assert channels == []

class TestSendMessageAction:
    def test_get_field_choices_from_config(self):
        field_config = {'choices': ['choice1', 'choice2']}
        assert SendMessageAction.get_field_choices("channel", field_config) == []

    def test_get_field_choices_dynamic_channels(self, slack_component):
        slack_component.get_channels = MagicMock(return_value=[
            {'key': 'C1', 'name': '#general'}
        ])
        field_config = {}
        choices = SendMessageAction.get_field_choices("channel", field_config, slack_component)
        assert {'key': 'C1', 'name': '#general'} in choices
        assert {'key': 'context', 'name': "📝 From context (use placeholder)"} in choices

    def test_execute_success(self, slack_component, mock_slack_sdk, mock_context):
        MockWebClient, _, _, _ = mock_slack_sdk
        mock_web_client_instance = MockWebClient.return_value
        mock_web_client_instance.chat_postMessage.return_value = {"ok": True, "ts": "123.456", "channel": "C1"}
        slack_component.web_client = mock_web_client_instance

        action = SendMessageAction(slack_component, {'message': 'Hello', 'channel': 'C1'})
        result = action.execute(mock_context)

        mock_web_client_instance.chat_postMessage.assert_called_once_with(
            channel='C1',
            text='Hello'
        )
        assert result['success'] is True
        assert result['message_ts'] == "123.456"

    def test_execute_missing_message(self, slack_component, mock_context):
        slack_component.web_client = MagicMock() # Mock web_client
        action = SendMessageAction(slack_component, {'channel': 'C1'})
        with pytest.raises(ValueError, match="Message is required"):
            action.execute(mock_context)

    def test_execute_missing_channel(self, slack_component, mock_context):
        slack_component.web_client = MagicMock() # Mock web_client
        action = SendMessageAction(slack_component, {'message': 'Hello'})
        with pytest.raises(ValueError, match="Channel is required in action configuration"):
            action.execute(mock_context)

    def test_execute_api_error(self, slack_component, mock_slack_sdk, mock_context):
        MockWebClient, _, _, _ = mock_slack_sdk
        mock_web_client_instance = MockWebClient.return_value
        mock_web_client_instance.chat_postMessage.return_value = {"ok": False, "error": "channel_not_found"}
        slack_component.web_client = mock_web_client_instance

        action = SendMessageAction(slack_component, {'message': 'Hello', 'channel': 'C1'})
        result = action.execute(mock_context)
        assert result['success'] is False
        assert result['error'] == "channel_not_found"

class TestReceiveMessageEvent:
    @pytest.fixture(autouse=True)
    def setup_receive_message_event(self):
        # Ensure the queue is empty before each test
        self.message_queue = Queue()
        with patch('src.components.slack.Queue', return_value=self.message_queue):
            yield

    def test_get_field_choices_from_config(self):
        field_config = {'choices': ['choice1', 'choice2']}
        assert ReceiveMessageEvent.get_field_choices("channel", field_config) == []

    def test_get_field_choices_dynamic_channels(self, slack_component):
        slack_component.get_channels = MagicMock(return_value=[
            {'key': 'C1', 'name': '#general'}
        ])
        field_config = {}
        choices = ReceiveMessageEvent.get_field_choices("channel", field_config, slack_component)
        assert {'key': 'C1', 'name': '#general'} in choices
        assert {'key': 'context', 'name': "📝 From context (use placeholder)"} in choices

    def test_set_workflow_callback(self, slack_component):
        event = ReceiveMessageEvent(slack_component, {})
        mock_callback = MagicMock()
        event.set_workflow_callback(mock_callback)
        assert event.workflow_callback == mock_callback

    def test_handle_message_success(self, slack_component, mock_slack_sdk):
        _, MockSocketModeClient, MockSocketModeRequest, MockSocketModeResponse = mock_slack_sdk
        mock_client = MockSocketModeClient.return_value
        mock_request = MockSocketModeRequest.return_value
        mock_request.type = "events_api"
        mock_request.envelope_id = "env123"
        mock_request.payload = {
            "event": {
                "type": "message",
                "subtype": None,
                "channel": "C1",
                "user": "U1",
                "text": "Hello Slack",
                "ts": "123.456"
            }
        }

        event = ReceiveMessageEvent(slack_component, {'channel': 'C1'})
        event._handle_message(mock_client, mock_request)

        mock_client.send_socket_mode_response.assert_called_once()
        # Further assertions can be made on the call_args if needed, e.g., checking envelope_id
        # assert isinstance(mock_client.send_socket_mode_response.call_args[0][0], MockSocketModeResponse)
        # assert mock_client.send_socket_mode_response.call_args[0][0].envelope_id == "env123"
        assert not self.message_queue.empty()
        message = self.message_queue.get()
        assert message['message_text'] == "Hello Slack"
        assert message['channel'] == "C1"

    def test_handle_message_channel_mismatch(self, slack_component, mock_slack_sdk):
        _, MockSocketModeClient, MockSocketModeRequest, _ = mock_slack_sdk
        mock_client = MockSocketModeClient.return_value
        mock_request = MockSocketModeRequest.return_value
        mock_request.type = "events_api"
        mock_request.payload = {
            "event": {
                "type": "message",
                "subtype": None,
                "channel": "C2",
                "user": "U1",
                "text": "Hello Slack",
                "ts": "123.456"
            }
        }

        event = ReceiveMessageEvent(slack_component, {'channel': 'C1'})
        event._handle_message(mock_client, mock_request)
        assert self.message_queue.empty()

    def test_handle_message_keyword_mismatch(self, slack_component, mock_slack_sdk):
        _, MockSocketModeClient, MockSocketModeRequest, _ = mock_slack_sdk
        mock_client = MockSocketModeClient.return_value
        mock_request = MockSocketModeRequest.return_value
        mock_request.type = "events_api"
        mock_request.payload = {
            "event": {
                "type": "message",
                "subtype": None,
                "channel": "C1",
                "user": "U1",
                "text": "Hello Slack",
                "ts": "123.456"
            }
        }

        event = ReceiveMessageEvent(slack_component, {'channel': 'C1', 'keyword': 'xyz'})
        event._handle_message(mock_client, mock_request)
        assert self.message_queue.empty()

    def test_handle_message_with_callback(self, slack_component, mock_slack_sdk):
        _, MockSocketModeClient, MockSocketModeRequest, _ = mock_slack_sdk
        mock_client = MockSocketModeClient.return_value
        mock_request = MockSocketModeRequest.return_value
        mock_request.type = "events_api"
        mock_request.payload = {
            "event": {
                "type": "message",
                "subtype": None,
                "channel": "C1",
                "user": "U1",
                "text": "Hello Slack",
                "ts": "123.456"
            }
        }

        event = ReceiveMessageEvent(slack_component, {'channel': 'C1'})
        mock_callback = MagicMock()
        event.set_workflow_callback(mock_callback)
        event._handle_message(mock_client, mock_request)
        mock_callback.assert_called_once()

    def test_start_listening_success(self, slack_component, mock_slack_sdk):
        _, MockSocketModeClient, _, _ = mock_slack_sdk
        mock_socket_client_instance = MockSocketModeClient.return_value
        slack_component.socket_client = mock_socket_client_instance

        event = ReceiveMessageEvent(slack_component, {'channel': 'C1'})
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt # Simulate stopping the loop
            event._start_listening()

        mock_socket_client_instance.connect.assert_called_once()
        assert event.is_listening is True
        mock_socket_client_instance.disconnect.assert_called_once()

    def test_execute_persistent_no_callback(self, slack_component, mock_context):
        slack_component.socket_client = MagicMock()
        event = ReceiveMessageEvent(slack_component, {'channel': 'C1', 'timeout': -1})

        # Simulate a message arriving after the listener starts
        def put_message_after_delay():
            time.sleep(0.1) # Small delay to allow listener to start
            event.message_queue.put({'message_text': 'Delayed message'})

        thread = threading.Thread(target=put_message_after_delay)
        thread.start()

        result = event.execute(mock_context)
        assert result['message_text'] == 'Delayed message'
        assert event.is_running() is True # Listener should still be running
        event.stop_listening() # Clean up

    def test_execute_persistent_with_callback(self, slack_component, mock_context):
        slack_component.socket_client = MagicMock()
        event = ReceiveMessageEvent(slack_component, {'channel': 'C1', 'timeout': -1})
        mock_callback = MagicMock()
        event.set_workflow_callback(mock_callback)

        result = event.execute(mock_context)
        assert result['reactive_listener'] is True
        assert event.is_running() is True
        event.stop_listening() # Clean up

    def test_execute_timeout(self, slack_component, mock_context):
        slack_component.socket_client = MagicMock()
        event = ReceiveMessageEvent(slack_component, {'channel': 'C1', 'timeout': 0.1})

        result = event.execute(mock_context)
        assert result['success'] is False
        assert "No matching message received within 0.1 seconds" in result['error']
        event.stop_listening() # Clean up

    def test_stop_listening(self, slack_component, mock_slack_sdk):
        _, MockSocketModeClient, _, _ = mock_slack_sdk
        mock_socket_client_instance = MockSocketModeClient.return_value
        slack_component.socket_client = mock_socket_client_instance

        event = ReceiveMessageEvent(slack_component, {'channel': 'C1'})
        event.is_listening = True # Manually set to true for testing stop
        event.listener_thread = threading.Thread(target=lambda: time.sleep(0.01)) # Dummy thread
        event.listener_thread.start()

        event.stop_listening()
        assert event.is_listening is False
        assert event.stop_event.is_set()
        event.listener_thread.join(timeout=1) # Ensure thread finishes
        assert not event.listener_thread.is_alive()

    def test_is_running(self, slack_component):
        event = ReceiveMessageEvent(slack_component, {})
        assert event.is_running() is False

        event.is_listening = True
        event.listener_thread = threading.Thread(target=lambda: time.sleep(1))
        event.listener_thread.start()
        assert event.is_running() is True
        event.stop_listening() # Clean up