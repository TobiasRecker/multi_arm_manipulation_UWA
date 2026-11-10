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

- Nutzerziel vom 2026-11-10: Simulation und die beiden rechten gemessenen URs
  gleichzeitig in RViz darstellen. `uwa_cell_visualization` überträgt nur die
  beiden JointState-Eingänge von Domain66 nach64, niemals Kommandos/Services/
  Actions. Reale Anzeigeframes/Gelenke ausschließlich mit `real_`-Präfix;
  Simulations-Topics/TFs nicht überschreiben. Zielzeitstempel auf die Anzeige-
  Simulationsuhr umsetzen, originale Hardware-Nachrichten unverändert lassen.
  Fehlende/veraltete Daten zeigen, keine erfundenen Null-/Initialposen anzeigen.
  Montageposen aus zentralem Zelllayout bleiben vorläufig, keine automatische
  Kalibrierung behaupten. Anzeige darf Hardware nicht einschalten/bewegen.
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
- Statische OAK4-D als Übersicht auf einem Stativ rechts neben der Zelle:
  `overview_camera` in derselben Layout-YAML verwenden, Pose/Look-at/FOV als
  Designannahmen behandeln. Ihre eigene Gazebo-Entität/TF lässt sich ohne
  Zellneustart neu laden. Keine Kamera-Designänderung darf Arme zurücksetzen.
  Nutzerkorrektur vom 2026-11-09: vorhandenes Stativ erreicht **höchstens 2 m**;
  aktuelle Montagevorschläge daran ausrichten. Die früheren 3-/2,6-m-Posen
  sind nur historische Designversuche, keine umsetzbare Standardmontage.
  Zwei zusätzliche OAK-Kameras sind laut Nutzer für tote Winkel verfügbar.
  Die erste wurde per USB als **OAK-D Pro AF (RVC2)** identifiziert (2026-11-09);
  die frühere Vermutung „beide OAK-D-S2-FF“ ist überholt. Zweites Modell noch
  ungeprüft. Montage/Einsatz offen; keine Kalibrierung der Zusatzkameras voraussetzen.
  Beide ChArUco-Boards aus echten Bildern prüfen; reine Sichtfeldprojektion
  beweist weder fehlende Verdeckung noch kalibrierte Genauigkeit. Das bisher
  nur visuelle Stativ ist kein Hindernis in der MoveIt-PlanningScene.
- ChArUco-Boards zentral je Tisch und Kameras initial darauf ausrichten.
  Präzisiertes Nutzerziel (2026-11-09): einen Tisch absichtlich bewegen und
  relative Tischpose/Bewegung messen und kompensieren. Boards bleiben starr
  an ihren Tischen; ihre weltfesten Posen dürfen nicht vorausgesetzt werden.
  Kameramontagen zu ihrem Träger getrennt von veränderlichen Tischposen schätzen.
  Option: OAK auf rechtem Tisch schaut auf linkes Board. Montage ist relativ zum
  rechten Tisch konstant, auch wenn dieser bewegt wird. Zur Einmessung ein
  separates bewegliches Board verwenden, Tischboards dafür nicht versetzen.
  Raumfeste Kamera, tischfeste Kamera und Tisch-zu-Tisch-Messung unterscheiden;
  Simulation-Ground-Truth bleibt unabhängig von der bildbasierten Schätzung.
  Referenzen für diese Kalibrierung sind `left_table_top` / `right_table_top`.
  OpenCV-Musterframe: Ursprung an der Musterecke ohne Rand, Z in die Platte.
  Bildschätzung und Ground-Truth-Vergleich getrennt halten; keine Ground Truth
  zur Auswahl/Initialisierung der PnP-Lösung verwenden. Bekannte Hand-Auge-
  Transformation nicht als aus einer Einzelansicht neu kalibriert bezeichnen.
- Simulation isoliert betreiben: Domain 64, lokale Discovery, Partition `uwa_cell_sim`.
  Physisches Inventar getrennt in `config/hardware_inventory.yaml`:
  `right_rear`=192.168.8.170, `right_front`=192.168.8.103, OAK4=192.168.8.238.
  Nutzerzählung „erster/zweiter“ ist zufällig; nur stabile Arm-IDs verwenden.
  Kabel laut Nutzer am2026-11-10 ersetzt. Roboterrouten geprüft über Ethernet
  enp87s0, PC192.168.8.209. Keine aktive Sonderbehandlung für die frühere
  Funkanbindung, historische Messwerte nicht in Ethernetwerte umdeuten.
  Nutzerziel vom 2026-11-10: reale Hand-Auge-Erprobung zuerst ausschließlich
  `right_rear`; Bildzugriff und manuell aufgenommene Messreihe vor automatischen
  Hardwarefahrten prüfen. Bestehender Kalibrierbackend bleibt Simulation-only;
  HTTP-Bildempfang ist kein Nachweis eines frischen Belichtungszeitpunkts.
  Nutzerpräferenz desselben Tages: Wrist-Fokus möglichst vom PC per Skript/
  Schieberegler steuern. Fehlende öffentliche API nicht als grundsätzliche
  Unmöglichkeit ausgeben; USB-Anwenderberichte von am Gerät geprüfter Funktion
  unterscheiden. Fokusstellwerte nicht ohne Kennlinie als Meter interpretieren.
  Seit demselben Tag Kamera-Schreibtest/Qt-Fokusfenster für right_rear genehmigt
  und umgesetzt: Kameraeinstellungen sichern, ausschließlich Fokus ändern,
  Bildwirkung/Readback prüfen; keine Robotermotion daraus ableiten.
  Seit 2026-11-09 ist MoveIt-Kollisionsprüfung für die automatische Kalibrierung
  umgesetzt. Allgemeine kooperative Planung und Hardware-Anbindung bleiben Folgearbeit.
- Automatische Hand-Auge-Kalibrierung: unbekannte Kameraextrinsics aus mehreren
  Stellungen schätzen, nominelle Montagen ausschließlich zum Planen verwenden.
  Validierungsbilder vor Aufnahme festlegen und nie zum Fit verwenden. Ground
  Truth erst nach dem Fit getrennt vergleichen. Linkes/rechtes Tischpaar getrennt.
- Genehmigte Bedienung: eigene Qt-GUI für die Kalibrierung mit Vorbereitung,
  Start, Pause/Fortsetzen, jederzeit erreichbarem Stopp und explizitem Übernehmen.
  rqt bleibt die manuelle Zellsteuerung. Seit dem Folgeauftrag vom 2026-11-09
  standardmäßig links vorne + rechts hinten, danach links hinten + rechts vorne
  parallel kalibrieren; andere Arme vorher seriell zur Seite parken. Alle Wege
  gegen die vollständige MoveIt-Szene und getrennte gepufferte Bewegungsräume
  prüfen; blockierte Wege ablehnen. Stopp/Pause betreffen das gesamte aktive Paar.
  Einzelarmmodus bleibt als Auswahl erhalten; keine automatische Rückfahrt nach Stopp.
- Übernommene Kalibrierung ausschließlich als versioniertes Profil und separates
  `calibrated/`-TF-/Planungsmodell aktivieren. Physische Gazebo-Montagen und
  Ground-Truth-Modell erhalten. Keine automatische Rückfahrt nach Stopp/Fehler.
  Sitzungen/Rohbilder unter `$UWA_WS/setup/calibration/` nicht einchecken.

## Verbindliche Bedienerwartungen

- Nutzerauftrag2026-11-10: MuR-artiges manuelles Jogging, zunächst right_rear,
  mit demselben IntegratedCartesianAdmittanceController/J-PARSE. Nachgiebigkeit
  standardmäßig AUS: admittance und wrench_twist_gain null, keine FT-Pflicht.
  Gainänderungen des on_init-Plugins durch inaktives Neuladen anwenden, nicht
  bloß als dynamische ROS-Parameter setzen. Hold-to-jog/Loslass-Stopp, Base-Frame,
  keine automatische Fahrt durch Öffnen des Dialogs oder Aktivieren des Reglers.

- Nutzerhinweis vom 2026-11-10: Monitor mit schwachem Kontrast. Klickannahme
  deutlich hervorheben, nicht nur durch subtile Standard-Buttonzustände.
  Dauerhafte Rückmeldung mit großen Textlabels RECEIVED/RUNNING/DONE/FAILED,
  Aktionsname, Verlauf/Fehlerdetail und Laufzeitanzeige. Automatische Statuspolls
  dürfen ein manuelles Fehlerergebnis nicht überschreiben. Bedienung auf Englisch.
- Nutzerwunsch vom 2026-11-10: UR-GUI vollständig **Englisch**, einschließlich
  Beschriftungen, Tooltips, eigener Meldungen und Startmenüeintrag **UWA Arms**.
  Gesprächssprache bleibt Deutsch. **Save logs** muss während laufender
  Operationen erreichbar bleiben und aktuelle Sitzung/Prozessausgaben/zugehörige
  ROS-Logs lokal mit Status-Snapshot exportieren. Eindeutige Sitzungsordner,
  keine bloß gekürzte Bildschirm-Logkopie; älteren übernommenen Treiberkontext
  kennzeichnen. Exporte unter `setup/logs/uwa-control/exports/`, neuester Pfad
  in `setup/logs/uwa-control/latest-export.txt`. Keine Roboterbefehle beim Export.
- Nutzerauftrag vom 2026-11-10: lokale Vierarm-Vorbereitung und vereinfachte
  eigene UWA-GUI mit Armauswahl oben links, ohne SSH/rsync/mobile Infrastruktur.
  Gemeinsamer UR-Start und Controller bleiben im MATCH-Repo (`match_ur_hardware`,
  `mur_control`, `mur_launch_hardware`); `uwa_cell_control` referenziert sie.
  Physische Konfiguration ausschließlich aus `config/hardware_inventory.yaml`.
  App **UWA Arms**: Mock als Standard in Domain67, Hardware in Domain66,
  jeweils lokale Discovery; Mock-Treiber/-Clients strikt von Hardware trennen; kein
  automatisches Power/Brake/Play beim Treiberstart. Vorhandene Ein-Gegenarm-
  Kollision nicht als vollständigen Vierarm-Kollisionsschutz darstellen.
  Neueste Nutzerkorrektur vom 2026-11-10: zusätzliche UWA-Sicherheitsgates
  entfernen. Keine Armzahl-, Dashboard-NORMAL/Remote/RUNNING/PLAYING-, exakte
  Programmpfad- oder GUI-Treiberbesitz-Sperre vor manuellen Operationen.
  Keine eigene Netzwerk-/Latenz-Sperre einführen. Native UR-/Treiber-
  Ablehnungen und vorhandene Kollisionsalgorithmen erhalten. Insbesondere keine
  UR-Sicherheitsfunktionen umgehen oder Stopps automatisch quittieren.
  Standardauswahl bleibt hinten rechts (`right_rear`). Tests des Agenten senden
  keine realen Power/Brake/Play/Ziele; laufende Hardwaretreiber erhalten.
  Technische Profil-/Portprüfung, Schutz gegen doppelte Treiberinstanzen und
  Aufräumen eigener Prozesse erhalten. Bedienung: `docs/ur_control_gui.md`.
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
