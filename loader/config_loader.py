import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def load_config() -> dict:
    with open(BASE_DIR / "setting/config.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("config.json is not instance 'dict'")

    return data