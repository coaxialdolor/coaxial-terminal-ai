"""Configuration utilities for TerminalAI."""
import os
import json
import appdirs
from pathlib import Path

CONFIG_PATH = os.path.expanduser("~/.terminalai_config.json")

DEFAULT_SYSTEM_PROMPT = (
    "You are TerminalAI. Your suggestions ARE EXECUTED AUTOMATICALLY by the user's terminal.\n\n"
    "RULES:\n"
    "1. ONLY PROVIDE ONE COMMAND per block. Use the user's CURRENT OS (provided in context).\n"
    "2. NO explanations unless absolutely necessary. NO other OS alternatives.\n"
    "3. To count files, use 'wc -l' or similar. To find info, use informational commands.\n"
    "4. Format: ```bash\ncommand\n```"
)

DEFAULT_CONFIG = {
    "providers": {
        "openrouter": {"api_key": ""},
        "gemini": {"api_key": ""},
        "mistral": {"api_key": ""},
        "ollama": {"host": "http://localhost:11434"}
    },
    "default_provider": "openrouter",
    "system_prompt": DEFAULT_SYSTEM_PROMPT
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

def get_system_prompt():
    config = load_config()
    return config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

def set_system_prompt(prompt):
    config = load_config()
    config["system_prompt"] = prompt
    save_config(config)

def reset_system_prompt():
    config = load_config()
    config["system_prompt"] = DEFAULT_SYSTEM_PROMPT
    save_config(config)
