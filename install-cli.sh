#!/usr/bin/env bash
# Install url-transcript editable + ensure ~/.local/bin links for ut / url-transcript.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: python3 not found" >&2
  exit 5
fi

echo ">> pip install -e ." >&2
"$PYTHON" -m pip install -e . --user --quiet 2>/dev/null || "$PYTHON" -m pip install -e . --quiet

BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

SCRIPTS_DIR="$("$PYTHON" -c "import sysconfig; print(sysconfig.get_path('scripts'))")"

for name in ut url-transcript; do
  src=""
  if [[ -x "${SCRIPTS_DIR}/${name}" ]]; then
    src="${SCRIPTS_DIR}/${name}"
  elif [[ -x "${BIN_DIR}/${name}" ]]; then
    src="${BIN_DIR}/${name}"
  fi
  if [[ -n "$src" ]]; then
    if [[ "$src" != "${BIN_DIR}/${name}" ]]; then
      ln -sfn "$src" "${BIN_DIR}/${name}"
      echo ">> linked ${BIN_DIR}/${name} -> ${src}" >&2
    else
      echo ">> already at ${BIN_DIR}/${name}" >&2
    fi
  else
    echo ">> warning: ${name} not found under ${SCRIPTS_DIR}" >&2
  fi
done

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo ">> add to your shell profile:" >&2
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
    ;;
esac

echo ">> done. Try: ut doctor" >&2
