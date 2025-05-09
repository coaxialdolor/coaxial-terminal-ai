# Plan: Refactor Stateful Command Handling in TerminalAI

This plan outlines the steps to rename "Forbidden Commands" to "Stateful Commands" and implement a "Copy to Clipboard" mechanism for handling them, ensuring that risky commands are still treated with appropriate caution.

## Phase 1: Refactor Terminology ("Forbidden" -> "Stateful")

1.  **In `terminalai/terminalai_cli.py`:**
    *   Rename the constant `FORBIDDEN_COMMANDS` to `STATEFUL_COMMANDS`.
    *   Rename the function `is_forbidden_command(cmd)` to `is_stateful_command(cmd)`.
    *   Update the docstring for `is_stateful_command` to: `"""Check if a command is in the stateful list (changes shell state)."""`
    *   Update the variable `forbidden` (where `is_forbidden_command` was called) to `is_cmd_stateful`.
    *   Update all related internal comments, docstrings for `install_shell_integration` and `uninstall_shell_integration`, and `argparse` help texts to use the "Stateful Command(s)" terminology.

2.  **In `README.md`:**
    *   Replace all instances of "Forbidden Command(s)" with "Stateful Command(s)".

## Phase 2: Implement "Copy to Clipboard" for Stateful Commands & Refine Logic

1.  **In `terminalai/terminalai_cli.py` (Modifying user-facing prompts and logic):**
    *   When a command `cmd_to_run` is identified as `is_cmd_stateful = True`:
        *   **A. Risk Check First:** Determine if the command is also risky: `is_cmd_risky = is_risky_command(cmd_to_run)`.
        *   **B. Handle Risky Commands:** If `is_cmd_risky` is `True`:
            *   Prompt the user with the standard risky command confirmation: `"[RISKY] This command is potentially dangerous. Are you absolutely sure? [Y/N] "`.
            *   If the user does not confirm 'y', print "Command not executed." and do not proceed further with this command.
            *   If the user confirms 'y' for the risky aspect, then proceed to the stateful command handling below.
        *   **C. Stateful Command Handling Prompt (shown if command is not risky, OR if it was risky and the user confirmed the risk):**
            *   Present the new prompt: `f"[STATEFUL COMMAND] The command '{cmd_to_run}' changes shell state. Copy to clipboard to run manually? [Y/N/S(how)] "`.
            *   If the user chooses 'Y' (Yes):
                *   (Code Mode will add a call to a clipboard utility function here).
                *   Print a confirmation: `f"Command '{cmd_to_run}' copied to clipboard. Paste it into your terminal to run."`
            *   If the user chooses 'S' (Show):
                *   Print the command directly: `f"Command to run: {cmd_to_run}"`.
            *   If the user chooses 'N' (No) or any other input:
                *   Print: "Command not executed."
        *   **D. Remove Old Mechanism:** The existing lines that print `#TERMINALAI_SHELL_COMMAND: {cmd_to_run}` and the informational message about using the shell function will be removed.
    *   This refined logic will apply to both single command suggestions and when a stateful command is selected from multiple suggestions.

2.  **Clipboard Utility (to be added by Code Mode):**
    *   A helper function to copy text to the clipboard will be implemented (e.g., using the `pyperclip` library, which would become a new dependency).

## Phase 3: Documentation Update (Post-Implementation)

1.  Update `README.md` to reflect the "Stateful Commands" terminology and the new "Copy to Clipboard" behavior.
2.  Update the interactive setup guide text within `terminalai_cli.py` similarly.
3.  Review and update `quick_setup_guide.md` for consistency.
4.  The documentation concerning the old shell integration function will need to be significantly revised or removed, as the "Copy to Clipboard" method will be the primary way to handle stateful commands.

This plan aims to improve user experience by making the handling of stateful commands more intuitive and by using clearer terminology, while maintaining safety checks for risky operations.