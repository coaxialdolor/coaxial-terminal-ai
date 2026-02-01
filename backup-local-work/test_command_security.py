#!/usr/bin/env python3
"""Test script for command security improvements."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'terminalai'))

from command_utils import is_shell_command, sanitize_command, run_shell_command

def test_command_security():
    """Test the command security improvements."""
    print("Testing Command Security Improvements")
    print("=" * 50)
    
    # Test cases for is_shell_command
    print("\n1. Testing is_shell_command():")
    test_commands = [
        ("ls", True),
        ("ls -la", True),
        ("echo hello", True),
        ("cat file.txt", True),
        ("grep pattern file.txt", True),
        ("find . -name '*.txt'", True),
        ("echo hello | grep hello", True),
        ("echo hello > file.txt", True),
        ("echo hello && ls", True),
        ("echo hello || ls", True),
        ("echo hello &", True),
        ("$(echo hello)", True),
        ("`echo hello`", True),
        ("", False),
        ("just text", False),
        ("123", False),
        (None, False),
    ]
    
    for cmd, expected in test_commands:
        result = is_shell_command(cmd)
        status = "✅" if result == expected else "❌"
        print(f"  {status} is_shell_command({repr(cmd)}) = {result} (expected {expected})")
    
    # Test cases for sanitize_command
    print("\n2. Testing sanitize_command():")
    dangerous_commands = [
        ("rm -rf /", "Dangerous rm command"),
        ("rm -rf ../", "Directory traversal"),
        ("chmod 777 file.txt", "Overly permissive chmod"),
        ("chown root file.txt", "Changing ownership to root"),
        ("sudo passwd root", "Password change"),
        ("passwd user", "Password change"),
        ("userdel user", "User deletion"),
        ("groupdel group", "Group deletion"),
        ("format disk", "Disk formatting"),
        ("dd if=file of=/dev/sda", "Disk writing"),
        ("fdisk /dev/sda", "Disk partitioning"),
        ("mkfs /dev/sda1", "Filesystem creation"),
        ("cryptsetup luksFormat /dev/sda1", "Disk encryption"),
        ("iptables -F", "Firewall flushing"),
        ("netstat -p", "Network process info"),
        ("kill -9 1", "Killing init process"),
        ("echo test > /proc/sys/kernel/panic", "Writing to proc filesystem"),
        ("echo test > /sys/class/leds/sda::indicator/brightness", "Writing to sys filesystem"),
        ("ls; rm -rf /", "Command chaining with rm"),
        ("ls | rm -rf /", "Pipe to rm"),
        ("ls $(rm -rf /)", "Command substitution with rm"),
        ("ls `rm -rf /`", "Backtick command substitution with rm"),
    ]
    
    safe_commands = [
        ("ls", "Safe ls command"),
        ("ls -la", "Safe ls with options"),
        ("cat file.txt", "Safe cat command"),
        ("echo hello", "Safe echo command"),
        ("grep pattern file.txt", "Safe grep command"),
        ("find . -name '*.txt'", "Safe find command"),
        ("git status", "Safe git command"),
        ("npm install", "Safe npm command"),
        ("pip install package", "Safe pip command"),
        ("python script.py", "Safe python command"),
        ("node app.js", "Safe node command"),
    ]
    
    for cmd, description in dangerous_commands:
        result = sanitize_command(cmd)
        status = "✅" if result == cmd else "❌"
        print(f"  {status} sanitize_command('{cmd}') = {result} ({description})")
    
    for cmd, description in safe_commands:
        result = sanitize_command(cmd)
        status = "✅" if result == cmd else "❌"
        print(f"  {status} sanitize_command('{cmd}') = {result} ({description})")
    
    # Test cases for run_shell_command
    print("\n3. Testing run_shell_command():")
    test_cases = [
        ("echo 'Hello World'", "Safe echo command"),
        ("ls", "Safe ls command"),
        ("rm -rf /", "Dangerous rm command (should be rejected)"),
        ("", "Empty command"),
        (None, "None command"),
    ]
    
    for cmd, description in test_cases:
        print(f"\n  Testing: {description}")
        print(f"  Command: {repr(cmd)}")
        result = run_shell_command(cmd)
        print(f"  Result: {'Success' if result else 'Failed'}")
    
    print("\n" + "=" * 50)
    print("Command security testing completed!")

if __name__ == "__main__":
    test_command_security()