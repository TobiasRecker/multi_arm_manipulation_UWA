# Arbeitsregeln für die UWA-Roboterzelle

## Vor der Arbeit

- [ACTIVE_WORK.md](ACTIVE_WORK.md) und aktive Einträge unter `work/` lesen.
  Eigene Aufgabe dort vor Änderungen eintragen und laufend aktualisieren;
  Statusdatei je Aufgabe verwenden, fremde Einträge erhalten. Dienstneustarts
  und gemeinsame Dateibereiche nennen, bestehende Diffs vor Edits erneut prüfen.
- [HANDOVER.md](HANDOVER.md) enthält Ziele, Entscheidungen, bekannte Grenzen und
  Prüfnachweise; [README.md](README.md) enthält Bedienung und Build-Anweisungen.
- Die übergeordneten Workspace-Regeln gelten zusätzlich.
- `HANDOVER.md` bei relevanten Anforderungen, Korrekturen, Entscheidungen und
  Ergebnissen parallel aktualisieren; dauerhafte Arbeitsregeln hier ergänzen.
  Diese laufende Dokumentation ist ein ausdrücklicher Nutzerwunsch vom 2026-11-09.
- Neue Entscheidungen mit Datum festhalten und widersprechende alte Angaben
  bereinigen. Momentaufnahmen laufender Prozesse nicht als dauerhafte Fakten behandeln.

## Fachliche Leitplanken

- Ziel ist der digitale Zwilling der echten UWA-Zelle mit vier UR-Armen auf
  zwei beweglich positionierbaren Tischen. Plattform: ROS 2 Lyrical / Gazebo Jetty.
- Geometrie, Tischposen, Montageposen und Anfangsstellungen kommen zentral aus
  `uwa_cell_description/config/cell_layout.yaml`; keine parallelen Zahlenkopien
  als zusätzliche Konfigurationsquelle einführen.
- Weltachsen: X rechts, Y hinten, Z oben. Montageposen beziehen sich auf
  **URDF `base_link`**, nicht auf den um 180° gedrehten UR-`base`-Frame.
- Die aktuellen Kabelrichtungen und Yaw-Werte aus der Übergabe erhalten.
  Sie ersetzen die ursprüngliche pauschale Front-/Heck-Ausrichtung.
- Tischhöhe und Montagewinkel bleiben Schätzungen bis zur Kalibrierung.
  Scan-Daten dürfen nicht stillschweigend zu kalibrierten Posen erklärt werden.
- 24 eindeutige Armgelenke, vier native Arm-Trajektoriencontroller und ein gemeinsamer
  Controller-Manager unter `/uwa_cell` beibehalten. Seit 2026-11-09 ergänzen vier
  Robotiq-2F-85-Greifer je einen eigenen Controller und fünf gekoppelte Fingergelenke.
- Wrist-Camera-Linse gegenüber dem UR-Werkzeug-I/O-Anschluss montieren:
  im UR-`tool0`-Frame auf +Y. Werkzeugparameter zentral in der Layout-YAML pflegen;
  primitive Kamerageometrie und nominelle Optik nicht als kalibriertes CAD ausgeben.
- ChArUco-Boards zentral je Tisch und Kameras initial darauf ausrichten.
  Referenzen für diese Kalibrierung sind `left_table_top` / `right_table_top`.
  OpenCV-Musterframe: Ursprung an der Musterecke ohne Rand, Z in die Platte.
  Bildschätzung und Ground-Truth-Vergleich getrennt halten; keine Ground Truth
  zur Auswahl/Initialisierung der PnP-Lösung verwenden. Bekannte Hand-Auge-
  Transformation nicht als aus einer Einzelansicht neu kalibriert bezeichnen.
- Simulation isoliert betreiben: Domain 64, lokale Discovery, Partition `uwa_cell_sim`.
  Seit 2026-11-09 ist MoveIt-Kollisionsprüfung für die automatische Kalibrierung
  umgesetzt. Allgemeine kooperative Planung und Hardware-Anbindung bleiben Folgearbeit.
- Automatische Hand-Auge-Kalibrierung: unbekannte Kameraextrinsics aus mehreren
  Stellungen schätzen, nominelle Montagen ausschließlich zum Planen verwenden.
  Validierungsbilder vor Aufnahme festlegen und nie zum Fit verwenden. Ground
  Truth erst nach dem Fit getrennt vergleichen. Linkes/rechtes Tischpaar getrennt.
- Genehmigte Bedienung: eigene Qt-GUI für die Kalibrierung mit Vorbereitung,
  Start, Pause/Fortsetzen, jederzeit erreichbarem Stopp und explizitem Übernehmen.
  rqt bleibt die manuelle Zellsteuerung. Nur ein Arm bewegt sich; alle Wege
  werden gegen die vollständige MoveIt-Szene geprüft. Blockierte Wege ablehnen.
- Übernommene Kalibrierung ausschließlich als versioniertes Profil und separates
  `calibrated/`-TF-/Planungsmodell aktivieren. Physische Gazebo-Montagen und
  Ground-Truth-Modell erhalten. Keine automatische Rückfahrt nach Stopp/Fehler.
  Sitzungen/Rohbilder unter `$UWA_WS/setup/calibration/` nicht einchecken.

## Verbindliche Bedienerwartungen

- Die App **UWA Cell Simulation** soll mit normalem Klick Gazebo, rqt, RViz
  **und den Scan-Publisher** starten. Auch ihre Aktion **RViz öffnen** lädt den Scan.
  Den früheren App-Standard ohne Scan nicht wieder einführen.
- Der direkte Terminal-Launch darf weiterhin ohne Scan starten; die Simulation
  muss auch bei fehlendem Drive/Scan funktionieren.
- Wiederholte App-Aufrufe sollen vorhandene Dienste weiterverwenden und weder
  doppelte Publisher erzeugen noch die laufende Simulation unnötig zurücksetzen.
  Bereits geöffnete Fenster wiederherstellen/nach vorne holen; „Dienst aktiv“
  allein erfüllt die sichtbare Bedienerwartung beim erneuten Icon-Klick nicht.
- RViz muss explizite Kamera-Werkzeuge enthalten: `MoveCamera` als erstes Tool,
  außerdem Interact, Select, FocusCamera und Measure. Orbit-Drehen und Zoom müssen funktionieren.
- Das App-Icon gefällt dem Nutzer. Außenrand transparent lassen, das dunkelblaue
  abgerundete Feld und das Vier-Roboter-Motiv erhalten. Den weißen Rand nicht zurückbringen.
- Originalscan auf Google Drive belassen; keine PLY-Dateien oder Scan-Caches einchecken.
- Scan-Bereinigung: 4 m Kugelradius in Weltmetern um den Mittelpunkt der vier
  Roboterbasen; die aufgenommenen Roboter durch feste Scan-Masken ausblenden.
  Masken nicht an die aktuellen bewegten Modell-TFs koppeln. Bei Änderung der
  Scanregistrierung die Masken neu prüfen; Rohdaten und Importcache erhalten.

## Prüfen und übergeben

- Build, Umgebungsvariablen und Prüfkommandos aus der README verwenden.
- Passend zur Änderung prüfen: bei Layoutänderungen Modell/TF, bei Controlleränderungen
  zusätzlich Simulation und gezielte Bewegungen, bei App-Änderungen den **installierten**
  Desktop-Eintrag statt nur einen manuell gestarteten ROS-Knoten testen.
- Eine aktivierte PointCloud-Anzeige oder „Status: Ok“ allein beweist keinen Scan-Empfang:
  Publisher, empfangene Punkte und den Transform zur Welt prüfen.
- Bei Änderungen an Setup/Startmenü die nötige Installation konkret durchführen
  und die Bedienung in der README mitpflegen. Bestehende lokale Änderungen erhalten.
- Dokumentation: belegte Erfolge mit Datum/Logpfad und offene Einschränkungen nennen;
  keine neuen Tests oder Hardware-Freigaben behaupten, die nicht erfolgt sind.
