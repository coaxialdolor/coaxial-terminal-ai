# Project Plan: TerminalAI

## Step 1: Initialize Repository
- [x] Create a new folder: `mkdir terminalai && cd terminalai`
- [x] Create README.md with an initial project description.
- [ ] Initialize Git repo: `git init`
- [ ] Create project_plan.md to document steps, marking completed ones.
- [ ] First commit: `git add . && git commit -m "Initialize repository"`

## Step 2: Setup Python Package
- [ ] Create terminalai.py with basic command input handling.
- [ ] Define CLI entry point with argparse for handling ai commands.
- [ ] Set up setup.py for pip installation, ensuring PATH integration.
- [ ] Commit changes: `git add . && git commit -m "Set up Python package"`

## Step 3: Implement AI Provider Selection
- [ ] Create config.py to manage API keys and default provider settings.
- [ ] Implement ai setup for choosing between OpenRouter, Gemini, Mistral, or local Ollama models.
- [ ] Allow switching default provider via `ai setup --set-default <provider>`.
- [ ] Commit changes: `git add . && git commit -m "Add AI provider selection"`

## Step 4: Implement AI Query Handling
- [ ] Write function to send user queries to the chosen AI provider.
- [ ] Ensure requests are formatted correctly for each provider’s API.
- [ ] Commit changes: `git add . && git commit -m "Implement AI query handling"`

## Step 5: Terminal Command Execution
- [ ] Detect when the AI suggests a terminal command.
- [ ] Ask for user confirmation before execution (unless -y is used).
- [ ] Use subprocess.run() to safely execute commands.
- [ ] Commit changes: `git add . && git commit -m "Add terminal command execution"`

## Step 6: Final Testing & Packaging
- [ ] Thoroughly test interactions.
- [ ] Ensure pip installation works (`pip install .`).
- [ ] Update documentation (README.md and project_plan.md).
- [ ] Final commit: `git add . && git commit -m "Finalize TerminalAI implementation"`
