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

def is_informational_command(cmd):
    """Check if a command is purely informational and safe to execute without confirmation.
    
    Args:
        cmd (str): Command to check
        
    Returns:
        bool: True if command is informational and safe
    """
    if not cmd:
        return False
    
    import re
    
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

def run_shell_command(command):
    """Execute a shell command and return whether it was successful."""
    try:
        system_name = platform.system()

        # On Windows, many commands are shell built-ins (e.g., 'dir') and redirection
        # is processed by the shell. Use shell=True so built-ins and operators work.
        if system_name == "Windows":
            result = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            # On POSIX, decide based on presence of shell operators
            has_shell_ops = bool(re.search(r"[|&;><]", command))
            if has_shell_ops:
                # Let the shell handle pipelines/redirection. Prefer bash if available.
                result = subprocess.run(
                    command,
                    shell=True,
                    check=False,
                    capture_output=True,
                    text=True,
                    executable=os.environ.get("SHELL", "/bin/bash"),
                )
            else:
                # Execute direct binary without a shell
                args = shlex.split(command)
                result = subprocess.run(
                    args,
                    check=False,
                    capture_output=True,
                    text=True,
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
