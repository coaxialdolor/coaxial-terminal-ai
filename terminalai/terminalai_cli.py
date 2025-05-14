"""Main CLI for TerminalAI.

Best practice: Run this script as a module from the project root:
    python -m terminalai.terminalai_cli
This ensures all imports work correctly. If you run this file directly, you may get import errors.
"""
import os
import sys
import requests
from terminalai.__init__ import __version__
from terminalai.config import load_config
from terminalai.ai_providers import get_provider
from terminalai.command_extraction import extract_commands_from_output
from terminalai.formatting import print_ai_answer_with_rich
from terminalai.shell_integration import get_system_context
from terminalai.cli_interaction import (
    parse_args, handle_commands, interactive_mode, setup_wizard,
    _set_default_provider_interactive,
    _set_ollama_model_interactive
)
from terminalai.color_utils import colorize_command
from rich.console import Console
from rich.text import Text

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    print("[WARNING] It is recommended to run this script as a module:")
    print("    python -m terminalai.terminalai_cli")
    print("Otherwise, you may get import errors.")

def main():
    """Main entry point for the TerminalAI CLI."""
    # --- Argument Parsing and Initial Setup ---
    args = parse_args()

    # Setup console for rich output (can be changed later if needed, e.g., for eval_mode stderr)
    # If eval_mode is true, rich output should go to stderr.
    # The handle_commands function itself will manage its console for stderr/stdout.
    # Here, we set up a default console. If print_ai_answer_with_rich needs to go to stderr,
    # it should be handled there or by passing a stderr_console to it.
    # For now, main output (non-command, non-error) from direct query goes to stdout.
    rich_output_to_stderr = args.eval_mode # Key decision: Rich AI explanations to stderr in eval_mode

    console = Console(file=sys.stderr if rich_output_to_stderr else sys.stdout)

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
        print(colorize_command("No AI provider configured. Running setup wizard..."))
        setup_wizard() # This will allow user to set a default
        # After setup, try to load config again or exit if user quit setup
        config = load_config()
        provider_to_use = config.get("default_provider", "")
        if not provider_to_use:
            print(colorize_command("Setup was not completed. Exiting."))
            sys.exit(1)

    # Run in interactive mode if no query provided or chat explicitly requested
    # (and not a config shortcut command that would have exited earlier)
    is_chat_request = getattr(args, 'chat', False) or sys.argv[0].endswith('ai-c')
    if not args.query or is_chat_request:
        interactive_mode(chat_mode=is_chat_request)
        sys.exit(0)

    # Get AI provider instance
    provider = get_provider(provider_to_use) # Use the determined provider_to_use
    if not provider:
        print(colorize_command(f"Error: Provider '{provider_to_use}' is not configured properly or is unknown."))
        print(colorize_command("Please run 'ai setup' to configure an AI provider, or check the provider name."))
        sys.exit(1)

    # Get system context
    system_context = get_system_context()
    # Add current working directory to context
    cwd = os.getcwd()
    system_context += f"\nThe user's current working directory is: {cwd}"

    # Adjust system context for verbosity/length if requested
    if args.verbose:
        system_context += (
            "\nPlease provide a detailed response with thorough explanation."
        )
    if args.long:
        system_context += (
            "\nPlease provide a comprehensive, in-depth response covering all relevant aspects."
        )

    # Generate response
    try:
        # Ensure args.query is a string, not a list
        user_query = args.query
        response = provider.generate_response(
            user_query, system_context, verbose=args.verbose or args.long
        )
    except (ValueError, TypeError, ConnectionError, requests.RequestException) as e:
        print(colorize_command(f"Error from AI provider: {str(e)}"))
        sys.exit(1)

    # Format and print response
    rich_to_stderr = getattr(args, 'eval_mode', False)

    console_for_direct = Console(stderr=rich_to_stderr, force_terminal=True)
    
    # Print an empty line before the prompt for direct queries
    console_for_direct.print()

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
    # No space or > here, as the response will be on the next line.
    
    console_for_direct.print(direct_query_prompt_text)

    # The original response from the AI provider might start with "[AI] "
    cleaned_response = response
    if response.startswith("[AI] "):
        cleaned_response = response[len("[AI] "):]

    # Print the cleaned AI response (which will start on a new line)
    print_ai_answer_with_rich(cleaned_response, to_stderr=rich_to_stderr)

    # Extract and handle commands from the response
    commands = extract_commands_from_output(response)
    if commands:
        handle_commands(
            commands,
            auto_confirm=args.yes,
            eval_mode=getattr(args, 'eval_mode', False),
            rich_to_stderr=rich_to_stderr
        )

    # If not a direct query, and not setup, and not chat mode, it's single interaction
    elif not args.setup and not args.chat and not args.set_default and not args.set_ollama:
        interactive_mode(chat_mode=False) # Single interaction then exit

if __name__ == "__main__":
    main()
