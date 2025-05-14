# Release Notes - TerminalAI (Feature: File Reading)

## Version: (Feature Branch - readfiles)

Date: $(date +%Y-%m-%d)

### ✨ New Features

*   **Contextual File Reading and Explanation:**
    *   TerminalAI can now read the content of specified files and use that content as context for your queries. This allows you to ask questions about specific files, get summaries, or understand their role within your project.
    *   **Usage:** Use the new `--read-file <filepath>` flag along with your query.
        ```bash
        ai --read-file path/to/your/script.py "Explain what this Python script does."
        ai --read-file config/settings.json "Summarize the main settings in this file."
        ```
    *   The AI will receive the file's content, its path, your current working directory, and your query to provide a contextual explanation.
    *   **Security Measures:**
        *   File access is restricted to the current project directory (or subdirectories).
        *   TerminalAI now attempts to read any file type, assuming it is plain text. The AI will determine if the content is understandable.
        *   A maximum file size limit (currently 1MB) is enforced to prevent issues with very large files.
        *   The tool attempts to decode files as UTF-8. If a file is binary or uses an incompatible encoding, an error will be reported.
        *   Users will be informed if a file cannot be read due to permissions, size, type (e.g., it's a directory), or if it's not found.
*   **Automatic File Explanation Shortcut (`--explain`):**
    *   A new flag `--explain <filepath>` provides a shortcut for getting an automatic summary and contextual explanation of a specified file.
    *   TerminalAI uses a predefined internal query to ask the AI to explain the file's purpose and role, considering its content and path. This is useful for quickly understanding a file without formulating a specific question.
    *   Example:
        ```bash
        ai --explain path/to/your/module.py
        ```
    *   This feature leverages the same secure file reading capabilities as `--read-file`.
*   **Ollama Model Selection UX:**
    *   When configuring Ollama, you now select a model by number or 'c' to cancel. Invalid input is rejected and you are re-prompted until a valid choice is made.

### ⚙️ Technical Details

*   Added a new module `terminalai/file_reader.py` to handle secure file reading operations.
*   Updated `terminalai/terminalai_cli.py` to process the `--read-file` argument and augment the prompt sent to the AI provider with file content and related context.
*   Modified `terminalai/cli_interaction.py` to include the `--read-file` argument in command-line parsing and help messages.
*   Updated `terminalai/terminalai_cli.py` and `terminalai/cli_interaction.py` to also handle the `--explain` flag and its distinct prompting logic.

### 📚 Documentation

*   The `README.md` has been updated with information about the new `--read-file` flag in the "Key Features" and "Usage Examples" sections.
*   The output of `ai --help` now includes the `--read-file` flag and its description.
*   The `README.md`, `Examples_of_features_and_usage.md`, and help page now also cover the `--explain` flag.

### ✅ Testing

*   The new feature has been tested by reading a sample file (`README.md`) and requesting a summary.
*   Existing `pytest` tests have been run to ensure no regressions were introduced into the core functionality (78 passed, 1 xfailed, 1 xpassed).

---

This feature significantly enhances TerminalAI's ability to act as a coding assistant by allowing it to directly engage with the user's codebase for more targeted and informed interactions.