import os

# Define max file size (e.g., 1MB)
# ALLOWED_EXTENSIONS = {".txt", ".py", ".json", ".md", ".log", ".sh", ".cfg", ".ini", ".yaml", ".yml", ".toml"} # Removed
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB

def get_file_context(filepath: str) -> dict:
    """
    Gathers context about a file and its directory.
    
    Args:
        filepath: Absolute path to the file.
        
    Returns:
        A dictionary containing:
        - parent_dir: Parent directory path
        - sibling_files: List of files in the same directory
        - parent_dir_files: List of files in the parent directory
    """
    try:
        parent_dir = os.path.dirname(filepath)
        context = {
            'parent_dir': parent_dir,
            'sibling_files': [],
            'parent_dir_files': []
        }
        
        # Get sibling files (files in the same directory)
        if os.path.exists(parent_dir):
            context['sibling_files'] = [
                f for f in os.listdir(parent_dir)
                if os.path.isfile(os.path.join(parent_dir, f))
            ]
            
            # Get parent directory files
            parent_parent = os.path.dirname(parent_dir)
            if os.path.exists(parent_parent):
                context['parent_dir_files'] = [
                    f for f in os.listdir(parent_parent)
                    if os.path.isfile(os.path.join(parent_parent, f))
                ]
                
        return context
    except Exception as e:
        return {
            'parent_dir': os.path.dirname(filepath),
            'sibling_files': [],
            'parent_dir_files': [],
            'error': str(e)
        }

def read_project_file(filepath: str, project_root: str) -> tuple[str | None, str | None, dict | None]:
    """
    Reads a file specified by filepath.

    Args:
        filepath: Relative or absolute path to the file.
        project_root: The root directory of the project (usually current working directory).

    Returns:
        A tuple (file_content, error_message, context).
        If successful, (file_content, None, context).
        If an error occurs, (None, error_message, None).
    """
    try:
        # Handle absolute paths correctly
        if os.path.isabs(filepath):
            abs_filepath = filepath
        else:
            abs_filepath = os.path.abspath(os.path.join(project_root, filepath))

        # Security: Check file size
        if not os.path.exists(abs_filepath):
            return None, f"Error: File not found at '{abs_filepath}'.", None

        if not os.path.isfile(abs_filepath):
            return None, f"Error: Path '{abs_filepath}' is a directory, not a file.", None

        if os.path.getsize(abs_filepath) > MAX_FILE_SIZE_BYTES:
            return None, f"Error: File '{filepath}' exceeds the maximum allowed size of {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB.", None

        # Get file context
        context = get_file_context(abs_filepath)

        with open(abs_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None, context

    except FileNotFoundError:
        return None, f"Error: File not found at '{filepath}' (resolved to '{abs_filepath}').", None
    except PermissionError:
        return None, f"Error: Permission denied when trying to read '{filepath}'.", None
    except Exception as e:
        return None, f"Error: An unexpected error occurred while reading '{filepath}': {str(e)}", None