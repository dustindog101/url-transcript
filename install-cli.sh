#!/usr/bin/env bash
# Install url-transcript into a local .venv and link ut / url-transcript into ~/.local/bin.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: python3 not found" >&2
  exit 5
fi

if [[ ! -d .venv ]]; then
  echo ">> creating .venv" >&2
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo ">> pip install -e ." >&2
pip install -e . -q

BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

for name in ut url-transcript; do
  cat > "${BIN_DIR}/${name}" <<EOF
#!/usr/bin/env bash
exec "${ROOT}/.venv/bin/${name}" "\$@"
EOF
  chmod +x "${BIN_DIR}/${name}"
  echo ">> wrote ${BIN_DIR}/${name}" >&2
done

grep -q '^\.venv$' .gitignore 2>/dev/null || echo '.venv' >> .gitignore

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo ">> add to your shell profile:" >&2
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
    ;;
esac

echo ">> done. Try: ut doctor" >&2
