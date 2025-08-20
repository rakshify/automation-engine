#!/usr/bin/env python3
"""Test script to verify the application setup."""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from workflow_manager.core.component import BaseComponent, BaseAction, BaseEvent
        from workflow_manager.core.context import WorkflowContext
        from workflow_manager.core.datastore import datastore
        from workflow_manager.core.factory import ComponentFactory, ActionFactory, EventFactory
        from workflow_manager.core.workflow import Workflow
        print("✅ Core modules imported successfully")
        
        # Test component imports
        from workflow_manager.components.formatter import Formatter, TextAction, NumberAction
        from workflow_manager.components.webhook import Webhook, GetAction, PostAction
        from workflow_manager.components.slack import Slack, SendMessageAction, ReceiveMessageEvent
        print("✅ Component modules imported successfully")
        
        # Test CLI imports
        from workflow_manager.cli.auth import get_current_user
        from workflow_manager.cli.utils import ask_question, validate_workflow_name
        from workflow_manager.cli.create_workflow import create_workflow
        from workflow_manager.cli.execute_workflow import execute_workflow
        print("✅ CLI modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_configuration_files():
    """Test that configuration files are valid JSON."""
    print("\nTesting configuration files...")
    
    import json
    
    config_files = [
        "configs/components_store.json",
        "configs/action_store.json",
        "configs/event_store.json"
    ]
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                json.load(f)
            print(f"✅ {config_file} is valid JSON")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ {config_file} error: {e}")
            return False
    
    return True


def test_factories():
    """Test that factories can create objects."""
    print("\nTesting factories...")
    
    try:
        from workflow_manager.core.factory import ComponentFactory, ActionFactory
        
        # Test component creation
        formatter = ComponentFactory.create('formatter')
        print("✅ Formatter component created")
        
        webhook = ComponentFactory.create('webhook')
        print("✅ Webhook component created")
        
        slack = ComponentFactory.create('slack')
        print("✅ Slack component created")
        
        # Test action creation
        text_action = ActionFactory.create('formatter.text', formatter)
        print("✅ Text action created")
        
        get_action = ActionFactory.create('webhook.get', webhook)
        print("✅ GET action created")
        
        return True
        
    except Exception as e:
        print(f"❌ Factory error: {e}")
        return False


def test_context():
    """Test the workflow context."""
    print("\nTesting workflow context...")
    
    try:
        from workflow_manager.core.context import WorkflowContext
        
        context = WorkflowContext()
        
        # Test basic operations
        context.set('test_key', 'test_value')
        value = context.get('test_key')
        assert value == 'test_value', f"Expected 'test_value', got '{value}'"
        print("✅ Context set/get works")
        
        # Test placeholder resolution
        context.set('name', 'World')
        resolved = context.resolve_placeholders('Hello {{name}}!')
        assert resolved == 'Hello World!', f"Expected 'Hello World!', got '{resolved}'"
        print("✅ Placeholder resolution works")
        
        return True
        
    except Exception as e:
        print(f"❌ Context error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Workflow Manager Setup")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_configuration_files,
        test_factories,
        test_context
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to use.")
        print("\nTo run the application:")
        print("  python run.py")
        print("  or")
        print("  python -m workflow_manager")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
