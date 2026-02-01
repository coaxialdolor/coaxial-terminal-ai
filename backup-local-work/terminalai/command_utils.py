import subprocess
import shlex
import re
from terminalai.color_utils import colorize_command, colorize_info, colorize_error, colorize_success

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

def is_dangerous_command(cmd):
    """Check if a command is potentially dangerous.
    
    Args:
        cmd (str): Command to check
        
    Returns:
        bool: True if command is potentially dangerous
    """
    if not cmd:
        return False
    
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
        r'echo\s+.*>\s*/proc/',  # Writing to proc filesystem
        r'echo\s+.*>\s*/sys/',  # Writing to sys filesystem
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True  # Command is potentially dangerous
    
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
            return True  # Command is potentially dangerous
    
    return False

def is_informational_command(cmd):
    """Check if a command is purely informational and safe to execute without confirmation.
    
    Args:
        cmd (str): Command to check
        
    Returns:
        bool: True if command is informational and safe
    """
    if not cmd:
        return False
    
    # List of safe informational commands that should execute immediately
    informational_patterns = [
        r'^ls(\s|$)',  # ls commands
        r'^pwd(\s|$)',  # pwd command
        r'^whoami(\s|$)',  # whoami command
        r'^date(\s|$)',  # date command
        r'^cat(\s|$)',  # cat command
        r'^head(\s|$)',  # head command
        r'^tail(\s|$)',  # tail command
        r'^grep(\s|$)',  # grep command
        r'^find(\s|$)',  # find command
        r'^echo(\s|$)',  # echo command
        r'^which(\s|$)',  # which command
        r'^whereis(\s|$)',  # whereis command
        r'^ps(\s|$)',  # ps command
        r'^top(\s|$)',  # top command
        r'^df(\s|$)',  # df command
        r'^du(\s|$)',  # du command
        r'^free(\s|$)',  # free command
        r'^uname(\s|$)',  # uname command
        r'^hostname(\s|$)',  # hostname command
        r'^id(\s|$)',  # id command
        r'^env(\s|$)',  # env command
        r'^printenv(\s|$)',  # printenv command
        r'^jobs(\s|$)',  # jobs command
        r'^history(\s|$)',  # history command
        r'^alias(\s|$)',  # alias command
        r'^type(\s|$)',  # type command
        r'^command(\s|$)',  # command command
        r'^git\s+(status|log|diff|show|branch|remote|config)(\s|$)',  # git informational commands
        r'^npm\s+(list|ls|info|show|view)(\s|$)',  # npm informational commands
        r'^pip\s+(list|show|freeze)(\s|$)',  # pip informational commands
        r'^python\s+--version|python\s+-V',  # python version
        r'^node\s+--version|node\s+-v',  # node version
        r'^java\s+--version|java\s+-version',  # java version
        r'^gcc\s+--version|gcc\s+-v',  # gcc version
        r'^clang\s+--version|clang\s+-v',  # clang version
        r'^make\s+--version|make\s+-v',  # make version
        r'^cmake\s+--version|cmake\s+-version',  # cmake version
        r'^docker\s+(version|info|ps|images|logs)(\s|$)',  # docker informational commands
        r'^kubectl\s+(version|get|describe|logs)(\s|$)',  # kubectl informational commands
        r'^aws\s+(help|version)(\s|$)',  # aws informational commands
        r'^gcloud\s+(help|version)(\s|$)',  # gcloud informational commands
        r'^curl\s+--version|curl\s+-V',  # curl version
        r'^wget\s+--version|wget\s+-V',  # wget version
        r'^ssh\s+-V',  # ssh version
        r'^rsync\s+--version|rsync\s+-V',  # rsync version
        r'^tar\s+--version|tar\s+-V',  # tar version
        r'^zip\s+--version|zip\s+-v',  # zip version
        r'^unzip\s+--version|unzip\s+-v',  # unzip version
        r'^gzip\s+--version|gzip\s+-V',  # gzip version
        r'^bzip2\s+--version|bzip2\s+-V',  # bzip2 version
        r'^xz\s+--version|xz\s+-V',  # xz version
        r'^vim\s+--version|vim\s+-v',  # vim version
        r'^nano\s+--version|nano\s+-V',  # nano version
        r'^emacs\s+--version|emacs\s+-version',  # emacs version
        r'^code\s+--version|code\s+-v',  # vscode version
        r'^subl\s+--version|subl\s+-v',  # sublime version
        r'^atom\s+--version|atom\s+-v',  # atom version
        r'^git\s+status',  # git status
        r'^git\s+log',  # git log
        r'^git\s+diff',  # git diff
        r'^git\s+show',  # git show
        r'^git\s+branch',  # git branch
        r'^git\s+remote',  # git remote
        r'^git\s+config',  # git config
        r'^npm\s+list',  # npm list
        r'^npm\s+ls',  # npm ls
        r'^npm\s+info',  # npm info
        r'^npm\s+show',  # npm show
        r'^npm\s+view',  # npm view
        r'^pip\s+list',  # pip list
        r'^pip\s+show',  # pip show
        r'^pip\s+freeze',  # pip freeze
        r'^docker\s+version',  # docker version
        r'^docker\s+info',  # docker info
        r'^docker\s+ps',  # docker ps
        r'^docker\s+images',  # docker images
        r'^docker\s+logs',  # docker logs
        r'^kubectl\s+version',  # kubectl version
        r'^kubectl\s+get',  # kubectl get
        r'^kubectl\s+describe',  # kubectl describe
        r'^kubectl\s+logs',  # kubectl logs
        r'^aws\s+help',  # aws help
        r'^aws\s+version',  # aws version
        r'^gcloud\s+help',  # gcloud help
        r'^gcloud\s+version',  # gcloud version
        r'^curl\s+--version',  # curl version
        r'^curl\s+-V',  # curl version
        r'^wget\s+--version',  # wget version
        r'^wget\s+-V',  # wget version
        r'^ssh\s+-V',  # ssh version
        r'^rsync\s+--version',  # rsync version
        r'^rsync\s+-V',  # rsync version
        r'^tar\s+--version',  # tar version
        r'^tar\s+-V',  # tar version
        r'^zip\s+--version',  # zip version
        r'^zip\s+-v',  # zip version
        r'^unzip\s+--version',  # unzip version
        r'^unzip\s+-v',  # unzip version
        r'^gzip\s+--version',  # gzip version
        r'^gzip\s+-V',  # gzip version
        r'^bzip2\s+--version',  # bzip2 version
        r'^bzip2\s+-V',  # bzip2 version
        r'^xz\s+--version',  # xz version
        r'^xz\s+-V',  # xz version
        r'^vim\s+--version',  # vim version
        r'^vim\s+-v',  # vim version
        r'^nano\s+--version',  # nano version
        r'^nano\s+-V',  # nano version
        r'^emacs\s+--version',  # emacs version
        r'^emacs\s+-version',  # emacs version
        r'^code\s+--version',  # vscode version
        r'^code\s+-v',  # vscode version
        r'^subl\s+--version',  # sublime version
        r'^subl\s+-v',  # sublime version
        r'^atom\s+--version',  # atom version
        r'^atom\s+-v',  # atom version
    ]
    
    for pattern in informational_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True  # Command is informational and safe
    
    # Check for safe command combinations (pipes, redirects that don't modify files)
    safe_combinations = [
        r'^ls\s+\|\s+grep',  # ls piped to grep
        r'^find\s+.*\|\s+grep',  # find piped to grep
        r'^cat\s+.*\|\s+grep',  # cat piped to grep
        r'^head\s+.*\|\s+grep',  # head piped to grep
        r'^tail\s+.*\|\s+grep',  # tail piped to grep
        r'^ps\s+\|\s+grep',  # ps piped to grep
        r'^df\s+\|\s+grep',  # df piped to grep
        r'^du\s+\|\s+grep',  # du piped to grep
        r'^git\s+.*\|\s+grep',  # git commands piped to grep
        r'^cat\s+.*\|\s+head',  # cat piped to head
        r'^cat\s+.*\|\s+tail',  # cat piped to tail
        r'^grep\s+.*\|\s+head',  # grep piped to head
        r'^grep\s+.*\|\s+tail',  # grep piped to tail
        r'^find\s+.*\|\s+head',  # find piped to head
        r'^find\s+.*\|\s+tail',  # find piped to tail
        r'^ls\s+.*\|\s+head',  # ls piped to head
        r'^ls\s+.*\|\s+tail',  # ls piped to tail
        r'^cat\s+.*\|\s+wc',  # cat piped to wc
        r'^grep\s+.*\|\s+wc',  # grep piped to wc
        r'^find\s+.*\|\s+wc',  # find piped to wc
        r'^ls\s+.*\|\s+wc',  # ls piped to wc
        r'^head\s+.*\|\s+wc',  # head piped to wc
        r'^tail\s+.*\|\s+wc',  # tail piped to wc
        r'^ps\s+\|\s+wc',  # ps piped to wc
        r'^df\s+\|\s+wc',  # df piped to wc
        r'^du\s+\|\s+wc',  # du piped to wc
        r'^git\s+.*\|\s+wc',  # git commands piped to wc
        r'^cat\s+.*\|\s+sort',  # cat piped to sort
        r'^grep\s+.*\|\s+sort',  # grep piped to sort
        r'^find\s+.*\|\s+sort',  # find piped to sort
        r'^ls\s+.*\|\s+sort',  # ls piped to sort
        r'^head\s+.*\|\s+sort',  # head piped to sort
        r'^tail\s+.*\|\s+sort',  # tail piped to sort
        r'^ps\s+\|\s+sort',  # ps piped to sort
        r'^df\s+\|\s+sort',  # df piped to sort
        r'^du\s+\|\s+sort',  # du piped to sort
        r'^git\s+.*\|\s+sort',  # git commands piped to sort
        r'^cat\s+.*\|\s+uniq',  # cat piped to uniq
        r'^grep\s+.*\|\s+uniq',  # grep piped to uniq
        r'^find\s+.*\|\s+uniq',  # find piped to uniq
        r'^ls\s+.*\|\s+uniq',  # ls piped to uniq
        r'^head\s+.*\|\s+uniq',  # head piped to uniq
        r'^tail\s+.*\|\s+uniq',  # tail piped to uniq
        r'^ps\s+\|\s+uniq',  # ps piped to uniq
        r'^df\s+\|\s+uniq',  # df piped to uniq
        r'^du\s+\|\s+uniq',  # du piped to uniq
        r'^git\s+.*\|\s+uniq',  # git commands piped to uniq
    ]
    
    for pattern in safe_combinations:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True  # Command is informational and safe
    
    # Check for safe redirects (reading from files, not writing to them)
    safe_redirects = [
        r'^cat\s+.*<\s+',  # cat with input redirect
        r'^grep\s+.*<\s+',  # grep with input redirect
        r'^head\s+.*<\s+',  # head with input redirect
        r'^tail\s+.*<\s+',  # tail with input redirect
        r'^sort\s+.*<\s+',  # sort with input redirect
        r'^uniq\s+.*<\s+',  # uniq with input redirect
        r'^wc\s+.*<\s+',  # wc with input redirect
        r'^find\s+.*<\s+',  # find with input redirect
        r'^ls\s+.*<\s+',  # ls with input redirect
        r'^ps\s+.*<\s+',  # ps with input redirect
        r'^df\s+.*<\s+',  # df with input redirect
        r'^du\s+.*<\s+',  # du with input redirect
        r'^git\s+.*<\s+',  # git commands with input redirect
        r'^npm\s+.*<\s+',  # npm commands with input redirect
        r'^pip\s+.*<\s+',  # pip commands with input redirect
        r'^docker\s+.*<\s+',  # docker commands with input redirect
        r'^kubectl\s+.*<\s+',  # kubectl commands with input redirect
        r'^aws\s+.*<\s+',  # aws commands with input redirect
        r'^gcloud\s+.*<\s+',  # gcloud commands with input redirect
        r'^curl\s+.*<\s+',  # curl commands with input redirect
        r'^wget\s+.*<\s+',  # wget commands with input redirect
        r'^ssh\s+.*<\s+',  # ssh commands with input redirect
        r'^rsync\s+.*<\s+',  # rsync commands with input redirect
        r'^tar\s+.*<\s+',  # tar commands with input redirect
        r'^zip\s+.*<\s+',  # zip commands with input redirect
        r'^unzip\s+.*<\s+',  # unzip commands with input redirect
        r'^gzip\s+.*<\s+',  # gzip commands with input redirect
        r'^bzip2\s+.*<\s+',  # bzip2 commands with input redirect
        r'^xz\s+.*<\s+',  # xz commands with input redirect
        r'^vim\s+.*<\s+',  # vim commands with input redirect
        r'^nano\s+.*<\s+',  # nano commands with input redirect
        r'^emacs\s+.*<\s+',  # emacs commands with input redirect
        r'^code\s+.*<\s+',  # vscode commands with input redirect
        r'^subl\s+.*<\s+',  # sublime commands with input redirect
        r'^atom\s+.*<\s+',  # atom commands with input redirect
    ]
    
    for pattern in safe_redirects:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True  # Command is informational and safe
    
    return False

def run_shell_command(cmd, show_command_box=True):
    """Execute a shell command with security validation and print its output.

    Args:
        cmd (str): Command to execute
        show_command_box (bool): Whether to show the command in a small box format
        
    Returns:
        bool: True if the command succeeded, False otherwise.
    """
    if not cmd:
        print("Error: No command provided")
        return False
    
    # Sanitize the command
    sanitized_cmd = sanitize_command(cmd)
    if sanitized_cmd is None:
        print("Error: Invalid command")
        return False
    
    # Check if command is informational and should execute immediately
    if is_informational_command(sanitized_cmd):
        # For informational commands, execute immediately with small command box
        if show_command_box:
            # Create a properly formatted command box (original remote format)
            box_width = 72
            
            print(f"\n{colorize_info('┌─ Command executed ──────────────────────────────────────────────────────┐')}")
            print(f"{colorize_info('│')} {colorize_command(sanitized_cmd):<70} {colorize_info('│')}")
            print(f"{colorize_info('└──────────────────────────────────────────────────────────────────────┘')}")
            print()
        
        try:
            # Check if command contains shell operators that require shell=True
            has_shell_operators = any(op in sanitized_cmd for op in ['|', '>', '<', '&&', '||', ';', '&', '$(', '`'])
            
            if has_shell_operators:
                # For commands with shell operators, use shell=True but validate carefully
                result = subprocess.run(sanitized_cmd, shell=True, check=True, capture_output=True, text=True)
            else:
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
            
            return True
        except subprocess.CalledProcessError as e:
            if e.stderr:
                print(f"Error: {e.stderr.strip()}")
            else:
                print(f"Command failed with exit code {e.returncode}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
    
    # Check if command is potentially dangerous
    if is_dangerous_command(sanitized_cmd):
        print(f"⚠️  WARNING: This command appears to be potentially dangerous:")
        print(f"   {sanitized_cmd}")
        print("This command could:")
        print("- Delete files or directories")
        print("- Modify system settings")
        print("- Change user permissions")
        print("- Affect system security")
        print()
        confirm = input("Are you sure you want to execute this command? [y/N]: ").lower().strip()
        if confirm != 'y':
            print("Command execution cancelled.")
            return False
        print("Proceeding with command execution...")
    
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
