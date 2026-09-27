# Driver web (Playwright)

Para apps web (por ejemplo, un portal en Django o Next.js). A diferencia del driver JavaFX, aquí las acciones se escriben en el mismo `manual.yaml` (campo `acciones` de cada paso) y `scripts/capture_web.py` las ejecuta y anota.

```bash
pip install playwright pyyaml pillow python-docx
python -m playwright install chromium
MANUAL_USER=demo MANUAL_PASS=... python scripts/capture_web.py manual.yaml --out build/manual
```

Opciones: `--seccion <id>` (repetible) para recapturar solo una sección, `--headed` para ver el navegador y `--slowmo 300` para depurar.

## Campos extra del YAML para web

Nivel superior: `base_url`, `viewport`, `escala`, `login` (url, acciones, esperar) y `ocultar` (selectores difuminados en todas las capturas). Credenciales siempre como `${VARIABLE}` de entorno.

En cada paso, `acciones` es una lista de acciones y `captura` puede llevar `resaltar`, `ocultar`, `recortar` y `pagina_completa`.

| Acción | Ejemplo |
|---|---|
| `goto` | `goto: /pedidos/` |
| `click` | `click: "text=Guardar"` |
| `fill` | `fill: {selector: "#id_nombre", valor: "Juan"}` |
| `select` | `select: {selector: "#id_ruta", valor: "Ruta 3"}` |
| `check` / `uncheck` | `check: "#id_activo"` |
| `press` | `press: {selector: "#buscar", tecla: "Enter"}` |
| `hover` | `hover: "#menu-reportes"` |
| `esperar` | `esperar: ".resultados"` o `esperar: 500` |
| `scroll` | `scroll: "#totales"` |
| `js` | `js: "..."` (último recurso) |

`resaltar` acepta selectores o `{selector, etiqueta}` (`etiqueta: false` = sin número). `recortar` acepta `{selector, margen}` o `{x, y, ancho, alto}`.

## HTML estático (prototipos de un solo archivo)

No hace falta servidor: usa `base_url: file:///ruta/absoluta/a/la/carpeta` y `goto: distribuidora.html`. Si la página usa APIs externas (imágenes, fetch), sírvela con `python -m http.server` para evitar bloqueos de `file://`.

## Consejos

- Selectores estables: `#id`, `[name=...]`, `[data-testid=...]` o `text=...`. Evita clases de Tailwind.
- Con HTMX o fetch, agrega un `esperar` con el selector del contenido nuevo después del clic.
- Datos de demo: `flush` + `loaddata` (Django) antes de cada corrida, para que sea reproducible.
