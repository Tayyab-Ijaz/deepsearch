from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx

from ..config import settings
from .cache import search_cache
from .previews import preview_image
from .providers import ProviderError, brave_search, pick_provider, serper_images, serper_search
from .ranker import RawHit, profile_key, rank, relevant_count

log = logging.getLogger(__name__)

# A page of results is only worth another request while it still held at least this many real name matches.
MIN_RELEVANT_TO_CONTINUE = 3
PREVIEW_ATTEMPTS = 40      # best results still without a picture that get an og:image lookup
PREVIEW_TIMEOUT = 5.0
# Google Images does not index these, so a targeted lookup would only spend a request.
NO_IMAGE_LOOKUP = {"tiktok", "threads"}


@dataclass(frozen=True)
class Platform:
    key: str
    query: str   # web query; when a location is given it narrows every platform query
    site: str    # filter for the Google Images query ("" = anywhere on the web)


PLATFORMS = [
    Platform("linkedin", 'site:linkedin.com/in "{name}"{loc}', "site:linkedin.com/in"),
    Platform("instagram", 'site:instagram.com "{name}"{loc}', "site:instagram.com"),
    Platform("facebook", 'site:facebook.com "{name}"{loc}', "site:facebook.com"),
    Platform("tiktok", 'site:tiktok.com "{name}"{loc}', "site:tiktok.com"),
    Platform("x", 'site:x.com "{name}"{loc}', "site:x.com"),
    Platform("youtube", 'site:youtube.com "{name}"{loc}', "site:youtube.com"),
    Platform("threads", '(site:threads.net OR site:threads.com) "{name}"{loc}', "(site:threads.net OR site:threads.com)"),
    Platform("github", 'site:github.com "{name}"{loc}', "site:github.com"),
    Platform("pinterest", 'site:pinterest.com "{name}"{loc}', "site:pinterest.com"),
    Platform("web", '"{name}"{loc}', ""),
]


class _Run:
    """Everything one search collects while its platforms run side by side."""

    def __init__(self, client: httpx.AsyncClient, provider: str, name: str, location: Optional[str]):
        self.client, self.provider, self.name, self.location = client, provider, name, location
        self.sem = asyncio.Semaphore(settings.search_concurrency if provider == "serper" else 2)
        self.hits: list[RawHit] = []
        self.warnings: dict[str, str] = {}   # platform -> message (first problem only)
        self.fresh = self.cached = self.attempted = self.failed = 0

    async def fetch(self, kind: str, query: str, page: int) -> tuple[list[RawHit], bool]:
        """(hits, served_from_cache). Raises ProviderError / httpx errors for the caller to judge."""
        key = (self.provider, kind, query, page)
        if key in search_cache:
            return search_cache[key], True
        fn = serper_images if kind == "images" else (brave_search if self.provider == "brave" else serper_search)
        async with self.sem:
            hits = await fn(self.client, query, page)
        search_cache[key] = hits
        return hits, False

    async def pages(self, plat: Platform, kind: str, query: str, max_pages: int) -> None:
        for page in range(1, max_pages + 1):
            try:
                hits, was_cached = await self.fetch(kind, query, page)
            except ProviderError as e:
                self._problem(plat, kind, page, str(e))
                return
            except httpx.TimeoutException:
                self._problem(plat, kind, page, "The search engine took too long to answer.")
                return
            except httpx.HTTPError:
                self._problem(plat, kind, page, "Could not reach the search engine. Check your internet connection.")
                return
            if kind == "search" and page == 1:
                self.attempted += 1
            self.cached += 1 if was_cached else 0
            self.fresh += 0 if was_cached else 1
            for h in hits:
                h.query_platform = plat.key
            self.hits.extend(hits)
            if relevant_count(hits, self.name, self.location, plat.key) < MIN_RELEVANT_TO_CONTINUE:
                return

    def _problem(self, plat: Platform, kind: str, page: int, message: str) -> None:
        if kind == "search" and page == 1:
            self.attempted += 1
            self.failed += 1
        if kind == "search" and plat.key not in self.warnings:
            self.warnings[plat.key] = message
        else:
            log.info("%s %s page %s failed: %s", plat.key, kind, page, message)   # pictures are only decoration

    async def platform(self, plat: Platform, loc: str) -> None:
        jobs = [self.pages(plat, "search", plat.query.format(name=self.name, loc=loc), max(1, settings.search_pages))]
        if settings.enable_platform_images and self.provider == "serper" and settings.image_pages > 0:
            image_query = f'"{self.name}" {plat.site}'.strip()
            jobs.append(self.pages(plat, "images", image_query, settings.image_pages))
        await asyncio.gather(*jobs)


async def _fill_previews(run: _Run, results: list) -> None:
    """Results that still have no picture: try the page's own preview image (free, read by this server)."""
    todo = [r for r in results if not r.image_url][:PREVIEW_ATTEMPTS]
    sem = asyncio.Semaphore(20)

    async def one(r):
        key = ("preview", r.profile_url)
        if key in search_cache:
            return search_cache[key]
        async with sem:
            try:
                found = await asyncio.wait_for(preview_image(run.client, r.profile_url), PREVIEW_TIMEOUT)
            except asyncio.TimeoutError:
                return None
        search_cache[key] = found
        return found

    for r, picture in zip(todo, await asyncio.gather(*[one(r) for r in todo])):
        r.image_url = picture


async def _lookup_pictures(run: _Run, results: list) -> None:
    """The best-ranked profiles still without a picture get one Google Images lookup for their exact page."""
    todo = [r for r in results if not r.image_url and r.platform_key not in NO_IMAGE_LOOKUP][:max(0, settings.image_lookups)]

    async def one(r):
        u = urlparse(r.profile_url)
        query = f"site:{(u.hostname or '').removeprefix('www.')}{u.path.rstrip('/')}"
        try:
            hits, was_cached = await run.fetch("images", query, 1)
        except (ProviderError, httpx.HTTPError):
            return None
        run.cached += 1 if was_cached else 0
        run.fresh += 0 if was_cached else 1
        want = profile_key(r.profile_url)
        return next((h.thumbnail for h in hits if profile_key(h.url) == want), None)

    for r, picture in zip(todo, await asyncio.gather(*[one(r) for r in todo])):
        r.image_url = r.image_url or picture


async def search_people(client: httpx.AsyncClient, name: str, location: Optional[str], requested_provider: str = "auto") -> dict:
    started = time.perf_counter()

    provider = pick_provider(requested_provider)
    safe_location = location.replace('"', '').strip() if location else ""
    loc = f' "{safe_location}"' if safe_location else ""

    run = _Run(client, provider, name, location)
    await asyncio.gather(*[run.platform(p, loc) for p in PLATFORMS])
    searched_ms = int((time.perf_counter() - started) * 1000)

    warnings = [f"{platform}: {message}" for platform, message in run.warnings.items()]
    if run.attempted and run.failed == run.attempted:
        # every platform failed: surface the first reason instead of an empty result
        raise ProviderError(next(iter(run.warnings.values()), "Search is temporarily unavailable."))

    unit = settings.brave_cost_per_request if provider == "brave" else settings.serper_cost_per_request
    results = rank(run.hits, name, location, limit=settings.results_limit)

    if settings.enable_result_images:
        await _fill_previews(run, results)
    previews_ms = int((time.perf_counter() - started) * 1000)
    if settings.enable_platform_images and provider == "serper":
        await _lookup_pictures(run, results)

    return {
        "results": [r.model_dump() for r in results], "provider": provider,
        "took_ms": int((time.perf_counter() - started) * 1000), "phase_ms": {"search": searched_ms, "previews": previews_ms},
        "cost_usd": round(run.fresh * unit, 5), "requests_made": run.fresh, "cached_requests": run.cached,
        "warnings": warnings,
    }
