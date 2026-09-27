// Copy to test_driver/manual_driver.dart
//
// Runs on the host machine: receives screenshots and metadata from the
// device/emulator and writes them to build/manual/raw (or MANUAL_OUTPUT).
import 'dart:convert';
import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

Future<void> main() async {
  final output = Directory(Platform.environment['MANUAL_OUTPUT'] ?? 'build/manual/raw');
  await output.create(recursive: true);

  await integrationDriver(
    onScreenshot: (String name, List<int> bytes, [Map<String, Object?>? args]) async {
      await File('${output.path}/$name.png').writeAsBytes(bytes);
      return true;
    },
    responseDataCallback: (Map<String, dynamic>? data) async {
      final meta = (data?['manual'] as Map?) ?? const {};
      for (final entry in meta.entries) {
        await File('${output.path}/${entry.key}.json').writeAsString(jsonEncode(entry.value));
      }
      stdout.writeln('Manual: ${meta.length} screenshots with metadata in ${output.path}');
    },
  );
}
