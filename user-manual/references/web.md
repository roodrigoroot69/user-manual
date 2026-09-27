# Web driver (Playwright)

For web apps (e.g. a portal in Django or Next.js). Unlike the JavaFX driver, actions are written in `manual.yaml` itself (each step's `actions` field) and `scripts/capture_web.py` runs and annotates them.

```bash
pip install playwright pyyaml pillow python-docx
python -m playwright install chromium
MANUAL_USER=demo MANUAL_PASS=... python scripts/capture_web.py manual.yaml --out build/manual
```

Options: `--section <id>` (repeatable) to recapture a single section, `--headed` to watch the browser, `--slowmo 300` to debug.

## Extra YAML fields for web

Top level: `base_url`, `viewport`, `scale`, `locale` (defaults to `es-MX` when `language: es`, `en-US` otherwise), `login` (url, actions, wait) and `redact` (selectors blurred in every screenshot). Credentials always as `${VARIABLE}` from the environment.

In each step, `actions` is a list of actions, and `capture` can carry `highlight`, `redact`, `crop` and `full_page`.

| Action | Example |
|---|---|
| `goto` | `goto: /orders/` |
| `click` | `click: "text=Save"` |
| `fill` | `fill: {selector: "#id_name", value: "John"}` |
| `select` | `select: {selector: "#id_route", value: "Route 3"}` |
| `check` / `uncheck` | `check: "#id_active"` |
| `press` | `press: {selector: "#search", key: "Enter"}` |
| `hover` | `hover: "#menu-reports"` |
| `wait` | `wait: ".results"` or `wait: 500` |
| `scroll` | `scroll: "#totals"` |
| `js` | `js: "..."` (last resort) |

`highlight` takes selectors or `{selector, label}` (`label: false` = no badge). `crop` takes `{selector, margin}` or `{x, y, width, height}`.

```yaml
base_url: ${DEMO_URL}
login:
  url: /accounts/login/
  actions:
    - fill: {selector: "#id_username", value: "${MANUAL_USER}"}
    - fill: {selector: "#id_password", value: "${MANUAL_PASS}"}
    - click: "button[type=submit]"
  wait: "nav"
redact: ["#user-email"]
sections:
  - id: record-stock-entry
    title: Record a stock entry
    steps:
      - actions: [{goto: /inventory/}]
        text: In the side menu, click **Inventory**.
        capture:
          highlight: ["#menu-inventory"]
      - actions:
          - click: "text=New entry"
          - wait: "form#entry"
          - fill: {selector: "#id_quantity", value: "48"}
        text: Type the quantity you received ①.
        capture:
          highlight: ["#id_quantity"]
          crop: {selector: "form#entry", margin: 16}
```

## Static HTML (single-file prototypes)

No server needed: use `base_url: file:///absolute/path/to/folder` and `goto: app.html`. If the page uses external APIs (images, fetch), serve it with `python -m http.server` to avoid `file://` restrictions.

## Tips

- Stable selectors: `#id`, `[name=...]`, `[data-testid=...]` or `text=...`. Avoid Tailwind utility classes.
- With HTMX or fetch, add a `wait` with the new content's selector after the click.
- Demo data: `flush` + `loaddata` (Django) before every run, so it's reproducible.
