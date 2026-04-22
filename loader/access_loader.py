import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def load_access():
    with open(BASE_DIR / "access/access.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    admins = set(data.get("admins", []))
    users = set(data.get("users", [])) | admins
    return admins, users
