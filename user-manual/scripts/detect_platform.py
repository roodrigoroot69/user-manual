#!/usr/bin/env python3
"""Detect the apps in a repository and the recommended capture driver for each.

Usage:
    python detect_platform.py [repo_path] [--json]

Walks the repo (up to 4 levels, skipping build and dependency folders) and
reports every app found: path, platform, driver and the reference to read.
A repo can contain several apps (e.g. desktop + tablet + web portal).
"""
import argparse
import json
import os
import re
from pathlib import Path

SKIP = {".git", "node_modules", "build", "target", "dist", ".dart_tool", "Pods",
        ".gradle", ".idea", "venv", ".venv", "__pycache__", ".next", "out", "bin",
        "obj", ".expo", "vendor", "coverage", "openspec"}
MAX_DEPTH = 4

DRIVERS = {
    "javafx": ("JavaFX (desktop)", "javafx", "references/javafx.md"),
    "flutter": ("Flutter", "flutter", "references/flutter.md"),
    "web": ("Web", "web", "references/web.md"),
    "static-web": ("Web (static HTML)", "web", "references/web.md"),
    "electron": ("Electron (desktop)", "manual (Playwright's Electron support not wired yet)",
                 "references/manual-mode.md"),
    "android": ("Native Android", "manual (Appium in the future)", "references/manual-mode.md"),
    "ios": ("Native iOS", "manual (Appium in the future)", "references/manual-mode.md"),
    "react-native": ("React Native / Expo", "manual (Appium in the future)",
                     "references/manual-mode.md"),
    "dotnet": (".NET desktop (WPF/WinForms)", "manual (Appium in the future)",
               "references/manual-mode.md"),
    "swing": ("Java Swing (desktop)", "manual", "references/manual-mode.md"),
}


def read(p, limit=200_000):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")] \
            if depth < MAX_DEPTH else []
        yield Path(dirpath), set(filenames), set(dirnames)


def detect_in(d, files, dirs):
    """Return a list of (kind, detail, notes) for folder d."""
    found = []

    if "pubspec.yaml" in files:
        pub = read(d / "pubspec.yaml")
        if re.search(r"^\s*flutter:\s*$", pub, re.M) or "sdk: flutter" in pub:
            platforms = [p for p in ("android", "ios", "web", "macos", "windows", "linux")
                         if p in dirs]
            notes = ["integration_test already configured"] if "integration_test" in pub else []
            found.append(("flutter", ", ".join(platforms) or "no platform folders", notes))
            return found  # android/ios inside Flutter are not separate native apps

    build_files = [f for f in ("pom.xml", "build.gradle", "build.gradle.kts") if f in files]
    if build_files:
        txt = "".join(read(d / f) for f in build_files)
        if "javafx" in txt.lower() or "org.openjfx" in txt:
            found.append(("javafx", ", ".join(build_files), []))
        elif "com.android.application" in txt:
            found.append(("android", ", ".join(build_files), []))
        elif "swing" in txt.lower():
            found.append(("swing", ", ".join(build_files), []))

    if "package.json" in files:
        try:
            data = json.loads(read(d / "package.json"))
        except json.JSONDecodeError:
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "electron" in deps:
            found.append(("electron", "electron", []))
        elif "react-native" in deps or "expo" in deps:
            found.append(("react-native", "react-native/expo", []))
        else:
            fw = [f for f in ("next", "nuxt", "react", "vue", "svelte", "@angular/core",
                              "vite", "astro", "remix") if f in deps]
            if fw:
                found.append(("web", ", ".join(fw), []))

    if "manage.py" in files:
        found.append(("web", "Django", []))
    if "Gemfile" in files and "rails" in read(d / "Gemfile"):
        found.append(("web", "Rails", []))
    if "composer.json" in files and "laravel" in read(d / "composer.json"):
        found.append(("web", "Laravel", []))

    if any(x.endswith(".xcodeproj") for x in dirs):
        found.append(("ios", "Xcode", []))

    for f in files:
        if f.endswith(".csproj"):
            txt = read(d / f)
            if "UseWPF" in txt or "UseWindowsForms" in txt:
                found.append(("dotnet", f, []))

    # loose static HTML (single-file PoCs, prototypes)
    if not found:
        htmls = sorted(f for f in files if f.endswith(".html"))
        if htmls and any("<script" in read(d / h, 50_000) for h in htmls):
            found.append(("static-web", ", ".join(htmls[:4]) + (" …" if len(htmls) > 4 else ""), []))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.path).resolve()

    apps, fxml = [], 0
    for d, files, dirs in walk(root):
        fxml += sum(1 for f in files if f.endswith(".fxml"))
        for kind, detail, notes in detect_in(d, files, dirs):
            name, driver, ref = DRIVERS[kind]
            apps.append({"path": str(d.relative_to(root)) or ".", "kind": kind,
                         "platform": name, "detail": detail, "driver": driver,
                         "reference": ref, "notes": notes})

    # Drop subfolders of an app already found: android/, ios/, web/ inside Flutter,
    # or same-kind submodules (multi-module Gradle/Maven projects).
    def inside(child, parent):
        return (parent == "." and child != ".") or child.startswith(parent.rstrip("/") + "/")
    kept = []
    for a in apps:
        if any(inside(a["path"], b["path"]) and b["kind"] in ("flutter", a["kind"]) for b in kept):
            continue
        kept.append(a)
    apps = kept

    # JavaFX app without a build file next to it (loose FXML)
    if fxml and not any(a["kind"] == "javafx" for a in apps):
        apps.append({"path": ".", "kind": "javafx", "platform": DRIVERS["javafx"][0],
                     "detail": f"{fxml} .fxml files", "driver": "javafx",
                     "reference": "references/javafx.md", "notes": []})

    if args.json:
        print(json.dumps(apps, indent=2, ensure_ascii=False))
        return
    if not apps:
        print("No app detected. Ask the user which platform it is; "
              "if there's no driver for it, use manual mode (references/manual-mode.md).")
        return
    print(f"Apps detected in {root}:\n")
    for a in apps:
        print(f"• {a['path']}  →  {a['platform']}  ({a['detail']})")
        print(f"    driver: {a['driver']}   read: {a['reference']}")
        for n in a["notes"]:
            print(f"    note: {n}")
    if len(apps) > 1:
        print("\nSeveral apps found: ask the user which one the manual is for "
              "(or whether they want one per app).")


if __name__ == "__main__":
    main()
