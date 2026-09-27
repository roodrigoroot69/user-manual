#!/usr/bin/env python3
"""Posiciones exactas de elementos en una app Android nativa (o React Native) vía adb.

Usa `uiautomator dump`, que da los límites de cada elemento en px físicos:
los mismos px que `adb exec-out screencap -p`. Así el modo manual no tiene
que estimar coordenadas.

Uso (con el dispositivo en la pantalla a capturar):
    python android_bounds.py "Guardar" "id/btnGuardar" "desc:Buscar"
Imprime JSON listo para pegar en "resaltar". Criterios: texto visible exacto,
"id/<resource-id>" o "desc:<content-desc>".
"""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def dump():
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/manual-ui.xml"],
                   check=True, capture_output=True)
    xml = subprocess.run(["adb", "exec-out", "cat", "/sdcard/manual-ui.xml"],
                         check=True, capture_output=True).stdout
    return ET.fromstring(xml)


def coincide(nodo, criterio):
    if criterio.startswith("id/"):
        return nodo.get("resource-id", "").endswith(":" + criterio) or \
            nodo.get("resource-id", "") == criterio[3:]
    if criterio.startswith("desc:"):
        return nodo.get("content-desc") == criterio[5:]
    return nodo.get("text") == criterio


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    raiz = dump()
    salida = []
    for i, criterio in enumerate(sys.argv[1:], start=1):
        nodo = next((n for n in raiz.iter("node") if coincide(n, criterio)), None)
        if nodo is None:
            print(f"⚠ no se encontró: {criterio}", file=sys.stderr)
            continue
        x1, y1, x2, y2 = map(int, BOUNDS.match(nodo.get("bounds")).groups())
        salida.append({"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1, "etiqueta": str(i)})
    print(json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    main()
