# Gathering project context

The goal is to understand **what the end user does and what the business calls it**, not the architecture. Read in this order and stop once you have what you need. In large repos, list first and read selectively.

## 1. Agent instructions

```bash
ls -a CLAUDE.md AGENTS.md .claude/ .cursorrules .github/copilot-instructions.md 2>/dev/null
find . -name "CLAUDE.md" -not -path "*/node_modules/*" -not -path "*/build/*" | head
```

`CLAUDE.md` (root and subfolders) usually covers how to run the app, build and test commands, conventions, and sometimes a business glossary. Also check `.claude/commands/` and `.claude/skills/` for flows that already exist (e.g. how to load demo data).

## 2. Specifications (OpenSpec and similar)

```bash
ls openspec/ 2>/dev/null && find openspec -name "*.md" | head -50
```

- `openspec/project.md`: project context and conventions.
- `openspec/specs/**/spec.md`: current requirements. Each requirement has **scenarios** (WHEN/THEN, or CUANDO/ENTONCES in Spanish specs) that translate almost directly into manual steps: the WHEN is the user's action and the THEN is "what they'll see".
- `openspec/changes/<change>/` (`proposal.md`, `design.md`, `tasks.md`, spec deltas): changes in progress. Note which features aren't finished yet (tasks without `[x]`) and **don't document them** as available; ask the user.
- Archived changes (`openspec/changes/archive/`): history; useful to understand why a rule exists, not for the manual.

Without OpenSpec, look for equivalents: `docs/specs`, `docs/adr`, `requirements*.md`, user stories.

## 3. Code graph or index

If there's a code index, use it to locate screens and their controllers instead of grepping blindly:

```bash
ls -a .codegraph* codegraph.* .mcp.json 2>/dev/null
```

- If `.mcp.json` declares a code-graph server (codegraph or another) and its tools are available, ask it things like "which controllers handle the stock entry view" or "which methods does the Save button call".
- If there are only config files or a generated index, read them to locate modules and entry points.

## 4. Markdown documentation

```bash
find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/build/*" -not -path "*/target/*" -not -path "./openspec/*" | head -80
```

Prioritize `README.md`, `docs/`, glossaries, client meeting notes and commercial proposals (they say what was promised and what's out of scope). Ignore dependency changelogs.

## 5. The UI itself

- JavaFX: `*.fxml` files give each screen's structure and the `fx:id`s the driver will use. Visible texts (`text="Save"`) or i18n `*.properties` files tell you what things are called on screen.
- Flutter: widget keys (`ValueKey`), `Text(...)` strings, `.arb` localization files.
- Web: templates, routes (`urls.py`, `app/`), navigation menus.

## What to produce

A short summary (for you, and to confirm with the user):
- User roles and what each one does.
- Glossary: business term → where it appears in the UI.
- Proposed manual sections (by task), flagging those that depend on unfinished features.
- How to start the app with demo data (if a mechanism already exists).
- The end user's language (the manual is written in it).
