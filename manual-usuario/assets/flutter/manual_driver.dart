// Copiar a test_driver/manual_driver.dart
//
// Corre en la computadora: recibe capturas y metadatos del dispositivo/emulador
// y los escribe en build/manual/crudas (o MANUAL_SALIDA).
import 'dart:convert';
import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

Future<void> main() async {
  final salida = Directory(Platform.environment['MANUAL_SALIDA'] ?? 'build/manual/crudas');
  await salida.create(recursive: true);

  await integrationDriver(
    onScreenshot: (String nombre, List<int> bytes, [Map<String, Object?>? args]) async {
      await File('${salida.path}/$nombre.png').writeAsBytes(bytes);
      return true;
    },
    responseDataCallback: (Map<String, dynamic>? datos) async {
      final meta = (datos?['manual'] as Map?) ?? const {};
      for (final entrada in meta.entries) {
        await File('${salida.path}/${entrada.key}.json')
            .writeAsString(jsonEncode(entrada.value));
      }
      stdout.writeln('Manual: ${meta.length} capturas con metadatos en ${salida.path}');
    },
  );
}
