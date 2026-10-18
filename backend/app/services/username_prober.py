"""Checks whether a username exists on public platforms by requesting the public URL.

No logins, no scraping of private content. Each platform is also tested with a random
fake username (the "self-test"). If a platform says "found" for a fake name it is a
catch-all and its answers are marked unreliable.
"""
from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from urllib.parse import quote

import httpx

from .cache import probe_reliability_cache

PLATFORMS = json.loads((Path(__file__).resolve().parent.parent / "data" / "platforms.json").read_text(encoding="utf-8"))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DeepSearchAI/1.0)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}


def _fake_username() -> str:
    return "zq" + secrets.token_hex(6)


async def probe_one(client: httpx.AsyncClient, platform: dict, username: str) -> dict:
    """Return {'status': found|not_found|unknown, 'url': ..., 'detail': ...}."""
    url = platform["url"].format(u=quote(username, safe=""))
    shown_url = _public_url(platform, username)
    try:
        r = await client.get(url, headers=HEADERS, follow_redirects=True)
    except httpx.TimeoutException:
        return {"status": "unknown", "url": shown_url, "detail": "timeout"}
    except httpx.HTTPError as e:
        # Say what really failed (DNS, SSL, connection refused...) so it can be fixed.
        reason = str(e).strip()[:120] or "no message"
        return {"status": "unknown", "url": shown_url, "detail": f"network error: {type(e).__name__}: {reason}"}

    if r.status_code in (401, 403, 429, 999) or r.status_code >= 500:
        return {"status": "unknown", "url": shown_url, "detail": f"blocked or unavailable (HTTP {r.status_code})"}

    check = platform["check"]
    if check == "status":
        status = "found" if r.status_code == 200 else "not_found" if r.status_code == 404 else "unknown"
    elif check == "absent_text":
        status = "not_found" if platform["absent"] in r.text else "found" if r.status_code == 200 else "unknown"
    elif check == "json_not_null":
        status = "not_found" if r.text.strip() in ("null", "") else "found"
    elif check == "json_nonempty":
        try:
            status = "found" if json.loads(r.text) else "not_found"
        except ValueError:
            status = "unknown"
    else:
        status = "unknown"
    return {"status": status, "url": shown_url, "detail": f"HTTP {r.status_code}"}


def _public_url(platform: dict, username: str) -> str:
    return {"gitlab": f"https://gitlab.com/{username}", "hackernews": f"https://news.ycombinator.com/user?id={username}"}.get(
        platform["key"], platform["url"].format(u=username)
    )


async def selftest(client: httpx.AsyncClient, force: bool = False) -> dict[str, dict]:
    """Per platform: reliable True/False + reason. Cached for an hour."""
    if not force and "selftest" in probe_reliability_cache:
        return probe_reliability_cache["selftest"]
    sem = asyncio.Semaphore(6)

    async def one(p):
        async with sem:
            res = await probe_one(client, p, _fake_username())
        if res["status"] == "found":
            return p["key"], {"reliable": False, "reason": "Says a fake username exists (catch-all)."}
        if res["status"] == "unknown":
            return p["key"], {"reliable": False, "reason": f"Could not check from this network ({res['detail']})."}
        return p["key"], {"reliable": True, "reason": "Fake username correctly reported as not found."}

    out = dict(await asyncio.gather(*[one(p) for p in PLATFORMS]))
    # Do not cache a run where nothing could be checked, so a fixed network works at once.
    if any(v["reliable"] for v in out.values()):
        probe_reliability_cache["selftest"] = out
    return out


def verdict_for(res: dict, rel: dict) -> tuple[str, str]:
    """One plain label plus a reason a person can read."""
    reliable, note = rel.get("reliable"), rel.get("reason", "")
    if res["status"] == "found":
        if reliable is True:
            return "confirmed", "Page exists, and this platform correctly rejects made-up names."
        if "catch-all" in note:
            return "unverified", "This platform shows a page for any name, so existence cannot be confirmed."
        return "unverified", "Page exists, but the reliability check did not finish."
    if res["status"] == "not_found":
        return "not_found", "No profile with this name." if reliable is True else "No profile found (reliability check incomplete)."
    d = res["detail"]
    if "403" in d or "429" in d:
        return "unchecked", "The platform blocked the request, so there is no answer."
    if "timeout" in d:
        return "unchecked", "The platform did not answer in time."
    return "unchecked", "No answer from this platform."


async def probe_username(client: httpx.AsyncClient, username: str, run_selftest: bool = True) -> list[dict]:
    reliability = await selftest(client) if run_selftest else {}
    sem = asyncio.Semaphore(6)

    async def one(p):
        async with sem:
            res = await probe_one(client, p, username)
        rel = reliability.get(p["key"], {"reliable": None, "reason": "Self-test skipped."})
        verdict, reason = verdict_for(res, rel)
        return {
            "key": p["key"], "platform": p["name"], "experimental": bool(p.get("experimental")),
            "verdict": verdict, "reason": reason,
            "url": res["url"] if res["status"] == "found" else None,
        }

    return list(await asyncio.gather(*[one(p) for p in PLATFORMS]))
