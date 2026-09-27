# Flutter driver (tablet and mobile)

Uses `integration_test` on an emulator or real device. The test drives the app (`tester.tap`, `enterText`) and `ManualCapturer` takes the screenshot and computes each widget's exact position. `test_driver/manual_driver.dart` runs on the host machine and saves images and JSON to `build/manual/raw`.

Requires Flutter 3.10+ and Dart 3.

## 1. Dependencies

In `pubspec.yaml`:
```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
  flutter_test:
    sdk: flutter
```

## 2. Copy files

- `assets/flutter/manual_capturer.dart` → `integration_test/manual/manual_capturer.dart`
- `assets/flutter/manual_driver.dart` → `test_driver/manual_driver.dart`
- `assets/flutter/manual_test.dart.example` → `integration_test/manual_test.dart`, adapted: the app's `main` import, real keys and texts.

## 3. Selectors

- Keys are the most stable: `find.byKey(const ValueKey('btnSave'))`. If key widgets have no key, propose adding one; it's a minimal change.
- `find.text('Save')` works and also verifies the button is labeled as the manual says. If the text appears several times, use `.first` or `find.descendant(of: ..., matching: ...)`.
- `find.byType(SnackBar)` or `find.byType(AlertDialog)` for messages and dialogs.

Unlike JavaFX, Flutter dialogs, menus and bottom sheets are drawn inside the same view, so they show up in a normal screenshot with nothing special.

## 4. Demo data

- The app must be able to start in demo mode: `--dart-define=MODE=demo`, read with `const String.fromEnvironment('MODE')`. In demo mode:
  - local database (sqflite, drift, hive…) in a separate file, wiped and reseeded with sample data at startup;
  - no server sync (or pointed at a staging server with demo data);
  - hardware services mocked: Bluetooth printer, GPS, camera. A "print" that does nothing but shows the confirmation is enough for the manual.
- If the app has no demo mode, propose the minimal change to the user before capturing. Never capture against real data.

## 5. Screen size

Capture on the device the client will use, or an equivalent emulator:
- Android tablet: a Pixel Tablet AVD or one matching the real tablet's resolution.
- iPad: the closest simulator model.
- Landscape or portrait as used in the field; if the app runs in landscape, set the emulator's orientation before running.

In the YAML, portrait phone screenshots look better with `capture: {width: 3}`; landscape tablet screenshots with the default width.

## 6. Run

```bash
flutter drive \
  --driver=test_driver/manual_driver.dart \
  --target=integration_test/manual_test.dart \
  --dart-define=MODE=demo \
  -d <emulator-id>          # flutter devices

python <skill>/scripts/annotate.py build/manual/raw --out build/manual
python <skill>/scripts/build_manual.py docs/manual/tablet/manual.yaml --build build/manual --pdf
```

If you run `flutter drive` from another folder, set `MANUAL_OUTPUT` to the output path.

## 7. What to check on the first run

- That boxes match the widgets. Boxes are computed in logical px and multiplied by `devicePixelRatio`. If there's a constant offset (e.g. the status bar height on some device), check whether the app draws under the status bar (edge-to-edge) and adjust with `SafeArea` or report it to the user.
- On Android, the first screenshot converts the Flutter surface to an image (`convertFlutterSurfaceToImage`). That's expected and required.
- Flutter web and desktop have limited `takeScreenshot` support. For a Flutter web app use the web driver (Playwright); for Flutter desktop, manual mode.
