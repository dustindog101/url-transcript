# url-transcript

Resilient **URL → transcript** CLI for **TikTok**, **YouTube**, and **Instagram**.

Primary ASR: [FluidAudio](https://github.com/FluidInference/FluidAudio) Parakeet (Apple Neural Engine).  
Fallback: whisper.cpp (`whisper-cli`).

Inspired by [spookyuser/yt-transcribe](https://github.com/spookyuser/yt-transcribe), extended for multi-platform downloads, optional save/JSON, cookie retries, and clearer errors.

## Requirements (macOS Apple Silicon)

- Python 3.11+
- `ffmpeg`, `yt-dlp` (Homebrew)
- FluidAudio CLI (`fluidaudio` / `fluidaudiocli`) + Parakeet models
- Optional: `whisper-cli` + ggml model for fallback

Parakeet models (already present if you use VoiceInk):

```
~/Library/Application Support/FluidAudio/Models/parakeet-tdt-0.6b-v3
```

Whisper fallback model (optional):

```
~/Library/Application Support/openscreen/stt-models/whisper-ggml/ggml-small-q8_0.bin
```

## Install

```bash
cd "/Users/king/Desktop/school files/tools/url-transcript"
./install-cli.sh
# or: pip install -e .
```

Aliases on PATH: `ut` and `url-transcript`.

### Build FluidAudio CLI (if missing)

```bash
git clone https://github.com/FluidInference/FluidAudio.git ~/Developer/FluidAudio
(cd ~/Developer/FluidAudio && swift build -c release)
# Binary: ~/Developer/FluidAudio/.build/release/fluidaudiocli  (or fluidaudio)
export FLUIDAUDIO_BIN="$HOME/Developer/FluidAudio/.build/release/fluidaudiocli"
```

## Doctor

```bash
ut doctor
```

## Usage

```bash
# Clean transcript on stdout only (progress on stderr)
ut "https://www.youtube.com/watch?v=l1kiTz-19iQ"

# YouTube Short
ut "https://youtube.com/shorts/fVcAJTLCdaw"

# TikTok
ut "https://www.tiktok.com/@user/video/123"

# Instagram Reel (cookies often required — Firefox preferred)
ut "https://www.instagram.com/reels/XXXX/" --cookies-from-browser firefox

# JSON for agents (includes optional YouTube captions enrichment)
ut "URL" --json

# Save to ./transcripts/ or custom path
ut "URL" --save
ut "URL" -o ./my-transcript.txt

# Engine / model overrides
ut "URL" --engine parakeet --model-version v3
ut "URL" --engine whisper
ut "URL" --model-version v2   # English-only Parakeet
```

## Instagram cookie notes (fragile)

Instagram frequently blocks anonymous downloads. Behavior:

1. Try **without** cookies first.
2. On auth / empty / login-wall errors, retry with `--cookies-from-browser` (Firefox → Chrome → …).
3. You can force: `--cookies-from-browser firefox` or `--cookies cookies.txt`.

**Prefer Firefox.** Chrome’s cookie DB encryption is often broken for yt-dlp on modern macOS.

If a challenge / login wall persists, the CLI exits with code `3` and does **not** invent a transcript.

## TikTok notes

Keep yt-dlp updated (`brew upgrade yt-dlp`). Challenge pages need cookies or a newer extractor.

## YouTube notes

Spoken ASR is the **primary** transcript for consistency across platforms. With `--json`, native captions may appear under `captions` as optional enrichment — not the default stdout text.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Bad / unsupported URL |
| 3 | Download failed |
| 4 | ASR failed |
| 5 | Required dependencies missing |

## Test URLs

```bash
ut "https://www.instagram.com/reels/Dcr7BNSN2se/" --cookies-from-browser firefox
ut "https://www.instagram.com/reels/Ddb2yZrxPyC/" --cookies-from-browser firefox
ut "https://www.tiktok.com/@deujbds/video/7675641781211467021?is_from_webapp=1&sender_device=pc"
ut "https://www.youtube.com/watch?v=l1kiTz-19iQ"
ut "https://youtube.com/shorts/fVcAJTLCdaw?si=y56pc0a7mvByVxoF"
```

## Env vars

| Var | Purpose |
|-----|---------|
| `FLUIDAUDIO_BIN` | Path to FluidAudio CLI binary |
| `WHISPER_CLI` | Path to whisper-cli |
| `WHISPER_MODEL` | Path to ggml model |
| `URL_TRANSCRIPT_CACHE` | Override audio cache directory |

## License

MIT
