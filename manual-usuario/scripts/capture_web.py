#!/usr/bin/env python3
"""Ejecuta manual.yaml en Chromium, toma capturas y las anota.

Uso:
    python capture_web.py manual.yaml --out build/ [--seccion ID] [--headed] [--slowmo MS]

Genera build/capturas/*.png y build/capturas.json (manifiesto con errores).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from annotate import annotate  # noqa: E402
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

TIMEOUT_MS = 10_000


# ---------------------------------------------------------------- utilidades
def expand_env(value):
    """Sustituye ${VAR} por variables de entorno, recursivamente."""
    if isinstance(value, str):
        def repl(m):
            var = m.group(1)
            if var not in os.environ:
                sys.exit(f"Falta la variable de entorno {var}")
            return os.environ[var]
        return re.sub(r"\$\{(\w+)\}", repl, value)
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    return value


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


# ---------------------------------------------------------------- acciones
def run_action(page, action, base_url):
    if not isinstance(action, dict) or len(action) != 1:
        raise ValueError(f"Acción inválida: {action!r}")
    (name, arg), = action.items()

    if name == "goto":
        url = arg if arg.startswith("http") else base_url.rstrip("/") + "/" + arg.lstrip("/")
        page.goto(url, wait_until="domcontentloaded")
    elif name == "click":
        page.locator(arg).first.click()
    elif name == "fill":
        page.locator(arg["selector"]).first.fill(str(arg["valor"]))
    elif name == "select":
        loc = page.locator(arg["selector"]).first
        try:
            loc.select_option(value=str(arg["valor"]), timeout=2000)
        except Exception:
            loc.select_option(label=str(arg["valor"]))
    elif name == "check":
        page.locator(arg).first.check()
    elif name == "uncheck":
        page.locator(arg).first.uncheck()
    elif name == "press":
        page.locator(arg["selector"]).first.press(arg["tecla"])
    elif name == "hover":
        page.locator(arg).first.hover()
    elif name == "scroll":
        page.locator(arg).first.scroll_into_view_if_needed()
    elif name == "esperar":
        if isinstance(arg, (int, float)):
            page.wait_for_timeout(arg)
        else:
            page.locator(arg).first.wait_for(state="visible")
    elif name == "js":
        page.evaluate(arg)
    else:
        raise ValueError(f"Acción desconocida: {name}")

    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PWTimeout:
        pass


def box_of(page, selector):
    """Bounding box en px CSS relativos al documento (para page_completa) y viewport."""
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=4000)
    b = loc.bounding_box()
    if not b:
        raise ValueError("elemento sin caja visible")
    return b


# ---------------------------------------------------------------- principal
def resolve_crop(page, spec):
    if not spec:
        return None
    if "selector" in spec:
        b = box_of(page, spec["selector"])
        m = spec.get("margen", 12)
        return {"x": b["x"] - m, "y": b["y"] - m,
                "width": b["width"] + 2 * m, "height": b["height"] + 2 * m}
    return {"x": spec["x"], "y": spec["y"], "width": spec["ancho"], "height": spec["alto"]}


def _rect(b, off):
    return {"x": b["x"] + off[0], "y": b["y"] + off[1], "w": b["width"], "h": b["height"]}


def capture_step(page, step_cap, global_blur, raw_path, scale):
    """Toma la captura cruda y devuelve los metadatos para annotate()."""
    errores = []
    cap = step_cap if isinstance(step_cap, dict) else {}
    full = bool(cap.get("pagina_completa"))
    # bounding_box() es relativo al viewport; en página completa se suma el scroll
    off = tuple(page.evaluate("[window.scrollX, window.scrollY]")) if full else (0, 0)

    resaltar = []
    for i, h in enumerate(as_list(cap.get("resaltar")), start=1):
        sel, label = (h["selector"], h.get("etiqueta", i)) if isinstance(h, dict) else (h, i)
        try:
            r = _rect(box_of(page, sel), off)
            r["etiqueta"] = None if label is False else str(label)
            resaltar.append(r)
        except Exception as e:
            errores.append(f"resaltar '{sel}': {e.__class__.__name__}: {str(e).splitlines()[0]}")

    ocultar = []
    for sel in global_blur + as_list(cap.get("ocultar")):
        try:
            for loc in page.locator(sel).all():
                if loc.is_visible() and loc.bounding_box():
                    ocultar.append(_rect(loc.bounding_box(), off))
        except Exception as e:
            errores.append(f"ocultar '{sel}': {str(e).splitlines()[0]}")

    recortar = None
    try:
        c = resolve_crop(page, cap.get("recortar"))
        if c:
            recortar = _rect(c, off)
    except Exception as e:
        errores.append(f"recortar: {str(e).splitlines()[0]}")

    page.screenshot(path=str(raw_path), full_page=full)
    return {"escala": scale, "resaltar": resaltar, "ocultar": ocultar,
            "recortar": recortar, "errores": errores}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default="build")
    ap.add_argument("--seccion", action="append", help="id de sección (repetible)")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--slowmo", type=int, default=0)
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    base_url = expand_env(spec["base_url"])
    viewport = spec.get("viewport", {"width": 1366, "height": 800})
    scale = spec.get("escala", 2)
    color = spec.get("color", "#E4572E")
    global_blur = as_list(spec.get("ocultar"))

    out = Path(args.out)
    shots = out / "capturas"
    raw = out / "crudas"
    shots.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "capturas.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    secciones = spec.get("secciones", [])
    if args.seccion:
        ids = {s["id"] for s in secciones}
        faltan = set(args.seccion) - ids
        if faltan:
            sys.exit(f"Secciones inexistentes: {', '.join(faltan)}")
        secciones = [s for s in secciones if s["id"] in args.seccion]

    total_err = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, slow_mo=args.slowmo)
        ctx = browser.new_context(viewport=viewport, device_scale_factor=scale,
                                  locale="es-MX")
        ctx.set_default_timeout(TIMEOUT_MS)
        page = ctx.new_page()

        login = spec.get("login")
        if login:
            print("→ Iniciando sesión…")
            try:
                run_action(page, {"goto": login["url"]}, base_url)
            except Exception as e:
                sys.exit(f"No se pudo abrir {base_url}{login['url']}: {str(e).splitlines()[0]}\n"
                         "¿Está corriendo el servidor (runserver) y es correcto base_url?")
            for a in login.get("acciones", []):
                run_action(page, expand_env(a), base_url)
            if login.get("esperar"):
                try:
                    page.locator(login["esperar"]).first.wait_for(state="visible")
                except PWTimeout:
                    page.screenshot(path=str(out / "login-fallido.png"))
                    sys.exit(f"El login no llegó a '{login['esperar']}'. "
                             f"Revisa {out / 'login-fallido.png'}")

        for sec in secciones:
            print(f"→ {sec['id']}: {sec.get('titulo', '')}")
            sec_manifest = []
            for n, step in enumerate(sec.get("pasos", []), start=1):
                entry = {"paso": n, "imagen": None, "errores": []}
                for a in step.get("acciones", []) or []:
                    try:
                        run_action(page, expand_env(a), base_url)
                    except Exception as e:
                        entry["errores"].append(
                            f"acción {a!r}: {e.__class__.__name__}: {str(e).splitlines()[0]}")
                        break  # no seguir con acciones si una falla

                cap = step.get("captura", False)
                if cap:
                    fname = f"{sec['id']}-{n:02d}.png"
                    try:
                        meta = capture_step(page, cap, global_blur, raw / fname, scale)
                        (raw / fname).with_suffix(".json").write_text(
                            json.dumps(meta, ensure_ascii=False, indent=1))
                        size = annotate(raw / fname, shots / fname, meta, color)
                        entry.update(imagen=f"capturas/{fname}", ancho_px=size[0],
                                     alto_px=size[1], escala=scale)
                        entry["errores"] += meta["errores"]
                    except Exception as e:
                        entry["errores"].append(f"captura: {e}")

                for err in entry["errores"]:
                    print(f"   ⚠ paso {n}: {err}")
                total_err += len(entry["errores"])
                sec_manifest.append(entry)
            manifest[sec["id"]] = sec_manifest

        browser.close()

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nCapturas en {shots}/ · manifiesto en {manifest_path}")
    if total_err:
        print(f"⚠ {total_err} problema(s). Revisa el YAML y vuelve a correr con --seccion.")
        sys.exit(1)
    print("✓ Sin errores. Revisa visualmente las imágenes antes de generar el documento.")


if __name__ == "__main__":
    main()
