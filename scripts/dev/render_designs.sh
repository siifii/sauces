#!/usr/bin/env bash
# Dev-only: render examples/designs/login/src/*.html to PNGs (780x1688) and a 3-page PDF
# with headless Chrome. Override the browser with CHROME=/path/to/chrome.
set -euo pipefail

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR="$ROOT/examples/designs/login"
SRC="$DIR/src"

if [[ ! -x "$CHROME" ]]; then
  echo "Chrome not found at: $CHROME (set CHROME=/path/to/chrome)" >&2
  exit 1
fi

# Pass a throwaway profile so a running Chrome does not swallow the command.
PROFILE="$(mktemp -d)"
trap 'rm -rf "$PROFILE"' EXIT
COMMON=(--headless=new --disable-gpu --hide-scrollbars --user-data-dir="$PROFILE" --no-first-run)

for state in default error loading; do
  out="$DIR/login--$state.png"
  "$CHROME" "${COMMON[@]}" --window-size=390,844 --force-device-scale-factor=2 \
    --screenshot="$out" "file://$SRC/$state.html" >/dev/null 2>&1
  # Headless windows can come out short (the viewport loses the window-chrome height).
  # If so, re-render with a taller window and crop to the exact canvas.
  size="$(python3 -I - "$out" <<'PY'
import struct, sys
with open(sys.argv[1], "rb") as f:
    d = f.read(24)
print(*struct.unpack(">II", d[16:24]))
PY
)"
  if [[ "$size" != "780 1688" ]]; then
    echo "viewport quirk: $state came out $size; re-rendering taller and cropping" >&2
    "$CHROME" "${COMMON[@]}" --window-size=390,1000 --force-device-scale-factor=2 \
      --screenshot="$out" "file://$SRC/$state.html" >/dev/null 2>&1
    python3 -I - "$out" <<'PY'
import sys
from PIL import Image
p = sys.argv[1]
im = Image.open(p)
im.crop((0, 0, 780, 1688)).save(p)
PY
  fi
  echo "wrote $out"
done

"$CHROME" "${COMMON[@]}" --no-pdf-header-footer --print-to-pdf="$DIR/login-flow.pdf" \
  "file://$SRC/flow.html" >/dev/null 2>&1
echo "wrote $DIR/login-flow.pdf"
