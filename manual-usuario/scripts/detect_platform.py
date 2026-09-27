#!/usr/bin/env python3
"""Detecta las aplicaciones de un repositorio y el driver de captura recomendado.

Uso:
    python detect_platform.py [ruta_repo] [--json]

Recorre el repo (hasta 4 niveles, ignorando carpetas de build y dependencias)
y reporta cada app encontrada: ruta, plataforma, driver y referencia a leer.
Un repo puede tener varias apps (p. ej. escritorio + tablet + portal).
"""
import argparse
import json
import os
import re
from pathlib import Path

IGNORAR = {".git", "node_modules", "build", "target", "dist", ".dart_tool", "Pods",
           ".gradle", ".idea", "venv", ".venv", "__pycache__", ".next", "out", "bin",
           "obj", ".expo", "vendor", "coverage", ".openspec", "openspec"}
MAX_NIVEL = 4

DRIVERS = {
    "javafx": ("JavaFX (escritorio)", "javafx", "references/javafx.md"),
    "flutter": ("Flutter", "flutter", "references/flutter.md"),
    "web": ("Web", "web", "references/web.md"),
    "web-estatico": ("Web (HTML estático)", "web", "references/web.md"),
    "electron": ("Electron (escritorio)", "web (Playwright + Electron)", "references/web.md"),
    "android": ("Android nativo", "manual (Appium a futuro)", "references/manual.md"),
    "ios": ("iOS nativo", "manual (Appium a futuro)", "references/manual.md"),
    "react-native": ("React Native / Expo", "manual (Appium a futuro)", "references/manual.md"),
    "dotnet": ("Escritorio .NET (WPF/WinForms)", "manual (Appium a futuro)", "references/manual.md"),
    "swing": ("Java Swing (escritorio)", "manual", "references/manual.md"),
}


def leer(p, limite=200_000):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:limite]
    except OSError:
        return ""


def carpetas(raiz):
    for dirpath, dirnames, filenames in os.walk(raiz):
        nivel = len(Path(dirpath).relative_to(raiz).parts)
        dirnames[:] = [d for d in dirnames if d not in IGNORAR and not d.startswith(".")] \
            if nivel < MAX_NIVEL else []
        yield Path(dirpath), set(filenames), set(dirnames)


def detectar_en(d, files, dirs):
    """Devuelve lista de (tipo, detalle) para la carpeta d."""
    hallazgos = []

    if "pubspec.yaml" in files:
        pub = leer(d / "pubspec.yaml")
        if re.search(r"^\s*flutter:\s*$", pub, re.M) or "sdk: flutter" in pub:
            plataformas = [p for p in ("android", "ios", "web", "macos", "windows", "linux")
                           if p in dirs]
            extra = []
            if "integration_test" in pub:
                extra.append("integration_test ya configurado")
            hallazgos.append(("flutter", ", ".join(plataformas) or "sin carpetas de plataforma",
                              extra))
            return hallazgos  # android/ios dentro de Flutter no son apps nativas aparte

    build_files = [f for f in ("pom.xml", "build.gradle", "build.gradle.kts") if f in files]
    if build_files:
        txt = "".join(leer(d / f) for f in build_files)
        if "javafx" in txt.lower() or "org.openjfx" in txt:
            hallazgos.append(("javafx", ", ".join(build_files), []))
        elif "com.android.application" in txt:
            hallazgos.append(("android", ", ".join(build_files), []))
        elif "javax.swing" in txt or "swing" in txt.lower():
            hallazgos.append(("swing", ", ".join(build_files), []))

    if "package.json" in files:
        pkg = leer(d / "package.json")
        try:
            data = json.loads(pkg)
        except json.JSONDecodeError:
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "electron" in deps:
            hallazgos.append(("electron", "electron", []))
        elif "react-native" in deps or "expo" in deps:
            hallazgos.append(("react-native", "react-native/expo", []))
        else:
            fw = [f for f in ("next", "nuxt", "react", "vue", "svelte", "@angular/core",
                              "vite", "astro", "remix") if f in deps]
            if fw:
                hallazgos.append(("web", ", ".join(fw), []))

    if "manage.py" in files:
        hallazgos.append(("web", "Django", []))
    if "Gemfile" in files and "rails" in leer(d / "Gemfile"):
        hallazgos.append(("web", "Rails", []))
    if "composer.json" in files and "laravel" in leer(d / "composer.json"):
        hallazgos.append(("web", "Laravel", []))

    if any(x.endswith(".xcodeproj") for x in dirs) and "pubspec.yaml" not in files:
        hallazgos.append(("ios", "Xcode", []))

    for f in files:
        if f.endswith(".csproj"):
            txt = leer(d / f)
            if "UseWPF" in txt or "UseWindowsForms" in txt:
                hallazgos.append(("dotnet", f, []))

    # HTML estático suelto (PoC de un solo archivo, prototipos)
    if not hallazgos:
        htmls = sorted(f for f in files if f.endswith(".html"))
        if htmls and not any(t in files for t in ("package.json", "manage.py")):
            if any("<script" in leer(d / h, 50_000) for h in htmls):
                hallazgos.append(("web-estatico", ", ".join(htmls[:4]) +
                                  (" …" if len(htmls) > 4 else ""), []))
    return hallazgos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ruta", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.ruta).resolve()

    apps = []
    fxml = 0
    for d, files, dirs in carpetas(raiz):
        fxml += sum(1 for f in files if f.endswith(".fxml"))
        for tipo, detalle, extra in detectar_en(d, files, dirs):
            nombre, driver, ref = DRIVERS[tipo]
            apps.append({"ruta": str(d.relative_to(raiz)) or ".", "tipo": tipo,
                         "plataforma": nombre, "detalle": detalle, "driver": driver,
                         "referencia": ref, "notas": extra})

    # Quitar subcarpetas de una app ya detectada: android/, ios/, web/ dentro de Flutter,
    # o submódulos del mismo tipo (proyectos multi-módulo de Gradle/Maven).
    def dentro(hija, padre):
        return padre == "." and hija != "." or hija.startswith(padre.rstrip("/") + "/")
    filtradas = []
    for a in apps:
        if any(dentro(a["ruta"], b["ruta"]) and (b["tipo"] == "flutter" or b["tipo"] == a["tipo"])
               for b in filtradas):
            continue
        filtradas.append(a)
    apps = filtradas

    # Una app JavaFX sin build file en la misma carpeta (FXML sueltos)
    if fxml and not any(a["tipo"] == "javafx" for a in apps):
        apps.append({"ruta": ".", "tipo": "javafx", "plataforma": DRIVERS["javafx"][0],
                     "detalle": f"{fxml} archivos .fxml", "driver": "javafx",
                     "referencia": "references/javafx.md", "notas": []})

    if args.json:
        print(json.dumps(apps, indent=2, ensure_ascii=False))
        return

    if not apps:
        print("No se detectó ninguna app. Pregunta al usuario qué plataforma es; "
              "si no hay driver, usa el modo manual (references/manual.md).")
        return
    print(f"Apps detectadas en {raiz}:\n")
    for a in apps:
        print(f"• {a['ruta']}  →  {a['plataforma']}  ({a['detalle']})")
        print(f"    driver: {a['driver']}   leer: {a['referencia']}")
        for n in a["notas"]:
            print(f"    nota: {n}")
    if len(apps) > 1:
        print("\nHay varias apps: pregunta al usuario de cuál es el manual "
              "(o si quiere uno por app).")


if __name__ == "__main__":
    main()
