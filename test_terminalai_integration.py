import os
import subprocess
import datetime
import time
import shutil
from pathlib import Path

# Example queries for testing
QUERIES = [
    "how do I list files in columns?",
    "how do I count the number of files in this folder?",
    "how do I show the first 3 lines of a file?",
    "how do I find all .txt files?",
    "how do I print the current directory?",
    "how do I show hidden files?",
    "how do I create a new empty file?",
    "how do I display the contents of a file?",
    "how do I list files in a tree view?"
]

TEST_ROOT = Path("test_terminalai")

# Helper to run a command and capture output
def run_cli(cmd, input_text=None):
    result = subprocess.run(cmd, input=input_text, capture_output=True, text=True, shell=True)
    return result.stdout, result.stderr

def setup_test_folder():
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = TEST_ROOT / f"Test_{now}"
    test_dir.mkdir(parents=True, exist_ok=True)
    # Create some files for testing
    (test_dir / "file1.txt").write_text("Hello world\nThis is file1\nLine3\nLine4\n")
    (test_dir / "file2.txt").write_text("Another file\nWith some text\n")
    (test_dir / "hiddenfile").write_text("hidden\n")
    (test_dir / ".DS_Store").write_text("")
    (test_dir / "script.sh").write_text("#!/bin/bash\necho script\n")
    (test_dir / "subdir").mkdir(exist_ok=True)
    (test_dir / "subdir" / "subfile.txt").write_text("subdir file\n")
    return test_dir

def take_screenshot(test_dir, query_idx):
    # Use terminal screenshot tool if available (e.g., 'screencapture' on macOS)
    screenshot_path = test_dir / f"screenshot_{query_idx+1}.png"
    try:
        # This is a placeholder: in real automation, you'd use a tool like pyautogui or a terminal recorder
        # For now, just touch the file to indicate where a screenshot would go
        screenshot_path.touch()
    except Exception as e:
        pass
    return screenshot_path

def main():
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir(exist_ok=True)
    test_dir = setup_test_folder()
    os.chdir(test_dir)
    report_lines = []
    for idx, query in enumerate(QUERIES):
        report_lines.append(f"Test {idx+1}: {query}")
        # Run the CLI and capture output
        cmd = f"ai \"{query}\""
        stdout, stderr = run_cli(cmd)
        report_lines.append("--- Output ---")
        report_lines.append(stdout)
        if stderr:
            report_lines.append("--- STDERR ---")
            report_lines.append(stderr)
        # Take a screenshot placeholder
        screenshot_path = take_screenshot(test_dir, idx)
        report_lines.append(f"Screenshot: {screenshot_path}")
        # Try to parse the output for commands
        found_commands = []
        for line in stdout.splitlines():
            if line.strip().startswith("[RUNNING]") or line.strip().startswith("1."):
                found_commands.append(line.strip())
        report_lines.append(f"Commands found: {found_commands}")
        # Try to run the first command if possible (simulate 'y' or '1')
        if "Do you want to run" in stdout:
            # Try running the first command
            try:
                stdout2, stderr2 = run_cli(cmd, input_text="1\n")
                report_lines.append("--- Output after running command ---")
                report_lines.append(stdout2)
                if stderr2:
                    report_lines.append("--- STDERR ---")
                    report_lines.append(stderr2)
            except Exception as e:
                report_lines.append(f"Error running command: {e}")
        report_lines.append("\n")
        time.sleep(1)  # Avoid rate limits
    # Write report
    report_path = test_dir / "test_report.txt"
    report_path.write_text("\n".join(report_lines))
    print(f"Test report written to {report_path}")

if __name__ == "__main__":
    main()
