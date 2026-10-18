"""Link preview picture: the image a page itself names as its preview (the og:image tag).

This is the same picture a chat app shows when you paste the link, so it is exactly what the
page presents. We identify ourselves honestly, never log in, never follow a page into a
private network, and only read the first part of the page. Sites that refuse (many social
networks do for non-logged-in programs) simply give no picture, and the app shows an icon."""
from __future__ import annotations

import asyncio
import ipaddress
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; DeepSearchPreview/1.0)"
MAX_BYTES = 262_144
MAX_REDIRECTS = 3
WANTED = {"og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"}


class _MetaImages(HTMLParser):
    """Collects image meta tags and stops being useful once </head> is seen."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: dict[str, str] = {}
        self.done = False

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        key = (a.get("property") or a.get("name") or "").lower()
        if key in WANTED and a.get("content") and key not in self.found:
            self.found[key] = a["content"].strip()

    def handle_endtag(self, tag):
        if tag == "head":
            self.done = True


def pick_image(html: str, base_url: str) -> Optional[str]:
    parser = _MetaImages()
    try:
        parser.feed(html)
    except Exception:
        pass
    for key in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"):
        value = parser.found.get(key)
        if value:
            absolute = urljoin(base_url, value)
            if absolute.startswith("https://") and len(absolute) <= 2000:
                return absolute
    return None


async def is_public_host(host: str) -> bool:
    """True only if every address the name points to is a normal public internet address."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, 443, type=0)
    except OSError:
        return False
    if not infos:
        return False
    try:
        return all(ipaddress.ip_address(i[4][0]).is_global for i in infos)
    except ValueError:
        return False


async def _allowed(url: str) -> bool:
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return False
    if u.port not in (None, 443):
        return False
    return await is_public_host(u.hostname)


async def preview_image(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """The page's own preview picture, or None. Never raises: a picture is only decoration."""
    try:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if not await _allowed(current):
                return None
            async with client.stream("GET", current, headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                                     follow_redirects=False) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    location = r.headers.get("location")
                    if not location:
                        return None
                    current = urljoin(current, location)
                    continue
                if r.status_code != 200 or "html" not in r.headers.get("content-type", "").lower():
                    return None
                buf, parser_done = b"", False
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) >= MAX_BYTES or b"</head>" in buf.lower():
                        parser_done = True
                        break
                charset = r.encoding or "utf-8"
            html = buf[:MAX_BYTES].decode(charset, errors="ignore")
            return pick_image(html, current)
        return None
    except Exception:
        return None
