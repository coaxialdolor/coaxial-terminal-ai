"""Command extraction and detection functionality."""
import re

# Constants for command detection (expanded)
_BASE_KNOWN_COMMANDS = [
    "ls", "cd", "cat", "cp", "mv", "rm", "find", "grep", "awk", "sed", "chmod",
    "chown", "head", "tail", "touch", "mkdir", "rmdir", "tree", "du", "df", "ps",
    "top", "htop", "less", "more", "man", "which", "whereis", "locate", "pwd", "whoami",
    "date", "cal", "env", "export", "ssh", "scp", "curl", "wget", "tar", "zip", "unzip",
    "python", "pip", "brew", "apt", "yum", "dnf", "docker", "git", "npm", "node",
    "make", "gcc", "clang", "javac", "java", "mvn", "gradle", "cargo", "rustc",
    "go", "swift", "kotlin", "dotnet", "perl", "php", "ruby", "mvn", "jest",
    "nano", "vim", "vi", "emacs", "pico", "subl", "code", "echo" # Added echo
]

_WINDOWS_CMD_COMMANDS = [
    "dir", "del", "copy", "move", "rd", "md", "cls", "type", "ren", "xcopy", "format",
    "diskpart", "tasklist", "taskkill", "sfc", "chkdsk", "schtasks", "netstat", "ipconfig"
]

_POWERSHELL_CMDLET_KEYWORDS = [ # Keywords from COMMON_POWERSHELL_CMDLET_STARTS in command_utils.py
    "remove-item", "get-childitem", "copy-item", "move-item", "new-item", "set-location",
    "select-string", "get-content", "set-content", "clear-content", "start-process",
    "stop-process", "get-process", "get-service", "start-service", "stop-service",
    "invoke-webrequest", "invoke-restmethod", "get-command", "get-help", "test-path",
    "resolve-path", "get-date", "measure-object", "write-output", "write-host"
]

KNOWN_COMMANDS = list(set(_BASE_KNOWN_COMMANDS + _WINDOWS_CMD_COMMANDS + _POWERSHELL_CMDLET_KEYWORDS))

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
    "format", "del", "rd", "rmdir", ":(){:", "fork", "shutdown", "halt", # Corrected fork bomb
    "reboot", "init", "mkpart", "gpart", "attrib", "takeown"
]

def is_likely_command(line):
    """Return True if the line looks like a shell command."""
    line = line.strip()
    if not line or line.startswith("#"):
        return False

    # Filter out command examples with shell prompts
    prompt_pattern = r'^[~\w\-\.\/]*[$#>]\s+'
    if re.match(prompt_pattern, line):
        return False

    # Filter out commands with user/machine prefixes like "user@machine:~$"
    user_machine_pattern = r'^[\w\-]+@[\w\-]+:.*[$#>]\s+'
    if re.match(user_machine_pattern, line):
        return False

    words = line.split()
    if not words:
        return False

    # Heuristic: Skip overly long lines that are likely prose
    if len(words) > 15 and line[0].isupper():
        return False

    # Heuristic: Skip lines that look like questions or full sentences ending with punctuation
    if len(words) > 3 and line[0].isupper() and line[-1] in ['.', '!', '?']:
        # More specific check for explanatory sentences like "This command will..."
        if words[0].lower() in ["this", "the", "it", "that"] and \
           any(verb in words for verb in ["command", "script", "will", "does", "is", "are"]):
            return False
        # Avoid returning False for short, uppercased commands like "ECHO Hello"
        if len(words) > 4: # Only return False if it's a longer sentence
             return False

    first_word_lower = words[0].lower()

    if first_word_lower in KNOWN_COMMANDS or first_word_lower in STATEFUL_COMMANDS:
        return True

    shell_operators_regex = r'(?:\s|^)(?:\||&&|\|\||>|>>|<)(?:\s|$)' # Non-capturing groups for spaces/start/end
    if re.search(shell_operators_regex, line):
        for cmd_keyword in KNOWN_COMMANDS:
            if re.search(rf'\b{re.escape(cmd_keyword)}\b', line, re.IGNORECASE):
                return True

    known_cmds_pattern = "|".join(map(re.escape, KNOWN_COMMANDS))
    option_flag_with_command_regex = rf'^(?:{known_cmds_pattern})\s+(-[a-zA-Z0-9]+(?:=[^\s]+)?|--[a-zA-Z0-9-]+(?:=[^\s]+)?)(?:\s|$)'
    if re.search(option_flag_with_command_regex, line, re.IGNORECASE):
        return True

    # Heuristic for commands like `some/path/script.sh --arg value` or `variable=value command`
    if (re.search(r'\s(-[a-zA-Z0-9]|--[a-zA-Z0-9-]+)', line) or \
        re.search(r'^[a-zA-Z_][a-zA-Z0-9_]*=.*\s+[a-zA-Z_]', line)) and \
       (re.search(r'[/\\~.]', words[0]) or first_word_lower.endswith(('.sh', '.py', '.bat', '.ps1')) or first_word_lower in KNOWN_COMMANDS):
        if not first_word_lower.startswith(('http:', 'https:')):
            return True

    return False

def extract_commands(ai_response, max_commands=None, auto_mode=False):
    """
    Extract shell commands from AI response.
    It processes lines within any ```...``` code blocks using is_likely_command.
    This function is typically used for interactive mode (aliased as get_commands_interactive).

    Args:
        ai_response: The AI's response text
        max_commands: Maximum number of commands to extract
        auto_mode: If True, be more conservative about what counts as a command
    """
    extracted_commands = []
    code_block_pattern = re.compile(r'```([a-zA-Z0-9_\.-]*)?\n?([\s\S]*?)```') # Allow . and - in lang tag

    # More aggressive filtering in auto mode
    if auto_mode:
        # Look for indications of example commands or command outputs in the text
        example_indicators = [
            "example", "example:", "for example", "as an example",
            "output", "output:", "result:", "console output:",
            "terminal output", "shell output", "command output",
            "this would produce", "you would see", "you'll see"
        ]

        # If any of these indicators are present, be very careful about command extraction
        has_examples = any(indicator in ai_response.lower() for indicator in example_indicators)

        if has_examples:
            # Only extract commands from code blocks with explicit bash/shell language tags
            tagged_code_blocks = re.compile(r'```(bash|shell|sh)\n?([\s\S]*?)```')

            for match in tagged_code_blocks.finditer(ai_response):
                block_content = match.group(2)
                # For blocks with command tags, take only the first line as a potential command
                lines = block_content.strip().splitlines()
                if lines:
                    first_line = lines[0].strip()
                    if is_likely_command(first_line) and not first_line.startswith('#'):
                        extracted_commands.append(first_line)
                        if max_commands and len(extracted_commands) >= max_commands:
                            break

            # Deduplicate and return the filtered commands
            seen = set()
            final_commands = []
            for cmd in extracted_commands:
                if cmd and cmd not in seen:
                    seen.add(cmd)
                    final_commands.append(cmd)
            return final_commands

    # Standard extraction for non-auto mode or when no example indicators are found
    for match in code_block_pattern.finditer(ai_response):
        block_content = match.group(2)
        for line_in_block in block_content.splitlines():
            stripped_line_in_block = line_in_block.strip()
            if is_likely_command(stripped_line_in_block):
                extracted_commands.append(stripped_line_in_block)
                if max_commands and len(extracted_commands) >= max_commands:
                    break
        if max_commands and len(extracted_commands) >= max_commands:
            break

    seen = set()
    final_commands = []
    for cmd in extracted_commands:
        if cmd and cmd not in seen:
            seen.add(cmd)
            final_commands.append(cmd)
    return final_commands

def extract_commands_from_output(output_text, max_commands=None):
    """
    Extract shell commands from AI's textual output.
    It applies is_likely_command to lines inside ANY ```...``` code blocks
    AND to lines outside of any code blocks.
    This function is typically used for direct query mode.
    """
    extracted_commands = []
    code_block_pattern = re.compile(r'```([a-zA-Z0-9_\.-]*)?\n?([\s\S]*?)```') # Allow . and - in lang tag
    last_block_end = 0
    processed_segments = []

    for match in code_block_pattern.finditer(output_text):
        plain_text_segment = output_text[last_block_end:match.start()]
        processed_segments.append(plain_text_segment)

        block_content = match.group(2)
        processed_segments.append(block_content) # Add block content itself as a segment to be line-split

        last_block_end = match.end()

    remaining_plain_text = output_text[last_block_end:]
    processed_segments.append(remaining_plain_text)

    for segment in processed_segments:
        for line_in_segment in segment.splitlines():
            stripped_line_in_segment = line_in_segment.strip()
            if is_likely_command(stripped_line_in_segment):
                extracted_commands.append(stripped_line_in_segment)
                if max_commands and len(extracted_commands) >= max_commands:
                    break
        if max_commands and len(extracted_commands) >= max_commands:
            break

    seen = set()
    final_commands = []
    for cmd in extracted_commands:
        if cmd and cmd not in seen:
            seen.add(cmd)
            final_commands.append(cmd)
    return final_commands

def is_stateful_command(cmd):
    """Return True if the command changes shell state."""
    if not cmd:
        return False
    words = cmd.split()
    if not words:
        return False
    first_word = words[0].lower()
    return first_word in STATEFUL_COMMANDS

def is_risky_command(cmd):
    """Return True if the command is potentially risky."""
    if not cmd:
        return False
    words = cmd.split()
    if not words:
        return False
    first_word_processed = words[0].lower()
    return any(risky_cmd_keyword in first_word_processed for risky_cmd_keyword in RISKY_COMMANDS) or \
           first_word_processed in RISKY_COMMANDS

# Note: extract_commands_from_output was previously more limited.
# The new version above is more comprehensive.
# The original extract_commands (used as get_commands_interactive) is also updated slightly
# to use the more general code block regex and ensure deduplication logic is sound.
# It specifically processes content *within* detected code blocks.