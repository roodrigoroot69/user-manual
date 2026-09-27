---
name: manual-usuario
description: Genera manuales de usuario para clientes finales a partir de la aplicación real. Recorre los flujos automáticamente, toma capturas de pantalla, las anota (recuadros numerados, datos difuminados, recortes) y arma un Word/PDF con pasos en lenguaje sencillo. Funciona con cualquier plataforma, ya que detecta el tipo de app del repositorio y usa el driver adecuado (web con Playwright, escritorio JavaFX con TestFX, tablet y móvil con Flutter) o un modo manual para el resto (Android/iOS nativo, .NET, etc.). Úsala siempre que el usuario pida un manual de usuario, guía de uso, instructivo, tutorial paso a paso, documentación para el cliente o material de capacitación, o quiera actualizar un manual después de cambios en la interfaz, aunque no mencione capturas.
---

# Manual de usuario automático

La skill tiene tres piezas desacopladas:

1. **Driver de captura** (depende de la tecnología de la app): recorre los flujos y deja, por cada paso, una captura cruda `<seccion>-<NN>.png` más un `<seccion>-<NN>.json` con las cajas a resaltar, difuminar o recortar.
2. **`scripts/annotate.py`** (común): dibuja recuadros y números, difumina y recorta.
3. **`scripts/build_manual.py`** (común): arma el Word/PDF con los textos de `manual.yaml` y las capturas anotadas.

Así, cuando la interfaz cambia, se vuelve a correr el driver y el manual se regenera solo.

## Paso 0 — Reunir contexto del proyecto

Antes de proponer nada, lee lo que el equipo ya escribió sobre el sistema. Esto evita adivinar nombres de pantallas, reglas de negocio y vocabulario del cliente. Sigue `references/contexto.md`: ahí está qué buscar (CLAUDE.md, AGENTS.md, OpenSpec, grafos de código como codegraph, docs en Markdown, FXML) y en qué orden.

Resultado de este paso: un resumen breve de roles de usuario, módulos y vocabulario del negocio (cómo le dice el cliente a cada cosa), además de la lista propuesta de secciones del manual organizada por **tarea** ("Registrar una entrada de mercancía"), no por pantalla. Confírmala con el usuario antes de capturar.

## Paso 1 — Detectar la plataforma y elegir el driver

Corre la detección sobre el repositorio:

```bash
python scripts/detect_platform.py <ruta-del-repo>
```

Reporta cada app que encuentra (un repo puede tener varias: escritorio, tablet y portal), con su driver recomendado y la referencia que debes leer. Lee **solo** la referencia del driver que vas a usar:

| Plataforma | Driver | Referencia | Se regenera solo |
|---|---|---|---|
| Web (Django, Next.js, HTML estático, etc.) | Playwright (`scripts/capture_web.py`) | `references/web.md` | Sí |
| Escritorio JavaFX | TestFX + `assets/javafx/` | `references/javafx.md` | Sí |
| Flutter (tablet, móvil) | `integration_test` + `assets/flutter/` | `references/flutter.md` | Sí |
| Android/iOS nativo, React Native, .NET, Swing, otras | Modo manual (`scripts/grid.py`, `scripts/android_bounds.py`) | `references/manual.md` | No |

Cómo decidir:
- **Varias apps detectadas:** pregunta de cuál es el manual. Cada app lleva su propio `manual.yaml` y su carpeta de salida (`docs/manual/<app>/manual.yaml` → `build/manual/<app>/`), así que se pueden hacer uno por uno con el mismo estilo visual.
- **Una app con varias plataformas** (Flutter con android/ios/web): pregunta en qué dispositivo la usará el cliente y captura en ese.
- **Nada detectado o la detección no coincide con lo que dice el usuario:** confía en el usuario. Si su plataforma no tiene driver, usa el modo manual.
- **El usuario pide ir rápido o no puede correr la app** (no tiene el emulador, la app es de un tercero): modo manual con las capturas que te pase.

Para una plataforma nueva que se vaya a documentar seguido, conviene escribir un driver: solo tiene que producir `<seccion>-<NN>.png` + `.json` en el formato del docstring de `scripts/annotate.py`. Todo lo demás se reutiliza.

## Paso 2 — Datos de demostración

Las capturas muestran lo que haya en la base de datos. Nunca uses datos reales del cliente: el manual se imprime y se reenvía. Prepara una base de demo con datos creíbles del giro y haz que el driver arranque siempre desde esa copia limpia, para que las capturas sean reproducibles. Los detalles por tecnología están en cada referencia.

## Paso 3 — Escribir `manual.yaml`

Contiene los textos del manual y la estructura de secciones y pasos (`references/formato-spec.md`). El número de paso en el YAML es el `NN` del nombre de la captura: `registrar-entrada` paso 3 corresponde a `registrar-entrada-03.png`.

## Paso 4 — Capturar y anotar

Corre el driver (ver su referencia) y luego:

```bash
python scripts/annotate.py build/manual/crudas --out build/manual
```

El driver web ya anota solo. Los drivers no se detienen si un elemento no existe: registran el error en el JSON y `annotate.py` lo reporta al final.

## Paso 5 — Revisar las capturas (no te saltes esto)

Mira las imágenes de `build/manual/capturas/`. Verifica que:
- La pantalla es la correcta (no un error, un diálogo inesperado o una carga a medias).
- Los recuadros caen sobre el elemento correcto y los números no tapan texto importante.
- No hay datos sensibles visibles.
- El texto del paso describe lo que realmente se ve.

Corrige y recaptura solo la sección afectada.

## Paso 6 — Generar el documento

```bash
python scripts/build_manual.py manual.yaml --build build/manual --pdf
```

Convierte el PDF a imágenes (`pdftoppm -r 60`) y revisa algunas páginas antes de entregar. Si un paso del YAML no tiene captura, el documento muestra un recuadro rojo `[FALTA CAPTURA]` y el script lo reporta.

## Cómo redactar para el usuario final

El lector no es técnico y probablemente tendrá el manual abierto junto al sistema:

- Segunda persona e imperativo amable: "Da clic en **Guardar**." No "El usuario deberá…".
- Nombra botones y menús exactamente como aparecen en pantalla, en negritas.
- Usa el vocabulario del cliente que encontraste en el Paso 0 (si en el negocio le dicen "mayoreo" o "empaque", úsalo tal cual).
- Una acción por paso, y di qué va a pasar: "Aparecerá la lista de productos."
- Nada de jerga técnica: nada de "modal", "sincronizar la cola", "registro", "query", "dropdown" (sí "lista desplegable" o "ventana").
- `importante` para lo que puede causar errores o pérdida de datos; `nota` para consejos; `problemas` al final de la sección para los errores frecuentes.
- Si una regla de negocio afecta lo que el usuario ve (precios por volumen, cantidades mínimas), explícala en una frase simple en el paso donde aparece.

## Archivos

- `scripts/detect_platform.py` — detecta apps y plataformas del repo (Paso 1).
- `references/contexto.md` — qué documentación del repo leer y cómo usarla (Paso 0).
- `references/web.md`, `references/javafx.md`, `references/flutter.md`, `references/manual.md` — un archivo por driver.
- `references/formato-spec.md` — formato de `manual.yaml`.
- `assets/javafx/`, `assets/flutter/` — helpers y pruebas de ejemplo para copiar al proyecto.
- `scripts/annotate.py` (común), `scripts/build_manual.py` (común), `scripts/capture_web.py`, `scripts/grid.py` y `scripts/android_bounds.py` (modo manual).
