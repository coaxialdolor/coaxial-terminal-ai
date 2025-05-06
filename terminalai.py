import argparse
import sys
from config import load_config, save_config, DEFAULT_CONFIG


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

    # Placeholder for AI logic
    print(f"[SYSTEMPROMPT] ai {' '.join(args.query)}")
    print("[AI] (AI response would go here)")

if __name__ == "__main__":
    main()
