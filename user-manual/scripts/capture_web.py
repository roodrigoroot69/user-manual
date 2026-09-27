#!/usr/bin/env python3
"""Run manual.yaml in Chromium (Playwright), take screenshots and annotate them.

Usage:
    python capture_web.py manual.yaml --out build/manual [--section ID] [--headed] [--slowmo MS]

Writes build/manual/raw/ (raw screenshots + JSON), build/manual/screenshots/
(annotated) and build/manual/screenshots.json (manifest with errors).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from annotate import annotate  # noqa: E402

TIMEOUT_MS = 10_000


# ---------------------------------------------------------------- helpers
def expand_env(value):
    """Replace ${VAR} with environment variables, recursively."""
    if isinstance(value, str):
        def repl(m):
            var = m.group(1)
            if var not in os.environ:
                sys.exit(f"Missing environment variable {var}")
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


def first_line(e):
    return str(e).splitlines()[0] if str(e) else e.__class__.__name__


# ---------------------------------------------------------------- actions
def run_action(page, action, base_url):
    if not isinstance(action, dict) or len(action) != 1:
        raise ValueError(f"Invalid action: {action!r}")
    (name, arg), = action.items()

    if name == "goto":
        url = arg if re.match(r"^(https?|file):", arg) else base_url.rstrip("/") + "/" + arg.lstrip("/")
        page.goto(url, wait_until="domcontentloaded")
    elif name == "click":
        page.locator(arg).first.click()
    elif name == "fill":
        page.locator(arg["selector"]).first.fill(str(arg["value"]))
    elif name == "select":
        loc = page.locator(arg["selector"]).first
        try:
            loc.select_option(value=str(arg["value"]), timeout=2000)
        except Exception:
            loc.select_option(label=str(arg["value"]))
    elif name == "check":
        page.locator(arg).first.check()
    elif name == "uncheck":
        page.locator(arg).first.uncheck()
    elif name == "press":
        page.locator(arg["selector"]).first.press(arg["key"])
    elif name == "hover":
        page.locator(arg).first.hover()
    elif name == "scroll":
        page.locator(arg).first.scroll_into_view_if_needed()
    elif name == "wait":
        if isinstance(arg, (int, float)):
            page.wait_for_timeout(arg)
        else:
            page.locator(arg).first.wait_for(state="visible")
    elif name == "js":
        page.evaluate(arg)
    else:
        raise ValueError(f"Unknown action: {name}")

    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PWTimeout:
        pass


def box_of(page, selector):
    """Bounding box in CSS px, relative to the viewport."""
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=4000)
    b = loc.bounding_box()
    if not b:
        raise ValueError("element has no visible box")
    return b


# ---------------------------------------------------------------- capture
def resolve_crop(page, spec):
    if not spec:
        return None
    if "selector" in spec:
        b = box_of(page, spec["selector"])
        m = spec.get("margin", 12)
        return {"x": b["x"] - m, "y": b["y"] - m,
                "width": b["width"] + 2 * m, "height": b["height"] + 2 * m}
    return {"x": spec["x"], "y": spec["y"], "width": spec["width"], "height": spec["height"]}


def _rect(b, off):
    return {"x": b["x"] + off[0], "y": b["y"] + off[1], "w": b["width"], "h": b["height"]}


def capture_step(page, step_cap, global_redact, raw_path, scale):
    """Take the raw screenshot and return the metadata for annotate()."""
    errors = []
    cap = step_cap if isinstance(step_cap, dict) else {}
    full = bool(cap.get("full_page"))
    # bounding_box() is viewport-relative; for full-page shots add the scroll offset
    off = tuple(page.evaluate("[window.scrollX, window.scrollY]")) if full else (0, 0)

    highlight = []
    for i, h in enumerate(as_list(cap.get("highlight")), start=1):
        sel, label = (h["selector"], h.get("label", i)) if isinstance(h, dict) else (h, i)
        try:
            r = _rect(box_of(page, sel), off)
            r["label"] = None if label in (False, None) else str(label)
            highlight.append(r)
        except Exception as e:
            errors.append(f"highlight '{sel}': {e.__class__.__name__}: {first_line(e)}")

    redact = []
    for sel in global_redact + as_list(cap.get("redact")):
        try:
            for loc in page.locator(sel).all():
                if loc.is_visible() and loc.bounding_box():
                    redact.append(_rect(loc.bounding_box(), off))
        except Exception as e:
            errors.append(f"redact '{sel}': {first_line(e)}")

    crop = None
    try:
        c = resolve_crop(page, cap.get("crop"))
        if c:
            crop = _rect(c, off)
    except Exception as e:
        errors.append(f"crop: {first_line(e)}")

    page.screenshot(path=str(raw_path), full_page=full)
    return {"scale": scale, "highlight": highlight, "redact": redact,
            "crop": crop, "errors": errors}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default="build/manual")
    ap.add_argument("--section", action="append", help="section id (repeatable)")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--slowmo", type=int, default=0)
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    base_url = expand_env(spec["base_url"])
    viewport = spec.get("viewport", {"width": 1366, "height": 800})
    scale = spec.get("scale", 2)
    color = spec.get("color", "#E4572E")
    locale = spec.get("locale", "es-MX" if spec.get("language") == "es" else "en-US")
    global_redact = as_list(spec.get("redact"))

    out = Path(args.out)
    shots, raw = out / "screenshots", out / "raw"
    shots.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "screenshots.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    sections = spec.get("sections", [])
    if args.section:
        missing = set(args.section) - {s["id"] for s in sections}
        if missing:
            sys.exit(f"Unknown sections: {', '.join(missing)}")
        sections = [s for s in sections if s["id"] in args.section]

    total_err = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, slow_mo=args.slowmo)
        ctx = browser.new_context(viewport=viewport, device_scale_factor=scale, locale=locale)
        ctx.set_default_timeout(TIMEOUT_MS)
        page = ctx.new_page()

        login = spec.get("login")
        if login:
            print("→ Logging in…")
            try:
                run_action(page, {"goto": login["url"]}, base_url)
            except Exception as e:
                sys.exit(f"Could not open {base_url}{login['url']}: {first_line(e)}\n"
                         "Is the server running, and is base_url correct?")
            for a in login.get("actions", []):
                run_action(page, expand_env(a), base_url)
            if login.get("wait"):
                try:
                    page.locator(login["wait"]).first.wait_for(state="visible")
                except PWTimeout:
                    page.screenshot(path=str(out / "login-failed.png"))
                    sys.exit(f"Login never reached '{login['wait']}'. "
                             f"Check {out / 'login-failed.png'}")

        for sec in sections:
            print(f"→ {sec['id']}: {sec.get('title', '')}")
            sec_manifest = []
            for n, step in enumerate(sec.get("steps", []), start=1):
                entry = {"step": n, "image": None, "errors": []}
                for a in step.get("actions", []) or []:
                    try:
                        run_action(page, expand_env(a), base_url)
                    except Exception as e:
                        entry["errors"].append(
                            f"action {a!r}: {e.__class__.__name__}: {first_line(e)}")
                        break  # stop this step's actions after a failure

                cap = step.get("capture", False)
                if cap:
                    fname = f"{sec['id']}-{n:02d}.png"
                    try:
                        meta = capture_step(page, cap, global_redact, raw / fname, scale)
                        (raw / fname).with_suffix(".json").write_text(
                            json.dumps(meta, ensure_ascii=False, indent=1))
                        size = annotate(raw / fname, shots / fname, meta, color)
                        entry.update(image=f"screenshots/{fname}",
                                     width_px=size[0], height_px=size[1])
                        entry["errors"] += meta["errors"]
                    except Exception as e:
                        entry["errors"].append(f"capture: {e}")

                for err in entry["errors"]:
                    print(f"   ⚠ step {n}: {err}")
                total_err += len(entry["errors"])
                sec_manifest.append(entry)
            manifest[sec["id"]] = sec_manifest

        browser.close()

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nScreenshots in {shots}/ · manifest in {manifest_path}")
    if total_err:
        print(f"⚠ {total_err} problem(s). Fix the YAML and rerun with --section.")
        sys.exit(1)
    print("✓ No errors. Review the images before building the document.")


if __name__ == "__main__":
    main()
