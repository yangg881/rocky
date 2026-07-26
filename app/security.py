from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_token(user_id: str, role: str, settings: Settings, session_version: int = 1) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "sv": max(1, int(session_version or 1)),
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def issue_file_token(
    bucket: str,
    key: str,
    settings: Settings,
    filename: str = "",
    minutes: int = 20,
    owner_id: str = "",
    purpose: str = "preview",
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "scope": "file-preview",
        "bucket": bucket,
        "key": key,
        "filename": filename,
        "owner_id": owner_id,
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_file_token(token: str, settings: Settings) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    if payload.get("scope") != "file-preview" or payload.get("purpose") not in {
        "preview",
        "avatar",
        "template-preview",
    }:
        raise jwt.InvalidTokenError("invalid file token scope")
    return payload
