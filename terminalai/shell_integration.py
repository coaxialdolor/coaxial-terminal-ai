"""Shell integration utilities for TerminalAI."""
import os
import platform
from terminalai.color_utils import colorize_command
from terminalai.clipboard_utils import copy_to_clipboard
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

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

def get_shell_config_file():
    system = platform.system()
    home = os.path.expanduser("~")
    shell = os.environ.get("SHELL", "")
    config_file = ""
    if "zsh" in shell:
        config_file = os.path.join(home, ".zshrc")
    elif "bash" in shell:
        config_file = os.path.join(home, ".bashrc")
        if system == "Darwin" and not os.path.exists(config_file):
            config_file = os.path.join(home, ".bash_profile")
    return config_file

def check_shell_integration():
    """Check if the ai shell integration is installed and highlight it in the config file."""
    console = Console()
    config_file = get_shell_config_file()
    if not config_file or not os.path.exists(config_file):
        console.print("[red]Could not determine shell config file.[/red]")
        return False
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    start_marker = '# >>> TERMINALAI SHELL INTEGRATION START'
    end_marker = '# <<< TERMINALAI SHELL INTEGRATION END'
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)
    if start_idx != -1 and end_idx != -1:
        end_idx += len(end_marker)
        before = content[:start_idx]
        block = content[start_idx:end_idx]
        after = content[end_idx:]
        # Print with highlighting
        console.print("[bold]Shell config file:[/bold] " + config_file)
        if before:
            console.print(Text(before, style="white"))
        console.print(Panel(Text(block, style="black on yellow"), title="[green]TerminalAI Shell Integration Block[/green]", border_style="yellow"))
        if after:
            console.print(Text(after, style="white"))
        console.print("\n[bold green]The shell integration is installed.[/bold green]")
        return True
    else:
        console.print("[bold]Shell config file:[/bold] " + config_file)
        console.print(Text(content, style="white"))
        console.print("\n[bold red]The shell integration is not installed.[/bold red]")
        return False

def install_shell_integration():
    """Install shell integration for seamless stateful command execution via 'ai' shell function."""
    import shutil
    system = platform.system()
    if system in ("Darwin", "Linux"):
        config_file = get_shell_config_file()
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
# Prompts and errors from the Python script are sent to stderr and are visible in the terminal.
ai() {{
    export TERMINALAI_SHELL_INTEGRATION=1
    # Bypass eval for interactive/chat/setup/help/version modes
    if [ $# -eq 0 ] || \
       [ "$1" = "setup" ] || \
       [ "$1" = "--chat" ] || \
       [ "$1" = "-c" ] || \
       [ "$1" = "--help" ] || \
       [ "$1" = "-h" ] || \
       [ "$1" = "--version" ] || \
       [ "$(basename "$0")" = "ai-c" ]; then
        command ai "$@"
    else
        # Use eval mode for direct queries to handle potential stateful commands
        local output
        # Run with --eval-mode and capture stdout
        output=$(command ai --eval-mode "$@")
        local ai_status=$?
        # If the command succeeded and produced output, evaluate it
        if [ $ai_status -eq 0 ] && [ -n "$output" ]; then
            eval "$output"
        fi
        # Return the original status code of the 'ai' command itself
        return $ai_status
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
        # Copy the appropriate source command to clipboard
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            source_cmd = f"source ~/.zshrc"
        elif "bash" in shell:
            if system == "Darwin" and os.path.exists(os.path.expanduser("~/.bash_profile")):
                source_cmd = f"source ~/.bash_profile"
            else:
                source_cmd = f"source ~/.bashrc"
        else:
            source_cmd = f"source {config_file}"
        copy_to_clipboard(source_cmd)
        print(colorize_command(
            f"TerminalAI shell integration installed in {config_file} as 'ai' shell function.\n"
            f"[Copied '{source_cmd}' to clipboard]\n"
            f"Please restart your shell or run '{source_cmd}'."
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