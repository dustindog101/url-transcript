"""Audio download via yt-dlp with retries and cookie fallback."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .urls import ParsedURL


class DownloadError(RuntimeError):
    """Audio download failed."""


@dataclass
class DownloadResult:
    audio_path: Path
    title: str
    url: str
    platform: str
    used_cookies: bool = False
    warnings: list[str] | None = None


_AUTH_HINTS = re.compile(
    r"(login|sign in|cookies?|authentication|403|401|private|challenge|"
    r"confirm you.?re a human|rate.?limit|empty file|no video|not available)",
    re.I,
)


def cache_dir() -> Path:
    override = os.environ.get("URL_TRANSCRIPT_CACHE")
    if override:
        p = Path(override).expanduser()
    elif Path.home().joinpath("Library/Caches").is_dir() or os.uname().sysname == "Darwin":
        p = Path.home() / "Library" / "Caches" / "url-transcript"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
        p = Path(xdg) / "url-transcript"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _slug(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)


def _run_yt_dlp(
    args: list[str],
    *,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def fetch_title(url: str) -> str:
    ytdlp = _which("yt-dlp")
    if not ytdlp:
        return "transcript"
    proc = _run_yt_dlp(
        [ytdlp, "--no-warnings", "--skip-download", "--print", "%(title)s", url],
        timeout=60,
    )
    title = (proc.stdout or "").strip().splitlines()
    return title[0] if title else "transcript"


def _cookie_args(
    cookies_from_browser: str | None,
    cookies_file: str | None,
) -> list[str]:
    if cookies_file:
        return ["--cookies", cookies_file]
    if cookies_from_browser:
        return ["--cookies-from-browser", cookies_from_browser]
    return []


def _looks_auth_failure(stderr: str, stdout: str, audio: Path) -> bool:
    blob = f"{stderr}\n{stdout}"
    if _AUTH_HINTS.search(blob):
        return True
    if not audio.exists() or audio.stat().st_size < 1024:
        return True
    return False


def download_audio(
    parsed: ParsedURL,
    *,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    retries: int = 3,
    backoff: float = 1.5,
    auto_cookie_retry: bool = True,
) -> DownloadResult:
    """Download best audio for URL into cache. Retries with backoff; IG cookie retry."""
    ytdlp = _which("yt-dlp")
    if not ytdlp:
        raise DownloadError("yt-dlp not found on PATH. Install via: brew install yt-dlp")

    ffmpeg = _which("ffmpeg")
    if not ffmpeg:
        raise DownloadError("ffmpeg not found on PATH. Install via: brew install ffmpeg")

    url = parsed.normalized
    out_base = cache_dir() / _slug(url)
    # yt-dlp will append extension; request m4a
    out_tmpl = str(out_base) + ".%(ext)s"
    expected = Path(str(out_base) + ".m4a")

    warnings: list[str] = []

    def attempt(cookie_args: list[str]) -> tuple[bool, str, str]:
        # Reuse existing cache if present and non-trivial
        for ext in (".m4a", ".webm", ".opus", ".mp3", ".wav", ".mp4"):
            cand = Path(str(out_base) + ext)
            if cand.exists() and cand.stat().st_size > 1024:
                return True, "", ""

        cmd = [
            ytdlp,
            "-f",
            "bestaudio[ext=m4a]/bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "m4a",
            "--no-playlist",
            "--no-warnings",
            "-o",
            out_tmpl,
            *cookie_args,
            url,
        ]
        last_err = ""
        last_out = ""
        for i in range(retries):
            proc = _run_yt_dlp(cmd)
            last_err = proc.stderr or ""
            last_out = proc.stdout or ""
            # Find produced file
            found = None
            for ext in (".m4a", ".webm", ".opus", ".mp3", ".wav", ".mp4"):
                cand = Path(str(out_base) + ext)
                if cand.exists() and cand.stat().st_size > 1024:
                    found = cand
                    break
            if found is not None and proc.returncode == 0:
                return True, last_out, last_err
            if i + 1 < retries:
                time.sleep(backoff * (2**i))
        return False, last_out, last_err

    # 1) Try with explicit cookies if provided, else without
    explicit = _cookie_args(cookies_from_browser, cookies_file)
    ok, out, err = attempt(explicit)
    used_cookies = bool(explicit)

    # 2) Auto cookie retry for IG (and auth-looking failures) if no cookies given
    if not ok and auto_cookie_retry and not explicit:
        if parsed.platform == "instagram" or _looks_auth_failure(err, out, expected):
            for browser in ("firefox", "chrome", "brave", "safari", "edge"):
                warnings.append(f"Retrying download with --cookies-from-browser {browser}")
                ok, out, err = attempt(["--cookies-from-browser", browser])
                if ok:
                    used_cookies = True
                    break

    if not ok:
        hint = ""
        if parsed.platform == "instagram":
            hint = (
                " Instagram often requires cookies. Try: "
                "`ut URL --cookies-from-browser firefox` "
                "or `--cookies cookies.txt`. Chrome cookie decryption is frequently broken on macOS."
            )
        if parsed.platform == "tiktok":
            hint = (
                " TikTok may show a challenge page. Update yt-dlp (`brew upgrade yt-dlp`) "
                "and/or pass cookies."
            )
        raise DownloadError(
            f"Failed to download audio from {url}.\n{(err or out).strip()[-2000:]}{hint}"
        )

    audio: Path | None = None
    for ext in (".m4a", ".webm", ".opus", ".mp3", ".wav", ".mp4"):
        cand = Path(str(out_base) + ext)
        if cand.exists() and cand.stat().st_size > 1024:
            audio = cand
            break
    if audio is None:
        raise DownloadError(f"Download appeared to succeed but no audio file at {out_base}.*")

    title = fetch_title(url)
    return DownloadResult(
        audio_path=audio,
        title=title,
        url=url,
        platform=parsed.platform,
        used_cookies=used_cookies,
        warnings=warnings or None,
    )
