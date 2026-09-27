// Copiar a src/test/java/<paquete>/manual/ y ajustar la línea package.
package manual;

import javafx.application.Platform;
import javafx.geometry.Bounds;
import javafx.scene.Node;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.scene.SnapshotParameters;
import javafx.scene.image.PixelFormat;
import javafx.scene.image.WritableImage;
import javafx.scene.paint.Color;
import javafx.scene.transform.Transform;
import javafx.stage.Window;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * Toma capturas de ventanas JavaFX y escribe, junto a cada PNG, un JSON con las
 * cajas a resaltar/difuminar/recortar. Luego scripts/annotate.py dibuja todo.
 *
 * Uso típico dentro de una prueba TestFX:
 *
 *   cap.captura(stage, "registrar-entrada-03")
 *      .resaltar("#cmbProducto").resaltar("#txtCantidad")
 *      .ocultar("#lblUsuario")
 *      .recortar("#formEntrada", 16)
 *      .guardar();
 *
 * Los selectores son los de Node.lookup(): "#fxId", ".clase-css", "Button".
 * Con fx:id en el FXML el nodo ya tiene id; si la vista se arma en código, usar setId().
 */
public final class ManualCapturador {

    private final Path salida;
    private final double escala;
    private final List<String> ocultarSiempre = new ArrayList<>();

    /** @param salida carpeta de capturas crudas (p. ej. build/manual/crudas)
     *  @param escala 2 = nítido en impresión; en Retina se usa igual */
    public ManualCapturador(Path salida, double escala) {
        this.salida = salida;
        this.escala = escala;
        try {
            Files.createDirectories(salida);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Selectores a difuminar en todas las capturas (correo del usuario, RFC, etc.). */
    public ManualCapturador ocultarSiempre(String... selectores) {
        ocultarSiempre.addAll(List.of(selectores));
        return this;
    }

    /** @param nombre "<seccion-id>-<NN>", p. ej. "registrar-entrada-03" (NN = número de paso en manual.yaml) */
    public Captura captura(Window ventana, String nombre) {
        return new Captura(ventana, nombre);
    }

    public final class Captura {
        private final Window ventana;
        private final String nombre;
        private final List<Object[]> resaltados = new ArrayList<>(); // {selector, etiqueta}
        private final List<String> ocultos = new ArrayList<>(ocultarSiempre);
        private String recorteSel;
        private double recorteMargen;
        private boolean pantalla;

        private Captura(Window ventana, String nombre) {
            this.ventana = ventana;
            this.nombre = nombre;
        }

        /** Recuadro con número automático (1, 2, 3… en orden). */
        public Captura resaltar(String selector) {
            resaltados.add(new Object[]{selector, String.valueOf(resaltados.size() + 1)});
            return this;
        }

        /** Recuadro con etiqueta propia; null = sin número. */
        public Captura resaltar(String selector, String etiqueta) {
            resaltados.add(new Object[]{selector, etiqueta});
            return this;
        }

        public Captura ocultar(String selector) {
            ocultos.add(selector);
            return this;
        }

        public Captura recortar(String selector, double margen) {
            this.recorteSel = selector;
            this.recorteMargen = margen;
            return this;
        }

        /**
         * Captura la pantalla real en vez de la escena. Necesario para que aparezcan
         * ventanas emergentes (lista abierta de un ComboBox, menús contextuales, tooltips).
         * Requiere ventana visible (no headless) y en macOS el permiso de
         * "Grabación de pantalla" para la terminal.
         */
        public Captura pantalla() {
            this.pantalla = true;
            return this;
        }

        public void guardar() {
            enFx(() -> {
                try {
                    guardarEnFx();
                } catch (IOException e) {
                    throw new IllegalStateException(e);
                }
                return null;
            });
        }

        private void guardarEnFx() throws IOException {
            Scene scene = ventana.getScene();
            Parent root = scene.getRoot();
            root.applyCss();
            root.layout();
            List<String> errores = new ArrayList<>();

            WritableImage img;
            double s;
            double ox, oy; // origen de la imagen en coordenadas de escena
            if (pantalla) {
                // origen real del contenido en pantalla (sin barra de título)
                Bounds sb = root.localToScreen(root.getBoundsInLocal());
                img = new javafx.scene.robot.Robot().getScreenCapture(
                        null, sb.getMinX(), sb.getMinY(), sb.getWidth(), sb.getHeight(), false);
                s = img.getWidth() / sb.getWidth(); // 2 en Retina, 1 en pantallas normales
                Bounds rs = root.localToScene(root.getBoundsInLocal());
                ox = rs.getMinX();
                oy = rs.getMinY();
            } else {
                SnapshotParameters p = new SnapshotParameters();
                p.setTransform(Transform.scale(escala, escala));
                p.setFill(scene.getFill() instanceof Color c ? c : Color.WHITE);
                img = root.snapshot(p, null);
                s = escala;
                Bounds rb = root.getBoundsInParent();
                ox = rb.getMinX();
                oy = rb.getMinY();
            }

            StringBuilder json = new StringBuilder();
            json.append("{\"escala\":").append(s).append(",\"resaltar\":[");
            boolean first = true;
            for (Object[] r : resaltados) {
                Bounds b = caja(root, (String) r[0], errores, "resaltar");
                if (b == null) continue;
                if (!first) json.append(',');
                first = false;
                json.append(rect(b, ox, oy, 0, (String) r[1]));
            }
            json.append("],\"ocultar\":[");
            first = true;
            for (String sel : ocultos) {
                for (Node n : root.lookupAll(sel)) {
                    if (!n.isVisible() || n.getScene() == null) continue;
                    if (!first) json.append(',');
                    first = false;
                    json.append(rect(n.localToScene(n.getBoundsInLocal()), ox, oy, 0, null));
                }
            }
            json.append("],\"recortar\":");
            Bounds rc = recorteSel == null ? null : caja(root, recorteSel, errores, "recortar");
            json.append(rc == null ? "null" : rect(rc, ox, oy, recorteMargen, null));
            json.append(",\"errores\":[");
            for (int i = 0; i < errores.size(); i++) {
                if (i > 0) json.append(',');
                json.append(str(errores.get(i)));
            }
            json.append("]}");

            escribirPng(img, salida.resolve(nombre + ".png"));
            Files.writeString(salida.resolve(nombre + ".json"), json, StandardCharsets.UTF_8);
        }
    }

    // ------------------------------------------------------------ utilidades

    private static Bounds caja(Parent root, String sel, List<String> errores, String uso) {
        Node n = root.lookup(sel);
        if (n == null) {
            errores.add(uso + " '" + sel + "': no se encontró el nodo");
            return null;
        }
        if (!n.isVisible() || n.getScene() == null) {
            errores.add(uso + " '" + sel + "': el nodo no está visible");
            return null;
        }
        return n.localToScene(n.getBoundsInLocal());
    }

    private static String rect(Bounds b, double ox, double oy, double m, String etiqueta) {
        String base = String.format(java.util.Locale.ROOT,
                "{\"x\":%.1f,\"y\":%.1f,\"w\":%.1f,\"h\":%.1f",
                b.getMinX() - ox - m, b.getMinY() - oy - m, b.getWidth() + 2 * m, b.getHeight() + 2 * m);
        return base + (etiqueta == null ? ",\"etiqueta\":null}" : ",\"etiqueta\":" + str(etiqueta) + "}");
    }

    private static String str(String v) {
        return "\"" + v.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ") + "\"";
    }

    /** PNG sin depender del módulo javafx.swing. */
    private static void escribirPng(WritableImage img, Path destino) throws IOException {
        int w = (int) img.getWidth(), h = (int) img.getHeight();
        int[] px = new int[w * h];
        img.getPixelReader().getPixels(0, 0, w, h, PixelFormat.getIntArgbInstance(), px, 0, w);
        BufferedImage bi = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
        bi.setRGB(0, 0, w, h, px, 0, w);
        ImageIO.write(bi, "png", destino.toFile());
    }

    private static <T> T enFx(Supplier<T> tarea) {
        if (Platform.isFxApplicationThread()) return tarea.get();
        CompletableFuture<T> f = new CompletableFuture<>();
        Platform.runLater(() -> {
            try {
                f.complete(tarea.get());
            } catch (Throwable t) {
                f.completeExceptionally(t);
            }
        });
        try {
            return f.get(20, TimeUnit.SECONDS);
        } catch (Exception e) {
            throw new IllegalStateException("Falló la captura: " + e.getMessage(), e);
        }
    }
}
