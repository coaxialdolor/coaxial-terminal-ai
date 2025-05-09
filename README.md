 # TerminalAI

TerminalAI is a command-line AI assistant designed to interpret user requests, suggest relevant terminal commands, and execute them interactively.

## Key Features
- Installable via pip, automatically adds itself to PATH for easy use
- Supports multiple AI providers: OpenRouter, Gemini, Mistral, and Ollama
- Interactive mode when run without arguments
- Intelligent command detection and execution flow
- Smart handling of factual vs. command-based questions
- Colored output with syntax highlighting for commands
- `ai setup` command with menu interface for configuration
- Handles stateful commands (like `cd`, `export`) by offering to copy them to your clipboard.
- Optional shell integration for advanced users (less emphasized now).

## Installation

### Option 1: Install from PyPI (Recommended)
```sh
pip install coaxial-terminal-ai
```

### Option 2: Install from source
```sh
git clone https://github.com/coaxialdolor/terminalai.git
cd terminalai
pip install -e .
```

## Quick Setup

See the [Quick Setup Guide](quick_setup_guide.md) for detailed instructions.

In brief:
1. Install TerminalAI
2. Run `ai setup` to configure your API keys
3. Set your default provider
4. Start using TerminalAI! (Shell integration is now optional and for specific use cases, see "Running Stateful Commands" section)

## Usage

### Interactive Mode
Simply run `ai` without arguments to enter interactive mode:
```sh
ai
AI: What is your question?
: how do I find all .txt files in this directory?
```

### Direct Query
```sh
ai "how do I find all .txt files in this directory?"
```

### Configuration
```sh
# Open the setup menu
ai setup

# Set a default provider directly
ai setup --set-default mistral

# Install shell integration for stateful commands
ai setup --install-shell-integration
```

### Command Flags
```sh
# Auto-confirm commands (except risky ones)
ai -y "create a temporary folder"

# Request more detailed responses
ai -v "explain how grep works"

# Get longer, more comprehensive answers
ai -l "explain docker networking"
```

## Command Execution

When TerminalAI suggests commands:

1. **Single Command**: You'll be prompted with a Y/N confirmation
2. **Multiple Commands**: You'll choose which command to run by number
3. **Risky Commands**: Always require an additional confirmation
4. **Stateful Commands**: For commands that change shell state (like `cd`, `export`), TerminalAI will offer to copy the command to your clipboard for you to run manually.

## Factual Questions vs. Commands

TerminalAI is designed to:
- Give direct factual answers to informational questions without suggesting commands
- Provide appropriate commands for task-based requests

Example:
```sh
ai "what is the capital of France?"
[AI] Paris

ai "how do I find files containing 'error' in this directory?"
[AI]
╭─── Command ───╮
│ grep -r "error" . │
╰───────────────╯
```

## Running Stateful Commands (cd, export, etc.)

Some commands, like `cd my_folder` or `export MY_VAR=value`, need to change the state of your current shell. A Python script like TerminalAI cannot directly make these changes in your active terminal session.

**How TerminalAI Handles Stateful Commands:**

When TerminalAI suggests a stateful command, it will:
1. Identify the command as stateful.
2. Prompt you with an option to copy the command to your clipboard (e.g., `[STATEFUL COMMAND] The command 'cd my_folder' changes shell state. Copy to clipboard to run manually? [Y/N/S(how)]`).
3. If you choose 'Y', the command is copied to your clipboard.
4. You can then paste (`Cmd+V` or `Ctrl+Shift+V`) and run the command directly in your terminal.

This method ensures you have full control over commands that modify your shell's environment.

**Optional Shell Integration (Advanced/Legacy):**

Previously, TerminalAI emphasized a shell integration function to handle these commands. While the code for this integration (`ai setup --install-shell-integration`) might still exist, the primary recommended method is now the copy-to-clipboard feature. The shell integration relies on parsing command history and may be less reliable or intuitive for some users. If you are an advanced user and prefer the shell function method, you can still install it via `ai setup`, but be aware that TerminalAI will no longer output the `#TERMINALAI_SHELL_COMMAND:` marker. You would need to adapt the shell function or manually identify the command if you choose this path.

## Supported AI Providers

TerminalAI supports the following providers:
- **OpenRouter** - Access to various models including GPT models
- **Mistral** - Efficient and powerful language models
- **Gemini** - Google's AI model
- **Ollama** - Run models locally

Configure your API keys through the setup menu:
```sh
ai setup
```

## Safety Features

- Commands are never executed without your explicit permission
- Risky commands (rm, chmod, etc.) require additional confirmation
- Stateful (shell state-changing) commands are handled by offering to copy them to your clipboard.
- Safe subprocess execution for normal commands

## Disclaimer

**TerminalAI is provided as-is without any warranties. Use at your own risk.**

The developers of TerminalAI cannot be held responsible for:
- Data loss
- System damage
- Any other adverse effects resulting from executing commands suggested by the AI

Always review commands before executing them, especially those that modify system files or can potentially delete data. The AI assistant makes its best effort to provide appropriate commands, but it may not always suggest the optimal or safest solution for your specific environment.

## Help and Documentation

For detailed usage instructions and examples:
```sh
ai --help
```