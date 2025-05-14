# Quick Setup Guide for TerminalAI

This guide helps you get TerminalAI installed and configured quickly.

## 1. Installation

Choose one method:

**Option A: Install from PyPI (Recommended)**
```sh
pip install coaxial-terminal-ai
```

**Option B: Install from Source**
```sh
git clone https://github.com/coaxialdolor/terminalai.git
cd terminalai
pip install -e .
```
The `ai` command should now be available in your terminal.

## 2. Initial Configuration - API Keys

TerminalAI needs access to an AI provider.

1.  Run `ai setup` in your terminal.
2.  Select option `5` ("Setup API Keys").
3.  Choose the provider you want to configure (e.g., Mistral, Ollama, Gemini, OpenRouter).
4.  Enter the required API key or host information when prompted.
    *   *Mistral* is often a good starting point due to performance and free tier.
    *   *Ollama* is great for running local models.
5.  Repeat for any other providers you wish to use.
6.  Press Enter to return to the main setup menu.
7.  When configuring Ollama, you will now select a model by number or 'c' to cancel. Invalid input is rejected for safety.

## 3. Set Default Provider

Tell TerminalAI which configured provider to use by default.

1.  In the `ai setup` menu, select option `1` ("Set default provider").
2.  Choose the number corresponding to your preferred provider.
3.  Press Enter to confirm and return to the menu.
4.  Exit the setup menu (option `12`).

## 4. Understanding Command Execution

TerminalAI helps you run commands suggested by the AI.

*   **Normal Commands (e.g., `ls`, `grep`, `mkdir`):** After the AI suggests the command, you'll be asked to confirm (`Execute? [Y/n]:`). Press `Y` or Enter to run it, `N` to skip.
*   **Risky Commands (e.g., `rm`, `sudo`):** These require explicit confirmation (`Execute? [y/N]:`). You must type `y` to run them.
*   **Stateful Commands (e.g., `cd`, `export`):** These need to change your *current* shell's state. How they are handled depends on the mode you used:

    *   **Default Behavior (All Modes - `ai`, `ai --chat`, `ai "..."` without shell integration):** TerminalAI cannot directly run these. It will prompt you to copy the command to your clipboard:
        ```
        [STATEFUL COMMAND] The command 'cd /some/dir' changes shell state. Copy to clipboard? [Y/n]:
        ```
        Press `Y` or Enter to copy, then paste (`Cmd+V` / `Ctrl+Shift+V`) into your shell and run it manually.

    *   **Shell Integration Behavior (`ai "..."` ONLY):** If you install the optional shell integration (see Step 5), stateful commands suggested in *Direct Query mode* (`ai "..."`) will execute directly in your shell after you confirm `Y`. This integration does *not* affect the `ai` or `ai --chat` modes.

## 5. (Optional) Install Shell Integration

If you want stateful commands (like `cd`) to run directly *when using the `ai "..."` format*, you can install the shell integration.

1.  Run `ai setup`.
2.  Choose option `7` ("Install ai shell integration").
3.  Follow the instructions (usually involves restarting your shell or running `source ~/.your_shell_rc_file`).

**Remember:** This only affects `ai "..."` commands. Interactive modes (`ai`, `ai --chat`) will still use the copy-to-clipboard method for stateful commands.

## 6. Start Using TerminalAI!

You're ready to go!

**File Reading & Explanation:**
```sh
# Read and explain a file
ai --read-file ./my_script.py "Summarize this Python script and what it does"
# Get an automatic explanation of a file
ai --explain ./config/app_settings.yaml
```

**Single Interaction:**
```sh
ai
AI:(mistral)> list files bigger than 10MB
```
*(Exits after handling the response)*

**Direct Query:**
```sh
ai "how to install brew on macos"
```
*(Exits after handling the response. Runs `cd` directly if integration installed)*

**Chat Mode:**
```sh
ai --chat
AI:(mistral)> explain the code in cli_interaction.py
```
*(Stays running until you type `exit` or `q`)*

## 7. Advanced: Reverting to Previous States

If you want to experiment with new features or merges, you can create a backup branch of your current main branch before merging. This allows you to easily revert to a previous state if needed:

```sh
# Create a backup branch before merging
git checkout main
git checkout -b main-backup-before-merge
git push -u origin main-backup-before-merge
# Merge your feature branch as usual
```
To revert, simply check out the backup branch.
