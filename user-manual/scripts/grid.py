#!/usr/bin/env python3
"""Draw a coordinate grid over a screenshot (manual mode).

Helps locate elements precisely when no driver provides their positions.
Coordinates are px of the original image.

Usage:
    python grid.py screenshot.png [--step 50] [--zone x,y,width,height] [--out /tmp/grid.png]

--zone zooms into a region with a finer grid to refine coordinates.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from annotate import load_font


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--step", type=int, help="grid spacing in px (auto if omitted)")
    ap.add_argument("--zone", help="x,y,width,height to zoom into")
    ap.add_argument("--out")
    args = ap.parse_args()

    original = Image.open(args.image).convert("RGB")
    img, ox, oy = original, 0, 0
    if args.zone:
        x, y, w, h = (int(v) for v in args.zone.split(","))
        img = original.crop((x, y, x + w, y + h))
        ox, oy = x, y

    # previews get downscaled when viewed: aim for a readable width
    factor = max(1.0, 1200 / img.width) if args.zone else min(1.0, 1600 / img.width)
    view = img.resize((int(img.width * factor), int(img.height * factor)))
    target = max(img.width, img.height) / 16
    step = args.step or min((10, 20, 25, 50, 100, 200, 250, 500), key=lambda v: abs(v - target))

    d = ImageDraw.Draw(view, "RGBA")
    font = load_font(18)
    for gx in range(0, img.width + 1, step):
        X = int(gx * factor)
        major = (gx + ox) % (step * 2) == 0
        d.line([(X, 0), (X, view.height)], fill=(255, 0, 80, 150 if major else 70), width=1)
        if major:
            d.text((X + 2, 2), str(gx + ox), fill=(255, 0, 80, 255), font=font,
                   stroke_width=2, stroke_fill="white")
    for gy in range(0, img.height + 1, step):
        Y = int(gy * factor)
        major = (gy + oy) % (step * 2) == 0
        d.line([(0, Y), (view.width, Y)], fill=(0, 110, 255, 150 if major else 70), width=1)
        if major:
            d.text((2, Y + 2), str(gy + oy), fill=(0, 110, 255, 255), font=font,
                   stroke_width=2, stroke_fill="white")

    out = Path(args.out or f"/tmp/grid-{Path(args.image).stem}.png")
    view.save(out)
    print(f"{out}  (image {original.width}x{original.height} px, "
          f"step {step} px; labels every {step * 2} px)")


if __name__ == "__main__":
    main()
