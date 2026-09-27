// Copy to integration_test/manual/manual_capturer.dart
//
// Takes screenshots from an integration_test run and records, for each one,
// the boxes to highlight/redact/crop. Images and metadata reach the host
// machine through test_driver/manual_driver.dart.
import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

class ManualCapturer {
  ManualCapturer(this.binding, {this.alwaysRedact = const []});

  final IntegrationTestWidgetsFlutterBinding binding;

  /// Finders to blur in every screenshot (sales rep name, phone number…).
  final List<Finder> alwaysRedact;

  /// Metadata for all screenshots; sent to the host through reportData.
  static final Map<String, Object?> _metadata = {};
  static bool _surfaceConverted = false;

  /// [name] = "<section-id>-<NN>", e.g. "take-order-03".
  FlutterCapture capture(WidgetTester tester, String name) =>
      FlutterCapture._(this, tester, name);
}

class FlutterCapture {
  FlutterCapture._(this._c, this._tester, this._name)
      : _redact = [..._c.alwaysRedact];

  final ManualCapturer _c;
  final WidgetTester _tester;
  final String _name;
  final List<(Finder, String?)> _highlight = [];
  final List<Finder> _redact;
  Finder? _crop;
  double _margin = 0;

  /// Numbered box (1, 2, 3… in order). `number: false` = box without a badge.
  FlutterCapture highlight(Finder f, {String? label, bool number = true}) {
    _highlight.add((f, number ? (label ?? '${_highlight.length + 1}') : null));
    return this;
  }

  FlutterCapture redact(Finder f) {
    _redact.add(f);
    return this;
  }

  FlutterCapture crop(Finder f, {double margin = 12}) {
    _crop = f;
    _margin = margin;
    return this;
  }

  Future<void> save() async {
    await _tester.pumpAndSettle();
    final errors = <String>[];

    Map<String, Object?> box(Rect r, {double m = 0}) =>
        {'x': r.left - m, 'y': r.top - m, 'w': r.width + 2 * m, 'h': r.height + 2 * m};

    Rect? rectOf(Finder f, String use) {
      final elements = f.evaluate();
      if (elements.isEmpty) {
        errors.add("$use '$f': not found");
        return null;
      }
      return _rectOfElement(elements.first);
    }

    final highlight = <Map<String, Object?>>[];
    for (final (f, label) in _highlight) {
      final r = rectOf(f, 'highlight');
      if (r != null) highlight.add({...box(r), 'label': label});
    }

    final redact = <Map<String, Object?>>[];
    for (final f in _redact) {
      for (final e in f.evaluate()) {
        final r = _rectOfElement(e);
        if (r != null) redact.add(box(r));
      }
    }

    Map<String, Object?>? crop;
    if (_crop != null) {
      final r = rectOf(_crop!, 'crop');
      if (r != null) crop = box(r, m: _margin);
    }

    // On Android the Flutter surface must be converted to an image once.
    if (!kIsWeb &&
        defaultTargetPlatform == TargetPlatform.android &&
        !ManualCapturer._surfaceConverted) {
      await _c.binding.convertFlutterSurfaceToImage();
      ManualCapturer._surfaceConverted = true;
      await _tester.pumpAndSettle();
    }

    await _c.binding.takeScreenshot(_name);

    ManualCapturer._metadata[_name] = {
      // the screenshot is in physical px; boxes are in logical px
      'scale': _tester.view.devicePixelRatio,
      'highlight': highlight,
      'redact': redact,
      'crop': crop,
      'errors': errors,
    };
    _c.binding.reportData = {'manual': ManualCapturer._metadata};
  }

  static Rect? _rectOfElement(Element e) {
    final ro = e.renderObject;
    if (ro is! RenderBox || !ro.hasSize || !ro.attached) return null;
    return ro.localToGlobal(Offset.zero) & ro.size;
  }
}
