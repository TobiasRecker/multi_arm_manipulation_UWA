# Statische OAK4-D als Übersichtskamera

Nutzerziel vom **2026-11-09**: reale OAK4-D neben dem Tisch auf einem Stativ,
aktuell rechts, nach unten auf beide Tischplatten gerichtet. Die genaue Montage
ist offen. In Gazebo Höhe, Blickwinkel und Auflösung vergleichen, um Überblick
und ChArUco-Details gleichzeitig zu erhalten. Die Wrist-Kameras bleiben erhalten.

## Ausgangspose und Optik

Einzige dauerhafte Konfigurationsquelle ist `overview_camera` in
`uwa_cell_description/config/cell_layout.yaml`. Alle Positionen sind Weltkoordinaten
in Metern, X rechts, Y hinten, Z oben. `xyz` bezeichnet das optische Zentrum des
RGB-Sensors, `look_at` einen Zielpunkt, `roll` die Drehung um die Blickachse.

```yaml
overview_camera:
  enabled: true
  xyz: [1.8, 0.0, 3.0]
  look_at: [0.0, 0.0, 1.4]
  roll: 0.0
  width: 4000
  height: 3000
  rate: 3.0
  horizontal_fov: 1.1746065865921838
  near: 0.1
  far: 12.0
```

Damit steht die Kamera seitlich 0,95 m außerhalb der rechten Tischkante,
2,1 m über der Tischoberfläche und blickt etwa 41,6° nach unten.
Der etwas höhere Zielpunkt lässt im Bild Raum für die Roboter über den Boards.
3 m ist eine zunächst untersuchte Aufbauhöhe; ob das reale Stativ sie erreicht,
ist noch nicht bestätigt. Eine niedrigere Variante ist ebenfalls geprüft.

Das horizontale Sichtfeld von nominell 67,3° stammt vom standardmäßigen
[IMX586-Autofokusmodell der OAK4-D](https://docs.luxonis.com/hardware/products/OAK%204%20D).
Bei 4:3 ergibt sich etwa 53° vertikal. Keine gemessene Intrinsics-/Verzeichnungs-
Kalibrierung der konkreten Kamera übernommen. Andere Auflösungsseitenverhältnisse
ändern das vertikale Feld bei gleichbleibendem horizontalem Feld.

Das ist ein idealer RGB-Pinhole-Sensor: kein modellierter Autofokus, Rolling-
Shutter-Effekt, Bildrauschen, Bewegungsunschärfe, Stereo-/Tiefen- oder IR-Kanal.
Die Hardware bleibt eine Rolling-Shutter-Farbkamera; ein ideales Gazebo-Bild
beweist keine Global-Shutter-Eigenschaft der echten Kamera.
Stativ und Gehäuse sind primitive Darstellungen ohne Hersteller-CAD.

## Bedienen und umpositionieren

Neue Zellstarts laden die Übersicht automatisch. Für eine schon laufende Zelle:

```bash
cd ~/UWA_ws
bash src/multi_arm_manipulation_UWA/scripts/overview.sh start
bash src/multi_arm_manipulation_UWA/scripts/overview.sh view
```

Die Kamera ist eine eigene statische Gazebo-Entität `uwa_oak_overview`. Dadurch
kann sie unabhängig von der Zell-URDF neu angelegt werden; das verändert keine
Tisch-/Gelenkstellungen. Es wird keine echte Kamera geöffnet oder konfiguriert.

Nach einer Änderung des zentralen YAML-Blocks:

```bash
bash src/multi_arm_manipulation_UWA/scripts/overview.sh reload
```

Das ersetzt ausschließlich die Übersichtskamera und aktualisiert ihren statischen
TF sowie die RViz-Marker. Das Bild pausiert kurz. Solche Designänderungen außerhalb
einer Kalibrieraufnahme durchführen; alte Bilder gehören zur vorherigen Pose.
Ungültige Einstellungen werden vor dem Entfernen der bisherigen Kamera abgelehnt.
Eine Gazebo-Service-/Renderstörung nach dem Entfernen kann dagegen einen erneuten
`reload` erfordern. Wiederholte Starts verwenden einen lokalen Prozess-Lock,
damit nicht zwei Prozesse dieselbe Kamera verwalten.

`overview.sh start /absoluter/pfad/layout.yaml` verwendet bei einem neuen
eigenständigen Start eine alternative Layout-Datei. Ein bereits laufender
Kameraknoten behält seinen Layoutpfad. Dafür erst gezielt dessen Parameter
`/uwa_cell/oak_overview layout` ändern und danach `reload` aufrufen.

`cell.sh stop` beendet auch die separat verwalteten Dienste
`uwa-cell-overview` und `uwa-cell-overview-view`; bei einem normalen Zelllaunch
läuft der Kameraknoten als dessen Kind. Der Bildbetrachter verwendet rqt_image_view.

## Überblick und Detail prüfen

```bash
bash src/multi_arm_manipulation_UWA/scripts/overview.sh coverage
bash src/multi_arm_manipulation_UWA/scripts/overview.sh check \
  --output ~/UWA_ws/setup/logs/uwa-oak-overview-check
```

`coverage` projiziert die Tisch-Ecken und Felder der beiden Boards aus dem Layout.
Es berechnet **keine Verdeckungen**. `check` verwendet anschließend echte Gazebo-
Bilder und CameraInfo, erkennt beide Muster ohne Ground-Truth-ROI und schreibt
Aufnahmen, markierte Bilder, PnP-Posen und einen JSON-Bericht. Erfolg verlangt
mindestens die konfigurierten zwölf Ecken je Board **im selben Bild**.

Die Marker-Mindestgröße wird für große Übersichtsbilder angepasst: ein minimaler
Umfang von 32 Pixeln statt OpenCVs relativen Standardwerts von 3 % der Bildkante.
Bei 4000 Pixeln würde dieser sonst Marker unter etwa 30 Pixel Seitenlänge
verwerfen. Der bestehende Wrist-/Hand-Eye-Standardwert bleibt unverändert.

Rein geometrische Abschätzung für die 3-m-Ausgangspose:

| Auflösung, gleiches 4:3-Sichtfeld | Kleinste Marker-Seite links / rechts |
|---|---:|
| 1600×1200 | etwa 7 / 11 px |
| 2560×1920 | etwa 11 / 18 px |
| **4000×3000** | **etwa 18 / 28 px** |
| 8000×6000 | etwa 35 / 57 px |

4000×3000 ist deshalb der erste getestete Kompromiss. Eine kleinere Vorschau
ist deutlich billiger zu rendern, bietet dem entfernten Board aber wenig Reserve.
Die 8000er-Variante ist hier nur abgeschätzt, nicht als stabiler Gazebo-Betrieb
getestet. Die 3 Hz sind eine bewusste Simulationslast-Einstellung; sie entsprechen
keiner Hardwareobergrenze. Lange Distanz, flache Sicht und Verdeckungen können
auch bei genügend Pixeln zu fehlenden Ecken führen.

Live-Nachweis am 2026-11-09:

| Optisches Zentrum / Zielpunkt | Tisch-Ecken im geometrischen Bild | Erkannte Ecken links / rechts | Reprojektions-RMS links / rechts |
|---|---|---:|---:|
| [1.8,0,3.0] / [0,0,1.4] m | alle acht | 18 / 24 | 0,069 / 0,061 px |
| [1.8,0,2.6] / [0,0,1.1] m | alle acht | 20 / 24 | 0,054 / 0,096 px |

Das sind einzelne Erkennungsnachweise bei damaligen Armstellungen, keine
Sichtbarkeitsgarantie für alle Bewegungen oder belastbare Extrinsikkalibrierung.
Die Kamera wurde für den Höhenvergleich ohne Zellneustart umgesetzt und danach
auf die 3-m-Pose zurückgestellt. Keine Gelenkbefehle durch diese Werkzeuge.

Belege im Workspace unter `setup/logs/uwa-oak-overview-{initial,final,lower}/`,
`uwa-oak-overview-visuals.json`, `uwa-oak-overview-build.log` und
`uwa-oak-overview-tests-final.log`. 70 Offline-Tests bestanden, einschließlich
bisheriger Beschreibungs-/Scan-/Wrist-/ChArUco-Tests und Kalibrierkern-Tests.
Die anfängliche linke Nichterkennung ist im `initial`-Bericht erhalten.

## ROS / RViz / Grenzen

- RGB: `/uwa_cell/oak_overview/rgb/image_raw`, Sensor-Data-QoS.
- Intrinsics: `/uwa_cell/oak_overview/rgb/camera_info`, gleiche Auflösung und Frame.
- TF: `world -> oak_overview_rgb_optical_frame` (X rechts, Y unten, Z Blickrichtung).
- Pose/Optik neu laden: `/uwa_cell/oak_overview/reload`, `std_srvs/srv/Trigger`.
- Marker: `/uwa_cell/oak_overview/markers`, zuverlässiges Transient-Local-QoS.
  Der Frustumrahmen ist ein 2,5-m-Symbol, kein gemessener Sichtbarkeitsbereich.
- Die neue RViz-Konfiguration zeigt Kameragehäuse, Stativ und Frustum. In einem
  bereits offenen RViz die MarkerArray-Anzeige manuell ergänzen, falls gewünscht.

Das Stativ ist derzeit **nur visuell**, ohne Gazebo-Kollision und ohne Eintrag in
der Hand-Eye-MoveIt-PlanningScene. Seine Kollisionsgeometrie muss ergänzt werden,
bevor reale Kollisionsfreiheit gegenüber diesem neuen Aufbau behauptet wird.
Simulation, Scan und Hardware bleiben unkalibriert gegenüber dieser Designpose.
Die vorhandene automatische Wrist-Hand-Auge-Routine wird durch die OAK nicht
automatisch zu einer Kalibrierung der externen Kamera erweitert.
