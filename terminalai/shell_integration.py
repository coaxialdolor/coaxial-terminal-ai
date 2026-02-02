"""Shell integration utilities for TerminalAI."""
import os
import platform
import subprocess
from terminalai.color_utils import colorize_command
from terminalai.clipboard_utils import copy_to_clipboard
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
import getpass

def get_system_context():
    """Get system context information for the AI."""
    # Get platform-specific info
    system_name = platform.system()
    system_release = platform.release()
    system_version = platform.version()
    system_machine = platform.machine()

    # Get user info
    username = getpass.getuser()

    # Get home directory and common paths
    home_dir = os.path.expanduser("~")
    desktop_dir = os.path.join(home_dir, "Desktop")
    documents_dir = os.path.join(home_dir, "Documents")
    downloads_dir = os.path.join(home_dir, "Downloads")

    # Get current working directory
    cwd = os.getcwd()

    # Construct path reference guide based on OS
    if system_name == "Windows":
        path_guide = (
            f"- When the user refers to 'my desktop', use the absolute path: {desktop_dir}\n"
            f"- When the user refers to 'my documents', use the absolute path: {documents_dir}\n"
            f"- When the user refers to 'my downloads', use the absolute path: {downloads_dir}\n"
            f"- When the user refers to 'my home directory', use the absolute path: {home_dir}\n"
            f"- When a location is not specified, assume they mean their current directory: {cwd}"
        )
    else:
        path_guide = (
            f"- When the user refers to 'my desktop', use the absolute path: {desktop_dir}\n"
            f"- When the user refers to 'my documents', use the absolute path: {documents_dir}\n"
            f"- When the user refers to 'my downloads', use the absolute path: {downloads_dir}\n"
            f"- When the user refers to 'my home directory', use the absolute path: {home_dir}\n"
            f"- When a location is not specified, assume they mean their current directory: {cwd}"
        )

    # Add additional system-specific guidance
    if system_name == "Windows":
        additional_guidance = (
            "- Use Windows-compatible commands (e.g., 'dir' instead of 'ls' for cmd.exe)\n"
            "- For paths, use backslashes (\\) or forward slashes (/) which both work in most modern Windows contexts\n"
            "- Use environment variables like %USERPROFILE% for user paths when appropriate\n"
            "- NEVER use 'cd' followed by another command - each command runs in a new shell\n"
            "- ALWAYS use absolute paths in commands (e.g., 'dir \"C:\\Users\\username\\Desktop\\*.log\"')\n"
            "- For file operations, use the full path in the command itself\n"
            "- Commands must be self-contained and work from any directory"
        )
    else:
        additional_guidance = (
            "- Use Unix/Linux compatible commands\n"
            "- For paths, use forward slashes (/)\n"
            "- Use ~ to represent the user's home directory when appropriate\n"
            "- Use 'cd' followed by commands only when they can be combined with && or ;"
        )

    context = (
        f"System Information:\n"
        f"- OS: {system_name} {system_release} {system_version}\n"
        f"- Architecture: {system_machine}\n"
        f"- Username: {username}\n"
        f"- Current Working Directory: {cwd}\n\n"
        f"Path References:\n{path_guide}\n\n"
        f"Command Guidelines:\n{additional_guidance}"
    )

    return context

def get_shell_config_file():
    system = platform.system()
    home = os.path.expanduser("~")
    shell = os.environ.get("SHELL", "")
    config_file = ""

    if system == "Windows":
        try:
            # For PowerShell, $PROFILE gives the path to the current user, current host profile
            # We try to get the AllUsersAllHosts profile first, then CurrentUserCurrentHost
            # For simplicity in this first pass, we'll just get $PROFILE which is CurrentUserCurrentHost
            # Note: PowerShell might not be the default shell, or $PROFILE might not exist.
            # We want the script that runs for the current user in the current host.
            # A common path is $HOME\\Documents\\WindowsPowerShell\\Microsoft.PowerShell_profile.ps1
            # or $HOME\\Documents\\PowerShell\\Microsoft.PowerShell_profile.ps1 for PS Core

            # Attempt to get the profile path directly from PowerShell
            # This is more reliable than guessing paths.
            process = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "$PROFILE.CurrentUserCurrentHost"],
                capture_output=True, text=True, check=True, shell=False # shell=False for security
            )
            profile_path = process.stdout.strip()
            if profile_path and os.path.isabs(profile_path): # Check if it's a non-empty absolute path
                # Ensure the directory exists, as $PROFILE might point to a non-existent file
                profile_dir = os.path.dirname(profile_path)
                if not os.path.exists(profile_dir):
                    try:
                        os.makedirs(profile_dir, exist_ok=True)
                        # If we created the directory, the file itself doesn't exist yet.
                        # We'll return the path, and installer can create it.
                    except OSError:
                         # Failed to create directory, fall back or indicate no profile
                        profile_path = "" # Reset if we can't ensure directory
                config_file = profile_path

            # Fallback or if $PROFILE is not what we expect (e.g., if user uses cmd.exe primarily)
            # For now, if the powershell command fails or returns unusable path, we'll have an empty config_file
            # The calling functions (check_shell_integration, install_shell_integration)
            # already handle cases where config_file is empty or doesn't exist.

        except (subprocess.CalledProcessError, FileNotFoundError):
            # FileNotFoundError if 'powershell' is not in PATH
            # CalledProcessError if the command fails
            # In these cases, we can't determine the PowerShell profile automatically.
            config_file = "" # Ensure it's empty

    elif "zsh" in shell:
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
    system = platform.system()

    if not config_file: # This means get_shell_config_file returned empty
        console.print("[red]Could not determine shell config file path.[/red]")
        if system == "Windows":
            console.print("[yellow]This can happen if PowerShell is not found or $PROFILE is not accessible.[/yellow]")
        return False

    if not os.path.exists(config_file):
        if system == "Windows":
            console.print(f"[yellow]PowerShell profile file '{config_file}' does not exist.[/yellow]")
            console.print("[bold red]The shell integration is not installed.[/bold red]")
        else:
            # For non-Windows, we generally expect .bashrc/.zshrc to exist if determined.
            console.print(f"[red]Shell configuration file '{config_file}' does not exist.[/red]")
        return False

    # If we reach here, config_file is valid and os.path.exists(config_file) is True
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
    system = platform.system()
    if system in ("Darwin", "Linux"):
        config_file = get_shell_config_file()
        if not config_file or not os.path.exists(config_file):
            # If the config file doesn't exist but we have a path (e.g. from $PROFILE for PS)
            # we might want to create it. For now, let's assume it should exist for Linux/Mac.
            if system == "Windows" and config_file: # Special handling for Windows if $PROFILE gave a path
                try:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write("# PowerShell profile created by TerminalAI\n")
                    # Proceed with installation
                except IOError:
                    print(colorize_command(
                        f"Could not create PowerShell profile at {config_file}. Please create it manually."
                    ))
                    return False
            else:
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
        shell_function = (
"""
# >>> TERMINALAI SHELL INTEGRATION START
# Added by TerminalAI (https://github.com/coaxialdolor/terminalai)
# This shell function enables seamless stateful command execution via eval $(ai ...)
# Prompts and errors from the Python script are sent to stderr and are visible in the terminal.
ai() {
    export TERMINALAI_SHELL_INTEGRATION=1
    # Bypass eval for interactive/chat/setup/help/version/config modes
    if [ $# -eq 0 ] || \
       [ "$1" = "setup" ] || \
       [ "$1" = "--setup" ] || \
       [ "$1" = "--set-default" ] || \
       [ "$1" = "--set-ollama" ] || \
       [ "$1" = "--chat" ] || \
       [ "$1" = "-c" ] || \
       [ "$1" = "--help" ] || \
       [ "$1" = "-h" ] || \
       [ "$1" = "--version" ] || \
       [ "$1" = "--read-file" ] || \
       [ "$1" = "--explain" ] || \
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
}
# <<< TERMINALAI SHELL INTEGRATION END
"""
        )
        # Ensure block is separated by newlines
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + shell_function + "\n"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        # Copy the appropriate source command to clipboard
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            source_cmd = "source ~/.zshrc"
        elif "bash" in shell:
            if system == "Darwin" and os.path.exists(os.path.expanduser("~/.bash_profile")):
                source_cmd = "source ~/.bash_profile"
            else:
                source_cmd = "source ~/.bashrc"
        else:
            source_cmd = f"source {config_file}"
        copy_to_clipboard(source_cmd)
        print(colorize_command(
            f"TerminalAI shell integration installed in {config_file} as 'ai' shell function.\n"
            f"[Copied '{source_cmd}' to clipboard]\n"
            f"Please restart your shell or run '{source_cmd}'."
        ))
        return True
    # PowerShell specific integration
    elif system == "Windows":
        config_file = get_shell_config_file()
        if not config_file: # This implies get_shell_config_file failed to get a PS profile path
            print(colorize_command(
                "Could not determine PowerShell profile path. Ensure PowerShell is installed and $PROFILE is accessible."
            ))
            return False

        # Ensure profile exists, create if not (get_shell_config_file might have created the dir)
        if not os.path.exists(config_file):
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write("# PowerShell profile created by TerminalAI\n")
            except IOError as e:
                print(colorize_command(f"Error creating PowerShell profile {config_file}: {e}"))
                return False

        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        start_marker = '# >>> TERMINALAI SHELL INTEGRATION START'
        end_marker = '# <<< TERMINALAI SHELL INTEGRATION END'
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)

        if start_idx != -1 and end_idx != -1:
            # If block exists, remove it before adding the new one to ensure update
            end_idx_inclusive = end_idx + len(end_marker)
            # Preserve content before and after the block, handling potential newlines
            before_block = content[:start_idx].rstrip('\r\n')
            after_block = content[end_idx_inclusive:].lstrip('\r\n')
            if before_block and after_block:
                content = before_block + "\r\n\r\n" + after_block # Ensure separation
            elif before_block:
                content = before_block + "\r\n"
            elif after_block:
                content = "\r\n" + after_block
            else:
                content = "" # File becomes empty if only block was present

        # Check for other ai aliases/functions (basic check)
        # PowerShell function definition is `Function ai { ... }`
        # Alias is `Set-Alias -Name ai -Value ...`
        if 'Function ai' in content or 'Set-Alias -Name ai' in content or 'function global:ai' in content:
            # A more robust check would involve parsing, but this is a heuristic
            # We need to be careful not to detect our own block if it was just partially removed or in a comment
            # For now, if the markers aren't present but these are, we warn.
            # If the markers *were* present, we've already stripped our block.
            if not (start_idx != -1 and end_idx != -1): # Only warn if we didn't just remove our own block
                print(colorize_command(
                    "Warning: An 'ai' function or alias might already exist in your PowerShell profile. "
                    "Please check your profile and resolve any conflicts before installing."
                ))
                return False

        powershell_function = (
'''\r\n\r\n# >>> TERMINALAI SHELL INTEGRATION START\r\n# Added by TerminalAI (https://github.com/coaxialdolor/terminalai)\r\n# This shell function enables seamless stateful command execution.\r\n# Prompts and errors from the Python script are sent to stderr and are visible in the terminal.\r\nfunction global:ai {
    # Set environment variable for TerminalAI to detect shell integration
    $env:TERMINALAI_SHELL_INTEGRATION = "1"

    # Determine if this is a direct query or interactive/setup/help mode
    $isDirectQuery = $true
    if ($args.Count -eq 0) {
        $isDirectQuery = $false
    } else {
        $firstArg = $args[0].ToLower()
        if (($firstArg -eq "setup") -or \r
            ($firstArg -eq "--chat") -or ($firstArg -eq "-c") -or \r
            ($firstArg -eq "--help") -or ($firstArg -eq "-h") -or \r
            ($firstArg -eq "--version") -or \r
            ($firstArg -eq "--set-default") -or \r
            ($firstArg -eq "--set-ollama")) {
            $isDirectQuery = $false
        }
    }

    if (-not $isDirectQuery) {
        # For non-direct queries, just call 'ai' normally
        # Ensure 'ai' is called from PATH. Get the full command path, specifically an Application.
        try {
            $aiCommandPath = (Get-Command -Name ai -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
        } catch {
            Write-Error "Could not resolve path for the 'ai' executable. Please ensure it is in your PATH."
            return
        }
        if ($aiCommandPath) {
            & $aiCommandPath @args
        } # Error already handled by catch
    } else {
        # For direct queries, use eval mode to handle stateful commands
        # Construct the command to run: ai --eval-mode @args
        try {
            $aiCommandPath = (Get-Command -Name ai -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
        } catch {
            Write-Error "Could not resolve path for the 'ai' executable (for eval-mode). Please ensure it is in your PATH."
            return
        }

        if (-not $aiCommandPath) {
            # This block should ideally not be reached if ErrorAction Stop is used and caught above.
            Write-Error "Could not resolve path for 'ai' command during eval-mode preparation."
            return
        }

        $evalArgs = @("--eval-mode") + @($args)

        # Run 'ai --eval-mode ...' and capture only stdout (command to eval).
        # Use native PowerShell invocation to preserve argument quoting and avoid pipe deadlocks.
        $outputToEval = & $aiCommandPath @evalArgs
        $aiExitCode = $LASTEXITCODE

        if ($aiExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($outputToEval)) {
            try {
                Invoke-Expression $outputToEval.Trim()
            } catch {
                Write-Error "Error evaluating command: $($_.Exception.Message)"
                Write-Error "Command from AI: $outputToEval"
            }
        }

        if ($aiExitCode -ne 0) {
            # Errors from 'ai --eval-mode' should have already printed to stderr.
            # PowerShell functions don't automatically set $LASTEXITCODE from external commands in the same way bash functions do.
            # The Invoke-Expression above *might* set $LASTEXITCODE if it runs an external command.
            # If 'ai --eval-mode' itself fails, $aiExitCode will be non-zero.
            # We can manually try to set $LASTEXITCODE using a trick if needed,
            # but it's often complex. For now, ensuring error messages are visible is key.
            # cmd /c exit $aiExitCode # This is a cmd.exe trick, might not be ideal here.
        }
    }
    # Optional: Remove-Item Env:TERMINALAI_SHELL_INTEGRATION
}
# <<< TERMINALAI SHELL INTEGRATION END
'''
        )

        # Ensure block is separated by newlines (use PowerShell/Windows newlines \r\n)
        new_content = content.rstrip('\r\n') # Clean trailing newlines from existing content
        if new_content: # If content was not empty or just newlines
            new_content += "\r\n\r\n" # Add two newlines before our block

        new_content += powershell_function

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except IOError as e:
            print(colorize_command(f"Error writing to PowerShell profile {config_file}: {e}"))
            return False

        source_cmd = ". $PROFILE" # General command to reload PowerShell profile
        # Try to get the specific profile path for the message, fallback to $PROFILE
        profile_to_source = config_file if os.path.exists(config_file) else "$PROFILE"

        copy_to_clipboard(source_cmd)
        print(colorize_command(
            f"TerminalAI shell integration installed in {profile_to_source} as 'ai' PowerShell function.\n"
            f"[Copied '{source_cmd}' to clipboard]\n"
            f"Please restart your PowerShell session or run '{source_cmd}' in your current session."
        ))
        return True

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
    elif system == "Windows": # PowerShell
        config_file = get_shell_config_file()
        if not config_file:
            print(colorize_command("Could not determine PowerShell profile path."))
            return False
        if not os.path.exists(config_file):
            print(colorize_command(f"PowerShell profile {config_file} not found. Nothing to uninstall."))
            return False

        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        start_marker = '# >>> TERMINALAI SHELL INTEGRATION START'
        end_marker = '# <<< TERMINALAI SHELL INTEGRATION END'
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)

        if start_idx != -1 and end_idx != -1:
            end_idx_inclusive = end_idx + len(end_marker)

            # Preserve content before and after the block
            before_block = content[:start_idx]
            after_block = content[end_idx_inclusive:]

            # Smartly remove block and surrounding newlines
            # Remove trailing newlines from before_block
            # Remove leading newlines from after_block
            new_content = before_block.rstrip('\r\n')
            if new_content and after_block.lstrip('\r\n'): # Both have content after stripping
                new_content += "\r\n\r\n" # Ensure at least one blank line between them if both exist

            new_content += after_block.lstrip('\r\n')

            # If the file becomes empty or just whitespace, make it truly empty.
            if not new_content.strip():
                new_content = ""
            else:
                 # Ensure a trailing newline if there's content
                 new_content = new_content.rstrip('\r\n') + '\r\n'

            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                source_cmd = ". $PROFILE" # General command to reload PowerShell profile
                profile_to_source = config_file if os.path.exists(config_file) else "$PROFILE"
                print(colorize_command(
                    f"TerminalAI shell integration removed from {profile_to_source}.\n"
                    f"Please restart your PowerShell session or run '{source_cmd}' to apply changes."
                ))
                return True
            except IOError as e:
                print(colorize_command(f"Error writing to PowerShell profile {config_file}: {e}"))
                return False
        else:
            print(colorize_command("TerminalAI shell integration not found in PowerShell profile."))
            return False

    print(colorize_command(f"Unsupported system: {system}"))
    return False