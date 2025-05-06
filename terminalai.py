import argparse
import sys
from config import load_config, save_config, DEFAULT_CONFIG
from ai_providers import get_provider
from command_utils import is_shell_command, run_shell_command

def setup_provider(args):
    config = load_config()
    if args.set_default:
        if args.set_default not in config['providers']:
            print(f"Provider '{args.set_default}' is not supported.")
            return
        config['default_provider'] = args.set_default
        save_config(config)
        print(f"Default provider set to {args.set_default}.")
        return
    print("AI Providers:")
    for provider in config['providers']:
        print(f"- {provider}")
    print(f"Current default: {config['default_provider']}")
    # Optionally, prompt for API keys or settings here

def main():
    parser = argparse.ArgumentParser(prog="ai", description="TerminalAI: Command-line AI assistant.")
    subparsers = parser.add_subparsers(dest='command')

    setup_parser = subparsers.add_parser('setup', help='Configure AI providers and settings')
    setup_parser.add_argument('--set-default', type=str, help='Set the default AI provider')

    parser.add_argument('query', nargs=argparse.REMAINDER, help='Your AI request or command')
    parser.add_argument('-y', '--yes', action='store_true', help='Automatically confirm command execution')
    args = parser.parse_args()

    if args.command == 'setup':
        setup_provider(args)
        return

    if not args.query:
        print("Please provide a query. Example: ai how do I see the newest file in this folder?")
        return

    provider = get_provider()
    prompt = ' '.join(args.query)
    ai_response = provider.query(prompt)
    print(f"[SYSTEMPROMPT] ai {prompt}")
    print(f"[AI] {ai_response}")

    # If the AI response looks like a shell command, ask for confirmation
    if is_shell_command(ai_response):
        if args.yes:
            print(f"[RUNNING] {ai_response}")
            output = run_shell_command(ai_response)
            print(output)
        else:
            confirm = input(f"Do you want to run this command? [Y/N] ").strip().lower()
            if confirm == 'y':
                print(f"[RUNNING] {ai_response}")
                output = run_shell_command(ai_response)
                print(output)
            else:
                print("Command not executed.")

if __name__ == "__main__":
    main()
