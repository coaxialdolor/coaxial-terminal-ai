import subprocess

def is_shell_command(text):
    # Naive check: if it starts with a common shell command or contains a pipe/redirect
    shell_keywords = ['ls', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 'cp', 'mv', 'rm', 'mkdir', 'touch']
    return any(text.strip().startswith(cmd) for cmd in shell_keywords) or '|' in text or '>' in text or '<' in text

def run_shell_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"
