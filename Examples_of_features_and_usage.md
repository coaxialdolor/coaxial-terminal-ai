# Terminal AI: Features & Usage Examples

```
████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██║       █████╗ ██╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║      ██╔══██╗██║
   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║      ███████║██║
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║      ██╔══██║██║
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗ ██║  ██║██║
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═╝  ╚═╝╚═╝
```

**Bring the power of AI directly to your command line!**

TerminalAI is your intelligent command-line assistant. It streamlines your workflow by translating your natural language requests into actionable commands and providing insightful explanations.

## With Terminal AI you can:

*   Quickly chat with your favorite LLMs directly from the terminal.
*   Ask them for help with terminal commands from natural language and execute them safely.
*   Get explanations for code, scripts, or any text-based files within your project.
*   Leverage multiple AI backends (OpenRouter, Gemini, Mistral, local Ollama).
*   Review and confirm commands before execution, with special handling for risky and state-altering operations.
*   Customize the AI's behavior with system prompts and verbosity controls.
*   Seamlessly integrate with your shell for an enhanced experience (optional).

---

## Usage Examples

*(Note: Actual AI responses and command suggestions will vary based on the configured AI provider and the specifics of your query and system.)*

### 1. Direct Query Mode (`ai "..."`)

Provide your query directly in quotes. This is great for quick questions and one-off tasks.

**Simple Query:**
```bash
$ ai "find all python files modified in the last day"
[AI] To find all Python files modified in the last day, you can use the following command:
'''sh
find . -name "*.py" -mtime -1
'''
Execute command? [Y/n]: y
Executing: find . -name "*.py" -mtime -1
./terminalai/file_reader.py
./terminalai/test_command_extraction.py
... (other files)
```

**Requesting Verbose Output (`-v`):**
```bash
$ ai -v "explain the concept of inodes"
[AI] An inode (index node) is a data structure in a Unix-style file system that describes a file-system object such as a file or a directory. Each inode stores the attributes and disk block location(s) of the object's data.
... (more detailed explanation follows) ...
```

**Requesting Long/Comprehensive Output (`-l`):**
```bash
$ ai -l "explain the difference between TCP and UDP"
[AI] TCP (Transmission Control Protocol) and UDP (User Datagram Protocol) are two core protocols of the Internet protocol suite. Here's a comprehensive breakdown of their differences:

**TCP (Transmission Control Protocol):**
*   **Reliability:** TCP is a connection-oriented protocol, meaning it establishes a connection before data is sent and ensures that data arrives in order and without errors. It uses mechanisms like acknowledgments, retransmissions, and checksums.
*   **Ordered Delivery:** Guarantees that data packets are delivered to the recipient in the same order they were sent.
... (much more detail) ...

**UDP (User Datagram Protocol):**
*   **Unreliability:** UDP is a connectionless protocol. It does not guarantee delivery, order, or error checking to the same extent as TCP.
... (much more detail) ...
```

**Auto-Confirming Non-Risky Commands (`-y`):**
```bash
$ ai -y "show current disk usage"
[AI] To show the current disk usage, you can use:
'''sh
df -h
'''
[Auto-executing: df -h]
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       230G   60G  170G  27% /
... (output of df -h)
```

**Combining Flags (e.g., `-y -v`):**
```bash
$ ai -y -v "create a new directory called 'docs_project' and list its contents"
[AI] To create a new directory named 'docs_project' and then list its contents, you can use the following sequence of commands:
'''sh
mkdir docs_project && ls -la docs_project
'''
[Auto-executing: mkdir docs_project && ls -la docs_project]
total 0
drwxr-xr-x  2 user group  64 Oct 26 10:00 .
drwxr-xr-x 30 user group 960 Oct 26 10:00 ..
```

**Reading and Explaining a File (`--read-file`):**
```bash
$ ai --read-file ./scripts/backup.sh "Explain this backup script and point out potential issues."
[AI] This shell script `./scripts/backup.sh` appears to be designed to create a backup of the `/home/user/documents` directory into `/mnt/backup/docs_backup.tar.gz`.

**Script Content:**
-------------------------------------------------------
#!/bin/bash
# Simple backup script
SRCDIR=/home/user/documents
DESTFILE=/mnt/backup/docs_backup.tar.gz
tar -czf $DESTFILE $SRCDIR
echo "Backup of $SRCDIR completed to $DESTFILE"
-------------------------------------------------------

**Explanation:**
1.  `#!/bin/bash`: Specifies the interpreter for the script.
2.  `SRCDIR=...`: Defines the source directory to be backed up.
3.  `DESTFILE=...`: Defines the destination path and filename for the tarball.
4.  `tar -czf $DESTFILE $SRCDIR`: This is the core command.
    *   `c`: Creates a new archive.
    *   `z`: Compresses the archive using gzip.
    *   `f`: Specifies the archive filename.
5.  `echo ...`: Prints a confirmation message.

**Potential Issues:**
*   **Error Handling:** The script lacks error handling. If `tar` fails (e.g., disk full, permissions issue), the script will still print "Backup ... completed".
*   **Destination Exists:** It doesn't check if `$DESTFILE` already exists. Each run will overwrite the previous backup.
*   **Permissions:** The script assumes it has read access to `$SRCDIR` and write access to the directory containing `$DESTFILE`.
*   **Path Safety:** While less of an issue here as paths are hardcoded, in scripts with variable paths, quoting (`"$DESTFILE"`, `"$SRCDIR"`) is crucial.

Would you like commands to address any of these issues?
```

### 2. Single Interaction Mode (`ai`)

Run `ai` without a query to enter a single-shot interactive mode.

```bash
$ ai
AI:(mistral)> how do I list files by size, largest first?
[AI] To list files by size, with the largest ones appearing first, you can use the `du` command combined with `sort`. Here's a common way:

For the current directory, showing human-readable sizes:
'''sh
du -sh * | sort -rh
'''
- `du -sh *`: Estimates file space usage for each item in the current directory (`*`), summarizing (`s`) and in human-readable format (`h`).
- `sort -rh`: Sorts the output in reverse order (`r`) based on human-readable numbers (`h`).

Execute command? [Y/n]: n
[Cancelled]
$ # (returns to shell)
```

### 3. Chat Mode (`ai --chat` or `ai -c`)

For a persistent conversation with the AI.

```bash
$ ai --chat
TerminalAI AI Chat Mode: You are now chatting with the AI. Type 'exit' to quit.
[dim]Type 'exit', 'quit', or 'q' to return to your shell.[/dim]

AI:(mistral)> Tell me about this project.
[AI] This project, TerminalAI, aims to provide an intelligent assistant directly in your command line. It allows users to interact with AI models using natural language to get command suggestions, explanations, and perform other tasks, all within the terminal environment. It appears to be written in Python and supports various AI backends.

AI:(mistral)> how can I contribute?
[AI] Contributions to open-source projects like this are usually very welcome! Here are some general ways you might be able to contribute:

1.  **Reporting Bugs:** If you find any issues or unexpected behavior, open an issue on the project's GitHub repository.
2.  **Suggesting Features:** If you have ideas for new features or improvements, you can also suggest them via GitHub issues.
3.  **Improving Documentation:** Clear documentation is vital. If you see areas that could be clearer or more detailed, that's a great place to help.
4.  **Writing Code:** If you're comfortable with Python, you could look for issues labeled "help wanted" or "good first issue" on GitHub, or even try to implement a feature you've suggested.
5.  **Spreading the Word:** If you find the tool useful, telling others about it can also be a form of contribution!

Typically, the project's `README.md` or a `CONTRIBUTING.md` file (if it exists) will have more specific guidelines.

AI:(mistral)> exit
[bold cyan]Goodbye![/bold cyan]
$
```

### 4. Setup and Version

**Setup Menu (`ai setup`):**
Configure providers, API keys, and shell integration.
```bash
$ ai setup
# (Interactive menu appears)
```

**Show Version (`ai --version`):**
```bash
$ ai --version
TerminalAI version 0.5.0 # (Example version)
```

**Show Help (`ai --help` or `ai -h`):**
Displays a detailed help message with all available flags and modes.
```bash
$ ai --help
# (Detailed help message is printed)
```

### 5. Handling Special Commands

**Stateful Commands (e.g., `cd`, `export`):**
These change your shell's state. TerminalAI will prompt you to copy them.
```bash
$ ai "change directory to my_project"
[AI] To change your current directory to 'my_project', use:
'''sh
cd my_project
'''
[STATEFUL COMMAND] The command 'cd my_project' changes shell state. Copy to clipboard? [Y/n]: Y
[green]Command copied to clipboard. Paste and run manually.[/green]
```

**Risky Commands (e.g., `rm`, `sudo`):**
These require explicit confirmation due to their potential impact.
```bash
$ ai "delete all .tmp files in current folder"
[AI] To delete all files ending with '.tmp' in the current folder, you can use:
'''sh
rm ./*.tmp
'''
[AI Risk Assessment]
-------------------------------------------------------
Potential Dangers:
*   **Data Loss:** This command will permanently delete all files ending with the `.tmp` extension in your current working directory ('/Users/user/projects/my_app'). Once deleted, these files cannot be easily recovered.
*   **Wildcard Risk:** The wildcard `*` can be risky if not used carefully. Ensure no important files inadvertently match `*.tmp`.
-------------------------------------------------------
Execute? [y/N]: y
Executing: rm ./*.tmp
```

---
This document provides a glimpse into the capabilities of TerminalAI. Explore and enjoy a more intelligent command-line experience!