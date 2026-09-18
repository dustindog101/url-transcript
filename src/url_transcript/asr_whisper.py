"""whisper.cpp fallback ASR."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from .asr_parakeet import AsrResult


class WhisperError(RuntimeError):
    """whisper.cpp transcription failed."""


def default_whisper_model() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "openscreen"
        / "stt-models"
        / "whisper-ggml"
        / "ggml-small-q8_0.bin"
    )


def resolve_whisper_cli() -> Path | None:
    env = os.environ.get("WHISPER_CLI")
    if env:
        p = Path(env).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return p
    for name in ("whisper-cli", "whisper-cpp", "whisper"):
        w = which(name)
        if w:
            return Path(w)
    # Homebrew locations
    for c in (
        Path("/opt/homebrew/bin/whisper-cli"),
        Path("/usr/local/bin/whisper-cli"),
    ):
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def model_present() -> bool:
    p = Path(os.environ.get("WHISPER_MODEL", default_whisper_model()))
    return p.is_file() and p.stat().st_size > 1024


def transcribe(
    audio_path: Path,
    *,
    timeout: int = 900,
) -> AsrResult:
    binary = resolve_whisper_cli()
    if binary is None:
        raise WhisperError(
            "whisper-cli not found. Install with: brew install whisper-cpp\n"
            "Or set WHISPER_CLI to the binary path."
        )
    model = Path(os.environ.get("WHISPER_MODEL", default_whisper_model()))
    if not model.is_file():
        raise WhisperError(
            f"Whisper model not found at {model}. "
            "Place ggml-small-q8_0.bin there or set WHISPER_MODEL."
        )

    # whisper-cli typical: whisper-cli -m model -f audio -nt (no timestamps)
    cmd = [str(binary), "-m", str(model), "-f", str(audio_path), "-nt", "-np"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise WhisperError(f"whisper-cli timed out after {timeout}s") from e
    except OSError as e:
        raise WhisperError(f"Failed to run whisper-cli: {e}") from e

    text = (proc.stdout or "").strip()
    if not text:
        # some builds print to stderr
        text = (proc.stderr or "").strip()
    # Drop common banner lines
    cleaned_lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("whisper_") or s.startswith("ggml_") or s.lower().startswith("system_info"):
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines).strip()

    if proc.returncode != 0 and not text:
        raise WhisperError(
            f"whisper-cli failed (exit {proc.returncode}):\n{(proc.stderr or proc.stdout or '')[-2000:]}"
        )
    if not text:
        raise WhisperError("whisper-cli returned empty transcript")

    return AsrResult(text=text, engine="whisper", model_version="ggml-small-q8_0", binary=str(binary))
