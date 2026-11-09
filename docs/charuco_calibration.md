# ChArUco: erste Prüfung der Tisch- und Roboterkoordinaten

## Szene und Referenzrahmen

Auf jedem Tisch liegt ein Board mittig zwischen den Robotern. Die Parameter
stehen unter `charuco` in `uwa_cell_description/config/cell_layout.yaml`:
7 × 5 Felder, Feldkante 40 mm, Marker 28 mm, weißer Rand 20 mm,
3 mm Trägerdicke. Das gedruckte Muster misst 280 × 200 mm, die Platte
320 × 240 mm. Wörterbuch `DICT_4X4_100`, links IDs 0–16, rechts 50–66.
Dadurch wird ein Board des anderen Tisches nicht als eigenes akzeptiert.

Die vorhandenen Frames **`left_table_top` und `right_table_top`** sind die
Tisch-Koordinatensysteme dieser ersten Kalibrierung: Ursprung jeweils in der
Mitte der Tischoberfläche, Z nach oben. `<table>_table_frame` liegt hingegen
auf Bodenhöhe und ist nicht der hier verwendete Referenzrahmen.

`<table>_charuco_mount` liegt im Mittelpunkt der bedruckten Oberfläche;
`<table>_charuco` entspricht OpenCVs Musterkoordinaten: Ursprung an der
oberen linken Ecke des eigentlichen Schachbretts, **ohne weißen Rand**,
X nach rechts, Y im Muster nach unten, Z in die Platte hinein.
Bei `yaw: 0` ist das relativ zu `table_top`:
Translation `[-0.14, +0.10, +0.003]` m und Rotation `Rx(pi)`.
Die Boardpose folgt jeder Verschiebung/Drehung ihres Tisches.

Die Kameras starten 0,55 m über der Boardmitte, entlang Tisch-Y um
±0,28 m versetzt, mit optischer Z-Achse auf die Mitte gerichtet. Die dafür
berechneten sechs Gelenkwinkel stehen je Arm in `initial_positions`.
Die Montage auf der vom Werkzeug-I/O-Stecker abgewandten Seite bleibt erhalten.
Diese Stellungen sind Initialzustände, kein geplanter Bewegungsweg.

## Ausführen und Bilder ansehen

Nach dem üblichen Build und Neustart der Zelle:

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_gazebo charuco_check \
  --output-dir "$UWA_WS/setup/logs/uwa-charuco-check"
```

Das Werkzeug liest ausschließlich die simulierte Domain 64. Es verändert
keine Gelenke und schreibt keine geschätzten Posen in die Layoutdatei.
Pro Kamera werden zehn verschiedene Bildzeitstempel ausgewertet.
Die Ausgabe enthält:

- `report.json`: Bildposen, Ground Truth, Positions-/Winkelfehler,
  Reprojektionsfehler, erste Basis- und Relativbasisschätzung.
- `<robot_id>_raw.png` und `<robot_id>_detected.png`: Originalbild sowie erkanntes Board, Ecken und gezeichnete Achsen
  (X rot, Y grün, Z blau). Bei fehlender Erkennung `<robot_id>_latest.png`.
- Während des Laufs `/uwa_cell/<robot_id>/charuco/image_annotated` für einen
  RViz-Image-Display mit Best-Effort-QoS. Der Publisher endet mit dem Prüfprogramm.

`--layout /path/layout.yaml` muss dieselbe Konfiguration wie die laufende
Simulation auswählen. `--timeout 60` begrenzt die Wartezeit in realen Sekunden.
Fehlende Bilder/Erkennungen oder Überschreitungen der konfigurierten Grenzen
erzeugen einen Fehlerstatus und Exit-Code 1. Standardgrenzen: mindestens zwölf
ChArUco-Ecken, maximal 1 px Reprojektions-RMS, 10 mm Positionsfehler und 2°
Rotationsfehler. Die Simulation ist idealisiert; diese Grenzwerte sind keine
Genauigkeitszusage für echte Kameras.

## Berechnung und Unabhängigkeit der Ground Truth

Notation: **`T_A_B` transformiert Koordinaten von B nach A**.

Die Bildschätzung verwendet OpenCV `CharucoDetector`, `matchImagePoints`,
planare IPPE-PnP-Kandidaten und `solvePnPRefineLM`. Positive Tiefen und der
Reprojektionsfehler wählen den Kandidaten. Eingang sind nur das Kamerabild,
`CameraInfo`, Marker-IDs und die metrischen Mustermaße. Weder Roboterbasispose
noch Ground Truth werden zur Erkennung, Initialisierung oder Auswahl verwendet.
Der Ergebniswert **`T_camera_board`** ist eine echte Bildschätzung.

Für die Auswertung werden danach die bekannten Simulationstransformationen
zum **Bildzeitstempel** aus TF gelesen. `board_error` vergleicht die Bildpose mit
`T_camera_board_ground_truth`. Die explizite Boardframe-Definition wird zusätzlich
gegen die Konfiguration geprüft; ein Achsen-/Randfehler soll nicht verborgen bleiben.

Ein erster Basisabgleich setzt folgende Größen als bekannt voraus:

- Boardpose im Tisch-KS, `T_table_board` (in Realität zu vermessen),
- interne Armkinematik, aktuelle Gelenkwinkel und Kameramontage,
  zusammen `T_base_camera` aus der internen TF-Kette ab **URDF `base_link`**.

Dann gilt:

```
T_table_base_est = T_table_board @ inv(T_camera_board_est) @ inv(T_base_camera)
T_front_rear_est = inv(T_table_front_est) @ T_table_rear_est
```

Die zweite Gleichung wird je Tisch separat ausgewertet. Erst im Anschluss
werden die geschätzten Basis-/Relativposen mit der Ground Truth verglichen.
Die bekannte Weltmontage des Roboters ist kein Eingang der Basisschätzung.
Die internen TFs sind in dieser Simulation exakt; auf echter Hardware gelten
deren Kalibrierfehler als zusätzliche Fehlerquellen. Die Frames `base_link`
und UR-Teach-Pendant-`base` unterscheiden sich weiterhin um die bekannte 180°-Drehung.

Eine einzelne Ansicht kalibriert **weder** unbekannte Kameraintrinsics **noch**
unbekannte Hand-Auge-Transformationen oder Gelenkparameter. Ein sinnvoller
Folgeschritt sind mehrere unterschiedliche Armstellungen, robuste gemeinsame
Schätzung der gewünschten Extrinsiken und unabhängige Validierungsstellungen.
Die im Bericht gemittelten stationären Bilder ersetzen diese Bewegungsvielfalt nicht.

Der [datierte Prüfbericht](charuco_validation_2026-11-09.json) enthält die erste
Validierung und einen abschließenden Bestätigungslauf. Im letzten Lauf betrug
der relative Basisfehler links 1,888 mm / 0,1645°, rechts 1,843 mm / 0,1570°.
Alle vier Kameras erkannten je 24 Ecken in zehn verschiedenen Bildern.
Originale, Achsenbilder und vollständiger Bericht liegen im Workspace unter
`setup/logs/uwa-charuco-final/`. 33 Offline-Tests bestanden; neun aktive
Controller und die stabile tatsächliche Gazebo-Zellwurzel wurden zusätzlich geprüft.

## Ausdruck derselben Boards

Die Originalgröße mit weißem Rand beträgt **320 × 240 mm**. Auf A3 passt ein
Board pro Blatt im Querformat. A4 ist nur auf mehrere Blätter verteilt möglich,
wenn Feldkante und metrische Pose mit der Simulation identisch bleiben sollen.

- [A3-Druckvorlage](../output/pdf/uwa_charuco_boards_A3_1to1.pdf): zwei Seiten,
  zuerst Tisch links, dann Tisch rechts; bevorzugt für eine durchgehende Oberfläche.
- [A4-Druckvorlage](../output/pdf/uwa_charuco_boards_A4_tiled_1to1.pdf): vier Seiten,
  links Teil 1/2 und 2/2, anschließend rechts Teil 1/2 und 2/2. An Schnittmarken
  zuschneiden und den gemeinsamen Musterstreifen **20 mm überlappend** ausrichten;
  rechte Hälfte deckungsgleich unter die linke legen.

**100% / Tatsächliche Größe** wählen, automatische Seitenanpassung deaktivieren.
Kontrollstrecke **100 mm** und Feldkante **40 mm** am Papier nachmessen. Die
beiden Boards nicht verschieden skalieren. Auf eine plane, feste Unterlage
kleben; ein verzogener Ausdruck verändert die zugrunde gelegte ebene Geometrie.

Die PDFs enthalten Vektorflächen aus genau dem von Gazebo verwendeten
OpenCV-Bitmap, keine nachgezeichneten oder generativ erzeugten Marker.
Seitenformate und Vektormaße wurden geprüft, alle sechs Seiten gerendert und
visuell kontrolliert. OpenCV erkennt auf beiden A3-Seiten und beiden digital
zusammengesetzten A4-Boards sämtliche 17 Marker und 24 ChArUco-Ecken.
[Prüfbericht](charuco_print_validation_2026-11-09.json). Dies prüft die Dateien,
nicht die Maßhaltigkeit eines konkreten Druckers.

Optional neu erzeugen (zusätzlich `sudo apt-get install python3-reportlab`):

```bash
source scripts/env.bash
python3 scripts/print_charuco.py
```

## Nach Layoutänderungen neue Anfangsstellungen berechnen

```bash
ros2 run uwa_cell_gazebo prepare_charuco_views \
  --layout /path/to/layout.yaml --output /tmp/uwa-aimed-layout.yaml
# Ergebnis prüfen und als alternative Konfiguration starten:
ros2 launch uwa_cell_gazebo cell.launch.py layout:=/tmp/uwa-aimed-layout.yaml
```

Der Helfer verwendet FK/IK aus der tatsächlich expandierten URDF. Er schreibt
eine neue Layoutdatei; die Eingabedatei wird nicht überschrieben. Er führt
keine Bewegung aus und garantiert keine Kollisionsfreiheit. Die gelieferten
Defaultstellungen werden zusätzlich mit den echten Gazebo-Bildern geprüft.

## Unbekannte Kameramontage aus mehreren Stellungen kalibrieren

Die hier beschriebene erste Bildprüfung verwendet die nominell bekannte
Hand-Auge-Transformation. Für deren tatsächliche Schätzung gibt es jetzt die
[automatische Hand-Auge-Routine mit Qt-GUI](automatic_handeye.md). Sie erfasst
standardmäßig 40 unterschiedliche Stellungen pro Arm, trennt Fit und
Validierung, bestimmt beide relativen Tischpaare und aktiviert Ergebnisse
erst nach ausdrücklichem Übernehmen in einem getrennten Modell.

## Abhängigkeiten und Quellen

Benötigt wird OpenCV mit `aruco.CharucoDetector` und `CharucoBoard.matchImagePoints`;
hier ist das systemweit installierte **OpenCV 4.10.0**. Die Paketabhängigkeit
`python3-opencv` ist deklariert. Keine parallele pip-OpenCV-Installation erforderlich.
Die Muster werden deterministisch durch OpenCV erzeugt, nicht durch Imagegen.
Textur und Mesh entstehen passend zur aktuellen YAML in einem temporären
Launch-Verzeichnis und werden beim Ende des Launchs entfernt.

Referenzen: [OpenCV ChArUco-Erkennung und Posenkonvention](https://docs.opencv.org/4.x/df/d4a/tutorial_charuco_detection.html),
[OpenCV solvePnP](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html).
