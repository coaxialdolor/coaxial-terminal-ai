import subprocess
import platform # Import platform module to check OS
import os # Import os for path manipulation

COMMON_POWERSHELL_CMDLET_STARTS = [
    "remove-item", "get-childitem", "copy-item", "move-item", "new-item", "set-location", 
    "select-string", "get-content", "set-content", "clear-content", "start-process", 
    "stop-process", "get-process", "get-service", "start-service", "stop-service", 
    "invoke-webrequest", "invoke-restmethod", "get-command", "get-help", "test-path",
    "resolve-path", "get-date", "measure-object", "write-output", "write-host"
] # Add more as needed, ensure lowercase

def is_shell_command(text):
    # Naive check: if it starts with a common shell command or contains a pipe/redirect
    shell_keywords = ['ls', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 'cp', 'mv', 'rm', 'mkdir', 'touch', 'dir', 'del', 'copy', 'move', 'rd', 'md']
    # Added common Windows commands: dir, del, copy, move, rd (rmdir), md (mkdir)
    
    # Add PowerShell cmdlets to known keywords for the check
    # This helps avoid the "Warning: ... not a valid shell command" for these
    all_keywords = shell_keywords + COMMON_POWERSHELL_CMDLET_STARTS

    first_word_lower = text.strip().lower().split()[0] if text.strip() else ""
    
    return any(first_word_lower == cmd_start for cmd_start in all_keywords) or \
           '|' in text or '>' in text or '<' in text

def run_shell_command(cmd):
    """Execute a shell command and print its output.

    Returns True if the command succeeded, False otherwise.
    """
    current_os = platform.system()
    executable_cmd = cmd # Default to the original command
    original_cmd_for_powershell_wrapper = cmd # Store original for the wrapper

    if current_os == "Windows":
        command_parts = cmd.strip().split()
        if command_parts:
            main_cmd_lower = command_parts[0].lower()
            if main_cmd_lower == "ls":
                # Use the original 'cmd' here to preserve casing and quoting if present
                executable_cmd = f"powershell -NoProfile -Command {original_cmd_for_powershell_wrapper}"
            elif main_cmd_lower in COMMON_POWERSHELL_CMDLET_STARTS:
                 # Use the original 'cmd' here to preserve casing and quoting
                executable_cmd = f"powershell -NoProfile -Command & {{{original_cmd_for_powershell_wrapper}}}"
                # Using & { ... } ensures PowerShell treats it as a command invocation,
                # especially important if the command string contains spaces or special characters
                # that might be misinterpreted by powershell -Command without the script block.
            elif main_cmd_lower == "del":
                # Handle path normalization for 'del' on Windows
                path_to_delete = " ".join(command_parts[1:]) # Reconstruct the path part
                if path_to_delete:
                    # Resolve ~ if present
                    if path_to_delete.startswith('~') or path_to_delete.startswith('"~') or path_to_delete.startswith("'~"):
                        # Handle quoted tilde paths
                        quote_char = ''
                        actual_path = path_to_delete
                        if path_to_delete.startswith('"~') or path_to_delete.startswith("'~"):
                            quote_char = path_to_delete[0]
                            actual_path = path_to_delete[1:-1] if path_to_delete.endswith(quote_char) else path_to_delete[1:]
                        
                        if actual_path.startswith('~'): # Should be true now
                           actual_path = os.path.expanduser('~') + actual_path[1:]
                        
                        # Re-quote if originally quoted
                        if quote_char:
                            path_to_delete = f"{quote_char}{actual_path}{quote_char}"
                        else:
                            path_to_delete = actual_path
                    
                    # Replace forward slashes with backslashes
                    # Only do this if it looks like a path and not a switch
                    # A simple heuristic: if it contains '/' and not a common switch pattern like /Q, /F, /S, /A
                    # For `del`, common switches are /P, /F, /S, /Q, /A[:attributes]
                    # This is tricky. A robust way is to only normalize if tilde was present or it contains / and no known switches.
                    # For now, let's assume AI gives paths with / that need conversion for `del`.
                    # We should be careful not to replace slashes in actual switches.
                    
                    # If path_to_delete is quoted, normalize inside the quotes
                    if (path_to_delete.startswith('"') and path_to_delete.endswith('"')) or \
                       (path_to_delete.startswith("'") and path_to_delete.endswith("'")):
                        quote_char = path_to_delete[0]
                        inner_path = path_to_delete[1:-1]
                        normalized_inner_path = inner_path.replace('/', '\\')
                        path_to_delete_normalized = f"{quote_char}{normalized_inner_path}{quote_char}"
                    else:
                        # Check for unquoted paths that might contain switches
                        # If a part starts with / and is short (e.g. /Q, /F), it's likely a switch
                        parts_for_slash_check = path_to_delete.split()
                        processed_parts = []
                        for part in parts_for_slash_check:
                            if part.startswith('/') and len(part) <= 2: # e.g. /F, /Q. len(part) <=3 for /A:R etc.
                                processed_parts.append(part) # Keep as is
                            else:
                                processed_parts.append(part.replace('/', '\\'))
                        path_to_delete_normalized = " ".join(processed_parts)
                    
                    executable_cmd = f"del {path_to_delete_normalized}"

    try:
        # Show what's being executed
        print(f"\nExecuting: {executable_cmd}") # Use executable_cmd
        print("-" * 80)  # Separator line for clarity

        # Run the command
        # If executable_cmd starts with "powershell", shell=True uses cmd.exe to launch powershell.exe.
        # This is generally fine.
        # Using shell=False with the full path to powershell.exe would be more robust but more complex to set up.
        result = subprocess.run(executable_cmd, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        # Always print the output, even if it's empty
        if result.stdout:
            print(result.stdout.rstrip())
        else:
            print("Command executed successfully. No output.")

        print("-" * 80)  # Separator line for clarity
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 80)  # Separator line for clarity
        if e.stderr:
            print(f"Error: {e.stderr.strip()}")
        else:
            print(f"Command failed with exit code {e.returncode}")
        print("-" * 80)  # Separator line for clarity
        return False
