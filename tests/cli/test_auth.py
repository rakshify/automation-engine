import unittest
from unittest.mock import patch, MagicMock
import os

from src.cli.auth import User, get_current_user

class TestUser(unittest.TestCase):

    def test_user_creation_with_email(self):
        """Test User creation with an explicit email."""
        user = User(user_id="u1", username="testuser", email="test@test.com")
        self.assertEqual(user.user_id, "u1")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@test.com")

    def test_user_creation_without_email(self):
        """Test User creation with a default email."""
        user = User(user_id="u2", username="testuser2")
        self.assertEqual(user.user_id, "u2")
        self.assertEqual(user.username, "testuser2")
        self.assertEqual(user.email, "testuser2@example.com")

    def test_to_dict(self):
        """Test the to_dict method."""
        user = User(user_id="u3", username="testuser3", email="test3@test.com")
        expected_dict = {
            'user_id': "u3",
            'username': "testuser3",
            'email': "test3@test.com"
        }
        self.assertEqual(user.to_dict(), expected_dict)

class TestGetCurrentUser(unittest.TestCase):

    @patch('getpass.getuser')
    def test_get_current_user_with_getpass(self, mock_getuser):
        """Test get_current_user using getpass."""
        mock_getuser.return_value = "testuser"
        
        user = get_current_user()
        
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.user_id, "user_testuser")
        mock_getuser.assert_called_once()

    @patch('getpass.getuser', side_effect=Exception("getpass failed"))
    @patch.dict(os.environ, {'USER': 'envuser'}, clear=True)
    def test_get_current_user_with_env_user(self, mock_getuser):
        """Test get_current_user falling back to USER environment variable."""
        user = get_current_user()
        
        self.assertEqual(user.username, "envuser")
        self.assertEqual(user.user_id, "user_envuser")
        mock_getuser.assert_called_once()

    @patch('getpass.getuser', side_effect=Exception("getpass failed"))
    @patch.dict(os.environ, {'USERNAME': 'envuser2'}, clear=True)
    def test_get_current_user_with_env_username(self, mock_getuser):
        """Test get_current_user falling back to USERNAME environment variable."""
        user = get_current_user()
        
        self.assertEqual(user.username, "envuser2")
        self.assertEqual(user.user_id, "user_envuser2")
        mock_getuser.assert_called_once()

    @patch('getpass.getuser', side_effect=Exception("getpass failed"))
    @patch.dict(os.environ, {}, clear=True)
    def test_get_current_user_with_anonymous_fallback(self, mock_getuser):
        """Test get_current_user falling back to anonymous."""
        user = get_current_user()
        
        self.assertEqual(user.username, "anonymous")
        self.assertEqual(user.user_id, "user_anonymous")
        mock_getuser.assert_called_once()

    @patch('getpass.getuser')
    def test_username_with_space(self, mock_getuser):
        """Test that usernames with spaces are handled correctly."""
        mock_getuser.return_value = "test user"
        
        user = get_current_user()
        
        self.assertEqual(user.username, "test user")
        self.assertEqual(user.user_id, "user_test_user")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
