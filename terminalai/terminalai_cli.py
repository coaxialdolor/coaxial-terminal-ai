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
    parse_args, handle_commands, interactive_mode, setup_wizard
)
from terminalai.color_utils import colorize_command
from terminalai.file_reader import read_project_file

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

    # Check for setup flag or "setup" command
    if args.setup:
        setup_wizard()
        sys.exit(0)

    # Check if first argument is "setup" (positional argument)
    if args.query and args.query == "setup":
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

    # Run in interactive mode if no query provided AND no --explain flag AND no --read-file flag, or if chat explicitly requested
    is_chat_request = getattr(args, 'chat', False) or sys.argv[0].endswith('ai-c')
    if (not args.query and not args.explain and not args.read_file) or is_chat_request:
        interactive_mode(chat_mode=is_chat_request)
        sys.exit(0)

    # Get AI provider
    provider = get_provider(provider_name)
    if not provider:
        print(colorize_command(f"Error: Provider '{provider_name}' is not configured properly."))
        print(colorize_command("Please run 'ai setup' to configure an AI provider."))
        sys.exit(1)

    # Get system context
    system_context = get_system_context()
    # Add current working directory to context
    cwd = os.getcwd()
    final_system_context = system_context # Start with base system context
    user_query = args.query # Initialize user_query from args

    file_content_for_prompt = None # Initialize

    if hasattr(args, 'explain') and args.explain:
        file_path_to_read = args.explain
        content, error = read_project_file(file_path_to_read, cwd)
        if error:
            print(colorize_command(error))
            sys.exit(1)
        if content is None:
            print(colorize_command(f"Error: Could not read file '{file_path_to_read}'. An unknown issue occurred."))
            sys.exit(1)

        file_content_for_prompt = content
        abs_file_path = os.path.abspath(os.path.join(cwd, file_path_to_read))

        # For --explain, the user_query becomes the predefined explanation query
        user_query = (
            f"The user wants an explanation of the file '{file_path_to_read}' (absolute path: '{abs_file_path}') "
            f"located in their current working directory '{cwd}'. "
            f"Please summarize this file, explain its likely purpose, and describe its context within a typical project structure found in this directory. "
            f"If relevant, also identify any other files or modules it appears to reference or interact with."
        )

        # The system context includes the file content and instructions
        final_system_context = (
            f"""You are assisting a user who wants to understand a file. Their current working directory is '{cwd}'.
The file in question is '{file_path_to_read}' (absolute path: '{abs_file_path}').
File Content of '{file_path_to_read}':
-------------------------------------------------------
{file_content_for_prompt}
-------------------------------------------------------

Please process the request which is to summarize this file, explain its likely purpose, and describe its context within a typical project structure. If relevant, also identify any other files or modules it appears to reference or interact with."""
        )

    elif hasattr(args, 'read_file') and args.read_file: # Ensure this is elif
        file_path_to_read = args.read_file
        content, error = read_project_file(file_path_to_read, cwd)
        if error:
            print(colorize_command(error))
            sys.exit(1)
        if content is None:
            print(colorize_command(f"Error: Could not read file '{file_path_to_read}'. An unknown issue occurred."))
            sys.exit(1)

        file_content_for_prompt = content
        abs_file_path = os.path.abspath(os.path.join(cwd, file_path_to_read))

        # For --read-file, user_query is the original user query.
        # The system context includes file content and guides the AI to use it for the user's query.
        final_system_context = (
            f"The user is in the directory: {cwd}.\n"
            f"They have provided the content of the file: '{file_path_to_read}' (absolute path: '{abs_file_path}').\n"
            f"Their query related to this file is: '{user_query}'.\n\n"
            f"File Content:\n"
            f"-------------------------------------------------------\n"
            f"{file_content_for_prompt}\n"
            f"-------------------------------------------------------\n\n"
            f"Based on the file content and the user's query, please provide an explanation or perform the requested task. "
            f"If relevant, identify any other files or modules it appears to reference or interact with, "
            f"considering standard import statements or common patterns for its file type. "
            f"Focus on its role within a typical project structure if it seems to be part of a larger application in '{cwd}'."
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

        response = provider.generate_response(
            user_query, final_system_context, verbose=args.verbose or args.long
        )
    except (ValueError, TypeError, ConnectionError, requests.RequestException) as e:
        print(colorize_command(f"Error from AI provider: {str(e)}"))
        sys.exit(1)

    # Format and print response
    rich_to_stderr = getattr(args, 'eval_mode', False)
    print_ai_answer_with_rich(response, to_stderr=rich_to_stderr)

    # Extract and handle commands from the response
    commands = extract_commands_from_output(response)
    if commands:
        handle_commands(
            commands,
            auto_confirm=args.yes,
            eval_mode=getattr(args, 'eval_mode', False),
            rich_to_stderr=rich_to_stderr
        )

if __name__ == "__main__":
    main()
