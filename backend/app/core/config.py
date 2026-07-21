import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent.parent  # careerkit-local/
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "app_name": "CareerKit Local",
    "db_path": str(DATA_DIR / "careerkit.db"),
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        merged = {**DEFAULT_SETTINGS, **data}
        return merged
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = load_settings()
    current.update(settings)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)


def get_setting(key: str, default=None):
    return load_settings().get(key, default)
