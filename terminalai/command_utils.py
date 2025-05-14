import subprocess
import platform # Import platform module to check OS

def is_shell_command(text):
    # Naive check: if it starts with a common shell command or contains a pipe/redirect
    shell_keywords = ['ls', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 'cp', 'mv', 'rm', 'mkdir', 'touch']
    return any(text.strip().startswith(cmd) for cmd in shell_keywords) or '|' in text or '>' in text or '<' in text

def run_shell_command(cmd):
    """Execute a shell command and print its output.

    Returns True if the command succeeded, False otherwise.
    """
    current_os = platform.system()
    executable_cmd = cmd # Default to the original command

    # Check if on Windows and the command is 'ls' (or starts with 'ls ')
    if current_os == "Windows":
        # Normalize to check just the command part, in case of arguments
        command_parts = cmd.strip().split()
        if command_parts and command_parts[0].lower() == "ls":
            executable_cmd = f"powershell -NoProfile -Command {cmd}"
            # Optional: print a notice that we're using PowerShell for ls
            # print(f"(Notice: Executing 'ls' via PowerShell on Windows as: {executable_cmd})")

    try:
        # Show what's being executed
        print(f"\nExecuting: {executable_cmd}") # Use executable_cmd
        print("-" * 80)  # Separator line for clarity

        # Run the command
        # When using `powershell -Command ...`, shell=True might still be okay,
        # or shell=False might be preferred if executable_cmd is a full path or specific executable.
        # For simplicity and consistency with previous behavior for other commands, keeping shell=True.
        # If executable_cmd starts with "powershell", shell=True will use cmd.exe to launch powershell.exe.
        result = subprocess.run(executable_cmd, shell=True, check=True, capture_output=True, text=True)

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
