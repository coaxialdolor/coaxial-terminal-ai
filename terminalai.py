import argparse


def main():
    parser = argparse.ArgumentParser(prog="ai", description="TerminalAI: Command-line AI assistant.")
    parser.add_argument('query', nargs=argparse.REMAINDER, help='Your AI request or command')
    parser.add_argument('-y', '--yes', action='store_true', help='Automatically confirm command execution')
    args = parser.parse_args()

    if not args.query:
        print("Please provide a query. Example: ai how do I see the newest file in this folder?")
        return

    # Placeholder for AI logic
    print(f"[SYSTEMPROMPT] ai {' '.join(args.query)}")
    print("[AI] (AI response would go here)")

if __name__ == "__main__":
    main()
