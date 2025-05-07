import os
import json

CONFIG_PATH = os.path.expanduser("~/.terminalai_config.json")

DEFAULT_SYSTEM_PROMPT = (
    "Always answer as concisely as possible, providing only the most relevant command for the user's system unless the user asks for more detail. "
    "If multiple commands are possible, enumerate them and keep explanations brief. The user will be viewing the answer in a terminal so format the text for best readability in a terminal environment. "
    "When you suggest a command, always put it in its own code block with triple backticks and specify the language (e.g., ```bash). "
    "Do not use inline code for commands. Do not include explanations or options in the same code block—only the actual shell command. "
    "If you suggest multiple commands, enumerate them, each in its own code block. Explanations should be outside code blocks. "
    "Commands must be guaranteed to work for the user's system unless the user specifically asks for another system (e.g., 'on windows'). If the user query specifies a different system, answer for that system instead."
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
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
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
