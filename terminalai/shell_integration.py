"""Shell integration utilities for TerminalAI."""
import os
import platform
from terminalai.color_utils import colorize_command

def get_system_context():
    """Return the system context string for the prompt."""
    system = platform.system()
    if system == "Darwin":
        sys_str = "macOS/zsh"
    elif system == "Linux":
        sys_str = "Linux/bash"
    elif system == "Windows":
        sys_str = "Windows/PowerShell"
    else:
        sys_str = "a Unix-like system"
    from terminalai.config import get_system_prompt
    prompt = get_system_prompt()
    return prompt.replace("the user's system", sys_str)

def install_shell_integration():
    """Install shell integration for handling stateful commands."""
    system = platform.system()

    if system == "Darwin" or system == "Linux":
        # Install for bash/zsh
        home = os.path.expanduser("~")

        # Determine which shell config file to use
        shell = os.environ.get("SHELL", "")
        config_file = ""

        if "zsh" in shell:
            config_file = os.path.join(home, ".zshrc")
        elif "bash" in shell:
            config_file = os.path.join(home, ".bashrc")
            # For macOS, also check .bash_profile
            if system == "Darwin" and not os.path.exists(config_file):
                config_file = os.path.join(home, ".bash_profile")

        if not config_file or not os.path.exists(config_file):
            print(colorize_command(
                "Could not determine shell config file. Please manually add the function to your shell config."
            ))
            return False

        # First check if already installed
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "function _terminalai_execute" in content:
                    print(colorize_command("Shell integration already installed."))
                    return True
        except (IOError, FileNotFoundError, PermissionError) as e:
            print(colorize_command(f"Error reading config file: {e}"))
            return False

        # Append the function to the shell config
        shell_function = """
# TerminalAI shell integration for stateful commands
function _terminalai_execute() {
    # Execute the command given by the AI
    local cmd="$1"
    if [ -n "$cmd" ]; then
        echo "Executing: $cmd"
        eval "$cmd"
    fi
}
"""

        try:
            with open(config_file, 'a', encoding='utf-8') as f:
                f.write(shell_function)

            print(colorize_command(
                f"Shell integration installed in {config_file}.\n"
                f"Please restart your shell or run 'source {config_file}'."
            ))
            return True
        except (IOError, FileNotFoundError, PermissionError) as e:
            print(colorize_command(f"Error installing shell integration: {e}"))
            return False

    elif system == "Windows":
        # For Windows PowerShell
        try:
            import subprocess
            # Check if PowerShell profile exists
            ps_command = "if(!(Test-Path -Path $PROFILE)) { New-Item -Path $PROFILE -Type File -Force }"
            subprocess.run(["powershell", "-Command", ps_command], check=True)

            # Check if already installed
            ps_check = "if(Select-String -Path $PROFILE -Pattern 'function TerminalAIExecute') { Write-Output 'installed' } else { Write-Output 'notinstalled' }"
            result = subprocess.run(["powershell", "-Command", ps_check], capture_output=True, text=True, check=True)

            if "installed" in result.stdout:
                print(colorize_command("Shell integration already installed in PowerShell profile."))
                return True

            # Add function to profile
            ps_function = """
# TerminalAI shell integration for stateful commands
function TerminalAIExecute {
    param($Command)
    if($Command) {
        Write-Host "Executing: $Command" -ForegroundColor Cyan
        Invoke-Expression $Command
    }
}
"""

            ps_append = f"Add-Content -Path $PROFILE -Value '{ps_function}'"
            subprocess.run(["powershell", "-Command", ps_append], check=True)

            print(colorize_command(
                "Shell integration installed in PowerShell profile.\n"
                "Please restart PowerShell or run '. $PROFILE'."
            ))
            return True
        except (subprocess.SubprocessError, FileNotFoundError, PermissionError) as e:
            print(colorize_command(f"Error installing shell integration: {e}"))
            return False

    else:
        print(colorize_command(f"Unsupported system: {system}"))
        return False

def uninstall_shell_integration():
    """Remove shell integration for handling stateful commands."""
    system = platform.system()

    if system == "Darwin" or system == "Linux":
        # Remove from bash/zsh
        home = os.path.expanduser("~")

        # Determine which shell config file to use
        shell = os.environ.get("SHELL", "")
        config_file = ""

        if "zsh" in shell:
            config_file = os.path.join(home, ".zshrc")
        elif "bash" in shell:
            config_file = os.path.join(home, ".bashrc")
            # For macOS, also check .bash_profile
            if system == "Darwin" and not os.path.exists(config_file):
                config_file = os.path.join(home, ".bash_profile")

        if not config_file or not os.path.exists(config_file):
            print(colorize_command("Could not determine shell config file."))
            return False

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remove the function if it exists
            new_content = content
            if "# TerminalAI shell integration" in content:
                start_idx = content.find("# TerminalAI shell integration")
                end_idx = content.find("}", start_idx)
                if end_idx > start_idx:
                    # Extract complete function including the closing brace and any trailing newline
                    end_idx = content.find("\n", end_idx + 1) if content.find("\n", end_idx + 1) != -1 else len(content)
                    new_content = content[:start_idx] + content[end_idx:]

            if new_content != content:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(colorize_command(
                    f"Shell integration removed from {config_file}.\n"
                    f"Please restart your shell or run 'source {config_file}'."
                ))
                return True
            else:
                print(colorize_command("Shell integration not found in config file."))
                return False
        except (IOError, FileNotFoundError, PermissionError) as e:
            print(colorize_command(f"Error removing shell integration: {e}"))
            return False

    elif system == "Windows":
        # For Windows PowerShell
        try:
            import subprocess
            # Check if function exists in profile
            ps_check = "if(Test-Path -Path $PROFILE) { if(Select-String -Path $PROFILE -Pattern 'function TerminalAIExecute') { Write-Output 'installed' } else { Write-Output 'notinstalled' } } else { Write-Output 'noprofile' }"
            result = subprocess.run(["powershell", "-Command", ps_check], capture_output=True, text=True, check=True)

            if "installed" not in result.stdout:
                print(colorize_command("Shell integration not found in PowerShell profile."))
                return False

            # Remove function from profile
            ps_remove = "(Get-Content $PROFILE) | Where-Object { $_ -notmatch 'TerminalAI shell integration' -and $_ -notmatch 'function TerminalAIExecute' } | Set-Content $PROFILE"
            subprocess.run(["powershell", "-Command", ps_remove], check=True)

            print(colorize_command(
                "Shell integration removed from PowerShell profile.\n"
                "Please restart PowerShell or run '. $PROFILE'."
            ))
            return True
        except (subprocess.SubprocessError, FileNotFoundError, PermissionError) as e:
            print(colorize_command(f"Error removing shell integration: {e}"))
            return False

    else:
        print(colorize_command(f"Unsupported system: {system}"))
        return False