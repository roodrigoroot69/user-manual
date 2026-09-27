#!/usr/bin/env python3
"""Dibuja una cuadrícula con coordenadas sobre una captura (modo manual).

Sirve para ubicar con precisión los elementos a resaltar cuando no hay driver
que dé las posiciones. Las coordenadas son px de la imagen original.

Uso:
    python grid.py captura.png [--paso 50] [--zona x,y,ancho,alto] [--out /tmp/grid.png]

--zona amplía una región con una cuadrícula más fina para afinar coordenadas.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from annotate import load_font


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imagen")
    ap.add_argument("--paso", type=int, help="separación de líneas en px (auto si se omite)")
    ap.add_argument("--zona", help="x,y,ancho,alto a ampliar")
    ap.add_argument("--out")
    args = ap.parse_args()

    img = Image.open(args.imagen).convert("RGB")
    ox = oy = 0
    if args.zona:
        x, y, w, h = (int(v) for v in args.zona.split(","))
        img = img.crop((x, y, x + w, y + h))
        ox, oy = x, y

    # la vista previa se muestra reducida: escalar para que ~1200 px de ancho
    factor = max(1.0, 1200 / img.width) if args.zona else min(1.0, 1600 / img.width)
    vista = img.resize((int(img.width * factor), int(img.height * factor)))
    objetivo = max(img.width, img.height) / 16
    paso = args.paso or min((10, 20, 25, 50, 100, 200, 250, 500), key=lambda v: abs(v - objetivo))

    d = ImageDraw.Draw(vista, "RGBA")
    font = load_font(18)
    for gx in range(0, img.width + 1, paso):
        X = int(gx * factor)
        mayor = (gx + ox) % (paso * 2) == 0
        d.line([(X, 0), (X, vista.height)], fill=(255, 0, 80, 150 if mayor else 70), width=1)
        if mayor:
            d.text((X + 2, 2), str(gx + ox), fill=(255, 0, 80, 255), font=font,
                   stroke_width=2, stroke_fill="white")
    for gy in range(0, img.height + 1, paso):
        Y = int(gy * factor)
        mayor = (gy + oy) % (paso * 2) == 0
        d.line([(0, Y), (vista.width, Y)], fill=(0, 110, 255, 150 if mayor else 70), width=1)
        if mayor:
            d.text((2, Y + 2), str(gy + oy), fill=(0, 110, 255, 255), font=font,
                   stroke_width=2, stroke_fill="white")

    out = Path(args.out or f"/tmp/grid-{Path(args.imagen).stem}.png")
    vista.save(out)
    print(f"{out}  (imagen {Image.open(args.imagen).size[0]}x{Image.open(args.imagen).size[1]} px,"
          f" paso {paso} px; etiquetas cada {paso * 2} px)")


if __name__ == "__main__":
    main()
