#!/usr/bin/env bash
# Build dist/user-manual.skill (zip) for uploading to claude.ai.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist && rm -f dist/user-manual.skill
zip -rq dist/user-manual.skill user-manual -x "*/__pycache__/*" "*.DS_Store"
echo "✓ dist/user-manual.skill"
