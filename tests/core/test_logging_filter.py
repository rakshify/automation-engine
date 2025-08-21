import pytest
import logging
import threading
import time
from unittest.mock import MagicMock, patch

from src.core.logging_filter import ContextFilter, set_logging_context, clear_logging_context, setup_context_filter

@pytest.fixture
def context_filter_instance():
    # Create a fresh instance for each test to ensure isolation
    return ContextFilter()

@pytest.fixture
def mock_logger_and_handler():
    mock_logger = MagicMock(spec=logging.Logger)
    mock_handler = MagicMock(spec=logging.Handler)
    mock_logger.handlers = [mock_handler]
    with patch('logging.getLogger', return_value=mock_logger):
        yield mock_logger, mock_handler

class TestContextFilter:
    def test_filter_adds_defaults(self, context_filter_instance):
        record = MagicMock(spec=logging.LogRecord)
        assert context_filter_instance.filter(record) is True
        assert record.user == 'unknown'
        assert record.workflow == 'none'
        assert record.context_keys == '[]'

    def test_set_user(self, context_filter_instance):
        record = MagicMock(spec=logging.LogRecord)
        context_filter_instance.set_user("test_user")
        context_filter_instance.filter(record)
        assert record.user == 'test_user'

    def test_set_workflow(self, context_filter_instance):
        record = MagicMock(spec=logging.LogRecord)
        context_filter_instance.set_workflow("test_workflow")
        context_filter_instance.filter(record)
        assert record.workflow == 'test_workflow'

    def test_set_context_keys(self, context_filter_instance):
        record = MagicMock(spec=logging.LogRecord)
        context_filter_instance.set_context_keys(["key1", "key2"])
        context_filter_instance.filter(record)
        assert record.context_keys == "['key1', 'key2']"

    def test_clear_context(self, context_filter_instance):
        record = MagicMock(spec=logging.LogRecord)
        context_filter_instance.set_user("test_user")
        context_filter_instance.set_workflow("test_workflow")
        context_filter_instance.set_context_keys(["key1"])

        context_filter_instance.clear_context()
        context_filter_instance.filter(record)
        assert record.user == 'unknown'
        assert record.workflow == 'none'
        assert record.context_keys == '[]'

    def test_thread_isolation(self, context_filter_instance):
        # This test uses the global context_filter instance as it's what the module uses
        # We need to ensure it's reset before and after the test
        clear_logging_context() # Clear any previous state

        def thread_func(user_id, workflow_name, context_keys_list):
            set_logging_context(user_id=user_id, workflow_name=workflow_name, context_keys=context_keys_list)
            time.sleep(0.01) # Simulate some work
            record = MagicMock(spec=logging.LogRecord)
            context_filter_instance.filter(record)
            assert record.user == user_id
            assert record.workflow == workflow_name
            assert record.context_keys == str(context_keys_list)
            clear_logging_context()

        thread1 = threading.Thread(target=thread_func, args=("user1", "wf1", ["k1"]))
        thread2 = threading.Thread(target=thread_func, args=("user2", "wf2", ["k2", "k3"]))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Verify main thread context is unaffected
        record = MagicMock(spec=logging.LogRecord)
        context_filter_instance.filter(record)
        assert record.user == 'unknown'
        assert record.workflow == 'none'
        assert record.context_keys == '[]'

class TestGlobalFunctions:
    def test_set_logging_context(self, context_filter_instance):
        # Patch the global instance to use our test instance
        with patch('src.core.logging_filter.context_filter', new=context_filter_instance):
            set_logging_context(user_id="global_user", workflow_name="global_wf", context_keys=["g1"])
            record = MagicMock(spec=logging.LogRecord)
            context_filter_instance.filter(record)
            assert record.user == 'global_user'
            assert record.workflow == 'global_wf'
            assert record.context_keys == "['g1']"

    def test_clear_logging_context(self, context_filter_instance):
        with patch('src.core.logging_filter.context_filter', new=context_filter_instance):
            set_logging_context(user_id="temp_user")
            clear_logging_context()
            record = MagicMock(spec=logging.LogRecord)
            context_filter_instance.filter(record)
            assert record.user == 'unknown'

    def test_setup_context_filter(self, mock_logger_and_handler):
        mock_logger, mock_handler = mock_logger_and_handler
        setup_context_filter()
        mock_logger.addFilter.assert_called_once_with(logging.Filter())
        mock_handler.addFilter.assert_called_once_with(logging.Filter())
        # Verify that the actual context_filter instance is passed
        assert isinstance(mock_logger.addFilter.call_args[0][0], ContextFilter)
        assert isinstance(mock_handler.addFilter.call_args[0][0], ContextFilter)
