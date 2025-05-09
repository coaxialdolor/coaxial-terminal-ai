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

For commands like `cd` or `export` that change your shell's state, TerminalAI
will offer to copy the command to your clipboard. You can then paste and run it.
This is the primary method for handling such commands.

**(Optional) Shell Integration for Advanced Users:**
* You can still install a shell integration via option `7` in the `ai setup` menu.
* This is for advanced users who might prefer a dedicated shell function.
* Note: The primary method is copy-to-clipboard, and TerminalAI no longer outputs the specific marker (`#TERMINALAI_SHELL_COMMAND:`) that this shell function traditionally relied on.

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