"""CLI interaction functionality for TerminalAI."""
import os
import sys
import argparse
import time # Import time module for sleep
from terminalai.command_utils import run_shell_command, is_shell_command
from terminalai.command_extraction import is_stateful_command, is_risky_command
from terminalai.clipboard_utils import copy_to_clipboard

# Imports for rich components - from HEAD, as 021offshoot was missing some
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

# Imports for terminalai components - from HEAD, as 021offshoot was missing some
from terminalai.config import (
    load_config, save_config,
    get_system_prompt, DEFAULT_SYSTEM_PROMPT
)
from terminalai.shell_integration import (
    install_shell_integration, uninstall_shell_integration,
    check_shell_integration, get_system_context
)
from terminalai.ai_providers import get_provider
from terminalai.formatting import print_ai_answer_with_rich
# Use the more specific get_commands_interactive (alias for extract_commands) from 021offshoot
from terminalai.command_extraction import extract_commands as get_commands_interactive
from terminalai.__init__ import __version__
from terminalai.color_utils import (
    colorize_success, colorize_error, colorize_info,
    colorize_prompt, colorize_highlight, AI_COLOR, COMMAND_COLOR, INFO_COLOR,
    ERROR_COLOR, SUCCESS_COLOR, PROMPT_COLOR, HIGHLIGHT_COLOR, RESET, BOLD
)
import requests # Add this import for Ollama model fetching
import json # Add this import for parsing Ollama response

# System Prompt for AI Risk Assessment (Hardcoded)
_RISK_ASSESSMENT_SYSTEM_PROMPT = """
You are a security analysis assistant. Your sole task is to explain the potential negative consequences and risks of executing the given shell command(s) within the specified user context.

Instructions:
- When the user query starts with the exact prefix "<RISK_CONFIRMATION>", strictly follow these rules.
- Focus exclusively on the potential dangers: data loss, system instability, security vulnerabilities, unintended modifications, or permission changes.
- DO NOT provide instructions on how to use the command, suggest alternatives, or offer reassurances. ONLY state the risks.
- Be specific about the impact. Refer to the *full, absolute paths* of any files or directories that would be affected, based on the provided Current Working Directory (CWD) and the command itself.
- If a command affects the CWD (e.g., `rm -r .`), state clearly what the full path of the CWD is and that its contents will be affected.
- If the risks are minimal or negligible for a typically safe command, state that concisely (e.g., "Minimal risk: This command lists directory contents.").
- Keep the explanation concise and clear. Use bullet points if there are multiple distinct risks.
- Output *only* the risk explanation, with no conversational introduction or closing.
"""

def parse_args():
    """Parse command line arguments, ignoring --eval-mode and unknown arguments for shell integration compatibility."""
    # Remove --eval-mode if present, to avoid argparse errors from shell integration
    filtered_argv = [arg for arg in sys.argv[1:] if arg != "--eval-mode"]
    description_text = """TerminalAI: Your command-line AI assistant.
Ask questions or request commands in natural language.

-----------------------------------------------------------------------
MODES OF OPERATION & EXAMPLES:
-----------------------------------------------------------------------
1. Direct Query: Ask a question directly, get a response, then exit.
   Syntax: ai [flags] "query"
   Examples:
     ai "list files ending in .py"
     ai -v "explain the concept of inodes"
     ai -y "show current disk usage"
     ai -y -v "create a new directory called 'test_project' and enter it"

2. Single Interaction: Enter a prompt, get one response, then exit.
   Syntax: ai [flags]
   Examples:
     ai
       AI:(provider)> your question here
     ai -l
       AI:(provider)> explain git rebase in detail

3. Persistent Chat: Keep conversation history until 'exit'/'q'.
   Syntax: ai --chat [flags]  OR  ai -c [flags]
   Examples:
     ai --chat
     ai -c -v  (start chat in verbose mode)

-----------------------------------------------------------------------
COMMAND HANDLING:
-----------------------------------------------------------------------
- Confirmation:  Commands require [Y/n] confirmation before execution.
                 Risky commands (rm, sudo) require explicit 'y'.
- Stateful cmds: Commands like 'cd' or 'export' that change shell state
                 will prompt to copy to clipboard [Y/n].
- Integration:   If Shell Integration is installed (via 'ai setup'):
                   Stateful commands *only* in Direct Query mode (ai "...")
                   will execute directly in the shell after confirmation.
                   Interactive modes (ai, ai --chat) still use copy.

-----------------------------------------------------------------------
AVAILABLE FLAGS:
-----------------------------------------------------------------------
  [query]           Your question or request (used in Direct Query mode).
  -h, --help        Show this help message and exit.
  -y, --yes         Auto-confirm execution of non-risky commands.
                     Effective in Direct Query mode or with Shell Integration.
                     Example: ai -y "show disk usage"
  -v, --verbose     Request a more detailed response from the AI.
                     Example: ai -v "explain RAID levels"
                     Example (chat): ai -c -v
  -l, --long        Request a longer, more comprehensive response from AI.
                     Example: ai -l "explain git rebase workflow"
  --setup           Run the interactive setup wizard.
  --version         Show program's version number and exit.
  --set-default     Shortcut to set the default AI provider.
  --set-ollama      Shortcut to configure the Ollama model.
  --provider        Override the default AI provider for this query only.
  --read-file <filepath>
                    Read the specified file (any plain text file) and use its content in the prompt.
                    The AI will be asked to explain/summarize this file based on your query.
                    Example: ai --read-file script.py "explain this script"
  --explain <filepath>
                    Read and automatically explain/summarize the specified file (any plain text file) in its project context.
                    Uses a predefined query and ignores any general query you provide.
                    Mutually exclusive with --read-file.

-----------------------------------------------------------------------
AI FORMATTING EXPECTATIONS:
-----------------------------------------------------------------------
- Provide commands in separate ```bash code blocks.
- Keep explanations outside code blocks."""
    epilog_text = """For full configuration, run 'ai setup'.
Project: https://github.com/coaxialdolor/terminalai"""
    parser = argparse.ArgumentParser(
        description=description_text,
        epilog=epilog_text,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "query",
        nargs="?",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "-l", "--long",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "--chat",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "--set-default",
        action="store_true",
        help="Shortcut to set the default AI provider."
    )

    parser.add_argument(
        "--set-ollama",
        action="store_true",
        help="Shortcut to configure the Ollama model."
    )

    parser.add_argument(
        "--provider",
        choices=["ollama", "openrouter", "gemini", "mistral"],
        help="Override the default AI provider for this query only."
    )

    parser.add_argument(
        "--read-file",
        type=str,
        metavar="<filepath>",
        help="Read the specified file and use its content in the prompt. Your query will then be about this file."
    )

    parser.add_argument(
        "--explain",
        type=str,
        metavar="<filepath>",
        help="Read and automatically explain/summarize the specified file in its project context. Ignores general query."
    )

    parser.add_argument(
        "--eval-mode",
        action="store_true",
        help=argparse.SUPPRESS
    )

    # Ensure --read-file and --explain are mutually exclusive
    args, unknown = parser.parse_known_args(filtered_argv)
    if args.read_file and args.explain:
        parser.error("argument --explain: not allowed with argument --read-file")

    # Check if --eval-mode was in original args but removed for parsing
    if "--eval-mode" in sys.argv:
        args.eval_mode = True

    return args

# --- Helper Function for AI Risk Assessment ---

def _get_ai_risk_assessment(command, console, provider):
    """Gets a risk assessment for a command using a secondary AI call."""
    if not provider:
        return "Risk assessment requires a configured AI provider."

    try:
        cwd = os.getcwd()
        risk_query = f"<RISK_CONFIRMATION> Explain the potential consequences and dangers of running the following command(s) if my current working directory is '{cwd}':\n---\n{command}\n---"

        # Increased delay for API rate limits
        time.sleep(1.5)

        risk_response = provider.generate_response(
            risk_query,
            system_context=None,
            verbose=False,
            override_system_prompt=_RISK_ASSESSMENT_SYSTEM_PROMPT
        )
        risk_explanation = risk_response.strip()
        if not risk_explanation:
             return "AI returned empty risk assessment."
        return risk_explanation
    except Exception as e:
        return f"Risk assessment failed. Error: {e}"

# --- Main Command Handling Logic ---

def handle_commands(commands, auto_confirm=False):
    """Handle extracted commands, prompting the user and executing if confirmed.

    Args:
        commands: List of commands to handle
        auto_confirm: If True, auto-confirm non-risky commands without prompting
    """
    console = Console()

    provider_instance = None
    if commands:
        try:
            config = load_config()
            default_provider_name = config.get("default_provider")
            if default_provider_name:
                provider_instance = get_provider(default_provider_name)
        except Exception as e:
            console.print(Text(f"[WARNING] Could not load AI provider for risk assessment: {e}", style="yellow"))
            # provider_instance remains None

    if not commands:
        return

    n_commands = len(commands)

    color_reset = "\033[0m"
    color_bold_green = "\033[1;32m"
    color_bold_yellow = "\033[1;33m"

    if n_commands == 1:
        command = commands[0]
        is_stateful_cmd = is_stateful_command(command)
        is_risky_cmd = is_risky_command(command)

        if is_risky_cmd:
            risk_explanation = _get_ai_risk_assessment(command, console, provider_instance)
            console.print(Panel(
                Text(risk_explanation, style="yellow"),
                title="[bold red]AI Risk Assessment[/bold red]",
                border_style="red",
                expand=False
            ))

        # Always handle stateful commands the same way, regardless of auto_confirm
        if is_stateful_cmd:
            prompt_text = (
                f"[STATEFUL COMMAND] '{command}' changes shell state. "
                "Copy to clipboard? [Y/n]: "
            )
            console.print(Text(prompt_text, style="yellow bold"), end="")
            choice = input().lower() or "y" # Default to yes (copy)
            if choice == 'y':
                copy_to_clipboard(command)
                console.print("[green]Command copied to clipboard. Paste and run manually.[/green]")
            return # Done with this single stateful command

        # Auto-confirm for non-stateful, non-risky commands
        if auto_confirm and not is_risky_cmd:
            console.print(Text("\n[Auto-executing command]", style="bold blue"))
            console.print(Panel(Text(command, style="cyan bold"),
                               border_style="blue",
                               expand=False))
            run_command(command, auto_confirm=True)
            return

        # Risky commands always require confirmation
        if is_risky_cmd:
            prompt_style = "red bold"
            prompt_msg_text = Text("[RISKY] Execute '", style=prompt_style)
            prompt_msg_text.append(command, style=prompt_style + " underline")
            prompt_msg_text.append("'? [y/N]: ", style=prompt_style)
            console.print(prompt_msg_text, end="")
            choice = input().lower() or "n"  # Default to no for risky
            if choice == "y":
                run_command(command, auto_confirm=auto_confirm)
            else:
                console.print("[Cancelled]")
            return

        # Regular non-risky, non-stateful command without auto_confirm
        prompt_style = "green"
        prompt_msg_text = Text("Execute '", style=prompt_style)
        prompt_msg_text.append(command, style=prompt_style + " underline")
        prompt_msg_text.append("'? [Y/n]: ", style=prompt_style)
        console.print(prompt_msg_text, end="")
        choice = input().lower() or "y"  # Default to yes

        if choice == "y":
            run_command(command, auto_confirm=auto_confirm)
        else:
            console.print("[Cancelled]")
        return

    # Multiple commands
    else:
        # Auto-confirm case for multiple commands
        if auto_confirm:
            for cmd_item in commands:
                is_stateful_item = is_stateful_command(cmd_item)
                is_risky_item = is_risky_command(cmd_item)

                if is_stateful_item:
                    copy_to_clipboard(cmd_item)
                    console.print(f"[green]Command copied to clipboard: {cmd_item}[/green]")
                elif not is_risky_item:
                    console.print(f"[green]Auto-executing: {cmd_item}[/green]")
                    run_command(cmd_item, auto_confirm=True)
                else:
                    # For risky commands, show assessment and ask for confirmation
                    risk_explanation = _get_ai_risk_assessment(cmd_item, console, provider_instance)
                    console.print(Panel(
                        Text(risk_explanation, style="yellow"),
                        title="[bold red]AI Risk Assessment[/bold red]",
                        border_style="red",
                        expand=False
                    ))
                    prompt_style = "red bold"
                    prompt_msg_text = Text("[RISKY] Execute '", style=prompt_style)
                    prompt_msg_text.append(cmd_item, style=prompt_style + " underline")
                    prompt_msg_text.append("'? [y/N]: ", style=prompt_style)
                    console.print(prompt_msg_text, end="")
                    choice = input().lower() or "n"  # Default to no for risky commands
                    if choice == "y":
                        run_command(cmd_item, auto_confirm=auto_confirm)
                    else:
                        console.print(f"[Skipped: {cmd_item}]")
            return

        # Display command list and prompt for selection (not auto_confirm)
        cmd_list_display = []
        for i, cmd_text_item in enumerate(commands, 1):
            is_risky_item = is_risky_command(cmd_text_item)
            is_stateful_item = is_stateful_command(cmd_text_item)

            display_item = Text()
            display_item.append(f"{i}", style="cyan")
            display_item.append(f": {cmd_text_item}", style="white")
            if is_risky_item:
                display_item.append(" [RISKY]", style="bold red")
            if is_stateful_item:
                display_item.append(" [STATEFUL]", style="bold yellow")
            cmd_list_display.append(display_item)

        # Create a single Text object for the panel content
        panel_content = Text("\n").join(cmd_list_display)
        console.print(Panel(
            panel_content,
            title=f"Found {n_commands} commands",
            border_style="blue"
        ))

        prompt_message = Text("Enter command number, 'a' for all, or 'q' to quit: ", style="bold cyan")
        console.print(prompt_message, end="")
        user_choice = input().lower()

        if user_choice == "q":
            return

        elif user_choice == "a":
            console.print(Text("Executing all non-stateful/non-risky (unless auto-confirmed) commands:", style="magenta"))
            for i, cmd_item in enumerate(commands):
                console.print(f"Processing command {i+1}: {cmd_item}")
                is_stateful_item = is_stateful_command(cmd_item)
                is_risky_item = is_risky_command(cmd_item)

                if is_risky_item:
                    risk_explanation = _get_ai_risk_assessment(cmd_item, console, provider_instance)
                    console.print(Panel(
                        Text(risk_explanation, style="yellow"),
                        title="[bold red]AI Risk Assessment[/bold red]",
                        border_style="red",
                        expand=False
                    ))

                if is_stateful_item:
                    copy_prompt_text = Text(f"[STATEFUL COMMAND] '{cmd_item}'. Copy to clipboard? [Y/n]: ", style="yellow bold")
                    console.print(copy_prompt_text, end="")
                    sub_choice = input().lower() or "y"
                    if sub_choice == 'y':
                        copy_to_clipboard(cmd_item)
                        console.print("[green]Command copied to clipboard.[/green]")
                    continue # Move to next command in 'a'

                # Non-stateful command in 'a'
                if auto_confirm and not is_risky_item:
                    console.print(f"[green]Auto-executing: {cmd_item}[/green]")
                    run_command(cmd_item, auto_confirm=True)
                elif is_risky_item: # Needs explicit confirmation even in 'a' if not auto_confirm
                    exec_prompt_text = Text(f"[RISKY] Execute '{cmd_item}'? [y/N]: ", style="red bold")
                    console.print(exec_prompt_text, end="")
                    sub_choice = input().lower() or "n"
                    if sub_choice == "y":
                        run_command(cmd_item, auto_confirm=auto_confirm)
                    else:
                        console.print(f"[Skipped: {cmd_item}]")
                else: # Not risky, not stateful, not auto_confirm - prompt for this specific one in 'a'
                    exec_prompt_text = Text(f"Execute '{cmd_item}'? [Y/n]: ", style="green")
                    console.print(exec_prompt_text, end="")
                    sub_choice = input().lower() or "y"
                    if sub_choice == "y":
                        run_command(cmd_item, auto_confirm=auto_confirm)
                    else:
                        console.print(f"[Skipped: {cmd_item}]")
            return

        elif user_choice.isdigit():
            idx = int(user_choice) - 1
            if 0 <= idx < len(commands):
                cmd_to_run = commands[idx]
                is_stateful_cmd_num = is_stateful_command(cmd_to_run)
                is_risky_cmd_num = is_risky_command(cmd_to_run)

                if is_risky_cmd_num:
                    risk_explanation_num = _get_ai_risk_assessment(cmd_to_run, console, provider_instance)
                    console.print(Panel(
                        Text(risk_explanation_num, style="yellow"),
                        title="[bold red]AI Risk Assessment[/bold red]",
                        border_style="red",
                        expand=False
                    ))

                if is_stateful_cmd_num:
                    copy_prompt_text_num = Text(f"[STATEFUL COMMAND] '{cmd_to_run}'. Copy to clipboard? [Y/n]: ", style="yellow bold")
                    console.print(copy_prompt_text_num, end="")
                    sub_choice_num = input().lower() or "y"
                    if sub_choice_num == 'y':
                        copy_to_clipboard(cmd_to_run)
                        console.print("[green]Command copied to clipboard.[/green]")
                elif is_risky_cmd_num: # Not stateful, but risky
                    exec_prompt_text_num = Text(f"[RISKY] Execute '{cmd_to_run}'? [y/N]: ", style="red bold")
                    console.print(exec_prompt_text_num, end="")
                    sub_choice_num = input().lower() or "n"
                    if sub_choice_num == "y":
                        run_command(cmd_to_run, auto_confirm=auto_confirm)
                    else:
                        console.print("[Cancelled]")
                else: # Not stateful, not risky - chosen by number, execute directly.
                    console.print(f"[green]Executing selected command: {cmd_to_run}[/green]")
                    run_command(cmd_to_run, auto_confirm=auto_confirm)
            else:
                console.print(f"[red]Invalid choice: {user_choice}[/red]")
            return
        else: # Invalid choice from multi-command prompt
            console.print(f"[red]Invalid selection: {user_choice}[/red]")
            return

    # Should be unreachable if all paths above return
    return

def run_command(command, auto_confirm=False):
    """Execute a shell command with error handling.

    Args:
        command: The command to execute
        auto_confirm: If True, execute without confirmation prompt
    """
    console = Console()

    if not command:
        return

    if not is_shell_command(command) and not auto_confirm:
        console.print(f"[yellow]Warning: '{command}' doesn't look like a valid shell command.[/yellow]")
        console.print("[yellow]Execute anyway? [y/N]:[/yellow]", end=" ")
        choice = input().lower()
        if choice != "y":
            return
    elif not is_shell_command(command) and auto_confirm:
        console.print(f"[yellow]Warning: '{command}' doesn't look like a valid shell command. Executing anyway due to auto-confirm.[/yellow]")

    # Display different message based on auto-confirm
    if auto_confirm:
        console.print(Text("\n[Auto-executing command]", style="bold blue"))
        console.print(Panel(Text(command, style="cyan bold"),
                           border_style="blue",
                           expand=False))
    else:
        console.print(Text("\n[Executing command]", style="bold green"))
        console.print(Panel(Text(command, style="cyan bold"),
                           border_style="green",
                           expand=False))

    # Capture the output to display it properly
    import subprocess
    import shlex

    # Check if command contains shell operators (|, >, <, &&, ||, ;, etc.)
    has_shell_operators = any(op in command for op in ['|', '>', '<', '&&', '||', ';', '$', '`', '*', '?', '{', '['])

    try:
        # Run the command and capture its output
        if has_shell_operators:
            # Use shell=True for commands with shell operators
            process = subprocess.run(
                command,  # Pass command as string when using shell=True
                shell=True,
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            # Use shlex.split for regular commands without shell operators
            process = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                check=False,
            )

        # Show command output with a clear label
        if process.stdout:
            console.print(Panel(
                process.stdout.strip(),
                title="[bold cyan]Command Result[/bold cyan]",
                title_align="center",
                border_style="cyan",
                padding=(1, 2),
                expand=False
            ))

        # Show any errors
        if process.returncode != 0:
            console.print(f"[bold red]Command failed with exit code {process.returncode}[/bold red]")
            if process.stderr:
                console.print(f"[red]Error: {process.stderr.strip()}[/red]")
            return False

        return True
    except Exception as e:
        console.print(f"[bold red]Failed to execute command: {e}[/bold red]")
        return False

def interactive_mode(chat_mode=False):
    """Run TerminalAI in interactive mode. If chat_mode is True, stay in a loop."""
    console = Console()

    if chat_mode:
        console.print(Panel.fit(
            Text("TerminalAI AI Chat Mode: You are now chatting with the AI. Type 'exit' to quit.", style="bold magenta"),
            border_style="magenta"
        ))
        console.print("[dim]Type 'exit', 'quit', or 'q' to return to your shell.[/dim]")
    else:
        # Create the styled text for the panel
        panel_text = Text()
        panel_text.append("Terminal AI: ", style="bold cyan")
        panel_text.append("What is your question? ", style="white")
        panel_text.append("(Type ", style="yellow")
        panel_text.append("exit", style="bold red")
        panel_text.append(" or ", style="yellow")
        panel_text.append("q", style="bold red")
        panel_text.append(" to quit)", style="yellow")
        console.print(Panel.fit(
            panel_text,
            border_style="cyan" # Keep border cyan
        ))

    while True:
        # Add visual separation between interactions
        console.print("")
        current_config = load_config() # Load config to get provider and model info
        provider_name = current_config.get("default_provider", "Unknown")

        display_provider_name = provider_name
        if provider_name == "ollama":
            ollama_model = current_config.get("providers", {}).get("ollama", {}).get("model", "")
            if ollama_model:
                display_provider_name = f"ollama-{ollama_model}"
            else:
                display_provider_name = "ollama (model not set)" # Fallback if model isn't in config

        prompt = Text()
        prompt.append("AI:", style="bold cyan")
        prompt.append("(", style="bold green")
        prompt.append(display_provider_name, style="bold green") # Use the potentially modified name
        prompt.append(")", style="bold green")
        prompt.append("> ", style="bold cyan")
        console.print(prompt, end="")
        query = input().strip()

        if query.lower() in ["exit", "quit", "q"]:
            console.print("[bold cyan]Goodbye![/bold cyan]")
            break

        if not query:
            continue

        system_context = get_system_context()

        provider = get_provider(load_config().get("default_provider", ""))
        if not provider:
            console.print("[bold red]No AI provider configured. Please run 'ai setup' first.[/bold red]")
            break

        try:
            # Show a thinking indicator
            console.print("[dim]Thinking...[/dim]")

            response_from_provider = provider.generate_response(query, system_context, verbose=False)

            # Clear the thinking indicator with a visual separator
            console.print(Rule(style="dim"))

            # Clean the response before printing and command extraction
            temp_response = response_from_provider.strip() # General strip first
            # Use a regex for more flexible prefix matching, e.g., "[AI] ", "AI: ", "[AI]", "AI:"
            # and ensure we only strip it if it's at the very beginning of the string.
            # common_ai_prefixes = re.compile(r"^(\[AI\]|AI:)\s*", re.IGNORECASE)
            # match = common_ai_prefixes.match(temp_response)
            # if match:
            #    cleaned_response = temp_response[match.end():]
            # else:
            #    cleaned_response = temp_response

            # Simpler string method approach, which should be sufficient here:
            cleaned_response = temp_response
            if temp_response.lower().startswith("[ai]"):
                # Strip "[ai]" and then any leading whitespace
                cleaned_response = temp_response[4:].lstrip()
            elif temp_response.lower().startswith("ai:"):
                # Strip "ai:" and then any leading whitespace
                cleaned_response = temp_response[3:].lstrip()

            print_ai_answer_with_rich(cleaned_response) # Pass cleaned response

            # Extract and handle commands from the CLEANED response
            commands = get_commands_interactive(cleaned_response, max_commands=3)

            if commands:
                handle_commands(commands, auto_confirm=False)

        except SystemExit: # Allow SystemExit from handle_commands (eval mode) to pass through
            raise
        except (ValueError, TypeError, OSError, KeyboardInterrupt) as e:
            # Catch common user/AI errors
            console.print(f"[bold red]Error during processing: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()
        except Exception as e:
            # Catch-all for truly unexpected errors (should be rare)
            console.print(f"[bold red]Unexpected error: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()

        # If NOT in chat_mode, exit after the first interaction (successful or error)
        if not chat_mode:
            break # Break the while loop

    # If the loop was broken (only happens if not chat_mode), exit cleanly.
    sys.exit(0)

# New refactored function for setting default provider
def _set_default_provider_interactive(console: Console):
    """Interactively sets the default AI provider and saves it to config."""
    config = load_config()
    providers = list(config['providers'].keys())
    console.print("\n[bold]Available providers:[/bold]")
    for idx, p_item in enumerate(providers, 1):
        is_default = ""
        if p_item == config.get('default_provider'):
            is_default = ' (default)'
        console.print(f"[bold yellow]{idx}[/bold yellow]. {p_item}{is_default}")
    sel_prompt = f"[bold green]Select provider (1-{len(providers)}): [/bold green]"
    sel = console.input(sel_prompt).strip()
    if sel.isdigit() and 1 <= int(sel) <= len(providers):
        selected_provider = providers[int(sel)-1]
        config['default_provider'] = selected_provider
        save_config(config)
        console.print(f"[bold green]Default provider set to "
                      f"{selected_provider}.[/bold green]")
        return True
    else:
        console.print("[red]Invalid selection.[/red]")
        return False

# New refactored function for setting Ollama model
def _set_ollama_model_interactive(console: Console):
    """Interactively sets the Ollama model and saves it to config."""
    import sys
    import os
    DEBUG = os.environ.get("TERMINALAI_DEBUG", "0") == "1"
    if DEBUG:
        print("[DEBUG] Entered _set_ollama_model_interactive", file=sys.stderr)
    config = load_config()
    pname = 'ollama' # We are specifically configuring Ollama here

    if pname not in config['providers']:
        config['providers'][pname] = {} # Ensure ollama provider entry exists

    current_host = config['providers'][pname].get('host', 'http://localhost:11434')
    console.print(f"Current Ollama host: {current_host}")
    ollama_host_prompt = (
        "Enter Ollama host (leave blank to keep current, e.g., http://localhost:11434): "
    )
    sys.stdout.flush()
    if DEBUG:
        print("[DEBUG] About to prompt for Ollama host", file=sys.stderr)
    new_host_input = console.input(ollama_host_prompt).strip()
    console.print()  # Add a blank line for separation
    if DEBUG:
        print(f"[DEBUG] Got Ollama host input: '{new_host_input}'", file=sys.stderr)
    host_to_use = current_host
    if new_host_input:
        config['providers'][pname]['host'] = new_host_input
        host_to_use = new_host_input
        console.print("[bold green]Ollama host updated.[/bold green]")

    current_model = config['providers'][pname].get('model', 'llama3')
    console.print(f"Current Ollama model: {current_model}")

    available_models = []
    try:
        tags_url = f"{host_to_use}/api/tags"
        console.print(f"[dim]Fetching models from {tags_url}...[/dim]")
        sys.stdout.flush()
        if DEBUG:
            print(f"[DEBUG] About to fetch models from {tags_url}", file=sys.stderr)
        response = requests.get(tags_url, timeout=5)
        response.raise_for_status()
        models_data = response.json().get("models", [])
        if DEBUG:
            print(f"[DEBUG] Models data: {models_data}", file=sys.stderr)
        if models_data:
            available_models = [m.get("name") for m in models_data if m.get("name")]

        if available_models:
            console.print("[bold]Available Ollama models:[/bold]")
            for i, model_name_option in enumerate(available_models, 1):
                console.print(f"  [bold yellow]{i}[/bold yellow]. {model_name_option}")
            if DEBUG:
                print(f"[DEBUG] Printed {len(available_models)} models", file=sys.stderr)
            model_choice_prompt = (
                "[bold green]Choose a model number, or enter 'c' to cancel: [/bold green]"
            )
            sys.stdout.flush()
            if DEBUG:
                print("[DEBUG] About to prompt for model selection", file=sys.stderr)
            while True:
                model_sel = console.input(model_choice_prompt).strip()
                if DEBUG:
                    print(f"[DEBUG] Got model selection input: '{model_sel}'", file=sys.stderr)
                if model_sel.lower() == 'c':
                    console.print(f"[yellow]Model selection cancelled. Model remains: {current_model}[/yellow]")
                    break
                if model_sel.isdigit() and 1 <= int(model_sel) <= len(available_models):
                    selected_model_name = available_models[int(model_sel)-1]
                    config['providers'][pname]['model'] = selected_model_name
                    console.print(f"[bold green]Ollama model set to: {selected_model_name}[/bold green]")
                    break
                else:
                    console.print(f"[red]Invalid selection. Please enter a number between 1 and {len(available_models)}, or 'c' to cancel.[/red]")
        else:
            console.print(f"[yellow]No models found via Ollama API or API not reachable at {host_to_use}.[/yellow]")
            console.print("[yellow]You can still enter a model name manually.[/yellow]")
            manual_model_prompt = f"Enter Ollama model name (e.g., mistral:latest, current: {current_model}): "
            sys.stdout.flush()
            if DEBUG:
                print("[DEBUG] About to prompt for manual model entry", file=sys.stderr)
            manual_model_input = console.input(manual_model_prompt).strip()
            if DEBUG:
                print(f"[DEBUG] Got manual model input: '{manual_model_input}'", file=sys.stderr)
            if manual_model_input:
                config['providers'][pname]['model'] = manual_model_input
                console.print(f"[bold green]Ollama model set to: {manual_model_input}[/bold green]")
            else:
                console.print(f"[yellow]No model entered. Model remains: {current_model}[/yellow]")

    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error fetching Ollama models: {e}[/red]")
        console.print("[yellow]Please ensure Ollama is running and accessible at the specified host.[/yellow]")
        console.print("[yellow]You can enter a model name manually.[/yellow]")
        manual_model_prompt_on_error = f"Enter Ollama model name (e.g., mistral:latest, current: {current_model}): "
        sys.stdout.flush()
        if DEBUG:
            print("[DEBUG] About to prompt for manual model entry after error", file=sys.stderr)
        manual_model_input_on_error = console.input(manual_model_prompt_on_error).strip()
        if DEBUG:
            print(f"[DEBUG] Got manual model input after error: '{manual_model_input_on_error}'", file=sys.stderr)
        if manual_model_input_on_error:
            config['providers'][pname]['model'] = manual_model_input_on_error
            console.print(f"[bold green]Ollama model set to: {manual_model_input_on_error}[/bold green]")
        else:
            console.print(f"[yellow]No model entered. Model remains: {current_model}[/yellow]")

    # Print summary of current host and model
    summary_host = config['providers'][pname].get('host', host_to_use)
    summary_model = config['providers'][pname].get('model', current_model)
    console.print("\n[bold cyan]Ollama configuration summary:[/bold cyan]")
    console.print(f"  [bold]Host:[/bold] [green]{summary_host}[/green]")
    console.print(f"  [bold]Model:[/bold] [yellow]{summary_model}[/yellow]\n")
    save_config(config)
    if DEBUG:
        print("[DEBUG] Exiting _set_ollama_model_interactive", file=sys.stderr)
    return True # Assuming success unless an unhandled exception occurs

def setup_wizard():
    """Run the setup wizard to configure TerminalAI."""
    console = Console()

    logo = '''
████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██║       █████╗ ██╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║      ██╔══██╗██║
   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║      ███████║██║
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║      ██╔══██║██║
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗ ██║  ██║██║
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═╝  ╚═╝╚═╝
'''
    while True:
        console.clear()
        console.print(logo, style="bold cyan")
        console.print("[bold magenta]TerminalAI Setup Menu:[/bold magenta]")
        menu_options = [
            "1. Set default provider",
            "2. See current system prompt",
            "3. Edit current system prompt",
            "4. Reset system prompt to default",
            "5. Setup API keys",
            "6. See current API keys",
            "7. Install ai shell integration",
            "8. Uninstall ai shell integration",
            "9. Check ai shell integration",
            "10. View quick setup guide",
            "11. About TerminalAI",
            "12. Exit"
        ]
        menu_info = {
            '1': ("Set which AI provider (OpenRouter, Gemini, Mistral, Ollama) "
                  "is used by default for all queries."),
            '2': "View the current system prompt that guides the AI's behavior.",
            '3': "Edit the system prompt to customize how the AI responds.",
            '4': "Reset the system prompt to the default recommended by TerminalAI.",
            '5': "Set/update API key/host for any provider.",
            '6': "List providers and their stored API key/host.",
            '7': ("Install the 'ai' shell function for seamless stateful command execution "
                  "(Only affects ai \"...\" mode)."),
            '8': "Uninstall the 'ai' shell function from your shell config.",
            '9': "Check if the 'ai' shell integration is installed in your shell config.",
            '10': "Display the quick setup guide to help you get started.",
            '11': "View information about TerminalAI, including version and links.",
            '12': "Exit the setup menu."
        }
        for opt in menu_options:
            num, desc = opt.split('.', 1)
            console.print(f"[bold yellow]{num}[/bold yellow].[white]{desc}[/white]")
        info_prompt = ("Type 'i' followed by a number (e.g., i1) "
                       "for more info about an option.")
        console.print(f"[dim]{info_prompt}[/dim]")
        choice = console.input("[bold green]Choose an action (1-12): [/bold green]").strip()

        if choice.startswith('i') and choice[1:].isdigit():
            info_num = choice[1:]
            if info_num in menu_info:
                info_text = menu_info[info_num]
                console.print(f"[bold cyan]Info for option {info_num}:[/bold cyan]")
                console.print(info_text)
            else:
                console.print("[red]No info available for that option.[/red]")
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '1':
            _set_default_provider_interactive(console)
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '2':
            config = load_config() # Ensure config is loaded if not through other paths
            console.print("\n[bold]Current system prompt:[/bold]\n")
            console.print(get_system_prompt())
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '3':
            config = load_config()
            console.print("\n[bold]Current system prompt:[/bold]\n")
            console.print(config.get('system_prompt', ''))
            new_prompt_input = (
                "\n[bold green]Enter new system prompt "
                "(leave blank to cancel):\n[/bold green]"
            )
            new_prompt = console.input(new_prompt_input)
            if new_prompt.strip():
                config['system_prompt'] = new_prompt.strip()
                save_config(config)
                console.print(
                    "[bold green]System prompt updated.[/bold green]"
                )
            else:
                console.print("[yellow]No changes made.[/yellow]")
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '4':
            config = load_config()
            config['system_prompt'] = DEFAULT_SYSTEM_PROMPT
            save_config(config)
            console.print("[bold green]System prompt reset to default.[/bold green]")
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '5':
            config = load_config()
            providers = list(config['providers'].keys())
            console.print("\n[bold]Providers:[/bold]")
            for idx, p_item in enumerate(providers, 1):
                console.print(f"[bold yellow]{idx}[/bold yellow]. {p_item}")
            sel_prompt = (f"[bold green]Select provider to set API key/host "
                          f"(1-{len(providers)}): [/bold green]")
            sel = console.input(sel_prompt).strip()
            if sel.isdigit() and 1 <= int(sel) <= len(providers):
                pname_selected = providers[int(sel)-1]
                if pname_selected == 'ollama':
                    _set_ollama_model_interactive(console) # Call the refactored function for Ollama
                else: # For other providers (OpenRouter, Gemini, Mistral)
                    current_api_key = config['providers'][pname_selected].get('api_key', '')
                    display_key = '(not set)' if not current_api_key else '[hidden]'
                    console.print(f"Current API key: {display_key}")
                    new_key_prompt = f"Enter new API key for {pname_selected}: "
                    new_key = console.input(new_key_prompt).strip()
                    if new_key:
                        config['providers'][pname_selected]['api_key'] = new_key
                        save_config(config)
                        console.print(
                            f"[bold green]API key for {pname_selected} updated.[/bold green]"
                        )
                    else:
                        console.print("[yellow]No changes made.[/yellow]")
            else:
                console.print("[red]Invalid selection.[/red]")
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '6':
            config = load_config()
            providers = list(config['providers'].keys())
            console.print("\n[bold]Current API keys / hosts:[/bold]")
            for p_item in providers:
                if p_item == 'ollama':
                    val = config['providers'][p_item].get('host', '')
                    shown = val if val else '[not set]'
                else:
                    val = config['providers'][p_item].get('api_key', '')
                    shown = '[not set]' if not val else '[hidden]'
                console.print(f"[bold yellow]{p_item}:[/bold yellow] {shown}")
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '7':
            install_shell_integration()
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '8':
            uninstall_shell_integration()
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '9':
            check_shell_integration()
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '10':
            console.print("\n[bold cyan]Quick Setup Guide:[/bold cyan]\n")
            guide = """
[bold yellow]1. Installation[/bold yellow]

You have two options to install TerminalAI:

[bold green]Option A: Install from PyPI (Recommended)[/bold green]
    pip install coaxial-terminal-ai

[bold green]Option B: Install from source[/bold green]
    git clone https://github.com/coaxialdolor/terminalai.git
    cd terminalai
    pip install -e .

[bold yellow]2. Initial Configuration[/bold yellow]

In a terminal window, run:
    ai setup

• Enter [bold]5[/bold] to select "Setup API Keys"
• Select your preferred AI provider:
  - Mistral is recommended for its good performance and generous free tier limits
  - Ollama is ideal if you prefer locally hosted AI
  - You can also use OpenRouter or Gemini
• Enter the API key for your selected provider(s)
• Press Enter to return to the setup menu

[bold yellow]3. Set Default Provider[/bold yellow]

• At the setup menu, select [bold]1[/bold] to "Setup default provider"
• Choose a provider that you've saved an API key for
• Press Enter to return to the setup menu

[bold yellow]4. Understanding Stateful Command Execution[/bold yellow]

For commands like 'cd' or 'export' that change your shell's state, TerminalAI
will offer to copy the command to your clipboard. You can then paste and run it.

(Optional) Shell Integration:
• You can still install a shell integration via option [bold]7[/bold] in the setup menu.
  This is for advanced users who prefer a shell function for such commands.
  Note that the primary method is now copy-to-clipboard.

[bold yellow]5. Start Using TerminalAI[/bold yellow]
You're now ready to use TerminalAI! Here's how:

[bold green]Direct Query with Quotes[/bold green]
    ai "how do I find all text files in the current directory?"

[bold green]Interactive Mode[/bold green]
    ai
    AI: What is your question?
    : how do I find all text files in the current directory?

[bold green]Running Commands[/bold green]
• When TerminalAI suggests terminal commands, you'll be prompted:
  - For a single command: Enter Y to run or N to skip
  - For multiple commands: Enter the number of the command you want to run
  - For stateful (shell state-changing) commands, you'll be prompted to copy them
    to your clipboard to run manually.
"""
            console.print(guide)
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '11':
            console.print("\n[bold cyan]About TerminalAI:[/bold cyan]\n")
            console.print(f"[bold]Version:[/bold] {__version__}")
            console.print("[bold]GitHub:[/bold] https://github.com/coaxialdolor/terminalai")
            console.print("[bold]PyPI:[/bold] https://pypi.org/project/coaxial-terminal-ai/")
            console.print("\n[bold]Description:[/bold]")
            console.print(
                "TerminalAI is a command-line AI assistant designed to interpret user"
            )
            console.print(
                "requests, suggest relevant terminal commands, "
                "and execute them interactively."
            )
            console.print("\n[bold red]Disclaimer:[/bold red]")
            console.print(
                "This application is provided as-is without any warranties. "
                "Use at your own risk."
            )
            console.print(
                "The developers cannot be held responsible for any data loss, system damage,"
            )
            console.print(
                "or other issues that may occur from executing "
                "suggested commands."
            )
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == '12':
            console.print(
                "[bold cyan]Exiting setup.[/bold cyan]"
            )
            break
        else:
            error_msg = (
                "Invalid choice. Please select a number from 1 to 12."
            )
            console.print(f"[red]{error_msg}[/red]")
            console.input("[dim]Press Enter to continue...[/dim]")
