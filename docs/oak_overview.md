# Statische OAK4-D als Übersichtskamera

Nutzerziel vom **2026-11-09**: reale OAK4-D neben dem Tisch auf einem Stativ,
aktuell rechts, nach unten auf beide Tischplatten gerichtet. Die genaue Montage
ist offen. In Gazebo Höhe, Blickwinkel und Auflösung vergleichen, um Überblick
und ChArUco-Details gleichzeitig zu erhalten. Die Wrist-Kameras bleiben erhalten.
**Nutzerkorrektur:** Das vorhandene Stativ erreicht höchstens **2 m**. Zwei
weitere OAK-Kameras stehen laut Nutzer bei Bedarf für tote Winkel zur Verfügung.
Die erste wurde per USB als **OAK-D Pro AF (RVC2)** identifiziert; die zweite
ist noch ungeprüft. Die frühere Vermutung „beide OAK-D-S2-FF“ ist damit überholt.
Montage und Einbindung als zusätzliche Zellkameras bleiben offen.

## Ausgangspose und Optik

Einzige dauerhafte Konfigurationsquelle ist `overview_camera` in
`uwa_cell_description/config/cell_layout.yaml`. Alle Positionen sind Weltkoordinaten
in Metern, X rechts, Y hinten, Z oben. `xyz` bezeichnet das optische Zentrum des
RGB-Sensors, `look_at` einen Zielpunkt, `roll` die Drehung um die Blickachse.

```yaml
overview_camera:
  enabled: true
  xyz: [1.8, -0.8, 2.0]
  look_at: [0.0, -0.1, 0.95]
  roll: 0.0
  width: 4000
  height: 3000
  rate: 3.0
  horizontal_fov: 1.1746065865921838
  near: 0.1
  far: 12.0
```

Damit steht die Kamera seitlich 0,95 m außerhalb der rechten Tischkante,
0,8 m zur Vorderseite versetzt, 1,1 m über der Tischoberfläche und blickt etwa
28,5° nach unten. Der Zielpunkt liegt 5 cm über der Tischplatte und 10 cm vor
der Zellmitte. Diese Designpose ist bei maximal 2 m optischer Höhe geprüft.
Frühere 3-/2,6-m-Vorschläge überschreiten die bestätigte Stativgrenze und sind
keine aktuellen Montageempfehlungen.

Das horizontale Sichtfeld von nominell 67,3° stammt vom standardmäßigen
[IMX586-Autofokusmodell der OAK4-D](https://docs.luxonis.com/hardware/products/OAK%204%20D).
Bei 4:3 ergibt sich etwa 53° vertikal. Keine gemessene Intrinsics-/Verzeichnungs-
Kalibrierung der konkreten Kamera übernommen. Andere Auflösungsseitenverhältnisse
ändern das vertikale Feld bei gleichbleibendem horizontalem Feld.

Das ist ein idealer RGB-Pinhole-Sensor: kein modellierter Autofokus, Rolling-
Shutter-Effekt, Bildrauschen, Bewegungsunschärfe, Stereo-/Tiefen- oder IR-Kanal.
Die Hardware bleibt eine Rolling-Shutter-Farbkamera; ein ideales Gazebo-Bild
beweist keine Global-Shutter-Eigenschaft der echten Kamera.
Seit12.11.2026 verwendet das Gehäuse das vom Nutzer bereitgestellte OAK-4-Pro-CAD.
Das Stativ ist eine selbst erstellte visuelle Näherung mit Teleskopbeinen und Kopf.
[Modell, Vorschau, Einheiten und Grenzen](oak_camera_cad.md).

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

Rein geometrische Abschätzung für die aktuelle 2-m-Ausgangspose:

| Auflösung, gleiches 4:3-Sichtfeld | Kleinste Marker-Seite links / rechts |
|---|---:|
| 1600×1200 | etwa 6 / 12 px |
| 2560×1920 | etwa 10 / 18 px |
| **4000×3000** | **etwa 15 / 29 px** |
| 8000×6000 | etwa 31 / 58 px |

4000×3000 ist deshalb der erste getestete Kompromiss. Eine kleinere Vorschau
ist deutlich billiger zu rendern, bietet dem entfernten Board aber wenig Reserve.
Die 8000er-Variante ist hier nur abgeschätzt, nicht als stabiler Gazebo-Betrieb
getestet. Die 3 Hz sind eine bewusste Simulationslast-Einstellung; sie entsprechen
keiner Hardwareobergrenze. Lange Distanz, flache Sicht und Verdeckungen können
auch bei genügend Pixeln zu fehlenden Ecken führen.

## Vergleich unter der 2-m-Grenze

Mehrere seitliche und diagonale Kandidaten bei 2 m wurden ohne Armbewegungen
durch diese Aufgabe getestet. Bloßes Absenken an der bisherigen seitlichen
Position erkennt das linke Board nicht zuverlässig. Stark diagonale Positionen
rechts vorne haben in den geprüften Armstellungen Verdeckungen durch die Arme.
Einige seitlich versetzte4k-Varianten erkennen17/24 Ecken, schneiden aber eine
Tischecke ab. Die aktuelle Pose verschiebt den Blick leicht nach vorne/unten:
alle acht Tisch-Ecken liegen geometrisch im Bild; in der geprüften Aufnahme
sind alle vier Arme und beide Tischplatten sichtbar.

Aktueller Live-Nachweis: **12 Ecken links / 24 rechts**, Reprojektions-RMS
**0,691 / 0,042 px**, bei4000×3000. Das linke Board erreicht damit gerade die
konfigurierte Mindestzahl und hat wenig Reserve; keine verlässliche
Sichtbarkeit für alle späteren Armbewegungen behaupten. Für bessere
Detailabdeckung oder verdeckte Bereiche stehen die zwei zusätzlichen OAKs als spätere
Erweiterungsoption bereit. Noch keine Zusatzkamera gespawnt oder kalibriert.

6k-Tests lieferten CameraInfo, aber im Prüfzeitfenster keine empfangenen
ROS-Bilder; ein5k-Versuch scheiterte ebenfalls am End-to-End-Nachweis. Daraus
wird keine Hardware-Auflösungsgrenze abgeleitet. Aktuell bleibt das getestete
4k-Profil aktiv. Die endgültige YAML ist wieder die Quelle des Kameraknotens,
kein temporärer Testlayoutpfad. Kein Zell-/Scan-Neustart, keine Gelenkbefehle.

Belege: `setup/logs/uwa-oak-2m/`, insbesondere `final/report.json` und
`final/overview.jpg`; Zusammenfassung in
`docs/oak_overview_2m_validation_2026-11-09.json`. 13 passende Offline-Tests
bestanden, einschließlich Stativgrenze, Tischabdeckung, Kamerabasis und Erkennung.

Historischer Live-Nachweis vor Bekanntgabe der Stativgrenze (2026-11-09):

| Optisches Zentrum / Zielpunkt | Tisch-Ecken im geometrischen Bild | Erkannte Ecken links / rechts | Reprojektions-RMS links / rechts |
|---|---|---:|---:|
| [1.8,0,3.0] / [0,0,1.4] m | alle acht | 18 / 24 | 0,069 / 0,061 px |
| [1.8,0,2.6] / [0,0,1.1] m | alle acht | 20 / 24 | 0,054 / 0,096 px |

Das sind einzelne Erkennungsnachweise bei damaligen Armstellungen, keine
Sichtbarkeitsgarantie für alle Bewegungen oder belastbare Extrinsikkalibrierung.
Die Kamera wurde für den Höhenvergleich ohne Zellneustart umgesetzt und danach
damals auf die 3-m-Pose zurückgestellt. Diese wurde inzwischen durch die
oben dokumentierte 2-m-Pose ersetzt. Keine Gelenkbefehle durch diese Werkzeuge.

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
