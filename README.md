# Terminal AI

**Bring the power of AI directly to your command line!**

TerminalAI is your intelligent command-line assistant. Ask questions in natural language, get shell command suggestions, and execute them safely and interactively. It streamlines your workflow by translating your requests into actionable commands.

```
████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██║       █████╗ ██╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║      ██╔══██╗██║
   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║      ███████║██║
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║      ██╔══██║██║
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗ ██║  ██║██║
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═╝  ╚═╝╚═╝
```

## Key Features

*   **Natural Language Interaction:** Ask questions or request actions naturally.
*   **Intelligent Command Suggestion:** Get relevant shell commands based on your query.
*   **Multiple AI Backends:** Supports OpenRouter, Gemini, Mistral, and local Ollama models.
*   **Interactive Execution:** Review and confirm commands before they run.
*   **Context-Aware:** Includes OS and current directory information in prompts to the AI.
*   **Safe Command Handling:**
    *   Non-stateful commands run directly after confirmation.
    *   Risky commands require explicit confirmation.
    *   Stateful commands (`cd`, `export`, etc.) are handled safely (see below).
*   **Multiple Modes:**
    *   **Direct Query (`ai "..."`):** Get a single response and command suggestions.
    *   **Single Interaction (`ai`):** Ask one question, get a response, and return to the shell.
    *   **Chat Mode (`ai --chat` or `ai -c`):** Persistent conversation with the AI.
*   **Easy Configuration:** `ai setup` provides a menu for API keys and settings.
*   **Optional Shell Integration:** For seamless execution of stateful commands in direct query mode.
*   **Syntax Highlighting:** Uses `rich` for formatted output.

## Installation

### Option 1: Install from PyPI (Recommended)
```sh
pip install coaxial-terminal-ai
```

### Option 2: Install from Source
```sh
git clone https://github.com/coaxialdolor/terminalai.git
cd terminalai
pip install -e .
```
This automatically adds the `ai` command to your PATH.

## Quick Setup

1.  **Install:** Use one of the methods above.
2.  **Configure API Keys:** Run `ai setup` and select option `5` to add API keys for your chosen provider(s) (e.g., Mistral, Ollama, OpenRouter, Gemini).
3.  **Set Default Provider:** In `ai setup`, select option `1` to choose which provider `ai` uses by default.
4.  **(Optional) Install Shell Integration:** See "Handling Stateful Commands" below if you want direct execution for commands like `cd` when using `ai "..."`.
5.  **Start Using:** You're ready!

See the [Quick Setup Guide](quick_setup_guide.md) for more detailed instructions.

## Usage Examples

**1. Single Interaction Mode (`ai`):** Ask one question, get an answer/commands, then return to shell.
   Flags like `-v` or `-l` can be used here.
```sh
# Basic usage
ai
AI:(mistral)> how do I list files by size?

# Request a long response
ai -l
AI:(mistral)> explain the history of Unix shells in detail
```

**2. Direct Query Mode (`ai "..."`):** Provide the query directly. This is where most flags are useful.
```sh
# Simple query
ai "find all python files modified in the last day"

# Auto-confirm non-risky command execution
ai -y "show current disk usage"
# (Example: If AI suggests 'df -h', it will run without a [Y/n] prompt)

# Request verbose output
ai -v "explain the concept of inodes"

# Request long output
ai -l "explain the difference between TCP and UDP"

# Combine flags: Auto-confirm and Verbose
ai -y -v "create a new directory called 'test_project' and list its contents"
# (Example: If AI suggests 'mkdir test_project && ls test_project', it will run without a prompt)
```

**3. Chat Mode (`ai --chat` or `ai -c`):** Have a persistent conversation.
```sh
# Start a normal chat
ai --chat
# Or use the alias 'ai-c' if configured via shell integration setup
# ai -c

# Start chat requesting verbose responses by default
ai -c -v
AI:(mistral)> Tell me about this project.
# ... AI response ...
AI:(mistral)> how can I contribute?
# ... AI response ...
# (Type 'exit' or 'q' to quit chat)
```

**4. Setup Menu (`ai setup`):** Configure providers, API keys, and shell integration.
```sh
ai setup
```

**5. Show Version (`ai --version`):**
```sh
ai --version
# Output: TerminalAI version X.Y.Z
```

**6. Show Help (`ai --help` or `ai -h`):**
```sh
ai --help
# Output: Detailed help message
```

## Handling Stateful Commands (`cd`, `export`, etc.)

Commands that need to change your *current* shell's state (like changing directory with `cd` or setting environment variables with `export`) require special handling because a child process (like the `ai` script) cannot directly modify its parent shell.

TerminalAI offers two ways to handle this:

**1. Copy to Clipboard (Default & Safest)**

*   This method works in **all** modes (`ai`, `ai "..."`, `ai --chat`).
*   When a stateful command is suggested, TerminalAI will prompt you to copy it:
    ```
    [STATEFUL COMMAND] The command 'cd /path/to/dir' changes shell state. Copy to clipboard? [Y/n]:
    ```
*   Press `Y` (or Enter) to copy the command.
*   Paste (`Cmd+V` / `Ctrl+Shift+V`) the command into your shell prompt and press Enter to run it manually.

**2. Shell Integration (for `ai "..."` mode)**

*   This method enables *direct execution* of stateful commands, but **only when using the Direct Query mode (`ai "..."`)**. It does *not* work for the interactive `ai` or `ai --chat` modes.
*   **How it works:** It installs an `ai` shell function that wraps the `ai` command. When you run `ai "query"`, this function runs the script in a special mode (`--eval-mode`), captures the confirmed command, and executes it using the shell's `eval` command.
*   **Installation:**
    *   Run `ai setup`.
    *   Choose option `7` ("Install ai shell integration").
    *   Restart your shell or source your config file (e.g., `source ~/.zshrc`).
*   **Usage:** Simply run `ai "change to parent directory"`. If you confirm `cd ..`, it will execute directly in your shell.

## Contributing & Feedback

Suggestions, bug reports, and contributions are welcome! Please feel free to:
*   Open an issue on [GitHub](https://github.com/coaxialdolor/terminalai).
*   Contact the author via email (you can find the email on the GitHub profile).

## Disclaimer

**TerminalAI is provided as-is without any warranties. Use at your own risk.**

Always review commands suggested by the AI before executing them, especially those marked as [RISKY] or [STATEFUL]. The developers are not responsible for any data loss, system damage, or other issues that may arise from using this tool.