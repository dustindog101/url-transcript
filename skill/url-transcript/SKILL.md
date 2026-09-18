---
name: url-transcript
description: >-
  Use when the user sends a TikTok, YouTube, YouTube Shorts, or Instagram
  Reel/post link; asks to transcribe, caption, or get the text/spoken words
  from a video; pastes a share URL that can be transcribed; or says ut /
  url-transcript / "what's this video saying". Prefer this over
  youtube-transcript-api or ad-hoc Whisper scripts for those platforms.
---

# URL → Transcript (`ut`)

Turn a **TikTok / YouTube / Instagram** URL into a clean spoken transcript using the local Mac CLI **`ut`** (`url-transcript`). Do this automatically when the user drops a supported link (or clearly asks for a transcript of one).

## Hard rules

1. **Run on the user's Mac only** — project and binaries live there. Never invent a transcript; never pretend cloud ASR ran.
2. **Default output:** clean transcript text the user can read. Progress belongs on stderr (`ut` already does this).
3. **Do not touch Codex** or unrelated agent skill trees when installing or updating this skill.
4. Prefer **`ut`** over `youtube-transcript-api`, browser copy-paste, or one-off Whisper Python scripts for TikTok / YouTube / Instagram.

## Install location (Mac)

```
/Users/king/Desktop/school files/tools/url-transcript/
```

Repo: https://github.com/dustindog101/url-transcript

Wrappers: `~/.local/bin/ut` and `~/.local/bin/url-transcript` (venv-backed).

Ensure PATH includes `~/.local/bin` before calling:

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
```

## When to trigger (do it)

- User message is (or contains) a TikTok, YouTube, Shorts, or Instagram Reel/post URL.
- User asks to transcribe / caption / "what are they saying" / "get the text" for such a link.
- User says `ut …` or `url-transcript …`.

### When NOT to use

- Non-video links (articles, docs, GitHub) — use normal fetch/read tools.
- Local audio/video **files** on disk — `ut` is URL-only today; use `whisper-cli` (or say so) instead of faking a URL.
- User only wants a title/thumbnail/metadata, not spoken text.

## Decision tree

```
Link or transcript ask?
├─ TikTok / YouTube / IG URL → run ut (below)
├─ Local media file → whisper-cli or ask; do not force ut
└─ Other → not this skill
```

## Commands

### Health check (first time in a session, or on failure)

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
ut doctor
```

Expect **Status: READY**. FluidAudio/Parakeet may show optional FAIL; whisper.cpp is a valid ready path.

### Transcribe (default)

```bash
ut "URL"
```

Stdout = transcript only. Show that to the user (summarize only if they asked for a summary).

### Instagram (cookies)

IG often needs browser cookies. Prefer Firefox:

```bash
ut "https://www.instagram.com/reels/XXXX/" --cookies-from-browser firefox
```

If Firefox fails, try `chrome`. Do not ask the user to paste cookie files unless both fail.

### Agent / structured

```bash
ut "URL" --json
```

### Force whisper (current default engine if Parakeet CLI not built)

```bash
ut --engine whisper "URL"
```

### Save to disk (only if user asks)

```bash
ut "URL" --save          # ./transcripts/
ut "URL" -o /path/out.txt
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Bad / unsupported URL |
| 3 | Download failed |
| 4 | ASR failed |
| 5 | Missing deps |

On non-zero: run `ut doctor`, read stderr, fix once (PATH, cookies, `--engine whisper`), then report the real error. Never fabricate spoken text.

## Engines

| Priority | Engine | Notes |
|----------|--------|-------|
| 1 | FluidAudio Parakeet | Primary when `fluidaudio` / `FLUIDAUDIO_BIN` exists |
| 2 | whisper.cpp | `brew` `whisper-cli` + local ggml model; auto WAV convert |

Until Parakeet CLI is built on this Mac, use `--engine whisper` or rely on auto-fallback.

## Local storage (what hits disk)

Yes — processing is **local on the Mac**, not a cloud transcription API.

| What | Where | Notes |
|------|--------|-------|
| Temp / cached audio | `~/Library/Caches/url-transcript/` | Content-hashed; deleted after ASR unless `--keep-audio` |
| Whisper model | `~/Library/Application Support/openscreen/stt-models/whisper-ggml/` | Already on disk |
| Parakeet models | `~/Library/Application Support/FluidAudio/Models/` | VoiceInk / FluidAudio cache |
| Optional saved transcript | `./transcripts/` or `-o` path | Only if user passes `--save` / `-o` |

Network use: **yt-dlp** downloads media from TikTok / YouTube / Instagram. ASR itself runs locally (whisper.cpp / Parakeet).

## Response shape

1. Run `ut` (Mac shell).
2. Lead with the transcript (or a short summary **only if asked**).
3. One line of provenance if useful: platform + engine (from `--json` or stderr).
4. If IG needed cookies, say so briefly.

## Do not

- Skip `ut` and invent dialogue.
- Upload the audio to a third-party ASR unless the user explicitly asks.
- Install this skill into Codex (`~/.codex/skills`) or other tools the user excluded.
- Run the CLI on a Linux box that lacks the Mac install / models.
