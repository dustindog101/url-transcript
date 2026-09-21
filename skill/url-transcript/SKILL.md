---
name: url-transcript
description: >-
  Use when the user sends a TikTok/YouTube/Instagram URL, asks to transcribe it,
  or asks what a short video is promoting / how BS the tools or claims are — run
  Mac `ut` first, then a visual pass if the transcript is thin or they want
  analysis.
---
# URL → Transcript + short-video intel (`ut`)

Turn a **TikTok / YouTube / Instagram** URL into a clean spoken transcript using the local Mac CLI **`ut`** (`url-transcript`). Prefer this over `youtube-transcript-api` or ad-hoc Whisper scripts.

Also use this skill when the user drops a short-video link and asks what it is, what tools it promotes, or how trustworthy / "BS" the claims are — not only when they say "transcribe."

## Hard rules

1. **Run `ut` on the user's Mac only** — project and binaries live there. Never invent a transcript; never pretend cloud ASR ran.
2. **Default for pure transcript asks:** clean transcript text. Progress stays on stderr (`ut` already does this).
3. **Do not touch Codex** or unrelated agent skill trees when installing or updating this skill.
4. Prefer **`ut`** for TikTok / YouTube / Instagram audio.
5. **On-screen text matters.** Many TikToks put the real list on screen while music buries speech. If the ask needs tools/claims/judgment and the transcript is thin, you must also inspect the video frames (download → watch/describe), then answer from spoken + visual evidence. Never fabricate product names.

## Install location (Mac)

```
/Users/king/Desktop/school files/tools/url-transcript/
```

Repo: https://github.com/dustindog101/url-transcript

Wrappers: `~/.local/bin/ut` and `~/.local/bin/url-transcript` (venv-backed).

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
```

## When to trigger

- TikTok, YouTube, Shorts, or Instagram Reel/post URL in the message.
- Transcribe / caption / "what's this saying" / `ut` / `url-transcript`.
- **Also:** "tell me about this," "what tools," "how BS," "is this legit," "review this," "what's the pitch" for those URLs.

### When NOT to use

- Non-video links — normal fetch/read.
- Local media files — `ut` is URL-only; use `whisper-cli` (or say so).
- Metadata-only asks (title/thumbnail) with no need for speech or on-screen content.

## Decision tree

```
Short-video URL?
├─ Want spoken words only → ut (--json preferred for agents)
├─ Want "about / tools / BS / review" → ut --json, THEN visual pass if needed
├─ Local file → whisper-cli / watch file; do not fake a URL
└─ Other → not this skill
```

### When a visual pass is required

Do a visual pass if **any** of these:

- User asked about tools, products, legitimacy, ads, or "how BS."
- `ut --json` duration is roughly **≥25s** but transcript is **very short** (outro-only, music-only, or under ~2–3 sentences).
- Title/description mentions a list ("10 websites," "tools," etc.) but transcript does not name them.

### Visual pass (Mac → work copy)

1. Download with yt-dlp into an **allowed** Mac path (e.g. under `Desktop/school files/`), not `/tmp` (local-exec may block `/tmp`).
2. Copy that file onto the assistant computer if needed, then **watch/describe the video** for on-screen names, URLs, and claims.
3. Merge: spoken transcript + on-screen list. Prefer on-screen spelling for product names.
4. Delete temp downloads when done unless the user asked to keep them.

## Commands

### Health check

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
ut doctor
```

Expect **Status: READY**. FluidAudio/Parakeet may be optional FAIL; whisper.cpp is valid.

### Transcribe

```bash
ut "URL"
ut "URL" --json
ut --engine whisper "URL"
```

Instagram cookies: `--cookies-from-browser firefox` (then `chrome` if needed).

Save only if asked: `ut "URL" --save` or `-o path`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Bad / unsupported URL |
| 3 | Download failed |
| 4 | ASR failed |
| 5 | Missing deps |

On failure: `ut doctor`, fix once, never invent spoken text.

## Engines

| Priority | Engine | Notes |
|----------|--------|-------|
| 1 | FluidAudio Parakeet | When `fluidaudio` / `FLUIDAUDIO_BIN` exists |
| 2 | whisper.cpp | Auto WAV convert; current default if Parakeet CLI missing |

## Local storage

| What | Where |
|------|--------|
| Temp audio | `~/Library/Caches/url-transcript/` |
| Whisper model | `~/Library/Application Support/openscreen/stt-models/whisper-ggml/` |
| Parakeet models | `~/Library/Application Support/FluidAudio/Models/` |
| Optional saved transcript | `./transcripts/` or `-o` |

Network: yt-dlp download. ASR: local.

## Response shape

**Transcript-only ask:** lead with transcript; optional one-line platform + engine.

**About / tools / BS ask:**
1. What the video is (creator, format, sponsorship tags like `#manuspartner` if present).
2. Ordered tool/product list with real URLs when shown.
3. Straight BS/legit rating per tool (real product vs oversell).
4. Note if speech was thin and on-screen text carried the list.

## Do not

- Skip `ut` and invent dialogue.
- Answer "what tools" from a thin outro transcript alone when a visual pass is required.
- Upload audio to third-party ASR unless the user asks.
- Install into Codex or other excluded trees.
- Run the CLI on a machine without the Mac install/models.
