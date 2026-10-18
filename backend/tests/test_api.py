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
    assert out["requests_made"] == 6 and out["cost_usd"] == pytest.approx(6 * settings.brave_cost_per_request)
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
    if request.url.path == "/images":
        if "instagram.com/johnsmith" in body["q"]:
            return httpx.Response(200, json={"images": [
                {"link": "https://www.instagram.com/johnsmith/p/OTHER/", "thumbnailUrl": "https://img.example/wrong.jpg"},
                {"link": "https://instagram.com/johnsmith/", "thumbnailUrl": "https://img.example/right.jpg"}]})
        return httpx.Response(200, json={"images": []})
    q = body["q"]
    if "instagram" in q:
        organic = [{"title": "John Smith (@johnsmith) • Instagram", "link": "https://www.instagram.com/johnsmith/", "snippet": "bio"}]
    elif "linkedin" in q:
        organic = [{"title": "John Smith - Engineer | LinkedIn", "link": "https://www.linkedin.com/in/john-smith-1a2b3c4d", "snippet": "NY"}]
    else:
        organic = []
    return httpx.Response(200, json={"organic": organic})


@pytest.mark.asyncio
async def test_result_picture_comes_only_from_the_exact_page(monkeypatch):
    monkeypatch.setattr(settings, "serper_api_key", "real-looking-key-123")
    monkeypatch.setattr(settings, "enable_result_images", True)
    monkeypatch.setattr(settings, "enable_google_images", True)

    async def no_preview(client, url):
        return None
    monkeypatch.setattr(search_service, "preview_image", no_preview)
    search_cache.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(serper_handler)) as client:
        out = await search_service.search_people(client, "John Smith", None, "serper")
    by = {r["platform_key"]: r for r in out["results"]}
    assert by["instagram"]["image_url"] == "https://img.example/right.jpg"   # same page, not the post
    assert by["linkedin"]["image_url"] is None                               # no match, no picture
    assert out["requests_made"] == 6 + 2                                     # 6 searches + 2 picture lookups

    search_cache.clear()
    monkeypatch.setattr(settings, "enable_result_images", False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(serper_handler)) as client:
        off = await search_service.search_people(client, "John Smith", None, "serper")
    assert off["requests_made"] == 6 and all(r["image_url"] is None for r in off["results"])
