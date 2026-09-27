# manual-usuario — skill para generar manuales de usuario

Skill de Claude que genera manuales de usuario para clientes finales a partir de la aplicación real: recorre los flujos, toma capturas, las anota (recuadros numerados, datos difuminados, recortes) y arma un Word/PDF con pasos en lenguaje sencillo.

## Plataformas

| Plataforma | Driver | Se regenera solo | Estado |
|---|---|---|---|
| Web (Django, Next.js, HTML estático…) | Playwright | Sí | Probado |
| Escritorio JavaFX | TestFX + `ManualCapturador.java` | Sí | Helper probado; la prueba con TestFX falta validarla en un proyecto real |
| Flutter (tablet, móvil) | `integration_test` + `manual_capturador.dart` | Sí | Sin probar |
| Android/iOS nativo, React Native, .NET, Swing, otras | Modo manual (cuadrícula / `adb`) | No | Probado |

Pendientes a futuro: soporte de Electron en `capture_web.py` (Playwright lo permite) y un driver Appium para plataformas nativas.

## Estructura

```
manual-usuario/          la skill (lo que se instala)
  SKILL.md               flujo: contexto → plataforma → datos demo → YAML → captura → revisión → documento
  references/            una guía por driver + contexto del repo + formato de manual.yaml
  scripts/               detect_platform, capture_web, annotate, build_manual, grid, android_bounds
  assets/javafx|flutter  helpers y pruebas de ejemplo para copiar al proyecto
ejemplos/
  web-demo/              app HTML de prueba + manual.yaml + correr.sh
  javafx-demo/           app JavaFX de prueba + arnés + manual.yaml + correr.sh
empaquetar.sh            genera dist/manual-usuario.skill
```

## Instalar

**Claude Code** (personal, en todos los proyectos):
```bash
ln -s "$(pwd)/manual-usuario" ~/.claude/skills/manual-usuario
```
Con enlace simbólico, los cambios en el repo se reflejan al instante. Para un solo proyecto, cópiala a `<proyecto>/.claude/skills/`.

**claude.ai:** `./empaquetar.sh` y sube `dist/manual-usuario.skill` en Ajustes → Capacidades.

## Dependencias (en la máquina donde se genera el manual)

```bash
pip install pyyaml pillow python-docx          # siempre
pip install playwright && python -m playwright install chromium   # driver web
brew install --cask libreoffice                # opcional, para PDF
```

## Uso

En Claude Code, dentro del proyecto: *"Hazme el manual de usuario del módulo de inventario"*. La skill revisa el contexto del repo (CLAUDE.md, OpenSpec, docs), detecta la plataforma, propone las secciones y, tras confirmarlas, captura y genera el documento.

## Probar los ejemplos

```bash
./ejemplos/web-demo/correr.sh
FX=/ruta/javafx-sdk/lib ./ejemplos/javafx-demo/correr.sh
```
