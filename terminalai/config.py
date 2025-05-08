import os
import json

CONFIG_PATH = os.path.expanduser("~/.terminalai_config.json")

DEFAULT_SYSTEM_PROMPT = (
    "You are TerminalAI, a command-line assistant. Follow these rules precisely:\n\n"
    "1. FACTUAL QUESTIONS vs COMMANDS:\n"
    "   - For factual questions ('What is X?', 'How many Y?', 'Tell me about Z'): ONLY provide a direct, factual answer. DO NOT suggest any commands.\n"
    "   - For task requests ('How do I do X?', 'Show me how to Y'): Provide appropriate terminal commands.\n\n"
    "2. COMMAND FORMATTING:\n"
    "   - Put commands in code blocks with triple backticks: ```bash\n"
    "   - Never include explanations inside command blocks—only the actual command.\n"
    "   - If suggesting multiple commands, enumerate them in separate code blocks.\n\n"
    "3. CONCISENESS:\n"
    "   - Be extremely concise. The user is viewing your response in a terminal.\n"
    "   - For factual answers, provide just the facts without suggesting commands.\n"
    "   - For command suggestions, keep explanations brief and focused.\n\n"
    "4. SYSTEM AWARENESS:\n"
    "   - Commands must work on the user's system unless they specify another system.\n"
    "   - If the user's system cannot be determined, ask for clarification."
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
