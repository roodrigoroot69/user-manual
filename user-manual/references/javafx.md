# JavaFX driver (desktop)

**TestFX** drives the app (clicks, typing, picking from lists) and `ManualCapturer` takes the screenshots with their metadata. Captures are written as a JUnit 5 test with its own tag, so they don't run with the regular test suite.

## 1. Dependencies (test scope only)

Use the JavaFX version the project already has.

Gradle:
```groovy
testImplementation "org.testfx:testfx-junit5:4.0.18"
testImplementation "org.junit.jupiter:junit-jupiter:5.10.2"
// optional headless mode (see section 5):
testRuntimeOnly "org.testfx:openjfx-monocle:21.0.2"

tasks.named('test') { useJUnitPlatform { excludeTags 'manual' } }
tasks.register('manualCapture', Test) {
    useJUnitPlatform { includeTags 'manual' }
    testClassesDirs = sourceSets.test.output.classesDirs
    classpath = sourceSets.test.runtimeClasspath
    systemProperty 'manual.output', "$buildDir/manual/raw"
    outputs.upToDateWhen { false }
}
```

Maven: add `testfx-junit5` with `<scope>test</scope>`, exclude the `manual` tag in Surefire (`<excludedGroups>manual</excludedGroups>`) and run it with `mvn test -Dgroups=manual -DexcludedGroups=none`.

If the project uses modules (`module-info.java`), tests may need `--add-opens` for TestFX; check how the existing tests are configured before changing anything.

## 2. Copy the helper

Copy `assets/javafx/ManualCapturer.java` to `src/test/java/<base-package>/manual/` and adjust the `package` line. It has no dependencies beyond JavaFX and the JDK.

## 3. Demo data (SQLite)

The test must start the app against a demo database, **never** the real one:

- Find out how the app decides its database path (system property, environment variable, config file). If it's hardcoded, propose a minimal change to the user: read `System.getProperty("app.db", <current path>)`.
- Keep a ready demo database (`src/test/resources/manual/demo.db`) or an SQL seed script, and copy it to `build/manual/demo.db` at the start of **every** section. Each section then starts from the same state and screenshots don't change between runs.
- Turn off anything that depends on the network or on time: cloud sync, automatic backups on start/close, update notices. Usually via a system property like `app.mode=demo`; if none exists, propose it to the user.
- If dates show on screen and you want identical screenshots, inject a fixed `Clock` in demo mode.

## 4. The test

One class, one `@Test` method per manual section; `@Start` launches the app fresh for each section. See `assets/javafx/ManualCaptureTest.java.example`. Rules:

- Each screenshot is named `"<section-id>-<NN>"`, where NN is the step number in `manual.yaml`. If the name doesn't match, the document will show `[MISSING SCREENSHOT]`.
- After each action that changes the screen, call `WaitForAsyncUtils.waitForFxEvents()` before capturing. If the app loads data on a background thread (Task/Service), wait for the expected node (`WaitForAsyncUtils.waitFor(5, SECONDS, () -> lookup("#table").tryQuery().isPresent())`).
- For dialogs (a separate Stage or Dialog), capture that window: `robot.listTargetWindows()` or `robot.window("Title")`.
- Selectors: `#fxId` is the most stable. If a key control has no id, propose adding an `fx:id` or `setId()`; it's a tiny change that keeps the manual from breaking.

### Popup windows

`root.snapshot()` (the default mode) captures only the scene, so it does **not** include open ComboBox lists, ContextMenus or tooltips, since those are separate windows. For those steps use `.screen()`: it takes a real screen capture. It needs a visible window (not headless) and, on macOS, the **Screen Recording** permission for the terminal (System Settings → Privacy & Security). On Retina the scale is detected automatically.

## 5. Run

```bash
./gradlew manualCapture          # or the Maven equivalent
python <skill>/scripts/annotate.py build/manual/raw --out build/manual
python <skill>/scripts/build_manual.py docs/manual/manual.yaml --build build/manual --pdf
```

With a visible window (recommended for final screenshots): windows appear for a few seconds while it runs; don't move the mouse over them. On macOS, the first run asks for the Accessibility permission so TestFX can move the mouse.

Headless (handy for iterating or CI; incompatible with `.screen()`):
```
-Dtestfx.robot=glass -Dtestfx.headless=true -Dprism.order=sw -Dglass.platform=Monocle -Dmonocle.platform=Headless
```
Software rendering can change font antialiasing slightly. Produce the final screenshots with a visible window.

## 6. Window size

Fix the Stage size in the test (e.g. 1366×768, a common resolution on front-desk PCs) so all screenshots are consistent. If the system will run on smaller monitors, capture at that size: the client will see exactly what's on their screen.
