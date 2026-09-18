# url-transcript Implementation Plan

**Date:** 2026-09-18

## Steps

1. **Scaffold** Python 3.11+ package at project root with `pyproject.toml` console scripts `url-transcript` / `ut`.
2. **urls** — detect youtube / tiktok / instagram; reject unsupported; normalize shorts/reels.
3. **download** — yt-dlp bestaudio→m4a/wav; 3 retries with exponential backoff; cookie retry path for IG.
4. **captions** — best-effort YouTube subtitle pull for `--json` enrichment only.
5. **asr_parakeet** — resolve `FLUIDAUDIO_BIN` / known build paths; `transcribe FILE --model-version v3`.
6. **asr_whisper** — resolve whisper-cli + ggml model; run as fallback when Parakeet missing/fails.
7. **pipeline** — wire download→ASR→output; temp cleanup; engine=auto prefers Parakeet.
8. **doctor** — check ffmpeg, yt-dlp, FluidAudio bin+models, whisper-cli+model, cookies advice.
9. **cli** — argparse + exit codes; progress stderr; clean stdout.
10. **install-cli.sh** — `pip install -e .` + PATH hint/symlink for `~/.local/bin`.
11. **FluidAudio build** — clone to `~/Developer/FluidAudio` if needed; `swift build -c release`.
12. **GitHub** — MIT LICENSE, initial commit, `gh repo create dustindog101/url-transcript --public --source=. --remote=origin --push`.
13. **Verify** — `ut doctor`; smoke-test IG×2, TikTok×1, YT×2; report honestly.

## Smoke URLs

- https://www.instagram.com/reels/Dcr7BNSN2se/
- https://www.instagram.com/reels/Ddb2yZrxPyC/
- https://www.tiktok.com/@deujbds/video/7675641781211467021?is_from_webapp=1&sender_device=pc
- https://www.youtube.com/watch?v=l1kiTz-19iQ
- https://youtube.com/shorts/fVcAJTLCdaw?si=y56pc0a7mvByVxoF
