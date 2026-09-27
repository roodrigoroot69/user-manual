#!/usr/bin/env python3
"""Annotate raw screenshots and build the manifest used by build_manual.py.

Technology-agnostic: any capture driver (web/Playwright, JavaFX/TestFX,
Flutter, manual mode...) only has to leave, for each screenshot:

    <section-id>-<NN>.png    raw screenshot
    <section-id>-<NN>.json   metadata (see below)

JSON (coordinates in logical px of the window/page, NOT scaled):
    {
      "scale": 2,                      # image px per logical px
      "density": 2,                    # optional: stroke/badge size (defaults to scale)
      "highlight": [{"x":10,"y":20,"w":100,"h":30,"label":"1"}],  # label null = no badge
      "redact":    [{"x":..,"y":..,"w":..,"h":..}],
      "crop":      {"x":..,"y":..,"w":..,"h":..} | null,
      "errors":    ["text", ...]
    }

Usage:
    python annotate.py build/manual/raw --out build/manual [--color "#E4572E"]
Writes build/manual/screenshots/*.png (annotated) and build/manual/screenshots.json.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

NAME = re.compile(r"^(?P<sec>.+)-(?P<n>\d{2,3})$")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(size):
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def annotate(src, dst, meta, color="#E4572E"):
    """Apply redaction, highlight boxes, numbered badges and crop. Returns (w, h)."""
    img = Image.open(src).convert("RGB")
    s = float(meta.get("scale", 1))            # coordinates
    d = float(meta.get("density", s))          # stroke and badge size

    def px(b, pad=0):
        return (int((b["x"] - pad) * s), int((b["y"] - pad) * s),
                int((b["x"] + b["w"] + pad) * s), int((b["y"] + b["h"] + pad) * s))

    def clamp(r):
        return (max(0, r[0]), max(0, r[1]), min(img.width, r[2]), min(img.height, r[3]))

    # 1) blur sensitive data
    for b in meta.get("redact") or []:
        r = clamp(px(b, 2))
        if r[2] > r[0] and r[3] > r[1]:
            img.paste(img.crop(r).filter(ImageFilter.GaussianBlur(radius=8 * d)), r[:2])

    # 2) translucent highlight boxes
    rgb = hex_to_rgb(color)
    highlights = meta.get("highlight") or []
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for b in highlights:
        od.rounded_rectangle(clamp(px(b, 6)), radius=int(8 * d), fill=rgb + (28,),
                             outline=rgb + (255,), width=max(2, int(3 * d)))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    # 3) numbered badges, outside the box so they don't cover text
    draw = ImageDraw.Draw(img)
    radius = int(14 * d)
    font = load_font(int(16 * d))
    badges = []
    for b in highlights:
        label = b.get("label")
        if label in (None, False, ""):
            continue
        r = px(b, 6)
        gap = int(6 * d)
        cy = (r[1] + r[3]) // 2
        # right side first (form labels usually sit on the left or above)
        if r[2] + gap + 2 * radius <= img.width:
            cx = r[2] + gap + radius
        elif r[0] - gap - 2 * radius >= 0:
            cx = r[0] - gap - radius
        else:
            cx, cy = r[0], r[1]
        cx = max(radius + 2, min(img.width - radius - 2, cx))
        cy = max(radius + 2, min(img.height - radius - 2, cy))
        badges.append((cx - radius - 4, cy - radius - 4, cx + radius + 4, cy + radius + 4))
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     fill=rgb + (255,), outline=(255, 255, 255, 255), width=max(1, int(2 * d)))
        draw.text((cx, cy), str(label), fill="white", font=font, anchor="mm")
    img = img.convert("RGB")

    # 4) crop (expanded so badges are never cut off)
    crop = meta.get("crop")
    if crop:
        c = list(px(crop))
        for bx in badges:
            c = [min(c[0], bx[0]), min(c[1], bx[1]), max(c[2], bx[2]), max(c[3], bx[3])]
        img = img.crop(clamp(tuple(c)))

    img.save(dst, optimize=True)
    return img.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="folder with <section>-<NN>.png + .json")
    ap.add_argument("--out", default="build/manual")
    ap.add_argument("--color", default="#E4572E")
    args = ap.parse_args()

    src_dir, out = Path(args.raw), Path(args.out)
    shots = out / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "screenshots.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    pngs = sorted(src_dir.glob("*.png"))
    if not pngs:
        sys.exit(f"No screenshots found in {src_dir}")

    fresh, total_err = {}, 0
    for png in pngs:
        m = NAME.match(png.stem)
        if not m:
            print(f"⚠ Invalid name (expected <section>-<NN>.png): {png.name}")
            continue
        meta_path = png.with_suffix(".json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        size = annotate(png, shots / png.name, meta, args.color)
        errs = meta.get("errors") or []
        for e in errs:
            print(f"   ⚠ {png.stem}: {e}")
        total_err += len(errs)
        fresh.setdefault(m["sec"], []).append({
            "step": int(m["n"]), "image": f"screenshots/{png.name}",
            "width_px": size[0], "height_px": size[1], "errors": errs})

    manifest.update(fresh)  # only replaces the sections that were recaptured
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"✓ {sum(len(v) for v in fresh.values())} screenshots annotated in {shots}/")
    if total_err:
        print(f"⚠ {total_err} problem(s) reported by the driver.")
        sys.exit(1)


if __name__ == "__main__":
    main()
