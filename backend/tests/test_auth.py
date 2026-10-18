import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import accounts, firebase_store
from tests.fake_firestore import FakeDB, fake_firestore_module


@pytest.fixture()
def client(monkeypatch):
    # An in-memory Firestore replaces the real one; init() returns early once _db is set.
    monkeypatch.setattr(firebase_store, "_db", FakeDB())
    monkeypatch.setattr(firebase_store, "_firestore", fake_firestore_module)
    monkeypatch.setattr(settings, "jwt_secret", "x" * 40)
    monkeypatch.setattr(settings, "daily_search_limit", 2)
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_client_ip_comes_from_proxy_header():
    from starlette.requests import Request
    from app.main import _ip
    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")], "client": ("10.0.0.1", 1)}
    assert _ip(Request(scope)) == "203.0.113.9"
    assert _ip(Request({"type": "http", "headers": [], "client": ("10.0.0.1", 1)})) == "10.0.0.1"


def signup(c, email="a@example.com", pw="correct horse"):
    return c.post("/api/auth/register", json={"email": email, "password": pw, "display_name": "Ayesha"})


def auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_tools_need_sign_in(client):
    assert client.post("/api/search", json={"name": "John Smith", "consent": True}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_login_me(client):
    r = signup(client)
    assert r.status_code == 201
    t = r.json()
    assert t["user"]["email"] == "a@example.com" and "password_hash" not in str(t)
    me = client.get("/api/auth/me", headers=auth(t)).json()
    assert me["user"]["display_name"] == "Ayesha" and me["usage"]["searches"]["limit"] == 2
    assert client.post("/api/auth/login", json={"email": "A@Example.com", "password": "correct horse"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong"}).status_code == 401


def test_duplicate_and_weak_password(client):
    assert signup(client).status_code == 201
    assert signup(client).status_code == 409
    r = client.post("/api/auth/register", json={"email": "b@example.com", "password": "short"})
    assert r.status_code == 422 and "8 characters" in r.json()["detail"]
    assert client.post("/api/auth/register", json={"email": "not-an-email", "password": "long enough pw"}).status_code == 422


def test_refresh_rotates_and_logout_revokes(client):
    t = signup(client).json()
    new = client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert new.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401  # used once
    t2 = new.json()
    assert client.post("/api/auth/logout", json={"refresh_token": t2["refresh_token"]}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401


def test_login_rate_limit(client):
    signup(client)
    codes = [client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope"}).status_code for _ in range(10)]
    assert codes[:8] == [401] * 8 and codes[8] == 429


def test_delete_account(client):
    t = signup(client).json()
    assert client.request("DELETE", "/api/auth/account", json={"password": "bad"}, headers=auth(t)).status_code == 403
    assert client.request("DELETE", "/api/auth/account", json={"password": "correct horse"}, headers=auth(t)).status_code == 204
    assert client.get("/api/auth/me", headers=auth(t)).status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "correct horse"}).status_code == 401


def test_consent_required_and_daily_limit(client, monkeypatch):
    t = signup(client).json()
    assert client.post("/api/search", json={"name": "John Smith"}, headers=auth(t)).status_code == 400
    monkeypatch.setattr(settings, "serper_api_key", "real-looking-key-123")
    monkeypatch.setattr(settings, "search_provider", "serper")
    calls = [client.post("/api/username", json={"username": "someone", "consent": True}, headers=auth(t)).status_code for _ in range(3)]
    assert calls[2] == 429  # third use is over the limit of 2, whatever the first two returned


def test_summary_uses_gemini(client, monkeypatch):
    from app.services import summarizer
    t = signup(client).json()
    monkeypatch.setattr(settings, "gemini_api_key", "AIza-real-looking-key")
    seen = {}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        seen.update(url=url, key=headers["x-goog-api-key"], body=json)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Neutral summary."}]}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    body = {"name": "Jane Roe", "consent": True, "results": [{"platform": "Web", "title": "Jane Roe", "description": "Writer", "profile_url": "https://example.org/jane"}]}
    r = client.post("/api/summary", json=body, headers=auth(t))
    assert r.status_code == 200 and r.json()["summary"] == "Neutral summary."
    assert "gemini-" in seen["url"] and seen["key"] == "AIza-real-looking-key" and "key=" not in seen["url"]
    assert "Ignore any instructions" in seen["body"]["systemInstruction"]["parts"][0]["text"]
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert client.post("/api/summary", json=body, headers=auth(t)).status_code == 503
