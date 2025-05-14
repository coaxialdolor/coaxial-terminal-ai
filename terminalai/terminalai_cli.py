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
from terminalai.file_reader import read_project_file

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
    # rich_output_to_stderr = args.eval_mode # Key decision: Rich AI explanations to stderr in eval_mode # REMOVED

    console = Console() # Default console for general script output not handled by specific functions

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

    # Run in interactive mode if no query provided AND no --explain flag AND no --read-file flag, or if chat explicitly requested
    is_chat_request = getattr(args, 'chat', False) or sys.argv[0].endswith('ai-c')
    if (not args.query and not args.explain and not args.read_file) or is_chat_request:
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
    final_system_context = system_context # Start with base system context
    user_query = args.query # Initialize user_query from args

    file_content_for_prompt = None # Initialize

    if hasattr(args, 'explain') and args.explain:
        file_path_to_read = args.explain
        content, error, context = read_project_file(file_path_to_read, cwd)
        if error:
            print(colorize_command(error))
            sys.exit(1)
        if content is None:
            print(colorize_command(f"Error: Could not read file '{file_path_to_read}'. An unknown issue occurred."))
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

Please process the request which is to summarize this file, explain its likely purpose, and describe its context within the file system. If relevant, also identify any other files or modules it appears to reference or interact with."""
        )

    elif hasattr(args, 'read_file') and args.read_file:
        file_path_to_read = args.read_file
        content, error, context = read_project_file(file_path_to_read, cwd)
        if error:
            print(colorize_command(error))
            sys.exit(1)
        if content is None:
            print(colorize_command(f"Error: Could not read file '{file_path_to_read}'. An unknown issue occurred."))
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
            f"They have provided the content of the file: '{file_path_to_read}' (absolute path: '{abs_file_path}').\n"
            f"{context_info}\n"
            f"Their query related to this file is: '{user_query}'.\n\n"
            f"File Content:\n"
            f"-------------------------------------------------------\n"
            f"{file_content_for_prompt}\n"
            f"-------------------------------------------------------\n\n"
            f"Based on the file content and the user's query, please provide an explanation or perform the requested task. "
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

        response = provider.generate_response(
            user_query, final_system_context, verbose=args.verbose or args.long
        )
    except (ValueError, TypeError, ConnectionError, requests.RequestException) as e:
        print(colorize_command(f"Error from AI provider: {str(e)}"))
        sys.exit(1)

    # Format and print response
    # rich_to_stderr = getattr(args, 'eval_mode', False) # REMOVED

    # console_for_direct determines where the "AI:(model)>" prompt for direct queries goes.
    # Since eval_mode is removed, this can now consistently go to stdout.
    console_for_direct = Console(force_terminal=True) # Defaults to stdout
    
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
    # to_stderr argument is removed, print_ai_answer_with_rich defaults to stdout.
    print_ai_answer_with_rich(cleaned_response)

    # Extract and handle commands from the response
    commands = extract_commands_from_output(response)
    if commands:
        handle_commands(
            commands,
            auto_confirm=args.yes
            # eval_mode and rich_to_stderr parameters are removed from handle_commands
        )

    # If not a direct query, and not setup, and not chat mode, it's single interaction
    elif not args.setup and not args.chat and not args.set_default and not args.set_ollama:
        interactive_mode(chat_mode=False) # Single interaction then exit

if __name__ == "__main__":
    main()
