// Copiar a integration_test/manual/manual_capturador.dart
//
// Toma capturas desde una prueba de integration_test y guarda, por cada una,
// las cajas a resaltar/difuminar/recortar. Las imágenes y los metadatos llegan
// a la computadora mediante test_driver/manual_driver.dart.
import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

class ManualCapturador {
  ManualCapturador(this.binding, {this.ocultarSiempre = const []});

  final IntegrationTestWidgetsFlutterBinding binding;

  /// Finders a difuminar en todas las capturas (nombre del vendedor, teléfono…).
  final List<Finder> ocultarSiempre;

  /// Metadatos acumulados de todas las capturas; viajan al host en reportData.
  static final Map<String, Object?> _metadatos = {};
  static bool _superficieConvertida = false;

  /// [nombre] = "<seccion-id>-<NN>", p. ej. "levantar-pedido-03".
  CapturaFlutter captura(WidgetTester tester, String nombre) =>
      CapturaFlutter._(this, tester, nombre);
}

class CapturaFlutter {
  CapturaFlutter._(this._c, this._tester, this._nombre)
      : _ocultar = [..._c.ocultarSiempre];

  final ManualCapturador _c;
  final WidgetTester _tester;
  final String _nombre;
  final List<(Finder, String?)> _resaltar = [];
  final List<Finder> _ocultar;
  Finder? _recorte;
  double _margen = 0;

  /// Recuadro numerado (1, 2, 3… en orden). `numero: false` = recuadro sin número.
  CapturaFlutter resaltar(Finder f, {String? etiqueta, bool numero = true}) {
    _resaltar.add((f, numero ? (etiqueta ?? '${_resaltar.length + 1}') : null));
    return this;
  }

  CapturaFlutter ocultar(Finder f) {
    _ocultar.add(f);
    return this;
  }

  CapturaFlutter recortar(Finder f, {double margen = 12}) {
    _recorte = f;
    _margen = margen;
    return this;
  }

  Future<void> guardar() async {
    await _tester.pumpAndSettle();
    final errores = <String>[];

    Map<String, Object?> caja(Rect r, {double m = 0, Object? etiqueta = _sinEtiqueta}) => {
          'x': r.left - m,
          'y': r.top - m,
          'w': r.width + 2 * m,
          'h': r.height + 2 * m,
          if (!identical(etiqueta, _sinEtiqueta)) 'etiqueta': etiqueta,
        };

    Rect? rectDe(Finder f, String uso) {
      final elementos = f.evaluate();
      if (elementos.isEmpty) {
        errores.add("$uso '$f': no se encontró");
        return null;
      }
      return _rectDeElemento(elementos.first);
    }

    final resaltar = <Map<String, Object?>>[];
    for (final (f, etiqueta) in _resaltar) {
      final r = rectDe(f, 'resaltar');
      if (r != null) resaltar.add(caja(r, etiqueta: etiqueta));
    }

    final ocultar = <Map<String, Object?>>[];
    for (final f in _ocultar) {
      for (final e in f.evaluate()) {
        final r = _rectDeElemento(e);
        if (r != null) ocultar.add(caja(r));
      }
    }

    Map<String, Object?>? recorte;
    if (_recorte != null) {
      final r = rectDe(_recorte!, 'recortar');
      if (r != null) recorte = caja(r, m: _margen);
    }

    // En Android hay que convertir la superficie de Flutter a imagen una sola vez.
    if (!kIsWeb &&
        defaultTargetPlatform == TargetPlatform.android &&
        !ManualCapturador._superficieConvertida) {
      await _c.binding.convertFlutterSurfaceToImage();
      ManualCapturador._superficieConvertida = true;
      await _tester.pumpAndSettle();
    }

    await _c.binding.takeScreenshot(_nombre);

    ManualCapturador._metadatos[_nombre] = {
      // la captura está en px físicos; las cajas en px lógicos
      'escala': _tester.view.devicePixelRatio,
      'resaltar': resaltar,
      'ocultar': ocultar,
      'recortar': recorte,
      'errores': errores,
    };
    _c.binding.reportData = {'manual': ManualCapturador._metadatos};
  }

  static Rect? _rectDeElemento(Element e) {
    final ro = e.renderObject;
    if (ro is! RenderBox || !ro.hasSize || !ro.attached) return null;
    return ro.localToGlobal(Offset.zero) & ro.size;
  }
}

const Object _sinEtiqueta = Object();
