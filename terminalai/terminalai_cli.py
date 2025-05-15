"""Main CLI for TerminalAI.

Best practice: Run this script as a module from the project root:
    python -m terminalai.terminalai_cli
This ensures all imports work correctly. If you run this file directly, you may get import errors.
"""
import os
import sys

import requests
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from terminalai.__init__ import __version__
from terminalai.ai_providers import get_provider
from terminalai.cli_interaction import (
    parse_args, handle_commands, interactive_mode, setup_wizard,
    _set_default_provider_interactive,
    _set_ollama_model_interactive
)
from terminalai.color_utils import colorize_command
from terminalai.command_extraction import extract_commands_from_output, is_stateful_command, is_risky_command
from terminalai.config import load_config
from terminalai.file_reader import read_project_file
from terminalai.formatting import print_ai_answer_with_rich
from terminalai.query_utils import preprocess_query
from terminalai.shell_integration import get_system_context

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    print("[WARNING] It is recommended to run this script as a module:")
    print("    python -m terminalai.terminalai_cli")
    print("Otherwise, you may get import errors.")

def main():
    """Main entry point for the TerminalAI CLI."""
    # --- Argument Parsing and Initial Setup ---
    args = parse_args()

    # Initialize user_query to prevent UnboundLocalError
    user_query = None

    # Check if we're in eval mode (used by shell integration)
    is_eval_mode = getattr(args, 'eval_mode', False)
    rich_output_to_stderr = is_eval_mode

    # In eval mode, all rich output goes to stderr, and only the raw command goes to stdout
    console = Console(file=sys.stderr if rich_output_to_stderr else None)

    # --- Main Logic Based on Arguments ---
    if args.version:
        console.print(f"TerminalAI version {__version__}")
        sys.exit(0)

    # Check for setup flag or "setup" command
    if args.setup:
        setup_wizard()
        sys.exit(0)

    # Handle --set-default flag
    if args.set_default:
        _set_default_provider_interactive(console)
        sys.exit(0)

    # Handle --set-ollama flag
    if args.set_ollama:
        _set_ollama_model_interactive(console)
        sys.exit(0)

    # Check if first argument is "setup" (positional argument)
    if args.query and args.query == "setup":
        setup_wizard()
        sys.exit(0)

    # Load configuration
    config = load_config()

    # Determine provider: override > config > setup prompt
    provider_to_use = None
    if args.provider: # Check for command-line override first
        provider_to_use = args.provider
    else:
        provider_to_use = config.get("default_provider", "")

    if not provider_to_use:
        print(colorize_command("No AI provider configured. Running setup wizard..."), file=sys.stderr)
        setup_wizard() # This will allow user to set a default
        # After setup, try to load config again or exit if user quit setup
        config = load_config()
        provider_to_use = config.get("default_provider", "")
        if not provider_to_use:
            print(colorize_command("Setup was not completed. Exiting."), file=sys.stderr)
            sys.exit(1)

    # Determine mode: interactive vs direct query
    is_interactive_mode = args.query is None

    # Handle interactive mode (chat or regular)
    if is_interactive_mode:
        if args.chat:
            interactive_mode(chat_mode=True)
        elif args.auto:
            interactive_mode(chat_mode=True, auto_mode=True)
        else:
            interactive_mode(chat_mode=False)
        # interactive_mode handles its own exit, so we shouldn't reach here
        sys.exit(0)
    # For direct query mode, proceed with the rest of the function
    else:
        # We have a query, so we're in direct query mode
        user_query = args.query

    # Get AI provider instance
    provider = get_provider(provider_to_use) # Use the determined provider_to_use
    if not provider:
        error_msg = f"Error: Provider '{provider_to_use}' is not configured properly or is unknown."
        print(colorize_command(error_msg), file=sys.stderr)
        setup_msg = "Please run 'ai setup' to configure an AI provider, or check the provider name."
        print(colorize_command(setup_msg), file=sys.stderr)
        sys.exit(1)

    # Get system context
    system_context = get_system_context()
    # Add current working directory to context
    cwd = os.getcwd()
    final_system_context = system_context # Start with base system context

    file_content_for_prompt = None # Initialize

    if hasattr(args, 'explain') and args.explain:
        file_path_to_read = args.explain
        content, error, context = read_project_file(file_path_to_read, cwd)
        if error:
            print(colorize_command(error), file=sys.stderr)
            sys.exit(1)
        if content is None:
            error_msg = f"Error: Could not read file '{file_path_to_read}'. An unknown issue occurred."
            print(colorize_command(error_msg), file=sys.stderr)
            sys.exit(1)

        file_content_for_prompt = content
        abs_file_path = os.path.abspath(os.path.join(cwd, file_path_to_read))

        # Build context information for the prompt
        context_info = ""
        if context:
            context_info = f"""
File Location and Context:
- File is located in: {context['parent_dir']}
- Sibling files in the same directory: {', '.join(context['sibling_files']) if context['sibling_files'] else 'None'}
- Files in parent directory: {', '.join(context['parent_dir_files']) if context['parent_dir_files'] else 'None'}
"""

        # For --explain, the user_query becomes the predefined explanation query
        user_query = (
            f"The user wants an explanation of the file '{file_path_to_read}' (absolute path: '{abs_file_path}') "
            f"located in their current working directory '{cwd}'. "
            f"Please summarize this file, explain its likely purpose, and describe its context within the file system. "
            f"If relevant, also identify any other files or modules it appears to reference or interact with."
        )

        # The system context includes the file content and instructions
        final_system_context = (
            f"""You are assisting a user who wants to understand a file. Their current working directory is '{cwd}'.
The file in question is '{file_path_to_read}' (absolute path: '{abs_file_path}').
{context_info}
File Content of '{file_path_to_read}':
-------------------------------------------------------
{file_content_for_prompt}
-------------------------------------------------------

"""
            f"""Please process the request which is to summarize this file, explain its likely purpose, """
            f"""and describe its context within the file system. If relevant, also identify any other """
            f"""files or modules it appears to reference or interact with."""
        )

    elif hasattr(args, 'read_file') and args.read_file:
        file_path_to_read = args.read_file
        content, error, context = read_project_file(file_path_to_read, cwd)
        if error:
            print(colorize_command(error), file=sys.stderr)
            sys.exit(1)
        if content is None:
            error_msg = f"Error: Could not read file '{file_path_to_read}'. An unknown issue occurred."
            print(colorize_command(error_msg), file=sys.stderr)
            sys.exit(1)

        file_content_for_prompt = content
        abs_file_path = os.path.abspath(os.path.join(cwd, file_path_to_read))

        # Build context information for the prompt
        context_info = ""
        if context:
            context_info = f"""
File Location and Context:
- File is located in: {context['parent_dir']}
- Sibling files in the same directory: {', '.join(context['sibling_files']) if context['sibling_files'] else 'None'}
- Files in parent directory: {', '.join(context['parent_dir_files']) if context['parent_dir_files'] else 'None'}
"""

        # For --read-file, user_query is the original user query.
        # The system context includes file content and guides the AI to use it for the user's query.
        final_system_context = (
            f"The user is in the directory: {cwd}.\n"
            f"They have provided the content of the file: '{file_path_to_read}' "
            f"(absolute path: '{abs_file_path}').\n"
            f"{context_info}\n"
            f"Their query related to this file is: '{user_query}'.\n\n"
            f"File Content:\n"
            f"-------------------------------------------------------\n"
            f"{file_content_for_prompt}\n"
            f"-------------------------------------------------------\n\n"
            f"Based on the file content and the user's query, please provide an explanation "
            f"or perform the requested task. "
            f"If relevant, identify any other files or modules it appears to reference or interact with, "
            f"considering standard import statements or common patterns for its file type. "
            f"Focus on its role within the file system and its relationship to other files in its directory."
        )
    else:
        # Original behavior if not reading a file, just add CWD to system_context
        final_system_context += f"\nThe user's current working directory is: {cwd}"

    # Adjust system context for verbosity/length if requested
    if args.verbose:
        final_system_context += (
            "\nPlease provide a detailed response with thorough explanation."
        )
    if args.long:
        final_system_context += (
            "\nPlease provide a comprehensive, in-depth response covering all relevant aspects."
        )

    # Generate response
    try:
        # Ensure user_query is a string before passing to provider.generate_response
        if user_query is None:
            user_query = "" # Default to empty string if None (e.g. if only --explain was used and no actual query text)

        # Preprocess query to clarify potentially ambiguous requests
        processed_query = preprocess_query(user_query)

        # Format and print response
        console_file = sys.stderr if rich_output_to_stderr else None
        force_term = bool(rich_output_to_stderr)
        console_for_direct = Console(
            file=console_file,
            force_terminal=force_term
        )
        console_for_direct.print()

        # Show clarification message if query was modified
        if processed_query != user_query:
            clarification_message = f"Note: Clarified your query to: \"{processed_query}\""
            console_for_direct.print(Panel(
                Text(clarification_message, style="cyan"),
                border_style="cyan",
                expand=False
            ))

        response = provider.generate_response(
            processed_query, final_system_context, verbose=args.verbose or args.long
        )
    except (ValueError, TypeError, ConnectionError, requests.RequestException) as e:
        print(colorize_command(f"Error from AI provider: {str(e)}"), file=sys.stderr)
        sys.exit(1)

    # Construct and print the display prompt for direct queries
    display_provider_for_direct_query = provider_to_use
    if provider_to_use == "ollama":
        ollama_model_for_direct = config.get("providers", {}).get("ollama", {}).get("model", "")
        if ollama_model_for_direct:
            display_provider_for_direct_query = f"ollama-{ollama_model_for_direct}"
        else:
            display_provider_for_direct_query = "ollama (model not set)"
    direct_query_prompt_text = Text()
    direct_query_prompt_text.append("AI:", style="bold cyan")
    direct_query_prompt_text.append("(", style="bold green")
    direct_query_prompt_text.append(display_provider_for_direct_query, style="bold green")
    direct_query_prompt_text.append(")", style="bold green")
    console_for_direct.print(direct_query_prompt_text)

    # The original response from the AI provider might start with "[AI] "
    cleaned_response = response
    if response.startswith("[AI] "):
        cleaned_response = response[len("[AI] ") :]
    # Check if we need to output to stderr (in eval mode)
    print_ai_answer_with_rich(cleaned_response, to_stderr=rich_output_to_stderr)

    # Extract and handle commands from the response
    commands = extract_commands_from_output(response)

    if commands:
        # In eval_mode (shell integration), we need special handling for commands
        if is_eval_mode and commands:
            # IMPORTANT: Do NOT auto-execute commands
            # Instead, handle commands normally but with special output handling

            # Print all explanations and prompts to stderr so they don't get executed
            auto_confirm = args.yes  # Only honor -y flag, ignore eval_mode for auto-confirm

            # Use a custom handling function for eval mode that will print the selected command to stdout
            # ONLY after user confirmation
            handle_eval_mode_commands(commands, auto_confirm=auto_confirm, auto_mode=args.auto)

            # After handling, exit without printing anything else to stdout
            sys.exit(0)

        # Normal mode (no shell integration)
        auto_confirm = args.yes
        handle_commands(
            commands,
            auto_confirm=auto_confirm,
            auto_mode=args.auto
        )

    # After handling a direct query, exit immediately. Do NOT call interactive_mode here.
    sys.exit(0)

def handle_eval_mode_commands(commands, auto_confirm=False, auto_mode=False):
    """Special handler for commands in eval mode (shell integration).

    In eval mode, we need to print the command ONLY to stdout (for shell execution)
    but ONLY after user confirmation. All other output goes to stderr.

    NOTE: Commands with shell operators (|, >, <, etc.) work correctly in this mode because
    the raw command string is printed directly to stdout, where it's evaluated by the shell.

    Args:
        commands: List of commands to handle
        auto_confirm: Whether to auto-confirm non-risky commands
        auto_mode: Whether to auto-execute non-risky commands in auto mode
    """
    if not commands:
        return

    # Create a console that writes to stderr for all prompts and info messages
    console = Console(file=sys.stderr)

    # For a single command
    if len(commands) == 1:
        command = commands[0]
        is_stateful = is_stateful_command(command)
        is_risky = is_risky_command(command)

        # Show command with appropriate styling
        console.print("\n[Suggested command]", style="bold green")
        console.print(Panel(Text(command, style="cyan bold"), border_style="green", expand=False))

        # If auto-confirm or auto mode is on and the command is not risky, execute without prompting
        if (auto_confirm or auto_mode) and not is_risky and not is_stateful:
            # Print the command to stdout for shell execution
            print(command)
            return

        # For stateful commands, always copy to clipboard (shell integration handles this)
        if is_stateful:
            console.print("[bold yellow]This command changes shell state and will be executed in your shell.[/bold yellow]")

        # Prompt with appropriate default based on command type
        default_choice = "n" if is_risky else "y"
        prompt_style = "red bold" if is_risky else "green"
        prompt_text = "[RISKY] " if is_risky else ""

        # Format yes/no options based on default choice
        yes_option = "Y" if default_choice == "y" else "y"
        no_option = "N" if default_choice == "n" else "n"
        yes_no_prompt = f"{yes_option}/{no_option}"

        console.print(
            f"[{prompt_style}]{prompt_text}Execute this command? [{yes_no_prompt}]:[/{prompt_style}] ",
            end=""
        )

        # Read from stdin (terminal input)
        try:
            choice = input().lower() or default_choice
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Command execution cancelled.[/yellow]")
            return

        if choice == "y":
            # Print the command to stdout for shell execution
            print(command)
        else:
            console.print("[yellow]Command execution cancelled.[/yellow]")

    # Multiple commands - auto mode with auto_mode=True would handle the same as auto_confirm
    else:
        # Display the list of commands
        cmd_list_display = []
        for i, cmd in enumerate(commands, 1):
            is_risky_item = is_risky_command(cmd)
            is_stateful_item = is_stateful_command(cmd)

            display_item = Text()
            display_item.append(f"{i}", style="cyan")
            display_item.append(f": {cmd}", style="white")
            if is_risky_item:
                display_item.append(" [RISKY]", style="bold red")
            if is_stateful_item:
                display_item.append(" [STATEFUL]", style="bold yellow")
            cmd_list_display.append(display_item)

        panel_content = Text("\n").join(cmd_list_display)
        console.print(Panel(panel_content, title=f"Found {len(commands)} commands", border_style="blue"))

        # Prompt for which command to execute
        console.print(Text("Enter command number, 'a' for all, or 'q' to quit: ", style="bold cyan"), end="")
        try:
            user_choice = input().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Command execution cancelled.[/yellow]")
            return

        if user_choice == "q":
            console.print("[yellow]Command execution cancelled.[/yellow]")
            return

        # Handle user selecting a specific command by number
        if user_choice.isdigit():
            idx = int(user_choice) - 1
            if 0 <= idx < len(commands):
                cmd_to_run = commands[idx]
                is_risky_item = is_risky_command(cmd_to_run)
                is_stateful_item = is_stateful_command(cmd_to_run)

                # Show selected command
                console.print(f"\n[Executing command {user_choice}]", style="bold green")
                console.print(Panel(Text(cmd_to_run, style="cyan bold"), border_style="green", expand=False))

                # For stateful commands in shell integration
                if is_stateful_item:
                    console.print(
                        "[bold yellow]This command changes shell state "
                        "and will be executed in your shell.[/bold yellow]"
                    )

                # Confirm execution for risky commands
                if is_risky_item:
                    console.print(Text("[RISKY] Execute this command? [y/N]: ", style="red bold"), end="")
                    try:
                        confirm = input().lower() or "n"
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[yellow]Command execution cancelled.[/yellow]")
                        return

                    if confirm != "y":
                        console.print("[yellow]Command execution cancelled.[/yellow]")
                        return

                # Print the selected command to stdout for shell execution
                print(cmd_to_run)
            else:
                console.print(f"[red]Invalid command number: {user_choice}[/red]")
        elif user_choice == "a":
            console.print("[yellow]All commands mode not supported in shell integration. Please select one command.[/yellow]")
        else:
            console.print(f"[red]Invalid choice: {user_choice}[/red]")

if __name__ == "__main__":
    main()
