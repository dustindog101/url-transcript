#!/usr/bin/env bash
# Finish install + smoke + GitHub on the Mac.
# Env: SKIP_FLUIDAUDIO=1 to skip FluidAudio build (whisper-only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ "${SKIP_FLUIDAUDIO:-}" == "1" ]]; then
  echo "==== skip FluidAudio; whisper-only ===="
  if ! command -v whisper-cli >/dev/null 2>&1; then
    brew install whisper-cpp
  fi
  ./install-cli.sh
else
  echo "==== bootstrap FluidAudio + install ===="
  ./bootstrap-mac.sh
fi

export PATH="$HOME/.local/bin:$PATH"
if [[ -x "$HOME/Developer/FluidAudio/.build/release/fluidaudiocli" ]]; then
  export FLUIDAUDIO_BIN="$HOME/Developer/FluidAudio/.build/release/fluidaudiocli"
elif [[ -x "$HOME/Developer/FluidAudio/.build/release/fluidaudio" ]]; then
  export FLUIDAUDIO_BIN="$HOME/Developer/FluidAudio/.build/release/fluidaudio"
fi

ENGINE_ARGS=()
if [[ "${SKIP_FLUIDAUDIO:-}" == "1" ]]; then
  ENGINE_ARGS=(--engine whisper)
fi

echo "==== doctor ===="
ut doctor || true

echo "==== smoke tests ===="
SMOKE_LOG="$ROOT/smoke-results.txt"
: > "$SMOKE_LOG"

run_one() {
  local label="$1"; shift
  echo "--- $label ---" | tee -a "$SMOKE_LOG"
  set +e
  out=$(ut "${ENGINE_ARGS[@]}" -q "$@" 2>"$ROOT/.smoke-err.txt")
  code=$?
  set -e
  # reject ggml/backend noise pretending to be a transcript
  if [[ $code -eq 0 && -n "${out// }" ]] && ! echo "$out" | grep -q '^load_backend:'; then
    echo "PASS ($code) chars=${#out}" | tee -a "$SMOKE_LOG"
    echo "${out:0:200}" | tee -a "$SMOKE_LOG"
  else
    echo "FAIL ($code)" | tee -a "$SMOKE_LOG"
    tail -20 "$ROOT/.smoke-err.txt" | tee -a "$SMOKE_LOG"
    echo "stdout head: ${out:0:120}" | tee -a "$SMOKE_LOG"
  fi
}

run_one "YT-watch" "https://www.youtube.com/watch?v=l1kiTz-19iQ"
run_one "YT-short" "https://youtube.com/shorts/fVcAJTLCdaw?si=y56pc0a7mvByVxoF"
run_one "TikTok" "https://www.tiktok.com/@deujbds/video/7675641781211467021?is_from_webapp=1&sender_device=pc"
run_one "IG-1" "https://www.instagram.com/reels/Dcr7BNSN2se/" --cookies-from-browser firefox
run_one "IG-2" "https://www.instagram.com/reels/Ddb2yZrxPyC/" --cookies-from-browser firefox

echo "==== GitHub ===="
if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create dustindog101/url-transcript --public --source=. --remote=origin --push \
    || gh repo create dustindog101/url-transcript --private --source=. --remote=origin --push
else
  git push -u origin main
fi
gh repo view dustindog101/url-transcript --json url -q .url

echo "==== done; see smoke-results.txt ===="
