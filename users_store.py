import json
import os
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet

DEFAULT_USERS_PATH = "users.json"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_cipher():
    key = os.getenv("STORAGE_KEY")
    return Fernet(key.encode()) if key else None


def load_users(path=DEFAULT_USERS_PATH):
    file_path = Path(path)
    if not file_path.exists():
        return []

    content = file_path.read_bytes()
    cipher = _get_cipher()

    if cipher:
        try:
            content = cipher.decrypt(content)
        except Exception:
            # If decryption fails, maybe it's plain text (first run or no encryption before)
            # or wrong key. We'll try to parse as plain JSON.
            pass

    try:
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError:
        # If decode fails, it might be encrypted but we have no key or wrong key
        print("Warning: Failed to parse users.json. It might be encrypted or corrupted.")
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("users", [])

    return []


def save_users(users, path=DEFAULT_USERS_PATH):
    file_path = Path(path)
    users_sorted = sorted(users, key=lambda u: (u.get("email") or "").lower())
    payload = {"users": users_sorted}
    json_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

    cipher = _get_cipher()
    if cipher:
        encrypted_bytes = cipher.encrypt(json_bytes)
        file_path.write_bytes(encrypted_bytes)
    else:
        file_path.write_bytes(json_bytes)


def find_user(users, email):
    email_lc = (email or "").lower()
    for user in users:
        if (user.get("email") or "").lower() == email_lc:
            return user
    return None


def upsert_user(users, email, username, password, current_status):
    now = utc_now_iso()
    existing = find_user(users, email)
    if existing:
        existing.update({
            "email": email,
            "username": username,
            "password": password,
            "current_status": current_status,
            "updated_at": now,
        })
        if "created_at" not in existing:
            existing["created_at"] = now
        return existing, False

    user = {
        "email": email,
        "username": username,
        "password": password,
        "current_status": current_status,
        "created_at": now,
        "updated_at": now,
    }
    users.append(user)
    return user, True
