# UWA-Zelle – Ziele, Anforderungen und Übergabe

Stand der Zusammenfassung: **2026-11-09**, Zeitzone Australia/Perth.
Diese Datei fasst die bisherigen Gespräche und die überprüfte Implementierung
zusammen. Sie soll bei weiterer Arbeit mitgepflegt werden, nicht als unveränderlicher
Abschlussbericht dienen. Arbeitsregeln: [AGENTS.md](AGENTS.md); Bedienung: [README.md](README.md).

## Nutzerziele und Vorlieben

- Neue Roboter-Codebasis auf **ROS 2 Lyrical** unter **Ubuntu 26.04** aufbauen.
  Die bestehenden Jazzy-Repositories wurden dafür lokal angepasst.
- Einen digitalen Zwilling der echten Roboterzelle in Gazebo erstellen, im Repository
  `multi_arm_manipulation_UWA` unter `~/UWA_ws/src/`.
- Zunächst Geometrie und steuerbare Kinematik; kalibrierte Genauigkeit, MoveIt,
  kollisionsfreie kooperative Planung und Synchronisation mit echter Hardware später.
- Bestehende rqt-Gelenksteuerung verwenden; für diese Version keine eigene Roboter-GUI.
- Bequemer Start wie eine Desktop-App mit eigenem Icon und RViz-Konfiguration.
- **Neuester Bedienwunsch, 2026-11-09:** Der normale App-Klick soll die Punktewolke
  mitladen. Keine zusätzliche Rechtsklick-Aktion zum erstmaligen Anzeigen verlangen.
- Das Vier-Roboter-Icon gefällt dem Nutzer; nur der weiße Außenrahmen sollte
  transparent werden. Das ist umgesetzt, der dunkelblaue Hintergrund bleibt erhalten.
- Deutsch als bisherige Gesprächssprache; praktische, nachvollziehbare Bedienhinweise.
- **Explizit seit 2026-11-09:** Wichtige Ziele, Anforderungen, Entscheidungen und
  Vorlieben parallel in AGENTS-/Handover-Dateien festhalten.

## Aufbau der realen Zelle und Modellannahmen

Ursprung am Boden zwischen den Tischmitten. **X nach rechts, Y nach hinten,
Z nach oben**; „vorne“ ist die dem Nutzer zugewandte Seite (−Y).

| ID | UR-Typ | Tisch | Basis XYZ bei Standardaufstellung (m) | Basis-Yaw |
|---|---|---|---|---|
| `left_front` | UR5 | links | −0,45; −0,675; 0,90 | 0° |
| `left_rear` | UR7e | links | −0,45; +0,675; 0,90 | 180° |
| `right_front` | UR5e | rechts | +0,45; −0,675; 0,90 | −90° |
| `right_rear` | UR5e | rechts | +0,45; +0,675; 0,90 | +90° |

- Zwei Tische mit je **0,80 × 1,70 m**; Längskantenabstand **0,10 m**.
- Beide Roboter pro Tisch mittig über der Breite, längs symmetrisch mit **1,35 m**
  Montageabstand. Jeweils 0,175 m Abstand zur vorderen/hinteren Tischkante.
- Tischoberkante vorläufig **0,90 m**, Plattendicke und Beinbreite je **0,05 m**.
  Tische sind in dieser Simulationsversion fest zur Welt verankert; eine geänderte
  Tischpose wird nach Neustart übernommen und verschiebt beide montierten Roboter mit.
- Die echte Aufstellung ist beweglich: Maße/Posen zentral konfigurierbar halten.
- Je Arm Anfangsstellung `[0, −π/2, 0, −π/2, 0, 0]`; seit 2026-11-09
  Robotiq 2F-85 und Wrist Camera ergänzt (siehe Werkzeugabschnitt).
- Pro Arm kann eine individuelle Kinematik-Kalibrierdatei angegeben werden.
- Offizielle UR-Beschreibungen verwenden. UR7e hat eine eigene Parameterkonfiguration,
  teilt im installierten Upstream-Paket aber visuelle Meshes mit UR5e.

### Korrektur der Montageorientierungen, 2026-11-06

Der Nutzer gab die Kabelrichtungen als groben Anhaltspunkt an:

- Links vorne: Kabel zum Nutzer (−Y), ausdrücklich **−90° gegenüber der ersten Simulation**.
- Links hinten: Kabel nach hinten (+Y).
- Rechts vorne: Kabel nach links zur Mitte (−X).
- Rechts hinten: Kabel nach rechts außen (+X).

Daraus wurden die Yaw-Werte der obigen Tabelle übernommen und im laufenden TF-Baum
geprüft. Die vorherige pauschale Ausrichtung „vorne +90°, hinten −90°“ ist **überholt**.
Alle Winkel beziehen sich auf **`base_link`**. Der UR-Teach-Pendant-`base`-Frame
hat zusätzlich die in der offiziellen Beschreibung enthaltene 180°-Drehung.
Höhe, Yaw-Werte und Scan-Pose sind weiterhin **nicht kalibriert**.

## Implementierung und Schnittstellen

| Bestandteil | Zuständigkeit |
|---|---|
| `uwa_cell_description` | ament_cmake; Tische, offizielle UR-Modelle, gemeinsame Xacro-Datei |
| `uwa_cell_gazebo` | ament_python; Launch, Controller-Konfiguration, Scan-Import/Publisher, Prüfwerkzeuge |
| `uwa_cell_description/config/cell_layout.yaml` | Zentrale Layout-, Montage-, Anfangsstellungs- und Scan-Konfiguration |
| `uwa_cell_gazebo/rviz/cell.rviz` | Roboter, Tische, Grid, optionale Frames und Scan-Referenz |
| `scripts/` | Dienst-, Desktop-, RViz- und Scan-Helfer |

- Eine zusammenhängende Zelle `uwa_cell`, **24 eindeutige bewegliche Armgelenke**
  mit Präfixen `left_front_`, `left_rear_`, `right_front_`, `right_rear_`.
- Ein Manager `/uwa_cell/controller_manager`, ein `joint_state_broadcaster`, vier
  Arm- und vier Greifer-`JointTrajectoryController`, alle neun nach Start aktiv.
- Action je Arm: `/uwa_cell/<id>_trajectory_controller/follow_joint_trajectory`.
- Je Controller steht auch `joint_trajectory` als Topic bereit.
- Gazebo-Server und GUI getrennt starten. Der verpackte Jetty-GUI-Client wird
  direkt gestartet, damit Launch den richtigen Prozess beim Stoppen signalisiert.
- `clock_bridge.py` überträgt echte Gazebo-Simulationszeit über die installierten
  Python-Transport-Bindings und meldet sich vor dem ROS-Abbau explizit ab.

### Robotiq-Werkzeuge, Nutzerauftrag 2026-11-09

- Alle vier Arme sollen ihre Greifer und Wrist Cameras erhalten. Gemeldete
  Beispielgeräte: 2F Adaptive 2020 **S/N C-43008**, Wrist Camera 2019
  **S/N Q-021114**. Der Nutzer hat ausdrücklich **2F-85 (85 mm)** bestätigt.
  Die Nummern sind keine bestätigte Zuordnung zu einem bestimmten Arm.
- Montagekorrektur des Nutzers: Kameralinse auf der vom UR-Werkzeug-I/O-Stecker
  abgewandten Seite. UR-`tool0` +Y zeigt vom Stecker weg; `camera_yaw: 0`
  setzt die Linse entsprechend auf +Y. Kein zusätzlicher TCP-Offset angenommen.
- Greifer-Geometrie, Massen und Kinematik aus PickNik `ros2_robotiq_gripper`,
  festgehaltener Commit und BSD-Lizenz in `THIRD_PARTY.md` / `LICENSES/`.
  Nur Modelldaten übernommen; keine Hardwaretreiber oder seriellen Verbindungen.
- Ein antreibendes Knöchelgelenk je Greifer (0 offen, 0,8 rad geschlossen),
  fünf Mimic-Gelenke. Insgesamt 48 bewegliche Gelenke, 28 Positionsbefehle.
  Greiferaction: `/uwa_cell/<id>_gripper_controller/follow_joint_trajectory`;
  über denselben rqt-Controllerwähler bedienbar.
- Wrist Camera als primitive Geometrienäherung, 13,5 mm Zusatzhöhe ohne
  separate Werkzeugplatte, 160 g; Sensor `[0; 35,7; −0,1]` mm, 30° Neigung
  nach außen, nominell 50° horizontal, 640 × 480, zunächst 10 Hz je Kamera.
  Datenquelle: Robotiq-Handbuch 2019 (Links in `THIRD_PARTY.md`).
- `tools` in `cell_layout.yaml` enthält gemeinsame Einstellungen; je Roboter
  sind partielle Überschreibungen möglich. Kamera und Greifer einzeln abschaltbar.
- ROS-Topics: `/uwa_cell/<id>/wrist_camera/image_raw` und `camera_info`,
  Sensor-Data-QoS, Frame `<id>_wrist_camera_optical_frame`.
  `camera_bridge.py` verwendet wie die Uhrbrücke Gazebo-Python-Bindings mit
  expliziter Abmeldung vor Shutdown. Gazebo-Sensors-System ergänzt.
- Grenzen: Keine herstellergenaue Kameragehäuseform, Objektivkalibrierung,
  URCap-Bildverarbeitung, Autofokus-/LED-Steuerung oder adaptive Kontaktmechanik.
  MoveIt und reale Hardware bleiben Folgearbeit.
- Prüfstand 2026-11-09: beide Pakete gebaut, **24 Offline-Tests erfolgreich**;
  vier gültige RGB-/CameraInfo-Streams, korrekte optische TFs und Zeitstempel,
  neun aktive Controller. Alle vier Greifer einzeln geschlossen/geöffnet und
  zurückgestellt, Mimic-Abweichung < 0,03 rad, andere Gelenke < 0,01 rad Drift.
  Alle vier Arme mit Werkzeugen am Handgelenk bewegt und zurückgestellt;
  tatsächliche Zellwurzel stabil. Installiertes rqt: acht Controller, je
  sechs Armeditoren/ein Greifereditor, gültige Haltebefehle.
  Belege: `setup/logs/uwa-cell-tools-{build,tests,verification,arm-verification,rqt-check}*`
  und `setup/logs/uwa-cell-camera-images/` im Workspace.
- EGL-Betrieb ohne Gazebo-Fenster ebenfalls mit vier Bildstreams und neun
  aktiven Controllern geprüft: `setup/logs/uwa-cell-tools-headless-verification.json`.
  Ein erster Start hatte Controller-Service-Timeouts; die Statusprüfung fragt
  nun höchstens alle 0,5 s ab, der erneute Headless-Start war erfolgreich.
  Uhr-/Kamerabrücke und Server beim Wechsel sauber beendet; Journalbeleg
  `setup/logs/uwa-cell-tools-restart.log`. Keine ungeprüfte Ursache des Timeouts behaupten.
- Das installierte Physik-Backend meldet fehlende native Mimic-Constraints.
  Die getestete Positionskopplung übernimmt `gz_ros2_control`. Kein Nachweis
  realistischer Kraftkopplung oder belastbarer Objektgriff-Physik.

## Bedienung: aktuelles Sollverhalten

- Startmenü: **UWA Cell Simulation** startet Gazebo, rqt, RViz **und Scan-Publisher**.
- Auch die Desktop-Aktion **RViz öffnen** startet den Scan. **Punktewolke anzeigen**
  bleibt als zusätzliche Aktion vorhanden; **Simulation beenden** stoppt alle drei Dienste.
- Dienste: `uwa-cell-sim`, `uwa-cell-rviz`, `uwa-cell-scan` (systemd-Benutzerdienste).
- Wiederholtes Anklicken verwendet laufende Dienste weiter; die bestehende Simulation
  und deren Gelenkzustände werden dabei nicht unnötig neu gestartet.
- Seit 2026-11-09 holt `scripts/show_cell_windows.py` die vorhandenen XWayland-Fenster
  nach vorne und stellt minimierte Fenster wieder her. Nur PIDs aus den Zell-Diensten
  werden berücksichtigt. Normaler Start fokussiert Gazebo, RViz-/Scan-Aktionen RViz.
  Der Desktop-Eintrag verwendet `StartupWMClass=Gazebo GUI`.
  Kurzlebige Splash-/Menüfenster werden ausgelassen; ein zwischenzeitlich
  verschwundenes Fenster darf den Launcher nicht mit X11-`BadWindow` abbrechen.
- Direktes `cell.sh start` / `ros2 launch ...` behält seine ursprünglichen Defaults:
  GUI und Controller-GUI an, RViz und Scan aus. Das ist bewusst vom Desktop-Start getrennt.
- `cell.sh rviz` öffnet direkt nur RViz; `cell.sh scan` schaltet nur den Scan hinzu.
  Die Desktop-Aktionen kombinieren diese Helfer für die gewünschte Bedienung.
- `MoveCamera` ist explizit das erste RViz-Werkzeug. Linke Maustaste: drehen;
  Mausrad: zoomen; mittlere Maustaste: verschieben. Views-Panel vorhanden.
- Icon: `assets/uwa-cell.png`, RGBA mit transparentem Außenrand. Installer verwendet
  einen inhaltsabhängigen Dateinamen unter `~/.local/share/icons/`, damit GNOME
  nach Bildänderungen nicht das alte Icon aus dem Cache weiterverwendet.
- Desktop-Datei: `~/.local/share/applications/uwa-cell.desktop`.
  Installer: `python3 scripts/install_desktop.py` (als normaler Nutzer, ohne sudo).

## Punktewolke und Grenzen der Referenz

- Original: `~/GoogleDrive/UWA/UR Setup.ply`, ca. **215 MB**, **867.068 Einträge**.
  Binäre Little-Endian-Gaussian-Splat-PLY, keine fertige Dreiecksgeometrie.
- Import übernimmt Zentren und Grundfarben aus SH-DC-Feldern; Opazität aus Logits,
  Ausdehnung aus logarithmischen Skalen. Keine Kollisionen aus dem Scan ableiten.
- Defaults: Mindestdeckkraft **0,1**, maximale Splat-Skala **0,05** Scan-Einheiten,
  Voxelgröße **0,01** Scan-Einheiten, höchstens **200.000 Punkte**.
- Ungültige Werte und ungeeignete Splats filtern; Reduktion und Punktbegrenzung
  deterministisch. Quelle unverändert auf Drive lassen und nicht ins Git aufnehmen.
- Cache: `$XDG_CACHE_HOME/uwa_cell/scans` bzw. `~/.cache/uwa_cell/scans`, NPZ ohne Pickle.
- Publisher: `/uwa_cell/scan_reference`, `PointCloud2`, Reliable / Transient Local.
  Frame `uwa_scan_reference`; statischer Transform von `world`.
- Ausgangswerte: Maßstab **1**, Identitätspose, ausdrücklich **UNREGISTERED**.
  Scan-Einheiten sind nicht als Meter bestätigt. Die Wolke kann gekippt/versetzt sein.
- Ein fehlender Scan darf Gazebo nicht verhindern. Bei `scan:=false` liest der
  direkte Launch den Scan nicht. **Aktuelle Grenze:** Auch zur Cache-Auswahl fragt
  der Importer noch Dateimetadaten des Originals ab; kein garantierter Offline-Fallback
  bei vollständig fehlendem Drive-Mount. Das ist keine bereits erledigte Anforderung.

## Behobene Probleme und Entscheidungen

| Datum | Beobachtung / Entscheidung | Ergebnis |
|---|---|---|
| 2026-11-06 | Gazebo-Wrapper und Clock-Bridge beendeten sich nicht sauber | Direkter GUI-Client; eigener kleiner Clock-Adapter; gezielte Dienststeuerung |
| 2026-11-06 | Nur diese RViz-Konfiguration erlaubte kein Drehen/Zoomen | Fehlende `Tools`-Liste ergänzt; echte Maus-/Mausrad-Ereignisse geprüft |
| 2026-11-06 | Weißer Außenrahmen am ansonsten gewünschten Icon | Mit Imagegen transparent gemacht; Motiv und dunkelblaues Feld erhalten |
| 2026-11-09 | App zeigte keine Wolke, manuell gestarteter Scan schon | Scan fehlte im normalen Desktop-Start; Start und RViz-Aktion laden ihn jetzt automatisch |
| 2026-11-09 | Nutzer wünscht dauerhaftes Festhalten der Gespräche | Workspace-/Projekt-AGENTS und diese Übergabe angelegt; fortlaufende Pflege vereinbart |
| 2026-11-09 | Icon-Klick scheint nichts zu starten, obwohl alle drei Dienste und Fenster laufen | Vorher nur „läuft schon“; nun Wiederherstellen/Aktivieren der vorhandenen Zell-Fenster ohne Neustart |

Ein früher Tracing-Schalter löste den Clock-Bridge-Absturz nicht vollständig;
ihn nicht als fertige Lösung wieder einführen. Zusätzlich wurde am 2026-11-06
ein einzelner RViz-Absturz beim Fensterbetrieb/-ende im Journal beobachtet.
Dessen Ursache ist nicht abschließend geklärt; bei erneutem Auftreten Journal
und Backtrace untersuchen, nicht automatisch mit dem behobenen Kamerafehler gleichsetzen.

Am **2026-11-09** wurde während dieser Prüfung zusätzlich ein neuer Simulationsstart
mit rückwärts springender Uhr beobachtet. Das noch geöffnete RViz brach anschließend
mit `tf2::LookupException: Static cache is empty` für `uwa_scan_reference` → `world`
ab. Die Desktop-Aktion konnte RViz erneut öffnen. Eine grundsätzliche Behebung dieses
Zeitsprung-/TF-Problems ist damit **nicht** nachgewiesen; bei weiteren Simulations-Resets
beachten. Die Zell-Simulation wurde für die Fensteraktivierung selbst nicht zurückgesetzt.

## Prüfstand und Belege

Historisch geprüfte Ergebnisse, keine Behauptung einer erneuten Gesamtprüfung
bei jeder Dokumentationsänderung:

- **2026-11-06:** Beide neuen Pakete gebaut, Systemabhängigkeiten vorhanden;
  **11 Offline-Tests** erfolgreich (Layout/TF-Topologie, Tischumpositionierung,
  Scan-Farben, Filter, ungültige Zahlen, Punktlimit und fehlerhafte PLY-Dateien).
- **2026-11-06:** Simulationszeit läuft, 24 endliche Gelenkzustände, fünf aktive
  Controller; tatsächliche Gazebo-Wurzel bleibt verankert.
- Alle vier Arme einzeln per Action am Handgelenk um 0,1 rad bewegt und zurückgestellt;
  Zielabweichung < 0,03 rad, Drift anderer Arme < 0,01 rad.
- Standard-rqt-Plugin: vier Controller auswählbar, sechs Gelenkeditoren je Arm,
  gültige Haltebefehle publiziert. Drei erfolgreiche Clock-Start-/Stopp-Zyklen.
- RViz: Mausdrehen und Zoom am realen Viewport geprüft; Gegenprobe ohne Tools-Liste
  reproduziert den Fehler. RViz meldete 200.000 Punkte und Transform „Ok“.
- **2026-11-09:** Tatsächlichen installierten App-Eintrag über `gio launch` geprüft:
  200.000 endliche Punkte, Welt-Transform vorhanden, genau ein Scan-Publisher;
  vorhandene Simulations-/RViz-Prozesse erhalten; wiederholtes Anklicken ohne Duplikat.
- **2026-11-09, Fensteraktivierung:** Installierter App-Aufruf fokussiert das vorhandene
  Gazebo-Fenster; Dienst-PIDs von Simulation, RViz und Scan bleiben gleich.
  Eine gezielt minimierte RViz-Ansicht wurde über die echte Desktop-Aktion wiederhergestellt
  und fokussiert. Es war kein Reset der laufenden Roboter nötig.

Belege unter `~/UWA_ws/setup/logs/`, insbesondere:

- `uwa-cell-tests.log`, `uwa-cell-build.log`
- `uwa-cell-motion-verification.json`, `uwa-cell-mount-orientation-verification.json`
- `uwa-cell-rqt-check.log`, `uwa-cell-python-clock-verification.log`
- `uwa-cell-rviz-interaction.log`, `uwa-cell-rviz-negative-check.log`
- `uwa-cell-rviz-interaction.png`, `uwa-cell-scan-verification.json`
- `uwa-cell-desktop-scan-verification.json`
- `uwa-cell-app-window-verification.json`

Temporäre RViz-C++-Testprogramme lagen unter `/tmp/uwa-rviz-check`; deren
Fortbestand nicht voraussetzen. Dauerhafte Prüfkommandos stehen in der README.

Momentaufnahme am 2026-11-09 bei Anlage dieser Datei: Zell-, RViz- und Scan-Dienst
aktiv; separate MuR-Simulation inaktiv. Vor weiterer Prozessarbeit neu prüfen.

## Umgebung und vorherige Workspace-Arbeit

- Workspace `~/UWA_ws`; ROS `/opt/ros/lyrical`; Gazebo Jetty (bei Einrichtung 10.5.0).
- Zell-Umgebung: `source scripts/env.bash` innerhalb dieses Repositories;
  Domain **64**, lokale Discovery, Partition **`uwa_cell_sim`**, `GZ_IP=127.0.0.1`.
- Allgemeines Setup: `~/UWA_ws/setup/lyrical_env.bash`, standardmäßig Domain **62**.
- Separate MuR-Simulation: `setup/start_mur_simulation.sh`, Benutzerdienst
  `uwa-mur620a-sim`, Domain **63**, Partition **`uwa_mur620a_sim`**.
  Nicht mit der Vierarm-Zelle oder echter Hardware vermischen.
- Weitere vom Nutzer gewünschte Repositories: `match_mur_gui`,
  `match_mobile_robotics_jazzy`, `match_mir_camera_calibration`,
  `match_cooperative_handling`, `oak_camera_calibration`, `match_software_utilities`
  (ursprünglich aus der GitHub-Organisation `match-ROS`).
- Bestehende Lyrical-Portierungen mit lokalen Änderungen auch in Submodulen:
  [Patch-Übersicht](../../setup/patches/lyrical-controllers/README.txt),
  [Manifest](../../setup/patches/lyrical-controllers/manifest.json).
  Laut Übersicht sind die Patches bereits angewendet; nicht erneut blind anwenden.
- Ursprüngliche Einrichtungshelfer: `setup/install_lyrical.sh`, `setup/check_lyrical.sh`,
  `setup/test_controllers_lyrical.sh`. Interaktive sudo-Anmeldung erfolgt lokal durch den Nutzer.
- Google Drive wurde via rclone unter `~/GoogleDrive` eingebunden. Setup-Hinweise
  liegen unter `setup/google-drive/`; Mount/Anmeldung bei Bedarf prüfen. Keine
  Zugangsdaten in Git oder in diese Übergabe kopieren.

## Offene Ziele / noch nicht freigegebene Genauigkeitsannahmen

1. Echte Tischhöhe und Montageposen messen, Basisorientierungen kalibrieren.
2. Individuelle UR-Kinematikdateien übernehmen, sobald verfügbar.
3. Scan-Maßstab, Achsen und Welt-Pose registrieren; daraus keine unbestätigte
   Montagekalibrierung automatisch als wahr übernehmen.
4. Später MoveIt und kooperative/kollisionsfreie Bewegungsplanung ergänzen.
5. Später explizit geplante Hardware-Anbindung und Synchronisation untersuchen.

Die Liste beschreibt offene Arbeitspakete, keinen Auftrag, sie ohne weitere
fachliche Abstimmung sofort alle umzusetzen. Aktuelle Konfigurationswerte und
Bedienung haben Vorrang vor überholten Gesprächsständen.
