# user-manual — a Claude skill for generating end-user manuals

A Claude skill that builds end-user manuals from the real application: it walks through the app's flows, takes screenshots, annotates them (numbered highlight boxes, blurred sensitive data, crops) and assembles a Word/PDF document with plain-language steps, in English or Spanish.

## Platforms

| Platform | Driver | Regenerates by itself | Status |
|---|---|---|---|
| Web (Django, Next.js, static HTML…) | Playwright | Yes | Tested |
| JavaFX desktop | TestFX + `ManualCapturer.java` | Yes | Helper tested; the TestFX harness still needs validation in a real project |
| Flutter (tablet, mobile) | `integration_test` + `manual_capturer.dart` | Yes | Untested |
| Native Android/iOS, React Native, Electron, .NET, Swing, others | Manual mode (grid / `adb`) | No | Tested |

Future work: Electron support in `capture_web.py` (Playwright supports it) and an Appium driver for native platforms.

## Layout

```
user-manual/             the skill (what gets installed)
  SKILL.md               flow: context → platform → demo data → YAML → capture → review → document
  references/            one guide per driver + repo context + manual.yaml format
  scripts/               detect_platform, capture_web, annotate, build_manual, grid, android_bounds
  assets/javafx|flutter  helpers and example tests to copy into the project
examples/
  web-demo/              demo HTML app + manual.yaml (English) + run.sh
  javafx-demo/           demo JavaFX app + harness + manual.yaml (Spanish) + run.sh
package.sh               builds dist/user-manual.skill
```

## Install

**Claude Code** (personal, all projects):
```bash
ln -s "$(pwd)/user-manual" ~/.claude/skills/user-manual
```
With a symlink, changes in the repo apply immediately. For a single project, copy it into `<project>/.claude/skills/`.

**claude.ai:** run `./package.sh` and upload `dist/user-manual.skill` under Settings → Capabilities.

## Dependencies (on the machine that generates the manual)

```bash
pip install pyyaml pillow python-docx                              # always
pip install playwright && python -m playwright install chromium    # web driver
brew install --cask libreoffice                                    # optional, for PDF
```

## Usage

In Claude Code, inside the project: *"Make the user manual for the inventory module"*. The skill reads the repo's context (CLAUDE.md, OpenSpec, docs), detects the platform, proposes the sections and, once confirmed, captures and builds the document. Manual texts are written in the end user's language (`language: en | es` in `manual.yaml`).

## Try the examples

```bash
./examples/web-demo/run.sh
FX=/path/to/javafx-sdk/lib ./examples/javafx-demo/run.sh
```
