#!/usr/bin/env python3
"""Arma el manual .docx (y PDF opcional) a partir de manual.yaml + capturas.

Uso:
    python build_manual.py manual.yaml --build build/ [--pdf]
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
TEXTO = RGBColor(0x22, 0x22, 0x22)
GRIS = RGBColor(0x66, 0x66, 0x66)


# ---------------------------------------------------------------- helpers
def hex_rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def add_md(par, text, size=None, color=None):
    """Agrega texto con **negritas** y *cursivas* a un párrafo."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text or ""):
        if not tok:
            continue
        if tok.startswith("**"):
            run = par.add_run(tok[2:-2]); run.bold = True
        elif tok.startswith("*"):
            run = par.add_run(tok[1:-1]); run.italic = True
        else:
            run = par.add_run(tok)
        if size:
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
    return par


def shade_cell(cell, fill_hex, border_hex=None):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex.lstrip("#"))
    tcPr.append(shd)
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        if border_hex and side == "left":
            el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "24")
            el.set(qn("w:color"), border_hex.lstrip("#"))
        else:
            el.set(qn("w:val"), "nil")
        borders.append(el)
    tcPr.append(borders)


def callout(doc, label, text, fill, border):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    shade_cell(cell, fill, border)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(label + "  "); r.bold = True; r.font.size = Pt(10)
    add_md(p, text, size=10)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_page_number(par):
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        run = par.add_run()
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind)
            run._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve")
            it.text = txt
            run._r.append(it)
        run.font.size = Pt(9); run.font.color.rgb = GRIS


def keep_with_next(par):
    par.paragraph_format.keep_with_next = True


# ---------------------------------------------------------------- documento
def setup(doc, accent):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Inches(1.0))
    sec.top_margin = sec.bottom_margin = Inches(0.9)

    st = doc.styles
    normal = st["Normal"]
    normal.font.name = "Calibri"; normal.font.size = Pt(11)
    normal.font.color.rgb = TEXTO
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for name, size, color in (("Heading 1", 20, accent), ("Heading 2", 14, TEXTO),
                              ("Title", 32, TEXTO)):
        s = st[name]
        s.font.name = "Calibri"; s.font.size = Pt(size); s.font.bold = True
        s.font.color.rgb = color
        rpr = s.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is not None:
            for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                rfonts.attrib.pop(qn(attr), None)
    st["Heading 1"].paragraph_format.space_before = Pt(0)
    st["Heading 1"].paragraph_format.space_after = Pt(10)


def cover(doc, spec, accent):
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph(style="Title")
    p.add_run(spec.get("titulo", "Manual de usuario"))
    if spec.get("subtitulo"):
        p = doc.add_paragraph()
        r = p.add_run(spec["subtitulo"]); r.font.size = Pt(16); r.font.color.rgb = accent
    bar = doc.add_paragraph()
    pPr = bar._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr"); b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "18")
    b.set(qn("w:color"), str(accent)); bdr.append(b); pPr.append(bdr)
    hoy = dt.date.today()
    meta = []
    if spec.get("cliente"):
        meta.append(("Preparado para", spec["cliente"]))
    if spec.get("version"):
        meta.append(("Versión", str(spec["version"])))
    meta.append(("Fecha", f"{hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}"))
    if spec.get("autor"):
        meta.append(("Elaborado por", spec["autor"]))
    for k, v in meta:
        p = doc.add_paragraph()
        r = p.add_run(f"{k}: "); r.bold = True; r.font.color.rgb = GRIS
        p.add_run(v)


def contents(doc, secciones):
    doc.add_paragraph(style="Heading 1").add_run("Contenido")
    for i, s in enumerate(secciones, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"{i}.  "); r.bold = True
        p.add_run(s["titulo"])


def build(spec, build_dir):
    accent = hex_rgb(spec.get("color", "#E4572E"))
    manifest_path = build_dir / "capturas.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    secciones = spec.get("secciones", [])

    doc = Document()
    setup(doc, accent)
    cover(doc, spec, accent)

    # contenido y resto en nueva sección (portada sin pie de página)
    new = doc.add_section(WD_SECTION.NEW_PAGE)
    new.footer.is_linked_to_previous = False
    fp = new.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run(spec.get("titulo", "Manual de usuario") + "  ·  ")
    r.font.size = Pt(9); r.font.color.rgb = GRIS
    add_page_number(fp)
    doc.sections[0].different_first_page_header_footer = True
    pg = OxmlElement("w:pgNumType"); pg.set(qn("w:start"), "1")
    new._sectPr.append(pg)

    contents(doc, secciones)

    if spec.get("introduccion"):
        h = doc.add_paragraph(style="Heading 1"); h.add_run("Introducción")
        h.paragraph_format.space_before = Pt(24)
        for para in str(spec["introduccion"]).strip().split("\n\n"):
            add_md(doc.add_paragraph(), para.strip())

    faltantes = []
    for i, sec in enumerate(secciones, 1):
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_paragraph(style="Heading 1").add_run(f"{i}. {sec['titulo']}")
        if sec.get("intro"):
            add_md(doc.add_paragraph(), sec["intro"], color=GRIS)
        shots = {e["paso"]: e for e in manifest.get(sec["id"], [])}

        for n, step in enumerate(sec.get("pasos", []), 1):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            r = p.add_run(f"Paso {n}.  "); r.bold = True; r.font.color.rgb = accent
            add_md(p, step.get("texto", ""))

            cap = step.get("captura")
            if cap:
                entry = shots.get(n) or {}
                img = build_dir / entry["imagen"] if entry.get("imagen") else None
                if img and img.exists():
                    keep_with_next(p)
                    want = cap.get("ancho", 6.0) if isinstance(cap, dict) else 6.0
                    # no agrandar una imagen por debajo de ~96 px por pulgada (se vería borrosa)
                    natural = entry["ancho_px"] / 96 if entry.get("ancho_px") else want
                    width = min(want, 6.5, max(natural, 2.0))
                    ip = doc.add_paragraph()
                    ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    ip.add_run().add_picture(str(img), width=Inches(width))
                else:
                    faltantes.append(f"{sec['id']} paso {n}")
                    callout(doc, "[FALTA CAPTURA]", f"{sec['id']} paso {n}", "#FDECEA", "#C0392B")

            if step.get("nota"):
                callout(doc, "Nota:", step["nota"], "#F2F2F2", "#999999")
            if step.get("importante"):
                callout(doc, "Importante:", step["importante"], "#FFF4E5", "#E69500")

        if sec.get("problemas"):
            h = doc.add_paragraph(style="Heading 2"); h.add_run("Si algo no sale como esperabas")
            h.paragraph_format.space_before = Pt(14)
            for item in sec["problemas"]:
                add_md(doc.add_paragraph(style="List Bullet"), item)

    name = spec.get("archivo", "manual-usuario")
    out = build_dir / f"{name}.docx"
    doc.save(out)
    return out, faltantes


def to_pdf(docx_path):
    soffice = shutil.which("soffice") or shutil.which("libreoffice") or \
        "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if not Path(soffice).exists() and not shutil.which(soffice):
        print("LibreOffice no encontrado; omito PDF (brew install --cask libreoffice).")
        return None
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir",
                    str(docx_path.parent), str(docx_path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return docx_path.with_suffix(".pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--build", default="build")
    ap.add_argument("--pdf", action="store_true")
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    build_dir = Path(args.build)
    build_dir.mkdir(parents=True, exist_ok=True)
    out, faltantes = build(spec, build_dir)
    print(f"✓ {out}")
    if args.pdf:
        pdf = to_pdf(out)
        if pdf:
            print(f"✓ {pdf}")
    if faltantes:
        print(f"⚠ Pasos sin captura ({len(faltantes)}): " + ", ".join(faltantes))
        sys.exit(1)


if __name__ == "__main__":
    main()
