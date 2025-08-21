import pytest
from unittest.mock import MagicMock, patch
import requests
import json
from src.components.webhook import Webhook, GetAction, PostAction
from src.core.context import WorkflowContext

@pytest.fixture
def mock_context():
    return MagicMock(spec=WorkflowContext)

@pytest.fixture
def webhook_component():
    return Webhook("test_webhook")

class MockResponse:
    def __init__(self, status_code, text, headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers if headers is not None else {}

class TestWebhook:
    def test_setup(self, webhook_component):
        # setup method does nothing, so just ensure it runs without error
        webhook_component.setup({"key": "value"})
        assert True

class TestGetAction:
    def test_get_field_choices(self):
        field_config_with_choices = {'choices': ['choice1', 'choice2']}
        assert GetAction.get_field_choices("url", field_config_with_choices) == ['choice1', 'choice2']

        field_config_no_choices = {}
        assert GetAction.get_field_choices("url", field_config_no_choices) == []

    def test_execute_success(self, webhook_component, mock_context):
        mock_response = MockResponse(200, "OK", {"Content-Type": "text/plain"})
        with patch('requests.get', return_value=mock_response) as mock_get:
            action = GetAction(webhook_component, {'url': 'http://test.com', 'headers': '{"Accept": "application/json"}'})
            result = action.execute(mock_context)
            mock_get.assert_called_once_with('http://test.com', headers={'Accept': 'application/json'}, timeout=30)
            assert result['status_code'] == 200
            assert result['response_body'] == "OK"
            assert result['headers'] == {'Content-Type': 'text/plain'}
            assert result['success'] is True

    def test_execute_non_200_status(self, webhook_component, mock_context):
        mock_response = MockResponse(404, "Not Found")
        with patch('requests.get', return_value=mock_response) as mock_get:
            action = GetAction(webhook_component, {'url': 'http://test.com'})
            result = action.execute(mock_context)
            assert result['status_code'] == 404
            assert result['response_body'] == "Not Found"
            assert result['success'] is True

    def test_execute_network_error(self, webhook_component, mock_context):
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Connection Error")) as mock_get:
            action = GetAction(webhook_component, {'url': 'http://test.com'})
            result = action.execute(mock_context)
            assert result['status_code'] == 0
            assert result['success'] is False
            assert "Connection Error" in result['error']

    def test_execute_no_url(self, webhook_component, mock_context):
        action = GetAction(webhook_component, {'url': ''})
        with pytest.raises(ValueError, match="URL is required for GET request"):
            action.execute(mock_context)

    def test_execute_invalid_headers(self, webhook_component, mock_context):
        mock_response = MockResponse(200, "OK")
        with patch('requests.get', return_value=mock_response) as mock_get:
            action = GetAction(webhook_component, {'url': 'http://test.com', 'headers': 'invalid json'})
            result = action.execute(mock_context)
            mock_get.assert_called_once_with('http://test.com', headers={}, timeout=30)
            assert result['status_code'] == 200

class TestPostAction:
    def test_get_field_choices(self):
        field_config_with_choices = {'choices': ['choice1', 'choice2']}
        assert PostAction.get_field_choices("url", field_config_with_choices) == ['choice1', 'choice2']

        field_config_no_choices = {}
        assert PostAction.get_field_choices("url", field_config_no_choices) == []

    def test_execute_success_json(self, webhook_component, mock_context):
        mock_response = MockResponse(200, "Created", {"Content-Type": "application/json"})
        with patch('requests.post', return_value=mock_response) as mock_post:
            action = PostAction(webhook_component, {'url': 'http://test.com/post', 'data': '{"key": "value"}', 'headers': '{}'})
            result = action.execute(mock_context)
            mock_post.assert_called_once_with('http://test.com/post', json={'key': 'value'}, headers={'Content-Type': 'application/json'}, timeout=30)
            assert result['status_code'] == 200
            assert result['response_body'] == "Created"
            assert result['success'] is True

    def test_execute_success_form_data(self, webhook_component, mock_context):
        mock_response = MockResponse(200, "OK")
        with patch('requests.post', return_value=mock_response) as mock_post:
            action = PostAction(webhook_component, {'url': 'http://test.com/post', 'data': 'key=value&key2=value2', 'headers': '{"Content-Type": "application/x-www-form-urlencoded"}'})
            result = action.execute(mock_context)
            mock_post.assert_called_once_with('http://test.com/post', data='key=value&key2=value2', headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=30)
            assert result['status_code'] == 200
            assert result['response_body'] == "OK"
            assert result['success'] is True

    def test_execute_non_200_status(self, webhook_component, mock_context):
        mock_response = MockResponse(500, "Internal Server Error")
        with patch('requests.post', return_value=mock_response) as mock_post:
            action = PostAction(webhook_component, {'url': 'http://test.com/post', 'data': '{}'})
            result = action.execute(mock_context)
            assert result['status_code'] == 500
            assert result['response_body'] == "Internal Server Error"
            assert result['success'] is True

    def test_execute_network_error(self, webhook_component, mock_context):
        with patch('requests.post', side_effect=requests.exceptions.RequestException("Timeout")) as mock_post:
            action = PostAction(webhook_component, {'url': 'http://test.com/post', 'data': '{}'})
            result = action.execute(mock_context)
            assert result['status_code'] == 0
            assert result['success'] is False
            assert "Timeout" in result['error']

    def test_execute_no_url(self, webhook_component, mock_context):
        action = PostAction(webhook_component, {'url': ''})
        with pytest.raises(ValueError, match="URL is required for POST request"):
            action.execute(mock_context)

    def test_execute_invalid_headers(self, webhook_component, mock_context):
        mock_response = MockResponse(200, "OK")
        with patch('requests.post', return_value=mock_response) as mock_post:
            action = PostAction(webhook_component, {'url': 'http://test.com', 'headers': 'invalid json'})
            result = action.execute(mock_context)
            mock_post.assert_called_once_with('http://test.com', json={}, headers={'Content-Type': 'application/json'}, timeout=30)
            assert result['status_code'] == 200

    def test_execute_default_content_type(self, webhook_component, mock_context):
        mock_response = MockResponse(200, "OK")
        with patch('requests.post', return_value=mock_response) as mock_post:
            action = PostAction(webhook_component, {'url': 'http://test.com/post', 'data': '{"key": "value"}'})
            result = action.execute(mock_context)
            mock_post.assert_called_once_with('http://test.com/post', json={'key': 'value'}, headers={'Content-Type': 'application/json'}, timeout=30)
            assert result['status_code'] == 200