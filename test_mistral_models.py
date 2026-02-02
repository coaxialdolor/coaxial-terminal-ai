#!/usr/bin/env python3
"""
Test script to check available Mistral models through the API.
"""

import requests
import sys
import os
from terminalai.config import load_config

def test_mistral_models():
    """Test available Mistral models."""
    print("🧪 Testing Mistral API Models")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    mistral_config = config.get("providers", {}).get("mistral", {})
    
    if not mistral_config or not mistral_config.get("api_key"):
        print("❌ No Mistral API key configured")
        print("Please run 'ai setup' and configure your Mistral API key")
        return False
    
    api_key = mistral_config["api_key"]
    print(f"✅ Mistral API key found")
    
    # Test the models endpoint
    url = "https://api.mistral.ai/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        print("\n📡 Fetching available Mistral models...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        models = data.get("data", [])
        
        if not models:
            print("❌ No models found in response")
            return False
        
        print(f"\n✅ Found {len(models)} Mistral models:")
        print("-" * 60)
        
        for i, model in enumerate(models, 1):
            model_id = model.get("id", "Unknown")
            model_type = model.get("type", "Unknown")
            model_context_window = model.get("context_window", "Unknown")
            
            print(f"{i:2d}. {model_id}")
            print(f"    Type: {model_type}")
            print(f"    Context Window: {model_context_window}")
            print()
        
        # Show current default in config
        current_default = config.get("default_provider", "")
        print(f"📋 Current default provider: {current_default}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error processing response: {e}")
        return False

def test_current_mistral_setup():
    """Test the current Mistral provider setup."""
    print("\n🔧 Testing Current Mistral Provider Setup")
    print("=" * 50)
    
    try:
        from terminalai.ai_providers import get_provider
        
        # Test getting Mistral provider
        provider = get_provider("mistral")
        if not provider:
            print("❌ Could not initialize Mistral provider")
            return False
        
        print("✅ Mistral provider initialized successfully")
        print(f"✅ Provider type: {type(provider).__name__}")
        
        # Test a simple query to verify it works
        print("\n📡 Testing simple query...")
        response = provider.query("Hello, what model are you?")
        
        if response and not response.startswith("[Mistral API error]"):
            print("✅ Simple query successful")
            print(f"Response preview: {response[:100]}...")
        else:
            print(f"❌ Query failed: {response}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Mistral provider: {e}")
        return False

def main():
    """Run all Mistral tests."""
    print("🚀 Testing Mistral API Integration")
    print("=" * 60)
    
    success = True
    
    # Test current setup
    if not test_current_mistral_setup():
        success = False
    
    # Test available models
    if not test_mistral_models():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Mistral tests passed!")
        print("✅ Mistral API is properly configured and working")
        print("✅ Available models have been listed")
    else:
        print("❌ Some Mistral tests failed")
        print("💡 Check your Mistral API key and network connection")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)