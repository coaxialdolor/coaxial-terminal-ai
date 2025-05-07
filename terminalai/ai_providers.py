import requests
import os
import json
from terminalai.config import load_config

class AIProvider:
    def query(self, prompt):
        raise NotImplementedError

class OpenRouterProvider(AIProvider):
    def __init__(self, api_key):
        self.api_key = api_key
    def query(self, prompt):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/coaxialdolor/terminalai"
        }
        
        # Check if the prompt includes a system prompt section
        if "\n\n" in prompt:
            system_prompt, user_prompt = prompt.split("\n\n", 1)
            data = {
                "model": "openai/gpt-3.5-turbo",  # Default model, can be modified
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
        else:
            # Just a user prompt without system instructions
            data = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[OpenRouter API error] {e}"

class GeminiProvider(AIProvider):
    def __init__(self, api_key):
        self.api_key = api_key
    def query(self, prompt):
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Check if the prompt includes a system prompt section
        if "\n\n" in prompt:
            system_prompt, user_prompt = prompt.split("\n\n", 1)
            # Gemini doesn't natively support system prompts, so we'll format it
            formatted_prompt = f"System instructions: {system_prompt}\n\nUser query: {user_prompt}"
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": formatted_prompt}
                        ]
                    }
                ]
            }
        else:
            # Just a user prompt without system instructions
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
        
        try:
            response = requests.post(f"{url}?key={self.api_key}", headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"[Gemini API error] {e}"

class MistralProvider(AIProvider):
    def __init__(self, api_key):
        self.api_key = api_key
    def query(self, prompt):
        # Real Mistral API call
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Check if the prompt includes a system prompt section
        if "\n\n" in prompt:
            system_prompt, user_prompt = prompt.split("\n\n", 1)
            data = {
                "model": "mistral-tiny",  # You can change to another model if needed
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
        else:
            # Just a user prompt without system instructions
            data = {
                "model": "mistral-tiny",  # You can change to another model if needed
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Mistral API error] {e}"

class OllamaProvider(AIProvider):
    def __init__(self, host):
        self.host = host
    def query(self, prompt):
        url = f"{self.host}/api/chat"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Check if the prompt includes a system prompt section
        if "\n\n" in prompt:
            system_prompt, user_prompt = prompt.split("\n\n", 1)
            data = {
                "model": "llama3",  # Default model, can be modified
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
        else:
            # Just a user prompt without system instructions
            data = {
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)  # Longer timeout for local models
            response.raise_for_status()
            return response.json()["message"]["content"]
        except Exception as e:
            return f"[Ollama API error] {e}"

def get_provider():
    config = load_config()
    provider_name = config.get('default_provider', 'openrouter')
    provider_cfg = config['providers'][provider_name]
    if provider_name == 'openrouter':
        return OpenRouterProvider(provider_cfg.get('api_key', ''))
    elif provider_name == 'gemini':
        return GeminiProvider(provider_cfg.get('api_key', ''))
    elif provider_name == 'mistral':
        return MistralProvider(provider_cfg.get('api_key', ''))
    elif provider_name == 'ollama':
        return OllamaProvider(provider_cfg.get('host', 'http://localhost:11434'))
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
