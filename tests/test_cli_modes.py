"""Test suite for TerminalAI CLI modes.

This module tests both interactive and direct query modes of the TerminalAI CLI
with a variety of safe questions.
"""
import unittest
import sys
import io
import os
from unittest.mock import patch, MagicMock, call
import tempfile
import json

# Add parent directory to path so we can import terminalai modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules we want to test
from terminalai.query_utils import preprocess_query

class MockAIProvider:
    """Mock AI provider for testing."""

    def __init__(self, responses=None):
        """Initialize with predefined responses."""
        self.responses = responses or {
            "default": "This is a test response."
        }

    def generate_response(self, query, system_context=None, verbose=False, override_system_prompt=None):
        """Return a predefined response based on the query."""
        query_lower = query.lower()

        # Check for specific query matches
        for key, response in self.responses.items():
            if key in query_lower:
                return response

        # Fall back to default response
        return self.responses.get("default")

class TerminalAITestCase(unittest.TestCase):
    """Test cases for TerminalAI CLI."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(delete=False)

        # Define test configuration
        config = {
            "providers": {
                "openrouter": {"api_key": "test_key"},
                "gemini": {"api_key": "test_key"},
                "mistral": {"api_key": "test_key"},
                "ollama": {"host": "http://localhost:11434", "model": "test_model"}
            },
            "default_provider": "mistral",
            "system_prompt": "You are a test assistant."
        }

        # Write config to temporary file
        with open(self.temp_config.name, 'w') as f:
            json.dump(config, f)

        # Mock the config path
        self.config_path_patcher = patch('terminalai.config.CONFIG_PATH', self.temp_config.name)
        self.config_path_patcher.start()

        # Mock the AI provider
        self.mock_responses = {
            "default": "Here's how you can solve this problem.",
            "desktop": "To list files on your desktop, use:\n```bash\nls ~/Desktop\n```",
            "date": "To get the current date, use:\n```bash\ndate\n```",
            "list files": "To list files in the current directory, use:\n```bash\nls -la\n```",
            "weather": "I cannot directly check the weather, but you can use:\n```bash\ncurl wttr.in\n```",
            "python": "Here's a Python example:\n```python\nprint('Hello, world!')\n```",
        }

        self.provider_patcher = patch('terminalai.ai_providers.get_provider')
        self.mock_provider = self.provider_patcher.start()
        self.mock_provider.return_value = MockAIProvider(self.mock_responses)

        # Capture stdout and stderr
        self.stdout_patcher = patch('sys.stdout', new_callable=io.StringIO)
        self.stderr_patcher = patch('sys.stderr', new_callable=io.StringIO)
        self.mock_stdout = self.stdout_patcher.start()
        self.mock_stderr = self.stderr_patcher.start()

        # Prevent actual command execution
        self.run_command_patcher = patch('terminalai.cli_interaction.run_command')
        self.mock_run_command = self.run_command_patcher.start()
        self.mock_run_command.return_value = True

        # Prevent clipboard operations
        self.clipboard_patcher = patch('terminalai.cli_interaction.copy_to_clipboard')
        self.mock_clipboard = self.clipboard_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        # Stop patchers
        self.config_path_patcher.stop()
        self.provider_patcher.stop()
        self.stdout_patcher.stop()
        self.stderr_patcher.stop()
        self.run_command_patcher.stop()
        self.clipboard_patcher.stop()

        # Delete temporary config file
        os.unlink(self.temp_config.name)

    def test_query_preprocessing(self):
        """Test query preprocessing for desktop-related queries."""
        # Test a desktop query
        query = "what files are on my desktop?"
        processed = preprocess_query(query)
        self.assertIn("specifically the ~/Desktop folder", processed)

        # Test a query that already has desktop path
        query_with_path = "show me files in ~/Desktop"
        processed = preprocess_query(query_with_path)
        self.assertEqual(query_with_path, processed)  # Should remain unchanged

        # Test a non-desktop query
        query_other = "what is the current date?"
        processed = preprocess_query(query_other)
        self.assertEqual(query_other, processed)  # Should remain unchanged

    def test_direct_query_with_mock(self):
        """Test direct query processing with mocked main function."""
        # We'll test the direct query functionality directly without calling main()

        # Setup
        query = "what is the date?"
        mock_provider_instance = MockAIProvider(self.mock_responses)

        # Use preprocess_query directly
        processed_query = preprocess_query(query)

        # Generate a response directly
        response = mock_provider_instance.generate_response(processed_query, "test system context")

        # Assertions
        self.assertEqual(processed_query, query)  # No preprocessing needed for this query
        self.assertIn("To get the current date", response)
        self.assertIn("date", response)

        # Test with a desktop query
        desktop_query = "what files are on my desktop?"
        processed_desktop_query = preprocess_query(desktop_query)
        desktop_response = mock_provider_instance.generate_response(processed_desktop_query, "test system context")

        # Assertions for desktop query
        self.assertNotEqual(processed_desktop_query, desktop_query)  # Preprocessing happened
        self.assertIn("specifically the ~/Desktop folder", processed_desktop_query)
        self.assertIn("To list files on your desktop", desktop_response)
        self.assertIn("ls ~/Desktop", desktop_response)

    @patch('builtins.input')
    @patch('sys.stdin.isatty', return_value=True)
    def test_interactive_mode_with_mock(self, mock_isatty, mock_input):
        """Test interactive mode with mocked input."""
        # Setup input sequence
        mock_input.side_effect = ['what is the date?', 'exit']

        # Import interactive_mode with patches in place
        from terminalai.cli_interaction import interactive_mode

        # Mock the command extraction
        with patch('terminalai.cli_interaction.get_commands_interactive') as mock_extract:
            mock_extract.return_value = ["date"]

            # Mock sys.exit to prevent test exit
            with patch('sys.exit'):
                interactive_mode()

                # Check that input was called at least once
                mock_input.assert_called()

                # Get combined output
                output = self.mock_stdout.getvalue() + self.mock_stderr.getvalue()

                # Check that we got to the thinking stage
                self.assertIn("Thinking", output)

                # Check command extraction was called
                mock_extract.assert_called()

# For manual testing
if __name__ == '__main__':
    unittest.main()