"""CLI interaction functionality for TerminalAI."""
import sys
import argparse
from terminalai.color_utils import colorize_command
from terminalai.command_utils import run_shell_command, is_shell_command
from terminalai.command_extraction import extract_commands, is_stateful_command, is_risky_command
from terminalai.formatting import ColoredDescriptionFormatter
from terminalai.clipboard_utils import copy_to_clipboard

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TerminalAI: Your command-line AI assistant.\n"
                    "Ask questions or request commands, and AI will suggest appropriate actions.\n"
                    "Examples:\n"
                    "  ai \"how do I find all python files in this directory?\"\n"
                    "  ai \"create a temporary folder and move all txt files there\"\n"
                    "  ai setup",
        epilog="For more details, visit https://github.com/coaxialdolor/terminalai",
        formatter_class=ColoredDescriptionFormatter
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Your question or request"
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Automatically confirm execution of non-risky commands"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Request a more detailed response from the AI"
    )

    parser.add_argument(
        "-l", "--long",
        action="store_true",
        help="Request a longer, more comprehensive response"
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the setup wizard"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information"
    )

    return parser.parse_args()

def handle_commands(commands, auto_confirm=False):
    """Handle extracted commands, prompting the user and executing if confirmed."""
    if not commands:
        return

    n_commands = len(commands)

    if n_commands == 1:
        command = commands[0]

        # Check if it's a stateful command that changes shell state
        if is_stateful_command(command):
            print(colorize_command(
                f"[STATEFUL COMMAND] The command '{command}' changes shell state."
                " Copy to clipboard to run manually? [Y/N/S(how)]: "
            ), end="")
            choice = input().lower()

            if choice == 's':
                print(colorize_command(f"\n{command}\n"))
                handle_commands([command])
            elif choice == 'y':
                copy_to_clipboard(command)
                print(colorize_command(f"Command copied to clipboard. Paste and run manually."))
            return

        # Check if it's a risky command
        is_risky = is_risky_command(command)
        confirm_msg = "Execute? [y/N]: " if is_risky else "Execute? [Y/n]: "
        default_choice = "n" if is_risky else "y"

        # If auto_confirm is True and it's not a risky command, skip confirmation
        if auto_confirm and not is_risky:
            print(colorize_command(f"Auto-executing: {command}"))
            run_command(command)
            return

        # Otherwise prompt for confirmation
        print(colorize_command(confirm_msg), end="")
        choice = input().lower()

        if not choice:  # Default based on risk
            choice = default_choice

        if choice == "y":
            run_command(command)

    else:  # Multiple commands
        print(colorize_command(f"Found {n_commands} commands:"))
        for i, cmd in enumerate(commands, 1):
            is_risky_cmd = is_risky_command(cmd)
            is_stateful_cmd = is_stateful_command(cmd)
            risk_label = " [RISKY]" if is_risky_cmd else ""
            stateful_label = " [STATEFUL]" if is_stateful_cmd else ""
            print(colorize_command(f"{i}: {cmd}{risk_label}{stateful_label}"))

        print(colorize_command("Enter the number of the command to execute (or 'a' for all, 'q' to quit): "), end="")
        choice = input().lower()

        if choice == "q":
            return
        elif choice == "a":
            # Execute all commands in sequence
            for cmd in commands:
                if is_stateful_command(cmd):
                    print(colorize_command(
                        f"[STATEFUL COMMAND] Skipping '{cmd}' as it changes shell state."
                    ))
                    continue

                if is_risky_command(cmd):
                    print(colorize_command(f"Execute risky command '{cmd}'? [y/N]: "), end="")
                    subchoice = input().lower()
                    if subchoice != "y":
                        continue

                run_command(cmd)
        elif choice.isdigit():
            # Execute the selected command
            idx = int(choice) - 1
            if 0 <= idx < len(commands):
                cmd = commands[idx]

                if is_stateful_command(cmd):
                    print(colorize_command(
                        f"[STATEFUL COMMAND] The command '{cmd}' changes shell state."
                        " Copy to clipboard? [Y/n]: "
                    ), end="")
                    subchoice = input().lower()
                    if subchoice.lower() != "n":
                        copy_to_clipboard(cmd)
                        print(colorize_command(f"Command copied to clipboard. Paste and run manually."))
                else:
                    if is_risky_command(cmd):
                        print(colorize_command(f"Execute risky command '{cmd}'? [y/N]: "), end="")
                        subchoice = input().lower()
                        if subchoice == "y":
                            run_command(cmd)
                    else:
                        print(colorize_command(f"Execute '{cmd}'? [Y/n]: "), end="")
                        subchoice = input().lower()
                        if subchoice.lower() != "n":
                            run_command(cmd)
            else:
                print(colorize_command(f"Invalid choice: {choice}"))

def run_command(command):
    """Execute a shell command with error handling."""
    if not command:
        return

    if not is_shell_command(command):
        print(colorize_command(f"Warning: '{command}' doesn't look like a valid shell command."))
        print(colorize_command("Execute anyway? [y/N]: "), end="")
        choice = input().lower()
        if choice != "y":
            return

    success = run_shell_command(command)
    if not success:
        print(colorize_command(f"Command failed: {command}"))

def interactive_mode():
    """Run TerminalAI in interactive mode."""
    from terminalai.config import load_config
    config = load_config()

    print(colorize_command("TerminalAI: What is your question? (Type 'exit' to quit)"))

    while True:
        print(colorize_command(": "), end="")
        query = input().strip()

        if query.lower() in ["exit", "quit", "q"]:
            print(colorize_command("Goodbye!"))
            sys.exit(0)

        if not query:
            continue

        from terminalai.shell_integration import get_system_context
        system_context = get_system_context()

        from terminalai.ai_providers import get_provider
        provider = get_provider(config.get("provider", ""))
        if not provider:
            print(colorize_command("No AI provider configured. Please run 'ai setup' first."))
            break

        try:
            response = provider.generate_response(query, system_context, verbose=False)

            from terminalai.formatting import print_ai_answer_with_rich
            print_ai_answer_with_rich(response)

            # Extract and handle commands from the response
            commands = extract_commands(response)
            if commands:
                handle_commands(commands, auto_confirm=False)

        except Exception as e:
            print(colorize_command(f"Error: {str(e)}"))

def setup_wizard():
    """Run the setup wizard to configure TerminalAI."""
    from terminalai.config import load_config, save_config
    config = load_config()

    print(colorize_command("TerminalAI Setup Wizard"))
    print(colorize_command("===================="))

    # Configure AI providers
    print(colorize_command("\nAI Provider Configuration:"))
    print(colorize_command("1. Configure OpenRouter (recommended for GPT access)"))
    print(colorize_command("2. Configure Mistral"))
    print(colorize_command("3. Configure Gemini"))
    print(colorize_command("4. Configure Ollama (local models)"))
    print(colorize_command("5. Skip provider setup"))

    choice = input(colorize_command("Choose an option (1-5): ")).strip()

    if choice == "1":
        api_key = input(colorize_command("Enter OpenRouter API key: ")).strip()
        if api_key:
            config["providers"] = config.get("providers", {})
            config["providers"]["openrouter"] = {"api_key": api_key}
            config["default_provider"] = "openrouter"
            print(colorize_command("OpenRouter configured as default provider."))

    elif choice == "2":
        api_key = input(colorize_command("Enter Mistral API key: ")).strip()
        if api_key:
            config["providers"] = config.get("providers", {})
            config["providers"]["mistral"] = {"api_key": api_key}
            config["default_provider"] = "mistral"
            print(colorize_command("Mistral configured as default provider."))

    elif choice == "3":
        api_key = input(colorize_command("Enter Gemini API key: ")).strip()
        if api_key:
            config["providers"] = config.get("providers", {})
            config["providers"]["gemini"] = {"api_key": api_key}
            config["default_provider"] = "gemini"
            print(colorize_command("Gemini configured as default provider."))

    elif choice == "4":
        host = input(colorize_command("Enter Ollama host (default: http://localhost:11434): ")).strip()
        if not host:
            host = "http://localhost:11434"
        model = input(colorize_command("Enter Ollama model name (default: llama2): ")).strip()
        if not model:
            model = "llama2"

        config["providers"] = config.get("providers", {})
        config["providers"]["ollama"] = {
            "host": host,
            "model": model
        }
        config["default_provider"] = "ollama"
        print(colorize_command(f"Ollama configured as default provider with model {model}."))

    # Shell integration
    print(colorize_command("\nShell Integration (for stateful commands):"))
    print(colorize_command("1. Install shell integration"))
    print(colorize_command("2. Uninstall shell integration"))
    print(colorize_command("3. Skip shell integration"))

    choice = input(colorize_command("Choose an option (1-3): ")).strip()

    if choice == "1":
        from terminalai.shell_integration import install_shell_integration
        install_shell_integration()
    elif choice == "2":
        from terminalai.shell_integration import uninstall_shell_integration
        uninstall_shell_integration()

    # Save configuration
    save_config(config)
    print(colorize_command("\nSetup completed successfully!"))

    # Show usage instructions
    print(colorize_command("\nUsage Instructions:"))
    print(colorize_command("- Run 'ai \"your question\"' to ask a question"))
    print(colorize_command("- Run 'ai' without arguments for interactive mode"))
    print(colorize_command("- Use 'ai -y \"your command request\"' to auto-confirm non-risky commands"))