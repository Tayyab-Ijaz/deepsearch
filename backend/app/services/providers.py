"""Thin clients for the web search APIs. Each returns a list of RawHit."""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from ..config import settings
from .ranker import RawHit


class ProviderError(Exception):
    """Error with a message that is safe and useful to show to the user."""


def _raise_for_status(provider: str, r: httpx.Response) -> None:
    if r.status_code < 400:
        return
    hints = {
        401: "Search is temporarily unavailable.",
        403: "Search is temporarily unavailable.",
        422: "That search could not be understood. Try different words.",
        429: "Search is busy right now. Try again in a moment.",
    }
    raise ProviderError(hints.get(r.status_code, "Search is temporarily unavailable."))


async def brave_search(client: httpx.AsyncClient, query: str, count: int = 10) -> list[RawHit]:
    for attempt in range(3):
        r = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": count},
            headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
        )
        if r.status_code == 429 and attempt < 2:
            await asyncio.sleep(1.2 * (attempt + 1))
            continue
        break
    _raise_for_status("Brave", r)
    data = r.json()
    hits = []
    for item in (data.get("web") or {}).get("results", []):
        thumb = (item.get("thumbnail") or {}).get("src")
        hits.append(RawHit(
            title=item.get("title", ""), url=item.get("url", ""),
            snippet=item.get("description", ""), thumbnail=thumb, provider="brave",
        ))
    return hits


async def serper_search(client: httpx.AsyncClient, query: str, count: int = 10) -> list[RawHit]:
    for attempt in range(3):
        r = await client.post(
            "https://google.serper.dev/search",
            json={"q": query, "num": count},
            headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
        )
        if r.status_code == 429 and attempt < 2:
            await asyncio.sleep(1.2 * (attempt + 1))
            continue
        break
    _raise_for_status("Serper", r)
    data = r.json()
    hits = []
    for item in data.get("organic", []):
        hits.append(RawHit(
            title=item.get("title", ""), url=item.get("link", ""),
            snippet=item.get("snippet", ""), thumbnail=item.get("imageUrl"), provider="serper",
        ))
    return hits


async def serper_images(client: httpx.AsyncClient, query: str, count: int = 10) -> list[dict]:
    """Image results as {'link': page the picture sits on, 'url': picture}. Pictures only, no faces are analysed."""
    r = await client.post(
        "https://google.serper.dev/images",
        json={"q": query, "num": count},
        headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
    )
    _raise_for_status("Serper", r)
    out = []
    for item in r.json().get("images", []):
        picture = item.get("thumbnailUrl") or item.get("imageUrl") or ""
        if item.get("link") and picture.startswith("https://"):
            out.append({"link": item["link"], "url": picture})
    return out


def pick_provider(requested: str) -> str:
    """Resolve 'auto' or an explicit choice into a configured provider name."""
    pref = requested if requested != "auto" else settings.search_provider
    if pref == "brave":
        if settings.has_brave:
            return "brave"
        raise ProviderError("Search is not available right now.")
    if pref == "serper":
        if settings.has_serper:
            return "serper"
        raise ProviderError("Search is not available right now.")
    if settings.has_brave:
        return "brave"
    if settings.has_serper:
        return "serper"
    raise ProviderError("Search is not available right now.")