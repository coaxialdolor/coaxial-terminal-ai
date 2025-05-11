"""Formatting and display utilities for TerminalAI."""
import re
import argparse
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from terminalai.color_utils import colorize_ai
from terminalai.command_extraction import is_likely_command
import os
import sys

def print_ai_answer_with_rich(ai_response, to_stderr=False):
    """Print the AI response using rich formatting for code blocks, replacing home dir with ~. If to_stderr is True, print to stderr."""
    console = Console(file=sys.stderr if to_stderr else None)
    home = os.path.expanduser("~")
    # Replace /Users/<username> or /home/<username> with ~ in code blocks and command lines
    def home_replace(text):
        # Replace both /Users/<username> and /home/<username> with ~
        text = re.sub(rf"{re.escape(home)}", "~", text)
        return text

    # Check if this is likely a pure factual response
    factual_response_patterns = [
        r'^\[AI\] [A-Z].*\.$',  # Starts with capital, ends with period
        r'^\[AI\] approximately',  # Approximate numerical answer
        r'^\[AI\] about',  # Approximate answer with "about"
        r'^\[AI\] [0-9]',  # Starts with a number
    ]

    is_likely_factual = False
    for pattern in factual_response_patterns:
        if re.search(pattern, ai_response, re.IGNORECASE):
            # If response is short and doesn't have code blocks, it's likely just factual
            if len(ai_response.split()) < 50 and '```' not in ai_response:
                is_likely_factual = True
                break

    # For factual answers, just print them directly without special formatting
    if is_likely_factual:
        console.print(f"[cyan]{ai_response}[/cyan]")
        return

    # For command-based responses, format them specially
    # Made the \n after ``` optional
    code_block_pattern = re.compile(r'```(bash|sh)?\n?([\s\S]*?)```')
    last_end = 0

    # Count how many commands we've found - for cleaner UI
    command_count = 0
    max_displayed_commands = 3  # Limit number of command panels displayed

    for match in code_block_pattern.finditer(ai_response):
        before = ai_response[last_end:match.start()]
        if before.strip():
            console.print(f"[cyan]{home_replace(before.strip())}[/cyan]")

        code = match.group(2)
        has_command = False

        # NEW: Extract and display commands even if code block has comments
        for line in code.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if is_likely_command(stripped) and command_count < max_displayed_commands:
                console.print(Panel(Syntax(home_replace(stripped), "bash", theme="monokai", line_numbers=False),
                                   title="Command", border_style="yellow"))
                has_command = True
                command_count += 1

        # If no detected commands, just print the code block as regular text
        if not has_command and code.strip():
            console.print("[cyan]```[/cyan]")
            for line_in_code in code.splitlines():
                console.print(f"[cyan]{home_replace(line_in_code)}[/cyan]")
            console.print("[cyan]```[/cyan]")

        last_end = match.end()

    after = ai_response[last_end:]
    if after.strip():
        console.print(f"[cyan]{home_replace(after.strip())}[/cyan]")

class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom argparse formatter with colored output."""
    def __init__(self, prog):
        super().__init__(prog, max_help_position=42)

    def _format_action(self, action):
        # Format the help with color codes
        result = super()._format_action(action)
        result = result.replace('usage:', '\033[1;36musage:\033[0m')
        result = result.replace('positional arguments:', '\033[1;33mpositional arguments:\033[0m')
        result = result.replace('options:', '\033[1;33moptions:\033[0m')

        # Highlight option strings (e.g., -h, --help)
        for opt_str in action.option_strings:
            result = result.replace(opt_str, f'\033[1;32m{opt_str}\033[0m')

        return result

class ColoredDescriptionFormatter(ColoredHelpFormatter):
    """Help formatter with colored description."""
    def __init__(self, prog):
        super().__init__(prog)
        self._prog_prefix = prog

    def format_help(self):
        help_text = super().format_help()

        # Description color
        if self._prog_prefix:
            desc_start = help_text.find(self._prog_prefix)
            if desc_start > 0:
                desc_text = help_text[desc_start:]
                color_desc = f'\033[1;36m{desc_text}\033[0m'
                help_text = help_text[:desc_start] + color_desc

        return help_text