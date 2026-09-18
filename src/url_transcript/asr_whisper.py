"""whisper.cpp fallback ASR."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
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


_NOISE = re.compile(
    r"^(load_backend:|ggml_|whisper_|system_info|main:|error:|read_audio_data:|"
    r"output_txt:|whisper_init|log_mel|metal_|MTL0)",
    re.I,
)


def _clean_transcript(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if _NOISE.match(s):
            continue
        # whisper sometimes prefixes speaker turns with >>
        if s.startswith(">>"):
            s = s[2:].strip()
        lines.append(s)
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _to_wav16k(audio_path: Path) -> Path:
    """Convert any ffmpeg-readable audio to 16 kHz mono WAV for whisper-cli."""
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise WhisperError("ffmpeg not found (needed to convert audio for whisper-cli)")
    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="ut-whisper-")
    os.close(fd)
    out = Path(tmp)
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(audio_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size < 44:
        out.unlink(missing_ok=True)
        raise WhisperError(
            f"ffmpeg convert failed:\n{(proc.stderr or proc.stdout or '')[-1500:]}"
        )
    return out


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

    wav: Path | None = None
    out_base: Path | None = None
    try:
        wav = _to_wav16k(audio_path)
        fd, tmp_base = tempfile.mkstemp(prefix="ut-wout-")
        os.close(fd)
        out_base = Path(tmp_base)
        out_base.unlink(missing_ok=True)  # whisper adds .txt

        # -nt no timestamps, -np no prints (except results), -otxt write .txt
        cmd = [
            str(binary),
            "-m",
            str(model),
            "-f",
            str(wav),
            "-nt",
            "-np",
            "-otxt",
            "-of",
            str(out_base),
        ]
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

        txt_path = Path(str(out_base) + ".txt")
        raw = ""
        if txt_path.is_file():
            raw = txt_path.read_text(encoding="utf-8", errors="replace")
            txt_path.unlink(missing_ok=True)
        if not raw.strip():
            raw = (proc.stdout or "") + "\n" + (proc.stderr or "")

        text = _clean_transcript(raw)
        if proc.returncode != 0 and not text:
            raise WhisperError(
                f"whisper-cli failed (exit {proc.returncode}):\n"
                f"{(proc.stderr or proc.stdout or '')[-2000:]}"
            )
        if not text:
            raise WhisperError("whisper-cli returned empty transcript")

        return AsrResult(
            text=text,
            engine="whisper",
            model_version="ggml-small-q8_0",
            binary=str(binary),
        )
    finally:
        if wav is not None:
            wav.unlink(missing_ok=True)
        if out_base is not None:
            Path(str(out_base) + ".txt").unlink(missing_ok=True)
