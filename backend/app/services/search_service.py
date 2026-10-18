from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx

from ..config import settings
from .cache import search_cache
from urllib.parse import urlparse

from .previews import preview_image
from .providers import ProviderError, brave_search, pick_provider, serper_images, serper_search
from .ranker import RawHit, rank

# (platform key, query template). When provided, location narrows every platform query.
PLATFORM_QUERIES = [
    ("linkedin", 'site:linkedin.com/in "{name}"{loc}'),
    ("instagram", 'site:instagram.com "{name}"{loc}'),
    ("facebook", 'site:facebook.com "{name}"{loc}'),
    ("tiktok", 'site:tiktok.com "{name}"{loc}'),
    ("x", 'site:x.com "{name}"{loc}'),
    ("web", '"{name}"{loc}'),
]


async def _run_query(client, provider: str, platform: str, query: str, sem: asyncio.Semaphore):
    key = (provider, query)
    if key in search_cache:
        return platform, search_cache[key], True, None
    async with sem:
        try:
            fn = brave_search if provider == "brave" else serper_search
            hits = await fn(client, query)
        except ProviderError as e:
            return platform, [], False, str(e)
        except httpx.TimeoutException:
            return platform, [], False, "The search engine took too long to answer."
        except httpx.HTTPError:
            return platform, [], False, "Could not reach the search engine. Check your internet connection."
    search_cache[key] = hits
    return platform, hits, False, None


def _page_key(url: str) -> tuple[str, str]:
    """Same page = same site and same path. Ignores www, country sub-domains, query strings and a trailing slash."""
    u = urlparse(url)
    return ".".join(u.netloc.lower().split(".")[-2:]), u.path.rstrip("/").lower()


def _site_query(url: str) -> str:
    u = urlparse(url)
    return f"site:{u.netloc.lower().removeprefix('www.')}{u.path.rstrip('/')}"


async def _image_for(client, result, sem: asyncio.Semaphore) -> tuple[Optional[str], bool]:
    """(picture or None, whether a paid request was made). Failure is silent: a picture is only decoration."""
    query = _site_query(result.profile_url)
    key = ("images", query)
    if key in search_cache:
        found, fresh = search_cache[key], False
    else:
        async with sem:
            try:
                found, fresh = await serper_images(client, query, 5), True
            except (ProviderError, httpx.HTTPError):
                return None, True
        search_cache[key] = found
    want = _page_key(result.profile_url)
    return next((i["url"] for i in found if _page_key(i["link"]) == want), None), fresh


async def search_people(client: httpx.AsyncClient, name: str, location: Optional[str], requested_provider: str = "auto") -> dict:
    started = time.perf_counter()

    provider = pick_provider(requested_provider)
    safe_location = location.replace('"', '').strip() if location else ""
    loc = f' "{safe_location}"' if safe_location else ""
    sem = asyncio.Semaphore(2)
    jobs = [
        _run_query(client, provider, plat, tpl.format(name=name, loc=loc), sem)
        for plat, tpl in PLATFORM_QUERIES
    ]
    outcomes = await asyncio.gather(*jobs)

    hits: list[RawHit] = []
    warnings: list[str] = []
    fresh = cached = 0
    for platform, platform_hits, was_cached, err in outcomes:
        if err:
            warnings.append(f"{platform}: {err}")
            continue
        cached += 1 if was_cached else 0
        fresh += 0 if was_cached else 1
        for h in platform_hits:
            h.query_platform = platform
        hits.extend(platform_hits)

    if len(warnings) == len(PLATFORM_QUERIES):
        # every query failed: surface the first reason instead of an empty result
        raise ProviderError(warnings[0].split(": ", 1)[-1])

    unit = settings.brave_cost_per_request if provider == "brave" else settings.serper_cost_per_request
    results = rank(hits, name, location, limit=settings.results_limit)

    if settings.enable_result_images:
        isem = asyncio.Semaphore(4)

        async def picture_for(r):
            key = ("preview", r.profile_url)
            if key in search_cache:
                found = search_cache[key]
            else:
                found = await preview_image(client, r.profile_url)  # free: our own server reads the page header
                search_cache[key] = found
            if found or not (settings.enable_google_images and provider == "serper"):
                return found, False
            return await _image_for(client, r, isem)

        todo = [r for r in results if not r.image_url]
        pictures = await asyncio.gather(*[picture_for(r) for r in todo])
        for r, (picture, paid) in zip(todo, pictures):
            r.image_url = picture
            fresh += 1 if paid else 0

    return {
        "results": [r.model_dump() for r in results], "provider": provider,
        "took_ms": int((time.perf_counter() - started) * 1000),
        "cost_usd": round(fresh * unit, 5), "requests_made": fresh, "cached_requests": cached,
        "warnings": warnings,
    }
