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
    """Install shell integration for seamless stateful command execution via 'ai' shell function."""
    import shutil
    system = platform.system()
    if system in ("Darwin", "Linux"):
        home = os.path.expanduser("~")
        shell = os.environ.get("SHELL", "")
        config_file = ""
        if "zsh" in shell:
            config_file = os.path.join(home, ".zshrc")
        elif "bash" in shell:
            config_file = os.path.join(home, ".bashrc")
            if system == "Darwin" and not os.path.exists(config_file):
                config_file = os.path.join(home, ".bash_profile")
        if not config_file or not os.path.exists(config_file):
            print(colorize_command(
                "Could not determine shell config file. Please manually add the function to your shell config."
            ))
            return False
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # Remove any existing TerminalAI block
        start_marker = '# >>> TERMINALAI SHELL INTEGRATION START'
        end_marker = '# <<< TERMINALAI SHELL INTEGRATION END'
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if start_idx != -1 and end_idx != -1:
            end_idx += len(end_marker)
            content = content[:start_idx] + content[end_idx:]
        # Check for other ai aliases/functions
        if 'function ai' in content or 'alias ai=' in content:
            print(colorize_command("Warning: An 'ai' function or alias already exists in your shell config. Please resolve this conflict before installing."))
            return False
        ai_path = shutil.which("ai") or "ai"
        shell_function = f"""
# >>> TERMINALAI SHELL INTEGRATION START
# Added by TerminalAI (https://github.com/coaxialdolor/terminalai)
# This shell function enables seamless stateful command execution via eval $(ai ...)
ai() {{
    local output
    output=$( {ai_path} --eval-mode "$@" )
    if [ -n "$output" ]; then
        eval "$output"
    fi
}}
# <<< TERMINALAI SHELL INTEGRATION END
"""
        # Ensure block is separated by newlines
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + shell_function + "\n"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(colorize_command(
            f"TerminalAI shell integration installed in {config_file} as 'ai' shell function.\n"
            f"Please restart your shell or run 'source {config_file}'."
        ))
        return True
    if system == "Windows":
        print(colorize_command("PowerShell shell integration is not yet implemented for seamless eval mode."))
        return False
    print(colorize_command(f"Unsupported system: {system}"))
    return False

def uninstall_shell_integration():
    """Remove the ai shell function installed by TerminalAI."""
    system = platform.system()
    if system in ("Darwin", "Linux"):
        home = os.path.expanduser("~")
        shell = os.environ.get("SHELL", "")
        config_file = ""
        if "zsh" in shell:
            config_file = os.path.join(home, ".zshrc")
        elif "bash" in shell:
            config_file = os.path.join(home, ".bashrc")
            if system == "Darwin" and not os.path.exists(config_file):
                config_file = os.path.join(home, ".bash_profile")
        if not config_file or not os.path.exists(config_file):
            print(colorize_command("Could not determine shell config file."))
            return False
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        start_marker = '# >>> TERMINALAI SHELL INTEGRATION START'
        end_marker = '# <<< TERMINALAI SHELL INTEGRATION END'
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if start_idx != -1 and end_idx != -1:
            end_idx += len(end_marker)
            # Remove any extra newlines before/after
            before = content[:start_idx].rstrip('\n')
            after = content[end_idx:].lstrip('\n')
            new_content = before + '\n' + after
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(colorize_command(
                f"TerminalAI shell integration removed from {config_file}.\n"
                f"Please restart your shell or run 'source {config_file}'."
            ))
            return True
        print(colorize_command("TerminalAI shell integration not found in config file."))
        return False
    if system == "Windows":
        print(colorize_command("PowerShell shell integration uninstall is not yet implemented for seamless eval mode."))
        return False
    print(colorize_command(f"Unsupported system: {system}"))
    return False