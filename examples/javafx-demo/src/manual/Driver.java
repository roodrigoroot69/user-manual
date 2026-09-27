package manual;

// Minimal harness without TestFX, only to exercise ManualCapturer + annotate + build_manual.
// In a real project, use TestFX (see user-manual/references/javafx.md).
import javafx.application.*; import javafx.scene.control.*; import java.nio.file.*;

public class Driver {
  static void fx(Runnable r) throws Exception {
    var f = new java.util.concurrent.CompletableFuture<Void>();
    Platform.runLater(() -> { r.run(); f.complete(null); });
    f.get(); Thread.sleep(300);
  }

  public static void main(String[] a) throws Exception {
    new Thread(() -> Application.launch(DemoApp.class)).start();
    while (DemoApp.stage == null) Thread.sleep(100);
    Thread.sleep(800);
    var cap = new ManualCapturer(Path.of("build/raw"), 2).alwaysRedact("#lblUsuario");
    var st = DemoApp.stage;
    cap.capture(st, "registrar-entrada-01").highlight("#btnInventario").save();
    fx(() -> ((Button) st.getScene().lookup("#btnInventario")).fire());
    cap.capture(st, "registrar-entrada-02").highlight("#btnNuevaEntrada").save();
    fx(() -> ((Button) st.getScene().lookup("#btnNuevaEntrada")).fire());
    cap.capture(st, "registrar-entrada-03").highlight("#cmbProducto").highlight("#txtCantidad")
       .crop("#formEntrada", 4).save();
    fx(() -> ((ComboBox<?>) st.getScene().lookup("#cmbProducto")).show());
    cap.capture(st, "registrar-entrada-04").screen().highlight("#cmbProducto").save();
    Platform.exit();
  }
}
