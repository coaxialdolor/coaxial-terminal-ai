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

## 4. Install Shell Integration (Recommended)

For technical reasons, certain commands like `cd`, `export`, etc. can't be automatically executed by TerminalAI.

* Select `7` to "Install shell integration" 
* This will add a function to your shell configuration file (`.bashrc`, `.zshrc`, etc.)
* The integration enables these special commands to work seamlessly
* After installation, restart your terminal or source your shell configuration file

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
  * For shell state-changing commands (marked with `#TERMINALAI_SHELL_COMMAND`), they'll execute automatically if shell integration is installed 