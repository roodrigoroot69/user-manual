# Modo manual (cualquier plataforma)

Para cuando no hay driver automático: apps nativas de Android o iOS, React Native, escritorio .NET o Swing, una app que no controlas, o para salir del paso rápido. Las capturas las toma el usuario (o tú, si tienes acceso a la herramienta); tú marcas los recuadros y el resto del flujo es el mismo.

A diferencia de los drivers, esto **no se regenera solo** cuando cambia la interfaz. Díselo al usuario si el manual va a necesitar actualizaciones frecuentes.

## 1. Conseguir las capturas

Pide o toma una captura por paso del `manual.yaml` y guárdala en `build/manual/crudas/` con el nombre `<seccion-id>-<NN>.png`. Si el usuario te da archivos con otros nombres, renómbralos tú siguiendo el orden de los pasos, y confírmalo con él si hay dudas.

Formas de capturar según la plataforma (todas en resolución completa, sin reducir):

| Plataforma | Comando |
|---|---|
| Android (dispositivo o emulador) | `adb exec-out screencap -p > nombre.png` |
| Simulador de iOS | `xcrun simctl io booted screenshot nombre.png` |
| Ventana en macOS | `screencapture -o -w nombre.png` (clic en la ventana; `-o` quita la sombra) |
| Windows | Win+Shift+S → recorte de ventana, o la herramienta Recortes |

Usa datos de demo, igual que con los drivers. Si una captura trae datos reales, márcalos para difuminar.

## 2. Ubicar los elementos

**Android nativo o React Native:** no estimes. Con la app en la pantalla de la captura, corre:
```bash
python scripts/android_bounds.py "Guardar" "id/btnGuardar" "desc:Buscar"
```
Devuelve las cajas exactas en los mismos px que `screencap`. Captura y ubica sin cambiar de pantalla entre un comando y otro.

**Cualquier otra plataforma:** genera una cuadrícula y léela:
```bash
python scripts/grid.py build/manual/crudas/levantar-pedido-03.png
```
Abre la imagen resultante y ubica cada elemento por las coordenadas de las líneas. Para afinar (sobre todo en botones chicos), amplía la zona:
```bash
python scripts/grid.py build/manual/crudas/levantar-pedido-03.png --zona 600,280,300,150
```
Las etiquetas de la cuadrícula siempre están en px de la imagen original, también en la vista ampliada.

## 3. Escribir el JSON

Junto a cada PNG, un `<seccion-id>-<NN>.json` con coordenadas en **px de la imagen**, así que `escala` es 1. Usa `densidad` para que los recuadros y números se vean del tamaño correcto: 2 para capturas Retina, de teléfonos o tablets modernas, y 1 para monitores normales. Regla práctica: si la imagen mide más de ~1600 px de ancho para una pantalla normal, es 2 (en teléfonos, casi siempre 3).

```json
{
  "escala": 1,
  "densidad": 2,
  "resaltar": [
    {"x": 651, "y": 309, "w": 142, "h": 49, "etiqueta": "1"},
    {"x": 120, "y": 80, "w": 300, "h": 40, "etiqueta": null}
  ],
  "ocultar": [{"x": 1385, "y": 18, "w": 400, "h": 40}],
  "recortar": {"x": 480, "y": 100, "w": 700, "h": 300},
  "errores": []
}
```

`etiqueta: null` = recuadro sin número. `recortar` y `ocultar` pueden ir vacíos (`null` / `[]`). Un paso sin nada que resaltar puede no tener JSON: la imagen se usa tal cual.

## 4. Anotar y verificar

```bash
python scripts/annotate.py build/manual/crudas --out build/manual
```

Luego **mira cada imagen anotada**. Si un recuadro quedó corrido, ajusta el JSON y vuelve a anotar; es barato. Revisa especialmente que los datos sensibles queden cubiertos por completo por el difuminado.

Después, `build_manual.py` como siempre.
