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
*   **File Reading & Explanation:**
    *   Use `--read-file <filepath>` along with your query to have the AI consider a file's content (any plain text file).
    *   Use `--explain <filepath>` for a direct summary and contextual explanation of a file (predefined query, ignores general query).
    *   Supports any plain text file; the AI attempts to interpret the content.
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
*   **Ollama Model Selection:**
    *   When configuring Ollama, you now select a model by number or 'c' to cancel. Invalid input is rejected for safety.

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

# Read and explain a file
ai --read-file ./my_script.py "Summarize this Python script and what it does"

# Get an automatic explanation of a file
ai --explain ./config/app_settings.yaml

# Ollama model selection (example):
# ai --set-ollama
# (Choose a model number, or 'c' to cancel)
```

**3. Chat Mode (`ai --chat` or `ai -c`):** Have a persistent conversation.
```