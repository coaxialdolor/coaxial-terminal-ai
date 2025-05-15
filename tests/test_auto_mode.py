"""Tests for the --auto mode feature of TerminalAI CLI."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Add parent directory to sys.path to import from terminalai package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from terminalai.cli_interaction import (
    handle_commands, parse_args, extract_exploration_commands, execute_exploration_commands
)
from terminalai.command_extraction import extract_commands_from_output


class TestAutoMode(unittest.TestCase):
    """Test cases for the --auto mode feature."""

    @patch('terminalai.cli_interaction.run_command')
    @patch('terminalai.cli_interaction.is_risky_command')
    @patch('terminalai.cli_interaction.is_stateful_command')
    @patch('terminalai.cli_interaction.Console')
    @patch('builtins.input', return_value='')
    def test_auto_mode_executes_non_risky_commands(self, mock_input, mock_console,
                                                 mock_is_stateful, mock_is_risky, mock_run_command):
        """Test that auto_mode automatically executes non-risky commands."""
        # Setup mocks
        mock_is_stateful.return_value = False
        mock_is_risky.return_value = False
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        # Test handle_commands with auto_mode=True
        commands = ['ls -la']
        handle_commands(commands, auto_confirm=False, auto_mode=True)

        # Verify that run_command was called with auto_confirm=True
        mock_run_command.assert_called_once_with('ls -la', auto_confirm=True)
        # Verify that input was not called, since the command should execute automatically
        mock_input.assert_not_called()

    @patch('terminalai.cli_interaction.run_command')
    @patch('terminalai.cli_interaction.is_risky_command')
    @patch('terminalai.cli_interaction.is_stateful_command')
    @patch('terminalai.cli_interaction.Console')
    @patch('builtins.input', return_value='y')
    def test_auto_mode_prompts_for_risky_commands(self, mock_input, mock_console,
                                                mock_is_stateful, mock_is_risky, mock_run_command):
        """Test that auto_mode still prompts for risky commands."""
        # Setup mocks
        mock_is_stateful.return_value = False
        mock_is_risky.return_value = True
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        # Test handle_commands with auto_mode=True
        commands = ['rm -rf /']
        handle_commands(commands, auto_confirm=False, auto_mode=True)

        # Verify that input was called, since the command is risky
        mock_input.assert_called_once()
        # Verify run_command was called with auto_confirm=False since we mocked the input to 'y'
        mock_run_command.assert_called_once_with('rm -rf /', auto_confirm=False)

    @patch('terminalai.cli_interaction.copy_to_clipboard')
    @patch('terminalai.cli_interaction.is_risky_command')
    @patch('terminalai.cli_interaction.is_stateful_command')
    @patch('terminalai.cli_interaction.Console')
    @patch('builtins.input', return_value='y')
    def test_auto_mode_handles_stateful_commands(self, mock_input, mock_console,
                                               mock_is_stateful, mock_is_risky, mock_copy_to_clipboard):
        """Test that auto_mode handles stateful commands correctly."""
        # Setup mocks
        mock_is_stateful.return_value = True
        mock_is_risky.return_value = False
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        # Test handle_commands with auto_mode=True
        commands = ['cd /tmp']
        handle_commands(commands, auto_confirm=False, auto_mode=True)

        # Verify that copy_to_clipboard was called, since the command is stateful
        mock_copy_to_clipboard.assert_called_once_with('cd /tmp')

    @patch('sys.argv', ['ai', '--auto'])
    def test_parse_args_auto_flag(self):
        """Test that the --auto flag is correctly parsed."""
        args = parse_args()
        self.assertTrue(args.auto)

    def test_extract_exploration_commands(self):
        """Test that exploration commands are correctly extracted from queries."""
        # Test file listing query
        query = "List all files in the current directory"
        commands = extract_exploration_commands("", query)
        self.assertIn("ls -la", commands)

        # Test file finding query
        query = "Find all .py files"
        commands = extract_exploration_commands("", query)
        expected_cmd = 'find . -name "*.py*" -type f -maxdepth 3'
        self.assertTrue(any(cmd.startswith('find . -name') for cmd in commands))

        # Test disk usage query
        query = "How much disk space is available?"
        commands = extract_exploration_commands("", query)
        self.assertIn("df -h", commands)

        # Test file counting query
        query = "Count the number of files in this directory"
        commands = extract_exploration_commands("", query)
        self.assertIn("find . -type f | wc -l", commands)

        # Test query that doesn't need exploration
        query = "What time is it?"
        commands = extract_exploration_commands("", query)
        self.assertEqual(len(commands), 0)

    @patch('subprocess.run')
    @patch('terminalai.cli_interaction.is_risky_command')
    @patch('terminalai.cli_interaction.is_stateful_command')
    @patch('terminalai.cli_interaction.Console')
    def test_execute_exploration_commands(self, mock_console, mock_is_stateful,
                                         mock_is_risky, mock_subprocess_run):
        """Test that exploration commands are correctly executed."""
        # Setup mocks
        mock_is_stateful.return_value = False
        mock_is_risky.return_value = False
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        # Mock subprocess.run to return dummy output
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "file1.txt\nfile2.py"
        mock_subprocess_run.return_value = mock_process

        # Test execution
        commands = ["ls -la", "find . -name '*.py'"]
        results = execute_exploration_commands(commands, mock_console_instance)

        # Verify results
        self.assertIn("Command: ls -la", results)
        self.assertIn("Command: find . -name '*.py'", results)
        self.assertIn("file1.txt", results)
        self.assertIn("file2.py", results)

        # Verify subprocess.run was called for both commands
        self.assertEqual(mock_subprocess_run.call_count, 2)

    @patch('terminalai.cli_interaction.execute_exploration_commands')
    @patch('terminalai.cli_interaction.extract_exploration_commands')
    @patch('builtins.input', side_effect=["how many python files?", "exit"])
    @patch('terminalai.cli_interaction.get_provider')
    @patch('terminalai.config.load_config')
    @patch('terminalai.cli_interaction.print_ai_answer_with_rich')
    @patch('terminalai.cli_interaction.get_system_context')
    @patch('sys.stdin.isatty', return_value=True)
    @patch('terminalai.cli_interaction.Console')
    def test_auto_mode_explores_filesystem(self, mock_console, mock_isatty, mock_get_system_context,
                                          mock_print_answer, mock_load_config, mock_get_provider,
                                          mock_input, mock_extract_cmds, mock_execute_cmds):
        """Test that auto mode correctly explores the filesystem."""
        # Setup mocks
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = "Here's what I found: There are 5 Python files."
        mock_get_provider.return_value = mock_provider

        mock_load_config.return_value = {"default_provider": "test"}
        mock_get_system_context.return_value = "You are a helpful assistant."

        # Mock exploration commands extraction
        mock_extract_cmds.return_value = ["find . -name '*.py' | wc -l"]
        mock_execute_cmds.return_value = "Command: find . -name '*.py' | wc -l\nOutput:\n5\n"

        # Run interactive mode with auto_mode=True
        with patch('sys.exit'):  # Prevent actual system exit
            from terminalai.cli_interaction import interactive_mode
            interactive_mode(chat_mode=True, auto_mode=True)

        # Verify auto mode functionality was used
        mock_extract_cmds.assert_called_once()
        mock_execute_cmds.assert_called_once()

        # Verify provider was called with both regular and enhanced contexts
        self.assertEqual(mock_provider.generate_response.call_count, 2)

        # The second call should include exploration results
        second_call_args = mock_provider.generate_response.call_args_list[1]
        self.assertIn("Based on the exploration results", second_call_args[0][0])
        self.assertIn("Exploration results", second_call_args[0][1])

        # Verify the enhanced answer was displayed
        self.assertIn(call("Here's what I found: There are 5 Python files."),
                     mock_print_answer.call_args_list)

if __name__ == '__main__':
    unittest.main()