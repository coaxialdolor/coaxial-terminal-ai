#!/bin/bash
# Test script for TerminalAI auto mode

echo "========================================================"
echo "TerminalAI Auto Mode Test Script"
echo "========================================================"
echo "This script will help you test the auto mode feature"
echo "that allows the AI to explore your filesystem to answer questions."
echo

# Check if terminalai is installed
if ! command -v ai &> /dev/null; then
    echo "The 'ai' command is not found. Please make sure TerminalAI is installed."
    echo "If installed in development mode, you might need to run:"
    echo "python -m terminalai.terminalai_cli instead of the commands below."
    exit 1
fi

echo "Suggested Test Commands:"
echo "------------------------"
echo "1. ai --auto"
echo "   This will start an interactive auto mode session"
echo
echo "2. ai --auto \"How many Python files are in this directory?\""
echo "   This will run a direct query in auto mode"
echo
echo "Example Questions for Testing:"
echo "-----------------------------"
echo "- How many Python files are in this directory?"
echo "- What's the largest file in this directory?"
echo "- How much disk space is available on this system?"
echo "- List all the markdown files in this project"
echo "- Find files related to command execution"
echo "- Count the number of lines of code in Python files"
echo "- What's in the README file?"
echo

echo "Safety Testing:"
echo "--------------"
echo "- Try asking it to delete a file - it should ask for confirmation"
echo "- Try asking for information about a sensitive file - it should respect permissions"
echo "- Test context retention by asking follow-up questions"
echo

echo "Ready to test! Choose one of the commands above to begin."
echo "========================================================"