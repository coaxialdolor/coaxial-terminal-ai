# TerminalAI Codebase Analysis

This document provides a concise analysis of the TerminalAI codebase, focusing on its operation and shell integration.

## Core Functionality

TerminalAI acts as a command-line AI assistant. It takes user queries (natural language questions or command requests), sends them to a configured AI provider along with system context, displays the AI's response, extracts potential shell commands from the response, and facilitates their execution.

## Key Components and Workflow

1.  **Entry Point (`terminalai/terminalai_cli.py`):**
    *   Parses command-line arguments (`ai "query"`, `ai --chat`, `ai setup`, etc.).
    *   Loads configuration (`terminalai/config.py`).
    *   Determines execution mode (direct query, interactive, chat, setup).
    *   Orchestrates the main workflow.

2.  **Configuration (`terminalai/config.py`):**
    *   Manages settings like the default AI provider, API keys/hosts, and the system prompt sent to the AI.
    *   Settings are typically stored in `~/.config/terminalai/config.json`.

3.  **Context Gathering (`terminalai/shell_integration.py`):**
    *   `get_system_context()`: Determines OS (macOS, Linux, Windows), shell (zsh, bash, PowerShell), and current working directory. This info is embedded into the system prompt to give the AI context.

4.  **AI Interaction (`terminalai/ai_providers.py`):**
    *   Abstracts communication with different AI backends (OpenRouter, Gemini, Mistral, Ollama).
    *   Handles sending the prompt (user query + system context) and receiving the response.

5.  **Response Formatting (`terminalai/formatting.py`):**
    *   Uses `rich` library to display the AI's textual response with markdown formatting and syntax highlighting.

6.  **Command Extraction (`terminalai/command_extraction.py`):**
    *   `extract_commands()`: Scans the AI response for markdown code blocks (e.g., \`\`\`bash ... \`\`\`).
    *   Uses heuristics (`is_likely_command()`) to identify lines within code blocks that are likely shell commands.
    *   Filters out comments and blank lines.
    *   Identifies potentially "risky" (`is_risky_command()`) or "stateful" (`is_stateful_command()`) commands based on predefined lists (e.g., `rm`, `sudo` are risky; `cd`, `export` are stateful).

7.  **Interaction & Execution (`terminalai/cli_interaction.py`):**
    *   `handle_commands()`: Presents extracted commands to the user, indicating if they are risky or stateful. Prompts for confirmation before execution. Handles single/multiple commands and auto-confirmation (`--yes`).
    *   `run_command()`: Executes non-stateful commands in a subprocess.
    *   `interactive_mode()`: Handles the `ai` (no args) or `ai --chat` modes, providing a loop for continuous interaction.
    *   `setup_wizard()`: Provides the menu (`ai setup`) for configuration and shell integration management.

## Shell Integration Explained

The shell integration aims to allow AI-suggested commands that modify the shell environment (like `cd`, `export`, setting variables) to work correctly.

*   **Installation (`install_shell_integration()`):** Adds a shell function named `ai` to the user's shell configuration file (`.zshrc`, `.bashrc`, etc.). This function *overrides* the default behavior of the `ai` executable *when called without specific flags like `--chat` or `setup`*.
*   **Mechanism:**
    1.  When the user types `ai "some query"`, the custom `ai` *shell function* executes.
    2.  This function calls the actual `terminalai_cli.py` script but adds the `--eval-mode` flag.
    3.  Inside Python (`handle_commands()`):
        *   It detects `--eval-mode` (or the `TERMINALAI_SHELL_INTEGRATION=1` environment variable set by the function).
        *   User prompts and AI text output are printed to **stderr**.
        *   If the user confirms command execution, the command *string itself* is printed to **stdout** and the script exits.
    4.  The shell function captures the stdout using `output=$(...)`.
    5.  The shell function executes the captured command string using `eval "$output"`.
*   **Result:** Commands like `cd ..` suggested by the AI and confirmed by the user are executed by `eval` directly within the *current* shell, correctly changing the directory.
*   **Fallback (No Integration):** If the integration is not installed, `handle_commands()` detects stateful commands and prompts the user to copy them to the clipboard for manual execution, as running them in a Python subprocess would not affect the parent shell. Interactive/chat modes also default to copy-to-clipboard for stateful commands.

## Summary

TerminalAI leverages an AI provider to understand user requests and suggest shell commands. It parses these commands from the AI response and provides a user-friendly way to review and execute them. The optional shell integration uses a clever `eval $(...)` mechanism combined with redirecting script output streams (stdout vs stderr) to enable the execution of stateful commands directly within the user's current shell environment.