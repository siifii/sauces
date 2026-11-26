#!/usr/bin/env bash
# Dev-only: render examples/designs/login-web/src/*.html to 1440x900 PNGs (DPR 1) with
# headless Chrome, and copy the mobile PNGs as the @390 frames.
# Override the browser with CHROME=/path/to/chrome.
set -euo pipefail

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR="$ROOT/examples/designs/login-web"
SRC="$DIR/src"

if [[ ! -x "$CHROME" ]]; then
  echo "Chrome not found at: $CHROME (set CHROME=/path/to/chrome)" >&2
  exit 1
fi

PROFILE="$(mktemp -d)"
trap 'rm -rf "$PROFILE"' EXIT
COMMON=(--headless=new --disable-gpu --hide-scrollbars --user-data-dir="$PROFILE" --no-first-run
        --force-device-scale-factor=1 --virtual-time-budget=2000)

for state in default error loading; do
  cp "$ROOT/examples/designs/login/login--$state.png" "$DIR/login@390--$state.png"
  out="$DIR/login@1440--$state.png"
  # Render taller than the canvas, then crop: headless windows can lose the chrome height.
  "$CHROME" "${COMMON[@]}" --window-size=1440,1100 --screenshot="$out" \
    "file://$SRC/$state.html" >/dev/null 2>&1
  python3 -I - "$out" <<'PY'
import sys
from PIL import Image
p = sys.argv[1]
Image.open(p).convert("RGB").crop((0, 0, 1440, 900)).save(p)
PY
  echo "wrote $out"
done
