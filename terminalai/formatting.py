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
from rich.text import Text

def print_ai_answer_with_rich(ai_response, to_stderr=False):
    """Print the AI response using rich formatting.
       This function NO LONGER handles a prefix; prefix should be printed by the caller.

    Args:
        ai_response (str): The raw response string from the AI, (cleaned of any initial [AI] by caller).
        to_stderr (bool): If True, print to stderr.
    """
    console = Console(file=sys.stderr if to_stderr else None, force_terminal=True if to_stderr else False)
    home = os.path.expanduser("~")

    def home_replace(text):
        return re.sub(rf"{re.escape(home)}", "~", text)

    # AI response is now expected to be pre-cleaned by the caller if necessary.
    processed_ai_response = ai_response

    # Ensure response starts on a new line IF a prefix was printed by the caller.
    # However, this function doesn't know if a prefix was printed.
    # The caller should handle newlines appropriately.
    # For now, we assume the caller printed a prefix ending with a space or newline.

    code_block_pattern = re.compile(r'```(bash|sh)?\n?([\s\S]*?)```')
    last_end = 0
    command_count = 0
    content_printed = False

    # If there are code blocks, we'll handle them separately
    has_code_blocks = bool(code_block_pattern.search(processed_ai_response))

    # If there are no code blocks, and it's a simple text response, display it in a panel
    if not has_code_blocks and processed_ai_response.strip():
        console.print(Panel(
            home_replace(processed_ai_response.strip()),
            title="[bold green]AI Response[/bold green]",
            title_align="center",
            border_style="green",
            padding=(1, 2),
            expand=False
        ))
        return

    for match in code_block_pattern.finditer(processed_ai_response):
        before = processed_ai_response[last_end:match.start()]
        if before.strip():
            # Display non-code explanations in a panel
            console.print(Panel(
                home_replace(before.strip()),
                title="[bold green]AI Explanation[/bold green]",
                title_align="center",
                border_style="green",
                padding=(1, 2),
                expand=False
            ))
            content_printed = True

        code = match.group(2)
        # Split code block into lines and display each command separately if valid
        block_has_command = False
        temp_command_buffer = []
        for line in code.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                if stripped.startswith('#') : temp_command_buffer.append(Syntax(home_replace(stripped), "bash", theme="monokai"))
                continue
            if is_likely_command(stripped):
                # Print any preceding comments in the block
                for comment_syntax in temp_command_buffer:
                    console.print(comment_syntax)
                temp_command_buffer = []
                console.print(Panel(Syntax(home_replace(stripped), "bash", theme="monokai", line_numbers=False),
                                   title="Command", border_style="yellow"))
                command_count += 1
                block_has_command = True
            else:
                 temp_command_buffer.append(Syntax(home_replace(stripped), "bash", theme="monokai"))

        # If the block had commands, and there are still comments in buffer, print them (comments after last command)
        if block_has_command:
            for item_syntax in temp_command_buffer:
                console.print(item_syntax)
        # If the entire block had no commands, print it as a single syntax block
        elif not block_has_command and code.strip():
            console.print(Syntax(home_replace(code.strip()), "bash", theme="monokai", background_color="default", line_numbers=False))

        content_printed = True
        last_end = match.end()

    after = processed_ai_response[last_end:]
    if after.strip():
        # Display trailing explanations in a panel
        console.print(Panel(
            home_replace(after.strip()),
            title="[bold green]AI Explanation[/bold green]",
            title_align="center",
            border_style="green",
            padding=(1, 2),
            expand=False
        ))
        content_printed = True

    if not content_printed and processed_ai_response: # If loop didn't run but there was non-whitespace response
        stripped_response = home_replace(processed_ai_response.strip())
        lines = stripped_response.splitlines()
        # Check if the entire response, after stripping, is a single line and that line is a command.
        if len(lines) == 1 and lines[0].strip() and is_likely_command(lines[0].strip()):
            console.print(Panel(Syntax(lines[0].strip(), "bash", theme="monokai", line_numbers=False),
                               title="Command", border_style="yellow"))
        else: # Otherwise, print as plain text in a panel
            console.print(Panel(
                stripped_response,
                title="[bold green]AI Response[/bold green]",
                title_align="center",
                border_style="green",
                padding=(1, 2),
                expand=False
            ))
        content_printed = True # Ensure we mark content as printed
    elif not processed_ai_response.strip(): # If response was empty or just whitespace
        console.print() # Newline for empty responses after a prompt.

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