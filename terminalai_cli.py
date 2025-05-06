"""Main CLI for TerminalAI.

Best practice: Run this script as a module from the project root:
    python -m terminalai.terminalai.terminalai
This ensures all imports work correctly. If you run this file directly, you may get import errors.
"""
import argparse
import sys
import platform
import re
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from terminalai.config import load_config, save_config, get_system_prompt
from terminalai.ai_providers import get_provider
from terminalai.command_utils import is_shell_command, run_shell_command
from terminalai.color_utils import colorize_ai, colorize_command

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    print("[WARNING] It is recommended to run this script as a module:")
    print("    python -m terminalai.terminalai.terminalai")
    print("Otherwise, you may get import errors.")

def setup_provider():
    """Stub for setup_provider. Replace with actual implementation if needed."""
    print("Provider setup not implemented.")

def get_system_context():
    """Return the system context string for the prompt."""
    system = platform.system()
    if system == "Darwin":
        sys_str = "macOS/zsh"
    elif system == "Linux":
        sys_str = "Linux/bash"
    elif system == "Windows":
        sys_str = "Windows/PowerShell"
    else:
        sys_str = "a Unix-like system"
    prompt = get_system_prompt()
    return prompt.replace("the user's system", sys_str)

def extract_commands(ai_response):
    """Extract shell commands from AI response code blocks."""
    commands = []
    code_blocks = re.findall(r'```(?:bash|sh)?\n([\s\S]*?)```', ai_response)
    for block in code_blocks:
        for line in block.splitlines():
            if is_likely_command(line):
                commands.append(line.strip())
    # Deduplicate, preserve order
    seen = set()
    result = []
    for cmd in commands:
        if cmd and cmd not in seen:
            seen.add(cmd)
            result.append(cmd)
    return result

def is_likely_command(line):
    """Return True if the line looks like a shell command."""
    line = line.strip()
    if not line or line.startswith("#"):
        return False
    known_cmds = [
        "ls", "cd", "cat", "echo", "cp", "mv", "rm", "find", "grep", "awk", "sed", "chmod",
        "chown", "head", "tail", "touch", "mkdir", "rmdir", "tree", "du", "df", "ps", "kill",
        "top", "htop", "less", "more", "man", "which", "whereis", "locate", "pwd", "whoami",
        "date", "cal", "env", "export", "ssh", "scp", "curl", "wget", "tar", "zip", "unzip",
        "python", "pip", "brew", "apt", "yum", "dnf", "docker", "git"
    ]
    for cmd in known_cmds:
        if line.startswith(cmd + ' '):
            if len(line.split()) >= 2:
                return True
    if '|' in line or '&&' in line:
        return True
    return False

def print_ai_answer_with_rich(ai_response):
    """Print the AI response using rich formatting for code blocks."""
    console = Console()
    code_block_pattern = re.compile(r'```(bash|sh)?\n([\s\S]*?)```')
    last_end = 0
    for match in code_block_pattern.finditer(ai_response):
        before = ai_response[last_end:match.start()]
        if before.strip():
            print(colorize_ai(before.strip()))
        code = match.group(2)
        for line in code.splitlines():
            if is_likely_command(line):
                console.print(Panel(Syntax(line, "bash", theme="monokai", line_numbers=False),
                                   title="Command", border_style="yellow"))
        last_end = match.end()
    after = ai_response[last_end:]
    if after.strip():
        print(colorize_ai(after.strip()))

def main():
    """Main entry point for the TerminalAI CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        parser = argparse.ArgumentParser(
            prog="ai setup",
            description="Configure AI providers and settings"
        )
        parser.add_argument('--set-default', type=str, help='Set the default AI provider')
        args = parser.parse_args(sys.argv[2:])
        if args.set_default:
            config = load_config()
            if args.set_default in config['providers']:
                config['default_provider'] = args.set_default
                save_config(config)
                print(f"Default provider set to {args.set_default}.")
            else:
                print(f"Provider '{args.set_default}' is not supported.")
        else:
            setup_provider()
        return

    parser = argparse.ArgumentParser(
        prog="ai",
        description="TerminalAI: Command-line AI assistant."
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Automatically confirm command execution'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose, bypass concise instruction'
    )
    parser.add_argument(
        '-l', '--long',
        action='store_true',
        help='Long, bypass concise instruction'
    )
    parser.add_argument('query', nargs=argparse.REMAINDER, help='Your AI request or command')
    args = parser.parse_args()

    if not args.query or (len(args.query) == 1 and args.query[0] == ''):
        print("Please provide a query. Example: ai how do I see the newest file in this folder?")
        return

    provider = get_provider()
    prompt = ' '.join(args.query)
    system_context = get_system_context()
    full_prompt = f"{system_context}\n\n{prompt}"
    ai_response = provider.query(full_prompt)
    print_ai_answer_with_rich(f"[AI] {ai_response}")

    commands = extract_commands(ai_response)
    if commands:
        if len(commands) == 1:
            if is_shell_command(commands[0]):
                if args.yes:
                    print(colorize_command(f"[RUNNING] {commands[0]}"))
                    output = run_shell_command(commands[0])
                    print(output)
                else:
                    confirm = input("Do you want to run this command? [Y/N] ").strip().lower()
                    if confirm == 'y':
                        print(colorize_command(f"[RUNNING] {commands[0]}"))
                        output = run_shell_command(commands[0])
                        print(output)
                    else:
                        print("Command not executed.")
        else:
            print(colorize_ai("\nCommands found:"))
            for idx, cmd in enumerate(commands, 1):
                print(colorize_command(f"  {idx}. {cmd}"))
            if args.yes:
                print(colorize_command(f"[RUNNING] {commands[0]}"))
                output = run_shell_command(commands[0])
                print(output)
            else:
                selection = input(
                    (
                        f"Do you want to run a command? Enter the number (1-{len(commands)}) "
                        "or N to skip: "
                    )
                ).strip().lower()
                if selection.isdigit() and 1 <= int(selection) <= len(commands):
                    cmd = commands[int(selection)-1]
                    print(colorize_command(f"[RUNNING] {cmd}"))
                    output = run_shell_command(cmd)
                    print(output)
                else:
                    print("Command not executed.")

if __name__ == "__main__":
    main()
