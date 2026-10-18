import httpx
import pytest

from app.config import settings
from app.services import previews, search_service
from app.services.search_service import search_cache
from tests.test_api import serper_handler


async def _yes(host):
    return True


async def _not_internal(host):
    return host != "internal.example"


def test_pick_image_reads_og_and_resolves_relative():
    html = '<head><meta property="og:image" content="/me.jpg"></head>'
    assert previews.pick_image(html, "https://site.example/u/1") == "https://site.example/me.jpg"


def test_pick_image_rejects_http():
    html = '<head><meta property="og:image" content="http://site.example/me.jpg"></head>'
    assert previews.pick_image(html, "https://site.example/") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://site.example/", "https://site.example:8443/", "https://u:p@site.example/",
])
async def test_preview_blocks_unsafe_urls(url, monkeypatch):
    monkeypatch.setattr(previews, "is_public_host", _yes)
    def boom(request):
        raise AssertionError("must not fetch")
    async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as c:
        assert await previews.preview_image(c, url) is None


@pytest.mark.asyncio
async def test_preview_blocks_private_hosts():
    def boom(request):
        raise AssertionError("must not fetch")
    async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as c:
        assert await previews.preview_image(c, "https://localhost/") is None
        assert await previews.preview_image(c, "https://127.0.0.1/") is None


@pytest.mark.asyncio
async def test_preview_revalidates_redirects(monkeypatch):
    monkeypatch.setattr(previews, "is_public_host", _not_internal)
    def handler(request):
        if request.url.host == "a.example":
            return httpx.Response(302, headers={"location": "https://internal.example/x"})
        raise AssertionError("must not fetch internal")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        assert await previews.preview_image(c, "https://a.example/") is None


@pytest.mark.asyncio
async def test_preview_follows_safe_redirect_and_reads_image(monkeypatch):
    monkeypatch.setattr(previews, "is_public_host", _yes)
    def handler(request):
        if request.url.host == "a.example":
            return httpx.Response(301, headers={"location": "https://b.example/p"})
        return httpx.Response(200, headers={"content-type": "text/html"},
                              content=b'<head><meta property="og:image" content="https://cdn.example/p.jpg"></head>')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        assert await previews.preview_image(c, "https://a.example/") == "https://cdn.example/p.jpg"


@pytest.mark.asyncio
async def test_pipeline_uses_page_preview_without_extra_paid_requests(monkeypatch):
    monkeypatch.setattr(settings, "serper_api_key", "real-looking-key-123")
    monkeypatch.setattr(settings, "enable_result_images", True)
    monkeypatch.setattr(settings, "enable_platform_images", False)
    async def fake(client, url):
        return "https://cdn.example/page.jpg"
    monkeypatch.setattr(search_service, "preview_image", fake)
    search_cache.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(serper_handler)) as c:
        out = await search_service.search_people(c, "John Smith", None, "serper")
    assert out["results"] and all(r["image_url"] == "https://cdn.example/page.jpg" for r in out["results"])
    assert out["requests_made"] == len(search_service.PLATFORMS)   # one results page per platform, nothing extra for pictures
