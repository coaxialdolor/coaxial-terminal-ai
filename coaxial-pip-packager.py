#!/usr/bin/env python3

import os
import sys
import subprocess
import re
import glob
import shutil
import configparser
import toml
import argparse
import datetime
import logging
import json
import threading
import time
import signal

# --- Configuration ---
# File patterns to search for version strings
# This is a limited set to avoid replacing unintended text in binary files etc.
# It includes common metadata files and source/doc files where versions might appear.
SEARCH_FILE_PATTERNS = [
    '*.py', '*.txt', '*.md', '*.rst', 'setup.py', 'setup.cfg', 'pyproject.toml', '*/__init__.py',
    'README*', 'CHANGELOG*', 'HISTORY*', 'VERSION*', 'docs/*.rst', 'docs/*.md',
    'docs/*.txt', 'docs/conf.py', '*/version.py', '*/about.py', '*/metadata.py'
]

# Additional version patterns to search for in files
VERSION_PATTERNS = [
    # Common version string patterns
    r'(?:version|__version__)\s*=\s*[\'"]([^\'"]+)[\'"]',
    r'VERSION\s*=\s*[\'"]([^\'"]+)[\'"]',
    # README/docs patterns (markdown)
    r'[Vv]ersion\s*:\s*([0-9]+\.[0-9]+\.[0-9]+(?:[\.a-zA-Z0-9]+)?)',
    r'[Vv]ersion\s*badge.*?\/v([0-9]+\.[0-9]+\.[0-9]+(?:[\.a-zA-Z0-9]+)?)(?:\/|\-)',
    # Sphinx docs patterns
    r'release\s*=\s*[\'"]([^\'"]+)[\'"]',
    # About section patterns
    r'[\'"]version[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]',
]

# Directories to exclude from the deep search
EXCLUDE_DIRS = [
    '.git', '__pycache__', '.venv', 'venv', 'env', 'dist', 'build', '*.egg-info', 'node_modules',
    '.tox', '.pytest_cache', '.coverage', 'htmlcov'
]

# Path to store run history for potential reversion
HISTORY_DIR = os.path.expanduser(os.path.join("~", ".coaxial-pip-packager", "history"))
LAST_RUN_FILE = os.path.join(HISTORY_DIR, "last_run.json")

# Config file location
CONFIG_FILE = os.path.expanduser(os.path.join("~", ".coaxial-pip-packager", "config.toml"))

# Default configuration
DEFAULT_CONFIG = {
    'patterns': {
        'search_files': SEARCH_FILE_PATTERNS,
        'version_regex': VERSION_PATTERNS,
        'exclude_dirs': EXCLUDE_DIRS
    },
    'preferences': {
        'always_prompt_for_confirmation': True,
        'default_project_path': None,
        'auto_increment': True
    },
    'spinners': {
        'use_spinners': True,
        'spinner_type': "dots"  # dots, line, arrows
    }
}

def load_config():
    """Load configuration from config file or return defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = toml.load(f)

                # Merge with defaults to ensure all keys exist
                merged_config = DEFAULT_CONFIG.copy()

                # Update with values from file
                if 'patterns' in config:
                    merged_config['patterns'].update(config['patterns'])
                if 'preferences' in config:
                    merged_config['preferences'].update(config['preferences'])
                if 'spinners' in config:
                    merged_config['spinners'].update(config['spinners'])

                logging.info("Loaded configuration from %s", CONFIG_FILE)
                return merged_config
        except (IOError, toml.TomlDecodeError, KeyError, TypeError, ValueError) as e:
            logging.warning("Error loading config file: %s", e)
            logging.warning("Using default configuration")
            return DEFAULT_CONFIG
    else:
        logging.info("No config file found, using default configuration")
        return DEFAULT_CONFIG

# Load configuration
CONFIG = load_config()

# --- Colors ---
try:
    from colorama import init, Fore, Style
    init()
    COLOR_RED = Fore.RED
    COLOR_GREEN = Fore.GREEN
    COLOR_YELLOW = Fore.YELLOW
    COLOR_BLUE = Fore.BLUE
    COLOR_CYAN = Fore.CYAN
    COLOR_MAGENTA = Fore.MAGENTA
    COLOR_BRIGHT = Style.BRIGHT
    COLOR_RESET = Style.RESET_ALL
except ImportError:
    # Fallback if colorama is not installed
    COLOR_RED = COLOR_GREEN = COLOR_YELLOW = COLOR_BLUE = COLOR_CYAN = COLOR_MAGENTA = COLOR_BRIGHT = COLOR_RESET = ''
    print("Warning: colorama not found. Output will not be colored. Install with 'pip install colorama'.")

# Simple compact ASCII art logo
def get_logo():
    return f"""
{COLOR_BRIGHT}{COLOR_BLUE}                      _       _
{COLOR_BRIGHT}{COLOR_BLUE}                     (_)     | |
{COLOR_BRIGHT}{COLOR_BLUE}  ___ ___   __ ___  ___  __ _| |{COLOR_CYAN}______
{COLOR_BRIGHT}{COLOR_BLUE} / __/ _ \\ / _` \\ \\/ / |/ _` | |{COLOR_CYAN}______|
{COLOR_BRIGHT}{COLOR_BLUE}| (_| (_) | (_| |>  <| | (_| | |
{COLOR_BRIGHT}{COLOR_BLUE} \\___\\___/ \\__,_/_/\\_\\_|\\__,_|_|


{COLOR_CYAN}       _                              {COLOR_MAGENTA}_
{COLOR_CYAN}      (_)                            {COLOR_MAGENTA}| |
{COLOR_CYAN} _ __  _ _ __ {COLOR_RESET}{COLOR_YELLOW}______{COLOR_RESET}{COLOR_MAGENTA} _ __   __ _  ___| | ____ _  __ _  ___ _ __
{COLOR_CYAN}| '_ \\| | '_ \\{COLOR_RESET}{COLOR_YELLOW}_____{COLOR_RESET}{COLOR_MAGENTA}| '_ \\ / _` |/ __| |/ / _` |/ _` |/ _ \\ '__|
{COLOR_CYAN}| |_) | | |_) |     {COLOR_MAGENTA}| |_) | (_| | (__|   < (_| | (_| |  __/ |
{COLOR_CYAN}| .__/|_| .__/      {COLOR_MAGENTA}| .__/ \\__,_|\\___|_|\\_\\__,_|\\__, |\\___|_|
{COLOR_CYAN}| |     | |         {COLOR_MAGENTA}| |                          __/ |
{COLOR_CYAN}|_|     |_|         {COLOR_MAGENTA}|_|                         |___/
{COLOR_RESET}"""

# --- Helper Functions ---

def print_color(text, color):
    """Prints text with the specified color."""
    print(f"{color}{text}{COLOR_RESET}")

def run_command(command, cwd=None, env=None, capture_output=False, shell=False):
    """Runs a shell command and checks for errors."""
    # Mask token in command if present for logging
    display_command = list(command) if isinstance(command, list) else command.split()

    # Mask any potential tokens or sensitive information in the command
    sensitive_patterns = [
        (r'ghp_[a-zA-Z0-9]{36,}', 'ghp_***'),
        (r'pypi-[a-zA-Z0-9_-]{36,}', 'pypi-***'),
        (r'([a-zA-Z0-9_-]{32,})', '***'),
        (r'(https?://)([^:]+:[^@]+)(@)', r'\1***:***\3')
    ]

    # Apply masking to each element that might contain sensitive info
    for i, arg in enumerate(display_command):
        for pattern, replacement in sensitive_patterns:
            if re.search(pattern, arg):
                if 'set-url' in display_command and i > display_command.index('set-url'):
                    display_command[i] = 'https://***:***@github.com/...'
                else:
                    display_command[i] = re.sub(pattern, replacement, arg)

    print_color(f"\n$ {' '.join(display_command) if isinstance(display_command, list) else display_command}", COLOR_BLUE)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=True,
            text=True,  # Use text mode for stdout/stderr decoding
            capture_output=capture_output,
            shell=shell
        )
        if capture_output:
            if result.stdout.strip():
                # Sanitize output before logging
                sanitized_stdout = result.stdout.strip()
                for pattern, replacement in sensitive_patterns:
                    sanitized_stdout = re.sub(pattern, replacement, sanitized_stdout)
                print(sanitized_stdout)
            if result.stderr.strip():
                sanitized_stderr = result.stderr.strip()
                for pattern, replacement in sensitive_patterns:
                    sanitized_stderr = re.sub(pattern, replacement, sanitized_stderr)
                print_color("stderr:", COLOR_YELLOW)
                print(sanitized_stderr)
        return result
    except subprocess.CalledProcessError as e:
        print_color(f"Error executing command: {e}", COLOR_RED)
        if capture_output:
            if e.stdout.strip():
                sanitized_stdout = e.stdout.strip()
                for pattern, replacement in sensitive_patterns:
                    sanitized_stdout = re.sub(pattern, replacement, sanitized_stdout)
                print_color("stdout:", COLOR_RED)
                print(sanitized_stdout)
            if e.stderr.strip():
                sanitized_stderr = e.stderr.strip()
                for pattern, replacement in sensitive_patterns:
                    sanitized_stderr = re.sub(pattern, replacement, sanitized_stderr)
                print_color("stderr:", COLOR_RED)
                print(sanitized_stderr)
        raise
    except FileNotFoundError:
        print_color(f"Error: Command not found. Make sure '{command[0] if isinstance(command, list) else command.split()[0]}' is in your PATH.", COLOR_RED)
        raise

def get_input(prompt, color=COLOR_YELLOW):
    """Gets user input with a colored prompt."""
    # Ensure input prompt ends with a space for cleaner look
    if not prompt.strip().endswith(':'):
        prompt = prompt.strip() + ': '
    return input(f"{color}{prompt}{COLOR_RESET}")

def confirm(prompt, default=True):
    """Gets a yes/no confirmation from the user."""
    if default:
        prompt_text = f"{prompt} [Y/n]: "
        options = "Yn"
    else:
        prompt_text = f"{prompt} [y/N]: "
        options = "yN"

    while True:
        response = get_input(prompt_text, color=COLOR_YELLOW).strip().lower()
        if not response:
            return default
        if response in options.lower():
            return response == options[0].lower()
        print_color("Invalid input. Please enter 'y' or 'n'.", COLOR_YELLOW)

def get_project_path():
    """Asks the user for the project path."""
    print_color("Choose the project directory:", COLOR_YELLOW)
    print_color("1. Use the current working directory", COLOR_CYAN)
    print_color("2. Specify another project folder", COLOR_CYAN)

    while True:
        choice = get_input("Enter choice (1 or 2): ")
        if choice == '1':
            path = os.getcwd()
            print_color(f"Using current directory: {path}", COLOR_GREEN)
            if not os.path.exists(path):
                print_color("Error: Current directory does not exist?", COLOR_RED)
                sys.exit(1)
            return path
        elif choice == '2':
            path = get_input("Enter the path to the project folder: ").strip()
            if os.path.isdir(path):
                print_color(f"Using specified directory: {path}", COLOR_GREEN)
                return path
            else:
                print_color(f"Error: Directory not found at '{path}'.", COLOR_RED)
        else:
            print_color("Invalid choice. Please enter 1 or 2.", COLOR_YELLOW)

def get_current_version(project_path):
    """Tries to find the current version in common project files."""
    print_color("Searching for current version...", COLOR_BLUE)

    # Priority list of files to check (relative to project_path)
    files_to_check = [
        'pyproject.toml',
        'setup.cfg',
        'setup.py',
    ]

    # Add __init__.py paths - search recursively but limit depth
    # Walk from the root, add __init__.py files found in potential package directories
    for root, dirs, files in os.walk(project_path):
        # Modify dirs in-place to prune search
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]

        if '__init__.py' in files:
            # Add the init file path relative to project_path
            rel_path = os.path.relpath(os.path.join(root, '__init__.py'), project_path)
            if rel_path not in files_to_check:  # Avoid duplicates
                files_to_check.append(rel_path)

    found_version = None
    version_source_file = None

    for file_name in files_to_check:
        file_path = os.path.join(project_path, file_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Specific parsing for known formats before general regex
                if file_name == 'pyproject.toml':
                    try:
                        data = toml.loads(content)
                        # Check common locations in pyproject.toml
                        if 'project' in data and 'version' in data['project']:
                            found_version = str(data['project']['version'])
                            version_source_file = file_name
                            break  # Found it, prioritize this
                        # Look in other common locations in TOML files
                        elif 'tool' in data and 'poetry' in data['tool'] and 'version' in data['tool']['poetry']:
                            found_version = str(data['tool']['poetry']['version'])
                            version_source_file = file_name
                            break
                        # Fallback to regex if not in standard 'project' table
                    except (toml.TomlDecodeError, KeyError) as e:
                        print_color(f"Could not parse TOML in {file_name}: {e}", COLOR_YELLOW)
                        # Continue to regex fallback

                elif file_name == 'setup.cfg':
                    try:
                        config = configparser.ConfigParser()
                        config.read_string(content)
                        if 'metadata' in config and 'version' in config['metadata']:
                            found_version = config['metadata']['version']
                            version_source_file = file_name
                            break  # Found it, prioritize this
                        # Fallback to regex if not in standard [metadata] section
                    except (configparser.Error, KeyError) as e:
                        print_color(f"Could not parse ConfigParser in {file_name}: {e}", COLOR_YELLOW)
                        # Continue to regex fallback

                # General regex search using all patterns
                for pattern in VERSION_PATTERNS:
                    match = re.search(pattern, content)
                    if match:
                        found_version = match.group(1)
                        version_source_file = file_name
                        # If it's from a high-priority file, break early
                        if file_name in ['pyproject.toml', 'setup.cfg', 'setup.py']:
                            break
                        # Otherwise store but continue checking

                # Break out of file loop if we found a version in a high-priority file
                if found_version and file_name in ['pyproject.toml', 'setup.cfg', 'setup.py']:
                    break

            except (IOError, UnicodeDecodeError) as e:
                print_color(f"Could not read or parse {file_name}: {e}", COLOR_YELLOW)

    if found_version:
        print_color(f"Found version '{found_version}' in {version_source_file}", COLOR_GREEN)
        return found_version, version_source_file  # Return both
    else:
        print_color("Could not automatically find the current version in common files.", COLOR_YELLOW)
        return None, None

def suggest_next_version(current_version):
    """Suggests the next version by incrementing the last number."""
    if not current_version:
        return "1.0.0"  # Default start version

    # Handle common version formats like X.Y.Z, X.Y.Z.postN, X.Y.ZaN, X.Y.ZbN, X.Y.ZrcN
    match = re.match(r'^(\d+(\.\d+)*)(?:(\.post)(\d+))?(?:([abc]|rc)(\d+))?$', current_version)
    if match:
        base_version_str = match.group(1)
        post_part = match.group(3)
        post_num_str = match.group(4)
        pre_release_letter = match.group(5)
        pre_release_num_str = match.group(6)

        base_parts = list(map(int, base_version_str.split('.')))

        if post_part is not None:
            # If it's a post release (e.g., 1.0.0.post1), increment the post number
            post_num = int(post_num_str) + 1 if post_num_str else 1
            return f"{base_version_str}{post_part}{post_num}"
        elif pre_release_letter is not None:
            # If it's a pre-release (a, b, rc), increment the pre-release number
            pre_release_num = int(pre_release_num_str) + 1 if pre_release_num_str else 1
            return f"{base_version_str}{pre_release_letter}{pre_release_num}"
        else:
            # If it's a standard release (X.Y.Z), increment the last number
            if base_parts:
                last_part = base_parts[-1]
                next_last_part = last_part + 1
                next_base_parts = base_parts[:-1] + [next_last_part]
                return '.'.join(map(str, next_base_parts))
            else:
                # Should not happen for a valid version string matching the regex
                print_color(f"Could not parse version parts for '{current_version}'. Suggesting 1.0.0.", COLOR_YELLOW)
                return "1.0.0"
    else:
        # Fallback for versions that don't match the pattern
        print_color(f"Could not parse '{current_version}' for auto-increment. Suggesting 1.0.0.", COLOR_YELLOW)
        return "1.0.0"

def get_new_version_input(current_version):
    """Asks the user for the new version, suggesting the incremented one."""
    suggested_version = suggest_next_version(current_version)
    current_display = current_version or 'not found'
    prompt = f"Current version is '{current_display}'. Do you want to update to suggested version '{suggested_version}'? (Y/n or specify manually): "

    while True:
        response = get_input(prompt, color=COLOR_YELLOW).strip()

        if response.lower() == 'y' or response == '': # Default is yes to suggested
            print_color(f"Using suggested version: {suggested_version}", COLOR_GREEN)
            return suggested_version
        elif response.lower() == 'n':
            manual_version = get_input("Enter the new version manually: ").strip()
            if manual_version:
                print_color(f"Using manual version: {manual_version}", COLOR_GREEN)
                return manual_version
            else:
                print_color("Manual version cannot be empty.", COLOR_YELLOW)
        else:
            # Assume the user entered a manual version string directly
            manual_version = response
            if manual_version:
                print_color(f"Using manual version: {manual_version}", COLOR_GREEN)
                return manual_version
            else:
                print_color("Input cannot be empty. Please enter a version or 'y'/'n'.", COLOR_YELLOW)

def update_version_in_files(project_path, old_version, new_version, version_source_file=None):
    """Finds and replaces the old version string with the new version string in relevant files."""
    if old_version is None:
        print_color("Cannot update version in files as old version was not found.", COLOR_RED)
        return []

    print_color(f"\nUpdating version from '{old_version}' to '{new_version}' in project files...", COLOR_BLUE)
    changed_files = []

    # Strategy: Prioritize updating the specific file where the version was found first.
    # Then do a broader search/replace in other specified files.

    files_to_process_first = []
    if version_source_file and os.path.exists(os.path.join(project_path, version_source_file)):
        files_to_process_first.append(os.path.join(project_path, version_source_file))
        print_color(f"Prioritizing update in source file: {version_source_file}", COLOR_CYAN)

    # Build the list of other files to check based on patterns, excluding the source file if already added
    other_files_to_process = set()

    # Use all file patterns from SEARCH_FILE_PATTERNS
    for pattern in SEARCH_FILE_PATTERNS:
        search_path = os.path.join(project_path, pattern)
        # Use recursive=True for patterns with '/' or '\' like '*/__init__.py'
        recursive = '/' in pattern or '\\' in pattern

        for file_path in glob.glob(search_path, recursive=recursive):
            # Check if path is within an excluded directory
            if any(excluded in file_path for excluded in EXCLUDE_DIRS):
                continue

            # Check if it's a file and not a directory
            if not os.path.isfile(file_path):
                continue

            # Only add to 'other' list if not already processed first
            if file_path not in files_to_process_first:
                other_files_to_process.add(file_path)

    # Find files with about/version information that might not match the glob patterns
    about_files = []
    for root, dirs, files in os.walk(project_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]

        for filename in files:
            if filename in ['__about__.py', '__version__.py', 'version.py', 'about.py', 'metadata.py']:
                file_path = os.path.join(root, filename)
                if file_path not in files_to_process_first and file_path not in other_files_to_process:
                    about_files.append(file_path)

    # Combine the lists (source file first, then about files, then others)
    all_files_to_process = (
        files_to_process_first +
        about_files +
        sorted(list(other_files_to_process))  # Sort others for consistent order
    )

    # Use spinner if we have many files to process
    use_spinner = len(all_files_to_process) > 5
    spinner = None

    if use_spinner:
        spinner = Spinner(message=f"Scanning {len(all_files_to_process)} files for version strings...")
        spinner.start()

    try:
        for i, file_path in enumerate(all_files_to_process):
            # Update spinner with current progress
            if spinner:
                spinner.update_message(f"Processing file {i+1}/{len(all_files_to_process)}: {os.path.basename(file_path)}")

            # Attempt to read and replace
            try:
                # Read with error handling for encoding
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                    except (IOError, UnicodeError, PermissionError) as e:
                        if spinner:
                            spinner.update_message(f"Skipping file due to encoding error: {os.path.relpath(file_path, project_path)}")
                            time.sleep(0.5)  # Brief pause so message can be seen
                        else:
                            print_color(f"Skipping file due to encoding error: {os.path.relpath(file_path, project_path)} ({e})", COLOR_YELLOW)
                        continue
                except (IOError, UnicodeError, PermissionError) as e:
                    if spinner:
                        spinner.update_message(f"Skipping file due to read error: {os.path.relpath(file_path, project_path)}")
                        time.sleep(0.5)  # Brief pause so message can be seen
                    else:
                        print_color(f"Skipping file due to read error: {os.path.relpath(file_path, project_path)} ({e})", COLOR_YELLOW)
                    continue

                # First try a simple string replace for exact matches
                if old_version in content:
                    new_content = content.replace(old_version, new_version)

                    if new_content != content:
                        # Write back the modified content
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:  # Always try writing utf-8
                                f.write(new_content)
                            if not spinner:
                                print_color(f"Updating {os.path.relpath(file_path, project_path)}", COLOR_YELLOW)
                            changed_files.append(file_path)
                            continue  # Skip to next file since we've already updated this one
                        except (IOError, UnicodeError, PermissionError) as e:
                            if spinner:
                                spinner.update_message(f"Could not write to file {os.path.relpath(file_path, project_path)}")
                                time.sleep(0.5)  # Brief pause so message can be seen
                            else:
                                print_color(f"Could not write to file {os.path.relpath(file_path, project_path)}: {e}", COLOR_RED)

                # If simple replace didn't work or didn't find anything, try pattern-based replacement
                file_changed = False
                for pattern in VERSION_PATTERNS:
                    # For each pattern, find all matches and replace them
                    if re.search(pattern, content):
                        # Use a function to replace the capture group only
                        def replace_version(match):
                            # Replace only the version part (first capture group)
                            prefix = match.string[match.start():match.start(1)]
                            suffix = match.string[match.end(1):match.end()]
                            return prefix + new_version + suffix

                        new_content = re.sub(pattern, replace_version, content)

                        if new_content != content:
                            # Write back if changed
                            try:
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                                if not file_changed:  # Only print once per file
                                    if not spinner:
                                        print_color(f"Updating {os.path.relpath(file_path, project_path)}", COLOR_YELLOW)
                                    changed_files.append(file_path)
                                    file_changed = True
                            except (IOError, UnicodeError, PermissionError) as e:
                                if spinner:
                                    spinner.update_message(f"Could not write to file {os.path.relpath(file_path, project_path)}")
                                    time.sleep(0.5)  # Brief pause so message can be seen
                                else:
                                    print_color(f"Could not write to file {os.path.relpath(file_path, project_path)}: {e}", COLOR_RED)

            except (IOError, UnicodeError, PermissionError, re.error) as e:
                # Catch any other unexpected errors during processing a file
                if spinner:
                    spinner.update_message(f"Error with {os.path.relpath(file_path, project_path)}: {str(e)[:40]}...")
                    time.sleep(0.5)  # Brief pause so message can be seen
                else:
                    print_color(f"An error occurred processing file {os.path.relpath(file_path, project_path)}: {e}", COLOR_RED)

    finally:
        # Always stop the spinner if it was started
        if spinner:
            spinner.stop()

    # Print summary of changes
    if changed_files:
        print_color(f"Updated version in {len(changed_files)} file(s):", COLOR_GREEN)
        # Only show the list if it's not too long
        if len(changed_files) <= 10:
            for file_path in changed_files:
                print_color(f"  - {os.path.relpath(file_path, project_path)}", COLOR_CYAN)
    else:
        print_color("Did not find the old version in searchable files. Ensure your version string is present.", COLOR_YELLOW)
        if old_version and not confirm(f"The string '{old_version}' was not found in any searchable files ({len(all_files_to_process)} checked). Continue anyway? (This might upload a package with the old version!)", default=False):
            print_color("Exiting.", COLOR_RED)
            sys.exit(1)

    return changed_files

def git_operations(project_path, old_version, new_version, changed_files):
    """Performs git add, commit, and push."""
    print_color("\nPerforming Git operations...", COLOR_BLUE)

    # Check if it's a git repository
    try:
        run_command(['git', 'rev-parse', '--is-inside-work-tree'], cwd=project_path, capture_output=True)
    except subprocess.CalledProcessError:
        print_color("Error: Not a git repository. Skipping git operations.", COLOR_RED)
        return False

    # Only proceed with add/commit if there were files changed or if forced
    if not changed_files:
        print_color("No version files were updated. Checking for other git changes...", COLOR_YELLOW)
        try:
            status_result = run_command(['git', 'status', '--porcelain'], cwd=project_path, capture_output=True)
            if not status_result.stdout.strip():
                print_color("No changes detected by git.", COLOR_YELLOW)
                if not confirm("No changes to commit. Continue with build/publish?", default=False):
                    print_color("Skipping git operations.", COLOR_YELLOW)
                    return False  # Signal git step was skipped, not failed
        except subprocess.SubprocessError as e:
            print_color(f"Could not check git status: {e}", COLOR_YELLOW)
            if not confirm("Could not verify git status. Continue anyway?", default=False):
                return False  # Treat as failure if status can't be checked and no files updated

    # Add all changes (including potentially other unrelated changes)
    try:
        # Add specifically the changed files if known, otherwise add all '.'
        if changed_files:
            # Add relative paths to avoid issues if project_path is absolute
            relative_changed_files = [os.path.relpath(f, project_path) for f in changed_files]
            run_command(['git', 'add'] + relative_changed_files, cwd=project_path, capture_output=True)
        else:
            run_command(['git', 'add', '.'], cwd=project_path, capture_output=True)  # Fallback to add all if no files reported updated
        print_color("Staged changes.", COLOR_GREEN)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_color(f"Error staging changes: {e}", COLOR_RED)
        if not confirm("Continue without committing/pushing?", default=False):
            return False

    # Commit changes
    commit_message = f"Bump version: {old_version} -> {new_version}" if old_version else f"Set version: {new_version}"
    try:
        commit_result = run_command(['git', 'commit', '-m', commit_message], cwd=project_path, capture_output=True)
        if "nothing to commit" in commit_result.stdout or "nothing added to commit" in commit_result.stdout:
            print_color("No changes to commit.", COLOR_YELLOW)
            if not confirm("Continue without pushing?", default=False):
                return False  # Signal git step skipped
        else:
            print_color(f"Created commit: '{commit_message}'", COLOR_GREEN)
    except subprocess.SubprocessError as e:
        print_color(f"Error committing changes: {e}", COLOR_RED)
        if not confirm("Continue without pushing?", default=False):
            return False

    # Push changes
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print_color("GITHUB_TOKEN environment variable is not set. Cannot push.", COLOR_YELLOW)  # Changed to yellow warning
        if confirm("Continue without pushing?", default=True):
            return True  # Indicate success/skipped, not failure, if user agrees
        else:
            return False  # User chose to stop because push is required

    try:
        # Get current branch
        branch_result = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path, capture_output=True)
        current_branch = branch_result.stdout.strip()
        print_color(f"Current branch: {current_branch}", COLOR_CYAN)

        # Get remote URL
        remote_url_result = run_command(['git', 'remote', 'get-url', 'origin'], cwd=project_path, capture_output=True)
        original_remote_url = remote_url_result.stdout.strip()
        print_color(f"Original remote URL: {original_remote_url}", COLOR_CYAN)

        push_successful = False  # Flag to track if push succeeded

        if original_remote_url.startswith('https://'):
            # Parse the URL
            parts = original_remote_url.split('//', 1)
            # Insert token before the host, handling potential existing user/pass
            auth_part = parts[1].split('@', 1)
            if len(auth_part) == 2:  # URL already has user@host
                print_color("Warning: Remote URL already has user/password info. Temporarily overwriting.", COLOR_YELLOW)
                host_path = auth_part[1]
            else:  # No user/pass
                host_path = auth_part[0]

            # Format token URL: https://oauth2:GITHUB_TOKEN@github.com/... or https://x-access-token:GITHUB_TOKEN@github.com/...
            # oauth2 is often preferred/newer for PATs
            token_remote_url = f"https://oauth2:{github_token}@{host_path}"

            print_color("Temporarily setting remote URL with token...", COLOR_YELLOW)
            run_command(['git', 'remote', 'set-url', 'origin', token_remote_url], cwd=project_path, capture_output=True)

            try:
                print_color(f"Pushing to origin/{current_branch}...", COLOR_BLUE)
                run_command(['git', 'push', 'origin', current_branch], cwd=project_path, capture_output=True)
                print_color("Push successful!", COLOR_GREEN)
                push_successful = True
            finally:
                # Always reset remote URL regardless of push success/failure
                print_color("Resetting remote URL...", COLOR_YELLOW)
                run_command(['git', 'remote', 'set-url', 'origin', original_remote_url], cwd=project_path, capture_output=True)

        elif original_remote_url.startswith('git@') or original_remote_url.startswith('ssh://'):
            print_color("Remote URL is SSH. Cannot inject GITHUB_TOKEN directly.", COLOR_YELLOW)
            print_color("Please ensure your SSH agent or git config is set up to authenticate.", COLOR_YELLOW)
            if confirm("Attempt SSH push?", default=True):
                try:
                    print_color(f"Pushing to origin/{current_branch} via SSH...", COLOR_BLUE)
                    run_command(['git', 'push', 'origin', current_branch], cwd=project_path, capture_output=True)
                    print_color("Push successful!", COLOR_GREEN)
                    push_successful = True
                except subprocess.SubprocessError as e:
                    print_color(f"SSH push failed: {e}", COLOR_RED)
                    # push_successful remains False
            else:
                pass  # User chose not to attempt SSH push

        else:
            print_color(f"Unsupported remote URL scheme: {original_remote_url}", COLOR_RED)
            print_color("Please ensure your remote 'origin' is an HTTPS or SSH URL.", COLOR_RED)
            # push_successful remains False

        return push_successful  # Return whether the push was successful

    except (subprocess.SubprocessError, ValueError, IndexError) as e:
        print_color(f"An error occurred during git push setup: {e}", COLOR_RED)
        return False

def build_package(project_path):
    """Builds the sdist and wheel packages."""
    print_color("\nBuilding package (sdist and wheel)...", COLOR_BLUE)

    # Clean up previous builds
    print_color("Cleaning up old build/dist directories...", COLOR_YELLOW)
    if os.path.exists(os.path.join(project_path, 'dist')):
        shutil.rmtree(os.path.join(project_path, 'dist'))
    if os.path.exists(os.path.join(project_path, 'build')):
        shutil.rmtree(os.path.join(project_path, 'build'))
    # Clean up egg-info directories (common leftover)
    for item in os.listdir(project_path):
        if item.endswith('.egg-info') and os.path.isdir(os.path.join(project_path, item)):
            shutil.rmtree(os.path.join(project_path, item))

    try:
        # Use the modern build module with spinner to show progress
        command = [sys.executable, '-m', 'build', '--sdist', '--wheel', project_path]

        # Display the command that would be run
        print_color(f"\n$ {' '.join(command)}", COLOR_BLUE)

        with Spinner(message="Building package...") as spinner:
            process = subprocess.Popen(
                command,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            # Process output in real-time to update spinner message
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Update spinner with latest status but keep it short
                    short_status = line.split("\n")[0][:50]
                    if len(short_status) == 50:
                        short_status += "..."
                    spinner.update_message(f"Building package: {short_status}")
                    # Also log the full line
                    logging.info(line)

            # Also process stderr
            for line in process.stderr:
                line = line.strip()
                if line:
                    logging.warning(line)

            # Wait for process to complete
            exit_code = process.wait()

            if exit_code != 0:
                print_color("Package build failed with exit code: " + str(exit_code), COLOR_RED)
                return False

        print_color("Package built successfully in the 'dist/' directory.", COLOR_GREEN)
        return True
    except (subprocess.SubprocessError, IOError, OSError) as e:
        print_color(f"Package build failed: {e}", COLOR_RED)
        return False

def publish_package(project_path):
    """Publishes the package to PyPI using twine."""
    print_color("\nPublishing package to PyPI...", COLOR_BLUE)

    pypi_token = os.environ.get('PYPI_TOKEN')
    if not pypi_token:
        print_color("PYPI_TOKEN environment variable is not set. Cannot publish.", COLOR_RED)
        return False

    dist_path = os.path.join(project_path, 'dist')
    packages_to_upload = glob.glob(os.path.join(dist_path, '*'))

    if not packages_to_upload:
        print_color(f"No packages found in the '{dist_path}' directory. Build the package first.", COLOR_RED)
        return False

    package_list = "\n".join([os.path.basename(p) for p in packages_to_upload])
    if not confirm(f"Are you sure you want to publish these packages to PyPI?\n{package_list}", default=False):
        print_color("Publishing cancelled by user.", COLOR_YELLOW)
        return False

    try:
        # Pass token via environment variables which twine supports
        env = os.environ.copy()
        env['TWINE_USERNAME'] = '__token__' # Standard username for token auth
        env['TWINE_PASSWORD'] = pypi_token

        # Use --verbose for better feedback
        # Pass the list of packages to upload
        command = [sys.executable, '-m', 'twine', 'upload', '--verbose'] + packages_to_upload

        # Display the masked command (hide token)
        masked_command = command.copy()
        print_color(f"\n$ {' '.join(masked_command)}", COLOR_BLUE)

        # Add specific warning about sensitive information in logs
        print_color("Note: Verbose upload logs may contain sensitive information. Logs are being sanitized but review them before sharing.", COLOR_YELLOW)

        with Spinner(message="Uploading to PyPI...") as spinner:
            process = subprocess.Popen(
                command,
                cwd=project_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            # Process output in real-time to update spinner message
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Sanitize the line to avoid logging tokens
                    sanitized_line = line
                    for pattern in [r'token:\s*\S+', r'password:\s*\S+', r'auth=([^&\s]+)', r'Authorization:\s*\S+']:
                        sanitized_line = re.sub(pattern, lambda m: m.group(0).split(':')[0] + ': <hidden>', sanitized_line)

                    # Update spinner with latest status but keep it short
                    if "uploading" in sanitized_line.lower():
                        package_name = sanitized_line.split(" ")[-1] if len(sanitized_line.split(" ")) > 1 else "package"
                        spinner.update_message(f"Uploading {package_name}...")
                    elif "100%" in sanitized_line:
                        spinner.update_message("Upload complete, processing...")
                    # Log the sanitized line
                    logging.info(sanitized_line)

            # Also process stderr and watch for network errors
            network_error = False
            for line in process.stderr:
                line = line.strip()
                if line:
                    # Sanitize stderr as well
                    sanitized_line = line
                    for pattern in [r'token:\s*\S+', r'password:\s*\S+', r'auth=([^&\s]+)', r'Authorization:\s*\S+']:
                        sanitized_line = re.sub(pattern, lambda m: m.group(0).split(':')[0] + ': <hidden>', sanitized_line)

                    logging.warning(sanitized_line)
                    if "network" in sanitized_line.lower() or "connection" in sanitized_line.lower() or "timeout" in sanitized_line.lower():
                        network_error = True

            # Wait for process to complete
            exit_code = process.wait()

            if exit_code != 0:
                if network_error:
                    print_color("Upload failed due to network issues. Please check your internet connection and try again.", COLOR_RED)
                else:
                    print_color("Package upload failed with exit code: " + str(exit_code), COLOR_RED)
                return False

        print_color("Package published successfully!", COLOR_GREEN)
        return True
    except (subprocess.SubprocessError, IOError, OSError) as e:
        print_color(f"Package publishing failed: {e}", COLOR_RED)
        return False

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Automate packaging and releasing Python packages to PyPI")
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip git operations and uploading to PyPI, only update version and build")
    parser.add_argument("--only-upload", action="store_true",
                        help="Only upload existing package to PyPI, skipping version update and build steps")
    parser.add_argument("--revert", action="store_true",
                        help="Revert the changes made in the previous run")
    parser.add_argument("--test", "--dry-run", action="store_true", dest="test_mode",
                        help="Test mode: discover and report what would change without making actual changes")
    parser.add_argument("--create-config", action="store_true",
                        help="Create a default configuration file at ~/.coaxial-pip-packager/config.toml")

    args = parser.parse_args()

    # Validate that only one special operation is requested
    if sum([args.no_upload, args.only_upload, args.revert, args.test_mode, args.create_config]) > 1:
        print_color("Error: Cannot use multiple operation flags together", COLOR_RED)
        sys.exit(1)

    return args

def create_default_config():
    """Create a default configuration file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    if os.path.exists(CONFIG_FILE):
        print_color(f"Config file already exists at {CONFIG_FILE}", COLOR_YELLOW)
        if not confirm("Overwrite existing config file?", default=False):
            print_color("Keeping existing config file.", COLOR_YELLOW)
            return False

    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            # Add comments to the configuration
            config_str = """# coaxial-pip-packager configuration file
# This file configures the behavior of the coaxial-pip-packager tool

[patterns]
# List of file patterns to search for version strings
search_files = [
    "*.py", "*.txt", "*.md", "*.rst", "setup.py", "setup.cfg", "pyproject.toml", "*/__init__.py",
    "README*", "CHANGELOG*", "HISTORY*", "VERSION*", "docs/*.rst", "docs/*.md",
    "docs/*.txt", "docs/conf.py", "*/version.py", "*/about.py", "*/metadata.py"
]

# Regular expressions to identify version strings
version_regex = [
    '(?:version|__version__)\\\\s*=\\\\s*[\\\'"]([\\\'"]+)[\\\'"]',
    'VERSION\\\\s*=\\\\s*[\\\'"]([\\\'"]+)[\\\'"]',
    '[Vv]ersion\\\\s*:\\\\s*([0-9]+\\\\.[0-9]+\\\\.[0-9]+(?:[\\\\.[a-zA-Z0-9]+)?)',
    '[Vv]ersion\\\\s*badge.*?\\\\/v([0-9]+\\\\.[0-9]+\\\\.[0-9]+(?:[\\\\.[a-zA-Z0-9]+)?)(?:\\\\/|\\\\-)',
    'release\\\\s*=\\\\s*[\\\'"]([\\\'"]+)[\\\'"]',
    '[\\\'"]\\\\\\\\\\"[\\\'"]\\\\\\\\\\"\\\\s*:\\\\s*[\\\'"]([\\\'"]+)[\\\'"]'
]

# Directories to exclude from search
exclude_dirs = [
    ".git", "__pycache__", ".venv", "venv", "env", "dist", "build", "*.egg-info", "node_modules",
    ".tox", ".pytest_cache", ".coverage", "htmlcov"
]

[preferences]
# Whether to always prompt for confirmation before critical actions
always_prompt_for_confirmation = true

# Default project path (leave as null to be prompted each time)
default_project_path = null

# Whether to auto-increment version numbers
auto_increment = true

[spinners]
# Whether to show spinners during long operations
use_spinners = true

# Type of spinner to use
# Options: "dots", "line", "arrows"
spinner_type = "dots"
"""
            f.write(config_str)

        print_color(f"Created default configuration file at {CONFIG_FILE}", COLOR_GREEN)
        print_color("You can now edit this file to customize the behavior of coaxial-pip-packager.", COLOR_CYAN)
        return True
    except (IOError, OSError, PermissionError) as e:
        print_color(f"Error creating config file: {e}", COLOR_RED)
        return False

def main():
    """Main function to run the packager."""
    display_logo()

    # Set up logging
    log_filename = setup_logging()
    print_color(f"Writing logs to {log_filename}", COLOR_CYAN)

    # Parse command-line arguments
    args = parse_arguments()

    # Handle config creation if requested
    if args.create_config:
        success = create_default_config()
        if success:
            print_color("Configuration file created successfully.", COLOR_GREEN)
        else:
            print_color("Configuration file creation failed or was cancelled.", COLOR_RED)
        return

    # Handle revert request if specified
    if args.revert:
        revert_result = revert_last_run()
        if revert_result:
            print_color("Reversion completed successfully.", COLOR_GREEN)
        else:
            print_color("Reversion failed or was cancelled.", COLOR_RED)
        return

    # Display test mode banner if enabled
    if args.test_mode:
        print_color("\n" + "="*80, COLOR_YELLOW)
        print_color(" TEST MODE ENABLED - NO ACTUAL CHANGES WILL BE MADE ", COLOR_BRIGHT + COLOR_YELLOW)
        print_color("="*80 + "\n", COLOR_YELLOW)

    original_cwd = os.getcwd()
    project_path = None
    try:
        # 1. Get project path
        project_path = get_project_path()
        # Change to project directory. Use a try/finally to ensure we change back.
        if not os.path.isdir(project_path):
            print_color(f"Error: Specified project path is not a directory: {project_path}", COLOR_RED)
            sys.exit(1)
        os.chdir(project_path)
        print_color(f"Changed working directory to: {os.getcwd()}", COLOR_CYAN)

        # If only uploading, skip version management and build steps
        if args.only_upload:
            if args.test_mode:
                print_color("\nTEST MODE: Would upload package to PyPI (skipping version management and build).", COLOR_YELLOW)
                print_color("Files that would be uploaded:", COLOR_CYAN)
                dist_path = os.path.join(project_path, 'dist')
                if os.path.exists(dist_path):
                    packages = glob.glob(os.path.join(dist_path, '*'))
                    if packages:
                        for pkg in packages:
                            print_color(f"  - {os.path.basename(pkg)}", COLOR_CYAN)
                    else:
                        print_color("  No packages found in dist/ directory", COLOR_RED)
                else:
                    print_color("  dist/ directory does not exist", COLOR_RED)
                print_color("\nTest completed. No actual changes were made.", COLOR_GREEN)
                return

            print_color("\nRunning in '--only-upload' mode. Skipping version management and build steps.", COLOR_YELLOW)
            # Check if dist directory exists
            if not os.path.exists(os.path.join(project_path, 'dist')):
                print_color("Error: No 'dist' directory found. Please build the package first or run without --only-upload flag.", COLOR_RED)
                sys.exit(1)

            # Jump directly to publish step
            publish_success = publish_package(project_path)
            if not publish_success:
                print_color("Package publishing failed.", COLOR_RED)
                sys.exit(1)

            print_color("\nUpload process completed successfully!", COLOR_GREEN)
            return

        # Normal flow for regular or --no-upload mode
        # 2. Find current version
        current_version, version_source_file = get_current_version(project_path)
        if not current_version:
            print_color("Warning: Current version not found automatically.", COLOR_YELLOW)
            print_color("Please ensure a version string exists in one of the standard locations (pyproject.toml, setup.cfg, setup.py, package/__init__.py) using 'version = \"X.Y.Z\"' or '__version__ = \"X.Y.Z\"'.", COLOR_YELLOW)

            # Option to proceed by manually providing the *old* version?
            if not confirm("Proceed by manually entering the current version string?", default=False):
                print_color("Exiting.", COLOR_RED)
                sys.exit(1)
            current_version = get_input("Enter the *current* version string manually: ").strip()
            if not current_version:
                print_color("Current version is required to proceed. Exiting.", COLOR_RED)
                sys.exit(1)
            print_color(f"Using manually entered current version: {current_version}", COLOR_YELLOW)
            version_source_file = None  # We don't know the source file if manually entered

        # 3. Get new version
        new_version = get_new_version_input(current_version)
        if not new_version:
            print_color("New version cannot be empty. Exiting.", COLOR_RED)
            sys.exit(1)

        if new_version == current_version:
            print_color("New version is the same as the current version. Nothing to update in files.", COLOR_YELLOW)
            # Ask if they still want to proceed (e.g., rebuild/re-release)
            if not confirm("Do you still want to proceed with build steps (e.g., for a re-release)?", default=False):
                print_color("Exiting.", COLOR_RED)
                sys.exit(0)
            # If they want to proceed, the rest of the script runs, but file update is skipped.
            updated_files = []  # No files were updated
        else:
            # If in test mode, we don't actually update files but simulate what would happen
            if args.test_mode:
                print_color(f"\nTEST MODE: Would update version from '{current_version}' to '{new_version}'", COLOR_YELLOW)

                # Find files that would be updated (similar to update_version_in_files but without changes)
                would_update_files = []

                with Spinner(message="Scanning for files that would be updated...") as spinner:
                    # Code similar to update_version_in_files but just for scanning
                    for pattern in SEARCH_FILE_PATTERNS:
                        search_path = os.path.join(project_path, pattern)
                        recursive = '/' in pattern or '\\' in pattern

                        for file_path in glob.glob(search_path, recursive=recursive):
                            # Skip excluded directories
                            if any(excluded in file_path for excluded in EXCLUDE_DIRS):
                                continue

                            # Skip non-files
                            if not os.path.isfile(file_path):
                                continue

                            spinner.update_message(f"Scanning: {os.path.relpath(file_path, project_path)}")

                            try:
                                # Try to read the file
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                except UnicodeDecodeError:
                                    with open(file_path, 'r', encoding='latin-1') as f:
                                        content = f.read()

                                # Check for exact version string
                                if current_version in content:
                                    would_update_files.append(file_path)
                                    continue

                                # Check for version patterns
                                for pattern in VERSION_PATTERNS:
                                    if re.search(pattern, content) and re.search(pattern, content).group(1) == current_version:
                                        would_update_files.append(file_path)
                                        break
                            except (IOError, UnicodeError, re.error, IndexError, AttributeError):
                                # Skip files with errors
                                pass

                # Display results
                print_color(f"\nTEST MODE: Would update {len(would_update_files)} file(s):", COLOR_GREEN)
                for file_path in would_update_files:
                    print_color(f"  - {os.path.relpath(file_path, project_path)}", COLOR_CYAN)

                print_color("\nTEST MODE: Would build package", COLOR_YELLOW)
                if not args.no_upload:
                    print_color("TEST MODE: Would commit changes", COLOR_YELLOW)
                    print_color("TEST MODE: Would push to remote", COLOR_YELLOW)
                    print_color("TEST MODE: Would upload to PyPI", COLOR_YELLOW)

                print_color("\nTest completed. No actual changes were made.", COLOR_GREEN)
                return

            # 4. Update version in files
            updated_files = update_version_in_files(project_path, current_version, new_version, version_source_file)
            # update_version_in_files already handles the case where old version isn't found or no files change and prompts the user.

            # Save run history for potential reversion
            if updated_files:
                save_run_history(project_path, current_version, new_version, updated_files)

        # 5. Git operations (skip if --no-upload flag is provided)
        if not args.no_upload:
            # Pass updated_files to git_operations so it knows if files were changed by the script
            git_success = git_operations(project_path, current_version, new_version, updated_files)
            # git_operations now returns True even if skipped due to user choice/no changes, but False on actual errors.
            if git_success is False:  # Only exit if there was an actual failure
                print_color("Git operations failed. Exiting.", COLOR_RED)
                sys.exit(1)
            # If git_success is True, it either worked or the user chose to skip without failing.
        else:
            print_color("\nSkipping git operations due to --no-upload flag.", COLOR_YELLOW)

        # 6. Build package
        build_success = build_package(project_path)
        if not build_success:
            print_color("Package build failed. Exiting.", COLOR_RED)
            sys.exit(1)

        # 7. Publish package (skip if --no-upload flag is provided)
        if args.no_upload:
            print_color("\nSkipping upload to PyPI due to --no-upload flag.", COLOR_YELLOW)
            print_color("\nProcess completed successfully!", COLOR_GREEN)
            print_color(f"Package version {new_version} built (but not published).", COLOR_GREEN)
            print_color("You can publish later with: python coaxial-pip-packager.py --only-upload", COLOR_GREEN)
        else:
            # publish_package prompts for confirmation inside
            publish_success = publish_package(project_path)
            if not publish_success:
                print_color("Package publishing failed.", COLOR_RED)
                sys.exit(1)

            print_color("\nProcess completed successfully!", COLOR_GREEN)
            print_color(f"Package version {new_version} built and published.", COLOR_GREEN)

    except SystemExit as e:
        # Catch SystemExit to ensure finally block runs before exiting
        print_color(f"\nExiting with status {e.code}", COLOR_YELLOW)
        logging.info("Exiting with status code %d", e.code)
        sys.exit(e.code)  # Re-raise the exit code

    except (IOError, subprocess.SubprocessError, ValueError) as e:
        print_color(f"\nAn unexpected error occurred: {e}", COLOR_RED)
        logging.exception("An unexpected error occurred")
        import traceback
        traceback.print_exc()
        sys.exit(1)  # Indicate failure

    finally:
        # Always change back to the original directory
        if project_path is not None and os.getcwd() != original_cwd:
            print_color(f"\nChanging back to original directory: {original_cwd}", COLOR_CYAN)
            os.chdir(original_cwd)

        # Log completion
        logging.info("Script execution completed")
        print_color(f"Log file has been written to {os.path.join('logs', log_filename)}", COLOR_CYAN)

def display_logo():
    """Displays the ASCII logo."""
    print(get_logo())

# --- Setup Logging ---
def setup_logging():
    """Set up logging to both console and file with timestamp in the filename."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"coaxial-pip-packager_{timestamp}.log"

    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create log directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create a filter to sanitize sensitive information from logs
    class SensitiveInfoFilter(logging.Filter):
        def __init__(self):
            super().__init__()
            # Patterns to look for in logs (tokens, passwords, etc.)
            self.patterns = [
                # GitHub tokens
                (r'ghp_[a-zA-Z0-9]{36,}', 'ghp_***'),
                # PyPI tokens
                (r'pypi-[a-zA-Z0-9_-]{36,}', 'pypi-***'),
                # Generic API tokens pattern
                (r'[a-zA-Z0-9_-]{32,}', '***TOKEN***'),
                # Credentials in URLs
                (r'(https?://)([^:]+:[^@]+)(@)', r'\1***:***\3')
            ]

        def filter(self, record):
            if isinstance(record.msg, str):
                for pattern, replacement in self.patterns:
                    record.msg = re.sub(pattern, replacement, record.msg)
            return True

    # Create file handler with timestamp in the name
    file_handler = logging.FileHandler(os.path.join("logs", log_filename))
    file_handler.setLevel(logging.INFO)
    file_handler.addFilter(SensitiveInfoFilter())

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(SensitiveInfoFilter())

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Use a simpler formatter for console to avoid duplication with our colorful output
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info("Started logging to %s", log_filename)
    return log_filename

# Custom print_color function that also logs
original_print_color = print_color

def print_color_with_logging(text, color):
    """Print text with color and also log it."""
    original_print_color(text, color)

    # Log the message without color codes
    if color == COLOR_RED:
        logging.error(text)
    elif color == COLOR_YELLOW:
        logging.warning(text)
    else:
        logging.info(text)

# Replace the original print_color with our logging version
print_color = print_color_with_logging

# --- Revert Functionality ---
def save_run_history(project_path, current_version, new_version, changed_files):
    """Save information about this run for potential reversion later."""
    os.makedirs(HISTORY_DIR, exist_ok=True)

    # Create a dictionary with information about this run
    run_info = {
        "timestamp": datetime.datetime.now().isoformat(),
        "project_path": project_path,
        "old_version": current_version,
        "new_version": new_version,
        "changed_files": [os.path.abspath(f) for f in changed_files]
    }

    # Save the run info to the last_run file
    with open(LAST_RUN_FILE, 'w', encoding='utf-8') as f:
        json.dump(run_info, f, indent=2)

    logging.info("Saved run history to %s", LAST_RUN_FILE)

def load_last_run():
    """Load information about the last run for reversion."""
    if not os.path.exists(LAST_RUN_FILE):
        print_color("No previous run found to revert.", COLOR_RED)
        return None

    try:
        with open(LAST_RUN_FILE, 'r', encoding='utf-8') as f:
            run_info = json.load(f)
        logging.info("Loaded run history from %s", LAST_RUN_FILE)
        return run_info
    except (json.JSONDecodeError, IOError) as e:
        print_color(f"Error loading last run info: {e}", COLOR_RED)
        return None

def revert_last_run():
    """Revert the changes made in the last run."""
    run_info = load_last_run()
    if not run_info:
        return False

    print_color("\nReverting last run:", COLOR_YELLOW)
    print_color(f"Timestamp: {run_info['timestamp']}", COLOR_CYAN)
    print_color(f"Project: {run_info['project_path']}", COLOR_CYAN)
    print_color(f"Version change: {run_info['old_version']} -> {run_info['new_version']}", COLOR_CYAN)
    print_color(f"Files changed: {len(run_info['changed_files'])}", COLOR_CYAN)

    if not confirm("Are you sure you want to revert these changes?", default=False):
        print_color("Revert cancelled.", COLOR_YELLOW)
        return False

    # Revert each changed file
    revert_success = True
    for file_path in run_info['changed_files']:
        if not os.path.exists(file_path):
            print_color(f"File does not exist, cannot revert: {file_path}", COLOR_RED)
            revert_success = False
            continue

        try:
            print_color(f"Reverting file: {file_path}", COLOR_CYAN)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace the new version with the old version
            if run_info['new_version'] in content:
                new_content = content.replace(run_info['new_version'], run_info['old_version'])

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print_color(f"Successfully reverted version in {file_path}", COLOR_GREEN)
            else:
                print_color(f"New version not found in {file_path}, skipping", COLOR_YELLOW)
        except (IOError, UnicodeError) as e:
            print_color(f"Error reverting file {file_path}: {e}", COLOR_RED)
            revert_success = False

    if revert_success:
        print_color("\nReversion completed successfully!", COLOR_GREEN)

        # Offer to commit the reversion
        if confirm("Would you like to commit this reversion?", default=True):
            try:
                commit_message = f"Revert version change: {run_info['new_version']} -> {run_info['old_version']}"
                run_command(['git', 'add', '.'], cwd=run_info['project_path'], capture_output=True)
                run_command(['git', 'commit', '-m', commit_message], cwd=run_info['project_path'], capture_output=True)
                print_color(f"Created reversion commit: '{commit_message}'", COLOR_GREEN)
            except subprocess.SubprocessError as e:
                print_color(f"Error committing reversion: {e}", COLOR_RED)
    else:
        print_color("\nReversion completed with some errors. Please check the log file.", COLOR_YELLOW)

    return revert_success

# --- Spinner Implementation ---
class Spinner:
    """Simple spinner to show progress during long operations."""
    def __init__(self, message="Working...", delay=0.1):
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.delay = delay
        self.message = message
        self.running = False
        self.spinner_thread = None
        self.counter = 0
        # Save original handlers for proper cleanup
        self.original_sigint = signal.getsignal(signal.SIGINT)

    def spin(self):
        while self.running:
            char = self.spinner_chars[self.counter % len(self.spinner_chars)]
            sys.stdout.write(f"\r{COLOR_CYAN}{char} {self.message}{COLOR_RESET}")
            sys.stdout.flush()
            time.sleep(self.delay)
            self.counter += 1

    def __enter__(self):
        # Handle SIGINT (Ctrl+C) gracefully
        def sigint_handler(signum, frame):
            self.stop()
            # Call the original handler
            if callable(self.original_sigint):
                self.original_sigint(signum, frame)
            else:
                # Default behavior: exit
                sys.exit(1)

        signal.signal(signal.SIGINT, sigint_handler)

        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        # Restore original SIGINT handler
        signal.signal(signal.SIGINT, self.original_sigint)
        # One final newline to prevent next output from being on the same line
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

    def start(self):
        if not self.running:
            self.running = True
            self.spinner_thread = threading.Thread(target=self.spin)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()

    def stop(self):
        self.running = False
        if self.spinner_thread and self.spinner_thread.is_alive():
            self.spinner_thread.join()

    def update_message(self, message):
        self.message = message
        # Clear the line and immediately show new message
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

# --- Main Execution ---
if __name__ == "__main__":
    main()