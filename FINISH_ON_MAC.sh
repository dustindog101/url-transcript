#!/usr/bin/env bash
# Parent: after CopyFromBox of the project (or tar extract) to
#   /Users/king/Desktop/school files/tools/url-transcript/
# run this ON the Mac (Shell machineId a3c2a22a-00dc-4cc2-8adf-26657de9a0d5).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==== bootstrap FluidAudio + install ===="
./bootstrap-mac.sh

export PATH="$HOME/.local/bin:$PATH"
if [[ -x "$HOME/Developer/FluidAudio/.build/release/fluidaudiocli" ]]; then
  export FLUIDAUDIO_BIN="$HOME/Developer/FluidAudio/.build/release/fluidaudiocli"
elif [[ -x "$HOME/Developer/FluidAudio/.build/release/fluidaudio" ]]; then
  export FLUIDAUDIO_BIN="$HOME/Developer/FluidAudio/.build/release/fluidaudio"
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
  out=$(ut "$@" 2>"$ROOT/.smoke-err.txt")
  code=$?
  set -e
  if [[ $code -eq 0 && -n "${out// }" ]]; then
    echo "PASS ($code) chars=${#out}" | tee -a "$SMOKE_LOG"
    echo "${out:0:200}" | tee -a "$SMOKE_LOG"
  else
    echo "FAIL ($code)" | tee -a "$SMOKE_LOG"
    tail -20 "$ROOT/.smoke-err.txt" | tee -a "$SMOKE_LOG"
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
