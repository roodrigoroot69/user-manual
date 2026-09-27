#!/usr/bin/env python3
"""Anota capturas crudas y genera el manifiesto para build_manual.py.

Es independiente de la tecnología: cualquier "driver" (web con Playwright,
JavaFX con TestFX, Flutter, etc.) solo tiene que dejar, por cada captura:

    <seccion-id>-<NN>.png    captura cruda
    <seccion-id>-<NN>.json   metadatos (ver abajo)

JSON (coordenadas en px lógicos de la ventana/página, SIN escalar):
    {
      "escala": 2,                     # px de la imagen por px lógico
      "densidad": 2,                   # opcional: grosor de trazos y números (por defecto = escala)
      "resaltar": [{"x":10,"y":20,"w":100,"h":30,"etiqueta":"1"}],  # etiqueta null = sin número
      "ocultar":  [{"x":..,"y":..,"w":..,"h":..}],
      "recortar": {"x":..,"y":..,"w":..,"h":..} | null,
      "errores":  ["texto", ...]
    }

Uso:
    python annotate.py build/crudas --out build [--color "#E4572E"]
Genera build/capturas/*.png anotadas y build/capturas.json.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

NOMBRE = re.compile(r"^(?P<sec>.+)-(?P<n>\d{2,3})$")


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
    """Aplica difuminado, recuadros, números y recorte. Devuelve (ancho, alto)."""
    img = Image.open(src).convert("RGB")
    s = float(meta.get("escala", 1))              # coordenadas
    d = float(meta.get("densidad", s))            # tamaño de trazos y números

    def px(b, pad=0):
        return (int((b["x"] - pad) * s), int((b["y"] - pad) * s),
                int((b["x"] + b["w"] + pad) * s), int((b["y"] + b["h"] + pad) * s))

    def clamp(r):
        return (max(0, r[0]), max(0, r[1]), min(img.width, r[2]), min(img.height, r[3]))

    # 1) difuminar datos sensibles
    for b in meta.get("ocultar") or []:
        r = clamp(px(b, 2))
        if r[2] > r[0] and r[3] > r[1]:
            img.paste(img.crop(r).filter(ImageFilter.GaussianBlur(radius=8 * d)), r[:2])

    # 2) recuadros semitransparentes
    rgb = hex_to_rgb(color)
    highlights = meta.get("resaltar") or []
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for b in highlights:
        od.rounded_rectangle(clamp(px(b, 6)), radius=int(8 * d), fill=rgb + (28,),
                             outline=rgb + (255,), width=max(2, int(3 * d)))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    # 3) números fuera del recuadro para no tapar texto
    draw = ImageDraw.Draw(img)
    radius = int(14 * d)
    font = load_font(int(16 * d))
    badges = []
    for b in highlights:
        label = b.get("etiqueta")
        if label in (None, False, ""):
            continue
        r = px(b, 6)
        gap = int(6 * d)
        cy = (r[1] + r[3]) // 2
        # derecha primero (en formularios la etiqueta suele ir a la izquierda o arriba)
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

    # 4) recorte (se amplía para no cortar los números)
    crop = meta.get("recortar")
    if crop:
        c = list(px(crop))
        for bx in badges:
            c = [min(c[0], bx[0]), min(c[1], bx[1]), max(c[2], bx[2]), max(c[3], bx[3])]
        img = img.crop(clamp(tuple(c)))

    img.save(dst, optimize=True)
    return img.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("crudas", help="carpeta con <seccion>-<NN>.png + .json")
    ap.add_argument("--out", default="build")
    ap.add_argument("--color", default="#E4572E")
    args = ap.parse_args()

    src_dir, out = Path(args.crudas), Path(args.out)
    shots = out / "capturas"
    shots.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "capturas.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    pngs = sorted(src_dir.glob("*.png"))
    if not pngs:
        sys.exit(f"No hay capturas en {src_dir}")

    nuevas, total_err = {}, 0
    for png in pngs:
        m = NOMBRE.match(png.stem)
        if not m:
            print(f"⚠ Nombre no válido (esperado <seccion>-<NN>.png): {png.name}")
            continue
        meta_path = png.with_suffix(".json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        size = annotate(png, shots / png.name, meta, args.color)
        errs = meta.get("errores") or []
        for e in errs:
            print(f"   ⚠ {png.stem}: {e}")
        total_err += len(errs)
        nuevas.setdefault(m["sec"], []).append({
            "paso": int(m["n"]), "imagen": f"capturas/{png.name}",
            "ancho_px": size[0], "alto_px": size[1], "escala": meta.get("escala", 1),
            "errores": errs})

    manifest.update(nuevas)  # solo reemplaza las secciones recapturadas
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"✓ {sum(len(v) for v in nuevas.values())} capturas anotadas en {shots}/")
    if total_err:
        print(f"⚠ {total_err} problema(s) reportados por el driver.")
        sys.exit(1)


if __name__ == "__main__":
    main()
