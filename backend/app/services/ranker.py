"""Turns raw search hits into ranked, labelled profile results.

Rules this module enforces:
  * only real hits from the search API are ever returned (nothing is invented)
  * the label describes NAME similarity only, never "same person"
  * junk (posts, reels, hashtag pages, very weak matches) is dropped
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from rapidfuzz import fuzz

from ..models import Result

PLATFORM_NAMES = {
    "linkedin": "LinkedIn",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "x": "X",
    "youtube": "YouTube",
    "threads": "Threads",
    "github": "GitHub",
    "pinterest": "Pinterest",
    "web": "Web",
}

MIN_SCORE = 0.45
STRONG = 0.85
POSSIBLE = 0.65

_IG_RESERVED = {"p", "reel", "reels", "explore", "stories", "tv", "accounts", "directory", "about", "legal"}
_FB_RESERVED = {
    "watch", "groups", "events", "marketplace", "pages", "photo", "photos", "posts", "story", "share",
    "hashtag", "public", "reel", "login", "policies", "help", "privacy", "gaming", "people", "videos",
}
_X_RESERVED = {"home", "search", "i", "explore", "hashtag", "intent", "share", "settings", "login", "tos", "privacy", "compose"}
_GITHUB_RESERVED = {
    "features", "topics", "about", "pricing", "login", "join", "marketplace", "sponsors", "orgs", "explore",
    "collections", "trending", "settings", "notifications", "issues", "pulls", "search", "enterprise",
    "security", "customer-stories", "readme", "site", "apps", "events", "new", "organizations", "codespaces",
}
_PINTEREST_RESERVED = {
    "pin", "ideas", "search", "today", "explore", "business", "about", "topics", "categories", "login",
    "videos", "news_hub", "settings", "create", "following", "_", "oauth",
}

_PROFILE_PATTERNS = {
    "linkedin": re.compile(r"^https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/([^/?#]+)/?", re.I),
    "instagram": re.compile(r"^https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]+)/?(?:[?#].*)?$", re.I),
    "facebook": re.compile(r"^https?://(?:www\.|m\.|[a-z]{2}-[a-z]{2}\.)?facebook\.com/([A-Za-z0-9.\-]+)/?(?:[?#].*)?$", re.I),
    "tiktok": re.compile(r"^https?://(?:www\.)?tiktok\.com/@([A-Za-z0-9._]+)/?(?:[?#].*)?$", re.I),
    "x": re.compile(r"^https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/?(?:[?#].*)?$", re.I),
    "youtube": re.compile(
        r"^https?://(?:www\.|m\.)?youtube\.com/(@[A-Za-z0-9._\-%]+|channel/[A-Za-z0-9_\-]+|c/[^/?#]+|user/[^/?#]+)"
        r"(?:/(?:about|featured|videos|shorts|playlists|community|streams|releases))?/?(?:[?#].*)?$", re.I),
    "threads": re.compile(r"^https?://(?:www\.)?threads\.(?:net|com)/@([A-Za-z0-9._]+)/?(?:[?#].*)?$", re.I),
    "github": re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/?(?:[?#].*)?$", re.I),
    "pinterest": re.compile(r"^https?://(?:www\.|[a-z]{2}\.)?pinterest\.[a-z.]{2,6}/([A-Za-z0-9_]{3,30})/?(?:[?#].*)?$", re.I),
}
_SOCIAL_DOMAINS = (
    "linkedin.com", "instagram.com", "facebook.com", "tiktok.com", "x.com", "twitter.com",
    "youtube.com", "threads.net", "threads.com", "github.com", "pinterest.com",
)


@dataclass
class RawHit:
    title: str
    url: str
    snippet: str = ""
    thumbnail: Optional[str] = None
    provider: str = ""
    query_platform: str = "web"
    position: int = 0  # place in the provider's own results; lower is better


# ------------------------------------------------------------------ URLs
def _host(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def classify_url(url: str) -> Optional[tuple[str, str]]:
    """Return (platform_key, handle) for a real profile page, ('web','') for ordinary
    websites, or None when the URL is a social-media page that is NOT a profile."""
    if not url.lower().startswith(("http://", "https://")):
        return None
    for key, pat in _PROFILE_PATTERNS.items():
        m = pat.match(url)
        if m:
            handle = m.group(1)
            low = handle.lower()
            if key == "instagram" and low in _IG_RESERVED:
                return None
            if key == "facebook":
                if low in _FB_RESERVED:
                    return None
            if key == "x" and low in _X_RESERVED:
                return None
            if key == "github" and low in _GITHUB_RESERVED:
                return None
            if key == "pinterest" and low in _PINTEREST_RESERVED:
                return None
            return key, handle.lstrip("@")
    host = _host(url)
    if any(host == d or host.endswith("." + d) for d in _SOCIAL_DOMAINS):
        if "facebook.com/profile.php" in url.lower():
            return "facebook", "profile.php"
        return None
    return "web", ""


def canonical(url: str) -> str:
    try:
        p = urlparse(url)
    except ValueError:
        return url
    host = (p.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    return f"{host}{p.path.rstrip('/').lower()}"


# ------------------------------------------------------------------ names
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def _expand_initials(a: list[str], b: list[str]) -> list[str]:
    used: set[int] = set()
    out = []
    for tok in a:
        if len(tok) == 1:
            for i, other in enumerate(b):
                if i not in used and len(other) > 1 and other.startswith(tok):
                    used.add(i)
                    tok = other
                    break
        out.append(tok)
    return out


def name_similarity(query: str, candidate: str) -> float:
    q, c = normalize(query), normalize(candidate)
    if not q or not c:
        return 0.0
    qt, ct = q.split(), c.split()
    qt2, ct2 = _expand_initials(qt, ct), _expand_initials(ct, qt)
    q2, c2 = " ".join(qt2), " ".join(ct2)
    sort = fuzz.token_sort_ratio(q2, c2)
    tset = fuzz.token_set_ratio(q2, c2)
    return round((0.65 * sort + 0.35 * tset) / 100, 4)


def title_to_name(title: str) -> str:
    t = re.split(r"\s[-–—|•·/]\s|\s\(@|\s\|", title or "")[0]
    t = re.sub(r"\b(?:on|@)\s*(?:Instagram|Facebook|TikTok|X|Twitter|LinkedIn)\b.*$", "", t, flags=re.I)
    named = re.fullmatch(r"[\w.\-]+ \(([^)]{2,60})\)", t.strip())  # "octocat (The Octocat)" -> the real name
    if named:
        t = named.group(1)
    return t.strip(" .,:")


def handle_to_name(platform: str, handle: str) -> str:
    if not handle or handle == "profile.php":
        return ""
    if platform == "youtube":
        if handle.startswith(("channel/", "UC")):
            return ""  # an id, not a name
        handle = handle.split("/")[-1]
    if platform == "linkedin":
        parts = [p for p in handle.split("-") if not (re.fullmatch(r"[0-9a-f]{6,}", p) or p.isdigit())]
        return " ".join(parts)
    return re.sub(r"[._-]+", " ", handle)


def score_hit(hit: RawHit, platform: str, handle: str, name: str, location: Optional[str]) -> float:
    title_score = name_similarity(name, title_to_name(hit.title))
    handle_score = 0.85 * name_similarity(name, handle_to_name(platform, handle)) if handle else 0.0
    score = max(title_score, handle_score)
    if location and score > 0:
        location_text = normalize(location)
        searchable = normalize(f"{hit.title} {hit.snippet}")
        if location_text and location_text in searchable:
            score = min(1.0, score + 0.1)
    return round(score, 4)


def label_for(score: float) -> str:
    if score >= STRONG:
        return "strong_match"
    if score >= POSSIBLE:
        return "possible_match"
    return "weak_match"


def profile_key(url: str) -> Optional[str]:
    """Same profile = same key, whichever country site or URL spelling it came from."""
    cls = classify_url(url)
    if cls is None:
        return None
    platform, handle = cls
    return f"{platform}:{handle.lower()}" if handle else canonical(url)


def relevant_count(hits: list[RawHit], name: str, location: Optional[str] = None, platform: Optional[str] = None) -> int:
    """How many different profiles of `platform` (any platform when None/'web') look like a real match.
    Used to decide whether fetching one more page of results is worth a request."""
    found: set[str] = set()
    for hit in hits:
        cls = classify_url(hit.url)
        if cls is None or (platform not in (None, "web") and cls[0] != platform):
            continue
        if score_hit(hit, cls[0], cls[1], name, location) >= POSSIBLE:
            found.add(profile_key(hit.url) or hit.url)
    return len(found)


# ------------------------------------------------------------------ main
def rank(hits: list[RawHit], name: str, location: Optional[str] = None, limit: int = 5, per_platform: int = 5) -> list[Result]:
    seen: dict[str, Result] = {}
    best_position: dict[str, int] = {}
    for hit in hits:
        cls = classify_url(hit.url)
        if cls is None:
            continue
        platform, handle = cls
        score = score_hit(hit, platform, handle, name, location)
        if score < MIN_SCORE:
            continue
        key = profile_key(hit.url) or canonical(hit.url)
        display = title_to_name(hit.title) or handle_to_name(platform, handle) or name
        res = Result(
            name=display[:90],
            platform=PLATFORM_NAMES.get(platform, "Web"),
            platform_key=platform,
            title=(hit.title or display)[:160],
            description=(hit.snippet or "")[:280],
            profile_url=hit.url,
            image_url=hit.thumbnail if (hit.thumbnail or "").startswith("https://") else None,
            match_label=label_for(score),
            match_score=score,
            source=hit.provider,
        )
        best_position[key] = min(hit.position, best_position.get(key, hit.position))
        current = seen.get(key)
        if current is None:
            seen[key] = res
            continue
        # The same profile found twice (e.g. a web result and an image result): keep the better
        # name match but never lose the picture or the description the other copy had.
        keep, other = (res, current) if res.match_score > current.match_score else (current, res)
        keep.image_url = keep.image_url or other.image_url
        keep.description = keep.description or other.description
        seen[key] = keep

    by_key = {id(r): best_position.get(k, 0) for k, r in seen.items()}
    ordered = sorted(seen.values(), key=lambda r: (-r.match_score, by_key[id(r)]))
    picked: list[Result] = []
    taken: dict[str, int] = {}
    for r in ordered:  # the best few of each platform first (diversity), so one platform cannot crowd out the rest
        if taken.get(r.platform_key, 0) < per_platform and len(picked) < limit:
            picked.append(r)
            taken[r.platform_key] = taken.get(r.platform_key, 0) + 1
    chosen = {id(r) for r in picked}
    for r in ordered:
        if len(picked) >= limit:
            break
        if id(r) not in chosen:
            picked.append(r)
    return sorted(picked, key=lambda r: (-r.match_score, by_key[id(r)]))
