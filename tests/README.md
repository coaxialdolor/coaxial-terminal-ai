# TerminalAI Test Suite

This directory contains automated tests for the TerminalAI CLI application.

## Running Tests

You can run the tests using either of these methods:

1. Use the test runner script:
   ```bash
   ./tests/run_tests.py
   ```

2. Use the Python unittest module directly:
   ```bash
   python -m unittest discover -s tests
   ```

## Test Structure

The test suite is organized into these main components:

- `test_cli_modes.py` - Tests for both interactive and direct query modes with various queries
- `test_pipe_handling.py` - Tests for handling input from pipes (non-interactive mode)
- `run_tests.py` - Helper script to run all tests

## Writing New Tests

When adding new tests:

1. Follow the existing patterns for mocking dependencies
2. Ensure you properly mock `sys.exit()` to prevent tests from exiting
3. Use appropriate assertions for verifying behavior
4. Add your test file with a `test_` prefix to be auto-discovered

## Test Methodology

The tests use Python's `unittest` framework with extensive mocking to:

1. Mock external dependencies like API calls
2. Capture stdout/stderr for output verification
3. Simulate user input in interactive mode
4. Mock command execution to prevent actual commands from running

When testing, be mindful that:
- Tests should be isolated and not depend on each other
- Tests should not make actual API calls or execute real commands
- Use appropriate mocking for stdin/stdout to verify behavior

## Manual Testing

While automated tests cover many scenarios, it's still important to manually test the
application, especially for:

- Shell integration features
- Clipboard functionality
- Actual API provider responses
- Terminal UI rendering (colors, panels, etc.)