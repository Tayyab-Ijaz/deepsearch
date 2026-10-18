import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import settings
from app.services import firebase_store, mailer
from tests.fake_firestore import FakeDB, fake_firestore_module

EMAIL, OLD, NEW = "ayesha@example.com", "correct horse", "brand new pass"


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setattr(firebase_store, "_db", FakeDB())
    monkeypatch.setattr(firebase_store, "_firestore", fake_firestore_module)
    monkeypatch.setattr(settings, "jwt_secret", "x" * 40)
    monkeypatch.setattr(settings, "resend_api_key", "re_real_looking_key_123")
    monkeypatch.setattr(main, "RESET_MIN_SECONDS", 0)
    sent = []
    monkeypatch.setattr(mailer, "send_reset_code", lambda to, code, minutes: sent.append((to, code)))
    with TestClient(main.app) as c:
        yield c, sent


def signup(c, email=EMAIL):
    r = c.post("/api/auth/register", json={"email": email, "password": OLD, "display_name": "Ayesha"})
    assert r.status_code == 201
    return r.json()


def ask(c, email=EMAIL):
    return c.post("/api/auth/forgot-password", json={"email": email})


def reset(c, code, password=NEW, email=EMAIL):
    return c.post("/api/auth/reset-password", json={"email": email, "code": code, "new_password": password})


def login(c, password, email=EMAIL):
    return c.post("/api/auth/login", json={"email": email, "password": password}).status_code


def test_full_flow_changes_password_and_signs_out_other_devices(env):
    c, sent = env
    tokens = signup(c)
    assert ask(c).status_code == 202
    (to, code), = sent
    assert to == EMAIL and len(code) == 6 and code.isdigit()

    assert reset(c, code).status_code == 204
    assert login(c, NEW) == 200
    assert login(c, OLD) == 401
    # the session that existed before the reset no longer works: refresh token revoked, access token rejected
    assert c.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer " + tokens["access_token"]}).status_code == 401
    # ...but a session started after it does
    fresh = c.post("/api/auth/login", json={"email": EMAIL, "password": NEW}).json()
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer " + fresh["access_token"]}).status_code == 200


def test_code_works_only_once(env):
    c, sent = env
    signup(c)
    ask(c)
    code = sent[0][1]
    assert reset(c, code).status_code == 204
    assert reset(c, code, "another good pass").status_code == 400


def test_unknown_email_gets_the_same_answer_and_no_email(env):
    c, sent = env
    signup(c)
    known, unknown = ask(c), ask(c, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert [to for to, _ in sent] == [EMAIL]


def test_wrong_codes_lock_the_code_after_five_tries(env):
    c, sent = env
    signup(c)
    ask(c)
    good = sent[0][1]
    wrong = "000000" if good != "000000" else "111111"
    assert [reset(c, wrong).status_code for _ in range(5)] == [400] * 5
    assert reset(c, good).status_code == 400            # locked, even with the right code
    assert login(c, OLD) == 200                         # and nothing changed


def test_expired_code_is_refused(env, monkeypatch):
    c, sent = env
    signup(c)
    ask(c)
    doc = firebase_store._db.data["password_resets"]
    key = next(iter(doc))
    doc[key]["expires_at"] = 0
    assert reset(c, sent[0][1]).status_code == 400


def test_new_request_replaces_the_old_code(env):
    c, sent = env
    signup(c)
    ask(c)
    ask(c)
    first, second = sent[0][1], sent[1][1]
    if first != second:
        assert reset(c, first).status_code == 400
    assert reset(c, second).status_code == 204


def test_code_is_not_stored_in_plain_text(env):
    c, sent = env
    signup(c)
    ask(c)
    stored = str(firebase_store._db.data["password_resets"])
    assert sent[0][1] not in stored.replace("code_hash", "")  # only a keyed hash is saved


def test_requests_are_rate_limited(env):
    c, sent = env
    signup(c)
    codes = [ask(c).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]               # three emails per address per 15 minutes
    assert len(sent) == 3


def test_validation(env):
    c, _ = env
    assert ask(c, "not-an-email").status_code == 422
    assert reset(c, "12345").status_code == 422
    assert reset(c, "abcdef").status_code == 422
    short = reset(c, "123456", "short")
    assert short.status_code == 422 and short.json()["detail"] == "Use at least 8 characters for the password."


def test_unavailable_when_email_is_not_configured(env, monkeypatch):
    c, sent = env
    monkeypatch.setattr(settings, "resend_api_key", "")
    r = ask(c)
    assert r.status_code == 503 and "contact support" in r.json()["detail"].lower() and not sent


def test_send_failure_does_not_reveal_anything(env, monkeypatch):
    c, _ = env
    signup(c)

    def boom(*a):
        raise mailer.MailError("down")
    monkeypatch.setattr(mailer, "send_reset_code", boom)
    assert ask(c).status_code == 202


def test_mailer_posts_to_resend_without_leaking_the_key(monkeypatch):
    import httpx
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, auth=headers["Authorization"], body=json)
        return httpx.Response(200, json={"id": "1"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "resend_api_key", "re_real_looking_key_123")
    monkeypatch.setattr(httpx, "post", fake_post)
    mailer.send_reset_code("a@example.com", "123456", 15)
    assert seen["url"] == "https://api.resend.com/emails" and seen["auth"] == "Bearer re_real_looking_key_123"
    assert seen["body"]["to"] == ["a@example.com"] and "123456" in seen["body"]["text"]
    assert seen["body"]["from"] == "DeepSearch AI <info@wellminddatasolutions.com>"


def test_public_pages_for_the_app_store(env):
    c, _ = env
    for path, words in (("/privacy", ("Privacy Policy", "Resend", "Serper", "Delete Account")),
                        ("/terms", ("Terms of Use", "identity verification")),
                        ("/support", ("info@wellminddatasolutions.com", "Forgot password"))):
        r = c.get(path)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/html"), path
        assert all(w in r.text for w in words), path
        assert "info@wellminddatasolutions.com" in r.text
