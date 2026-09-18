"""End-to-end URL → transcript orchestration."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import asr_parakeet, asr_whisper, captions, download
from .urls import ParsedURL, UnsupportedURLError, parse_url


@dataclass
class TranscriptResult:
    url: str
    platform: str
    title: str
    engine: str
    model_version: str
    transcript: str
    captions: dict | None = None
    audio_path: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


def _safe_filename(title: str, fallback: str = "transcript") -> str:
    safe = re.sub(r"[^\w\s.\-]+", "-", title, flags=re.UNICODE)
    safe = re.sub(r"\s+", " ", safe).strip(" .-")
    return (safe[:120] or fallback)


def _log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def run(
    url: str,
    *,
    engine: str = "auto",  # auto | parakeet | whisper
    model_version: str = "v3",
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    keep_audio: bool = False,
    want_captions: bool = False,
    verbose: bool = True,
) -> TranscriptResult:
    parsed = parse_url(url)
    _log(f">> platform: {parsed.platform}", verbose)
    _log(f">> downloading audio…", verbose)

    try:
        dl = download.download_audio(
            parsed,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
    except download.DownloadError:
        raise

    warnings = list(dl.warnings or [])
    if dl.used_cookies:
        warnings.append("Download used browser/file cookies")

    _log(f">> audio: {dl.audio_path}", verbose)

    caps = None
    if want_captions and parsed.platform == "youtube":
        _log(">> fetching native captions (enrichment)…", verbose)
        try:
            caps = captions.fetch_youtube_captions(
                parsed.normalized, download.cache_dir() / "captions" / (parsed.video_id or "yt")
            )
        except Exception as e:  # noqa: BLE001 — enrichment only
            warnings.append(f"captions enrichment failed: {e}")

    asr_result = None
    errors: list[str] = []

    prefer = engine
    if prefer == "auto":
        order = ["parakeet", "whisper"]
    elif prefer == "parakeet":
        order = ["parakeet"]
    elif prefer == "whisper":
        order = ["whisper"]
    else:
        raise ValueError(f"Unknown engine: {engine}")

    for eng in order:
        try:
            if eng == "parakeet":
                _log(f">> ASR: FluidAudio Parakeet ({model_version})…", verbose)
                asr_result = asr_parakeet.transcribe(dl.audio_path, model_version=model_version)
            else:
                _log(">> ASR: whisper.cpp fallback…", verbose)
                asr_result = asr_whisper.transcribe(dl.audio_path)
            break
        except (asr_parakeet.ParakeetError, asr_whisper.WhisperError) as e:
            errors.append(f"{eng}: {e}")
            _log(f">> {eng} failed: {e}", verbose)
            continue

    if asr_result is None:
        raise asr_parakeet.ParakeetError(
            "All ASR engines failed:\n" + "\n---\n".join(errors)
        )

    audio_path_out = str(dl.audio_path) if keep_audio else None
    if not keep_audio:
        # Leave cache file (content-addressed reuse); user asked cleanup of temp —
        # we keep hashed cache but could unlink. Spec: "Temp audio in cache dir,
        # cleanup unless --keep-audio". Remove the downloaded file.
        try:
            dl.audio_path.unlink(missing_ok=True)
        except OSError:
            warnings.append(f"could not remove temp audio {dl.audio_path}")

    return TranscriptResult(
        url=parsed.normalized,
        platform=parsed.platform,
        title=dl.title,
        engine=asr_result.engine,
        model_version=asr_result.model_version,
        transcript=asr_result.text,
        captions=caps,
        audio_path=audio_path_out,
        warnings=warnings,
    )


def save_transcript(result: TranscriptResult, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.transcript + ("\n" if not result.transcript.endswith("\n") else ""), encoding="utf-8")
    return path


def default_save_path(result: TranscriptResult, directory: Path | None = None) -> Path:
    d = directory or Path("transcripts")
    name = _safe_filename(result.title, fallback=result.platform)
    return d / f"{name}.txt"
