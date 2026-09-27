#!/usr/bin/env bash
# Try the JavaFX capture helper against the demo app. Needs JDK 17+ and the JavaFX SDK.
#   FX=/path/to/javafx-sdk/lib ./run.sh
set -euo pipefail
cd "$(dirname "$0")"
FX="${FX:?Set FX to the JavaFX SDK lib folder}"
SKILL=../../user-manual
rm -rf build out
cp "$SKILL/assets/javafx/ManualCapturer.java" src/manual/
javac --module-path "$FX" --add-modules javafx.controls -d out src/manual/*.java
java --module-path "$FX" --add-modules javafx.controls -cp out manual.Driver
python3 "$SKILL/scripts/annotate.py" build/raw --out build
python3 "$SKILL/scripts/build_manual.py" manual.yaml --build build --pdf
