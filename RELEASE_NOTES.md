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
        *   A predefined list of allowed file extensions (e.g., `.py`, `.json`, `.md`, `.txt`) prevents accidental reading of unintended file types.
        *   A maximum file size limit (currently 1MB) is enforced to prevent issues with very large files.
        *   Users will be informed if a file cannot be read due to permissions, size, type, or if it's not found.

### ⚙️ Technical Details

*   Added a new module `terminalai/file_reader.py` to handle secure file reading operations.
*   Updated `terminalai/terminalai_cli.py` to process the `--read-file` argument and augment the prompt sent to the AI provider with file content and related context.
*   Modified `terminalai/cli_interaction.py` to include the `--read-file` argument in command-line parsing and help messages.

### 📚 Documentation

*   The `README.md` has been updated with information about the new `--read-file` flag in the "Key Features" and "Usage Examples" sections.
*   The output of `ai --help` now includes the `--read-file` flag and its description.

### ✅ Testing

*   The new feature has been tested by reading a sample file (`README.md`) and requesting a summary.
*   Existing `pytest` tests have been run to ensure no regressions were introduced into the core functionality (78 passed, 1 xfailed, 1 xpassed).

---

This feature significantly enhances TerminalAI's ability to act as a coding assistant by allowing it to directly engage with the user's codebase for more targeted and informed interactions.