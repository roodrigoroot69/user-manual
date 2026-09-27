# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This repo **is a Claude skill**, not an application. `user-manual/` is the installable artifact; everything else (`examples/`, `package.sh`, `README.md`) exists to develop and ship it.

The skill's job: run inside *someone else's* project, walk their app's real flows, screenshot them, annotate the screenshots, and assemble a Word/PDF end-user manual in English or Spanish. So there are two audiences for any change here: the future Claude instance reading `SKILL.md`/`references/` inside a target repo, and the Python scripts it will run there.

## Architecture: a three-stage pipeline with one file contract

```
capture driver  →  build/manual/raw/<section>-<NN>.png + .json  →  annotate.py  →  build_manual.py
(per platform)                  ^^^ the contract ^^^               (shared)        (shared)
```

The **PNG + sidecar JSON contract** (documented in the `scripts/annotate.py` docstring) is the load-bearing design decision. A new platform driver is cheap precisely because it only has to emit those two files per step; annotation and document generation are reused untouched. Preserve that decoupling — do not let platform specifics leak into `annotate.py` or `build_manual.py`.

Existing drivers, all producing the same output:
- **Web** — `scripts/capture_web.py` (Playwright). The only driver where actions live in `manual.yaml` itself; it also calls `annotate()` inline, so it writes raw + annotated + manifest in one run.
- **JavaFX** — TestFX in the target project + `assets/javafx/ManualCapturer.java` copied in.
- **Flutter** — `integration_test` + `assets/flutter/*.dart` copied in.
- **Manual mode** — no driver: human screenshots, coordinates found via `scripts/grid.py` or `scripts/android_bounds.py`, JSON hand-written.

### Conventions that tie the stages together

- **Filename is the join key.** Step *N* of section `foo` in `manual.yaml` ⇔ `foo-0N.png`. Inserting a step mid-section requires renumbering in the driver too. A YAML step with no matching screenshot renders a red `[MISSING SCREENSHOT]` box in the document rather than failing.
- **Coordinates are logical px; `scale` = image px per logical px.** `density` (defaults to `scale`) independently sizes strokes and badges. Manual mode therefore uses `scale: 1` with `density: 2`–`3`.
- **`screenshots.json` is a merge-on-write manifest.** `annotate.py` replaces only the sections it just processed, which is what makes recapturing a single section (`--section <id>`) safe.
- **Drivers never abort on a missing element.** They append to the JSON's `errors[]`; `annotate.py` prints them and exits 1. Keep this — a partial capture is more useful than a crash mid-run.
- **Badges are drawn outside the highlight box**, and `crop` is expanded to never clip them.

### Bilingual output

`language: en|es` in `manual.yaml` selects the `LABELS` table in `build_manual.py` (fixed strings, month names, date format) and the Playwright `locale`. Manual *body* text is authored by the agent in the end user's language, which is independent of the skill's or codebase's language. Adding a language = one entry in `LABELS`.

## Skill-authoring rules

- `SKILL.md` is the entry point and stays short: the 6-step flow plus a routing table. Detail belongs in `references/` — the agent is told to read **only** the reference for the driver it picked. Resist growing `SKILL.md`.
- One reference per driver (`web.md`, `javafx.md`, `flutter.md`, `manual-mode.md`), plus `context.md` (what repo docs to read before proposing anything) and `spec-format.md` (the `manual.yaml` schema). A change to the YAML schema must land in `spec-format.md`, and in `web.md` if it's web-only.
- **Dependency discipline.** Shared scripts import only stdlib + `pyyaml`/`pillow`/`python-docx`; `playwright` is imported by `capture_web.py` alone. `assets/javafx/ManualCapturer.java` needs nothing beyond the JDK and JavaFX, and the Flutter helpers nothing beyond `integration_test` — they get copied into arbitrary client projects, so keep them dependency-free.
- `capture_web.py` and `grid.py` import `annotate` as a sibling module; the scripts must stay in one flat folder.
- Two non-negotiables the skill enforces on users: **never capture the client's real data** (manuals get printed and forwarded) and **always review the annotated images before building the document**. Keep these prominent in any rewrite.

## Commands

```bash
pip install pyyaml pillow python-docx                            # always
pip install playwright && python -m playwright install chromium  # web driver
brew install --cask libreoffice                                  # optional; --pdf needs soffice

./examples/web-demo/run.sh                        # end-to-end web driver check
FX=/path/to/javafx-sdk/lib ./examples/javafx-demo/run.sh   # JavaFX helper check (JDK 17+)
./package.sh                                      # → dist/user-manual.skill for claude.ai
```

Individual stages (run from a target project, `<skill>` = this repo's `user-manual/`):

```bash
python <skill>/scripts/detect_platform.py <repo-path> [--json]
python <skill>/scripts/capture_web.py manual.yaml --out build/manual [--section ID] [--headed] [--slowmo 300]
python <skill>/scripts/annotate.py build/manual/raw --out build/manual [--color "#E4572E"]
python <skill>/scripts/build_manual.py manual.yaml --build build/manual [--pdf]
python <skill>/scripts/grid.py shot.png [--step 50] [--zone x,y,w,h]   # manual mode
python <skill>/scripts/android_bounds.py "Save" "id/btnSave" "desc:Search"
```

## Verifying changes

There is no unit test suite; **the two examples are the test.** After touching a script, run `examples/web-demo/run.sh` and actually open `examples/web-demo/build/screenshots/*.png` and the generated PDF — most regressions here are visual (box offsets, clipped badges, blur not covering the redacted area) and invisible to exit codes. `examples/web-demo` is English, `examples/javafx-demo` is Spanish; between them they cover both `LABELS` tables.

Install for live iteration: `ln -s "$(pwd)/user-manual" ~/.claude/skills/user-manual` — with a symlink, repo edits take effect on the next invocation, no repackaging.

Generated output (`build/`, `dist/`, `**/raw/`, `**/screenshots/`, `*.docx`, `*.pdf`) is gitignored, as is `examples/javafx-demo/src/manual/ManualCapturer.java` — `run.sh` copies that file in from `assets/` at run time, so never commit it.

## Known gaps (stated in README; keep honest)

Web and manual mode are tested. The JavaFX helper is tested but its TestFX harness hasn't been validated in a real project; the Flutter driver is untested. Electron falls back to manual mode even though Playwright could drive it, and native mobile awaits an Appium driver. If you change status here, update the tables in both `README.md` and `SKILL.md`.
