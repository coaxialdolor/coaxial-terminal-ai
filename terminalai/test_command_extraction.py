"""
Automated tests for TerminalAI command extraction and formatting logic.
Ensures that command parsing is robust and safe. All file/folder operations are performed in a dedicated test directory.
"""
import os
import shutil
import pytest
from terminalai.command_extraction import extract_commands, is_stateful_command, is_risky_command
import subprocess
import sys
import re

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

def run_cli_query(query):
    """Run the CLI with a direct query and return stdout."""
    result = subprocess.run([
        sys.executable, '-m', 'terminalai.terminalai_cli', query
    ], capture_output=True, text=True, check=False)
    return result.stdout + result.stderr

def test_cli_direct_query():
    # This should extract a safe command
    query = "How do I list files in the current directory?"
    output = run_cli_query(query)
    assert "ls" in output or "ls -l" in output

# Interactive mode test (simulate user input)
def test_cli_interactive_mode():
    # Simulate entering a query and then 'exit' to quit
    process = subprocess.Popen([
        sys.executable, '-m', 'terminalai.terminalai_cli'
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Send a query and then 'exit' to quit
    input_sequence = "How do I list files in the current directory?\nexit\n"
    stdout, stderr = process.communicate(input=input_sequence, timeout=10)
    output = stdout + stderr
    assert "ls" in output or "ls -l" in output

# List of (ai_response, expected_commands) tuples for offline extraction tests
offline_extraction_cases = [
    # Example 1
    ("Here are two ways to list files in the current directory:\n"
     "```bash\nls\n```\n"
     "```bash\nfind .\n```\n"
     "Explanation: The first command uses ls, the second uses find.\n",
     ["ls", "find ."]),
    # Example 2
    ("[AI] To list files by date (most recent first) and by size (largest first), you can use the following `zsh` command:\n"
     "╭────────────────────────────────────────── Command ──────────────────────────────────────────╮\n"
     "│ ls -ltrS                                                                                    │\n"
     "╰─────────────────────────────────────────────────────────────────────────────────────────────╯\n"
     "This command uses the `ls` command with the options:\n"
     "- `-l` (ell) to display the output in a long format.\n"
     "- `-t` to sort by modification time (most recent first).\n"
     "- `-r` to reverse the order of the sort (largest files first).\n"
     "- `-S` to sort by file size.\n"
     "If you prefer to see hidden files (files whose names start with a dot), add the `-a` option:\n"
     "╭────────────────────────────────────────── Command ──────────────────────────────────────────╮\n"
     "│ ls -lartS                                                                                   │\n"
     "╰─────────────────────────────────────────────────────────────────────────────────────────────╯\n"
     "Alternatively, if you are using a different shell like Bash, you can use the `sort` command:\n"
     "╭────────────────────────────────────────── Command ──────────────────────────────────────────╮\n"
     "│ ls -lt | sort -nrk 5                                                                        │\n"
     "╰─────────────────────────────────────────────────────────────────────────────────────────────╯\n"
     "This command uses the `ls` command with the `-l` option to display the output in long format.\n"
     "The output is piped (`|`) to the `sort` command, which sorts by the 5th column (file size). The\n"
     "`-n` option tells `sort` to sort numerically, and the `-r` option tells it to sort in reverse \n"
     "order (largest files first).\n",
     ["ls -ltrS", "ls -lartS", "ls -lt | sort -nrk 5"]),
    # Example 3
    ("[AI]\n╭────────────────────────────────── Command ───────────────────────────────────╮\n"
     "│ ls                                                                           │\n"
     "╰──────────────────────────────────────────────────────────────────────────────╯\n"
     "╭────────────────────────────────── Command ───────────────────────────────────╮\n"
     "│ ls -l                                                                        │\n"
     "╰──────────────────────────────────────────────────────────────────────────────╯\n"
     "Explanation: The first command lists files, the second lists them in long format.\n",
     ["ls", "ls -l"]),
    # Example 4
    ("```bash\nls\n```\nThis command will list the files in the current directory.\n", ["ls"]),
    # Example 5
    ("```bash\nrm -rf /tmp/testdir\n```\nBe careful: this will delete the directory.\n", ["rm -rf /tmp/testdir"]),
    # Example 6
    ("The ls command lists files in a directory.\n", []),
    # Example 7
    ("```bash\nls -l  # lists files in long format\n```\n", ["ls -l  # lists files in long format"]),
    # Example 8
    ("```bash\n\n# comment\nls\n\n```\n", ["ls"]),
    # Example 9
    ("╭─────────────────────────────── Command ───────────────────────────────╮\n"
     "│   ls -lh   │\n"
     "╰─────────────────────────────────────────────────────────────────────╯\n", ["ls -lh"]),
    # Example 10
    ("```bash\nls\n```\n"
     "╭─────────────────────────────── Command ───────────────────────────────╮\n"
     "│ ls -a │\n"
     "╰─────────────────────────────────────────────────────────────────────╯\n", ["ls", "ls -a"]),
    # Example 11
    ("```bash\nls; pwd; whoami\n```\n", ["ls; pwd; whoami"]),
    # Example 12
    ("```bash\nls\npwd\nwhoami\n```\n", ["ls", "pwd", "whoami"]),
    # Example 13
    ("```bash\n  ls -l  \n```\n", ["ls -l"]),
    # Example 14
    ("```sh\nls -a\n```\n", ["ls -a"]),
    # Example 15
    ("```\nls -lh\n```\n", ["ls -lh"]),
    # Example 16
    ("```bash\nls\nls\n```\n", ["ls"]),
    # Example 17
    ("╭───── Command ─────╮\n│ ls │\n╰─────────────────────╯\n"
     "╭───── Command ─────╮\n│ ls │\n╰─────────────────────╯\n", ["ls"]),
    # Example 18
    ("```bash\n# just a comment\n```\n", []),
    # Example 19
    ("```bash\n   \n```\n", []),
    # Example 20
    ("╭───── Command ─────╮\n│ This lists files │\n╰───────────────────╯\n", ["This lists files"]),
    # Example 21
    ("╭───── Command ─────╮\n│ ls # list │\n╰─────────────────────╯\n", ["ls # list"]),
    # Example 22
    ("```bash\nls | grep py > out.txt\n```\n", ["ls | grep py > out.txt"]),
    # Example 23
    ("```bash\nsudo rm -rf /tmp/test\n```\n", ["sudo rm -rf /tmp/test"]),
    # Example 24
    ("```bash\ncd /tmp\n```\n", ["cd /tmp"]),
    # Example 25
    ("```bash\nexport FOO=bar\n```\n", ["export FOO=bar"]),
    # Example 26 (here-doc, expect current behavior: split lines)
    ("```bash\ncat <<EOF\nhello\nEOF\n```\n", ["cat <<EOF", "hello", "EOF"]),
    # Example 27
    ("```bash\nmyfunc() { echo hi; }\n```\n", ["myfunc() { echo hi; }"]),
    # Example 28
    ("```bash\nalias ll='ls -l'\n```\n", ["alias ll='ls -l'"]),
    # Example 29
    ("```bash\nFOO=bar\n```\n", ["FOO=bar"]),
    # Example 30
    ("```bash\narr=(1 2 3)\n```\n", ["arr=(1 2 3)"]),
    # Example 31
    ("```bash\necho $((1+2))\n```\n", ["echo $((1+2))"]),
    # Example 32
    ("```bash\necho \"foo\"\n```\n", ["echo \"foo\""]),
    # Example 33
    ("```bash\necho $(ls)\n```\n", ["echo $(ls)"]),
    # Example 34
    ("```bash\ndiff <(ls) <(ls -a)\n```\n", ["diff <(ls) <(ls -a)"]),
    # Example 35
    ("```bash\nls > out.txt\n```\n", ["ls > out.txt"]),
    # Example 36
    ("```bash\nls | grep foo\n```\n", ["ls | grep foo"]),
    # Example 37
    ("```bash\nls && echo ok\n```\n", ["ls && echo ok"]),
    # Example 38
    ("```bash\n[ -f foo.txt ] && cat foo.txt\n```\n", ["[ -f foo.txt ] && cat foo.txt"]),
    # Example 39
    ("```bash\nfor f in *; do echo $f; done\n```\n", ["for f in *; do echo $f; done"]),
    # Example 40
    ("```bash\ncase $1 in foo) echo foo;; esac\n```\n", ["case $1 in foo) echo foo;; esac"]),
    # Example 41
    ("```bash\nselect x in a b; do echo $x; break; done\n```\n", ["select x in a b; do echo $x; break; done"]),
    # Example 42
    ("```bash\ncoproc mycop { ls; }\n```\n", ["coproc mycop { ls; }"]),
    # Example 43
    ("```bash\ntrap 'echo hi' EXIT\n```\n", ["trap 'echo hi' EXIT"]),
    # Example 44
    ("```bash\nkill -9 1234\n```\n", ["kill -9 1234"]),
    # Example 45
    ("```bash\njobs\n```\n", ["jobs"]),
    # Example 46
    ("```bash\ndisown %1\n```\n", ["disown %1"]),
    # Example 47
    ("```bash\nwait %1\n```\n", ["wait %1"]),
    # Example 48
    ("```bash\nfg %1\n```\n", ["fg %1"]),
    # Example 49
    ("```bash\necho café\n```\n", ["echo café"]),
    # Example 50
    ("```bash\nLS -L\n```\n", ["LS -L"]),
    # Example 51
    ("1. ```bash\nls\n```\n2. ```bash\npwd\n```\n", ["ls", "pwd"]),
    # Example 52
    ("> ```bash\nls\n```\n", ["ls"]),
    # Example 53
    ("| Command |\n|---------|\n| ```bash\nls\n``` |\n", ["ls"]),
    # Example 54
    ("```bash\nthis is not valid shell\n```\n", ["this is not valid shell"]),
    # Example 55
    ("'''bash\nls\n'''\n", []),
    # Example 56
    ("<div>```bash\nls\n```</div>\n", ["ls"]),
    # Example 57
    ("╭───── Command ─────╮\n│ ls │\n╰─────────────────────╯\n"
     "╭───── Command ─────╮\n│ ls -l │\n╰─────────────────────╯\n", ["ls", "ls -l"]),
    # Example 58
    ("╭───── Command ─────╮\n│\tls -l\t│\n╰─────────────────────╯\n", ["ls -l"]),
    # Example 59
    ("╭───── Command ─────╮\n│ Ls -L │\n╰─────────────────────╯\n", ["Ls -L"]),
    # Example 60
    ("╭───── Command ─────╮\n│ echo café │\n╰─────────────────────╯\n", ["echo café"]),
    # Example 61: Multiple rich panel commands as in user example
    ("[AI] There are multiple ways to list files in a directory by date and by size on macOS/zsh. Here are two examples:\n"
     "1. Using the `ls` command with custom sorting options:\n"
     "╭───────────────────────────────── Command ──────────────────────────────────╮\n"
     "│ ls -lt --time-style=+\"%Y-%m-%d %H:%M\" --group-directories-first            │\n"
     "╰────────────────────────────────────────────────────────────────────────────╯\n"
     "This command lists files in long format, sorted by modification date in descending order, with the year, month, day, hour, and minute displayed. The `--group-directories-first` option groups directories at the beginning of the output.\n"
     "2. Using the `lsd` command:\n\nIf you have the `lsd` package installed, you can use it to display file details in a more colorful and organized manner:\n"
     "This command lists files in a detailed format, grouped by modification time in descending order.\n\nTo install `lsd`, you can use Homebrew:\n"
     "╭───────────────────────────────── Command ──────────────────────────────────╮\n"
     "│ brew install lsd                                                           │\n"
     "╰────────────────────────────────────────────────────────────────────────────╯\n"
     "Remember to replace the commands above with the appropriate paths if you installed them elsewhere.\n\nFor listing files by size, you can use the following command:\n"
     "╭───────────────────────────────── Command ──────────────────────────────────╮\n"
     "│ ls -lS                                                                     │\n"
     "╰────────────────────────────────────────────────────────────────────────────╯\n"
     "This command lists files in long format, sorted by file size in ascending order.\n",
     ["ls -lt --time-style=+\"%Y-%m-%d %H:%M\" --group-directories-first", "brew install lsd", "ls -lS"]),
]

@pytest.mark.parametrize("ai_response,expected", offline_extraction_cases)
def test_offline_extraction_case(ai_response, expected):
    commands = extract_commands_from_output(ai_response)
    assert commands == expected

# Add more tests as needed to cover edge cases, e.g. code blocks with explanations, mixed factual and command responses, etc.
