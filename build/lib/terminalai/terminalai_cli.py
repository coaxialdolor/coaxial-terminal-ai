"""Main CLI for TerminalAI.

Best practice: Run this script as a module from the project root:
    python -m terminalai.terminalai.terminalai
This ensures all imports work correctly. If you run this file directly, you may get import errors.
"""
import argparse
import sys
import platform
import re
import os
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from terminalai.config import load_config, save_config, get_system_prompt, DEFAULT_SYSTEM_PROMPT
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

FORBIDDEN_COMMANDS = [
    'cd', 'export', 'set', 'unset', 'alias', 'unalias', 'source', 'pushd', 'popd', 'dirs', 'fg', 'bg', 'jobs', 'disown', 'exec', 'login', 'logout', 'exit', 'kill', 'trap', 'shopt', 'enable', 'disable', 'declare', 'typeset', 'readonly', 'eval', 'help', 'times', 'umask', 'wait', 'suspend', 'hash', 'bind', 'compgen', 'complete', 'compopt', 'history', 'fc', 'getopts', 'let', 'local', 'read', 'readonly', 'return', 'shift', 'test', 'times', 'type', 'ulimit', 'unalias', 'wait'
]
RISKY_COMMANDS = ['rm', 'dd', 'mkfs', 'chmod 777', 'chown', 'shutdown', 'reboot', 'init', 'halt', 'poweroff', 'mv /', 'cp /', '>:']

def is_forbidden_command(cmd):
    cmd_strip = cmd.strip().split()
    if not cmd_strip:
        return False
    return cmd_strip[0] in FORBIDDEN_COMMANDS

def is_risky_command(cmd):
    lower = cmd.lower()
    for risky in RISKY_COMMANDS:
        if risky in lower:
            return True
    return False

def install_shell_integration():
    """Install shell integration for forbidden commands in ~/.zshrc."""
    zshrc = os.path.expanduser('~/.zshrc')
    func_name = 'run_terminalai_shell_command'
    comment = '# Shell integration for terminalai to be able to execute cd, and other forbidden commands\n'
    func = '''run_terminalai_shell_command() {
  local cmd=$(history | grep '#TERMINALAI_SHELL_COMMAND:' | tail -1 | sed 's/.*#TERMINALAI_SHELL_COMMAND: //')
  if [ -n "$cmd" ]; then
    echo "[RUNNING in current shell]: $cmd"
    eval "$cmd"
  else
    echo "No TerminalAI shell command found in history."
  fi
}
'''
    with open(zshrc, 'r', encoding='utf-8') as f:
        content = f.read()
    if func_name in content:
        print('Shell integration already installed in ~/.zshrc.')
        return
    with open(zshrc, 'a', encoding='utf-8') as f:
        f.write('\n' + comment + func + '\n')
    print('Shell integration installed in ~/.zshrc.')

def uninstall_shell_integration():
    """Uninstall shell integration for forbidden commands from ~/.zshrc."""
    zshrc = os.path.expanduser('~/.zshrc')
    with open(zshrc, 'r', encoding='utf-8') as f:
        content = f.read()
    # Remove the comment and function
    pattern = re.compile(r'\n?# Shell integration for terminalai to be able to execute cd, and other forbidden commands\nrun_terminalai_shell_command\(\) \{[\s\S]+?^\}', re.MULTILINE)
    new_content, n = pattern.subn('', content)
    if n == 0:
        print('Shell integration not found in ~/.zshrc.')
        return
    with open(zshrc, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Shell integration removed from ~/.zshrc.')

def main():
    """Main entry point for the TerminalAI CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        parser = argparse.ArgumentParser(
            prog="ai setup",
            description="Configure AI providers and settings"
        )
        parser.add_argument('--set-default', type=str, help='Set the default AI provider')
        parser.add_argument('--install-shell-integration', action='store_true', help='Install shell integration to make cd and other forbidden commands executable')
        parser.add_argument('--uninstall-shell-integration', action='store_true', help='Uninstall shell integration for forbidden commands')
        args = parser.parse_args(sys.argv[2:])
        if args.set_default:
            config = load_config()
            if args.set_default in config['providers']:
                config['default_provider'] = args.set_default
                save_config(config)
                print(f"Default provider set to {args.set_default}.")
            else:
                print(f"Provider '{args.set_default}' is not supported.")
        elif args.install_shell_integration:
            install_shell_integration()
        elif args.uninstall_shell_integration:
            uninstall_shell_integration()
        elif len(sys.argv) == 2:
            # Interactive setup menu
            console = Console()
            logo = '''
████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗     █████╗ ██╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║    ██╔══██╗██║
   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║    ███████║██║
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║    ██╔══██║██║
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║██║    ██║  ██║███████╗
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝╚══════╝
'''
            while True:
                console.clear()
                console.print(logo, style="bold cyan")
                console.print("[bold magenta]TerminalAI Setup Menu:[/bold magenta]")
                menu_options = [
                    "1. Set default provider",
                    "2. See current system prompt",
                    "3. Edit current system prompt",
                    "4. Reset system prompt to default",
                    "5. Setup API keys",
                    "6. Install shell extension",
                    "7. Uninstall shell extension",
                    "8. Exit"
                ]
                for opt in menu_options:
                    num, desc = opt.split('.', 1)
                    console.print(f"[bold yellow]{num}[/bold yellow].[white]{desc}[/white]")
                choice = console.input("[bold green]Choose an action (1-8): [/bold green]").strip()
                config = load_config()
                if choice == '1':
                    providers = list(config['providers'].keys())
                    console.print("\n[bold]Available providers:[/bold]")
                    for idx, p in enumerate(providers, 1):
                        is_default = ' (default)' if p == config.get('default_provider') else ''
                        console.print(f"[bold yellow]{idx}[/bold yellow]. {p}{is_default}")
                    sel = console.input(f"[bold green]Select provider (1-{len(providers)}): [/bold green]").strip()
                    if sel.isdigit() and 1 <= int(sel) <= len(providers):
                        config['default_provider'] = providers[int(sel)-1]
                        save_config(config)
                        console.print(f"[bold green]Default provider set to {providers[int(sel)-1]}.[/bold green]")
                    else:
                        console.print("[red]Invalid selection.[/red]")
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '2':
                    console.print("\n[bold]Current system prompt:[/bold]\n")
                    console.print(get_system_prompt())
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '3':
                    console.print("\n[bold]Current system prompt:[/bold]\n")
                    console.print(config.get('system_prompt', ''))
                    new_prompt = console.input("\n[bold green]Enter new system prompt (leave blank to cancel):\n[/bold green]")
                    if new_prompt.strip():
                        config['system_prompt'] = new_prompt.strip()
                        save_config(config)
                        console.print("[bold green]System prompt updated.[/bold green]")
                    else:
                        console.print("[yellow]No changes made.[/yellow]")
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '4':
                    config['system_prompt'] = DEFAULT_SYSTEM_PROMPT
                    save_config(config)
                    console.print("[bold green]System prompt reset to default.[/bold green]")
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '5':
                    providers = list(config['providers'].keys())
                    console.print("\n[bold]Providers:[/bold]")
                    for idx, p in enumerate(providers, 1):
                        console.print(f"[bold yellow]{idx}[/bold yellow]. {p}")
                    sel = console.input(f"[bold green]Select provider to set API key/host (1-{len(providers)}): [/bold green]").strip()
                    if sel.isdigit() and 1 <= int(sel) <= len(providers):
                        pname = providers[int(sel)-1]
                        if pname == 'ollama':
                            current = config['providers'][pname].get('host', '')
                            console.print(f"Current host: {current}")
                            new_host = console.input("Enter new Ollama host (e.g., http://localhost:11434): ").strip()
                            if new_host:
                                config['providers'][pname]['host'] = new_host
                                save_config(config)
                                console.print("[bold green]Ollama host updated.[/bold green]")
                            else:
                                console.print("[yellow]No changes made.[/yellow]")
                        else:
                            current = config['providers'][pname].get('api_key', '')
                            console.print(f"Current API key: {'(not set)' if not current else '[hidden]'}")
                            new_key = console.input(f"Enter new API key for {pname}: ").strip()
                            if new_key:
                                config['providers'][pname]['api_key'] = new_key
                                save_config(config)
                                console.print(f"[bold green]API key for {pname} updated.[/bold green]")
                            else:
                                console.print("[yellow]No changes made.[/yellow]")
                    else:
                        console.print("[red]Invalid selection.[/red]")
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '6':
                    install_shell_integration()
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '7':
                    uninstall_shell_integration()
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '8':
                    console.print("[bold cyan]Exiting setup.[/bold cyan]")
                    break
                else:
                    console.print("[red]Invalid choice. Please select a number from 1 to 8.[/red]")
                    console.input("[dim]Press Enter to continue...[/dim]")
        else:
            parser.print_help()
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
            cmd = commands[0]
            forbidden = is_forbidden_command(cmd)
            risky = is_risky_command(cmd)
            if is_shell_command(cmd):
                if forbidden:
                    # Always require confirmation for forbidden commands
                    confirm = input(f"[FORBIDDEN] This command ('{cmd}') changes shell state. Run in your current shell? [Y/N] ").strip().lower()
                    if confirm == 'y':
                        if risky:
                            confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                            if confirm2 != 'y':
                                print("Command not executed.")
                                return
                        # Output marker for shell integration
                        print(f"#TERMINALAI_SHELL_COMMAND: {cmd}")
                        print("[INFO] To run this command in your current shell, use the provided shell function.")
                    else:
                        print("Command not executed.")
                else:
                    if args.yes:
                        if risky:
                            confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                            if confirm2 != 'y':
                                print("Command not executed.")
                                return
                        print(colorize_command(f"[RUNNING] {cmd}"))
                        output = run_shell_command(cmd)
                        print(output)
                    else:
                        confirm = input("Do you want to run this command? [Y/N] ").strip().lower()
                        if confirm == 'y':
                            if risky:
                                confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                                if confirm2 != 'y':
                                    print("Command not executed.")
                                    return
                            print(colorize_command(f"[RUNNING] {cmd}"))
                            output = run_shell_command(cmd)
                            print(output)
                        else:
                            print("Command not executed.")
        else:
            print(colorize_ai("\nCommands found:"))
            for idx, cmd in enumerate(commands, 1):
                print(colorize_command(f"  {idx}. {cmd}"))
            selection = input(
                (
                    f"Do you want to run a command? Enter the number (1-{len(commands)}) "
                    "or N to skip: "
                )
            ).strip().lower()
            if selection.isdigit() and 1 <= int(selection) <= len(commands):
                cmd = commands[int(selection)-1]
                forbidden = is_forbidden_command(cmd)
                risky = is_risky_command(cmd)
                if forbidden:
                    confirm = input(f"[FORBIDDEN] This command ('{cmd}') changes shell state. Run in your current shell? [Y/N] ").strip().lower()
                    if confirm == 'y':
                        if risky:
                            confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                            if confirm2 != 'y':
                                print("Command not executed.")
                                return
                        print(f"#TERMINALAI_SHELL_COMMAND: {cmd}")
                        print("[INFO] To run this command in your current shell, use the provided shell function.")
                    else:
                        print("Command not executed.")
                else:
                    if args.yes:
                        if risky:
                            confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                            if confirm2 != 'y':
                                print("Command not executed.")
                                return
                        print(colorize_command(f"[RUNNING] {cmd}"))
                        output = run_shell_command(cmd)
                        print(output)
                    else:
                        confirm = input("Do you want to run this command? [Y/N] ").strip().lower()
                        if confirm == 'y':
                            if risky:
                                confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                                if confirm2 != 'y':
                                    print("Command not executed.")
                                    return
                            print(colorize_command(f"[RUNNING] {cmd}"))
                            output = run_shell_command(cmd)
                            print(output)
                        else:
                            print("Command not executed.")
            else:
                print("Command not executed.")
    else:
        # Interactive setup menu
        while True:
            print("\nTerminalAI Setup Menu:")
            print("1. Set default provider")
            print("2. See current system prompt")
            print("3. Edit current system prompt")
            print("4. Reset system prompt to default")
            print("5. Setup API keys")
            print("6. Install shell extension")
            print("7. Uninstall shell extension")
            print("8. Exit")
            choice = input("Choose an action (1-8): ").strip()
            config = load_config()
            if choice == '1':
                providers = list(config['providers'].keys())
                print("\nAvailable providers:")
                for idx, p in enumerate(providers, 1):
                    print(f"  {idx}. {p}{' (default)' if p == config.get('default_provider') else ''}")
                sel = input(f"Select provider (1-{len(providers)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(providers):
                    config['default_provider'] = providers[int(sel)-1]
                    save_config(config)
                    print(f"Default provider set to {providers[int(sel)-1]}.")
                else:
                    print("Invalid selection.")
            elif choice == '2':
                console.print("\n[bold]Current system prompt:[/bold]\n")
                console.print(get_system_prompt())
                console.input("[dim]Press Enter to continue...[/dim]")
            elif choice == '3':
                console.print("\nCurrent system prompt:\n")
                console.print(config.get('system_prompt', ''))
                new_prompt = input("\nEnter new system prompt (leave blank to cancel):\n")
                if new_prompt.strip():
                    config['system_prompt'] = new_prompt.strip()
                    save_config(config)
                    console.print("System prompt updated.")
                else:
                    console.print("No changes made.")
                console.input("[dim]Press Enter to continue...[/dim]")
            elif choice == '4':
                config['system_prompt'] = DEFAULT_SYSTEM_PROMPT
                save_config(config)
                console.print("System prompt reset to default.")
            elif choice == '5':
                providers = list(config['providers'].keys())
                console.print("\nProviders:")
                for idx, p in enumerate(providers, 1):
                    console.print(f"  {idx}. {p}")
                sel = console.input(f"Select provider to set API key/host (1-{len(providers)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(providers):
                    pname = providers[int(sel)-1]
                    if pname == 'ollama':
                        current = config['providers'][pname].get('host', '')
                        console.print(f"Current host: {current}")
                        new_host = input("Enter new Ollama host (e.g., http://localhost:11434): ").strip()
                        if new_host:
                            config['providers'][pname]['host'] = new_host
                            save_config(config)
                            console.print("Ollama host updated.")
                        else:
                            console.print("No changes made.")
                    else:
                        current = config['providers'][pname].get('api_key', '')
                        console.print(f"Current API key: {'(not set)' if not current else '[hidden]'}")
                        new_key = input(f"Enter new API key for {pname}: ").strip()
                        if new_key:
                            config['providers'][pname]['api_key'] = new_key
                            save_config(config)
                            console.print(f"API key for {pname} updated.")
                        else:
                            console.print("No changes made.")
                else:
                    console.print("Invalid selection.")
            elif choice == '6':
                install_shell_integration()
            elif choice == '7':
                uninstall_shell_integration()
            elif choice == '8':
                print("Exiting setup.")
                break
            else:
                print("Invalid choice. Please select a number from 1 to 8.")

if __name__ == "__main__":
    main()
