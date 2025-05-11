import subprocess

def is_shell_command(text):
    # Naive check: if it starts with a common shell command or contains a pipe/redirect
    shell_keywords = ['ls', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 'cp', 'mv', 'rm', 'mkdir', 'touch']
    return any(text.strip().startswith(cmd) for cmd in shell_keywords) or '|' in text or '>' in text or '<' in text

def run_shell_command(cmd):
    """Execute a shell command and print its output.

    Returns True if the command succeeded, False otherwise.
    """
    try:
        # Show what's being executed
        print(f"\nExecuting: {cmd}")
        print("-" * 80)  # Separator line for clarity

        # Run the command
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

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
