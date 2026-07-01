from __future__ import annotations

import secrets

from app.core.security import hash_password, verify_password

API_KEY_PREFIX_LENGTH = 16


def generate_api_key() -> tuple[str, str, str]:
    prefix = secrets.token_hex(API_KEY_PREFIX_LENGTH // 2)
    secret = secrets.token_urlsafe(32)
    api_key = f"sentinel_{prefix}_{secret}"
    return api_key, prefix, hash_api_key(api_key)


def hash_api_key(api_key: str) -> str:
    return hash_password(api_key)


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    return verify_password(api_key, api_key_hash)


def extract_api_key_prefix(api_key: str) -> str | None:
    parts = api_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "sentinel":
        return None
    return parts[1]
