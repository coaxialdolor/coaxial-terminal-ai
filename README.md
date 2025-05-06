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
