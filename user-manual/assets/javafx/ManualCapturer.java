// Copy to src/test/java/<package>/manual/ and adjust the package line.
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
import java.util.Locale;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * Takes screenshots of JavaFX windows and writes, next to each PNG, a JSON file
 * with the boxes to highlight/redact/crop. scripts/annotate.py then draws them.
 *
 * Typical use inside a TestFX test:
 *
 *   cap.capture(stage, "record-stock-entry-03")
 *      .highlight("#cmbProduct").highlight("#txtQuantity")
 *      .redact("#lblUser")
 *      .crop("#entryForm", 16)
 *      .save();
 *
 * Selectors are Node.lookup() selectors: "#fxId", ".css-class", "Button".
 * With fx:id in FXML the node already has an id; for views built in code, call setId().
 */
public final class ManualCapturer {

    private final Path output;
    private final double scale;
    private final List<String> alwaysRedact = new ArrayList<>();

    /** @param output folder for raw screenshots (e.g. build/manual/raw)
     *  @param scale  2 = crisp when printed; also fine on Retina */
    public ManualCapturer(Path output, double scale) {
        this.output = output;
        this.scale = scale;
        try {
            Files.createDirectories(output);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Selectors to blur in every screenshot (logged-in user's email, tax ID, etc.). */
    public ManualCapturer alwaysRedact(String... selectors) {
        alwaysRedact.addAll(List.of(selectors));
        return this;
    }

    /** @param name "<section-id>-<NN>", e.g. "record-stock-entry-03" (NN = step number in manual.yaml) */
    public Capture capture(Window window, String name) {
        return new Capture(window, name);
    }

    public final class Capture {
        private final Window window;
        private final String name;
        private final List<String[]> highlights = new ArrayList<>(); // {selector, label}
        private final List<String> redactions = new ArrayList<>(alwaysRedact);
        private String cropSelector;
        private double cropMargin;
        private boolean screen;

        private Capture(Window window, String name) {
            this.window = window;
            this.name = name;
        }

        /** Box with an automatic number (1, 2, 3… in order). */
        public Capture highlight(String selector) {
            highlights.add(new String[]{selector, String.valueOf(highlights.size() + 1)});
            return this;
        }

        /** Box with a custom label; null = no number badge. */
        public Capture highlight(String selector, String label) {
            highlights.add(new String[]{selector, label});
            return this;
        }

        public Capture redact(String selector) {
            redactions.add(selector);
            return this;
        }

        public Capture crop(String selector, double margin) {
            this.cropSelector = selector;
            this.cropMargin = margin;
            return this;
        }

        /**
         * Capture the real screen instead of the scene. Needed for popup windows
         * (an open ComboBox list, context menus, tooltips). Requires a visible
         * window (not headless) and, on macOS, the "Screen Recording" permission
         * for the terminal.
         */
        public Capture screen() {
            this.screen = true;
            return this;
        }

        public void save() {
            onFx(() -> {
                try {
                    saveOnFx();
                } catch (IOException e) {
                    throw new IllegalStateException(e);
                }
                return null;
            });
        }

        private void saveOnFx() throws IOException {
            Scene scene = window.getScene();
            Parent root = scene.getRoot();
            root.applyCss();
            root.layout();
            List<String> errors = new ArrayList<>();

            WritableImage img;
            double s;
            double ox, oy; // image origin in scene coordinates
            if (screen) {
                // real on-screen origin of the content (excluding the title bar)
                Bounds sb = root.localToScreen(root.getBoundsInLocal());
                img = new javafx.scene.robot.Robot().getScreenCapture(
                        null, sb.getMinX(), sb.getMinY(), sb.getWidth(), sb.getHeight(), false);
                s = img.getWidth() / sb.getWidth(); // 2 on Retina, 1 on regular displays
                Bounds rs = root.localToScene(root.getBoundsInLocal());
                ox = rs.getMinX();
                oy = rs.getMinY();
            } else {
                SnapshotParameters p = new SnapshotParameters();
                p.setTransform(Transform.scale(scale, scale));
                p.setFill(scene.getFill() instanceof Color c ? c : Color.WHITE);
                img = root.snapshot(p, null);
                s = scale;
                Bounds rb = root.getBoundsInParent();
                ox = rb.getMinX();
                oy = rb.getMinY();
            }

            StringBuilder json = new StringBuilder();
            json.append("{\"scale\":").append(s).append(",\"highlight\":[");
            boolean first = true;
            for (String[] h : highlights) {
                Bounds b = box(root, h[0], errors, "highlight");
                if (b == null) continue;
                if (!first) json.append(',');
                first = false;
                json.append(rect(b, ox, oy, 0, h[1]));
            }
            json.append("],\"redact\":[");
            first = true;
            for (String sel : redactions) {
                for (Node n : root.lookupAll(sel)) {
                    if (!n.isVisible() || n.getScene() == null) continue;
                    if (!first) json.append(',');
                    first = false;
                    json.append(rect(n.localToScene(n.getBoundsInLocal()), ox, oy, 0, null));
                }
            }
            json.append("],\"crop\":");
            Bounds cb = cropSelector == null ? null : box(root, cropSelector, errors, "crop");
            json.append(cb == null ? "null" : rect(cb, ox, oy, cropMargin, null));
            json.append(",\"errors\":[");
            for (int i = 0; i < errors.size(); i++) {
                if (i > 0) json.append(',');
                json.append(str(errors.get(i)));
            }
            json.append("]}");

            writePng(img, output.resolve(name + ".png"));
            Files.writeString(output.resolve(name + ".json"), json, StandardCharsets.UTF_8);
        }
    }

    // ------------------------------------------------------------ helpers

    private static Bounds box(Parent root, String sel, List<String> errors, String use) {
        Node n = root.lookup(sel);
        if (n == null) {
            errors.add(use + " '" + sel + "': node not found");
            return null;
        }
        if (!n.isVisible() || n.getScene() == null) {
            errors.add(use + " '" + sel + "': node is not visible");
            return null;
        }
        return n.localToScene(n.getBoundsInLocal());
    }

    private static String rect(Bounds b, double ox, double oy, double m, String label) {
        String base = String.format(Locale.ROOT, "{\"x\":%.1f,\"y\":%.1f,\"w\":%.1f,\"h\":%.1f",
                b.getMinX() - ox - m, b.getMinY() - oy - m, b.getWidth() + 2 * m, b.getHeight() + 2 * m);
        return base + (label == null ? ",\"label\":null}" : ",\"label\":" + str(label) + "}");
    }

    private static String str(String v) {
        return "\"" + v.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ") + "\"";
    }

    /** PNG without depending on the javafx.swing module. */
    private static void writePng(WritableImage img, Path target) throws IOException {
        int w = (int) img.getWidth(), h = (int) img.getHeight();
        int[] px = new int[w * h];
        img.getPixelReader().getPixels(0, 0, w, h, PixelFormat.getIntArgbInstance(), px, 0, w);
        BufferedImage bi = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
        bi.setRGB(0, 0, w, h, px, 0, w);
        ImageIO.write(bi, "png", target.toFile());
    }

    private static <T> T onFx(Supplier<T> task) {
        if (Platform.isFxApplicationThread()) return task.get();
        CompletableFuture<T> f = new CompletableFuture<>();
        Platform.runLater(() -> {
            try {
                f.complete(task.get());
            } catch (Throwable t) {
                f.completeExceptionally(t);
            }
        });
        try {
            return f.get(20, TimeUnit.SECONDS);
        } catch (Exception e) {
            throw new IllegalStateException("Capture failed: " + e.getMessage(), e);
        }
    }
}
