# AI Risk Confirmation Implementation Plan

## 1. Objective

Implement a feature where, upon encountering a potentially risky command suggested by the primary AI, TerminalAI performs a secondary AI call to get a context-aware explanation of the specific risks involved. This explanation will be presented to the user before the standard confirmation prompt for the risky command.

## 2. Core Logic Flow

1.  User runs `ai` (either mode).
2.  Primary AI suggests commands.
3.  `terminalai.command_extraction.extract_commands` extracts commands.
4.  `terminalai.cli_interaction.handle_commands` receives the list of commands.
5.  Inside `handle_commands`, loop through the commands or process the single command.
6.  For each command, call `terminalai.command_extraction.is_risky_command`.
7.  **If `is_risky_command` returns `True`:**
    a.  Get the Current Working Directory (CWD) using `os.getcwd()`.
    b.  Construct a specific query for the secondary AI call (Risk Assessment Query).
    c.  Define or retrieve the specialized System Prompt for Risk Assessment (should be hardcoded).
    d.  Get the configured AI provider (e.g., using `terminalai.ai_providers.get_provider`).
    e.  Perform the secondary AI call using the provider's `generate_response` method, passing the Risk Assessment Query and the **hardcoded Risk Assessment System Prompt** (ignoring the user's default system prompt).
    f.  Handle potential errors during the secondary AI call (e.g., timeout, API error). Fall back to a static warning if needed.
    g.  Parse/clean the AI's risk explanation response.
    h.  Display the AI-generated risk explanation prominently to the user (e.g., using `rich.panel.Panel` with a warning color).
    i.  Display the standard confirmation prompt (`[Y/n/A/Q]`) for the risky command.
8.  **If `is_risky_command` returns `False`:**
    a.  Proceed with the standard confirmation/execution logic.
9.  User confirms/denies/quits.
10. Confirmed commands are executed (or prepared for `eval`).

## 3. Detailed Implementation Steps

**Target File:** `terminalai/cli_interaction.py`

**A. Define Risk Assessment System Prompt:** ✅ DONE

*   Add a constant string variable within `terminalai/cli_interaction.py` (or potentially a separate constants file if preferred) to hold the specialized system prompt.

    ```python
    _RISK_ASSESSMENT_SYSTEM_PROMPT = """
    You are a security analysis assistant. Your sole task is to explain the potential negative consequences and risks of executing the given shell command(s) within the specified user context.

    Instructions:
    - When the user query starts with the exact prefix "<RISK_CONFIRMATION>", strictly follow these rules.
    - Focus exclusively on the potential dangers: data loss, system instability, security vulnerabilities, unintended modifications, or permission changes.
    - DO NOT provide instructions on how to use the command, suggest alternatives, or offer reassurances. ONLY state the risks.
    - Be specific about the impact. Refer to the *full, absolute paths* of any files or directories that would be affected, based on the provided Current Working Directory (CWD) and the command itself.
    - If a command affects the CWD (e.g., `rm -r .`), state clearly what the full path of the CWD is and that its contents will be affected.
    - If the risks are minimal or negligible for a typically safe command, state that concisely (e.g., "Minimal risk: This command lists directory contents.").
    - Keep the explanation concise and clear. Use bullet points if there are multiple distinct risks.
    - Output *only* the risk explanation, with no conversational introduction or closing.
    """
    ```

**B. Modify `handle_commands` Function:** ✅ DONE

*   Import necessary modules: `os`, potentially `get_provider` from `terminalai.ai_providers`, `Panel` from `rich.panel`, `Text` from `rich.text`. ✅ DONE (with Step A)
*   **Identify where risky checks occur:** Locate the parts of the function that call `is_risky_command` for single commands and for commands within the multiple-command loop (`choice == 'a'` or `choice.isdigit()`). ✅ DONE (Implicitly)
*   **Before confirmation prompts for risky commands:** ✅ DONE
    1.  **Get CWD:** `cwd = os.getcwd()` ✅ DONE (Inside helper)
    2.  **Get Risky Command:** Identify the specific `cmd` string being evaluated. ✅ DONE
    3.  **Construct Risk Query:** ✅ DONE (Inside helper)
        ```python
        risk_query = f"<RISK_CONFIRMATION> Explain the potential consequences and dangers of running the following command(s) if my current working directory is '{cwd}':\n---\n{cmd}\n---"
        ```
        *(Note: Handle multi-command sequences if applicable, e.g., if checking risk for `a` before the loop)*
    4.  **Get AI Provider:** `provider = get_provider(load_config().get("default_provider", ""))` (Ensure `load_config` is available or passed in). ✅ DONE (At start of handle_commands)
    5.  **Secondary AI Call:** ✅ DONE (Inside helper)
        ```python
        risk_explanation = "Risk assessment unavailable." # Default fallback
        if provider:
            try:
                # Ensure console is defined for status context manager if provider uses it
                # console.print("[dim]Assessing command risk...[/dim]") # Optional thinking message
                risk_response = provider.generate_response(
                    risk_query,
                    system_prompt=_RISK_ASSESSMENT_SYSTEM_PROMPT, # Use the hardcoded prompt
                    verbose=False # Risk assessment should be concise
                )
                # Basic cleaning (could be more sophisticated)
                risk_explanation = risk_response.strip()
            except Exception as e:
                risk_explanation = f"Risk assessment failed: {e}"
                # Optionally log the error e
        ```
    6.  **Display Risk Explanation:** ✅ DONE (Integrated in handle_commands)
        ```python
        console.print(Panel(
            Text(risk_explanation, style="yellow"),
            title="[bold red]AI Risk Assessment[/bold red]",
            border_style="red",
            expand=False
        ))
        ```
    7.  **Proceed to Existing Confirmation:** Continue with the colored `[Y/n/A/Q]` prompt logic already implemented. ✅ DONE

*   **Refactor:** Structure the logic cleanly, potentially creating a helper function like `_get_ai_risk_assessment(command, cwd)` to avoid code duplication between single-command and multi-command handling paths. ✅ DONE (Created `_get_ai_risk_assessment`)

**C. (Optional) Add Configuration Flag:**

*   Modify `terminalai/config.py` to add a boolean flag like `enable_ai_risk_assessment` (defaulting to `True` or `False`).
*   Modify `handle_commands` to check this flag before performing the secondary AI call (steps B.4-B.6).

## 4. Considerations / Edge Cases

*   **Latency:** Secondary AI call will add delay.
*   **Cost:** May increase API costs.
*   **AI Accuracy:** The risk assessment AI might be inaccurate or hallucinate.
The hardcoded prompt aims to minimize this, but it's not guaranteed.
*   **Error Handling:** Robustly handle failures in the secondary AI call (network issues, API errors, invalid responses).
*   **Prompt Iteration:** The `_RISK_ASSESSMENT_SYSTEM_PROMPT` may need refinement based on observed AI behavior.
*   **Complex Commands:** How well will the AI analyze complex pipes, scripts, or obscure commands?
*   **User Fatigue:** Overly verbose or frequent warnings might be ignored.

## 5. Testing

*   **Manual Testing:**
    *   Test with known safe commands flagged as risky (e.g., `chmod` changing non-critical file permissions) - ensure explanation is reasonable.
    *   Test with genuinely dangerous commands (`rm -rf /`, `dd`, `mkfs`).
    *   Test the specific `cd .. && rm -r .` sequence.
    *   Test when the secondary AI call fails (e.g., temporarily disable network or use invalid API key) - check fallback.
    *   Test in different modes (`ai`, `ai "..."` with shell integration).
*   **Unit Testing (Optional but Recommended):**
    *   Test the construction of the `risk_query` string.
    *   Mock the `provider.generate_response` call to test the display logic and error handling within `handle_commands` without actual API calls.