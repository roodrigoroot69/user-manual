#!/usr/bin/env python3
"""Exact element positions in a native Android (or React Native) app via adb.

Uses `uiautomator dump`, which reports each element's bounds in physical px:
the same px as `adb exec-out screencap -p`. That way manual mode doesn't have
to estimate coordinates.

Usage (with the device showing the screen being documented):
    python android_bounds.py "Save" "id/btnSave" "desc:Search"
Prints JSON ready to paste into "highlight". Criteria: exact visible text,
"id/<resource-id>" or "desc:<content-desc>".
"""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def dump():
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/manual-ui.xml"],
                   check=True, capture_output=True)
    xml = subprocess.run(["adb", "exec-out", "cat", "/sdcard/manual-ui.xml"],
                         check=True, capture_output=True).stdout
    return ET.fromstring(xml)


def matches(node, criterion):
    if criterion.startswith("id/"):
        rid = node.get("resource-id", "")
        return rid.endswith(":" + criterion) or rid == criterion[3:]
    if criterion.startswith("desc:"):
        return node.get("content-desc") == criterion[5:]
    return node.get("text") == criterion


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = dump()
    result = []
    for i, criterion in enumerate(sys.argv[1:], start=1):
        node = next((n for n in root.iter("node") if matches(n, criterion)), None)
        if node is None:
            print(f"⚠ not found: {criterion}", file=sys.stderr)
            continue
        x1, y1, x2, y2 = map(int, BOUNDS.match(node.get("bounds")).groups())
        result.append({"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1, "label": str(i)})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
