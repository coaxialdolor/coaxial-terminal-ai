"""Command extraction and detection functionality."""
import re

# Constants for command detection
KNOWN_COMMANDS = [
    "ls", "cd", "cat", "cp", "mv", "rm", "find", "grep", "awk", "sed", "chmod",
    "chown", "head", "tail", "touch", "mkdir", "rmdir", "tree", "du", "df", "ps",
    "top", "htop", "less", "more", "man", "which", "whereis", "locate", "pwd", "whoami",
    "date", "cal", "env", "export", "ssh", "scp", "curl", "wget", "tar", "zip", "unzip",
    "python", "pip", "brew", "apt", "yum", "dnf", "docker", "git", "npm", "node",
    "make", "gcc", "clang", "javac", "java", "mvn", "gradle", "cargo", "rustc",
    "go", "swift", "kotlin", "dotnet", "perl", "php", "ruby", "mvn", "jest",
    "nano", "vim", "vi", "emacs", "pico", "subl", "code"
]

STATEFUL_COMMANDS = [
    'cd', 'export', 'set', 'unset', 'alias', 'unalias', 'source', 'pushd', 'popd',
    'dirs', 'fg', 'bg', 'jobs', 'disown', 'exec', 'login', 'logout', 'exit',
    'kill', 'trap', 'shopt', 'enable', 'disable', 'declare', 'typeset',
    'readonly', 'eval', 'help', 'times', 'umask', 'wait', 'suspend', 'hash',
    'bind', 'compgen', 'complete', 'compopt', 'history', 'fc', 'getopts',
    'let', 'local', 'read', 'readonly', 'return', 'shift', 'test', 'times'
]

RISKY_COMMANDS = [
    "rm", "dd", "chmod", "chown", "sudo", "mkfs", "fdisk", "diskpart",
    "format", "del", "rd", "rmdir", ":(){", "fork", "shutdown", "halt",
    "reboot", "init", "mkpart", "gpart", "attrib", "takeown"
]

def is_likely_command(line):
    """Return True if the line looks like a shell command."""
    line = line.strip()
    if not line or line.startswith("#"):
        return False

    # Skip natural language sentences
    if len(line.split()) > 3 and line[0].isupper() and line[-1] in ['.', '!', '?']:
        return False

    # Skip lines that look like factual statements (starts with capital, contains verb phrases)
    factual_indicators = [
        "is", "are", "was", "were", "has", "have", "had", "means", "represents",
        "consists"
    ]
    if line.split() and line[0].isupper():
        for word in factual_indicators:
            if f" {word} " in f" {line} ":
                return False

    # Command detection approach: look for known command patterns
    first_word = line.split()[0] if line.split() else ""
    # Allow single-word commands if they are known
    if first_word in KNOWN_COMMANDS or first_word in STATEFUL_COMMANDS:
        return True
    if first_word == "echo" and len(line.split()) >= 2:  # echo itself is a command
        return True

    # Check for shell operators that indicate command usage
    shell_operators = [' | ', ' && ', ' || ', ' > ', ' >> ', ' < ', '$(', '`']
    for operator in shell_operators:
        if operator in line:
            for cmd in KNOWN_COMMANDS:
                if re.search(rf'\b{cmd}\b', line):  # Use word boundaries for exact match
                    return True

    # Check for options/flags which indicate commands
    has_option_flag = (
        re.search(r'\s-[a-zA-Z]+\b', line) or
        re.search(r'\s--[a-zA-Z-]+\b', line)
    )
    if has_option_flag:
        for cmd in KNOWN_COMMANDS:
            if line.startswith(cmd + ' '):
                return True

    return False

def extract_commands(ai_response, max_commands=None):
    """
    Extract shell commands from AI response code blocks.

    Args:
        ai_response: The AI response text
        max_commands: Optional limit on number of commands to extract

    Returns:
        List of commands
    """
    commands = []

    # Check if this is a purely factual response without any command suggestions
    # Common patterns in factual responses
    factual_response_patterns = [
        r'^\[AI\] [A-Z].*\.$',  # Starts with capital, ends with period
        r'^\[AI\] approximately',  # Approximate numerical answer
        r'^\[AI\] about',  # Approximate answer with "about"
        r'^\[AI\] [0-9]',  # Starts with a number
    ]

    # If factual and no code blocks, skip command extraction
    is_likely_factual = False
    for pattern in factual_response_patterns:
        if re.search(pattern, ai_response, re.IGNORECASE):
            # If response is short and doesn't have code blocks, it's likely just factual
            if len(ai_response.split()) < 50 and '```' not in ai_response:
                is_likely_factual = True
                break

    # Skip command extraction for factual responses
    if is_likely_factual:
        return []

    # Only extract commands from code blocks (most reliable source)
    # Made the \n after ``` optional to handle cases where AI omits it
    code_blocks = re.findall(r'```(?:bash|sh)?\n?([\s\S]*?)```', ai_response)

    # Split the AI response into sections
    sections = re.split(r'```(?:bash|sh)?\n[\s\S]*?```', ai_response)

    for i, block in enumerate(code_blocks):
        # Get the text before this code block (if available)
        context_before = sections[i] if i < len(sections) else ""

        # Skip code blocks that appear to be presenting information rather than commands
        skip_patterns = [
            r'(?i)example',
            r'(?i)here\'s how',
            r'(?i)alternatively',
            r'(?i)you can use',
            r'(?i)other approach',
            r'(?i)result is',
            r'(?i)output will be',
            r'(?i)this is what'
        ]

        should_skip = False
        for pattern in skip_patterns:
            search_context = context_before[-100:] if len(context_before) > 100 else context_before
            if re.search(pattern, search_context):
                should_skip = True
                break

        if should_skip:
            continue

        for line in block.splitlines():
            # Skip blank lines and comments
            if not line.strip() or line.strip().startswith('#'):
                continue
            if is_likely_command(line):
                commands.append(line.strip())
                # If we have a max limit and reached it, return early
                if max_commands and len(commands) >= max_commands:
                    # Deduplicate before returning
                    seen = set()
                    result = []
                    for cmd in commands:
                        if cmd and cmd not in seen:
                            seen.add(cmd)
                            result.append(cmd)
                    return result

    # Deduplicate, preserve order
    seen = set()
    result = []
    for cmd in commands:
        if cmd and cmd not in seen:
            seen.add(cmd)
            result.append(cmd)
    return result

def is_stateful_command(cmd):
    """Return True if the command changes shell state."""
    if not cmd:
        return False
    first_word = cmd.split()[0] if cmd.split() else ""
    return first_word in STATEFUL_COMMANDS

def is_risky_command(cmd):
    """Return True if the command is potentially risky."""
    if not cmd:
        return False
    first_word = cmd.split()[0] if cmd.split() else ""
    return any(risky in first_word for risky in RISKY_COMMANDS)

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