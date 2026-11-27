#!/usr/bin/env bash
# Dev-only: render examples/designs/login-dark/src/*.html to 780x1688 PNGs (390x844 at DPR 2)
# with headless Chrome, and copy the light frames from ../login. CHROME=/path/to/chrome overrides.
set -euo pipefail
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR="$ROOT/examples/designs/login-dark"
[[ -x "$CHROME" ]] || { echo "Chrome not found at: $CHROME (set CHROME=/path/to/chrome)" >&2; exit 1; }
PROFILE="$(mktemp -d)"; trap 'rm -rf "$PROFILE"' EXIT
for state in default error loading; do
  cp "$ROOT/examples/designs/login/login--$state.png" "$DIR/login--$state.png"
  out="$DIR/login--$state-dark.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$PROFILE" --no-first-run \
    --force-device-scale-factor=2 --virtual-time-budget=2000 --window-size=390,1000 \
    --screenshot="$out" "file://$DIR/src/$state.html" >/dev/null 2>&1
  python3 -I - "$out" <<'PY'
import sys
from PIL import Image
p = sys.argv[1]
Image.open(p).convert("RGB").crop((0, 0, 780, 1688)).save(p)
PY
  echo "wrote $out"
done
