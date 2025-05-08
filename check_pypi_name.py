#!/usr/bin/env python3
import sys
import requests

def check_package_name(name):
    """Check if a package name is available on PyPI."""
    url = f"https://pypi.org/project/{name}/"
    response = requests.get(url)
    if response.status_code == 404:
        print(f"✅ Good news! The name '{name}' appears to be available on PyPI.")
        return True
    else:
        print(f"❌ The name '{name}' is already taken or reserved on PyPI.")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_pypi_name.py <package-name>")
        sys.exit(1)
    
    name = sys.argv[1]
    check_package_name(name) 