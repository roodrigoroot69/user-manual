# Driver JavaFX (escritorio)

Se usa **TestFX** para manejar la app (clics, escribir, elegir en listas) y `ManualCapturador` para tomar capturas con sus metadatos. Las capturas se escriben como una prueba JUnit 5 con una etiqueta aparte, para que no corran en la suite normal.

## 1. Dependencias (solo de pruebas)

Usa la misma versión de JavaFX que ya tiene el proyecto.

Gradle:
```groovy
testImplementation "org.testfx:testfx-junit5:4.0.18"
testImplementation "org.junit.jupiter:junit-jupiter:5.10.2"
// headless opcional (ver sección 5):
testRuntimeOnly "org.testfx:openjfx-monocle:21.0.2"

tasks.named('test') { useJUnitPlatform { excludeTags 'manual' } }
tasks.register('manualCapturas', Test) {
    useJUnitPlatform { includeTags 'manual' }
    testClassesDirs = sourceSets.test.output.classesDirs
    classpath = sourceSets.test.runtimeClasspath
    systemProperty 'manual.salida', "$buildDir/manual/crudas"
    outputs.upToDateWhen { false }
}
```

Maven: agrega `testfx-junit5` con `<scope>test</scope>`, excluye el tag `manual` en Surefire (`<excludedGroups>manual</excludedGroups>`) y córrelo con `mvn test -Dgroups=manual -DexcludedGroups=none`.

Si el proyecto usa módulos (`module-info.java`), las pruebas pueden necesitar `--add-opens` para TestFX; revisa cómo están configuradas las pruebas existentes antes de tocar nada.

## 2. Copiar el helper

Copia `assets/javafx/ManualCapturador.java` a `src/test/java/<paquete-base>/manual/` y ajusta la línea `package`. No tiene dependencias fuera de JavaFX y el JDK.

## 3. Datos de demo (SQLite)

La prueba debe arrancar la app apuntando a una base de demo, **nunca** a la base real:

- Busca cómo la app decide la ruta de la base (propiedad del sistema, variable de entorno, archivo de configuración). Si está fija en el código, propone al usuario un cambio mínimo: leer `System.getProperty("app.db", <ruta actual>)`.
- Guarda una base de demo lista (`src/test/resources/manual/demo.db`) o un script SQL de carga, y cópiala a `build/manual/demo.db` al inicio de **cada** sección. Así cada sección parte del mismo estado y las capturas no cambian entre corridas.
- Desactiva lo que dependa de red o de tiempo: sincronización con la nube, respaldos automáticos al iniciar o cerrar, avisos de actualización. Normalmente con una propiedad del sistema tipo `app.modo=demo`; si no existe, propónla al usuario.
- Si aparecen fechas en pantalla y quieres capturas idénticas, inyecta un `Clock` fijo en modo demo.

## 4. La prueba

Una clase, un método `@Test` por sección del manual; `@Start` arranca la app de nuevo para cada sección. Mira `assets/javafx/ManualCapturaTest.java.ejemplo`. Reglas:

- El nombre de cada captura es `"<seccion-id>-<NN>"`, donde NN es el número de paso en `manual.yaml`. Si el nombre no coincide, el documento marcará `[FALTA CAPTURA]`.
- Después de cada acción que cambie la pantalla, llama `WaitForAsyncUtils.waitForFxEvents()` antes de capturar. Si la app carga datos en un hilo aparte (Task/Service), espera a que aparezca el nodo esperado (`WaitForAsyncUtils.waitFor(5, SECONDS, () -> lookup("#tabla").tryQuery().isPresent())`).
- Para ventanas de diálogo (Stage o Dialog aparte), captura esa ventana: `robot.listTargetWindows()` o `robot.window("Título")`.
- Selectores: `#fxId` es lo más estable. Si algún control clave no tiene id, propón agregarle `fx:id` o `setId()`; es un cambio mínimo y hace que el manual no se rompa.

### Ventanas emergentes

`root.snapshot()` (el modo por defecto) captura solo la escena, así que **no** incluye listas abiertas de ComboBox, ContextMenu ni tooltips, porque son ventanas aparte. Para esos pasos usa `.pantalla()`: toma la captura real de pantalla. Requiere que la ventana sea visible (no headless) y, en macOS, que la terminal tenga permiso de **Grabación de pantalla** (Ajustes del Sistema → Privacidad y seguridad). En Retina la escala se detecta sola.

## 5. Correr

```bash
./gradlew manualCapturas          # o el equivalente en Maven
python <skill>/scripts/annotate.py build/manual/crudas --out build/manual
python <skill>/scripts/build_manual.py docs/manual/manual.yaml --build build/manual --pdf
```

Con ventana visible (recomendado para las capturas finales): las ventanas aparecen unos segundos mientras corre; no muevas el mouse encima. En macOS, la primera vez pedirá permiso de Accesibilidad para que TestFX pueda mover el mouse.

Headless (útil para iterar o en CI; incompatible con `.pantalla()`):
```
-Dtestfx.robot=glass -Dtestfx.headless=true -Dprism.order=sw -Dglass.platform=Monocle -Dmonocle.platform=Headless
```
El renderizado por software puede cambiar un poco el suavizado de las fuentes. Genera las capturas finales con ventana visible.

## 6. Tamaño de ventana

Fija el tamaño del Stage en la prueba (p. ej. 1366×768, una resolución común en las PCs de mostrador) para que todas las capturas sean consistentes. Si el sistema se usará en monitores más chicos, captura en ese tamaño: el cliente verá lo mismo que en su pantalla.
