import argparse
import sys
import platform
import re
from terminalai.config import load_config, save_config, DEFAULT_CONFIG
from terminalai.ai_providers import get_provider
from terminalai.command_utils import is_shell_command, run_shell_command
from terminalai.color_utils import colorize_ai, colorize_command
from rich.console import Console
from rich.syntax import Syntax

def get_system_context(verbose=False):
    system = platform.system()
    if system == "Darwin":
        sys_str = "macOS/zsh"
    elif system == "Linux":
        sys_str = "Linux/bash"
    elif system == "Windows":
        sys_str = "Windows/PowerShell"
    else:
        sys_str = "a Unix-like system"
    if verbose:
        return (
            f"You are answering for a user on {sys_str}. The user may want detailed explanations. "
            "When you suggest a command, always put it in a code block with triple backticks and specify the language (e.g., ```bash). "
            "Do not use inline code for commands. Do not include explanations or options in the same code block—only the actual shell command."
        )
    else:
        return (
            f"Always answer as concisely as possible, providing only the most relevant command for {sys_str} unless the user asks for more detail. "
            "If multiple commands are possible, enumerate them and keep explanations brief. The user will be viewing the answer in a terminal so format the text for best readability in a terminal environmnent. "
            "When you suggest a command, always put it in a code block with triple backticks and specify the language (e.g., ```bash). "
            "Do not use inline code for commands. Do not include explanations or options in the same code block—only the actual shell command."
        )

def setup_provider(args):
    config = load_config()
    print("AI Providers:")
    for provider in config['providers']:
        print(f"- {provider}")
    print(f"Current default: {config['default_provider']}")

    # Prompt to change default provider
    if not args.set_default:
        change_default = input("Do you want to change the default provider? (y/n): ").strip().lower()
        if change_default == 'y':
            new_default = input("Enter the provider name: ").strip().lower()
            if new_default in config['providers']:
                config['default_provider'] = new_default
                print(f"Default provider set to {new_default}.")
            else:
                print("Invalid provider name.")

    # Prompt to set API keys
    for provider in config['providers']:
        if provider in ['openrouter', 'gemini', 'mistral']:
            set_key = input(f"Do you want to set/update the API key for {provider}? (y/n): ").strip().lower()
            if set_key == 'y':
                api_key = input(f"Enter API key for {provider}: ").strip()
                config['providers'][provider]['api_key'] = api_key
                print(f"API key for {provider} updated.")

    save_config(config)

def extract_commands(ai_response):
    # Only extract commands from code blocks labeled as bash/sh
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
    # Require at least two words (command + argument), or a pipeline, or a $ prefix
    line = line.strip()
    if not line or line.startswith('#'):
        return False
    known_cmds = [
        'ls', 'cat', 'cd', 'find', 'grep', 'echo', 'touch', 'mv', 'cp', 'rm', 'pwd', 'tree', 'column',
        'head', 'tail', 'sort', 'awk', 'sed', 'chmod', 'chown', 'ps', 'kill', 'du', 'df', 'tar', 'zip', 'unzip',
        'ssh', 'scp', 'curl', 'wget', 'python', 'pip', 'brew', 'git', 'make', 'docker', 'npm', 'yarn', 'node', 'which', 'where', 'whoami', 'man', 'history', 'clear', 'export', 'env', 'alias', 'sudo', 'open', 'defaults', 'osascript', 'pbcopy', 'pbpaste', 'xargs', 'uniq', 'sort', 'cut', 'tr', 'tee', 'less', 'more', 'printf', 'date', 'cal', 'bc', 'expr', 'seq', 'basename', 'dirname', 'ln', 'readlink', 'stat', 'file', 'diff', 'patch', 'cmp', 'comm', 'uniq', 'wc', 'nl', 'split', 'csplit', 'paste', 'join', 'expand', 'unexpand', 'fmt', 'pr', 'col', 'colrm', 'column', 'rev', 'fold', 'iconv', 'dos2unix', 'unix2dos', 'hexdump', 'xxd', 'strings', 'od', 'base64', 'uuencode', 'uudecode', 'md5', 'sha1sum', 'sha256sum', 'sha512sum', 'openssl', 'gpg', 'pgp', 'cryptsetup', 'mount', 'umount', 'df', 'fdisk', 'mkfs', 'fsck', 'tune2fs', 'e2fsck', 'mke2fs', 'resize2fs', 'badblocks', 'lsblk', 'blkid', 'parted', 'partprobe', 'losetup', 'swapon', 'swapoff', 'free', 'top', 'htop', 'atop', 'iotop', 'dstat', 'vmstat', 'mpstat', 'pidof', 'pgrep', 'pkill', 'jobs', 'bg', 'fg', 'disown', 'wait', 'time', 'watch', 'yes', 'sleep', 'usleep']
    if line.startswith('$ '):
        return True
    for cmd in known_cmds:
        if line.startswith(cmd + ' '):
            if len(line.split()) >= 2:
                return True
    if '|' in line or '&&' in line:
        return True
    return False

def print_ai_answer_with_rich(ai_response):
    console = Console()
    # Print everything except code blocks as normal, but render code blocks with rich
    code_block_pattern = re.compile(r'```(bash|sh)?\n([\s\S]*?)```')
    last_end = 0
    for match in code_block_pattern.finditer(ai_response):
        # Print text before the code block
        before = ai_response[last_end:match.start()]
        if before.strip():
            print(colorize_ai(before.strip()))
        code = match.group(2)
        console.print(Syntax(code, "bash", theme="monokai", line_numbers=False))
        last_end = match.end()
    # Print any remaining text after the last code block
    after = ai_response[last_end:]
    if after.strip():
        print(colorize_ai(after.strip()))

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        parser = argparse.ArgumentParser(prog="ai setup", description="Configure AI providers and settings")
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
            setup_provider(args)
        return

    parser = argparse.ArgumentParser(prog="ai", description="TerminalAI: Command-line AI assistant.")
    parser.add_argument('-y', '--yes', action='store_true', help='Automatically confirm command execution')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose, bypass concise instruction')
    parser.add_argument('-l', '--long', action='store_true', help='Long, bypass concise instruction')
    parser.add_argument('query', nargs=argparse.REMAINDER, help='Your AI request or command')
    args = parser.parse_args()

    if not args.query or (len(args.query) == 1 and args.query[0] == ''):
        print("Please provide a query. Example: ai how do I see the newest file in this folder?")
        return

    provider = get_provider()
    prompt = ' '.join(args.query)
    verbose_mode = args.verbose or args.long
    system_context = get_system_context(verbose=verbose_mode)
    full_prompt = f"{system_context}\n\n{prompt}"
    ai_response = provider.query(full_prompt)
    print_ai_answer_with_rich(f"[AI] {ai_response}")

    # Extract commands from the AI response
    commands = extract_commands(ai_response)
    if commands:
        if len(commands) == 1:
            # Only one command found
            if is_shell_command(commands[0]):
                if args.yes:
                    print(colorize_command(f"[RUNNING] {commands[0]}"))
                    output = run_shell_command(commands[0])
                    print(output)
                else:
                    confirm = input(f"Do you want to run this command? [Y/N] ").strip().lower()
                    if confirm == 'y':
                        print(colorize_command(f"[RUNNING] {commands[0]}"))
                        output = run_shell_command(commands[0])
                        print(output)
                    else:
                        print("Command not executed.")
        else:
            # Multiple commands found, enumerate and prompt
            print(colorize_ai("\nCommands found:"))
            for idx, cmd in enumerate(commands, 1):
                print(colorize_command(f"  {idx}. {cmd}"))
            if args.yes:
                print(colorize_command(f"[RUNNING] {commands[0]}"))
                output = run_shell_command(commands[0])
                print(output)
            else:
                selection = input(f"Do you want to run a command? Enter the number (1-{len(commands)}) or N to skip: ").strip().lower()
                if selection.isdigit() and 1 <= int(selection) <= len(commands):
                    cmd = commands[int(selection)-1]
                    print(colorize_command(f"[RUNNING] {cmd}"))
                    output = run_shell_command(cmd)
                    print(output)
                else:
                    print("Command not executed.")

if __name__ == "__main__":
    main()
