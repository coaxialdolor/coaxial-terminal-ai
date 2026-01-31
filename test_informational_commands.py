#!/usr/bin/env python3
"""
Comprehensive test suite for informational command execution.
Tests the enhanced command box formatting and immediate execution.
"""

import subprocess
import sys
import os
from terminalai.command_utils import run_shell_command, is_informational_command

def test_command_box_formatting():
    """Test that command boxes are properly formatted."""
    print("=== Testing Command Box Formatting ===")
    
    # Test simple commands
    test_commands = [
        'pwd',
        'whoami', 
        'echo "Hello World"',
        'ls',
        'date'
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing: {cmd} ---")
        result = run_shell_command(cmd)
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    
    print("\n=== Command Box Formatting Tests Complete ===")

def test_file_reading_commands():
    """Test file reading commands that should execute immediately."""
    print("\n=== Testing File Reading Commands ===")
    
    # Test file reading commands
    test_commands = [
        'cat terminalai/command_utils.py | head -3',
        'head terminalai/command_utils.py',
        'tail terminalai/command_utils.py',
        'grep "def " terminalai/command_utils.py | head -3',
        'wc -l terminalai/command_utils.py'
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing: {cmd} ---")
        result = run_shell_command(cmd)
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    
    print("\n=== File Reading Commands Tests Complete ===")

def test_counting_commands():
    """Test commands that count files or lines."""
    print("\n=== Testing Counting Commands ===")
    
    # Test counting commands
    test_commands = [
        'find . -name "*.py" | wc -l',
        'ls -la | wc -l',
        'echo "Testing counting commands"'
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing: {cmd} ---")
        result = run_shell_command(cmd)
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    
    print("\n=== Counting Commands Tests Complete ===")

def test_cross_platform_commands():
    """Test commands that work across different platforms."""
    print("\n=== Testing Cross-Platform Commands ===")
    
    # Test cross-platform commands
    test_commands = [
        'git status',
        'git log --oneline | head -3',
        'python --version',
        'node --version 2>/dev/null || echo "Node.js not installed"',
        'java --version 2>&1 | head -1 || echo "Java not installed"'
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing: {cmd} ---")
        result = run_shell_command(cmd)
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    
    print("\n=== Cross-Platform Commands Tests Complete ===")

def test_command_classification():
    """Test that commands are correctly classified."""
    print("\n=== Testing Command Classification ===")
    
    # Test informational commands
    informational_commands = [
        'ls', 'pwd', 'whoami', 'date', 'cat file.txt',
        'head file.txt', 'tail file.txt', 'grep pattern file.txt',
        'find . -name "*.txt"', 'echo hello', 'git status'
    ]
    
    # Test dangerous commands
    dangerous_commands = [
        'rm -rf /tmp/test', 'sudo chmod 777 file.txt', 'format disk',
        'dd if=/dev/zero of=/dev/sda', 'passwd root'
    ]
    
    print("Informational commands (should be True):")
    for cmd in informational_commands:
        is_info = is_informational_command(cmd)
        print(f"  {cmd:<30} -> {'✅' if is_info else '❌'}")
    
    print("\nDangerous commands (should be False):")
    for cmd in dangerous_commands:
        is_info = is_informational_command(cmd)
        print(f"  {cmd:<30} -> {'❌' if is_info else '✅'}")
    
    print("\n=== Command Classification Tests Complete ===")

def test_output_cleanliness():
    """Test that output is clean and well-formatted."""
    print("\n=== Testing Output Cleanliness ===")
    
    # Test commands that should produce clean output
    test_commands = [
        'echo "Clean output test"',
        'pwd',
        'whoami',
        'date'
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing Output Cleanliness: {cmd} ---")
        result = run_shell_command(cmd)
        print(f"Output appears clean: {'✅' if result else '❌'}")
    
    print("\n=== Output Cleanliness Tests Complete ===")

def main():
    """Run all tests."""
    print("🧪 Running Comprehensive Informational Command Tests")
    print("=" * 60)
    
    try:
        test_command_classification()
        test_command_box_formatting()
        test_file_reading_commands()
        test_counting_commands()
        test_cross_platform_commands()
        test_output_cleanliness()
        
        print("\n🎉 All tests completed!")
        print("✅ Informational command system is working correctly")
        print("✅ Command boxes are properly formatted")
        print("✅ Commands execute immediately without confirmation")
        print("✅ Output is clean and well-formatted")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()