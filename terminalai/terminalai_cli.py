"""Main CLI for TerminalAI.

Best practice: Run this script as a module from the project root:
    python -m terminalai.terminalai_cli
This ensures all imports work correctly. If you run this file directly, you may get import errors.
"""
import sys
import requests
from terminalai.__init__ import __version__
from terminalai.config import load_config
from terminalai.ai_providers import get_provider
from terminalai.command_extraction import extract_commands
from terminalai.formatting import print_ai_answer_with_rich
from terminalai.shell_integration import get_system_context
from terminalai.cli_interaction import (
    parse_args, handle_commands, interactive_mode, setup_wizard
)
from terminalai.color_utils import colorize_command

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    print("[WARNING] It is recommended to run this script as a module:")
    print("    python -m terminalai.terminalai_cli")
    print("Otherwise, you may get import errors.")

def main():
    """Main entry point for the TerminalAI CLI."""
    args = parse_args()

    # Check for version flag
    if args.version:
        print(f"TerminalAI version {__version__}")
        sys.exit(0)

    # Check for setup flag
    if args.setup:
        setup_wizard()
        sys.exit(0)

    # Load configuration
    config = load_config()

    # Check if AI provider is configured
    provider_name = config.get("default_provider", "")
    if not provider_name:
        print(colorize_command("No AI provider configured. Running setup wizard..."))
        setup_wizard()
        sys.exit(0)

    # Run in interactive mode if no query provided
    if not args.query:
        interactive_mode()
        sys.exit(0)

    # Get AI provider
    provider = get_provider(provider_name)
    if not provider:
        print(colorize_command(f"Error: Provider '{provider_name}' is not configured properly."))
        print(colorize_command("Please run 'ai setup' to configure an AI provider."))
        sys.exit(1)

    # Get system context
    system_context = get_system_context()

    # Adjust system context for verbosity/length if requested
    if args.verbose:
        system_context = system_context + "\nPlease provide a detailed response with thorough explanation."
    if args.long:
        system_context = system_context + "\nPlease provide a comprehensive, in-depth response covering all relevant aspects."

    # Generate response
    try:
        # Ensure args.query is a string, not a list
        user_query = args.query
        response = provider.generate_response(user_query, system_context, verbose=args.verbose or args.long)
    except (ValueError, TypeError, ConnectionError, requests.RequestException) as e:
        print(colorize_command(f"Error from AI provider: {str(e)}"))
        sys.exit(1)

    # Format and print response
    print_ai_answer_with_rich(response)

    # Extract and handle commands from the response
    commands = extract_commands(response)
    if commands:
        handle_commands(commands, auto_confirm=args.yes)

if __name__ == "__main__":
    main()
