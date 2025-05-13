# Plan: File Reading and Contextual Summarization Feature for TerminalAI

This document outlines the plan to implement a feature enabling TerminalAI to read specified files, understand their content in the context of the current project, and provide explanations or summaries.

## 1. Goals

*   Allow users to ask TerminalAI to read a specific file.
*   Enable TerminalAI to summarize or explain the file's content.
*   The explanation should be context-aware, considering the project structure and potential interactions with other files (e.g., if it's a settings file for an app in the current directory).
*   Provide information about other files referenced or called from the specified file.

## 2. User Interaction

We need a way for users to invoke this feature.

### Option A: New Command-Line Flags (for Direct Query and Single Interaction modes)

Introduce new flags, for example:
`--read-file <path_to_file>`: Specifies the file to be read.
`--explain-file`: A flag to indicate the primary goal is to explain the file. The user's query would then be context for the explanation.

**Example Usage:**
```bash
# Direct Query
ai --read-file app/settings.json --explain-file "What is this file for in the 'app' project?"
ai --read-file my_script.py "Summarize this script and tell me what other modules it imports."

# Single Interaction (less direct, might be clunky)
ai --read-file app/settings.json --explain-file
AI:(provider)> What is this file for in the 'app' project?
```

### Option B: Special Command/Syntax in Query (All Modes)

Use a special prefix or command within the natural language query.

**Example Usage:**
```bash
# Direct Query / Single Interaction / Chat Mode
ai "read:app/settings.json and explain its purpose for the 'app' project"
ai "explain_file:src/utils.py what functions does it define and where are they used?"

# Chat Mode specific command
AI:(provider)> /read_explain path/to/file.py What does this do?
```

**Decision:** Option A (new flags) seems more explicit for command-line usage. For chat mode, a `/command` style could be added later. We'll start with flags for direct queries.

## 3. Implementation Steps

### 3.1. Argument Parsing (`terminalai/cli_interaction.py` or `terminalai/terminalai_cli.py`)

*   Modify `parse_args()` in `terminalai/cli_interaction.py` (or ensure `terminalai_cli.py`'s parsing is updated) to include:
    *   `--read-file <filepath>`: Argument to specify the path to the file.
    *   `--file-query <query_string>` (Optional, better name TBD): A specific query related to the file, distinct from the main AI query. If not provided, the main query is used.
    *   Alternatively, the main query `args.query` will be used as the prompt for explaining the file.

### 3.2. File Reading Logic (New Module: `terminalai/file_reader.py`)

*   Create a new file `terminalai/file_reader.py`.
*   Implement `read_project_file(filepath: str, project_root: str) -> tuple[str | None, str | None]`:
    *   Takes a relative or absolute file path and the project root.
    *   **Security:**
        *   Crucially, ensure the `filepath` is constrained within the `project_root` (or user's current working directory if no project context is defined yet) to prevent arbitrary file access (path traversal attacks). Resolve `filepath` to an absolute path and check if it starts with the resolved `project_root`.
        *   The tool will attempt to read any file type, assuming it is plain text. The main safeguards are size and UTF-8 decoding.
        *   Warn users about reading very large files. Implement a size limit (e.g., 1MB, configurable) and truncate or refuse if exceeded, informing the user.
    *   Reads the file content (attempts UTF-8 decoding).
    *   Handles `FileNotFoundError`, `PermissionError`, `UnicodeDecodeError` gracefully.

### 3.3. Contextual Analysis and Prompt Engineering (Modify `terminalai/terminalai_cli.py` and AI provider logic)

*   In `terminalai/terminalai_cli.py` (or wherever the main AI call is made):
    *   If `--read-file` is used:
        *   Call `file_reader.read_project_file()`.
        *   If successful, construct a new system prompt or augment the user query for the AI provider.
        *   The prompt should include:
            *   The user's original query (e.g., "Explain this file").
            *   The file path.
            *   The full file content (or a significant portion if very large, with a note).
            *   The current working directory (`cwd`).
            *   A specific instruction to the AI, e.g.:
                ```
                "The user has provided the content of the file '{filepath}' located in their current working directory '{cwd}'.
                File Content:
                ---
                {file_content}
                ---
                Based on this file and their query '{user_query}', please provide an explanation.
                If relevant, identify any other files or modules it appears to reference or interact with, considering standard import statements or common patterns for its file type.
                Focus on its role within a typical project structure if it seems to be part of a larger application in '{cwd}'."
                ```

### 3.4. Identifying File Interactions (Initial Simple Approach)

*   For the first iteration, the AI will be prompted to identify interactions based on the file content.
*   Future enhancements could involve:
    *   Language-specific parsing (e.g., Python's `ast` module for imports).
    *   Regex for common import/require/include statements.
    *   Searching the workspace for filenames mentioned in the text.

### 3.5. Modifying AI Provider Interaction (`terminalai/ai_providers.py`)

*   Ensure `generate_response` methods in providers can handle potentially larger inputs if full file contents are passed.
*   No major changes anticipated here for the first pass, as the main logic change is in the prompt construction.

### 3.6. Output Handling (`terminalai/terminalai_cli.py` and `terminalai/formatting.py`)

*   The AI's response will be text. Existing formatting functions should largely suffice.
*   Consider if special formatting is needed for file excerpts or lists of referenced files in the output.

## 4. Code Structure Impact

*   **New File:** `terminalai/file_reader.py`
*   **Modifications:**
    *   `terminalai/terminalai_cli.py`: Main logic for orchestrating file reading and AI prompting.
    *   `terminalai/cli_interaction.py`: Argument parsing.
    *   Potentially `terminalai/config.py` if file size limits or allowed extensions become configurable.

## 5. Security and Safety

*   **File Access:** Strictly limit file reading to the project directory/CWD. Clearly communicate this to the user.
*   **Large Files:** Implement size limits and truncation.
*   **Sensitive Information:** Remind users that the content of the file they select will be sent to the AI provider. This is similar to how their queries are sent, but file content can be much larger and more sensitive.
*   **Binary Files:** The tool will attempt to read files as UTF-8. If a file is binary or uses an incompatible encoding, an error during decoding will be caught and reported to the user. The primary safeguards against problematic binary files are the size limit and the AI potentially not understanding garbled content.

## 6. Future Enhancements

*   Advanced static analysis for call graphs (e.g., using AST for Python).
*   Allowing users to specify line ranges.
*   Interactive exploration: "You mentioned it imports `utils.py`. Can you tell me about that file too?"
*   Support for reading multiple files.
*   Integration with `/chat_mode` commands.

## 7. Example Workflow (Internal)

1.  User runs: `ai --read-file my_app/config.py "Explain this config and what uses it."`
2.  `terminalai_cli.py`: `parse_args()` gets `read_file="my_app/config.py"` and query.
3.  `terminalai_cli.py` calls `file_reader.read_project_file("my_app/config.py", os.getcwd())`.
4.  `file_reader.py`:
    *   Validates path (e.g., `os.path.abspath("my_app/config.py")` starts with `os.path.abspath(os.getcwd())`).
    *   Checks file size.
    *   Reads content of `my_app/config.py`.
    *   Returns content string.
5.  `terminalai_cli.py`: Constructs a detailed prompt for the AI, including the CWD, file path, file content, and user's query.
6.  Sends prompt to the configured AI provider.
7.  Receives response and prints using `print_ai_answer_with_rich`.

This plan provides a roadmap for implementing the desired functionality.