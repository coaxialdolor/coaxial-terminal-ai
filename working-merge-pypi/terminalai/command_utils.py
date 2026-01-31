import subprocess
import platform # Import platform module to check OS
import os # Import os for path manipulation
import re
import shlex
import tempfile

COMMON_POWERSHELL_CMDLET_STARTS = [
    "remove-item", "get-childitem", "copy-item", "move-item", "new-item", "set-location",
    "select-string", "get-content", "set-content", "clear-content", "start-process",
    "stop-process", "get-process", "get-service", "start-service", "stop-service",
    "invoke-webrequest", "invoke-restmethod", "get-command", "get-help", "test-path",
    "resolve-path", "get-date", "measure-object", "write-output", "write-host"
] # Add more as needed, ensure lowercase

def is_shell_command(command):
    """Check if a string looks like a shell command."""
    # Empty string or None is not a command
    if not command:
        return False

    # Split the command on whitespace
    parts = command.strip().split()
    if not parts:
        return False

    # Get the command name (first part before any spaces)
    cmd_name = parts[0]

    # Check if it starts with a shell built-in
    builtins = [
        "cd", "export", "source", "alias", "unalias", "set", "unset",
        "echo", "read", "eval", "exec", "pwd", "exit", "while", "for",
        "if", "then", "fi", "return", "function", "break", "continue",
        "pushd", "popd", "ls", "mv", "cp", "rm", "grep", "find", "cat",
        "mkdir", "rmdir", "touch", "chmod", "chown", "curl", "wget",
        "git", "python", "python3", "node", "npm", "yarn", "docker",
        "make", "gcc", "go", "cargo", "rustc", "java", "javac", "mvn",
        "sudo", "apt", "apt-get", "yum", "brew", "pip", "pip3", "gem",
        "sh", "bash", "zsh",
    ]

    # Add macOS specific commands
    if platform.system() == "Darwin":
        builtins.extend(["open", "pbcopy", "pbpaste", "defaults", "softwareupdate", "xcode-select", "pkgutil", "osascript", "networksetup"])

    # Add Linux specific commands
    if platform.system() == "Linux":
        builtins.extend(["systemctl", "journalctl", "apt", "apt-get", "yum", "dnf", "pacman"])

    # Add Windows specific commands (with or without .exe extension)
    if platform.system() == "Windows":
        builtins.extend(["dir", "powershell", "cmd", "ipconfig", "ping", "netstat", "tasklist", "taskkill", "fc", "type"])
        # Handle potential .exe extension in Windows
        windows_cmd = re.sub(r'\.exe$', '', cmd_name)
        if windows_cmd in builtins:
            return True

    # Looks like a valid shell command if the first word is in our builtins list
    return cmd_name in builtins

def run_shell_command(command):
    """Execute a shell command and return whether it was successful."""
    try:
        # Use shlex to properly split the command while respecting quotes
        args = shlex.split(command)

        # Run the command and capture output (both stdout and stderr)
        result = subprocess.run(
            args,
            check=False,  # Don't raise exception on non-zero exit
            capture_output=True,
            text=True
        )

        # Print the stdout
        if result.stdout:
            print(result.stdout.strip())

        # Print the stderr (if any)
        if result.stderr:
            print(result.stderr.strip())

        # Return True if command succeeded, False otherwise
        return result.returncode == 0

    except Exception as e:
        print(f"Error executing command: {e}")
        return False


def sanitize_command(cmd):
    """Sanitize and validate a shell command for security.

    Args:
        cmd (str): Command to sanitize

    Returns:
        str: Sanitized command
    """
    if not cmd or not isinstance(cmd, str):
        return None

    cmd = cmd.strip()
    if not cmd:
        return None

    # Remove leading/trailing whitespace and normalize
    cmd = ' '.join(cmd.split())

    return cmd

def is_informational_command(cmd):
    """Check if a command is informational and safe to execute immediately.

    Args:
        cmd (str): Command to check

    Returns:
        bool: True if command is informational
    """
    if not cmd or not isinstance(cmd, str):
        return False

    cmd = cmd.strip().lower()

    # Informational commands that are safe to execute
    informational_patterns = [
        # File reading commands
        r'^cat\s+', r'^head\s+', r'^tail\s+', r'^grep\s+', r'^find\s+',
        r'^ls\s*', r'^dir\s*', r'^pwd\s*', r'^whoami\s*', r'^date\s*',
        r'^echo\s+', r'^which\s+', r'^whereis\s+', r'^type\s+',
        r'^man\s+', r'^help\s+', r'^info\s+',

        # System info commands
        r'^uname\s*', r'^hostname\s*', r'^uptime\s*', r'^df\s*',
        r'^free\s*', r'^ps\s*', r'^top\s*', r'^htop\s*',

        # Git commands (read-only)
        r'^git\s+(status|diff|log|show|branch|remote|config\s+--get|config\s+--list)',
        r'^git\s+(rev-parse|rev-list|ls-remote)',

        # Package managers (read-only)
        r'^(npm|yarn|pip|pip3|conda|brew)\s+(list|show|info|search)',
        r'^(apt|apt-get|yum|dnf)\s+(list|show|info|search)',

        # Development tools
        r'^(python|python3|node|java)\s+--version',
        r'^(gcc|g\+\+|clang|make)\s+--version',
        r'^docker\s+(version|info|ps|images|network\s+ls|volume\s+ls)',
        r'^kubectl\s+(version|cluster-info|get\s+(pods|services|nodes|deployments))',

        # Network commands
        r'^(curl|wget)\s+--head',
        r'^ping\s+-c\s+\d+',
        r'^nslookup\s+', r'^dig\s+', r'^host\s+',

        # Text processing
        r'^(sort|uniq|wc|cut|awk|sed)\s+',
        r'^tr\s+', r'^sed\s+', r'^awk\s+',

        # Environment
        r'^env\s*', r'^printenv\s*', r'^set\s*',
    ]

    # Check if command matches any informational pattern
    for pattern in informational_patterns:
        if re.match(pattern, cmd):
            return True

    # Allow simple commands without arguments that are likely informational
    simple_commands = ['ls', 'dir', 'pwd', 'whoami', 'date', 'uname', 'hostname', 'uptime']
    if cmd in simple_commands:
        return True

    return False
