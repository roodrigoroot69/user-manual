package manual;

// Arnés mínimo sin TestFX, solo para probar ManualCapturador + annotate + build_manual.
// En un proyecto real se usa TestFX (ver manual-usuario/references/javafx.md).
import javafx.application.*; import javafx.scene.control.*; import java.nio.file.*;
public class Driver {
  static void fx(Runnable r) throws Exception { var f=new java.util.concurrent.CompletableFuture<Void>(); Platform.runLater(()->{r.run();f.complete(null);}); f.get(); Thread.sleep(300);}
  public static void main(String[] a) throws Exception {
    new Thread(()->Application.launch(DemoApp.class)).start();
    while(DemoApp.stage==null) Thread.sleep(100); Thread.sleep(800);
    var cap=new ManualCapturador(Path.of("build/crudas"),2).ocultarSiempre("#lblUsuario");
    var st=DemoApp.stage;
    cap.captura(st,"registrar-entrada-01").resaltar("#btnInventario").guardar();
    fx(()->((Button)st.getScene().lookup("#btnInventario")).fire());
    cap.captura(st,"registrar-entrada-02").resaltar("#btnNuevaEntrada").guardar();
    fx(()->((Button)st.getScene().lookup("#btnNuevaEntrada")).fire());
    cap.captura(st,"registrar-entrada-03").resaltar("#cmbProducto").resaltar("#txtCantidad").recortar("#formEntrada",4).guardar();
    fx(()->((ComboBox<?>)st.getScene().lookup("#cmbProducto")).show());
    cap.captura(st,"registrar-entrada-04").pantalla().resaltar("#cmbProducto").guardar();
    Platform.exit();
  }
}
