"""Account operations backed exclusively by Cloud Firestore."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any

import jwt

from ..config import settings

_SCRYPT = dict(n=2 ** 14, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)
_DUMMY_HASH = ""


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.message, self.status = message, status


def init() -> None:
    global _DUMMY_HASH
    _DUMMY_HASH = hash_password("dummy-password-for-timing")
    from . import firebase_store
    firebase_store.init()


def jwt_secret() -> str:
    if not settings.jwt_secret or len(settings.jwt_secret) < 24:
        raise RuntimeError("JWT_SECRET is missing or too short in .env (use at least 24 random characters).")
    return settings.jwt_secret


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, hash_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(hash_b64)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                                maxmem=64 * 1024 * 1024, dklen=len(expected))
    except Exception:
        return False
    return hmac.compare_digest(digest, expected)


def make_access_token(user_id: int) -> str:
    now = int(time.time())
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + settings.access_token_minutes * 60, "typ": "access"},
                      jwt_secret(), algorithm="HS256")


def read_access_token(token: str) -> int:
    try:
        data = jwt.decode(token, jwt_secret(), algorithms=["HS256"], options={"require": ["exp", "sub"]})
        if data.get("typ") != "access":
            raise AuthError("Invalid session.")
        return int(data["sub"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Session expired.")
    except (jwt.InvalidTokenError, ValueError):
        raise AuthError("Invalid session.")


def public_user(user: dict[str, Any] | None) -> dict | None:
    if user is None:
        return None
    return {"id": int(user["id"]), "email": user["email"], "display_name": user.get("display_name"),
            "auth_provider": user.get("auth_provider", "password")}


def register(email: str, password: str, display_name: str | None) -> dict:
    from . import firebase_store
    return firebase_store.register(email, password, display_name)


def login(email: str, password: str) -> dict:
    from . import firebase_store
    return firebase_store.login(email, password)


def login_with_firebase_token(id_token: str) -> dict:
    from . import firebase_store
    return firebase_store.login_with_firebase_token(id_token)


def save_person(user_id: int, person: dict[str, Any]) -> dict[str, Any]:
    from . import firebase_store
    return firebase_store.save_person(user_id, person)


def list_saved_people(user_id: int) -> list[dict[str, Any]]:
    from . import firebase_store
    return firebase_store.list_saved_people(user_id)


def delete_saved_person(user_id: int, saved_id: str) -> bool:
    from . import firebase_store
    return firebase_store.delete_saved_person(user_id, saved_id)


def refresh(refresh_token: str) -> dict:
    from . import firebase_store
    return firebase_store.refresh(refresh_token)


def logout(refresh_token: str) -> None:
    from . import firebase_store
    return firebase_store.logout(refresh_token)


def get_user(user_id: int) -> dict | None:
    from . import firebase_store
    return firebase_store.get_user(user_id)


def delete_account(user_id: int, password: str | None) -> None:
    from . import firebase_store
    return firebase_store.delete_account(user_id, password)


def usage_today(user_id: int) -> dict:
    from . import firebase_store
    return firebase_store.usage_today(user_id)


def spend(user_id: int, kind: str, limit: int) -> None:
    from . import firebase_store
    return firebase_store.spend(user_id, kind, limit)


# Attempt counters live in Firestore: serverless instances do not share memory and restart often.
WINDOW, MAX_FAILS = 15 * 60, 8


def check_rate(key: str) -> None:
    from . import firebase_store
    if firebase_store.rate_count(key, WINDOW) >= MAX_FAILS:
        raise AuthError("Too many attempts. Try again in a few minutes.", 429)


def note_failure(key: str) -> None:
    from . import firebase_store
    firebase_store.rate_add(key, WINDOW)


def clear_failures(key: str) -> None:
    from . import firebase_store
    firebase_store.rate_clear(key)
