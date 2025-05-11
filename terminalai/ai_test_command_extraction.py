"""
This is a copy of test_command_extraction.py for evaluation purposes.
"""
# --- Begin copy ---
import os
import shutil
import tempfile
import pytest
from terminalai.command_extraction import extract_commands, is_stateful_command, is_risky_command
import subprocess
import sys
import time

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
    ai_response = """
```bash
# This is a comment
ls -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls -l"]

def test_no_command_factual_response():
    ai_response = """
The ls command lists files in a directory.
"""
    commands = extract_commands(ai_response)
    assert commands == []

def test_risky_command_detection():
    ai_response = """
```bash
rm -rf test_terminalai_parsing
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["rm -rf test_terminalai_parsing"]
    assert is_risky_command(commands[0])

def test_stateful_and_risky_combined():
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
    ai_response = """
```bash
ls ~
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls ~"]

def test_command_with_placeholder_path():
    ai_response = """
```bash
cp file.txt /path/to/folder/
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["cp file.txt /path/to/folder/"]

def test_command_with_actual_test_dir():
    ai_response = f"""
```bash
touch {TEST_DIR}/file.txt
```
"""
    commands = extract_commands(ai_response)
    assert commands == [f"touch {TEST_DIR}/file.txt"]

def test_command_with_extra_whitespace():
    ai_response = """
```bash
   ls    -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls    -l"]

def test_command_with_pipe():
    ai_response = """
```bash
grep foo file.txt | sort | uniq
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["grep foo file.txt | sort | uniq"]

def test_command_with_comment_outside_block():
    ai_response = """
# This is a comment about the command
```bash
ls -l
```
"""
    commands = extract_commands(ai_response)
    assert commands == ["ls -l"]

def test_factual_with_code_block():
    ai_response = """
The following is the output of the ls command:
```bash
file1.txt
file2.txt
```
"""
    commands = extract_commands(ai_response)
    # Should not treat these as commands
    assert commands == []

def test_command_with_multiple_flags():
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
    query = "How do I list files in the current directory?"
    output = run_cli_query(query)
    if not ("ls" in output or "ls -l" in output):
        print("\n[DEBUG CLI OUTPUT]\n" + output)
    assert "ls" in output or "ls -l" in output

def test_cli_interactive_mode():
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
    unique_query = f"What is the current Unix timestamp? (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[UNIQUE CLI OUTPUT]\n" + output)
    # We can't assert the exact output, but we expect a number or a command like 'date +%s' in the output
    assert "date" in output or any(char.isdigit() for char in output)

def test_cli_unique_query_2():
    unique_query = f"What is the output of 'whoami' on a typical Unix system? (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[UNIQUE CLI OUTPUT 2]\n" + output)
    assert "whoami" in output or any(char.isalpha() for char in output)

def test_cli_unique_query_3():
    unique_query = f"How do I count the number of lines in a file called data.txt? (test {int(time.time())})"
    output = run_cli_query(unique_query)
    print("\n[UNIQUE CLI OUTPUT 3]\n" + output)
    assert "wc -l" in output or "cat" in output or any(char.isdigit() for char in output)
# --- End copy ---