from pygments import highlight
from pygments.lexers import BashLexer, PythonLexer, TextLexer
from pygments.formatters import TerminalFormatter
import re

# ANSI color codes
AI_COLOR = "\033[96m"  # Bright cyan
COMMAND_COLOR = "\033[95;1m"  # Bright bold magenta
RESET = "\033[0m"
BOLD = "\033[1m"


def colorize_ai(text):
    return f"{AI_COLOR}{text}{RESET}"

def colorize_command(text):
    return f"{COMMAND_COLOR}{text}{RESET}"

def highlight_code_blocks(text):
    # Highlight triple backtick code blocks
    def block_replacer(match):
        code = match.group(2)
        lang = match.group(1)
        if lang == 'bash' or lang == 'sh':
            lexer = BashLexer()
        elif lang == 'python':
            lexer = PythonLexer()
        else:
            lexer = TextLexer()
        return highlight(code, lexer, TerminalFormatter())
    text = re.sub(r'```(\w+)?\n([\s\S]*?)```', block_replacer, text)

    # Highlight inline code (single backticks)
    def inline_replacer(match):
        code = match.group(1)
        return highlight(code, BashLexer(), TerminalFormatter()).strip()
    text = re.sub(r'`([^`]+)`', inline_replacer, text)
    return text
