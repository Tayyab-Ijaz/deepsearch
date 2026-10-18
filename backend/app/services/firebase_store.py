"""Firestore is the sole persistent database for accounts, usage, and metrics."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import date
from pathlib import Path
from typing import Any

from ..config import BASE_DIR, settings

log = logging.getLogger(__name__)
_db = None
_firestore = None
_firebase_admin = None
_firebase_app = None


def configured() -> bool:
    project = settings.firebase_project_id.strip()
    credentials = settings.firebase_credentials.strip()
    if not project or not credentials:
        raise RuntimeError("Set FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS; this API requires Cloud Firestore.")
    return True


def _email_id(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init() -> None:
    global _db, _firestore, _firebase_admin, _firebase_app
    if _db is not None:
        return
    configured()
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise RuntimeError("Install backend requirements to enable Firebase Firestore.") from exc

    credential_value = settings.firebase_credentials.strip()
    if len(credential_value) > 1 and credential_value[0] == credential_value[-1] and credential_value[0] in "'\"":
        credential_value = credential_value[1:-1].strip()  # an importer that kept the wrapping quotes
    if credential_value.startswith("{"):
        # Vercel stores the service-account JSON as an encrypted environment variable.
        # Local development can continue to provide a path to the JSON file instead.
        try:
            service_account_info = json.loads(credential_value)
        except json.JSONDecodeError as exc:
            raise RuntimeError("FIREBASE_CREDENTIALS must contain valid service-account JSON or a path to its JSON file.") from exc
        if not isinstance(service_account_info, dict):
            raise RuntimeError("FIREBASE_CREDENTIALS must contain a service-account JSON object.")
        firebase_credential = credentials.Certificate(service_account_info)
    else:
        credential_path = Path(credential_value)
        if not credential_path.is_absolute():
            credential_path = BASE_DIR / credential_path
        if not credential_path.is_file():
            raise RuntimeError("FIREBASE_CREDENTIALS must contain service-account JSON or point to its JSON file.")
        firebase_credential = credentials.Certificate(str(credential_path))

    try:
        app = firebase_admin.get_app("deepsearch")
    except ValueError:
        app = firebase_admin.initialize_app(
            firebase_credential,
            {"projectId": settings.firebase_project_id},
            name="deepsearch",
        )
    _firestore = firestore
    _firebase_admin = firebase_admin
    _firebase_app = app
    _db = firestore.client(app=app)


def _public_user(user: dict[str, Any]) -> dict:
    return {"id": int(user["id"]), "email": user["email"], "display_name": user.get("display_name"),
            "auth_provider": user.get("auth_provider", "password")}


def _session(user: dict[str, Any]) -> dict:
    from . import accounts

    refresh_token = secrets.token_urlsafe(48)
    _db.collection("refresh_tokens").document(_token_hash(refresh_token)).set({
        "token_hash": _token_hash(refresh_token),
        "user_id": int(user["id"]),
        "expires_at": time.time() + settings.refresh_token_days * 86400,
    })
    return {
        "user": _public_user(user),
        "access_token": accounts.make_access_token(int(user["id"])),
        "refresh_token": refresh_token,
        "expires_in": settings.access_token_minutes * 60,
    }


def _user(user_id: int) -> dict | None:
    snap = _db.collection("users").document(str(user_id)).get()
    return snap.to_dict() if snap.exists else None


def register(email: str, password: str, display_name: str | None) -> dict:
    from . import accounts

    password_hash = accounts.hash_password(password)
    transaction = _db.transaction()
    email_ref = _db.collection("email_index").document(_email_id(email))
    counter_ref = _db.collection("_system").document("user_id_counter")

    @_firestore.transactional
    def create(tx):
        if email_ref.get(transaction=tx).exists:
            from .accounts import AuthError
            raise AuthError("An account with this email already exists.", 409)
        counter = counter_ref.get(transaction=tx)
        user_id = int(counter.to_dict().get("last_id", 0) if counter.exists else 0) + 1
        user = {"id": user_id, "email": email, "display_name": display_name,
                "password_hash": password_hash, "auth_provider": "password", "created_at": time.time()}
        tx.set(counter_ref, {"last_id": user_id})
        tx.set(_db.collection("users").document(str(user_id)), user)
        tx.set(email_ref, {"user_id": user_id})
        return user

    return _session(create(transaction))


def login(email: str, password: str) -> dict:
    from . import accounts
    from .accounts import AuthError

    lookup = _db.collection("email_index").document(_email_id(email)).get()
    user = _user(int(lookup.to_dict()["user_id"])) if lookup.exists else None
    ok = accounts.verify_password(password, user.get("password_hash") if user else accounts._DUMMY_HASH)
    if not user or not ok:
        raise AuthError("Email or password is incorrect.")
    return _session(user)


def refresh(refresh_token: str) -> dict:
    from .accounts import AuthError

    token_ref = _db.collection("refresh_tokens").document(_token_hash(refresh_token))
    token = token_ref.get()
    data = token.to_dict() if token.exists else None
    if not data or data["expires_at"] < time.time():
        if data:
            token_ref.delete()
        raise AuthError("Please sign in again.")
    token_ref.delete()
    user = _user(int(data["user_id"]))
    if not user:
        raise AuthError("Please sign in again.")
    return _session(user)


def logout(refresh_token: str) -> None:
    _db.collection("refresh_tokens").document(_token_hash(refresh_token)).delete()


def get_user(user_id: int) -> dict | None:
    return _user(user_id)


def delete_account(user_id: int, password: str | None) -> None:
    from . import accounts
    from .accounts import AuthError

    user = _user(user_id)
    if not user:
        raise AuthError("Account not found.", 404)
    password_hash = user.get("password_hash")
    if password_hash and (not password or not accounts.verify_password(password, password_hash)):
        raise AuthError("Password is incorrect.", 403)
    batch = _db.batch()
    pending = 0

    def commit_if_full(force: bool = False):
        nonlocal batch, pending
        if pending >= 400 or (force and pending):
            batch.commit()
            batch = _db.batch()
            pending = 0

    batch.delete(_db.collection("users").document(str(user_id)))
    batch.delete(_db.collection("email_index").document(_email_id(user["email"])))
    pending += 2
    if user.get("firebase_uid"):
        batch.delete(_db.collection("firebase_uid_index").document(hashlib.sha256(user["firebase_uid"].encode()).hexdigest()))
        pending += 1
    for collection in ("refresh_tokens", "usage", "saved_people"):
        for snap in _db.collection(collection).where("user_id", "==", user_id).stream():
            batch.delete(snap.reference)
            pending += 1
            commit_if_full()
    commit_if_full(force=True)


def save_person(user_id: int, person: dict[str, Any]) -> dict[str, Any]:
    profile_url = str(person["profile_url"])
    saved_id = hashlib.sha256(profile_url.encode("utf-8")).hexdigest()
    ref = _db.collection("saved_people").document(f"{user_id}_{saved_id}")
    if not ref.get().exists:
        saved_at = time.time()
        ref.set({"user_id": user_id, "saved_id": saved_id, "person": person, "saved_at": saved_at})
    row = ref.get().to_dict()
    return {"id": saved_id, "person": row["person"], "saved_at": row["saved_at"]}


def list_saved_people(user_id: int) -> list[dict[str, Any]]:
    rows = _db.collection("saved_people").where("user_id", "==", user_id).stream()
    saved = []
    for snapshot in rows:
        row = snapshot.to_dict()
        saved.append({"id": row["saved_id"], "person": row["person"], "saved_at": row["saved_at"]})
    return sorted(saved, key=lambda item: item["saved_at"], reverse=True)


def delete_saved_person(user_id: int, saved_id: str) -> bool:
    if len(saved_id) != 64 or any(ch not in "0123456789abcdef" for ch in saved_id):
        return False
    ref = _db.collection("saved_people").document(f"{user_id}_{saved_id}")
    snapshot = ref.get()
    if not snapshot.exists:
        return False
    ref.delete()
    return True


def usage_today(user_id: int) -> dict:
    today = date.today().isoformat()
    used = {"search": 0, "summary": 0}
    for kind in used:
        snap = _db.collection("usage").document(f"{user_id}_{today}_{kind}").get()
        if snap.exists:
            row = snap.to_dict()
            used[kind] = int(row.get("count", 0))
    return {
        "searches": {"used": used["search"], "limit": settings.daily_search_limit},
        "summaries": {"used": used["summary"], "limit": settings.daily_summary_limit},
    }


def spend(user_id: int, kind: str, limit: int) -> None:
    from .accounts import AuthError

    today = date.today().isoformat()
    ref = _db.collection("usage").document(f"{user_id}_{today}_{kind}")
    transaction = _db.transaction()

    @_firestore.transactional
    def increment(tx):
        snap = ref.get(transaction=tx)
        count = int(snap.to_dict().get("count", 0) if snap.exists else 0)
        if count >= limit:
            raise AuthError("You have reached today's limit. It resets at midnight.", 429)
        tx.set(ref, {"user_id": user_id, "day": today, "kind": kind, "count": count + 1})

    increment(transaction)


def log_run(kind: str, provider: str, took_ms: int, cost_usd: float, n_results: int, warnings: int = 0) -> None:
    _db.collection("runs").add({
        "ts": time.time(), "kind": kind, "provider": provider, "took_ms": took_ms,
        "cost_usd": cost_usd, "n_results": n_results, "warnings": warnings,
    })


def _rate_ref(key: str):
    return _db.collection("rate_limits").document(hashlib.sha256(key.encode("utf-8")).hexdigest())


def _recent(snap, window: float) -> list[float]:
    cutoff = time.time() - window
    return [t for t in (snap.to_dict() or {}).get("attempts", []) if t > cutoff] if snap.exists else []


def rate_count(key: str, window: float) -> int:
    return len(_recent(_rate_ref(key).get(), window))


def rate_add(key: str, window: float) -> None:
    """Record one attempt. `expires_at` lets a Firestore TTL policy on `rate_limits` clean up old documents."""
    ref = _rate_ref(key)
    transaction = _db.transaction()

    @_firestore.transactional
    def append(tx):
        attempts = _recent(ref.get(transaction=tx), window) + [time.time()]
        tx.set(ref, {"attempts": attempts, "expires_at": _firestore_datetime(time.time() + window)})

    append(transaction)


def rate_clear(key: str) -> None:
    _rate_ref(key).delete()


def _firestore_datetime(ts: float):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc)
