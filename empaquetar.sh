#!/usr/bin/env bash
# Genera dist/manual-usuario.skill (zip) para subirla a claude.ai.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist && rm -f dist/manual-usuario.skill
zip -rq dist/manual-usuario.skill manual-usuario -x "*/__pycache__/*" "*.DS_Store"
echo "✓ dist/manual-usuario.skill"
