package manual;
// Demo desktop app. Its UI is in Spanish on purpose, to show a manual generated with language: es.
import javafx.application.*; import javafx.scene.*; import javafx.scene.control.*; import javafx.scene.layout.*; import javafx.stage.*; import javafx.geometry.*;
public class DemoApp extends Application {
  static Stage stage;
  public void start(Stage st){
    stage=st;
    VBox nav=new VBox(6); nav.setPadding(new Insets(16)); nav.setStyle("-fx-background-color:#1f2937"); nav.setPrefWidth(180);
    Label logo=new Label("Distribuidora"); logo.setStyle("-fx-text-fill:white;-fx-font-weight:bold");
    Button bInv=new Button("Inventario"); bInv.setId("btnInventario"); bInv.setMaxWidth(Double.MAX_VALUE);
    Button bPed=new Button("Pedidos"); bPed.setMaxWidth(Double.MAX_VALUE);
    nav.getChildren().addAll(logo,bInv,bPed);
    BorderPane root=new BorderPane(); root.setLeft(nav);
    Label user=new Label("sergio.cortes@correo-real.mx"); user.setId("lblUsuario");
    HBox top=new HBox(user); top.setAlignment(Pos.CENTER_RIGHT); top.setPadding(new Insets(10)); root.setTop(top);
    root.setCenter(new Label("Bienvenido"));
    bInv.setOnAction(e->{
      TableView<String> t=new TableView<>(); t.getColumns().add(new TableColumn<>("Producto"));
      Button nueva=new Button("Nueva entrada"); nueva.setId("btnNuevaEntrada");
      nueva.setOnAction(ev->{
        GridPane g=new GridPane(); g.setId("formEntrada"); g.setHgap(10); g.setVgap(10); g.setPadding(new Insets(20));
        ComboBox<String> c=new ComboBox<>(); c.setId("cmbProducto"); c.getItems().addAll("Aceite 1L","Arroz 1kg"); c.setValue("Arroz 1kg");
        TextField q=new TextField("48"); q.setId("txtCantidad");
        Button g1=new Button("Guardar"); g1.setId("btnGuardar");
        g.addRow(0,new Label("Producto"),c); g.addRow(1,new Label("Cantidad (piezas)"),q); g.add(g1,1,2);
        root.setCenter(new VBox(10,new Label("Nueva entrada"),g));
      });
      root.setCenter(new VBox(10,nueva,t));
    });
    st.setScene(new Scene(root,900,560)); st.setTitle("Demo"); st.show();
  }
}
