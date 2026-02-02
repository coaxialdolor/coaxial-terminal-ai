"""Clipboard utilities for TerminalAI."""
import pyperclip

def copy_to_clipboard(text_to_copy):
    """
    Copies the given text to the system clipboard.

    Args:
        text_to_copy (str): The text to be copied.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        pyperclip.copy(text_to_copy)
        return True
    except pyperclip.PyperclipException as e:
        # This can happen if a copy/paste mechanism is not available.
        # For example, on a headless server or if xclip/xsel is not installed on Linux.
        print(f"[ERROR] Could not copy to clipboard: {e}")
        print("Please ensure a clipboard mechanism is installed (e.g., xclip or xsel on Linux).")
        return False

if __name__ == '__main__':
    # Example usage and test
    SAMPLE_TEXT = "echo 'Hello from TerminalAI clipboard test!'"
    print(f"Attempting to copy: '{SAMPLE_TEXT}'")
    if copy_to_clipboard(SAMPLE_TEXT):
        print("Copied to clipboard successfully. Try pasting it.")
        # You can try to paste here to verify, though pyperclip.paste() might also fail if copy did.
        # try:
        #     pasted_text = pyperclip.paste()
        #     print(f"Pasted text: '{pasted_text}'")
        #     assert pasted_text == sample_text, "Pasted text does not match copied text!"
        #     print("Verification successful.")
        # except pyperclip.PyperclipException:
        #     print("Could not paste for verification.")
    else:
        print("Failed to copy to clipboard.")
