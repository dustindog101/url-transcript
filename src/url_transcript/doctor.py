"""Dependency health checks."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass

from . import asr_parakeet, asr_whisper, download


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def run_checks() -> list[Check]:
    checks: list[Check] = []

    # Python
    py = sys.version.split()[0]
    checks.append(Check("python", True, f"{py} ({sys.executable})", required=True))

    # ffmpeg
    ff = shutil.which("ffmpeg")
    checks.append(
        Check("ffmpeg", ff is not None, ff or "missing — brew install ffmpeg", required=True)
    )

    # yt-dlp
    yt = shutil.which("yt-dlp")
    checks.append(
        Check("yt-dlp", yt is not None, yt or "missing — brew install yt-dlp", required=True)
    )

    # FluidAudio binary
    fa = asr_parakeet.resolve_fluidaudio_bin()
    checks.append(
        Check(
            "fluidaudio",
            fa is not None,
            str(fa)
            if fa
            else "missing — clone FluidInference/FluidAudio && swift build -c release; or set FLUIDAUDIO_BIN",
            required=True,
        )
    )

    # Parakeet models v3
    m3 = asr_parakeet.models_present("v3")
    checks.append(
        Check(
            "parakeet-v3-models",
            m3,
            str(asr_parakeet.default_model_dir("v3"))
            if m3
            else f"missing at {asr_parakeet.default_model_dir('v3')} (VoiceInk / FluidAudio cache)",
            required=True,
        )
    )

    m2 = asr_parakeet.models_present("v2")
    checks.append(
        Check(
            "parakeet-v2-models",
            m2,
            str(asr_parakeet.default_model_dir("v2")) if m2 else "optional (English-only)",
            required=False,
        )
    )

    # whisper fallback
    wcli = asr_whisper.resolve_whisper_cli()
    checks.append(
        Check(
            "whisper-cli",
            wcli is not None,
            str(wcli) if wcli else "optional fallback — brew install whisper-cpp",
            required=False,
        )
    )
    wm = asr_whisper.model_present()
    checks.append(
        Check(
            "whisper-model",
            wm,
            str(asr_whisper.default_whisper_model())
            if wm
            else f"optional — expected {asr_whisper.default_whisper_model()}",
            required=False,
        )
    )

    # cache dir writable
    try:
        c = download.cache_dir()
        checks.append(Check("cache-dir", True, str(c), required=True))
    except OSError as e:
        checks.append(Check("cache-dir", False, str(e), required=True))

    # cookies tip
    checks.append(
        Check(
            "instagram-cookies",
            True,
            "IG often needs --cookies-from-browser firefox (Chrome encryption frequently broken)",
            required=False,
        )
    )

    env_bin = os.environ.get("FLUIDAUDIO_BIN")
    if env_bin:
        checks.append(Check("FLUIDAUDIO_BIN", True, env_bin, required=False))

    return checks


def format_report(checks: list[Check]) -> str:
    lines = ["url-transcript doctor", ""]
    for c in checks:
        mark = "OK  " if c.ok else "FAIL"
        req = "" if c.required else " (optional)"
        lines.append(f"  [{mark}] {c.name}{req}: {c.detail}")
    required_fail = [c for c in checks if c.required and not c.ok]
    lines.append("")
    if required_fail:
        lines.append(f"Status: NOT READY ({len(required_fail)} required check(s) failed)")
    else:
        lines.append("Status: READY")
    return "\n".join(lines)


def required_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks if c.required)
