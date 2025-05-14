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
    """Parse command line arguments."""
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
        "--eval-mode",
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

    return parser.parse_args()

# --- Helper Function for AI Risk Assessment ---

def _get_ai_risk_assessment(command, console, provider):
    """Gets a risk assessment for a command using a secondary AI call."""
    if not provider:
        return "Risk assessment requires a configured AI provider."

    try:
        cwd = os.getcwd()
        risk_query = f"<RISK_CONFIRMATION> Explain the potential consequences and dangers of running the following command(s) if my current working directory is '{cwd}':\n---\n{command}\n---"

        time.sleep(1) # Add 1-second delay before the API call

        # Optional: Show thinking indicator
        # with console.status("[dim]Assessing command risk...[/dim]"):
        risk_response = provider.generate_response(
            risk_query,
            system_context=None, # Not needed as we are overriding
            verbose=False, # Keep assessment concise
            override_system_prompt=_RISK_ASSESSMENT_SYSTEM_PROMPT # Use the hardcoded prompt
        )
        # Basic cleaning - remove potential leading/trailing whitespace/newlines
        risk_explanation = risk_response.strip()
        if not risk_explanation:
             return "AI returned empty risk assessment."
        return risk_explanation

    except Exception as e:
        # Log the exception details?
        # print(f"Error during risk assessment: {e}", file=sys.stderr)
        return f"Risk assessment failed. Error: {e}" # Return error info

# --- Main Command Handling Logic ---

def handle_commands(commands, auto_confirm=False, eval_mode=False, rich_to_stderr=False):
    """Handle extracted commands, prompting the user and executing if confirmed."""
    console = Console(file=sys.stderr if rich_to_stderr else None)
    provider = get_provider(load_config().get("default_provider", ""))

    # ANSI color codes for prompts (accessible throughout the function)
    color_reset = "\033[0m"
    color_bold_green = "\033[1;32m"
    color_bold_yellow = "\033[1;33m"
    color_bold_red = "\033[1;31m"
    color_bold_cyan = "\033[1;36m"
    color_dim = "\033[2m"

    # Detect shell integration
    shell_integration_active = os.environ.get("TERMINALAI_SHELL_INTEGRATION") == "1"

    if not commands:
        return

    n_commands = len(commands)

    # === Single Command Logic ===
    if n_commands == 1:
        command = commands[0]
        is_stateful = is_stateful_command(command)
        is_risky = is_risky_command(command)

        # --- Insert Risk Assessment Here if is_risky ---
        if is_risky:
            risk_explanation = _get_ai_risk_assessment(command, console, provider)
            console.print(Panel(
                Text(risk_explanation, style="yellow"),
                title="[bold red]AI Risk Assessment[/bold red]",
                border_style="red",
                expand=False
            ))

        # A. Handle eval_mode pathway STRICTLY first.
        if eval_mode:
            # --- Insert Risk Assessment Here if is_risky ---
            # Note: Assessment must print to stderr in eval_mode
            if is_risky:
                # Get provider if not already loaded (might be loaded at function start)
                if 'provider' not in locals() or not provider:
                    provider = get_provider(load_config().get("default_provider", ""))

                risk_explanation = "Risk assessment skipped (no provider)."
                if provider:
                     risk_explanation = _get_ai_risk_assessment(command, console, provider)

                # Print panel directly to stderr for eval_mode visibility
                # Create a temporary console writing to stderr for the panel
                stderr_console = Console(file=sys.stderr)
                stderr_console.print(Panel(
                    Text(risk_explanation, style="yellow"),
                    title="[bold red]AI Risk Assessment[/bold red]",
                    border_style="red",
                    expand=False
                ))

            # A.1 Auto-confirm non-risky commands if -y is used IN eval_mode
            if auto_confirm and not is_risky:
                print(command) # Output command to stdout for shell function to eval
                sys.exit(0) # Exit successfully after printing command

            # A.2 Otherwise, prompt for confirmation (to stderr)
            if is_risky:
                confirm_msg, default_choice = "Execute? [y/N]: ", "n"
            else: # Not risky, but -y was not used
                confirm_msg, default_choice = "Execute? [Y/n]: ", "y"
            style = "yellow" if is_risky else "green"
            # Print prompt to stderr so it's visible but not captured by shell eval
            print(confirm_msg, end="", file=sys.stderr); sys.stderr.flush()
            choice = input().lower() or default_choice # Read choice from stdin

            if choice == "y":
                print(command) # Output command to stdout for shell function to eval
                sys.exit(0) # Exit successfully after printing command
            else:
                print("[Cancelled]", file=sys.stderr) # Notify user on stderr
                sys.exit(1) # Exit with error if cancelled IN eval_mode to signal failure

        # B. Handle NON-eval_mode pathway (covers interactive `ai` and `ai --chat`)
        # This block is only reached if eval_mode is False.
        elif is_stateful: # Check if the command is stateful
            # B.1 Prompt user to copy the stateful command
            prompt_text = (
                f"[STATEFUL COMMAND] '{command}' changes shell state. "
                "Copy to clipboard? [Y/n]: " # Standard clipboard prompt
            )
            console.print(Text(prompt_text, style="yellow bold"), end="")
            choice = input().lower()
            if choice != 'n': # Default to yes (copy)
                copy_to_clipboard(command)
                console.print("[green]Command copied to clipboard. Paste and run manually.[/green]")
            # We do NOT exit here in interactive mode; just return to the interactive loop
            # or let the main script exit if it was a single (non-chat) interaction.
            return

        else: # C. Handle NON-eval_mode and NON-stateful command
            # --- Risk Assessment already displayed above if is_risky ---
            # C.1 Auto-confirm non-risky if -y was used (only relevant if called non-interactively without eval)
            if auto_confirm and not is_risky:
                console.print(f"[green]Auto-executing: {command}[/green]")
                run_command(command)
                return

            # C.2 Regular confirmation prompt for direct execution
            # Default N if risky, Y otherwise
            default_choice_c = "n" if is_risky else "y"
            prompt_style_c = "red bold" if is_risky else "green"
            confirm_msg_c = f"Execute '{command}'? [{color_bold_green}Y{color_reset}/{color_bold_yellow}N{color_reset}]: " # Simplified prompt for single non-eval non-stateful
            console.print(Text(confirm_msg_c, style=prompt_style_c), end="")
            choice_c = input().lower() or default_choice_c
            if choice_c == "y":
                    run_command(command) # Execute using subprocess
            else:
                 console.print("[Cancelled]")
            return # Return after single non-eval command processed or cancelled

    # === Multiple Command Logic ===
    else:
        cmd_list = []
        for i, cmd_text_item in enumerate(commands, 1): # Renamed cmd to cmd_text_item
            is_risky_cmd = is_risky_command(cmd_text_item)
            is_stateful_cmd = is_stateful_command(cmd_text_item)
            cmd_display_text = f"[cyan]{i}[/cyan]: [white]{cmd_text_item}[/white]" # Renamed cmd_text to cmd_display_text
            if is_risky_cmd:
                cmd_display_text += " [bold red][RISKY][/bold red]"
            if is_stateful_cmd:
                cmd_display_text += " [bold yellow][STATEFUL][/bold yellow]"
            cmd_list.append(cmd_display_text)
        console.print(Panel(
            "\n".join(cmd_list),
            title=f"Found {n_commands} commands",
            border_style="blue"
        ))
        # Prompt to stderr if in eval_mode, otherwise use console (respecting rich_to_stderr)
        prompt_message = "Enter command number, 'a' for all, or 'q' to quit: "
        if eval_mode:
            print(prompt_message, end="", file=sys.stderr)
            sys.stderr.flush()
        else:
            console.print(Text(prompt_message, style="bold cyan"), end="")
        choice = input().lower()

        if choice == "q":
            if eval_mode:
                print("[Cancelled]", file=sys.stderr)
                sys.exit(1) # Signal cancellation in eval_mode
            return

        elif choice == "a":
            if eval_mode:
                cmds_to_eval = []
                confirm_remaining_non_risky = False
                for i, cmd_item in enumerate(commands):
                    item_is_risky = is_risky_command(cmd_item)
                    item_is_stateful = is_stateful_command(cmd_item)

                    # --- Insert Risk Assessment Here if is_risky ---
                    # Needs to print to stderr
                    if item_is_risky:
                        # Provider should be loaded at function start
                        risk_explanation = "Risk assessment skipped (no provider)."
                        if provider: # Check if provider was successfully loaded
                             risk_explanation = _get_ai_risk_assessment(cmd_item, console, provider)

                        stderr_console = Console(file=sys.stderr)
                        stderr_console.print(Panel(
                            Text(risk_explanation, style="yellow"),
                            title="[bold red]AI Risk Assessment[/bold red]",
                            border_style="red",
                            expand=False
                        ))

                    # If 'Yes to All' was chosen and current cmd is not risky, auto-confirm
                    if confirm_remaining_non_risky and not item_is_risky:
                        cmds_to_eval.append(cmd_item)
                        print(f"[Auto-confirmed (A): {cmd_item}]", file=sys.stderr)
                        continue

                    # Auto-confirm non-risky if -y is used (and not already handled by confirm_remaining)
                    if auto_confirm and not item_is_risky:
                        cmds_to_eval.append(cmd_item)
                        print(f"[Auto-confirmed (-y): {cmd_item}]", file=sys.stderr)
                        continue

                    # --- Prompting logic starts here ---
                    prompt_parts = [f"Cmd {i+1}/{len(commands)} ('{cmd_item}'):"]
                    if item_is_risky: prompt_parts.append(" [RISKY]")
                    if item_is_stateful: prompt_parts.append(" [STATEFUL]")
                    if confirm_remaining_non_risky: prompt_parts.append(" ['A' previously selected]") # Indicate 'A' status

                    prompt_base = "".join(prompt_parts) + " Execute? "
                    options_text = (
                        f"{color_dim}[{color_reset}{color_bold_green}Y{color_reset}{color_dim}]{color_reset}es {color_dim}/{color_reset} "
                        f"{color_dim}[{color_reset}{color_bold_yellow}N{color_reset}{color_dim}]{color_reset}o {color_dim}/{color_reset} "
                        f"{color_dim}[{color_reset}{color_bold_cyan}A{color_reset}{color_dim}]{color_reset}ll remaining non-risky {color_dim}/{color_reset} " # Added 'A' option
                        f"{color_dim}[{color_reset}{color_bold_red}Q{color_reset}{color_dim}]{color_reset}uit: " # Changed to Q/Quit
                    )

                    if item_is_risky:
                        # Default N for risky commands
                        # Note: 'A' behaves like 'y' for the *current* risky command if selected.
                        prompt_formatted = prompt_base + options_text
                        default_choice_a = "n"
                    else:
                        # Default Y for non-risky commands
                        prompt_formatted = prompt_base + options_text
                        default_choice_a = "y"

                    print(prompt_formatted, end="", file=sys.stderr); sys.stderr.flush()
                    # Read choice - strip whitespace and take the first char if multiple entered
                    raw_choice = input().strip()
                    subchoice_a = (raw_choice[0].lower() if raw_choice else "") or default_choice_a

                    if subchoice_a == 'y' or subchoice_a == 'a': # Treat 'a' as 'y' for the current one
                        cmds_to_eval.append(cmd_item)
                        if subchoice_a == 'a':
                            confirm_remaining_non_risky = True # Set flag for subsequent loops
                    elif subchoice_a == 'q':
                        print("[Quit All]", file=sys.stderr)
                        # Exit with error only if *no* commands were confirmed before quitting
                        exit_code = 1 if not cmds_to_eval else 0
                        if cmds_to_eval:
                           print("\n".join(cmds_to_eval)) # Output confirmed commands before quitting
                        sys.exit(exit_code)
                    else: # 'n' or other invalid input defaults to skip
                        print(f"[Skipped cmd: {cmd_item}]", file=sys.stderr)

                # After loop completes
                if cmds_to_eval:
                    print("\n".join(cmds_to_eval))
                    sys.exit(0)
            else: # Not eval_mode, for 'a'
                # Loop through commands for non-eval 'a'
                for i, cmd_val_non_eval in enumerate(commands):
                    is_stateful_cmd_val = is_stateful_command(cmd_val_non_eval)
                    is_risky_cmd_val = is_risky_command(cmd_val_non_eval)

                    # --- Insert Risk Assessment Here if is_risky_cmd_val ---
                    if is_risky_cmd_val:
                        # Provider should be loaded at function start
                        risk_explanation = "Risk assessment skipped (no provider)."
                        if provider: # Check if provider was successfully loaded
                             risk_explanation = _get_ai_risk_assessment(cmd_val_non_eval, console, provider)

                        console.print(Panel(
                            Text(risk_explanation, style="yellow"),
                            title="[bold red]AI Risk Assessment[/bold red]",
                            border_style="red",
                            expand=False
                        ))

                    # --- Existing non-eval 'a' logic follows ---
                    if is_stateful_cmd_val:
                        prompt_text = (
                            f"[STATEFUL COMMAND] '{cmd_val_non_eval}' changes shell state. "
                            "Copy to clipboard? [Y/n]: "
                        )
                        console.print(Text(prompt_text, style="yellow bold"), end="")
                        subchoice = input().lower()
                        if subchoice.lower() != "n":
                            copy_to_clipboard(cmd_val_non_eval)
                            console.print("[green]Command copied to clipboard. Paste and run manually.[/green]")
                    else: # Not stateful, not eval_mode, in 'a'
                        if auto_confirm and not is_risky_cmd_val:
                            console.print(f"[green]Auto-executing: {cmd_val_non_eval}[/green]")
                            run_command(cmd_val_non_eval)
                        elif is_risky_cmd_val:
                            console.print(Text(f"[RISKY] Execute risky command '{cmd_val_non_eval}'? [y/N]: ", style="red bold"), end="")
                            subchoice = input().lower()
                            if subchoice == "y":
                                run_command(cmd_val_non_eval)
                            else:
                                console.print(f"[Skipped: {cmd_val_non_eval}]")
                        else: # Not risky, not auto_confirm
                            console.print(Text(f"Execute command '{cmd_val_non_eval}'? [Y/n]: ", style="green"), end="")
                            subchoice = input().lower() or "y"
                            if subchoice == "y":
                                run_command(cmd_val_non_eval)
                            else:
                                console.print(f"[Skipped: {cmd_val_non_eval}]")
                return # Return after processing 'a' in non-eval mode

        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(commands):
                cmd = commands[idx]
                is_cmd_risky = is_risky_command(cmd)
                is_cmd_stateful = is_stateful_command(cmd)

                # --- Insert Risk Assessment Here if is_cmd_risky ---
                if is_cmd_risky:
                    # Provider should be loaded at function start
                    risk_explanation = "Risk assessment skipped (no provider)."
                    if provider: # Check if provider was successfully loaded
                         risk_explanation = _get_ai_risk_assessment(cmd, console, provider)

                    # Print to stderr if in eval_mode
                    if eval_mode:
                        stderr_console = Console(file=sys.stderr)
                        stderr_console.print(Panel(
                            Text(risk_explanation, style="yellow"),
                            title="[bold red]AI Risk Assessment[/bold red]",
                            border_style="red",
                            expand=False
                        ))
                    else:
                        console.print(Panel(
                            Text(risk_explanation, style="yellow"),
                            title="[bold red]AI Risk Assessment[/bold red]",
                            border_style="red",
                            expand=False
                        ))

                # --- Existing numbered choice logic follows ---
                if eval_mode:
                    # In eval_mode, all prompts to stderr, command to stdout, then exit.
                    if auto_confirm and not is_cmd_risky: # Applies to both stateful and non-stateful
                        print(cmd) # Auto-confirmed non-risky command
                        sys.exit(0)
                    else:
                        # Needs confirmation (either risky, or not auto_confirm)
                        prompt_parts = []
                        if is_cmd_risky: prompt_parts.append("[RISKY]")
                        if is_cmd_stateful: prompt_parts.append("[STATEFUL COMMAND]")

                        base_prompt = "".join(prompt_parts) + f" Execute command '{cmd}'?"
                        if is_cmd_risky:
                            confirm_prompt_text, default_choice_num = base_prompt + " [y/N]: ", "n"
                        else: # Not risky (but needs confirmation, so -y not used or it's stateful)
                            confirm_prompt_text, default_choice_num = base_prompt + " [Y/n]: ", "y"

                        print(confirm_prompt_text, end="", file=sys.stderr); sys.stderr.flush()
                        subchoice_num = input().lower() or default_choice_num

                        if subchoice_num == "y":
                            print(cmd)
                            sys.exit(0)
                        else:
                            print("[Cancelled]", file=sys.stderr)
                            sys.exit(1)
                else: # Not eval_mode (interactive, direct query without shell integration)
                    if is_cmd_stateful:
                        prompt_text_ne = (
                            f"[STATEFUL COMMAND] '{cmd}' changes shell state. "
                            "Copy to clipboard? [Y/n]: "
                        )
                        console.print(Text(prompt_text_ne, style="yellow bold"), end="")
                        subchoice_ne = input().lower()
                        if subchoice_ne.lower() != "n":
                            copy_to_clipboard(cmd)
                            console.print("[green]Command copied to clipboard. Paste and run manually.[/green]")
                    else: # Not stateful, not eval_mode
                        if auto_confirm and not is_cmd_risky:
                            console.print(f"[green]Auto-executing: {cmd}[/green]")
                            run_command(cmd)
                        else:
                            if is_cmd_risky:
                                console.print(Text(f"[RISKY] Execute command '{cmd}'? [y/N]: ", style="red bold"), end="")
                                default_choice_ne_r = "n"
                            else:
                                console.print(Text(f"Execute command '{cmd}'? [Y/n]: ", style="green"), end="")
                                default_choice_ne_r = "y"
                            subchoice_ne_r = input().lower() or default_choice_ne_r
                            if subchoice_ne_r == "y":
                                run_command(cmd)
                            else:
                                console.print("[Cancelled]")
            else: # Invalid index
                # Use console for this error message as it could be non-eval mode
                console.print(f"[red]Invalid choice: {choice}[/red]")

            # After handling a numbered choice (or invalid), return from handle_commands.
            # If eval_mode, sys.exit would have occurred. If not eval_mode, this return is correct.
            return

    # Fallback for single command logic - This section should not be reached if n_commands > 1 handled above.
    # The original single command logic remains below this multi-command block.
    # However, the original code had some single command logic duplicated *after* the multi-command block.
    # That needs to be reviewed to ensure it's not dead code or causing issues.
    # For now, assuming the multi-command block correctly returns or exits.

    # The following block seems to be a duplicate or misplaced version of single command logic.
    # It should ideally be part of the `if n_commands == 1:` block or removed if redundant.
    # Given the structure, if n_commands > 1, the function should have returned or exited within the 'else' block above.
    # Thus, this bottom part is likely only reachable if n_commands == 1, but that's handled at the top.
    # This looks like leftover code. I will remove it to prevent confusion.
    # --- Start of potentially redundant block to remove ---
    # command = commands[0]
    # is_stateful = is_stateful_command(command)
    # is_risky = is_risky_command(command)
    # if eval_mode or shell_integration_active: # This condition is too broad if shell_integration_active but not eval_mode
    # ... (rest of this block)
    # --- End of potentially redundant block ---
    return # Should be a clear return if not exited for eval_mode.

def run_command(command):
    """Execute a shell command with error handling."""
    console = Console()

    if not command:
        return

    if not is_shell_command(command):
        console.print(f"[yellow]Warning: '{command}' doesn't look like a valid shell command.[/yellow]")
        console.print("[yellow]Execute anyway? [y/N]:[/yellow]", end=" ")
        choice = input().lower()
        if choice != "y":
            return

    console.print(Panel(f"[bold white]Executing: [/bold white][cyan]{command}[/cyan]",
                       border_style="green",
                       title="Command Execution",
                       title_align="left"))

    success = run_shell_command(command)
    if not success:
        console.print(f"[bold red]Command failed: {command}[/bold red]")

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

            response = provider.generate_response(query, system_context, verbose=False)

            # Clear the thinking indicator with a visual separator
            console.print(Rule(style="dim"))

            print_ai_answer_with_rich(response)

            # Extract and handle commands from the response, limiting to max 3 commands
            # to avoid overwhelming the user in interactive mode
            commands = get_commands_interactive(response, max_commands=3)

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
    config = load_config()
    pname = 'ollama' # We are specifically configuring Ollama here

    if pname not in config['providers']:
        config['providers'][pname] = {} # Ensure ollama provider entry exists

    # Configure Ollama Host (can be part of this, or assumed to be set)
    current_host = config['providers'][pname].get('host', 'http://localhost:11434')
    console.print(f"Current Ollama host: {current_host}")
    ollama_host_prompt = (
        "Enter Ollama host (leave blank to keep current, e.g., http://localhost:11434): "
    )
    new_host_input = console.input(ollama_host_prompt).strip()
    host_to_use = current_host
    if new_host_input:
        config['providers'][pname]['host'] = new_host_input
        host_to_use = new_host_input
        console.print("[bold green]Ollama host updated.[/bold green]")
    else:
        console.print("[yellow]Ollama host unchanged.[/yellow]")

    # Configure Ollama Model
    current_model = config['providers'][pname].get('model', 'llama3') 
    console.print(f"Current Ollama model: {current_model}")
    
    available_models = []
    try:
        tags_url = f"{host_to_use}/api/tags"
        console.print(f"[dim]Fetching models from {tags_url}...[/dim]")
        response = requests.get(tags_url, timeout=5)
        response.raise_for_status()
        models_data = response.json().get("models", [])
        if models_data:
            available_models = [m.get("name") for m in models_data if m.get("name")]
        
        if available_models:
            console.print("[bold]Available Ollama models:[/bold]")
            for i, model_name_option in enumerate(available_models, 1):
                console.print(f"  [bold yellow]{i}[/bold yellow]. {model_name_option}")
            
            model_choice_prompt = (
                "[bold green]Choose a model number, or enter a model name directly: [/bold green]"
            )
            model_sel = console.input(model_choice_prompt).strip()
            
            selected_model_name = ""
            if model_sel.isdigit() and 1 <= int(model_sel) <= len(available_models):
                selected_model_name = available_models[int(model_sel)-1]
            elif model_sel: 
                selected_model_name = model_sel
            
            if selected_model_name:
                config['providers'][pname]['model'] = selected_model_name
                console.print(f"[bold green]Ollama model set to: {selected_model_name}[/bold green]")
            else:
                console.print("[yellow]No model selected/entered. Model remains: {current_model}[/yellow]")
        else:
            console.print("[yellow]No models found via Ollama API or API not reachable at {host_to_use}.[/yellow]")
            console.print("[yellow]You can still enter a model name manually.[/yellow]")
            manual_model_prompt = f"Enter Ollama model name (e.g., mistral:latest, current: {current_model}): "
            manual_model_input = console.input(manual_model_prompt).strip()
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
        manual_model_input_on_error = console.input(manual_model_prompt_on_error).strip()
        if manual_model_input_on_error:
            config['providers'][pname]['model'] = manual_model_input_on_error
            console.print(f"[bold green]Ollama model set to: {manual_model_input_on_error}[/bold green]")
        else:
            console.print(f"[yellow]No model entered. Model remains: {current_model}[/yellow]")
    
    save_config(config)
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
