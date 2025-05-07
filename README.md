# TerminalAI

TerminalAI is a command-line AI assistant designed to interpret user requests, suggest relevant terminal commands, and execute them interactively.

## Key Features
- Installable via pip, automatically adds itself to PATH for easy use.
- Supports multiple AI providers: OpenRouter, Gemini, Mistral, and Ollama.
- `ai setup` command to manage API keys, accounts, and set the default provider.
- Executes commands only after user confirmation, unless `-y` flag is used.
- Uses Python's `subprocess.run()` for safe shell execution.

## Example Interaction
```
SYSTEMPROMPT: ai how do I see the newest file in this folder?
AI: You can run ls -lt | head -n 1 to find the newest file. Do you want me to run it? Y/N
```
If `-y` flag is used:
```
SYSTEMPROMPT: ai -y how do I see the newest file in this folder?
AI: ls -lt | head -n 1
newtext.txt
The newest file in the folder is newtext.txt
```

## Installation
```sh
pip install .
```

## Usage
```sh
ai how do I see the newest file in this folder?
ai setup --set-default gemini
```

## Running Forbidden Commands (cd, export, etc.)

Some commands (like `cd`, `export`, etc.) change your shell state and cannot be run safely by a subprocess. When TerminalAI suggests such a command, it will print a special marker:

```
#TERMINALAI_SHELL_COMMAND: cd myfolder
```

To run these commands in your current shell, add the following function to your `.bashrc` or `.zshrc`:

```sh
run_terminalai_shell_command() {
  # Run the last forbidden command output by TerminalAI
  local cmd=$(history | grep '#TERMINALAI_SHELL_COMMAND:' | tail -1 | sed 's/.*#TERMINALAI_SHELL_COMMAND: //')
  if [ -n "$cmd" ]; then
    echo "[RUNNING in current shell]: $cmd"
    eval "$cmd"
  else
    echo "No TerminalAI shell command found in history."
  fi
}
```

After you see a `#TERMINALAI_SHELL_COMMAND:` line, just run:

```
run_terminalai_shell_command
```

This will safely execute the command in your current shell context, only after your explicit confirmation.

**Warning:** Always review the command before running it, especially if it is risky (like `rm`).
