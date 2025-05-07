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
- Shell integration for executing state-changing commands (cd, export, etc.)

## Installation

From the repository:
```sh
git clone https://github.com/coaxialdolor/terminalai.git
cd terminalai
pip install -e .
```

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

# Install shell integration for forbidden commands
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
4. **Forbidden Commands**: Commands that change shell state (like `cd`) will be marked with a special marker

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

## Running Forbidden Commands (cd, export, etc.)

Some commands change your shell state and cannot be run by a subprocess. TerminalAI marks these with:

```
#TERMINALAI_SHELL_COMMAND: cd myfolder
```

To execute these commands, you can either:

1. **Install shell integration** (recommended):
   ```sh
   ai setup --install-shell-integration
   ```
   
2. **Manually add** the following function to your `.bashrc` or `.zshrc`:
   ```sh
   run_terminalai_shell_command() {
     local cmd=$(history | grep '#TERMINALAI_SHELL_COMMAND:' | tail -1 | sed 's/.*#TERMINALAI_SHELL_COMMAND: //')
     if [ -n "$cmd" ]; then
       echo "[RUNNING in current shell]: $cmd"
       eval "$cmd"
     else
       echo "No TerminalAI shell command found in history."
     fi
   }
   ```

After you see a `#TERMINALAI_SHELL_COMMAND:` line, run:
```sh
run_terminalai_shell_command
```

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
- Shell state-changing commands are explicitly marked
- Safe subprocess execution for normal commands

## Help and Documentation

For detailed usage instructions and examples:
```sh
ai --help
```
