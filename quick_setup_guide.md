# Quick Setup Guide for TerminalAI

## 1. Installation

You have two options to install TerminalAI:

**Option A: Install from PyPI (Recommended)**
```
pip install coaxial-terminal-ai
```

**Option B: Install from source**
```
git clone https://github.com/coaxialdolor/terminalai.git
cd terminalai
pip install -e .
```

## 2. Initial Configuration

In a terminal window, run:
```
ai setup
```

* Enter `5` to select "Setup API Keys"
* Select your preferred AI provider:
  * Mistral is recommended for its good performance and generous free tier limits
  * Ollama is ideal if you prefer locally hosted AI
  * You can also use OpenRouter or Gemini
* Enter the API key for your selected provider(s)
* Press Enter to return to the setup menu

## 3. Set Default Provider

* At the setup menu, select `1` to "Setup default provider"
* Choose a provider that you've saved an API key for
* Press Enter to return to the setup menu

## 4. Understanding Stateful Command Execution

There are now two ways to handle commands that change your shell's state (like `cd` or `export`):

### A. Seamless Execution via ai Shell Integration (Advanced/Recommended)

- Run `ai setup` and select option 7 to install the ai shell integration.
- This adds a shell function named `ai` to your shell config (e.g., `.zshrc` or `.bashrc`).
- After restarting your shell or sourcing your config, you can use `ai` as before:

```
ai "cd my_folder && export VAR=1"
```
- If you confirm the command, it will be executed in your current shell, and state changes will apply.
- If you cancel, nothing is executed.
- This works for Bash/Zsh. PowerShell support for seamless mode is not yet implemented.

### B. Copy to Clipboard (Default)

When TerminalAI suggests a stateful command, it will:
- Identify the command as stateful.
- Prompt you to copy the command to your clipboard (e.g., `[STATEFUL COMMAND] The command 'cd my_folder' changes shell state. Copy to clipboard to run manually? [Y/n]`).
- If you choose 'Y', the command is copied to your clipboard.
- You can then paste and run the command directly in your terminal.

## 5. Start Using TerminalAI

You're now ready to use TerminalAI! Here's how:

**Direct Query with Quotes**
```
ai "how do I find all text files in the current directory?"
```

**Interactive Mode**
```
ai
AI: What is your question?
: how do I find all text files in the current directory?
```

**Running Commands**
* When TerminalAI suggests terminal commands, you'll be prompted:
  * For a single command: Enter `Y` to run or `N` to skip
  * For multiple commands: Enter the number of the command you want to run
  * For stateful (shell state-changing) commands like `cd` or `export`, you'll be prompted to copy them to your clipboard to run manually.