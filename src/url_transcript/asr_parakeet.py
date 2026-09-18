"""FluidAudio Parakeet ASR wrapper."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which


class ParakeetError(RuntimeError):
    """Parakeet / FluidAudio transcription failed."""


@dataclass
class AsrResult:
    text: str
    engine: str
    model_version: str
    binary: str


_CANDIDATE_BINS = (
    "FLUIDAUDIO_BIN",  # env handled separately
)


def default_model_dir(version: str = "v3") -> Path:
    # VoiceInk / FluidAudio shared cache
    base = Path.home() / "Library" / "Application Support" / "FluidAudio" / "Models"
    if version in {"v2", "2"}:
        return base / "parakeet-tdt-0.6b-v2"
    return base / "parakeet-tdt-0.6b-v3"


def resolve_fluidaudio_bin() -> Path | None:
    env = os.environ.get("FLUIDAUDIO_BIN")
    if env:
        p = Path(env).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return p

    # PATH names
    for name in ("fluidaudiocli", "fluidaudio"):
        w = which(name)
        if w:
            return Path(w)

    # Common build locations
    candidates = [
        Path.home() / "Developer" / "FluidAudio" / ".build" / "release" / "fluidaudiocli",
        Path.home() / "Developer" / "FluidAudio" / ".build" / "release" / "fluidaudio",
        Path(__file__).resolve().parents[2] / ".deps" / "FluidAudio" / ".build" / "release" / "fluidaudiocli",
        Path(__file__).resolve().parents[2] / ".deps" / "FluidAudio" / ".build" / "release" / "fluidaudio",
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def models_present(version: str = "v3") -> bool:
    d = default_model_dir(version)
    if not d.is_dir():
        return False
    # Any non-empty model bundle is enough for doctor
    try:
        return any(d.iterdir())
    except OSError:
        return False


def _clean_transcript(raw: str) -> str:
    """Strip FluidAudio CLI log noise; keep spoken text."""
    lines = raw.splitlines()
    keep: list[str] = []
    noise = re.compile(
        r"^(>>|Using batch|Streaming mode|Loading|Model|INFO|DEBUG|WARNING|"
        r"Transcription:|Confidence:|Processed|RTFx|Tokens)",
        re.I,
    )
    for line in lines:
        s = line.rstrip()
        if not s.strip():
            if keep and keep[-1] != "":
                keep.append("")
            continue
        if noise.match(s.strip()):
            # "Transcription: actual text" → keep the text after prefix
            m = re.match(r"^Transcription:\s*(.*)$", s.strip(), re.I)
            if m and m.group(1).strip():
                keep.append(m.group(1).strip())
            continue
        keep.append(s)
    text = "\n".join(keep).strip()
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def transcribe(
    audio_path: Path,
    *,
    model_version: str = "v3",
    extra_args: list[str] | None = None,
    timeout: int = 600,
) -> AsrResult:
    binary = resolve_fluidaudio_bin()
    if binary is None:
        raise ParakeetError(
            "FluidAudio CLI not found. Build with:\n"
            "  git clone https://github.com/FluidInference/FluidAudio.git ~/Developer/FluidAudio\n"
            "  (cd ~/Developer/FluidAudio && swift build -c release)\n"
            "Or set FLUIDAUDIO_BIN to the binary path."
        )

    ver = model_version if model_version.startswith("v") else f"v{model_version}"
    cmd = [str(binary), "transcribe", str(audio_path), "--model-version", ver]
    if extra_args:
        cmd.extend(extra_args)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ParakeetError(f"FluidAudio timed out after {timeout}s") from e
    except OSError as e:
        raise ParakeetError(f"Failed to run FluidAudio: {e}") from e

    raw = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    text = _clean_transcript(proc.stdout or "")
    if proc.returncode != 0 or not text.strip():
        # Sometimes transcript lands only on stderr
        text = _clean_transcript(raw)
    if proc.returncode != 0 and not text.strip():
        raise ParakeetError(
            f"FluidAudio failed (exit {proc.returncode}):\n{(proc.stderr or proc.stdout or '')[-2000:]}"
        )
    if not text.strip():
        raise ParakeetError("FluidAudio returned empty transcript")

    return AsrResult(text=text.strip(), engine="parakeet", model_version=ver, binary=str(binary))
