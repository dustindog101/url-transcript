"""URL detection and validation for supported platforms."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs, urlunparse


class UnsupportedURLError(ValueError):
    """Raised when the URL is not a supported TikTok / YouTube / Instagram link."""


@dataclass(frozen=True)
class ParsedURL:
    original: str
    normalized: str
    platform: str  # youtube | tiktok | instagram
    video_id: str | None = None


_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
_TT_HOSTS = {"tiktok.com", "www.tiktok.com", "vm.tiktok.com", "m.tiktok.com"}
_IG_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}


def _host(netloc: str) -> str:
    h = netloc.lower().split("@")[-1]
    if h.startswith("www."):
        # keep www. for membership checks that include both
        pass
    return h


def detect_platform(url: str) -> str:
    """Return platform name or raise UnsupportedURLError."""
    raw = url.strip()
    if not raw:
        raise UnsupportedURLError("Empty URL")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = _host(parsed.netloc)
    # strip port
    host = host.split(":")[0]

    if host in _YT_HOSTS or host.endswith(".youtube.com"):
        return "youtube"
    if host in _TT_HOSTS or host.endswith(".tiktok.com"):
        return "tiktok"
    if host in _IG_HOSTS or host.endswith(".instagram.com"):
        return "instagram"
    raise UnsupportedURLError(
        f"Unsupported host '{host}'. v1 supports TikTok, YouTube, and Instagram only."
    )


def _youtube_id(parsed) -> str | None:
    host = _host(parsed.netloc).split(":")[0]
    path = parsed.path or ""
    if host in {"youtu.be", "www.youtu.be"}:
        return path.strip("/").split("/")[0] or None
    if "/shorts/" in path:
        return path.split("/shorts/")[1].split("/")[0].split("?")[0] or None
    if "/embed/" in path:
        return path.split("/embed/")[1].split("/")[0] or None
    qs = parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        return qs["v"][0]
    return None


def _tiktok_id(parsed) -> str | None:
    m = re.search(r"/video/(\d+)", parsed.path or "")
    return m.group(1) if m else None


def _instagram_id(parsed) -> str | None:
    m = re.search(r"/(reel|reels|p|tv)/([^/?#]+)", parsed.path or "")
    return m.group(2) if m else None


def parse_url(url: str) -> ParsedURL:
    """Validate and normalize a media URL."""
    raw = url.strip()
    if not raw:
        raise UnsupportedURLError("Empty URL")
    if "://" not in raw:
        raw = "https://" + raw

    platform = detect_platform(raw)
    parsed = urlparse(raw)

    # Drop tracking noise from query for normalized form (keep essential ids)
    if platform == "youtube":
        vid = _youtube_id(parsed)
        if not vid:
            raise UnsupportedURLError("Could not extract YouTube video id from URL")
        normalized = f"https://www.youtube.com/watch?v={vid}"
        return ParsedURL(original=url.strip(), normalized=normalized, platform=platform, video_id=vid)

    if platform == "tiktok":
        vid = _tiktok_id(parsed)
        # Keep original path for vm.tiktok short links (yt-dlp resolves redirects)
        host = _host(parsed.netloc).split(":")[0]
        if host.startswith("vm."):
            normalized = urlunparse(("https", host, parsed.path, "", "", ""))
        elif vid:
            # preserve username path if present
            normalized = urlunparse(("https", "www.tiktok.com", parsed.path, "", "", ""))
        else:
            normalized = urlunparse(("https", "www.tiktok.com", parsed.path, "", parsed.query, ""))
        return ParsedURL(original=url.strip(), normalized=normalized, platform=platform, video_id=vid)

    # instagram
    vid = _instagram_id(parsed)
    if not vid:
        raise UnsupportedURLError(
            "Could not extract Instagram media id. Expected /reel/, /reels/, /p/, or /tv/ URL."
        )
    kind = "reel"
    m = re.search(r"/(reel|reels|p|tv)/", parsed.path or "")
    if m:
        kind = "reel" if m.group(1) in {"reel", "reels"} else m.group(1)
    path = f"/{'reels' if kind == 'reel' else kind}/{vid}/"
    normalized = f"https://www.instagram.com{path}"
    return ParsedURL(original=url.strip(), normalized=normalized, platform=platform, video_id=vid)
