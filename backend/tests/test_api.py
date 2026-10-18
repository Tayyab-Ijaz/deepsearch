import json

import httpx
import pytest

from app.config import settings
from app.services import search_service
from app.services.cache import search_cache


def brave_handler(request: httpx.Request) -> httpx.Response:
    q = request.url.params.get("q", "")
    if "linkedin" in q:
        results = [{"title": "John Smith - Engineer | LinkedIn", "url": "https://www.linkedin.com/in/john-smith-1a2b3c4d",
                    "description": "New York"}]
    elif "instagram" in q:
        results = [{"title": "John Smith (@johnsmith) • Instagram", "url": "https://www.instagram.com/johnsmith/",
                    "description": "bio", "thumbnail": {"src": "https://img.example/x.jpg"}}]
    else:
        results = []
    return httpx.Response(200, json={"web": {"results": results}})


@pytest.mark.asyncio
async def test_search_pipeline_with_mock_brave(monkeypatch):
    monkeypatch.setattr(settings, "brave_api_key", "real-looking-key-123")
    search_cache.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(brave_handler)) as client:
        out = await search_service.search_people(client, "John Smith", None, "brave")
    platforms = {r["platform_key"] for r in out["results"]}
    assert platforms == {"linkedin", "instagram"}
    n = len(search_service.PLATFORMS)  # a page with fewer than 3 real matches is never followed by another
    assert out["requests_made"] == n and out["cost_usd"] == pytest.approx(n * settings.brave_cost_per_request)
    assert out["results"][0]["match_score"] >= 0.85


@pytest.mark.asyncio
async def test_all_queries_failing_raises(monkeypatch):
    from app.services.providers import ProviderError
    monkeypatch.setattr(settings, "brave_api_key", "real-looking-key-123")
    search_cache.clear()
    handler = lambda req: httpx.Response(401, json={})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError):
            await search_service.search_people(client, "John Smith", None, "brave")


def test_placeholder_keys_are_not_configured():
    from app.config import is_set
    assert not is_set("PASTE_YOUR_BRAVE_API_KEY_HERE")
    assert not is_set("")
    assert is_set("BSAabc123realkey")


def serper_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    q = body["q"]
    if request.url.path == "/images":
        if q == '"John Smith" site:instagram.com':
            return httpx.Response(200, json={"images": [
                {"title": "post", "link": "https://www.instagram.com/p/OTHER/", "thumbnailUrl": "https://img.example/wrong.jpg"},
                {"title": "John Smith (@johnsmith) • Instagram", "link": "https://instagram.com/johnsmith/", "thumbnailUrl": "https://img.example/right.jpg"}]})
        return httpx.Response(200, json={"images": []})
    if "instagram" in q:
        organic = [{"title": "John Smith (@johnsmith) • Instagram", "link": "https://www.instagram.com/johnsmith/", "snippet": "bio"}]
    elif "linkedin" in q:
        organic = [{"title": "John Smith - Engineer | LinkedIn", "link": "https://www.linkedin.com/in/john-smith-1a2b3c4d", "snippet": "NY"}]
    else:
        organic = []
    return httpx.Response(200, json={"organic": organic})


@pytest.fixture()
def serper(monkeypatch):
    monkeypatch.setattr(settings, "serper_api_key", "real-looking-key-123")
    monkeypatch.setattr(settings, "enable_result_images", False)
    search_cache.clear()

    async def go(handler, name="John Smith"):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await search_service.search_people(client, name, None, "serper")
    return go


@pytest.mark.asyncio
async def test_result_picture_comes_only_from_the_exact_page(serper, monkeypatch):
    monkeypatch.setattr(settings, "image_lookups", 0)
    out = await serper(serper_handler)
    by = {r["platform_key"]: r for r in out["results"]}
    assert by["instagram"]["image_url"] == "https://img.example/right.jpg"   # same profile, not the post
    assert by["linkedin"]["image_url"] is None                               # no match, no picture
    n = len(search_service.PLATFORMS)
    assert out["requests_made"] == 2 * n                                     # one results page + one picture page each


@pytest.mark.asyncio
async def test_missing_picture_gets_one_targeted_lookup(serper, monkeypatch):
    monkeypatch.setattr(settings, "image_lookups", 5)
    seen = []

    def handler(request):
        seen.append(json.loads(request.content)["q"])
        return serper_handler(request)

    out = await serper(handler)
    assert "site:linkedin.com/in/john-smith-1a2b3c4d" in seen                # the profile that had no picture
    assert not any(q.startswith("site:instagram.com/johnsmith") for q in seen)  # the one that had one is left alone
    assert out["requests_made"] == 2 * len(search_service.PLATFORMS) + 1


@pytest.mark.asyncio
async def test_pictures_can_be_switched_off(serper, monkeypatch):
    monkeypatch.setattr(settings, "enable_platform_images", False)
    out = await serper(serper_handler)
    assert out["requests_made"] == len(search_service.PLATFORMS)
    assert all(r["image_url"] is None for r in out["results"])


@pytest.mark.asyncio
async def test_more_pages_only_while_they_keep_matching(serper, monkeypatch):
    monkeypatch.setattr(settings, "enable_platform_images", False)
    monkeypatch.setattr(settings, "search_pages", 3)
    pages = {}

    def handler(request):
        body = json.loads(request.content)
        page = body.get("page", 1)
        if "linkedin" in body["q"]:
            pages.setdefault("linkedin", []).append(page)
            # pages 1 and 2 are full of real matches; page 3 is not asked for because the limit is 3 pages
            organic = [{"title": f"John Smith - Person {page}{i} | LinkedIn", "link": f"https://www.linkedin.com/in/john-smith-{page}{i}",
                        "snippet": ""} for i in range(4)]
        elif "instagram" in body["q"]:
            pages.setdefault("instagram", []).append(page)
            organic = [{"title": "Somebody Else (@else) • Instagram", "link": "https://www.instagram.com/else/", "snippet": ""}]
        else:
            organic = []
        return httpx.Response(200, json={"organic": organic})

    out = await serper(handler)
    assert pages["linkedin"] == [1, 2, 3]       # kept finding matches, so it kept going (up to the limit)
    assert pages["instagram"] == [1]            # nothing matched, so no second page was bought
    assert len([r for r in out["results"] if r["platform_key"] == "linkedin"]) == 12
    assert out["requests_made"] == 3 + len(search_service.PLATFORMS) - 1
