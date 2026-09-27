# Manual mode (any platform)

For when there's no automatic driver: native Android or iOS apps, React Native, Electron, .NET or Swing desktop, an app you don't control, or just to get it done quickly. The user takes the screenshots (or you do, if you have access to the tool); you place the boxes and the rest of the flow is the same.

Unlike the drivers, this **does not regenerate itself** when the UI changes. Tell the user if the manual will need frequent updates.

## 1. Get the screenshots

Ask for or take one screenshot per step in `manual.yaml` and save it in `build/manual/raw/` as `<section-id>-<NN>.png`. If the user gives you files with other names, rename them following the step order, and confirm with them if unsure.

Ways to capture by platform (all at full resolution, never downscaled):

| Platform | Command |
|---|---|
| Android (device or emulator) | `adb exec-out screencap -p > name.png` |
| iOS simulator | `xcrun simctl io booted screenshot name.png` |
| macOS window | `screencapture -o -w name.png` (click the window; `-o` removes the shadow) |
| Windows | Win+Shift+S → window snip, or the Snipping Tool |

Use demo data, same as with the drivers. If a screenshot contains real data, mark it for redaction.

## 2. Locate the elements

**Native Android or React Native:** don't estimate. With the app on the screenshot's screen, run:
```bash
python scripts/android_bounds.py "Save" "id/btnSave" "desc:Search"
```
It returns exact boxes in the same px as `screencap`. Capture and locate without changing screens between the two commands.

**Any other platform:** generate a grid and read it:
```bash
python scripts/grid.py build/manual/raw/take-order-03.png
```
Open the resulting image and locate each element by the grid-line coordinates. To refine (especially for small buttons), zoom in on the area:
```bash
python scripts/grid.py build/manual/raw/take-order-03.png --zone 600,280,300,150
```
Grid labels are always in px of the original image, including in the zoomed view.

## 3. Write the JSON

Next to each PNG, a `<section-id>-<NN>.json` with coordinates in **image px**, so `scale` is 1. Use `density` so boxes and badges come out the right size: 2 for Retina screenshots or modern phones/tablets, 1 for regular monitors. Rule of thumb: if the image is wider than ~1600 px for a regular screen, it's 2 (phones are usually 3).

```json
{
  "scale": 1,
  "density": 2,
  "highlight": [
    {"x": 651, "y": 309, "w": 142, "h": 49, "label": "1"},
    {"x": 120, "y": 80, "w": 300, "h": 40, "label": null}
  ],
  "redact": [{"x": 1385, "y": 18, "w": 400, "h": 40}],
  "crop": {"x": 480, "y": 100, "w": 700, "h": 300},
  "errors": []
}
```

`label: null` = box without a badge. `crop` and `redact` can be empty (`null` / `[]`). A step with nothing to highlight can skip the JSON: the image is used as-is.

## 4. Annotate and verify

```bash
python scripts/annotate.py build/manual/raw --out build/manual
```

Then **look at every annotated image**. If a box is off, fix the JSON and annotate again; it's cheap. Pay special attention to sensitive data being fully covered by the blur.

Then run `build_manual.py` as usual.
