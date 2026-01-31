import subprocess
import shlex
import re

def is_shell_command(text):
    """Check if text appears to be a shell command.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if text appears to be a shell command
    """
    if not text or not isinstance(text, str):
        return False
    
    text = text.strip()
    if not text:
        return False
    
    # Check for common shell commands
    shell_keywords = ['ls', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 'cp', 'mv', 'rm', 'mkdir', 'touch', 'pwd', 'whoami', 'date', 'ps', 'kill', 'git', 'npm', 'pip', 'python', 'node']
    
    # Check if it starts with a known command or contains shell operators
    has_shell_operator = any(op in text for op in ['|', '>', '<', '&&', '||', ';', '&', '$(', '`'])
    starts_with_command = any(text.startswith(cmd) for cmd in shell_keywords)
    
    return starts_with_command or has_shell_operator

def sanitize_command(cmd):
    """Sanitize and validate a shell command for security.
    
    Args:
        cmd (str): Command to sanitize
        
    Returns:
        str: Sanitized command or None if invalid
    """
    if not cmd or not isinstance(cmd, str):
        return None
    
    cmd = cmd.strip()
    if not cmd:
        return None
    
    # Remove leading/trailing whitespace and normalize
    cmd = ' '.join(cmd.split())
    
    # Check for dangerous patterns that could lead to command injection
    dangerous_patterns = [
        r'\.\./',  # Directory traversal
        r'rm\s+[-/]',  # Dangerous rm commands
        r'chmod\s+777',  # Overly permissive chmod
        r'chown\s+root',  # Changing ownership to root
        r'sudo\s+.*passwd',  # Password changes
        r'passwd\s+',  # Password changes
        r'userdel\s+',  # User deletion
        r'groupdel\s+',  # Group deletion
        r'format\s+',  # Disk formatting
        r'dd\s+.*of=',  # Disk writing
        r'fdisk\s+',  # Disk partitioning
        r'mkfs\s+',  # Filesystem creation
        r'cryptsetup\s+',  # Disk encryption
        r'iptables\s+.*-F',  # Firewall flushing
        r'netstat\s+.*-p',  # Network process info
        r'kill\s+-9\s+1',  # Killing init process
        r'echo\s+.*>/proc/',  # Writing to proc filesystem
        r'echo\s+.*>/sys/',  # Writing to sys filesystem
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return None  # Reject dangerous commands
    
    # Check for command injection attempts
    injection_patterns = [
        r';\s*rm\s+',  # Command chaining with rm
        r';\s*sudo\s+',  # Command chaining with sudo
        r';\s*passwd\s+',  # Command chaining with passwd
        r'\|\s*rm\s+',  # Pipe to rm
        r'\|\s*sudo\s+',  # Pipe to sudo
        r'\|\s*passwd\s+',  # Pipe to passwd
        r'\$\(\s*rm\s+',  # Command substitution with rm
        r'\$\(\s*sudo\s+',  # Command substitution with sudo
        r'\$\(\s*passwd\s+',  # Command substitution with passwd
        r'`rm\s+',  # Backtick command substitution with rm
        r'`sudo\s+',  # Backtick command substitution with sudo
        r'`passwd\s+',  # Backtick command substitution with passwd
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return None  # Reject potential injection attempts
    
    return cmd

def run_shell_command(cmd):
    """Execute a shell command with security validation and print its output.

    Args:
        cmd (str): Command to execute
        
    Returns:
        bool: True if the command succeeded, False otherwise.
    """
    if not cmd:
        print("Error: No command provided")
        return False
    
    # Sanitize the command
    sanitized_cmd = sanitize_command(cmd)
    if sanitized_cmd is None:
        print("Error: Command contains potentially dangerous operations and was rejected for security reasons.")
        return False
    
    try:
        # Show what's being executed
        print(f"\nExecuting: {sanitized_cmd}")
        print("-" * 80)  # Separator line for clarity

        # Use shlex.split for safer command parsing
        try:
            cmd_args = shlex.split(sanitized_cmd)
        except ValueError as e:
            print(f"Error: Invalid command syntax: {e}")
            return False

        # Run the command with shell=False for better security
        result = subprocess.run(cmd_args, check=True, capture_output=True, text=True)

        # Always print the output, even if it's empty
        if result.stdout:
            print(result.stdout.rstrip())
        else:
            print("Command executed successfully. No output.")

        print("-" * 80)  # Separator line for clarity
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 80)  # Separator line for clarity
        if e.stderr:
            print(f"Error: {e.stderr.strip()}")
        else:
            print(f"Command failed with exit code {e.returncode}")
        print("-" * 80)  # Separator line for clarity
        return False
    except Exception as e:
        print("-" * 80)  # Separator line for clarity
        print(f"Unexpected error: {e}")
        print("-" * 80)  # Separator line for clarity
        return False
