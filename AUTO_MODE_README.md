# TerminalAI Auto Mode

The Auto Mode feature allows TerminalAI to proactively explore your filesystem to answer questions more accurately. With Auto Mode, the AI can:

1. Execute safe commands to gather information
2. Read file contents when relevant
3. Maintain conversation context for follow-up questions
4. Automatically execute non-risky commands

## How It Works

When running in Auto Mode, TerminalAI:

1. Analyzes your question to determine what file system exploration is needed
2. Generates and safely executes appropriate commands (like `ls`, `find`, `grep`, etc.)
3. Incorporates the exploration results into a more informed answer
4. Maintains the conversation history for context in follow-up questions

## Safety Guarantees

The Auto Mode is designed with safety in mind:

- Commands that modify, delete, or move files are **never** executed automatically
- Risky commands always require explicit confirmation
- Stateful commands (like `cd`) are always presented to the user rather than executed
- All executed exploration commands are displayed to keep you informed

## Using Auto Mode

You can use Auto Mode in two ways:

### 1. Interactive Auto Mode

```
ai --auto
```

This starts an interactive session where you can ask multiple questions. The AI will maintain context between questions and can explore the filesystem to answer them better.

### 2. Direct Query Auto Mode

```
ai --auto "How many Python files are in this directory?"
```

This runs a single query in Auto Mode, exploring as needed to answer your question accurately.

## Example Use Cases

Auto Mode is particularly useful for:

- Finding and analyzing files (`"Find all Python files that import the requests library"`)
- Getting system information (`"How much disk space do I have available?"`)
- Navigating complex directories (`"What's in the src/components directory?"`)
- Examining file contents (`"What's in the README file?"`)
- Following complex inquiries that require multiple exploration steps

## Testing Auto Mode

A test script is provided to help you experiment with Auto Mode:

```
./test_auto_mode.sh
```

This script provides examples of commands and questions you can use to explore the capabilities of Auto Mode.

## Implementation Details

Auto Mode adds several key components to TerminalAI:

1. **Conversation History Tracking**: Maintains context for multi-turn conversations
2. **Proactive Exploration**: Generates and executes safe commands based on user queries
3. **Enhanced System Context**: Provides the AI with exploration results and history
4. **Command Safety Checks**: Ensures only safe, non-destructive commands are executed automatically

Auto Mode respects all the same safety guardrails as the standard mode, while adding the capability for the AI to be more proactive in gathering the information needed to answer questions accurately.