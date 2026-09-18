#!/usr/bin/env bash
# Run ON the Mac after project lands at the target path.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

FLUID_DIR="${FLUIDAUDIO_DIR:-$HOME/Developer/FluidAudio}"
if [[ ! -x "$FLUID_DIR/.build/release/fluidaudiocli" && ! -x "$FLUID_DIR/.build/release/fluidaudio" ]]; then
  if [[ ! -d "$FLUID_DIR/.git" ]]; then
    mkdir -p "$(dirname "$FLUID_DIR")"
    git clone https://github.com/FluidInference/FluidAudio.git "$FLUID_DIR"
  fi
  echo ">> building FluidAudio release CLI…" >&2
  (cd "$FLUID_DIR" && swift build -c release)
fi

if [[ -x "$FLUID_DIR/.build/release/fluidaudiocli" ]]; then
  export FLUIDAUDIO_BIN="$FLUID_DIR/.build/release/fluidaudiocli"
elif [[ -x "$FLUID_DIR/.build/release/fluidaudio" ]]; then
  export FLUIDAUDIO_BIN="$FLUID_DIR/.build/release/fluidaudio"
fi
echo "FLUIDAUDIO_BIN=$FLUIDAUDIO_BIN" >&2

# whisper-cli optional
if ! command -v whisper-cli >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo ">> installing whisper-cpp via brew (optional fallback)…" >&2
    brew install whisper-cpp || true
  fi
fi

./install-cli.sh
export PATH="$HOME/.local/bin:$PATH"
ut doctor
