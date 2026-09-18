"""Optional native captions enrichment (YouTube) for --json only."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from shutil import which


def fetch_youtube_captions(url: str, dest_dir: Path) -> dict | None:
    """Best-effort pull of YouTube captions. Returns {lang, text, source} or None."""
    ytdlp = which("yt-dlp")
    if not ytdlp:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(dest_dir / "captions")
    # Prefer manual en, then auto
    cmd = [
        ytdlp,
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-langs",
        "en.*,en",
        "--sub-format",
        "vtt/srt/best",
        "--convert-subs",
        "srt",
        "-o",
        outtmpl,
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None

    # Find any produced subtitle
    candidates = sorted(dest_dir.glob("captions*.srt")) + sorted(dest_dir.glob("captions*.vtt"))
    if not candidates:
        return None
    path = candidates[0]
    try:
        text = _strip_sub_file(path)
    except OSError:
        return None
    if not text.strip():
        return None
    lang = "en"
    name = path.name
    if ".en" in name:
        lang = "en"
    source = "auto" if "auto" in name or path.suffix else "sub"
    return {"lang": lang, "text": text.strip(), "source": source, "path": str(path)}


def _strip_sub_file(path: Path) -> str:
    lines: list[str] = []
    raw = path.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.isdigit():
            continue
        if "-->" in s:
            continue
        if s.startswith("WEBVTT") or s.startswith("NOTE"):
            continue
        # drop simple tags
        s = s.replace("<c>", "").replace("</c>", "")
        lines.append(s)
    # de-dupe consecutive
    out: list[str] = []
    for ln in lines:
        if not out or out[-1] != ln:
            out.append(ln)
    return " ".join(out)
