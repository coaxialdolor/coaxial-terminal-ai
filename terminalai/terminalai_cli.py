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

def is_likely_command(line):
    """Return True if the line looks like a shell command."""
    line = line.strip()
    if not line or line.startswith("#"):
        return False
    
    # Skip natural language sentences
    if len(line.split()) > 3 and line[0].isupper() and line[-1] in ['.', '!', '?']:
        return False
    
    # Command detection approach: look for known command patterns
    known_cmds = [
        "ls", "cd", "cat", "cp", "mv", "rm", "find", "grep", "awk", "sed", "chmod",
        "chown", "head", "tail", "touch", "mkdir", "rmdir", "tree", "du", "df", "ps", 
        "top", "htop", "less", "more", "man", "which", "whereis", "locate", "pwd", "whoami",
        "date", "cal", "env", "export", "ssh", "scp", "curl", "wget", "tar", "zip", "unzip",
        "python", "pip", "brew", "apt", "yum", "dnf", "docker", "git"
    ]
    
    # Include echo but with special handling
    if line.startswith("echo "):
        content = line[5:].strip()
        # Skip if it looks like a sentence (starts with capital, ends with punctuation)
        if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        if content and content[0].isupper() and content[-1] in ['.', '!', '?']:
            return False
    
    # Check if the line starts with a known command
    first_word = line.split()[0] if line.split() else ""
    if first_word in known_cmds and len(line.split()) >= 2:
        return True
    if first_word == "echo" and len(line.split()) >= 2:
        return True
    
    # Check for shell operators
    if ' | ' in line or ' && ' in line or ' || ' in line or ' > ' in line or ' >> ' in line:
        for cmd in known_cmds:
            if line.startswith(cmd + ' '):
                return True
    
    return False

def extract_commands(ai_response):
    """Extract shell commands from AI response code blocks."""
    commands = []
    
    # Only extract commands from code blocks (most reliable source)
    code_blocks = re.findall(r'```(?:bash|sh)?\n([\s\S]*?)```', ai_response)
    
    # Split the AI response into sections
    sections = re.split(r'```(?:bash|sh)?\n[\s\S]*?```', ai_response)
    
    for i, block in enumerate(code_blocks):
        # Get the text before this code block (if available)
        context_before = sections[i] if i < len(sections) else ""
        
        # Skip code blocks that appear to be presenting information rather than commands
        skip_patterns = [
            r'(?i)example',
            r'(?i)here\'s how',
            r'(?i)alternatively',
            r'(?i)you can use',
            r'(?i)other approach',
            r'(?i)result is',
            r'(?i)output will be'
        ]
        
        should_skip = False
        for pattern in skip_patterns:
            if re.search(pattern, context_before[-100:] if len(context_before) > 100 else context_before):
                should_skip = True
                break
        
        if should_skip:
            continue
        
        for line in block.splitlines():
            # Skip blank lines and comments
            if not line.strip() or line.strip().startswith('#'):
                continue
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
        has_command = False
        for line in code.splitlines():
            if is_likely_command(line):
                console.print(Panel(Syntax(line, "bash", theme="monokai", line_numbers=False),
                                   title="Command", border_style="yellow"))
                has_command = True
        # If no detected commands, just print the code block as regular text
        if not has_command and code.strip():
            print(colorize_ai(f"```\n{code}\n```"))
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
                    "6. See current API keys",
                    "7. Install shell extension",
                    "8. Uninstall shell extension",
                    "9. Exit"
                ]
                menu_info = {
                    '1': "Set which AI provider (OpenRouter, Gemini, Mistral, Ollama) is used by default for all queries.",
                    '2': "View the current system prompt that guides the AI's behavior.",
                    '3': "Edit the system prompt to customize how the AI responds to your queries.",
                    '4': "Reset the system prompt to the default recommended by TerminalAI.",
                    '5': "Set or update the API key (or host for Ollama) for any provider.",
                    '6': "See a list of all providers and the currently stored API key or host for each.",
                    '7': "This option will install a script in your shell to allow certain commands like 'cd' to be performed by the AI. Some shell commands (like changing directories) can only run in your current shell and not in a subprocess. This integration adds a function to your shell configuration that allows TerminalAI to execute these commands in your active shell.",
                    '8': "Uninstall the shell extension from your shell config.",
                    '9': "Exit the setup menu."
                }
                for opt in menu_options:
                    num, desc = opt.split('.', 1)
                    console.print(f"[bold yellow]{num}[/bold yellow].[white]{desc}[/white]")
                console.print("[dim]Type 'i' followed by a number (e.g., i1) for more info about an option.[/dim]")
                choice = console.input("[bold green]Choose an action (1-9): [/bold green]").strip()
                config = load_config()
                if choice.startswith('i') and choice[1:].isdigit():
                    info_num = choice[1:]
                    if info_num in menu_info:
                        console.print(f"[bold cyan]Info for option {info_num}:[/bold cyan] {menu_info[info_num]}")
                    else:
                        console.print("[red]No info available for that option.[/red]")
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '1':
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
                    providers = list(config['providers'].keys())
                    console.print("\n[bold]Current API keys / hosts:[/bold]")
                    for p in providers:
                        if p == 'ollama':
                            val = config['providers'][p].get('host', '')
                            shown = val if val else '[not set]'
                        else:
                            val = config['providers'][p].get('api_key', '')
                            shown = '[not set]' if not val else '[hidden]'
                        console.print(f"[bold yellow]{p}:[/bold yellow] {shown}")
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '7':
                    install_shell_integration()
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '8':
                    uninstall_shell_integration()
                    console.input("[dim]Press Enter to continue...[/dim]")
                elif choice == '9':
                    console.print("[bold cyan]Exiting setup.[/bold cyan]")
                    break
                else:
                    console.print("[red]Invalid choice. Please select a number from 1 to 9.[/red]")
                    console.input("[dim]Press Enter to continue...[/dim]")
        else:
            parser.print_help()
        return

    # Create a custom formatter class with colored help
    class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=40, width=100)
        
        def _format_action(self, action):
            # Format the help with color codes
            result = super()._format_action(action)
            # Add color to argument names
            result = result.replace('ai setup', '\033[1;36mai setup\033[0m')
            result = result.replace('--yes', '\033[1;33m--yes\033[0m')
            result = result.replace('-y', '\033[1;33m-y\033[0m')
            result = result.replace('--verbose', '\033[1;33m--verbose\033[0m')
            result = result.replace('-v', '\033[1;33m-v\033[0m')
            result = result.replace('--long', '\033[1;33m--long\033[0m')
            result = result.replace('-l', '\033[1;33m-l\033[0m')
            result = result.replace('--help', '\033[1;33m--help\033[0m')
            result = result.replace('-h', '\033[1;33m-h\033[0m')
            return result
    
    # Custom help formatter for the program description
    class ColoredDescriptionFormatter(ColoredHelpFormatter):
        def format_help(self):
            help_text = super().format_help()
            # Add colored logo
            logo = '''
\033[1;36m████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗     █████╗ ██╗
\033[1;36m╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║    ██╔══██╗██║
\033[1;36m   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║    ███████║██║
\033[1;36m   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║    ██╔══██║██║
\033[1;36m   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║██║    ██║  ██║███████╗
\033[1;36m   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝╚══════╝\033[0m
'''
            # Add usage examples with color
            examples = '''
\033[1;32mUsage Examples:\033[0m
  \033[1m1. Interactive Mode:\033[0m
     \033[33mai\033[0m
     \033[90m# Starts an interactive session where you can type your query\033[0m

  \033[1m2. Direct Query:\033[0m
     \033[33mai "how do I list all files in the current directory?"\033[0m
     \033[90m# Sends query directly to the AI assistant\033[0m

  \033[1m3. Auto-confirm Commands:\033[0m
     \033[33mai -y "create a temporary file with random data"\033[0m
     \033[90m# Automatically confirms command execution (except for risky commands)\033[0m

  \033[1m4. Configure Settings:\033[0m
     \033[33mai setup\033[0m
     \033[90m# Opens the setup menu to configure providers, API keys, and preferences\033[0m

  \033[1m5. Shell Integration:\033[0m
     \033[33mai setup --install-shell-integration\033[0m
     \033[90m# Enables running shell state-changing commands like 'cd'\033[0m

\033[1;35mNote:\033[0m When the AI suggests multiple commands, you can select which one to run by number.
      For risky commands, you'll always be asked for confirmation before execution.
'''
            return logo + "\n" + help_text + examples
    
    # Custom parser with colored help
    parser = argparse.ArgumentParser(
        prog="ai",
        description="\033[1;37mTerminalAI: An AI-powered assistant for your command line.\033[0m",
        epilog="\033[1;37mFor more information, use 'ai setup' to configure providers and settings.\033[0m",
        formatter_class=ColoredDescriptionFormatter
    )
    
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='\033[1;32mAutomatically confirm command execution\033[0m'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='\033[1;32mVerbose output with detailed explanations\033[0m'
    )
    parser.add_argument(
        '-l', '--long',
        action='store_true',
        help='\033[1;32mRequest longer, more comprehensive responses\033[0m'
    )
    parser.add_argument('query', nargs=argparse.REMAINDER, help='\033[1;32mYour question or command for the AI\033[0m')
    args = parser.parse_args()

    # Interactive mode when no query is provided
    if not args.query or (len(args.query) == 1 and args.query[0] == ''):
        print(colorize_ai("AI: What is your question?"))
        try:
            prompt = input(": ").strip()
            if not prompt:
                print("No question provided. Exiting.")
                return
        except KeyboardInterrupt:
            print("\nExiting.")
            return
    else:
        prompt = ' '.join(args.query)

    provider = get_provider()
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
                        # Automatic confirmation with -y flag, still check for risky commands
                        if risky:
                            confirm2 = input("[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                            if confirm2 != 'y':
                                print("Command not executed.")
                                return
                        print(colorize_command(f"[RUNNING] {cmd}"))
                        output = run_shell_command(cmd)
                        print(output)
                    else:
                        # Single Y/N confirmation for regular commands
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
                    # For forbidden commands, always ask for confirmation
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
                    # For normal commands, run immediately after selection without extra confirmation
                    if risky:
                        # Still confirm risky commands
                        confirm = input(f"[RISKY] The command '{cmd}' is potentially dangerous. Are you absolutely sure? [Y/N] ").strip().lower()
                        if confirm != 'y':
                            print("Command not executed.")
                            return
                    # Run the command without additional confirmation
                    print(colorize_command(f"[RUNNING] {cmd}"))
                    output = run_shell_command(cmd)
                    print(output)
            else:
                print("Command not executed.")

if __name__ == "__main__":
    main()
