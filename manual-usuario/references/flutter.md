# Driver Flutter (tablet y móvil)

Se usa `integration_test` sobre un emulador o dispositivo real. La prueba maneja la app (`tester.tap`, `enterText`) y `ManualCapturador` toma la captura y calcula la posición exacta de cada widget. `test_driver/manual_driver.dart` corre en la computadora y guarda las imágenes y los JSON en `build/manual/crudas`.

Requiere Flutter 3.10 o superior y Dart 3.

## 1. Dependencias

En `pubspec.yaml`:
```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
  flutter_test:
    sdk: flutter
```

## 2. Copiar archivos

- `assets/flutter/manual_capturador.dart` → `integration_test/manual/manual_capturador.dart`
- `assets/flutter/manual_driver.dart` → `test_driver/manual_driver.dart`
- `assets/flutter/manual_test.dart.ejemplo` → `integration_test/manual_test.dart`, adaptado: import del `main` de la app, keys y textos reales.

## 3. Selectores

- Lo más estable son las keys: `find.byKey(const ValueKey('btnGuardar'))`. Si los widgets clave no tienen key, propón agregarlas; es un cambio mínimo.
- `find.text('Guardar')` sirve y además verifica que el botón se llama como dice el manual. Si el texto aparece varias veces, usa `.first` o `find.descendant(of: ..., matching: ...)`.
- `find.byType(SnackBar)` o `find.byType(AlertDialog)` para mensajes y diálogos.

A diferencia de JavaFX, los diálogos, menús y hojas inferiores de Flutter se dibujan dentro de la misma vista, así que salen en la captura normal sin nada especial.

## 4. Datos de demo

- La app debe poder arrancar en modo demo: `--dart-define=MODO=demo` y leerlo con `const String.fromEnvironment('MODO')`. En modo demo:
  - base local (sqflite, drift, hive…) en un archivo aparte, borrado y recargado con datos de ejemplo al inicio;
  - sin sincronización con el servidor (o apuntando a un servidor de staging con datos demo);
  - servicios de hardware simulados: la impresora Bluetooth, el GPS, la cámara. Un "imprimir" que no hace nada pero muestra la confirmación basta para el manual.
- Si la app no tiene modo demo, propón al usuario el cambio mínimo antes de capturar. Nunca captures contra datos reales.

## 5. Tamaño de pantalla

Captura en el dispositivo que usará el cliente, o en un emulador equivalente:
- Tablet Android: un AVD tipo Pixel Tablet o uno con la resolución de la tablet real.
- iPad: el simulador del modelo más parecido.
- Horizontal o vertical según se use en campo; si la app se usa en horizontal, fija la orientación en el emulador antes de correr.

En el YAML, las capturas verticales de teléfono se ven mejor con `captura: {ancho: 3}`; las de tablet horizontal, con el ancho por defecto.

## 6. Correr

```bash
flutter drive \
  --driver=test_driver/manual_driver.dart \
  --target=integration_test/manual_test.dart \
  --dart-define=MODO=demo \
  -d <id-del-emulador>          # flutter devices

python <skill>/scripts/annotate.py build/manual/crudas --out build/manual
python <skill>/scripts/build_manual.py docs/manual/manual-tablet.yaml --build build/manual --pdf
```

Si corres `flutter drive` desde otra carpeta, define `MANUAL_SALIDA` con la ruta de salida.

## 7. Qué revisar la primera vez

- Que los recuadros coincidan con los widgets. Las cajas se calculan en px lógicos y se multiplican por `devicePixelRatio`. Si hay un desfase constante (por ejemplo, del alto de la barra de estado en algún dispositivo), revisa si la app dibuja debajo de la barra de estado (edge-to-edge) y ajusta con `SafeArea` o reportándolo al usuario.
- En Android, la primera captura convierte la superficie de Flutter a imagen (`convertFlutterSurfaceToImage`). Es normal y necesario.
- Flutter web y desktop tienen soporte limitado de `takeScreenshot`. Para una app Flutter web usa el driver web (Playwright); para Flutter desktop, el modo manual.
