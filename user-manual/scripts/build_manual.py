#!/usr/bin/env python3
"""Build the manual .docx (and optional PDF) from manual.yaml + annotated screenshots.

Usage:
    python build_manual.py manual.yaml --build build/manual [--pdf]

The document's fixed labels ("Step", "Note", "Contents"...) follow the
`language` key in manual.yaml ("en" or "es"; default "en").
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

LABELS = {
    "en": {
        "manual": "User manual", "contents": "Contents", "introduction": "Introduction",
        "step": "Step", "note": "Note:", "important": "Important:",
        "troubleshooting": "If something doesn't go as expected",
        "prepared_for": "Prepared for", "version": "Version", "date": "Date",
        "author": "Prepared by", "missing": "[MISSING SCREENSHOT]",
        "months": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "date_fmt": "{month} {day}, {year}",
    },
    "es": {
        "manual": "Manual de usuario", "contents": "Contenido", "introduction": "Introducción",
        "step": "Paso", "note": "Nota:", "important": "Importante:",
        "troubleshooting": "Si algo no sale como esperabas",
        "prepared_for": "Preparado para", "version": "Versión", "date": "Fecha",
        "author": "Elaborado por", "missing": "[FALTA CAPTURA]",
        "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                   "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        "date_fmt": "{day} de {month} de {year}",
    },
}
TEXT = RGBColor(0x22, 0x22, 0x22)
GRAY = RGBColor(0x66, 0x66, 0x66)


# ---------------------------------------------------------------- helpers
def hex_rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def add_md(par, text, size=None, color=None):
    """Add text with **bold** and *italic* to a paragraph."""
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
        run.font.size = Pt(9); run.font.color.rgb = GRAY


# ---------------------------------------------------------------- document
def setup(doc, accent):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(1.0)
    sec.top_margin = sec.bottom_margin = Inches(0.9)

    st = doc.styles
    normal = st["Normal"]
    normal.font.name = "Calibri"; normal.font.size = Pt(11)
    normal.font.color.rgb = TEXT
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for name, size, color in (("Heading 1", 20, accent), ("Heading 2", 14, TEXT),
                              ("Title", 32, TEXT)):
        s = st[name]
        s.font.name = "Calibri"; s.font.size = Pt(size); s.font.bold = True
        s.font.color.rgb = color
        rfonts = s.element.get_or_add_rPr().find(qn("w:rFonts"))
        if rfonts is not None:  # drop theme fonts so Calibri actually applies
            for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                rfonts.attrib.pop(qn(attr), None)
    st["Heading 1"].paragraph_format.space_before = Pt(0)
    st["Heading 1"].paragraph_format.space_after = Pt(10)


def cover(doc, spec, accent, L):
    for _ in range(6):
        doc.add_paragraph()
    doc.add_paragraph(style="Title").add_run(spec.get("title", L["manual"]))
    if spec.get("subtitle"):
        r = doc.add_paragraph().add_run(spec["subtitle"])
        r.font.size = Pt(16); r.font.color.rgb = accent
    bar = doc.add_paragraph()
    bdr = OxmlElement("w:pBdr"); b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "18"); b.set(qn("w:color"), str(accent))
    bdr.append(b); bar._p.get_or_add_pPr().append(bdr)

    today = dt.date.today()
    meta = []
    if spec.get("client"):
        meta.append((L["prepared_for"], spec["client"]))
    if spec.get("version"):
        meta.append((L["version"], str(spec["version"])))
    meta.append((L["date"], L["date_fmt"].format(
        day=today.day, month=L["months"][today.month - 1], year=today.year)))
    if spec.get("author"):
        meta.append((L["author"], spec["author"]))
    for k, v in meta:
        p = doc.add_paragraph()
        r = p.add_run(f"{k}: "); r.bold = True; r.font.color.rgb = GRAY
        p.add_run(v)


def build(spec, build_dir):
    L = LABELS.get(spec.get("language", "en"), LABELS["en"])
    accent = hex_rgb(spec.get("color", "#E4572E"))
    manifest_path = build_dir / "screenshots.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    sections = spec.get("sections", [])

    doc = Document()
    setup(doc, accent)
    cover(doc, spec, accent, L)

    # everything after the cover goes in a new section with a footer and page numbers
    body = doc.add_section(WD_SECTION.NEW_PAGE)
    body.footer.is_linked_to_previous = False
    fp = body.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run(spec.get("title", L["manual"]) + "  ·  ")
    r.font.size = Pt(9); r.font.color.rgb = GRAY
    add_page_number(fp)
    doc.sections[0].different_first_page_header_footer = True
    pg = OxmlElement("w:pgNumType"); pg.set(qn("w:start"), "1")
    body._sectPr.append(pg)

    doc.add_paragraph(style="Heading 1").add_run(L["contents"])
    for i, s in enumerate(sections, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"{i}.  "); r.bold = True
        p.add_run(s["title"])

    if spec.get("introduction"):
        h = doc.add_paragraph(style="Heading 1"); h.add_run(L["introduction"])
        h.paragraph_format.space_before = Pt(24)
        for para in str(spec["introduction"]).strip().split("\n\n"):
            add_md(doc.add_paragraph(), para.strip())

    missing = []
    for i, sec in enumerate(sections, 1):
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_paragraph(style="Heading 1").add_run(f"{i}. {sec['title']}")
        if sec.get("intro"):
            add_md(doc.add_paragraph(), sec["intro"], color=GRAY)
        shots = {e["step"]: e for e in manifest.get(sec["id"], [])}

        for n, step in enumerate(sec.get("steps", []), 1):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            r = p.add_run(f"{L['step']} {n}.  "); r.bold = True; r.font.color.rgb = accent
            add_md(p, step.get("text", ""))

            cap = step.get("capture")
            if cap:
                entry = shots.get(n) or {}
                img = build_dir / entry["image"] if entry.get("image") else None
                if img and img.exists():
                    p.paragraph_format.keep_with_next = True
                    want = cap.get("width", 6.0) if isinstance(cap, dict) else 6.0
                    # never enlarge below ~96 px per inch (it would look blurry)
                    natural = entry["width_px"] / 96 if entry.get("width_px") else want
                    width = min(want, 6.5, max(natural, 2.0))
                    ip = doc.add_paragraph()
                    ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    ip.add_run().add_picture(str(img), width=Inches(width))
                else:
                    missing.append(f"{sec['id']} step {n}")
                    callout(doc, L["missing"], f"{sec['id']}-{n:02d}", "#FDECEA", "#C0392B")

            if step.get("note"):
                callout(doc, L["note"], step["note"], "#F2F2F2", "#999999")
            if step.get("important"):
                callout(doc, L["important"], step["important"], "#FFF4E5", "#E69500")

        if sec.get("troubleshooting"):
            h = doc.add_paragraph(style="Heading 2"); h.add_run(L["troubleshooting"])
            h.paragraph_format.space_before = Pt(14)
            for item in sec["troubleshooting"]:
                add_md(doc.add_paragraph(style="List Bullet"), item)

    out = build_dir / f"{spec.get('filename', 'user-manual')}.docx"
    doc.save(out)
    return out, missing


def to_pdf(docx_path):
    soffice = (shutil.which("soffice") or shutil.which("libreoffice")
               or "/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if not Path(soffice).exists():
        print("LibreOffice not found; skipping PDF (brew install --cask libreoffice).")
        return None
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir",
                    str(docx_path.parent), str(docx_path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return docx_path.with_suffix(".pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--build", default="build/manual")
    ap.add_argument("--pdf", action="store_true")
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    build_dir = Path(args.build)
    build_dir.mkdir(parents=True, exist_ok=True)
    out, missing = build(spec, build_dir)
    print(f"✓ {out}")
    if args.pdf and (pdf := to_pdf(out)):
        print(f"✓ {pdf}")
    if missing:
        print(f"⚠ Steps without a screenshot ({len(missing)}): " + ", ".join(missing))
        sys.exit(1)


if __name__ == "__main__":
    main()
