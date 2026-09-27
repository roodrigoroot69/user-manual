# Formato de `manual.yaml`

`manual.yaml` contiene los textos y la estructura. En JavaFX, las acciones y los resaltados viven en la prueba Java; en web, van aquí mismo (ver `web.md`).

```yaml
titulo: Manual de usuario
subtitulo: Sistema de Inventario y Ventas        # opcional
cliente: Distribuidora Ejemplo                   # opcional, portada
version: "1.0"                                   # opcional
autor: Nombre                                    # opcional
archivo: manual-escritorio                       # nombre del .docx
color: "#E4572E"                                 # recuadros, números y títulos

introduccion: |                                  # opcional
  Este manual explica cómo usar el sistema…

  Cada sección describe una tarea completa.

secciones:
  - id: registrar-entrada                        # las capturas se llaman registrar-entrada-01.png…
    titulo: Registrar una entrada de mercancía
    intro: Úsalo cada vez que llegue mercancía de un proveedor.
    pasos:
      - texto: En el menú de la izquierda, da clic en **Inventario**.
        captura: true
      - texto: Da clic en **Nueva entrada**.
        captura: true
      - texto: Abre la lista de productos y elige el que llegó.
        captura: true
      - texto: Escribe la cantidad ② que recibiste.
        captura: {ancho: 4.5}                     # recortes pequeños: menos ancho en la hoja
        importante: La cantidad se captura en **piezas**, no en cajas.
      - texto: Da clic en **Guardar**. Verás un mensaje de confirmación.
        captura: true
        nota: La existencia se actualiza de inmediato.
      - texto: Listo. Ya puedes cerrar la ventana.   # paso sin captura: omite `captura`
    problemas:
      - "Si el producto no aparece en la lista, primero dalo de alta en **Catálogo**."
```

## Campos de un paso

| Campo | Qué hace |
|---|---|
| `texto` | Instrucción para el lector. `**x**` = negritas, `*x*` = cursiva. Puedes referir los números de la captura con ① ② ③. |
| `captura` | `true` o un objeto (`{ancho: 4.5}`, en pulgadas; por defecto 6). Omítelo para un paso sin imagen. En web, el objeto también lleva `resaltar`, `recortar`, etc. |
| `nota` | Consejo en un recuadro gris. |
| `importante` | Advertencia en un recuadro de color. |
| `acciones` | Solo web: acciones a ejecutar antes de la captura. |

El paso N del YAML corresponde a `<id>-NN.png` (01, 02…), así que si agregas o quitas un paso en medio, renumera también las capturas en el driver.
