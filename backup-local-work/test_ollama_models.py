#!/usr/bin/env python3
"""Test script to verify Ollama model listing functionality."""

import sys
import os

# Add the terminalai directory to the Python path to use local code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_ollama_provider():
    """Test the OllamaProvider class directly."""
    print("Testing OllamaProvider class...")
    
    from terminalai.ai_providers import OllamaProvider
    from terminalai.config import load_config
    
    # Get the configured host from config
    config = load_config()
    ollama_config = config.get("providers", {}).get("ollama", {})
    host = ollama_config.get("host", "http://localhost:11434")
    
    print(f"Testing with configured host: {host}")
    provider = OllamaProvider(host)
    
    print("Testing list_models() method...")
    models = provider.list_models()
    
    if isinstance(models, str) and models.startswith("[Ollama API error]"):
        print(f"Error: {models}")
        print("This is expected if Ollama is not running.")
    elif not models:
        print("No models found. This is expected if Ollama has no models installed.")
    else:
        print(f"Success! Found {len(models)} models:")
        for i, model in enumerate(models, 1):
            model_name = model.get('name', 'Unknown')
            model_size = model.get('size', 0)
            model_modified = model.get('modified_at', 'Unknown')
            
            # Format size in human-readable format
            if model_size > 0:
                if model_size >= 1024**3:
                    size_str = f"{model_size / (1024**3):.1f} GB"
                elif model_size >= 1024**2:
                    size_str = f"{model_size / (1024**2):.1f} MB"
                elif model_size >= 1024:
                    size_str = f"{model_size / 1024:.1f} KB"
                else:
                    size_str = f"{model_size} B"
            else:
                size_str = "Unknown size"
            
            print(f"  {i}. {model_name}")
            print(f"     Size: {size_str}")
            print(f"     Modified: {model_modified}")
    
    return models

def test_get_available_models():
    """Test the get_available_models helper function."""
    print("\nTesting get_available_models() helper function...")
    
    from terminalai.cli_interaction import get_available_models
    
    models = get_available_models()
    
    if isinstance(models, str) and models.startswith("[Ollama API error]"):
        print(f"Error: {models}")
        print("This is expected if Ollama is not running.")
    elif not models:
        print("No models found. This is expected if Ollama has no models installed.")
    else:
        print(f"Success! Found {len(models)} models:")
        for i, model in enumerate(models, 1):
            model_name = model.get('name', 'Unknown')
            print(f"  {i}. {model_name}")
    
    return models

def test_config_loading():
    """Test that we can load and save configuration."""
    print("\nTesting configuration loading...")
    
    from terminalai.config import load_config, save_config
    
    config = load_config()
    print("Current configuration loaded successfully")
    
    # Check if Ollama is configured
    ollama_config = config.get("providers", {}).get("ollama", {})
    host = ollama_config.get("host", "http://localhost:11434")
    model = ollama_config.get("model", "llama3")
    
    print(f"Ollama host: {host}")
    print(f"Ollama default model: {model}")
    
    return config

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Ollama Model Listing Functionality")
    print("=" * 60)
    
    # Test 1: Direct OllamaProvider testing
    models1 = test_ollama_provider()
    
    # Test 2: Helper function testing
    models2 = test_get_available_models()
    
    # Test 3: Configuration testing
    config = test_config_loading()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    if isinstance(models1, str) and models1.startswith("[Ollama API error]"):
        print("❌ OllamaProvider.list_models() failed - Ollama server not running")
    elif not models1:
        print("⚠️  OllamaProvider.list_models() returned no models - Ollama may be running but has no models")
    else:
        print("✅ OllamaProvider.list_models() working correctly")
    
    if isinstance(models2, str) and models2.startswith("[Ollama API error]"):
        print("❌ get_available_models() failed - Ollama server not running")
    elif not models2:
        print("⚠️  get_available_models() returned no models - Ollama may be running but has no models")
    else:
        print("✅ get_available_models() working correctly")
    
    print("✅ Configuration loading working correctly")
    
    print("\nTo test with a running Ollama server:")
    print("1. Start Ollama: ollama serve")
    print("2. Install a model: ollama pull llama3")
    print("3. Run this test script again")
    
    print("\nTo test the setup wizard:")
    print("1. Run: python -m terminalai.terminalai_cli --setup")
    print("2. Choose option 12 to list available Ollama models")

if __name__ == "__main__":
    main()