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
* After setting the API key, you'll see a list of available models for that provider
* Select a model to use as the default for that provider
* Press Enter to return to the setup menu

## 3. Model Selection

TerminalAI now supports model selection for all providers:

* **Mistral**: Choose from models like mistral-medium-2505, mistral-small-2506, codestral-2508, etc.
* **Gemini**: Choose from available Gemini models
* **OpenRouter**: Choose from available OpenRouter models
* **Ollama**: Choose from locally installed models like llama3, mistral, codellama, etc.

To change models later:
* Run `ai setup` and select `5` to "Setup API Keys"
* Select your provider and you'll see available models
* Choose a different model if desired

## 5. Set Default Provider

* At the setup menu, select `1` to "Setup default provider"
* Choose a provider that you've saved an API key for
* Press Enter to return to the setup menu

## 6. Understanding Stateful Command Execution

There are now two ways to handle commands that change your shell's state (like `cd` or `export`):

### A. Seamless Execution via ai Shell Integration (Advanced/Recommended)

- Run `ai setup` and select option 7 to install the ai shell integration.
- This adds a shell function named `ai` to your shell config (e.g., `.zshrc` or `.bashrc`).
- After restarting your shell or sourcing your config, you can use `ai` as before:

```sh
aio() {
    # Bypass eval for interactive/chat/setup modes
    if [ $# -eq 0 ] || [ "$1" = "setup" ] || [ "$1" = "--chat" ] || [ "$1" = "-c" ] || [ "$1" = "ai-c" ]; then
        command ai "$@"
    else
        local output
        output=$(command ai --eval-mode "$@")
        local ai_status=$?
        if [ $ai_status -eq 0 ] && [ -n "$output" ]; then
            eval "$output"
        fi
    fi
}
```

- This ensures that interactive and chat modes (like `ai`, `ai setup`, `ai --chat`, `ai -c`, and `ai-c`) work as expected, and only normal queries use eval mode for seamless stateful command execution.

### B. Copy to Clipboard (Default)

When TerminalAI suggests a stateful command, it will:
- Identify the command as stateful.
- Prompt you to copy the command to your clipboard (e.g., `[STATEFUL COMMAND] The command 'cd my_folder' changes shell state. Copy to clipboard to run manually? [Y/n]`).
- If you choose 'Y', the command is copied to your clipboard.
- You can then paste and run the command directly in your terminal.

## 7. Start Using TerminalAI

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

## Improved Shell Integration and Command Formatting

- With the latest shell integration, stateful commands (like `cd`, `export`, etc.) are now executable in all modes (including interactive and multi-command selection) if the integration is installed.
- The AI is instructed to always put each command in its own code block, with no comments or explanations inside. Explanations must be outside code blocks.
- If the AI puts multiple commands in a single code block, TerminalAI will still extract and show each as a separate command for selection and execution.

### Examples

**Correct (multiple commands):**
```bash
ls
```
```bash
ls -l
```
Explanation: The first command lists files, the second lists them in long format.

**Incorrect:**
```bash
# List files
ls
# List files in long format
ls -l
```
(Never put comments or multiple commands in a single code block.)
