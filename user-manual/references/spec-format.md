# `manual.yaml` format

`manual.yaml` holds the texts and structure. For JavaFX and Flutter, actions and highlights live in the test code; for web, they go here too (see `web.md`).

```yaml
title: User manual
subtitle: Inventory and Sales System            # optional
client: Example Distributor                     # optional, cover page
version: "1.0"                                  # optional
author: Name                                    # optional
filename: desktop-manual                        # .docx name
language: en                                    # en | es — fixed labels (Step, Note, Contents…)
color: "#E4572E"                                # boxes, badges and headings

introduction: |                                 # optional
  This manual explains how to use the system…

  Each section describes a complete task.

sections:
  - id: record-stock-entry                      # screenshots are record-stock-entry-01.png…
    title: Record a stock entry
    intro: Use this every time a supplier delivers goods.
    steps:
      - text: In the left menu, click **Inventory**.
        capture: true
      - text: Click **New entry**.
        capture: true
      - text: Open the product list and pick the one that arrived.
        capture: true
      - text: Type the quantity ② you received.
        capture: {width: 4.5}                    # small crops: narrower on the page
        important: Quantities are entered in **pieces**, not boxes.
      - text: Click **Save**. A confirmation message will appear.
        capture: true
        note: Stock is updated immediately.
      - text: Done. You can close the window.    # step without a screenshot: omit `capture`
    troubleshooting:
      - "If the product isn't in the list, add it first in **Catalog**."
```

Write every text in the end user's language, and set `language` to match.

## Step fields

| Field | What it does |
|---|---|
| `text` | Instruction for the reader. `**x**` = bold, `*x*` = italic. You can refer to screenshot badges with ① ② ③. |
| `capture` | `true` or an object (`{width: 4.5}`, in inches; default 6). Omit it for a step without an image. For web, the object also takes `highlight`, `crop`, etc. |
| `note` | Tip in a gray box. |
| `important` | Warning in a colored box. |
| `actions` | Web only: actions to run before the screenshot. |

Step N in the YAML maps to `<id>-NN.png` (01, 02…), so if you add or remove a step in the middle, renumber the screenshots in the driver too.
