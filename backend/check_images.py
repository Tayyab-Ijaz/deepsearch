"""Runs a real search and shows which of the final results got a picture.

Run from the backend folder, with the virtual environment active:
    python check_images.py "Satya Nadella"
"""
import asyncio
import sys
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.search_service import search_people


async def main(name: str) -> None:
    print(f'Name: "{name}"   ENABLE_RESULT_IMAGES={settings.enable_result_images}\n')
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        out = await search_people(client, name, None, "auto")
    shown = 0
    for r in out["results"]:
        has = bool(r["image_url"])
        shown += has
        where = urlparse(r["image_url"]).netloc if has else "-"
        print(f'{r["platform"]:10s} {"IMAGE" if has else "no   "}  {where:30s} {r["profile_url"][:60]}')
    print(f'\n{shown} of {len(out["results"])} results have a picture.')
    print(f'Search requests used: {out["requests_made"]} (cost about ${out["cost_usd"]})')
    for w in out["warnings"]:
        print("warning:", w)


asyncio.run(main(" ".join(sys.argv[1:]) or "Satya Nadella"))