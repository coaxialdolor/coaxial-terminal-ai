import os

# Define max file size (e.g., 1MB)
# ALLOWED_EXTENSIONS = {".txt", ".py", ".json", ".md", ".log", ".sh", ".cfg", ".ini", ".yaml", ".yml", ".toml"} # Removed
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB

def read_project_file(filepath: str, project_root: str) -> tuple[str | None, str | None]:
    """
    Reads a file specified by filepath, ensuring it's within the project_root.

    Args:
        filepath: Relative or absolute path to the file.
        project_root: The root directory of the project (usually current working directory).

    Returns:
        A tuple (file_content, error_message).
        If successful, (file_content, None).
        If an error occurs, (None, error_message).
    """
    try:
        # Resolve to absolute paths for robust comparison
        abs_filepath = os.path.abspath(os.path.join(project_root, filepath))
        abs_project_root = os.path.abspath(project_root)

        # Security: Ensure the file is within the project root
        if not abs_filepath.startswith(abs_project_root):
            return None, f"Error: Access denied. File '{filepath}' is outside the project directory '{project_root}'."

        # Security: Check file extension # Removed extension check
        # _, ext = os.path.splitext(abs_filepath)
        # if ext.lower() not in ALLOWED_EXTENSIONS:
        #     return None, f"Error: File type '{ext}' is not allowed. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}."

        # Security: Check file size
        # First, check if file exists and is a file, otherwise getsize will fail
        if not os.path.exists(abs_filepath):
            return None, f"Error: File not found at '{abs_filepath}'."

        if not os.path.isfile(abs_filepath):
             return None, f"Error: Path '{abs_filepath}' is a directory, not a file."

        if os.path.getsize(abs_filepath) > MAX_FILE_SIZE_BYTES:
            return None, f"Error: File '{filepath}' exceeds the maximum allowed size of {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB."

        with open(abs_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None

    except FileNotFoundError:
        return None, f"Error: File not found at '{filepath}' (resolved to '{abs_filepath}')."
    except PermissionError:
        return None, f"Error: Permission denied when trying to read '{filepath}'."
    except Exception as e:
        return None, f"Error: An unexpected error occurred while reading '{filepath}': {str(e)}"