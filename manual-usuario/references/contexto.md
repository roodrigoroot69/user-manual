# Reunir contexto del proyecto

El objetivo es entender **qué hace el usuario final y cómo lo llama el negocio**, no la arquitectura. Lee en este orden y detente cuando ya tengas lo necesario. En repos grandes, lista primero y lee de forma selectiva.

## 1. Instrucciones para agentes

```bash
ls -a CLAUDE.md AGENTS.md .claude/ .cursorrules .github/copilot-instructions.md 2>/dev/null
find . -name "CLAUDE.md" -not -path "*/node_modules/*" -not -path "*/build/*" | head
```

`CLAUDE.md` (raíz y subcarpetas) suele tener: cómo correr la app, comandos de build y pruebas, convenciones, y a veces glosario del negocio. También revisa `.claude/commands/` y `.claude/skills/` por si ya hay flujos definidos (por ejemplo, cómo cargar datos de demo).

## 2. Especificaciones (OpenSpec y similares)

```bash
ls openspec/ 2>/dev/null && find openspec -name "*.md" | head -50
```

- `openspec/project.md`: contexto y convenciones del proyecto.
- `openspec/specs/**/spec.md`: requisitos vigentes. Cada requisito tiene **escenarios** (CUANDO/ENTONCES o WHEN/THEN) que se traducen casi directo a pasos del manual: el CUANDO es la acción del usuario y el ENTONCES es "lo que va a ver".
- `openspec/changes/<cambio>/` (`proposal.md`, `design.md`, `tasks.md`, deltas de specs): cambios en curso. Marca qué funcionalidades aún no están terminadas (tareas sin `[x]`) y **no las documentes** como disponibles; pregunta al usuario.
- Cambios archivados (`openspec/changes/archive/`): historia; útiles para entender el porqué de una regla, no para el manual.

Si no hay OpenSpec, busca equivalentes: `docs/specs`, `docs/adr`, `requirements*.md`, historias de usuario.

## 3. Grafo o índice de código

Si existe un índice del código, úsalo para ubicar pantallas y sus controladores en vez de buscar con grep a ciegas:

```bash
ls -a .codegraph* codegraph.* .mcp.json 2>/dev/null
```

- Si `.mcp.json` declara un servidor de grafo de código (codegraph u otro) y sus herramientas están disponibles, pregúntale cosas como "qué controladores manejan la vista de entradas" o "qué métodos invoca el botón Guardar".
- Si solo hay archivos de configuración o un índice generado, léelos para ubicar módulos y puntos de entrada.

## 4. Documentación en Markdown

```bash
find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/build/*" -not -path "*/target/*" -not -path "./openspec/*" | head -80
```

Prioriza `README.md`, `docs/`, glosarios, notas de reuniones con el cliente y propuestas comerciales (dicen qué se prometió entregar y qué no incluye). Ignora changelogs de dependencias.

## 5. La interfaz misma

- JavaFX: los `*.fxml` dan la estructura de cada pantalla y los `fx:id` que usará el driver. Los textos visibles (`text="Guardar"`) o los `*.properties` de i18n dicen cómo se llaman las cosas en pantalla.
- Web: templates, rutas (`urls.py`, `app/`), y menús de navegación.

## Qué producir

Un resumen corto (para ti y para confirmar con el usuario):
- Roles de usuario y qué hace cada uno.
- Glosario: término del negocio → dónde aparece en la interfaz.
- Secciones propuestas del manual (por tarea), marcando las que dependen de funcionalidad en curso.
- Cómo arrancar la app con datos de demo (si ya existe un mecanismo).
