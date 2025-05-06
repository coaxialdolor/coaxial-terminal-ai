import requests
import os
from terminalai.config import load_config

class AIProvider:
    def query(self, prompt):
        raise NotImplementedError

class OpenRouterProvider(AIProvider):
    def __init__(self, api_key):
        self.api_key = api_key
    def query(self, prompt):
        # Placeholder for OpenRouter API call
        return f"[OpenRouter] {prompt}"

class GeminiProvider(AIProvider):
    def __init__(self, api_key):
        self.api_key = api_key
    def query(self, prompt):
        # Placeholder for Gemini API call
        return f"[Gemini] {prompt}"

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
        # Placeholder for Ollama API call
        return f"[Ollama] {prompt}"

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
