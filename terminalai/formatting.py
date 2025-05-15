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
from rich.markdown import Markdown
from rich.theme import Theme

# New color theme with better contrast and highlighting
TERMINALAI_THEME = Theme({
    "ai_response": "bold cyan",
    "command": "yellow",
    "key_info": "bold white",
    "success": "green",
    "error": "red",
    "path": "magenta",
    "explanation": "dim white",
})

def print_ai_answer_with_rich(text):
    """Print AI's answer with rich formatting.

    Args:
        text: The AI's answer text
    """
    console = Console(theme=TERMINALAI_THEME)

    # Extract and format code blocks
    parts = []
    current_pos = 0

    # Find all code blocks (```...```)
    code_block_pattern = r'```(?:bash|shell|sh|cmd|powershell|zsh|)\s*(.*?)```'
    for match in re.finditer(code_block_pattern, text, re.DOTALL):
        # Add text before the code block
        if match.start() > current_pos:
            parts.append(("text", text[current_pos:match.start()]))

        # Add the code block
        code_content = match.group(1).strip()
        parts.append(("code", code_content))
        current_pos = match.end()

    # Add any remaining text
    if current_pos < len(text):
        parts.append(("text", text[current_pos:]))

    # If no code blocks were found, just print the text
    if not parts:
        parts = [("text", text)]

    # Process and print each part
    for i, (part_type, content) in enumerate(parts):
        if part_type == "text":
            # Improve formatting of text sections
            content = format_text_section(content)
            console.print(content)
        elif part_type == "code":
            # Format command blocks
            cmd_panel = Panel(
                Syntax(content, "bash", theme="monokai", line_numbers=False),
                title="Command",
                border_style="yellow",
                expand=False
            )
            console.print(cmd_panel)

def format_text_section(text):
    """Format regular text sections with improved highlighting.

    Args:
        text: The text to format

    Returns:
        Rich Text object with formatting
    """
    result = Text()

    # Highlight file paths
    path_pattern = r'(?:\/[\w\.\-\_\/]+)|(?:~\/[\w\.\-\_\/]+)|(?:[A-Za-z]:\\(?:[^<>:"/\\|?*\n])+)'

    # Highlight commands outside of code blocks
    cmd_pattern = r'`([^`]+)`'

    # Variables to track current position
    current_pos = 0

    # Process command highlights
    for match in re.finditer(cmd_pattern, text):
        # Add text before the match
        if match.start() > current_pos:
            result.append(text[current_pos:match.start()])

        # Add the highlighted command
        cmd = match.group(1)
        result.append(cmd, style="command")

        current_pos = match.end()

    # Add any remaining text
    if current_pos < len(text):
        remaining = text[current_pos:]

        # Process path highlights in the remaining text
        current_pos_remaining = 0
        for match in re.finditer(path_pattern, remaining):
            # Add text before the path
            if match.start() > current_pos_remaining:
                result.append(remaining[current_pos_remaining:match.start()])

            # Add the highlighted path
            path = match.group(0)
            result.append(path, style="path")

            current_pos_remaining = match.end()

        # Add final remaining text
        if current_pos_remaining < len(remaining):
            result.append(remaining[current_pos_remaining:])

    return result

def create_response_panel(text, title="AI Response"):
    """Create a panel with the AI response.

    Args:
        text: The text to display
        title: The panel title

    Returns:
        A panel object
    """
    formatted_text = format_text_section(text)
    return Panel(
        formatted_text,
        title=f"[bold white]{title}[/bold white]",
        border_style="cyan",
        expand=False
    )

def print_exploration_results(results, title="Exploration Results"):
    """Print exploration results in a condensed format with height limit and scrolling.

    Args:
        results: The exploration results text
        title: The panel title
    """
    console = Console(theme=TERMINALAI_THEME)

    # Split the results by command
    sections = re.split(r'Command: (.*?)\nOutput:', results)

    if len(sections) > 1:
        summary = Text()
        for i in range(1, len(sections), 2):
            cmd = sections[i].strip()
            output = sections[i+1].strip() if i+1 < len(sections) else ""

            # Check for file counts from ls commands
            if "ls -la" in cmd and "grep" in cmd and "wc -l" in cmd:
                try:
                    # Extract and format count information
                    count = int(output.strip())

                    # Determine what we're counting based on the command pattern
                    if "grep -v '^d'" in cmd and "grep -v '^total'" in cmd and "grep -v '^\\.'" in cmd:
                        summary.append(f"\n• Files in ", style="explanation")
                    elif "grep '^d'" in cmd and "grep -v '^\\.\\.'" in cmd and "grep -v '^\\.$'" in cmd and "grep -v '^d.* \\.'" in cmd:
                        summary.append(f"\n• Folders in ", style="explanation")
                    elif "grep -v '^d'" in cmd and "grep -v '^total'" in cmd and "grep '^\\." in cmd:
                        summary.append(f"\n• Hidden files in ", style="explanation")
                    elif "grep '^d'" in cmd and "grep '^\\.\\|^d.* \\.'" in cmd:
                        summary.append(f"\n• Hidden folders in ", style="explanation")
                    elif "grep -v '^total'" in cmd and "grep -v '^\\.$'" in cmd and "grep -v '^\\.\\.'" in cmd:
                        summary.append(f"\n• Total items in ", style="explanation")
                    else:
                        summary.append(f"\n• Items in ", style="explanation")

                    path = cmd.split('ls -la ')[1].split(' |')[0].strip()
                    summary.append(f"{path}", style="path")
                    summary.append(f": ", style="explanation")
                    summary.append(f"{count}", style="key_info")
                    summary.append("\n")
                    continue
                except (ValueError, IndexError):
                    pass  # Fall back to default formatting if parsing fails

            # Check for file/folder listings
            elif ("ls -p" in cmd or "ls -la" in cmd) and "wc -l" not in cmd:
                if not output.strip():
                    continue  # Skip empty outputs

                if "ls -p" in cmd and "grep -v /" in cmd:
                    summary.append(f"\n• Files found: ", style="explanation")
                elif "ls -p" in cmd and "grep '/$'" in cmd:
                    summary.append(f"\n• Folders found: ", style="explanation")
                elif "ls -la" in cmd and "grep '^d'" in cmd and "grep -v '^\\.\\.'" in cmd and "grep -v '^\\.$'" in cmd and "grep -v '^\\." in cmd:
                    summary.append(f"\n• Folders found: ", style="explanation")
                elif "ls -la" in cmd and "grep -v '^d'" in cmd and "grep -v '^total'" in cmd and "grep '^\\." in cmd:
                    summary.append(f"\n• Hidden files found: ", style="explanation")
                elif "ls -la" in cmd and "grep '^d'" in cmd and "grep '^\\.\\|^d.* \\.'" in cmd:
                    summary.append(f"\n• Hidden folders found: ", style="explanation")
                else:
                    summary.append(f"\n• Items found: ", style="explanation")

                summary.append(f"\n", style="explanation")

                # Format the file/folder list nicely
                items = output.strip().split('\n')
                for item in items:
                    if item:
                        # Extract just the filename from the path
                        basename = os.path.basename(item.strip())
                        summary.append(f"  - {basename}\n", style="key_info")
                continue

            # File content handling
            elif "find" in cmd and "xargs cat" in cmd:
                if output and "No text files found" not in output:
                    summary.append(f"\n• Content of text file: ", style="explanation")
                    # Limit length of output for display
                    content_preview = output.strip()
                    if len(content_preview) > 500:
                        content_preview = content_preview[:500] + "..."
                    summary.append(f"\n{content_preview}\n", style="key_info")
                continue

            # Legacy find count handling for backward compatibility
            elif "find" in cmd and "type f" in cmd and "wc -l" in cmd:
                try:
                    # Extract and format file count information
                    file_count = int(output.strip())

                    # Check if we're counting hidden files specifically
                    if "-name '.*'" in cmd:
                        summary.append(f"\n• Hidden files in ", style="explanation")
                    else:
                        summary.append(f"\n• Files in ", style="explanation")

                    path = cmd.split('find ')[1].split(' -maxdepth')[0].split(' -type')[0].strip()
                    summary.append(f"{path}", style="path")
                    summary.append(f": ", style="explanation")  # Remove descriptive text
                    summary.append(f"{file_count}", style="key_info")
                    summary.append("\n")
                    continue
                except (ValueError, IndexError):
                    pass  # Fall back to default formatting if parsing fails

            elif "find" in cmd and "type d" in cmd and "wc -l" in cmd:
                try:
                    # Extract and format directory count information
                    dir_count = int(output.strip())

                    # Check if we're counting hidden directories specifically
                    if "-name '.*'" in cmd:
                        summary.append(f"\n• Hidden folders in ", style="explanation")
                    else:
                        summary.append(f"\n• Folders in ", style="explanation")

                    path = cmd.split('find ')[1].split(' -maxdepth')[0].split(' -type')[0].strip()
                    summary.append(f"{path}", style="path")
                    summary.append(f": ", style="explanation")  # Remove descriptive text
                    summary.append(f"{dir_count}", style="key_info")
                    summary.append("\n")
                    continue
                except (ValueError, IndexError):
                    pass  # Fall back to default formatting if parsing fails

            # Check for total count (including hidden)
            elif "ls -la" in cmd and "grep" in cmd and "wc -l" in cmd:
                try:
                    total_count = int(output.strip())
                    summary.append(f"\n• Total items in ", style="explanation")
                    path = cmd.split('ls -la ')[1].split(' |')[0].strip()
                    summary.append(f"{path}", style="path")
                    summary.append(f" (including hidden): ", style="explanation")
                    summary.append(f"{total_count}", style="key_info")
                    summary.append("\n")
                    continue
                except (ValueError, IndexError):
                    pass  # Fall back to default formatting if parsing fails

            # Check for file/folder listings
            elif "find" in cmd and "-type" in cmd and "wc -l" not in cmd:
                if not output.strip():
                    continue  # Skip empty outputs

                if "-type f" in cmd:
                    if "-name '.*'" in cmd:
                        summary.append(f"\n• Hidden files found in ", style="explanation")
                    else:
                        summary.append(f"\n• Files found in ", style="explanation")
                elif "-type d" in cmd:
                    if "-name '.*'" in cmd:
                        summary.append(f"\n• Hidden folders found in ", style="explanation")
                    else:
                        summary.append(f"\n• Folders found in ", style="explanation")
                else:
                    summary.append(f"\n• Items found in ", style="explanation")

                path = cmd.split('find ')[1].split(' -maxdepth')[0].split(' -type')[0].strip()
                summary.append(f"{path}", style="path")
                summary.append(f":\n", style="explanation")

                # Format the file/folder list nicely
                items = output.strip().split('\n')
                for item in items:
                    if item:
                        # Extract just the filename from the path
                        basename = os.path.basename(item)
                        summary.append(f"  - {basename}\n", style="key_info")
                continue

            # Default formatting for other commands
            if output:
                summary.append(f"\n• {cmd}", style="command")

                # Truncate long outputs
                if len(output) > 300:
                    output = output[:300] + "..."

                summary.append(f": {output}\n")

        if summary:
            # Remove redundant "(at root level)" text if present
            summary_text = summary.plain
            summary_text = summary_text.replace(" (at root level)", "")

            # Create a new Text object with the cleaned text
            cleaned_summary = Text(summary_text)
            for span in summary.spans:
                # Adjust spans for removed text
                if "(at root level)" in summary.plain[span.start:span.end]:
                    # Skip this span as it contains text we're removing
                    continue
                cleaned_summary.stylize(span.style, span.start, span.end)

            # Create the panel with fixed height and scrollable content
            panel_height = min(20, cleaned_summary.plain.count('\n') + 2)  # Limit height to 20 lines max

            panel = Panel(
                cleaned_summary,
                title=f"[bold white]{title}[/bold white]",
                border_style="blue",
                expand=False,
                height=panel_height  # Set fixed height
            )
            console.print(panel)

            # If content is larger than panel, add a note
            if cleaned_summary.plain.count('\n') + 2 > panel_height:
                console.print("[dim]Note: More results available but not shown. The output has been truncated.[/dim]")
    else:
        # No valid sections found
        console.print(f"[dim]{results}[/dim]")

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