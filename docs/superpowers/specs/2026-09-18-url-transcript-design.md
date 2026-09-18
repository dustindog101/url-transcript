# url-transcript Design Spec

**Date:** 2026-09-18  
**Status:** Locked for v1  
**Repo:** dustindog101/url-transcript

## Problem

Need a resilient CLI that turns TikTok / YouTube / Instagram URLs into clean spoken transcripts on Apple Silicon, using FluidAudio Parakeet (ANE) as primary ASR and whisper.cpp as fallback. Inspired by spookyuser/yt-transcribe (bash + fluidaudiocli) but multi-platform, agent-friendly, and failure-tolerant.

## Goals (v1)

- Platforms: TikTok, YouTube, Instagram (Reels / posts with video)
- ASR: FluidAudio Parakeet primary (`parakeet-tdt-0.6b-v3` default); whisper.cpp fallback
- Default output: clean transcript text on **stdout only** (progress on stderr)
- Optional persistence: `--save` → `./transcripts/`, or `-o PATH`
- `--json` structured payload for agents
- Console aliases: `ut` and `url-transcript`
- `doctor` subcommand for dependency health
- Exit codes: `0` ok, `2` bad URL, `3` download fail, `4` ASR fail, `5` deps missing

## Non-goals (v1)

- Captions-only mode as default (native YouTube captions may appear in JSON `captions` as enrichment only)
- Batch playlist transcription
- Diarization / word timestamps as default
- Windows / Linux ASR (Parakeet CoreML is macOS-only; whisper fallback may work elsewhere but unsupported)

## Architecture

```
URL → urls.detect → download (yt-dlp + retries)
                 → captions (optional YT enrichment for --json)
                 → asr_parakeet (primary) | asr_whisper (fallback)
                 → stdout text | --json | --save / -o
```

### Modules

| Module | Responsibility |
|--------|----------------|
| `cli` | argparse, routing, exit codes, stderr progress |
| `urls` | platform detection, URL normalization, validation |
| `download` | yt-dlp audio extract, retries/backoff, cookies retry |
| `captions` | optional YouTube auto/manual captions for JSON enrichment |
| `asr_parakeet` | FluidAudio CLI wrapper (`fluidaudio` / `fluidaudiocli`) |
| `asr_whisper` | whisper-cli / whisper.cpp wrapper |
| `pipeline` | orchestration, temp audio lifecycle, engine selection |
| `doctor` | dependency probe + actionable fix hints |

### Audio cache

- Temp audio under `~/Library/Caches/url-transcript/` (macOS) or `$XDG_CACHE_HOME/url-transcript`
- Content-addressed by URL hash (reuse downloads)
- Cleanup after success unless `--keep-audio`

### Cookies (Instagram fragility)

1. Try download **without** cookies
2. On auth / empty / login-wall errors, retry with `--cookies-from-browser` (Firefox preferred; Chrome cookie DB often broken on modern macOS)
3. Support `--cookies FILE` and `--cookies-from-browser BROWSER`
4. Document IG challenge pages and cookie requirements clearly; never invent transcripts

### TikTok / YouTube

- Keep yt-dlp updated; optional cookies
- Clear stderr errors on TikTok challenge pages
- YouTube: ASR is primary; native captions optional in JSON `captions` field only

### FluidAudio

- Build from https://github.com/FluidInference/FluidAudio.git → `~/Developer/FluidAudio` or project `.deps/FluidAudio`
- Binary: `.build/release/fluidaudio` or `fluidaudiocli`
- Override: `FLUIDAUDIO_BIN`
- Models reuse Application Support cache (same path VoiceInk uses):  
  `~/Library/Application Support/FluidAudio/Models/parakeet-tdt-0.6b-v3`
- Default `--model-version v3`; `--engine parakeet|whisper` and `--model-version v2|v3` overrides

### Whisper fallback

- Prefer `whisper-cli` if on PATH
- Model: `~/Library/Application Support/openscreen/stt-models/whisper-ggml/ggml-small-q8_0.bin`
- If missing CLI: `brew install whisper-cpp` (doctor / install hint)

## CLI surface

```bash
ut <url> [--json] [--save] [-o PATH] [--engine auto|parakeet|whisper]
         [--model-version v2|v3] [--cookies-from-browser firefox|chrome|…]
         [--cookies FILE] [--keep-audio] [--verbose]

ut doctor
```

## JSON schema (v1)

```json
{
  "url": "...",
  "platform": "youtube|tiktok|instagram",
  "title": "...",
  "engine": "parakeet|whisper",
  "model_version": "v3",
  "transcript": "...",
  "captions": null,
  "audio_path": null,
  "warnings": []
}
```

## Success criteria

- Public GitHub repo `dustindog101/url-transcript`
- `ut doctor` runs
- ≥1 YouTube Short or TikTok yields real Parakeet transcript
- Default stdout is clean transcript text only
