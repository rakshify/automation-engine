import pytest
import json
from pathlib import Path
from src.core.datastore import DataStore

@pytest.fixture
def temp_datastore(tmp_path):
    # Create a temporary directory for the datastore
    data_dir = tmp_path / "test_data"
    return DataStore(data_dir=str(data_dir))

class TestDataStore:
    def test_initialization(self, tmp_path):
        data_dir = tmp_path / "test_data_init"
        datastore = DataStore(data_dir=str(data_dir))
        assert data_dir.exists()
        assert (data_dir / "users").exists()
        assert (data_dir / "workflows").exists()
        assert (data_dir / "setups").exists()

    def test_save_and_load_user_profile(self, temp_datastore):
        user_id = "user123"
        profile_data = {"name": "Test User", "email": "test@example.com"}
        temp_datastore.save_user_profile(user_id, profile_data)
        loaded_profile = temp_datastore.load_user_profile(user_id)
        assert loaded_profile == profile_data

    def test_load_non_existent_user_profile(self, temp_datastore):
        loaded_profile = temp_datastore.load_user_profile("non_existent_user")
        assert loaded_profile is None

    def test_save_and_load_workflow(self, temp_datastore):
        user_id = "user123"
        workflow_name = "my_workflow"
        workflow_data = {"name": workflow_name, "steps": ["step1", "step2"]}
        temp_datastore.save_workflow(user_id, workflow_name, workflow_data)
        loaded_workflow = temp_datastore.load_workflow(user_id, workflow_name)
        assert loaded_workflow == workflow_data

    def test_load_non_existent_workflow(self, temp_datastore):
        loaded_workflow = temp_datastore.load_workflow("user123", "non_existent_workflow")
        assert loaded_workflow is None

    def test_list_workflows(self, temp_datastore):
        user_id = "user_list"
        temp_datastore.save_workflow(user_id, "workflow_a", {})
        temp_datastore.save_workflow(user_id, "workflow_c", {})
        temp_datastore.save_workflow(user_id, "workflow_b", {})
        temp_datastore.save_workflow("another_user", "workflow_x", {})

        workflows = temp_datastore.list_workflows(user_id)
        assert workflows == ["workflow_a", "workflow_b", "workflow_c"]

    def test_list_workflows_empty(self, temp_datastore):
        workflows = temp_datastore.list_workflows("user_no_workflows")
        assert workflows == []

    def test_workflow_exists(self, temp_datastore):
        user_id = "user_exists"
        workflow_name = "existing_workflow"
        temp_datastore.save_workflow(user_id, workflow_name, {})
        assert temp_datastore.workflow_exists(user_id, workflow_name) is True
        assert temp_datastore.workflow_exists(user_id, "non_existent") is False

    def test_save_and_load_component_setup(self, temp_datastore):
        user_id = "user_setup"
        component_name = "slack"
        setup_name = "dev_config"
        setup_data = {"token": "abc", "channel": "#general"}
        temp_datastore.save_component_setup(user_id, component_name, setup_data, setup_name)
        loaded_setup = temp_datastore.load_component_setup(user_id, component_name, setup_name)
        assert loaded_setup == setup_data

    def test_load_non_existent_component_setup(self, temp_datastore):
        loaded_setup = temp_datastore.load_component_setup("user_setup", "slack", "non_existent_setup")
        assert loaded_setup is None

    def test_has_component_setup(self, temp_datastore):
        user_id = "user_has_setup"
        component_name = "webhook"
        setup_name = "prod_config"
        temp_datastore.save_component_setup(user_id, component_name, {}, setup_name)
        assert temp_datastore.has_component_setup(user_id, component_name, setup_name) is True
        assert temp_datastore.has_component_setup(user_id, component_name, "non_existent") is False

    def test_list_component_setups(self, temp_datastore):
        user_id = "user_list_setup"
        component_name = "formatter"
        temp_datastore.save_component_setup(user_id, component_name, {}, "setup_a")
        temp_datastore.save_component_setup(user_id, component_name, {}, "setup_c")
        temp_datastore.save_component_setup(user_id, component_name, {}, "setup_b")
        temp_datastore.save_component_setup("another_user", component_name, {}, "setup_x")

        setups = temp_datastore.list_component_setups(user_id, component_name)
        assert setups == ["setup_a", "setup_b", "setup_c"]

    def test_list_component_setups_empty(self, temp_datastore):
        setups = temp_datastore.list_component_setups("user_no_setup", "component_no_setup")
        assert setups == []

    def test_delete_component_setup(self, temp_datastore):
        user_id = "user_delete"
        component_name = "email"
        setup_name = "main_config"
        temp_datastore.save_component_setup(user_id, component_name, {}, setup_name)
        assert temp_datastore.has_component_setup(user_id, component_name, setup_name) is True

        deleted = temp_datastore.delete_component_setup(user_id, component_name, setup_name)
        assert deleted is True
        assert temp_datastore.has_component_setup(user_id, component_name, setup_name) is False

    def test_delete_non_existent_component_setup(self, temp_datastore):
        deleted = temp_datastore.delete_component_setup("user_delete", "email", "non_existent")
        assert deleted is False
