# Greifadapter und Tischaufnahme für den COS-Whiteboardmarker

[CAD-Vorschau und Schnitt](vorschau.png) · [STEP-Baugruppe](marker-werkzeug.step)

Der Adapter klemmt den Stift am hinteren Ende in zwei Ebenen. Die
Stiftachse bleibt frei für eine axiale Entnahme von oben. Zwei flache
Flächen im Abstand von 34 mm nehmen die Backen des Robotiq 2F-85 auf.
Seitliche Leisten begrenzen das Verdrehen des Blocks in den Backen.
Die Klemmung der runden Stifthülse im Block beruht auf Reibung.

Der Fuß hat Ø64 mm und ist 102,5 mm hoch. Der Stift hängt darin nach
unten. Ein Trichter führt den Zapfen des Adapters in die Ablage. Eine
abgeschrägte Ecke legt die Orientierung fest. Der Anschlag trägt am
Adapter, die Stiftspitze behält nominell 5 mm Luft zum Boden. Zwei
Durchgangslöcher Ø4,5 mm im 50-mm-Raster dienen zur Befestigung an
einer geeigneten Unterlage. Der offene Ablageplatz ist für den
Arbeitszyklus gedacht. Für längere Lagerung bleibt die Originalkappe
erforderlich, damit der Stift nicht austrocknet.

## Druck, Montage und Abgleich

| Druckteil | Datei | Montage |
|---|---|---|
| Adapterhälfte mit Schraubenkopfsitzen | [STL](greifadapter-schraube.stl) | Vier M3 × 30 mm Zylinderkopfschrauben |
| Adapterhälfte mit Sechskanttaschen | [STL](greifadapter-mutter.stl) | Vier M3-Sechskantmuttern |
| Tischaufnahme | [STL](tischaufnahme.stl) | Zwei M4-Schrauben an geeigneter Unterlage |

1. Zuerst die beiden Adapterhälften drucken. Die STLs liegen mit der
   Außenfläche auf dem Bett, die Mulde ist offen nach oben. PETG ist
   ein Startmaterial. Slicer-Vorschau an Schraubentaschen und unter
   dem kurzen versetzten Zapfen kontrollieren und dort bei Bedarf
   lokale Stützen setzen. Zapfen und Greifflächen entgraten.
2. Den offenen Stift hinten bis zum inneren Anschlag einlegen und die
   Schrauben gleichmäßig anziehen. Zwischen den Hälften bleibt ein
   Spalt. Der Marker soll sich von Hand weder drehen noch längs
   verschieben lassen, ohne dass die Hülse sichtbar gequetscht wird.
   Falls er rutscht, Sitz und Durchmesser nachmessen und den
   Klemmsitz korrigieren.
3. Die Tischaufnahme aufrecht drucken und gegen Verschieben sichern.
   Den Adapter zuerst von Hand einsetzen. Die abgeflachte Ecke zeigt
   zur entsprechenden Ecke im Trichter. Korrekten Sitz und den
   Abstand der Spitze zum Boden mit dem echten Stift prüfen.
4. Für die spätere Aufnahme am Roboter die Greifhöhe so festlegen,
   dass die Backen in den Leisten sitzen und ihre Unterkanten über
   dem Rand der Aufnahme bleiben. Danach senkrecht ausheben, bis die
   Spitze komplett frei ist. Beim Absetzen senkrecht einfahren und
   erst am Sitzanschlag öffnen. Die reale Pose und Backenfreiheit
   vor einer automatischen Sequenz prüfen. Anschließend den
   TCP an der tatsächlichen Stiftspitze einmessen.

## Maße und Nachweis

- Nutzermaße am offenen Stift vom 19.11.2026. Ø20 mm bei 10 mm
  Abstand vom hinteren Ende, Ø19 mm bei 35 mm, Gesamtlänge etwa
  125 mm. Zwischen diesen Stationen ist ein leichter Konus
  angenommen. Für den unteren Schaft ist im Trichter und
  Schacht ein maximaler Ø21 mm als Modellannahme angesetzt.
- Für die Greifflächen ist eine **22 mm breite Standardbacke** aus
  der Robotiq-Zeichnung angenommen. Der lichte Abstand zwischen den
  Leisten beträgt 23,2 mm. Bei anderem Pad das tatsächlich montierte
  Maß prüfen und den Adapter neu exportieren.
  [Robotiq-Zeichnung, Fig. 6-14](https://assets.robotiq.com/website-assets/support_documents/document/2F-85_2F-140_Instruction_Manual_e-Series_PDF_20190315.pdf)
- Der Trichter erweitert den Einlauf um 4 mm pro Seite. Die trocken
  geprüfte CAD-Passung umfasst den lotrechten Aus-/Einzug und
  ausgewählte, zum Sitz hin korrigierte Versätze. Der um 180°
  gedrehte Adapter kann im CAD den Sitzanschlag nicht erreichen.
  Daraus folgt keine reale Einführ- oder Drehwinkeltoleranz für den
  Roboter. Druckpassung, Klemmsitz, Grifferreichbarkeit und
  Schreiblast sind noch praktisch zu prüfen.
- Der Produktlink bezeichnet die verwendete Stiftfamilie.
  [COS-Whiteboardmarker, 2 mm](https://www.cos.net.au/p/marker-whiteboard-bullet-cos-2mm-black-box-12-black)

## Export aus dem Workspace

Mit der vorhandenen OpenCascade-Umgebung neue Varianten erzeugen:

```bash
.venvs/oak-model/bin/python \
  src/multi_arm_manipulation_UWA/hardware/marker_tool/make_marker_tool.py \
  --d10 20 --d35 19 --length 125 --max-od 21 --pad-width 22 \
  --output /tmp/uwa-marker
```

STEP zeigt den montierten Adapter ohne Schrauben und Marker als drei
CAD-Körper. Die Vorschau zeigt die angenäherte Stiftkontur im Schnitt.
Die drei STL-Dateien sind einzeln in Drucklage und in Millimetern.

## Optische Erkennung und A4-Marker, 24.11.2026

Für das gewünschte Library-Teilprogramm zur Stiftaufnahme empfiehlt sich als
erster Ansatz eine plane ArUco-Fläche am Greifadapter. Die schmale runde
Stifthülse und wechselnde Verdeckungen erschweren eine rein geometrische
Lagebestimmung; deren Robustheit ist ohne aktuelle Aufnahmen nicht belegt.
Der bekannte verdrehgesicherte Sitz hilft bei der Bestimmung einer Greifpose,
beweist aber weder den vollständigen Sitz noch die Stiftanwesenheit.

Den Quadratmarker nicht um den runden Stift oder den runden Halter wickeln.
Die gesamte Fläche muss plan und starr bleiben. Am Adapter Greifflächen,
Schrauben, die Trennfuge und Einführgeometrie berücksichtigen. Falls dort
keine ausreichend große freie Fläche zur Kamera zeigt, eine kleine starre
Trägerlasche verwenden; deren Form und Montage sind noch nicht konstruiert
oder geprüft. Ein separater Marker am Halter kann dessen Lage liefern,
ersetzt aber keine aktuelle Prüfung des eingesetzten Stifts/Adapters.

Der [A4-Druckbogen](../../output/pdf/uwa_pen_markers_A4_1to1.pdf) enthält
26 Etiketten mit 4 mm Weißrand an jeder Seite. Die angegebene Markerkante
umfasst den äußeren schwarzen Rand, ohne den Weißrand. Reine Schwarz-Weiß-
Vektorgrafik, `DICT_4X4_100`, `borderBits=1`; alle IDs sind von den festen
Tischboards und dem mobilen ChArUco-Board verschieden.

| Schwarze Kante | Ausschnitt mit Weißrand | Adapter-ID | Halter-ID |
|---|---|---|---|
| 20 mm | 28 × 28 mm | 92 | 93 |
| 25 mm | 33 × 33 mm | 94 | 95 |
| 30 mm | 38 × 38 mm | 96 | 97 |
| 40 mm | 48 × 48 mm | 98 | 99 |

Ursprünglich war ID 92 mit 20 mm als erster Versuch vorgeschlagen. Ob diese Größe aus
der echten Entfernung und Blickrichtung ausreichend sichtbar ist, muss am
aktuellen Originalbild geprüft werden; keine garantierte Reichweite oder
Millimetergenauigkeit. Größere Größen benötigen entsprechend mehr plane
Trägerfläche. Jede ID hat genau eine Größe. Doppelte IDs sind Ersatzkopien:
pro ID nur ein Exemplar im Kamerabild, den übrigen Bogen außerhalb ablegen.
Bei mehreren Markern auf demselben Körper unterschiedliche IDs und ihre
starren Beziehungen erfassen.

**Drucken:** A4 hoch, 100 % / Tatsächliche Größe, keine Seitenanpassung.
Die 50-mm-Kontrollstrecke und die schwarze Markerkante mit einem Lineal
prüfen. An den gestrichelten Linien ausschneiden und den weißen Rand
erhalten. Matt aufkleben; reflektierendes Klebeband über dem Muster vermeiden.
Für spätere metrische Auswertung tatsächliches Maß und starre Transformation
vom Marker zur Greifpose aufnehmen. Ein leicht erkennbarer Marker allein
belegt noch keine ausreichend genaue Greifpose oder Stiftspitzenkalibrierung.

Reproduktion aus dem Workspace:

```bash
.venvs/charuco-print/bin/python \
  src/multi_arm_manipulation_UWA/scripts/print_pen_markers.py
```

ID-, Maß- und Positionsmetadaten stehen in der JSON-Datei neben dem PDF.
Der Nachweis `uwa_pen_markers_A4_validation.json` dokumentiert die Prüfung
des fertigen 300-dpi-Renders: 26/26 Marker im Gesamtblatt und einzeln lesbar,
A4 und Kantenmaße geprüft. Nur digitaler Druckvorlagennachweis; keine neue
Kameraaufnahme, kein Druck-/Roboter-/Greifversuch. Das Library-Teilprogramm
selbst ist in dieser ersten Etappe noch nicht implementiert.

**Aktueller Aufbau24.11.2026:** Der Nutzer hat zwei30mm-Marker am Stift
angebracht. Im nativen OAK-Pro-Foto17:41AWST sind obenID97 und seitlichID96
lesbar; die seitliche Fläche steht laut Nutzer senkrecht zu den Greifflächen.
Beide IDs dem Stift/Adapter zuordnen, auch wenn97 auf dem Druckbogen als
„Halter“ beschriftet war. Kanten97 etwa60–74px,96 etwa42–75px im4056×3040-
Original, Fokus112. Aufnahme und Pixelbefund unter
`setup/tasks/pen_pick_20261124/20261124-pen-markers-oakpro-01/` im Workspace.
Die Anzeige ist180° gedreht; Messkoordinaten bleiben im nativen Rohbild.
Dies bestätigt die gleichzeitige Erkennung in einer aktuellen Aufnahme;
eine metrische Marker-zu-Greifpose-Kalibrierung und Sichtprüfung während
der Anfahrt stehen noch aus. Keine Roboterbewegung ausgeführt.

Technischer Hintergrund: [OpenCV: Detection of ArUco Markers](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html).

## Gazebo und RViz

Die Zelle zeigt `marker_station` und `cos_marker_docked` als zwei
getrennte, statische Ansichtsobjekte. Die Meshes der Aufnahme und des
Adapters stammen aus der STEP-Baugruppe. Der Stiftschaft ist aus den
gemessenen Maßen angenähert. Beide Objekte liegen auf dem linken Tisch,
270 mm links und 400 mm nach vorne ab Tischplattenmitte. Die Lage ist
ein Vorschlag im Modell. Der Ursprung von `asset/cos_marker_docked`
liegt an der nominellen Stiftspitze, 10,5 mm über der Tischplatte.

- Die normale **UWA Cell Simulation** lädt beide Objekte über
  `scene_objects` im gemeinsamen Zelllayout. In RViz erscheinen sie
  unter **Tabletop props and reconstructions**.
- Die Haus-/Bohr-Kontaktwelt lädt das Dock und den Stift als eigene
  Props. Ihre physische Kartonentität ist davon unabhängig.
  `rviz:=true` bei `grasp.launch.py` öffnet den passenden Viewer.
- Für eine bereits laufende Kontaktwelt lässt sich der Viewer
  separat starten. Namespace und Layout aus deren Startkommando übernehmen.

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 launch uwa_cell_gazebo grasp_visuals.launch.py \
  namespace:=/uwa_grasp_house \
  layout:="$PWD/setup/tasks/house_drill_gazebo_live_20261119_01/layout.yaml"
```

Die Darstellung ist visuell. Für ein späteres Pick-and-place sind
Greifpose und reale TCP-Messung sowie getrennte Kontakt- und
Kollisionsgeometrien für Stift und Aufnahme nötig. Die bestehende
virtuelle Zeichenwerkzeugpose bleibt im jeweiligen Aufgabenmodell.

Bei geändertem Hardware-CAD die beiden DAE-Assets mit
`.venvs/oak-model/bin/python src/multi_arm_manipulation_UWA/tools/export_marker_scene.py`
erneuern, dann `uwa_cell_description` in die Lyrical-Installation bauen.
