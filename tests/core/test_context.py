import pytest
import threading
import time
from src.core.context import WorkflowContext

@pytest.fixture
def workflow_context():
    return WorkflowContext()

class TestWorkflowContext:
    def test_set_and_get(self, workflow_context):
        workflow_context.set("key1", "value1")
        assert workflow_context.get("key1") == "value1"

    def test_get_default_value(self, workflow_context):
        assert workflow_context.get("non_existent_key", "default") == "default"
        assert workflow_context.get("non_existent_key") is None

    def test_update(self, workflow_context):
        workflow_context.set("key1", "value1")
        workflow_context.update({"key2": "value2", "key3": "value3"})
        assert workflow_context.get("key1") == "value1"
        assert workflow_context.get("key2") == "value2"
        assert workflow_context.get("key3") == "value3"

    def test_get_all(self, workflow_context):
        workflow_context.set("key1", "value1")
        workflow_context.set("key2", 123)
        all_data = workflow_context.get_all()
        assert all_data == {"key1": "value1", "key2": 123}
        # Ensure it's a copy
        all_data["key1"] = "new_value"
        assert workflow_context.get("key1") == "value1"

    def test_clear(self, workflow_context):
        workflow_context.set("key1", "value1")
        workflow_context.clear()
        assert workflow_context.get_all() == {}

    def test_thread_safety(self, workflow_context):
        num_threads = 10
        num_operations = 100
        results = []

        def thread_func(thread_id):
            for i in range(num_operations):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                workflow_context.set(key, value)
                retrieved_value = workflow_context.get(key)
                results.append((key, value, retrieved_value))

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=thread_func, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(workflow_context.get_all()) == num_threads * num_operations
        for key, expected_value, retrieved_value in results:
            assert expected_value == retrieved_value
            assert workflow_context.get(key) == expected_value

    def test_resolve_placeholders_basic(self, workflow_context):
        workflow_context.set("name", "Alice")
        text = "Hello, {{name}}!"
        resolved = workflow_context.resolve_placeholders(text)
        assert resolved == "Hello, Alice!"

    def test_resolve_placeholders_multiple(self, workflow_context):
        workflow_context.set("name", "Alice")
        workflow_context.set("age", 30)
        text = "Name: {{name}}, Age: {{age}}."
        resolved = workflow_context.resolve_placeholders(text)
        assert resolved == "Name: Alice, Age: 30."

    def test_resolve_placeholders_non_existent(self, workflow_context):
        text = "Hello, {{name}}!"
        resolved = workflow_context.resolve_placeholders(text)
        assert resolved == "Hello, {{name}}!"

    def test_resolve_placeholders_mixed_content(self, workflow_context):
        workflow_context.set("item", "apple")
        text = "I like {{item}} and oranges."
        resolved = workflow_context.resolve_placeholders(text)
        assert resolved == "I like apple and oranges."

    def test_resolve_placeholders_non_string_input(self, workflow_context):
        assert workflow_context.resolve_placeholders(123) == 123
        assert workflow_context.resolve_placeholders(None) is None

    def test_resolve_config_string_values(self, workflow_context):
        workflow_context.set("user", "Bob")
        config = {"greeting": "Hi, {{user}}", "message": "Welcome!"}
        resolved = workflow_context.resolve_config(config)
        assert resolved == {"greeting": "Hi, Bob", "message": "Welcome!"}

    def test_resolve_config_nested_dict(self, workflow_context):
        workflow_context.set("city", "New York")
        config = {"location": {"country": "USA", "city": "{{city}}"}}
        resolved = workflow_context.resolve_config(config)
        assert resolved == {"location": {"country": "USA", "city": "New York"}}

    def test_resolve_config_list_values(self, workflow_context):
        workflow_context.set("fruit1", "apple")
        workflow_context.set("fruit2", "banana")
        config = {"fruits": ["{{fruit1}}", "{{fruit2}}", "orange"]}
        resolved = workflow_context.resolve_config(config)
        assert resolved == {"fruits": ["apple", "banana", "orange"]}

    def test_resolve_config_mixed_types(self, workflow_context):
        workflow_context.set("num", 100)
        workflow_context.set("status", "active")
        config = {
            "id": 123,
            "data": {"value": "{{num}}", "state": "{{status}}"},
            "tags": ["tag1", "{{status}}"],
            "is_enabled": True
        }
        resolved = workflow_context.resolve_config(config)
        assert resolved == {
            "id": 123,
            "data": {"value": "100", "state": "active"},
            "tags": ["tag1", "active"],
            "is_enabled": True
        }

    def test_resolve_config_empty(self, workflow_context):
        config = {}
        resolved = workflow_context.resolve_config(config)
        assert resolved == {}

    def test_resolve_config_no_placeholders(self, workflow_context):
        config = {"key": "value", "num": 123}
        resolved = workflow_context.resolve_config(config)
        assert resolved == {"key": "value", "num": 123}