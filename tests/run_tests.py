#!/usr/bin/env python3
"""Run all TerminalAI tests.

This script will run all test files in the tests directory.
"""
import unittest
import os
import sys

# Add parent directory to path so we can import terminalai modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_all_tests():
    """Discover and run all test files in the tests directory."""
    # Use the test discovery mechanism of unittest
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern="test_*.py")

    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)

    # Run the tests
    result = runner.run(suite)

    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    print("Running all TerminalAI tests...")

    # Show overview of what will be tested
    for root, dirs, files in os.walk(os.path.dirname(os.path.abspath(__file__))):
        test_files = [f for f in files if f.startswith("test_") and f.endswith(".py")]
        if test_files:
            print(f"\nFound {len(test_files)} test files:")
            for file in test_files:
                print(f"  - {file}")

    print("\nStarting tests...\n")

    # Run the tests and exit with appropriate exit code
    exit_code = run_all_tests()
    sys.exit(exit_code)