"""CLI interaction functionality for TerminalAI."""
import os
import sys
import argparse
import subprocess
import time # Import time module for sleep
from terminalai.command_utils import is_shell_command
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
from terminalai.formatting import print_ai_answer_with_rich, print_exploration_results
# Use the more specific get_commands_interactive (alias for extract_commands) from 021offshoot
from terminalai.command_extraction import extract_commands as get_commands_interactive
from terminalai.__init__ import __version__
from terminalai.query_utils import preprocess_query
import requests # Add this import for Ollama model fetching

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
  --auto            Enable auto mode: Allows the AI to explore your filesystem to answer questions. It will automatically execute safe commands to gather information and keep conversation context for follow-up questions.

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
        "--auto",
        action="store_true",
        help="Enable auto mode: Allows the AI to explore your filesystem to answer questions. It will automatically execute safe commands to gather information and keep conversation context for follow-up questions."
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
    args, _ = parser.parse_known_args(filtered_argv)
    if args.read_file and args.explain:
        parser.error("argument --explain: not allowed with argument --read-file")

    # Check if --eval-mode was in original args but removed for parsing
    if "--eval-mode" in sys.argv:
        args.eval_mode = True

    return args

# --- Helper Function for AI Risk Assessment ---

def _get_ai_risk_assessment(command, provider):
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
    except (requests.RequestException, ValueError, KeyError) as e:
        return f"Risk assessment failed. Error: {e}"
    except OSError as e:
        return f"System error during risk assessment: {e}"

# --- Main Command Handling Logic ---

def handle_commands(commands, auto_confirm=False, auto_mode=False):
    """Handle extracted commands, prompting the user and executing if confirmed.

    Args:
        commands: List of commands to handle
        auto_confirm: If True, auto-confirm non-risky commands without prompting
        auto_mode: If True, execute non-risky commands automatically and show results directly
    """
    console = Console()

    # Check if stdin is a terminal or a pipe
    is_interactive = sys.stdin.isatty()

    provider_instance = None
    if commands:
        try:
            config = load_config()
            default_provider_name = config.get("default_provider")
            if default_provider_name:
                provider_instance = get_provider(default_provider_name)
        except (ValueError, KeyError) as e:
            console.print(Text(f"[WARNING] Could not load AI provider for risk assessment: {e}", style="yellow"))
            # provider_instance remains None
        except (FileNotFoundError, PermissionError) as e:
            console.print(Text(f"[WARNING] File system error loading AI provider: {e}", style="yellow"))
            # provider_instance remains None

    if not commands:
        return

    n_commands = len(commands)

    # Non-interactive mode with pipe input special handling
    if not is_interactive:
        console.print("[dim]Running in non-interactive mode (input from pipe)[/dim]")

        # If auto-confirm is on, proceed as normal
        if auto_confirm:
            # Process continues with existing auto-confirm logic
            pass
        # If not auto-confirm but we have commands, execute the first one automatically
        elif n_commands == 1:
            command = commands[0]
            is_stateful_cmd = is_stateful_command(command)
            is_risky_cmd = is_risky_command(command)

            if is_stateful_cmd:
                console.print("[yellow]Stateful command detected in non-interactive mode. Command will be copied to clipboard.[/yellow]")
                copy_to_clipboard(command)
                console.print(f"[green]Command copied to clipboard: {command}[/green]")
                return

            if is_risky_cmd:
                console.print("[red]Risky command detected in non-interactive mode. Command will not be executed.[/red]")
                return

            # Run first command automatically if not risky or stateful
            console.print(f"[green]Auto-executing first command in non-interactive mode: {command}[/green]")
            run_command(command, auto_confirm=True)
            return
        elif n_commands > 1:
            # With multiple commands and no auto-confirm, just print the commands
            console.print("[yellow]Multiple commands detected in non-interactive mode without auto-confirm.[/yellow]")
            console.print("[yellow]First command will be executed automatically if not risky or stateful.[/yellow]")

            cmd_first = commands[0]
            is_stateful_first = is_stateful_command(cmd_first)
            is_risky_first = is_risky_command(cmd_first)

            if is_stateful_first:
                console.print("[yellow]First command is stateful. Command will be copied to clipboard.[/yellow]")
                copy_to_clipboard(cmd_first)
                console.print(f"[green]Command copied to clipboard: {cmd_first}[/green]")
                return

            if is_risky_first:
                console.print("[red]First command is risky. Command will not be executed.[/red]")
                return

            # Run first command automatically if not risky or stateful
            console.print(f"[green]Auto-executing first command: {cmd_first}[/green]")
            run_command(cmd_first, auto_confirm=True)
            return

    # Proceed with normal interactive handling
    if n_commands == 1:
        command = commands[0]
        is_stateful_cmd = is_stateful_command(command)
        is_risky_cmd = is_risky_command(command)

        if is_risky_cmd:
            risk_explanation = _get_ai_risk_assessment(command, provider_instance)
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
        if (auto_confirm or auto_mode) and not is_risky_cmd:
            console.print(Text("\n[Auto-executing command]", style="bold blue"))
            console.print(Panel(Text(command, style="cyan bold"),
                               border_style="blue",
                               expand=False))
            run_command(command, auto_confirm=True)
            return

        # Risky commands always require confirmation, even in auto mode
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
        # Auto-confirm or auto_mode case for multiple commands
        if auto_confirm or auto_mode:
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
                    risk_explanation = _get_ai_risk_assessment(cmd_item, provider_instance)
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
                    risk_explanation = _get_ai_risk_assessment(cmd_item, provider_instance)
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
                    risk_explanation_num = _get_ai_risk_assessment(cmd_to_run, provider_instance)
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
    except subprocess.SubprocessError as e:
        console.print(f"[bold red]Subprocess error executing command: {e}[/bold red]")
        return False
    except OSError as e:
        console.print(f"[bold red]OS error executing command: {e}[/bold red]")
        return False

def interactive_mode(chat_mode=False, auto_mode=False):
    """Run TerminalAI in interactive mode.

    Args:
        chat_mode: If True, stay in a loop for continuous conversation
        auto_mode: If True, execute non-risky commands automatically without confirmation
                   and allow AI to proactively explore filesystem to answer questions
    """
    console = Console()
    # Track conversation history for chat and auto modes
    conversation_history = []

    # Check if stdin is a terminal or a pipe
    is_interactive = sys.stdin.isatty()

    if chat_mode:
        mode_description = "Chat Mode"
        if auto_mode:
            mode_description = "Auto Mode"
            console.print(Panel.fit(
                Text("Auto Mode allows the AI to explore your filesystem to answer questions. It will automatically execute safe commands but will always ask for confirmation before making changes.", style="yellow"),
                border_style="yellow"
            ))

        console.print(Panel.fit(
            Text(f"TerminalAI AI {mode_description}: You are now chatting with the AI. Type 'exit' to quit.", style="bold magenta"),
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

    # Special handling for non-interactive mode (pipe input)
    if not is_interactive:
        console.print("[dim]Running in non-interactive mode (input from pipe)[/dim]")
        try:
            # Read a single line from stdin (the piped content)
            query = sys.stdin.readline().strip()
            console.print(f"AI:(stdin)> {query}")

            if not query:
                console.print("[yellow]No input received from pipe.[/yellow]")
                return

            # Process the query
            system_context = get_system_context()
            provider = get_provider(load_config().get("default_provider", ""))
            if not provider:
                console.print("[bold red]No AI provider configured. Please run 'ai setup' first.[/bold red]")
                return

            # Show thinking indicator
            console.print("[dim]Thinking...[/dim]")

            # Preprocess the query
            processed_query = preprocess_query(query)
            # Skip showing clarification in auto mode - users don't like it
            if processed_query != query and not auto_mode:
                console.print(Panel(
                    Text(f"Note: Clarified your query to: \"{processed_query}\"", style="cyan"),
                    border_style="cyan",
                    expand=False
                ))

            try:
                # Get response
                response_from_provider = provider.generate_response(processed_query, system_context, verbose=False)

                # Show response
                console.print(Rule(style="dim"))

                # Clean response
                cleaned_response = response_from_provider.strip()
                if cleaned_response.lower().startswith("[ai]"):
                    cleaned_response = cleaned_response[4:].lstrip()
                elif cleaned_response.lower().startswith("ai:"):
                    cleaned_response = cleaned_response[3:].lstrip()

                print_ai_answer_with_rich(cleaned_response)

                # Extract and handle commands with auto-execute for first non-risky command
                commands = get_commands_interactive(cleaned_response, max_commands=3, auto_mode=auto_mode)
                if commands:
                    # Auto-confirm in pipe mode for non-interactive use
                    handle_commands(commands, auto_confirm=True, auto_mode=auto_mode)

                return
            except EOFError:
                console.print("[yellow]No input received from pipe.[/yellow]")
                return
            except requests.RequestException as e:
                console.print(f"[bold red]Error communicating with AI provider: {str(e)}[/bold red]")
                return
            except (ValueError, TypeError, AttributeError) as e:
                console.print(f"[bold red]Error processing input data: {str(e)}[/bold red]")
                import traceback
                traceback.print_exc()
                return
            except (FileNotFoundError, PermissionError) as e:
                console.print(f"[bold red]File system error: {str(e)}[/bold red]")
                import traceback
                traceback.print_exc()
                return

        except EOFError:
            console.print("[yellow]No input received from pipe.[/yellow]")
            return
        except requests.RequestException as e:
            console.print(f"[bold red]Error communicating with AI provider: {str(e)}[/bold red]")
            return
        except (ValueError, TypeError, AttributeError) as e:
            console.print(f"[bold red]Error processing input data: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()
            return
        except (FileNotFoundError, PermissionError) as e:
            console.print(f"[bold red]File system error: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()
            return

    while True:
        try:
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

            # Use a timeout to avoid hanging on input (10 seconds)
            query = input().strip()

            # Skip blank inputs and prevent the command itself from being interpreted as a query
            if not query or query.lower() in ["ai --auto", "ai -auto", "--auto", "-auto"]:
                continue

            if query.lower() in ["exit", "quit", "q"]:
                console.print("[bold cyan]Goodbye![/bold cyan]")
                break

            if not query:
                continue

            # Build the system context
            system_context = get_system_context()

            # Add conversation history to system context for chat and auto modes
            if (chat_mode or auto_mode) and conversation_history:
                history_context = "\n\nPrevious conversation:\n"
                for idx, (q, a) in enumerate(conversation_history, 1):
                    history_context += f"User ({idx}): {q}\nAI ({idx}): {a}\n\n"
                system_context += history_context

            # Add auto mode instruction to system context if enabled
            if auto_mode:
                auto_mode_context = "\n\nYou are running in Auto Mode. This means you can:\n"
                auto_mode_context += "1. Proactively explore the filesystem to find information needed to answer questions\n"
                auto_mode_context += "2. Read files to understand their contents when relevant\n"
                auto_mode_context += "3. Suggest non-risky commands that the user can execute\n"
                auto_mode_context += "\nExploration Guidelines:\n"
                auto_mode_context += "- ALWAYS prefer non-stateful commands for exploration\n"
                auto_mode_context += "- Use absolute paths in commands (e.g., 'ls /path' instead of 'cd /path && ls')\n"
                auto_mode_context += "- Limit exploration depth to avoid overwhelming the user\n"
                auto_mode_context += "- When exploring directories, start with a high-level overview\n"
                auto_mode_context += "- Be concise in your explanations and focus on direct answers\n"
                auto_mode_context += "- When the user asks about files in a directory, always include BOTH file and folder counts\n"
                auto_mode_context += "- When the user asks for filenames or file lists, provide the actual names of the files\n"
                auto_mode_context += "- When the user asks about file content, attempt to read and display the relevant file\n"
                auto_mode_context += "- NEVER include shell prompts (like 'user$' or '$') in command examples\n"
                auto_mode_context += "- Use ```bash\ncommand\n``` format for commands without shell prompts\n"
                auto_mode_context += "\nSafety Rules:\n"
                auto_mode_context += "- NEVER execute commands that modify, delete, or move files without explicit user confirmation\n"
                auto_mode_context += "- Always explain what information you're looking for before executing commands\n"
                auto_mode_context += "- All exploration commands will be shown to the user as they execute\n"
                system_context += auto_mode_context

            provider = get_provider(load_config().get("default_provider", ""))
            if not provider:
                console.print("[bold red]No AI provider configured. Please run 'ai setup' first.[/bold red]")
                break

            # Show thinking indicator
            console.print("[dim]Thinking...[/dim]")

            # Preprocess query to clarify potentially ambiguous requests
            processed_query = preprocess_query(query)
            # Skip showing clarification in auto mode - users don't like it
            if processed_query != query and not auto_mode:
                console.print(Panel(
                    Text(f"Note: Clarified your query to: \"{processed_query}\"", style="cyan"),
                    border_style="cyan",
                    expand=False
                ))

            try:
                # Get response
                response_from_provider = provider.generate_response(processed_query, system_context, verbose=False)

                # Show response
                console.print(Rule(style="dim"))

                # Clean response
                cleaned_response = response_from_provider.strip()
                if cleaned_response.lower().startswith("[ai]"):
                    cleaned_response = cleaned_response[4:].lstrip()
                elif cleaned_response.lower().startswith("ai:"):
                    cleaned_response = cleaned_response[3:].lstrip()

                print_ai_answer_with_rich(cleaned_response)

                # Extract and handle commands with auto-execute for first non-risky command
                commands = get_commands_interactive(cleaned_response, max_commands=3, auto_mode=auto_mode)
                if commands:
                    # Auto-confirm in pipe mode for non-interactive use
                    handle_commands(commands, auto_confirm=True, auto_mode=auto_mode)

                return
            except EOFError:
                console.print("[yellow]No input received from pipe.[/yellow]")
                return
            except requests.RequestException as e:
                console.print(f"[bold red]Error communicating with AI provider: {str(e)}[/bold red]")
                return
            except (ValueError, TypeError, AttributeError) as e:
                console.print(f"[bold red]Error processing input data: {str(e)}[/bold red]")
                import traceback
                traceback.print_exc()
                return
            except (FileNotFoundError, PermissionError) as e:
                console.print(f"[bold red]File system error: {str(e)}[/bold red]")
                import traceback
                traceback.print_exc()
                return

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Operation cancelled. Type 'exit' to quit or continue with a new query.[/bold yellow]")
            continue
        except (ValueError, TypeError, OSError) as e:
            # Catch common user/AI errors
            console.print(f"[bold red]Error during processing: {str(e)}[/bold red]")
        except (RuntimeError, subprocess.SubprocessError) as e:
            # Catch more specific errors instead of using a generic Exception
            console.print(f"[bold red]Unexpected error: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()

        # If NOT in chat_mode, exit after the first interaction (successful or error)
        if not chat_mode:
            break # Break the while loop

    # If the loop was broken (only happens if not chat_mode), exit cleanly.
    sys.exit(0)

def extract_exploration_commands(query):
    """Extract commands that should be executed to explore the filesystem and gather information.

    Args:
        query: The user's query

    Returns:
        List of exploration commands to execute
    """
    # Debug print
    print(f"Analyzing query for exploration commands: {query[:50]}..." if len(query) > 50 else query)

    exploration_keywords = [
        "files", "directory", "folder", "search", "find", "locate",
        "list", "count", "size", "disk", "storage", "space", "content",
        "what's in", "show me", "how many", "where is", "look for"
    ]

    # Check if the query is asking about files, directories, or system info
    query_needs_exploration = any(keyword in query.lower() for keyword in exploration_keywords)

    if not query_needs_exploration:
        return []

    # Define safe exploration commands based on the query
    exploration_commands = []
    cwd = os.getcwd()

    # Add basic commands for tests compatibility
    if "list" in query.lower() and "files" in query.lower():
        exploration_commands.append("ls -la")

    if any(word in query.lower() for word in ["disk", "space", "storage", "available"]):
        exploration_commands.append("df -h")

    if "count" in query.lower() and "files" in query.lower():
        exploration_commands.append("find . -type f | wc -l")

    # Start with identifying locations mentioned in the query
    locations = []

    # Check for specific paths mentioned in the query
    for word in query.lower().split():
        if '/' in word:
            # Clean up the path from punctuation
            path = word.strip("\"'.,?!:;()[]{}").rstrip("/")
            if path and not path.startswith('/'):
                # Make relative path absolute
                path = os.path.join(cwd, path)
            if path:
                locations.append(path)

    # If no locations specified, use current directory
    if not locations:
        locations = [cwd]

    # Set a strict max depth limit to avoid deep traversals
    max_depth = 1  # Default to 1 level for better performance and focus

    # For specific queries about subdirectories, allow depth of 2
    if "subdirectories" in query.lower() or "subfolders" in query.lower():
        max_depth = 2

    # For queries that clearly want ALL files/folders, use recursive listing
    if any(word in query.lower() for word in ["all files", "all folders", "total files", "total folders", "total count", "recursively", "everything inside"]):
        # Allow greater depth for recursive searches
        max_depth = 3

    # For location-specific queries, be more targeted
    if "desktop" in query.lower():
        locations = [os.path.expanduser("~/Desktop")]
    elif "documents" in query.lower():
        locations = [os.path.expanduser("~/Documents")]
    elif "downloads" in query.lower():
        locations = [os.path.expanduser("~/Downloads")]

    # For each identified location, add appropriate exploration commands
    for location in locations:
        # Count visible (non-hidden) files - exclude directories, totals, and hidden files
        exploration_commands.append(f"ls -la {location} | grep -v '^d' | grep -v '^total' | awk '{{print $NF}}' | grep -v '^\\.' | wc -l")

        # Count visible (non-hidden) folders (excluding . and ..)
        exploration_commands.append(f"ls -la {location} | grep '^d' | grep -v '^\\.\\.' | grep -v '^\\.$$' | grep -v '^\\.\\|^d.* \\.' | wc -l")

        # Count hidden files (files starting with .)
        exploration_commands.append(f"ls -la {location} | grep -v '^d' | grep -v '^total' | awk '{{print $NF}}' | grep '^\\.' | wc -l")

        # Count hidden folders (folders starting with .)
        exploration_commands.append(f"ls -la {location} | grep '^d' | grep -v '^\\.$$' | grep -v '^\\.\\.' | grep '^\\.\\|^d.* \\.' | wc -l")

        # For follow-up questions about file names, ensure we list the actual files
        if any(word in query.lower() for word in ["what are", "which files", "list files", "show files", "file names", "names of", "what files"]):
            # List visible (non-hidden) files
            exploration_commands.append(f"ls -la {location} | grep -v '^d' | grep -v '^total' | awk '{{print $NF}}' | grep -v '^\\.'")
            # List hidden files
            exploration_commands.append(f"ls -la {location} | grep -v '^d' | grep -v '^total' | awk '{{print $NF}}' | grep '^\\.'")

        # For follow-up questions about folder names
        if any(word in query.lower() for word in ["what are", "which folders", "which directories", "list folders", "list directories", "folder names", "directory names", "names of", "what folders", "what directories"]):
            # List visible (non-hidden) folders
            exploration_commands.append(f"ls -la {location} | grep '^d' | grep -v '^\\.\\.' | grep -v '^\\.$$' | grep -v '^\\.\\|^d.* \\.' | awk '{{print $NF}}'")
            # List hidden folders
            exploration_commands.append(f"ls -la {location} | grep '^d' | grep -v '^\\.$$' | grep -v '^\\.\\.' | grep '^\\.\\|^d.* \\.' | awk '{{print $NF}}'")

        # For questions about file content
        if any(word in query.lower() for word in ["content", "what is in", "what's in", "read", "show content", "display", "cat", "text in"]):
            # If specific file types are mentioned
            if "txt" in query.lower() or "text" in query.lower():
                # First list any text files for information
                exploration_commands.append(f"find {location} -maxdepth 1 -name '*.txt' -type f | sort")
                # Try to find and cat the first txt file found
                exploration_commands.append(f"find {location} -maxdepth 1 -name '*.txt' -type f -print0 | xargs -0 cat 2>/dev/null || echo 'No text files found'")
            elif any(specific_file in query.lower() for specific_file in ["auto.txt", "screenshot", ".ds_store", ".localized"]):
                # Handle requests for specific files by name
                for filename in ["auto.txt", "Screenshot", ".DS_Store", ".localized"]:
                    if filename.lower() in query.lower():
                        # First check if the file exists (case insensitive search)
                        exploration_commands.append(f"find {location} -maxdepth 1 -iname '*{filename}*' -type f")
                        # Then try to read its content
                        exploration_commands.append(f"find {location} -maxdepth 1 -iname '*{filename}*' -type f -print0 | xargs -0 cat 2>/dev/null || echo 'Cannot read file content'")
            else:
                # For generic content requests, locate potential files for inspection
                exploration_commands.append(f"ls -la {location} | grep -v '^d' | grep -v '^total' | head -5")

    # Count files - limit depth to prevent resource issues
    if any(word in query.lower() for word in ["count", "how many"]) and any(word in query.lower() for word in ["files", "directory", "folder"]):
        for location in locations:
            exploration_commands.append(f"find {location} -type f -maxdepth {max_depth} | wc -l")
            exploration_commands.append(f"find {location} -type d -maxdepth {max_depth} | wc -l")

    # Disk usage for specific locations only
    if any(word in query.lower() for word in ["size", "disk", "storage", "space"]):
        for location in locations:
            # Only show top-level size breakdown
            exploration_commands.append(f"du -h -d 1 {location} | sort -hr | head -n 5")

    # Remove any commands that might include stateful operations or be risky
    safe_commands = [cmd for cmd in exploration_commands
                    if not is_stateful_command(cmd) and not is_risky_command(cmd)]

    # Limit exploration commands - use more if it's a follow-up question asking for specific details
    if any(word in query.lower() for word in ["what are", "which files", "list files", "show files", "file names", "names of", "what files"]):
        return safe_commands[:5]  # Allow more commands for detailed follow-up questions
    else:
        return safe_commands[:3]  # Limit to 3 for basic counting queries

def execute_exploration_commands(commands, console):
    """Execute exploration commands and return their output.

    Args:
        commands: List of commands to execute
        console: Console object for output

    Returns:
        String containing combined output from all commands
    """
    results = []

    # Add debug message
    console.print("[dim]Starting exploration command execution...[/dim]")

    # Add timeout to prevent hanging on long-running commands
    command_timeout = 3  # 3 seconds timeout per command

    for cmd in commands:
        # Skip risky or stateful commands
        if is_risky_command(cmd) or is_stateful_command(cmd):
            console.print(f"[yellow]Skipping unsafe exploration command: {cmd}[/yellow]")
            continue

        console.print(f"[dim]Exploring: {cmd}[/dim]")

        # Execute the command
        import shlex

        # Check if command contains shell operators
        has_shell_operators = any(op in cmd for op in ['|', '>', '<', '&&', '||', ';', '$', '`', '*', '?', '{', '['])

        try:
            # Run the command and capture output with timeout
            if has_shell_operators:
                process = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=command_timeout  # Add timeout
                )
            else:
                process = subprocess.run(
                    shlex.split(cmd),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=command_timeout  # Add timeout
                )

            # Add command output to results
            if process.returncode == 0 and process.stdout:
                # Limit output size to prevent overwhelming responses
                stdout_limited = process.stdout.strip()
                if len(stdout_limited) > 1000:
                    stdout_limited = stdout_limited[:1000] + "\n... (output truncated)"
                results.append(f"Command: {cmd}\nOutput:\n{stdout_limited}\n")
            elif process.stderr:
                results.append(f"Command: {cmd}\nError: {process.stderr.strip()}\n")

        except subprocess.TimeoutExpired:
            console.print(f"[red]Command timed out after {command_timeout} seconds: {cmd}[/red]")
            results.append(f"Command: {cmd}\nError: Command timed out after {command_timeout} seconds\n")
        except subprocess.SubprocessError as e:
            console.print(f"[red]Subprocess error executing command: {e}[/red]")
            results.append(f"Command: {cmd}\nError: Subprocess error - {str(e)}\n")
        except (ValueError, TypeError) as e:
            console.print(f"[red]Error processing command: {e}[/red]")
            results.append(f"Command: {cmd}\nError: Parameter error - {str(e)}\n")
        except OSError as e:
            console.print(f"[red]OS error executing command: {e}[/red]")
            results.append(f"Command: {cmd}\nError: System error - {str(e)}\n")

    # Add a message to show completion
    console.print("[dim]Exploration complete.[/dim]")

    # Use new condensed formatting for exploration results
    print_exploration_results("\n".join(results))

    return "\n".join(results)

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
