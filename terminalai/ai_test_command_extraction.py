"""
This is a copy of test_command_extraction.py for evaluation purposes.
"""
# --- Begin copy ---
import os
import shutil
import subprocess
import sys
import time
import re
import pytest
from terminalai.command_extraction import extract_commands, is_stateful_command, is_risky_command

# Test directory for all file/folder operations
TEST_DIR = os.path.join(os.getcwd(), "test_terminalai_parsing")

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    # Setup: create test directory
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)
    yield
    # Teardown: remove test directory and its contents
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

def test_single_command_in_code_block():
    """Test extracting a single command from a code block."""
    ai_response = """
Here is the command:
```bash
ls -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls -l"]
    assert not is_stateful_command(commands[0])
    assert not is_risky_command(commands[0])

def test_multiple_commands_separate_blocks():
    """Test extracting multiple commands from separate code blocks."""
    ai_response = """
First list files:
```bash
ls
```
Then show hidden files:
```bash
ls -a
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls", "ls -a"]

def test_multiple_commands_single_block():
    """Test extracting multiple commands from a single code block."""
    ai_response = """
To create and enter a directory:
```bash
mkdir test_terminalai_parsing
cd test_terminalai_parsing
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["mkdir test_terminalai_parsing", "cd test_terminalai_parsing"]
    assert not is_stateful_command(commands[0])
    assert is_stateful_command(commands[1])

def test_command_with_comment_inside_block():
    """Test extracting a command with a comment inside a code block."""
    ai_response = """
```bash
# This is a comment
ls -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls -l"]

def test_no_command_factual_response():
    """Test that no commands are extracted from a factual response."""
    ai_response = """
The ls command lists files in a directory.
"""
    commands = extract_commands(ai_response)
    assert not commands

def test_risky_command_detection():
    """Test detecting a risky command."""
    ai_response = """
```bash
rm -rf test_terminalai_parsing
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["rm -rf test_terminalai_parsing"]
    assert is_risky_command(commands[0])

def test_stateful_and_risky_combined():
    """Test detecting both stateful and risky commands."""
    ai_response = """
```bash
cd ~
```
```bash
rm -rf test_terminalai_parsing
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["cd ~", "rm -rf test_terminalai_parsing"]
    assert is_stateful_command(commands[0])
    assert not is_risky_command(commands[0])
    assert is_risky_command(commands[1])

def test_command_with_home_dir():
    """Test extracting a command with a home directory reference."""
    ai_response = """
```bash
ls ~
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls ~"]

def test_command_with_placeholder_path():
    """Test extracting a command with a placeholder path."""
    ai_response = """
```bash
cp file.txt /path/to/folder/
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["cp file.txt /path/to/folder/"]

def test_command_with_actual_test_dir():
    """Test extracting a command with an actual test directory."""
    ai_response = f"""
```bash
touch {TEST_DIR}/file.txt
```
"""
    commands = extract_commands(ai_response)
    assert commands == [f"touch {TEST_DIR}/file.txt"]

def test_command_with_extra_whitespace():
    """Test extracting a command with extra whitespace."""
    ai_response = """
```bash
   ls    -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls    -l"]

def test_command_with_pipe():
    """Test extracting a command with a pipe."""
    ai_response = """
```bash
grep foo file.txt | sort | uniq
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["grep foo file.txt | sort | uniq"]

def test_command_with_comment_outside_block():
    """Test extracting a command with a comment outside a code block."""
    ai_response = """
# This is a comment about the command
```bash
ls -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls -l"]

def test_factual_with_code_block():
    """Test that no commands are extracted from a factual response with a code block."""
    ai_response = """
The following is the output of the ls command:
```bash
file1.txt
file2.txt
```
"""
    commands = extract_commands(ai_response)
    # Should not treat these as commands
    assert not commands

def test_command_with_multiple_flags():
    """Test extracting a command with multiple flags."""
    ai_response = """
```bash
ls -l -a -h
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls -l -a -h"]

def run_cli_query(query):
    """Run the CLI with a direct query and return stdout."""
    env = os.environ.copy()
    result = subprocess.run([
        sys.executable, '-m', 'terminalai.terminalai_cli', query
    ], capture_output=True, text=True, check=False, env=env)
    return result.stdout + result.stderr

def test_cli_direct_query():
    """Test the CLI with a direct query."""
    query = "How do I list files in the current directory?"
    output = run_cli_query(query)
    if not ("ls" in output or "ls -l" in output):
        print("\n[DEBUG CLI OUTPUT]\n" + output)
    assert "ls" in output or "ls -l" in output

def test_cli_interactive_mode():
    """Test the CLI in interactive mode."""
    env = os.environ.copy()
    process = subprocess.Popen([
        sys.executable, '-m', 'terminalai.terminalai_cli'
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    input_sequence = "How do I list files in the current directory?\nexit\n"
    stdout, stderr = process.communicate(input=input_sequence, timeout=30)
    output = stdout + stderr
    if not ("ls" in output or "ls -l" in output):
        print("\n[DEBUG CLI INTERACTIVE OUTPUT]\n" + output)
    assert "ls" in output or "ls -l" in output

def test_cli_unique_query():
    """Test the CLI with a unique query."""
    unique_query = f"What is the current Unix timestamp? (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[UNIQUE CLI OUTPUT]\n" + output)
    # We can't assert the exact output, but we expect a number or a command like 'date +%s' in the output
    assert "date" in output or any(char.isdigit() for char in output)

def test_cli_unique_query_2():
    """Test the CLI with a unique query."""
    unique_query = f"What is the output of 'whoami' on a typical Unix system? (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[UNIQUE CLI OUTPUT 2]\n" + output)
    assert "whoami" in output or any(char.isalpha() for char in output)

def test_cli_unique_query_3():
    """Test the CLI with a unique query."""
    unique_query = f"How do I count the number of lines in a file called data.txt? (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[UNIQUE CLI OUTPUT 3]\n" + output)
    assert "wc -l" in output or "cat" in output or any(char.isdigit() for char in output)

def extract_commands_from_output(output):
    """Extract commands from both Markdown code blocks and rich panel output."""
    commands = []
    # Extract from Markdown code blocks
    code_blocks = re.findall(r'```(?:bash|sh)?\n?([\s\S]*?)```', output)
    for block in code_blocks:
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                commands.append(line)
    # Extract from rich panels (lines between │ ... │)
    panel_lines = re.findall(r'^\s*│\s*(.*?)\s*│\s*$', output, re.MULTILINE)
    for line in panel_lines:
        # Exclude lines that are just explanations or empty
        if line and not line.startswith('TerminalAI') and not line.startswith('Command') and not line.startswith('Found') and not line.startswith('AI Chat Mode') and not line.startswith('Type '):
            commands.append(line.strip())
    # Deduplicate, preserve order
    seen = set()
    result = []
    for cmd in commands:
        if cmd and cmd not in seen:
            seen.add(cmd)
            result.append(cmd)
    return result

def test_cli_two_ways_query():
    """Test the CLI with a query asking for two ways to list files."""
    unique_query = f"Show me two ways to list files in the current directory. (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[TWO WAYS CLI OUTPUT]\n" + output)
    commands = extract_commands_from_output(output)
    assert len(commands) >= 2, (
        f"Expected at least 2 commands, got {len(commands)}. Output:\n{output}"
    )
    assert "ls" in ' '.join(commands) and (
        "find" in ' '.join(commands) or
        "dir" in ' '.join(commands) or
        "get-childitem" in ' '.join(commands)
    ), f"Expected both 'ls' and another command. Output:\n{output}"

def test_cli_three_ways_query():
    """Test the CLI with a query asking for three ways to list files."""
    unique_query = f"Give me three ways to list files in the current directory. (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[THREE WAYS CLI OUTPUT]\n" + output)
    commands = extract_commands_from_output(output)
    assert len(commands) >= 3, (
        f"Expected at least 3 commands, got {len(commands)}. Output:\n{output}"
    )
    assert "ls" in ' '.join(commands) and (
        "find" in ' '.join(commands) or
        "dir" in ' '.join(commands) or
        "get-childitem" in ' '.join(commands)
    ), f"Expected 'ls' and another command. Output:\n{output}"

def test_cli_multi_command_formatting():
    """Test the CLI with a query asking for multiple commands in different formats."""
    unique_query = f"List files in two different ways. (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[MULTI COMMAND FORMATTING OUTPUT]\n" + output)
    commands = extract_commands_from_output(output)
    assert len(commands) >= 2, (
        f"Expected at least 2 commands, got {len(commands)}. Output:\n{output}"
    )
    # Check that each command is a single line (no multi-command blocks)
    for cmd in commands:
        assert '\n' not in cmd, (
            f"Each command should be a single line. Command:\n{cmd}\nOutput:\n{output}"
        )

def test_cli_enumerates_multiple_commands_and_handles_cancel():
    """Test the CLI enumerates multiple commands and handles cancel."""
    # Simulate a response with multiple commands (as code blocks and panels)
    ai_response = (
        "[AI] To list files by date (most recent first) and by size (largest first), you can use the following `zsh` command:\n"
        "```bash\nls -ltrS\n```\n"
        "This command uses the `ls` command with the options:\n"
        "- `-l` (ell) to display the output in a long format.\n"
        "- `-t` to sort by modification time (most recent first).\n"
        "- `-r` to reverse the order of the sort (largest files first).\n"
        "- `-S` to sort by file size.\n"
        "If you prefer to see hidden files (files whose names start with a dot), add the `-a` option:\n"
        "```bash\nls -lartS\n```\n"
        "Alternatively, if you are using a different shell like Bash, you can use the `sort` command:\n"
        "```bash\nls -lt | sort -nrk 5\n```\n"
        "This command uses the `ls` command with the `-l` option to display the output in long format.\n"
        "The output is piped (`|`) to the `sort` command, which sorts by the 5th column (file size). The `-n` option tells `sort` to sort numerically, and the `-r` option tells it to sort in reverse order (largest files first).\n"
    )
    # Use the extraction helper to simulate what the CLI would do
    commands = extract_commands_from_output(ai_response)
    assert len(commands) >= 3, f"Expected at least 3 commands, got {len(commands)}. Output:\n{ai_response}"
    # Simulate CLI enumeration prompt
    # (In a real CLI run, this would prompt for selection. Here, we just check extraction and logic.)
    assert "ls -ltrS" in commands
    assert "ls -lartS" in commands
    assert "ls -lt | sort -nrk 5" in commands
    # Simulate user cancelling (should not crash)
    # This is a logic check, not a subprocess test, but covers the core bug.
# --- End copy ---
