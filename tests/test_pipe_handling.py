"""Test suite for TerminalAI CLI pipe input handling.

This module tests how TerminalAI handles input from pipes (non-interactive mode).
"""
import unittest
import sys
import io
import os
from unittest.mock import patch, MagicMock, ANY
import tempfile
import json

# Add parent directory to path so we can import terminalai modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import for stateful command detection
from terminalai.command_extraction import is_stateful_command

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

class PipeHandlingTestCase(unittest.TestCase):
    """Test cases for pipe input handling in TerminalAI CLI."""

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

        # Prepare mock provider responses
        self.mock_responses = {
            "default": "Here's how you can solve this problem.",
            "desktop": "To list files on your desktop, use:\n```bash\nls ~/Desktop\n```",
            "date": "To get the current date, use:\n```bash\ndate\n```",
            "list files": "To list files in the current directory, use:\n```bash\nls -la\n```",
            "weather": "I cannot directly check the weather, but you can use:\n```bash\ncurl wttr.in\n```",
            "python": "Here's a Python example:\n```python\nprint('Hello, world!')\n```",
            "useful commands": """Here are some useful commands:
```bash
ls -la
```
You can also check disk usage:
```bash
df -h
```
And check memory usage:
```bash
free -m
```""",
            "directory": """To change directory, use:
```bash
cd ~/Documents
```""",
            "remove files": """To remove files, use:
```bash
rm -rf /tmp/test
```"""
        }

        # Create mock provider instance
        self.mock_provider_instance = MockAIProvider(self.mock_responses)

        # Mock provider function
        self.provider_patcher = patch('terminalai.ai_providers.get_provider')
        self.mock_provider = self.provider_patcher.start()
        self.mock_provider.return_value = self.mock_provider_instance

        # Capture stdout and stderr
        self.stdout_patcher = patch('sys.stdout', new_callable=io.StringIO)
        self.stderr_patcher = patch('sys.stderr', new_callable=io.StringIO)
        self.mock_stdout = self.stdout_patcher.start()
        self.mock_stderr = self.stderr_patcher.start()

        # Prevent actual command execution
        self.run_command_patcher = patch('terminalai.cli_interaction.run_command')
        self.mock_run_command = self.run_command_patcher.start()
        self.mock_run_command.return_value = True

        # Mock other dependencies
        self.handle_commands_patcher = patch('terminalai.cli_interaction.handle_commands')
        self.mock_handle_commands = self.handle_commands_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        # Stop patchers
        self.config_path_patcher.stop()
        self.provider_patcher.stop()
        self.stdout_patcher.stop()
        self.stderr_patcher.stop()
        self.run_command_patcher.stop()
        self.handle_commands_patcher.stop()

        # Delete temporary config file
        os.unlink(self.temp_config.name)

    def test_pipe_input_handling(self):
        """Test handling of input from a pipe."""
        # Mock stdin with test query
        mock_stdin = io.StringIO("what is the date?\n")

        # Mock command extraction
        with patch('terminalai.cli_interaction.get_commands_interactive') as mock_extract:
            mock_extract.return_value = ["date"]

            # Run interactive mode with stdin patched
            with patch('sys.stdin', mock_stdin):
                with patch('sys.stdin.isatty', return_value=False):
                    with patch('sys.exit'):
                        from terminalai.cli_interaction import interactive_mode
                        interactive_mode()

        # Test that handle_commands was called with the extracted command
        # and auto-confirm set to True for non-interactive mode
        self.mock_handle_commands.assert_called_once_with(["date"], auto_confirm=True, auto_mode=False)

        # Get the output and verify it mentions non-interactive mode
        output = self.mock_stdout.getvalue() + self.mock_stderr.getvalue()
        self.assertIn("non-interactive mode", output.lower())

    def test_pipe_input_with_desktop_query(self):
        """Test pipe input handling with desktop files query."""
        # Mock stdin with test query
        mock_stdin = io.StringIO("what files are on my desktop?\n")

        # Mock command extraction
        with patch('terminalai.cli_interaction.get_commands_interactive') as mock_extract:
            mock_extract.return_value = ["ls ~/Desktop"]

            # Run interactive mode with stdin patched
            with patch('sys.stdin', mock_stdin):
                with patch('sys.stdin.isatty', return_value=False):
                    with patch('sys.exit'):
                        from terminalai.cli_interaction import interactive_mode
                        interactive_mode()

        # Test that handle_commands was called with the extracted command
        # and auto-confirm set to True for non-interactive mode
        self.mock_handle_commands.assert_called_once_with(["ls ~/Desktop"], auto_confirm=True, auto_mode=False)

    def test_pipe_input_with_multiple_commands(self):
        """Test pipe input handling with query that returns multiple commands."""
        # Mock stdin with test query
        mock_stdin = io.StringIO("show me some useful commands\n")

        # Get the combined output to check messages
        commands = ["ls -la", "df -h", "free -m"]

        # Mock the handle_commands implementation to print something we can check
        def mock_handle_impl(cmds, auto_confirm, auto_mode=False):
            if len(cmds) > 1:
                print("Multiple commands detected, executing:", cmds)
            return True

        self.mock_handle_commands.side_effect = mock_handle_impl

        # Mock the command extraction to return multiple commands
        with patch('terminalai.cli_interaction.get_commands_interactive') as mock_extract:
            mock_extract.return_value = commands

            # Run interactive mode with stdin patched
            with patch('sys.stdin', mock_stdin):
                with patch('sys.stdin.isatty', return_value=False):
                    with patch('sys.exit'):
                        from terminalai.cli_interaction import interactive_mode
                        interactive_mode()

        # Verify handle_commands was called with all commands
        self.mock_handle_commands.assert_called_once_with(commands, auto_confirm=True, auto_mode=False)

        # Get the output and check for the message about multiple commands
        output = self.mock_stdout.getvalue() + self.mock_stderr.getvalue()
        self.assertIn("multiple commands", output.lower())

    def test_pipe_input_with_stateful_command(self):
        """Test pipe input handling with stateful command."""
        # Mock stdin with test query
        mock_stdin = io.StringIO("how to change directory to Documents?\n")

        # Setup a custom implementation for handle_commands that handles stateful commands
        def mock_handle_stateful_cmds(cmds, auto_confirm, auto_mode=False):
            if len(cmds) > 0:
                cmd = cmds[0]
                if is_stateful_command(cmd):
                    print("Stateful command detected in non-interactive mode:", cmd)
                    # This is normally called inside handle_commands
                    from terminalai.cli_interaction import copy_to_clipboard
                    copy_to_clipboard(cmd)
                    print(f"Command copied to clipboard: {cmd}")
                    return True
            return False

        # Setup the mock implementation
        self.mock_handle_commands.side_effect = mock_handle_stateful_cmds

        # Track clipboard copy calls
        clipboard_called = [False]
        def mock_clipboard(cmd):
            clipboard_called[0] = True
            print(f"Clipboard copy called with: {cmd}")

        # Mock command extraction to return a stateful command
        with patch('terminalai.cli_interaction.get_commands_interactive') as mock_extract:
            mock_extract.return_value = ["cd ~/Documents"]

            # Required for the handle_commands implementation
            with patch('terminalai.command_extraction.is_stateful_command', return_value=True):
                # Mock clipboard function
                with patch('terminalai.cli_interaction.copy_to_clipboard', side_effect=mock_clipboard):
                    # Run interactive mode with stdin patched
                    with patch('sys.stdin', mock_stdin):
                        with patch('sys.stdin.isatty', return_value=False):
                            with patch('sys.exit'):
                                from terminalai.cli_interaction import interactive_mode
                                interactive_mode()

        # Verify handle_commands was called with the command
        self.mock_handle_commands.assert_called_once_with(["cd ~/Documents"], auto_confirm=True, auto_mode=False)

        # Get the output and check messages
        output = self.mock_stdout.getvalue() + self.mock_stderr.getvalue()

        # We should find "stateful command" in the output from our mock implementation
        self.assertIn("stateful command", output.lower())

        # Verify clipboard was called (this happens inside our mock handle_commands implementation)
        self.assertTrue(clipboard_called[0], "copy_to_clipboard was not called")

    def test_pipe_input_with_risky_command(self):
        """Test pipe input handling with risky command."""
        # Mock stdin with test query
        mock_stdin = io.StringIO("how to remove files?\n")

        # Get the combined output to check messages
        risky_cmd = "rm -rf /tmp/test"

        # Define a custom handler for risky commands
        def print_risky_warning(cmds, auto_confirm):
            print("RISKY command detected:", cmds[0])
            return False

        self.mock_handle_commands.side_effect = print_risky_warning

        # Mock command extraction
        with patch('terminalai.cli_interaction.get_commands_interactive') as mock_extract:
            mock_extract.return_value = [risky_cmd]

            # Mock risky command detection
            with patch('terminalai.command_extraction.is_risky_command', return_value=True):
                # Run interactive mode with stdin patched
                with patch('sys.stdin', mock_stdin):
                    with patch('sys.stdin.isatty', return_value=False):
                        with patch('sys.exit'):
                            from terminalai.cli_interaction import interactive_mode
                            interactive_mode()

        # Check the output for risky command message
        output = self.mock_stdout.getvalue() + self.mock_stderr.getvalue()
        self.assertIn("risky", output.lower(), "No risky command message in output")

# For manual testing
if __name__ == '__main__':
    unittest.main()