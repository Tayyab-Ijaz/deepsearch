"""Aggregate operational metrics stored in Cloud Firestore only."""
from . import firebase_store


def init() -> None:
    # Firebase is initialized by the account service during application startup.
    return None


def log_run(kind: str, provider: str, took_ms: int, cost_usd: float, n_results: int, warnings: int = 0) -> None:
    firebase_store.log_run(kind, provider, took_ms, cost_usd, n_results, warnings)
