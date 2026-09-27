#!/usr/bin/env bash
# Prueba el driver JavaFX con la app de demo. Requiere JDK 17+ y el SDK de JavaFX.
#   FX=/ruta/a/javafx-sdk/lib ./correr.sh
set -euo pipefail
cd "$(dirname "$0")"
FX="${FX:?Define FX con la carpeta lib del SDK de JavaFX}"
SKILL=../../manual-usuario
rm -rf build out
cp "$SKILL/assets/javafx/ManualCapturador.java" src/manual/
javac --module-path "$FX" --add-modules javafx.controls -d out src/manual/*.java
java --module-path "$FX" --add-modules javafx.controls -cp out manual.Driver
python3 "$SKILL/scripts/annotate.py" build/crudas --out build
python3 "$SKILL/scripts/build_manual.py" manual.yaml --build build --pdf
