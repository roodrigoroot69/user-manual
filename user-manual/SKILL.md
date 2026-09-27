---
name: user-manual
description: Generates end-user manuals from the real application. It walks through the app's flows automatically, takes screenshots, annotates them (numbered highlight boxes, blurred sensitive data, crops) and builds a Word/PDF document with plain-language steps, in English or Spanish. Works on any platform, since it detects the kind of app in the repository and uses the right driver (web via Playwright, JavaFX desktop via TestFX, tablet and mobile via Flutter) or a manual mode for everything else (native Android/iOS, .NET, etc.). Use it whenever the user asks for a user manual, user guide, how-to guide, step-by-step tutorial, end-user documentation, training material, or "manual de usuario", or wants to update a manual after UI changes, even if they don't mention screenshots.
---

# User manual generator

The skill has three decoupled pieces:

1. **Capture driver** (depends on the app's technology): walks through the flows and leaves, for each step, a raw screenshot `<section>-<NN>.png` plus a `<section>-<NN>.json` with the boxes to highlight, redact or crop.
2. **`scripts/annotate.py`** (shared): draws boxes and numbered badges, blurs, crops.
3. **`scripts/build_manual.py`** (shared): builds the Word/PDF from the texts in `manual.yaml` and the annotated screenshots.

When the UI changes, rerun the driver and the manual regenerates itself.

## Step 0 — Gather project context

Before proposing anything, read what the team already wrote about the system. This avoids guessing screen names, business rules and the client's vocabulary. Follow `references/context.md`: it lists what to look for (CLAUDE.md, AGENTS.md, OpenSpec, code graphs such as codegraph, Markdown docs, FXML) and in what order.

Output of this step: a short summary of user roles, modules and business vocabulary (what the client calls each thing), plus the proposed list of manual sections organized by **task** ("Record a stock entry"), not by screen. Confirm it with the user before capturing.

## Step 1 — Detect the platform and pick a driver

Run detection on the repository:

```bash
python scripts/detect_platform.py <repo-path>
```

It reports every app it finds (a repo can hold several: desktop, tablet and web portal), with the recommended driver and the reference to read. Read **only** the reference for the driver you'll use:

| Platform | Driver | Reference | Regenerates by itself |
|---|---|---|---|
| Web (Django, Next.js, static HTML, etc.) | Playwright (`scripts/capture_web.py`) | `references/web.md` | Yes |
| JavaFX desktop | TestFX + `assets/javafx/` | `references/javafx.md` | Yes |
| Flutter (tablet, mobile) | `integration_test` + `assets/flutter/` | `references/flutter.md` | Yes |
| Native Android/iOS, React Native, Electron, .NET, Swing, others | Manual mode (`scripts/grid.py`, `scripts/android_bounds.py`) | `references/manual-mode.md` | No |

How to decide:
- **Several apps detected:** ask which one the manual is for. Each app gets its own `manual.yaml` and output folder (`docs/manual/<app>/manual.yaml` → `build/manual/<app>/`), so they can be done one by one with the same visual style.
- **One app, several platforms** (Flutter with android/ios/web): ask which device the client will use it on, and capture on that one.
- **Nothing detected, or detection contradicts the user:** trust the user. If their platform has no driver, use manual mode.
- **The user wants it fast or can't run the app** (no emulator, third-party app): manual mode with the screenshots they provide.

For a new platform that will be documented often, write a driver: it only has to produce `<section>-<NN>.png` + `.json` in the format described in the `scripts/annotate.py` docstring. Everything else is reused.

## Step 2 — Demo data

Screenshots show whatever is in the database. Never use the client's real data: the manual gets printed and forwarded. Prepare a demo database with believable data for the business, and make the driver always start from a clean copy so screenshots are reproducible. Details per technology are in each reference.

## Step 3 — Write `manual.yaml`

It holds the manual's texts and the section/step structure (`references/spec-format.md`). The step number in the YAML is the `NN` in the screenshot name: step 3 of `record-stock-entry` is `record-stock-entry-03.png`.

## Step 4 — Capture and annotate

Run the driver (see its reference), then:

```bash
python scripts/annotate.py build/manual/raw --out build/manual
```

The web driver annotates by itself. Drivers never stop when an element is missing: they record the error in the JSON and `annotate.py` reports it at the end.

## Step 5 — Review the screenshots (don't skip this)

Look at the images in `build/manual/screenshots/`. Check that:
- It's the right screen (not an error, an unexpected dialog or a half-loaded view).
- Boxes sit on the right element and badges don't cover important text.
- No sensitive data is visible.
- The step text describes what's actually on screen.

Fix and recapture only the affected section.

## Step 6 — Build the document

```bash
python scripts/build_manual.py manual.yaml --build build/manual --pdf
```

Convert the PDF to images (`pdftoppm -r 60`) and review a few pages before delivering. If a step in the YAML has no screenshot, the document shows a red `[MISSING SCREENSHOT]` box and the script reports it.

## Writing for the end user

Write the manual in the **end user's language**, which is not necessarily the language of this skill or of the codebase. Set `language` in `manual.yaml` (`en` or `es`) so the document's fixed labels match. The reader is not technical and will probably have the manual open next to the system:

- Second person, friendly imperative: "Click **Save**." Not "The user shall…".
- Name buttons and menus exactly as they appear on screen, in bold.
- Use the client's vocabulary found in Step 0 (if the business says "wholesale tier" or "pack size", use it as-is).
- One action per step, and say what will happen: "The product list will appear."
- No technical jargon: no "modal", "sync queue", "record", "query", "dropdown" ("drop-down list" or "window" are fine).
- `important` for things that can cause errors or data loss; `note` for tips; `troubleshooting` at the end of a section for common errors.
- If a business rule affects what the user sees (volume pricing, minimum quantities), explain it in one simple sentence in the step where it shows up.

## Files

- `scripts/detect_platform.py` — detects apps and platforms in the repo (Step 1).
- `references/context.md` — which repo documentation to read and how to use it (Step 0).
- `references/web.md`, `references/javafx.md`, `references/flutter.md`, `references/manual-mode.md` — one file per driver.
- `references/spec-format.md` — `manual.yaml` format.
- `assets/javafx/`, `assets/flutter/` — helpers and example tests to copy into the project.
- `scripts/annotate.py` and `scripts/build_manual.py` (shared), `scripts/capture_web.py`, `scripts/grid.py` and `scripts/android_bounds.py` (manual mode).
