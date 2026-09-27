#!/usr/bin/env bash
# Try the web driver against the demo app.
#   pip install playwright pyyaml pillow python-docx && python -m playwright install chromium
set -euo pipefail
cd "$(dirname "$0")"
python3 -m http.server 8765 >/dev/null 2>&1 &
SERVER=$!; trap 'kill $SERVER' EXIT; sleep 1
rm -rf build
DEMO_URL=http://localhost:8765 MANUAL_USER=demo MANUAL_PASS=demo \
  python3 ../../user-manual/scripts/capture_web.py manual.yaml --out build
python3 ../../user-manual/scripts/build_manual.py manual.yaml --build build --pdf
