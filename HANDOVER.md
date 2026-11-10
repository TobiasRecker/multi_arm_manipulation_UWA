# UWA-Zelle – Ziele, Anforderungen und Übergabe

Stand der Zusammenfassung: **2026-11-10**, Zeitzone Australia/Perth.
Diese Datei fasst die bisherigen Gespräche und die überprüfte Implementierung
zusammen. Sie soll bei weiterer Arbeit mitgepflegt werden, nicht als unveränderlicher
Abschlussbericht dienen. Arbeitsregeln: [AGENTS.md](AGENTS.md); Bedienung: [README.md](README.md).

## Nutzerziele und Vorlieben

- Neue Roboter-Codebasis auf **ROS 2 Lyrical** unter **Ubuntu 26.04** aufbauen.
  Die bestehenden Jazzy-Repositories wurden dafür lokal angepasst.
- Einen digitalen Zwilling der echten Roboterzelle in Gazebo erstellen, im Repository
  `multi_arm_manipulation_UWA` unter `~/UWA_ws/src/`.
- Zunächst Geometrie und steuerbare Kinematik. Seit 2026-11-09 zusätzlich automatische
  Hand-Auge-Kalibrierung mit MoveIt-Kollisionsprüfung; allgemeine kooperative Planung
  und Synchronisation mit echter Hardware bleiben Folgearbeit.
- rqt für manuelle Gelenksteuerung erhalten. Neuer ausdrücklicher Auftrag vom
  2026-11-09: eine eigene Qt-GUI für Vorbereitung, Aufnahme, Überwachung, Stopp und
  Übernahme der automatischen Kalibrierung (ersetzt die frühere Einschränkung dafür).
- Bequemer Start wie eine Desktop-App mit eigenem Icon und RViz-Konfiguration.
- **Neuester Bedienwunsch, 2026-11-09:** Der normale App-Klick soll die Punktewolke
  mitladen. Keine zusätzliche Rechtsklick-Aktion zum erstmaligen Anzeigen verlangen.
- Das Vier-Roboter-Icon gefällt dem Nutzer; nur der weiße Außenrahmen sollte
  transparent werden. Das ist umgesetzt, der dunkelblaue Hintergrund bleibt erhalten.
- Deutsch als bisherige Gesprächssprache; praktische, nachvollziehbare Bedienhinweise.
- **Explizit seit 2026-11-09:** Wichtige Ziele, Anforderungen, Entscheidungen und
  Vorlieben parallel in AGENTS-/Handover-Dateien festhalten.

## Englische UR-GUI und Sitzungsdiagnose, 2026-11-10

- Neuer Nutzerhinweis: schwacher Monitorkontrast; Klickannahme deutlich
  rückmelden. GUI mit kontrastreichem Button-Highlight (1,2s), großer dauerhafter
  RECEIVED/RUNNING/DONE/FAILED-Anzeige, Aktionsname/Detail und Laufzeit umgesetzt.
  Hintergrund-Statuspolls überschreiben manuelle Fehler nicht; Klicks/Ergebnisse
  zusätzlich im Sitzungslog und aktueller Feedbackzustand im Exportmanifest.
- Nutzerexport14:35:45 ausgewertet: Dashboard erreichbar/NORMAL/Remote, aber
  Manager hinten rechts seit13:59:00 mit−11 abgestürzt; State-Helper ebenfalls−11.
  Verwaister Launch41339 blockierte neue Starts. Nur diesen Rest beendet;
  künftige Manager-Exits räumen zugehörigen Launch samt Sperre automatisch auf.
  Nativer Segfault selbst noch ungeklärt, keine bewiesene WLAN-Ursache.
  [Diagnose](docs/ur_log_diagnosis_2026-11-10.md).
- Abschluss:17 Offline-Tests, Zwei-Paket-Build und isolierter Live-Mock-Test
  inklusive gezieltem Manager-Exit, Bereinigung nur dieser Instanz und anschließendem
  erfolgreichem Armneustart bestanden. Fehlerhafter alter GUI-Status nach
  Treiberexit wird verworfen. Logs setup/logs/uwa-feedback-{tests,build,live}.log.
  Kontrastreiche Darstellung anhand zweier Screenshots geprüft; aktuelle GUI
  über Desktop-Aktion geöffnet, ohne lebende Hardwaretreiber zu unterbrechen.
- Nutzerauftrag: aktuelle UR-GUI ins Englische übersetzen und Save logs für
  die aktuelle Sitzung ergänzen. Eigene Beschriftungen/Tooltips/Meldungen,
  eigene MATCH-Adapterantworten und Startmenü UWA Arms übersetzt. Native oder
  alte gespeicherte Logs werden unverändert erhalten.
- Eindeutige Sitzungsverzeichnisse unter setup/logs/uwa-control/sessions/.
  Vollständiges GUI-Log und gesonderte Prozessdateien inklusive Statusausgaben,
  Exitcodes; sichtbarer Logpuffer darf weiterhin gekürzt sein.
- Save logs als dauerhaft erreichbarer Button; Export im Hintergrund als
  tar.gz nach setup/logs/uwa-control/exports/. Neuester erfolgreicher Pfad in
  latest-export.txt daneben. Manifest: Zeitpunkte, Modus, Auswahl, letzte
  Statusdaten, PIDs, whitelisted Profilwerte, Dateiliste/Warnungen und Screenshot.
  Kein automatischer Roboterbefehl/Upload, kein vollständiger Environment-Dump.
- Passende seit Sitzungsbeginn geschriebene ROS-Dateien und ältere, noch von
  angehängten Treiberprozessen verwendete ROS-Logs erfassen. Altes gemeinsames
  gui.log explizit als inherited_context, damit Diagnose früherer Treiberstarts
  möglich bleibt. Wiederholte Exporte überschreiben keine vorherigen Archive.
- Offline-Prüfung:16 Tests bestanden, darunter archivierte Fehlerausgaben,
  getrennte Sitzungen, ROS-Auswahl, keine externen Symlink-Dateien und echter
  GUI-Button-Export während einer als laufend markierten Operation.
  Logs setup/logs/uwa-english-log-{tests,build,live}.log; Details Bedienungsdatei.
- Beide Pakete gebaut, isolierter Live-Mock-Test inklusive Save logs bei vier
  aktiven Mock-Controllern bestanden. Archiv enthält Prozessdateien, ROS-Dateien,
  Status-Snapshot und vier Treiber-PIDs; anschließend Controllerstopp und
  sauberer Abbau bestätigt. Beispielarchiv im JSON-Bericht
  setup/logs/uwa-control/mock-gui-validation.json verzeichnet.
- Englischen Desktop-Eintrag installiert/validiert und dessen Hardware-Aktion
  geöffnet. Nur treiberloses Vorgängerfenster ersetzt; Besitzerfenster und beide
  Hardware-Launch-Prozesse41338/41339 erhalten. Neue GUI UWA · Direct UR Test,
  Hardwaremodus/rear right; keine realen Power-/Brake-/Play-/Bewegungsbefehle.

## Aufbau der realen Zelle und Modellannahmen

### Lokale UR-Vorbereitung und direkte UWA-GUI, 2026-11-10

- Nutzerwunsch: gemeinsame Start-/Bereitstellungs-/Admittanz-/Kollisionsbausteine
  in MATCH belassen; einfache UWA-Oberfläche mit vier Armauswahlen oben links,
  ohne SSH/rsync/mobile Infrastruktur. Adapter `match_ur_hardware`, Client
  `uwa_cell_control`; bestehende MuR-Algorithmen und Launch-Defaults erhalten.
- **Neueste Nutzerkorrektur:** zusätzliche UWA-Sicherheitsgates entfernen, um
  Bremsenlösen, Gelenkwinkel und Controllerwechsel auch per WLAN direkt zu testen.
  Damit sind frühere pauschale bzw. Ein-/Zweiarm-Sperren ausdrücklich überholt.
  Entfernt: Armzahl-/Aktivarmzählung/-lock, Dashboard-NORMAL/Remote/RUNNING/
  PLAYING-Vorprüfungen, exakter Programmpfadvergleich, Inaktivpflicht vor
  Bereitstellung, GUI-Treiberbesitzpflicht und rqt-Statusfreigabe.
- Native UR-Sicherheitsfunktionen, Treiber-Controller-Stopper, bestehende
  Kollisionsalgorithmen/Reglergrenzen nicht verändert. Technische Profil-/Port-
  Validierung und doppelte-Treiber-Schutz bleiben. WLAN wird nicht gesperrt.
  Dashboard-/Treiberablehnungen werden angezeigt; keine automatischen
  Schutzstoppquittierungen, kein automatisches Power/Brake/Play beim Launch.
- Standard nur `right_rear`; App UWA Arme, neues Fenster **UWA · Direkter UR-Test**.
  Domain66/localhost; Gazebo64/OAK65 unverändert. Hardwareinventar separat,
  links weiterhin keine IPs. Eigene Werkskinematik noch nicht hinterlegt.
- Prepare verwendet vorhandenen UR-SetMode-Helfer, ohne Programmstart. Separates
  Play startet aktuell geladenes UR-Programm; `external_control_program` nur
  noch informativ. Native reale Trajektorien mit skaliertem UR-Controller.
- **Gelenkwinkel lesen** empfängt JointState ohne Programm-/Dashboardprüfung,
  Anzeige rad/Grad. **Broadcaster / Controller laden** holt fehlgeschlagene
  Spawner nach, Broadcaster aktiv/Motion inaktiv. Beim Schließen kein zusätzlicher
  Dashboard-Stopp mehr; eigene Prozesse werden beendet. Neues Fenster kann
  fremd gestartete Treiber bedienen, beendet deren Prozesse aber nicht.
- Hardwarediagnose: Log zeigt beide Spawner13:48/13:49 fehlgeschlagen, später
  Verbindungsabbrüche/Reconnects30001/30004. Lesender8-s-Test ohne JointState;
  echte Winkelübertragung noch nicht nachgewiesen. Native UR-read()-Logik liest
  RTDE actual_q unabhängig vom laufenden External-Control-Programm.
- 14 Offline-Tests und Zwei-Paket-Build bestanden, Live-Mock-Test getrennt unter
  /uwa_mock_validation: direkte Ein-/Zwei-/Vierarm-Aktivierung ohne Dashboard,
  JointState-Leser, vier Admittanzcontroller und GUI-Stopp/Prozessabbau bestanden.
  Logs setup/logs/uwa-direct-{tests,build,live}.log und finaler JSON-Bericht unter
  setup/logs/uwa-control/. Frühere gate-spezifische Tests sind historisch.
- Neues direktes Hardware-GUI-Fenster neben altem Besitzerfenster geöffnet,
  dessen laufende reale Treiber nicht gestoppt/neugestartet. Agent hat keine
  realen Power-/Brake-/Play-/Bewegungsbefehle gesendet. Softwarestopp ist kein
  Hardware-Not-Halt. Kollisionsoption in UWA-Profilen bleibt deaktiviert;
  kein vollständiger Zellenschutz. Anleitung [UWA Arme](docs/ur_control_gui.md).

### Reale Netzwerkverbindung, 2026-11-10

- **Verbindliche Nutzerzuordnung:** hinten rechts=`right_rear`=192.168.8.170,
  vorne rechts=`right_front`=192.168.8.103. „Erster/zweiter“ sind zufällige
  Bezeichnungen, keine dauerhaften Arm-IDs. Separates Inventar in
  `config/hardware_inventory.yaml`; keine Hardware-IP in den Simulationslaunch.
- OAK4-D R9 weiterhin192.168.8.238, ID1479883285. PC wegen defektem langem
  LAN-Kabel vorübergehend per WLAN, Geräte weiter kabelgebunden am Router.
  Beobachtet PC192.168.8.209/24 aufwlp88s0f0, alle Zielrouten WLAN;
  enp87s0 DOWN. Alte LAN-Leistungswerte nicht als WLAN-Werte verwenden.
- **Alle drei Geräte erreicht.** UR-Dashboard-Leseabfragen erfolgreich:
  ModellfamilieUR5, Software5.10.1.106310, Seriennummern hinten20195501620 /
  vorne20195501617. Beide zum TestPOWER_OFF, StatusNORMAL, ProgrammSTOPPED,
  RemoteControl=false; nichts davon verändert. Keine Robotertreiber/Bewegung.
- Je40 Pings:0% Verlust; RTT-Mittel hinten6,87ms, vorne5,02ms, OAK6,52ms.
  Maxima30,92 /45,82 /14,52ms: sichtbarer Jitter, keine Echtzeitgarantie.
- OAK-Agentinfos erfolgreich; kurzer SDK-Stream640×480NV12@5fps lieferte
  gemessen4,997fps über10,21s, etwa18,9Mbit/s Bildnutzdaten. Danach geschlossen.
  Kein Maximalbandbreitentest, keine Wiederholung der LAN-Extremprofile.
  Hardware-OAK- und Simulations-Livedienste waren vor Test bereits inaktiv.
- [Prüfbericht](docs/hardware_network_2026-11-10.md); lokale Rohdaten unter
  `setup/logs/hardware-wifi-2026-11-10/`. WLAN-Bildprofile zunächst klein halten,
  Kalibrieraufnahmen bei Stillstand; spätere Rückverbindungen benötigen die
  aktuelle PC-IP. Keine URCap-/Netzwerk-/Firmwareänderung ausgeführt.

### Erster realer Wrist-/Hand-Auge-Test, 2026-11-10

- Neuer Nutzerwunsch: zunächst ausschließlich hinten rechts (`right_rear`,
  192.168.8.170) reale Tests vorbereiten, insbesondere Kamerabildzugriff klären.
- [Konkretes Vorgehen](docs/right_rear_hardware_first_test.md): Robotiq dokumentiert
  HTTP4242`/current.jpg?type=color` am UR-Controller für das letzte Kamerabild.
  Bildfrische, tatsächlichen Bildmodus/Intrinsics und Fokus separat prüfen.
- Lesender Versuch: HTTP`No route to host`, Dashboard29999Timeout. PC weiterhin
  192.168.8.209 aufWLANwlp88s0f0, Route vorhanden. Kein Bild/Zustand bestätigt,
  Ursache offen. Lokaler Bericht`setup/logs/right-rear-wrist-2026-11-10/report.json`.
  Keine Treiberstarts, Bewegung oder Power-/Brake-/Programm-/Kameraänderungen.
- Empfehlung, noch keine Umsetzung: zunächst am Pendant manuell angefahrene
  Stellungen, hardwareseitiger Bild-/Pose-Recorder mit gesicherter Bildfrische,
  reale Intrinsics/Werkskinematik und unabhängige Prüfstellungen. Automatischer
  Backend/Stopp derzeit weiterhin Simulation, nicht für echte Arme freigegeben.
- right_rear allein liefert Hand-Auge und Basis-zu-Board; relativer Abstand zum
  right_front erst mit dessen Messreihe am gleichen unbewegten Board. Vorhandene
  parallele Hardware-GUI-Arbeit bleibt erhalten und wurde nicht als fertige
  Kalibrier-Hardwareanbindung ausgegeben.
- Folgefrage Bildqualität am selben Tag: Nutzer meldet falschen Fokus und
  geringe Auflösung. Erneuter lesender HTTP-Abruf jetzt erfolgreich: **640×480**,
  83379Bytes, HTTP200. Frühere Nichterreichbarkeit damit historisch; keine
  Netz-/Kameraänderung durch diesen Agenten. Bild/Report`quality_check.jpg/json`
  unter`setup/logs/right-rear-wrist-2026-11-10/`. Sichtprüfung: Pendant überbelichtet,
  kein Board; genaue Fokusursache/Bildfrische noch nicht nachgewiesen.
- Herstellerdaten2019:2560×1920 bei2fps,640×480 bei bis30fps, Flüssiglinse70mm–∞.
  Sensorfähigkeit von tatsächlich gelieferten HTTP-Pixeln unterscheiden. Fokus
  über Robotiq-Teach-/Configure-Model-Kameraeinstellungen/Retake prüfen;
  HTTP-GET ist kein belegter Autofokus-Trigger. Höhere Auflösung noch nicht
  praktisch erschlossen; Bedienhinweise/Quellen in obiger Anleitung ergänzt.
- Fernfokus-Folgefrage2026-11-10: Nutzer möchte Skript/PC-Schieberegler und
  distanzbasierte Einstellung. Frühere Formulierung „Fokus nur per URCap“ zu
  pauschal: Primärbericht eines Anwenders im Robotiq-Forum beschreibt Fokus via
  OpenCV bei direktem USB; Hersteller unterstützt diese Integration nicht
  offiziell. Keine Prüfung am eigenen Gerät, Beispiel-Link inzwischenHTTP404.
  Für den bestehenden Controllerpfad weiter kein dokumentierter Netzwerksetter
  gefunden; installierten URCap-/Programmskriptpfad künftig lesend untersuchen.
- Physikalischen Zielabstand von elektronischem Stellwert unterscheiden:
  V4L2-Fokuseinheit nicht definiert; Kennlinie oder Board-ROI-Schärfesuche nötig.
  Kein Fokussetter/Schieberegler implementiert, keine Kamera-/Roboteränderungen.
  Für Hand-Auge Fokus und passende Intrinsics konstant halten; Fokusprofile
  wären bei distanzabhängiger Verstellung zusätzlich zu kalibrieren.

### Zellgeometrie

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
- Die ursprüngliche aufrechte Anfangsstellung `[0, −π/2, 0, −π/2, 0, 0]`
  wurde am 2026-11-09 durch ChArUco-Zielansichten ersetzt (siehe unten).
  Robotiq 2F-85 und Wrist Camera sind seit demselben Tag ergänzt.
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
  Die spätere Kalibrier-Routine ergänzt MoveIt-Kollisionsprüfung;
  reale Hardware bleibt Folgearbeit.
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

### ChArUco und erster Basisabgleich, Nutzerauftrag 2026-11-09

- Je ein Board mittig zwischen den Robotern pro Tisch; zunächst linkes Paar in
  `left_table_top`, rechtes Paar in `right_table_top` prüfen. Der Nutzer will
  darauf aufbauend ein Werkzeug zur relativen Roboterkalibrierung entwickeln.
- Muster 7 × 5, Feldkante 40 mm, Marker 28 mm, Rand 20 mm, Träger 3 mm;
  `DICT_4X4_100`, links IDs 0–16, rechts 50–66. Alles unter `charuco` in YAML.
- Kamera-Zielansichten per URDF-FK/IK ermittelt und in `initial_positions`
  übernommen: 0,55 m über der Boardmitte, je ±0,28 m entlang Tisch-Y versetzt.
  Bestehende Basis-/Werkzeugmontagen erhalten; kein geplanter Bewegungsweg.
- `charuco_check`: OpenCV 4.10 `CharucoDetector`, PnP/IPPE und LM-Verfeinerung;
  zehn verschiedene Bildzeitstempel pro Kamera, PNGs und JSON-Bericht.
  Ground Truth erst nach der Bildschätzung für Fehlerprüfung aus TF lesen.
- Erste Basisformel: `T_table_base = T_table_board @ inv(T_camera_board) @ inv(T_base_camera)`.
  Die interne TF-Kette beginnt bei URDF `base_link`, ohne bekannte Weltmontage
  als Eingang. Boardplatzierung, Intrinsics, Hand-Auge-Transformation und
  Gelenkkinematik werden als bekannt vorausgesetzt. Noch keine Schätzung
  unbekannter Hand-Auge-/Gelenkparameter aus mehreren Armstellungen.
- Offizielle Boardframes `<table>_charuco`: Musterecke ohne Rand; X rechts,
  Y im Muster nach unten, Z in die Platte. Plattenmitte ist `<table>_charuco_mount`.
- Erster Live-Erfolg: alle vier Gazebo-Bilder mit jeweils 24 ChArUco-Ecken.
  Relative Basenfehler beider Tische ca. 1,9 mm / 0,17°, individuelle
  gemittelte Basisfehler ca. 1,1–1,2 mm / 0,08–0,09°. Idealisiertes Rendering,
  keine Genauigkeitszusage für echte Kameras. Konkrete Zahlen im
  [datierten Bericht](docs/charuco_validation_2026-11-09.json).
- Materialfehler beim ersten Liveversuch: Collada-Fläche ohne Normalen blieb
  unsichtbar. Explizite +Z-Normalen ergänzt, echter Vierkamera-Test danach bestanden;
  Assetprüfung dafür ergänzt. PNG-Muster bleiben deterministisch OpenCV-generiert.
- **33 Offline-Tests bestanden**, beide Pakete gebaut. Vollständiger Bildbericht:
  `setup/logs/uwa-charuco-second/report.json`, annotierte Bilder im selben Ordner;
  Logs `uwa-cell-charuco-{build,tests,live,cell-verification}*` im Workspace.
- Finaler Bestätigungslauf mit Roh- und Erkennungsbildern:
  `setup/logs/uwa-charuco-final/`; zehn erfolgreiche Bilder je Kamera,
  relative Fehler links **1,888 mm / 0,1645°**, rechts **1,843 mm / 0,1570°**.
  Neun Controller aktiv, Zellwurzel stabil, RViz wiederhergestellt. Der separate
  Scan-Publisher blieb erhalten; keine weiteren Zellneustarts geplant.
- Anleitung/Formeln/Bedienung: [docs/charuco_calibration.md](docs/charuco_calibration.md).
  `prepare_charuco_views` erzeugt nach Layoutänderungen eine alternative YAML,
  ohne die Quelle zu überschreiben oder Bewegungen auszuführen.
- Zusammenarbeit: Nutzer arbeitet mit mehreren unabhängigen Agenten im selben
  Checkout. [ACTIVE_WORK.md](ACTIVE_WORK.md) plus eigene Datei je Aufgabe unter
  `work/` eingeführt; vor Edits/Neustarts lesen, Änderungen bereichsweise anwenden.
  Der fremde Scanregistrierungs-Diff wurde erhalten. Für Uhrenreset RViz kurz
  schließen und danach wiederherstellen, separaten Scan-Publisher erhalten.

### Druckvorlagen, Nutzerauftrag 2026-11-09

- Dieselben ChArUco-Muster für echte Versuche angefordert. Originalmaß inklusive
  Weißrand **320 × 240 mm**; Muster 280 × 200 mm, Feldkante 40 mm, Marker 28 mm.
- `output/pdf/uwa_charuco_boards_A3_1to1.pdf`: zwei A3-Querformat-Seiten,
  links/rechts jeweils komplett. `uwa_charuco_boards_A4_tiled_1to1.pdf` im selben
  Ordner: vier A4-Hochformat-Seiten, je Board zwei Hälften mit 20 mm Überlappung.
  Keine verkleinerte A4-Einblatt-Version, da sie andere metrische Maße hätte.
- Beide PDFs als Vektorflächen aus derselben `board_image()`-Ausgabe wie Gazebo;
  IDs links 0–16, rechts 50–66 unverändert. Generator `scripts/print_charuco.py`
  liest die zentrale YAML; optionale PDF-Abhängigkeit `python3-reportlab`.
- Druck: **100% / Tatsächliche Größe**, keine Seitenanpassung; 100-mm-Kontrollstrecke
  und 40-mm-Feldkante nachmessen, plan auf festen Träger aufbringen. Für echte
  Kalibrierung die tatsächliche Boardoberflächenpose im Tisch-KS vermessen.
- Dateiprüfung: korrekte Seitenformate/-zahlen und metrische Vektorgeometrie,
  alle sechs Seiten gerendert und angesehen. OpenCV erkennt auf beiden A3-Seiten
  sowie den digital zusammengesetzten A4-Boards je alle 17 Marker und 24 Ecken.
  Beleg: `docs/charuco_print_validation_2026-11-09.json`, vollständiges Log unter
  `setup/logs/uwa-charuco-print-verification.log` im Workspace. Kein physischer
  Druckertest durchgeführt. Simulation und laufende Dienste nicht verändert.

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
- Ursprünglich Maßstab **1** und Identitätspose; diese Anzeige war deutlich gekippt.
  Seit 2026-11-09 ist eine grobe Tischflächen-Ausrichtung eingestellt (siehe unten).
  Die Referenz bleibt ausdrücklich **nicht kalibriert**.
- Ein fehlender Scan darf Gazebo nicht verhindern. Bei `scan:=false` liest der
  direkte Launch den Scan nicht. **Aktuelle Grenze:** Auch zur Cache-Auswahl fragt
  der Importer noch Dateimetadaten des Originals ab; kein garantierter Offline-Fallback
  bei vollständig fehlendem Drive-Mount. Das ist keine bereits erledigte Anforderung.

### Grobausrichtung des Scans, 2026-11-09

- Nutzerauftrag: Die deutlich verdrehte Punktewolke an der Szene ausrichten;
  bei nötigen Bezugspunkten unterstützt der Nutzer.
- Vorgehen: Dominante Boden-/Tischebenen im lokalen Scan-Cache bestimmen,
  zwei zentrale zusammenhängende Tischflächen isolieren und ihre Rechteckkanten
  an den nominellen 0,80 × 1,70 m ausrichten. Keine Roboterposen aus dem Scan ableiten.
- Maßstab **0,9531928102**, Translation **[−0,28749867; −0,43623572; +0,58765448]**,
  RPY in Grad **[−89,761396; +0,349501; +60,140648]**.
  Die Runtime-Werte bleiben zentral in `cell_layout.yaml`; der datierte
  [Fit-Bericht](docs/scan_alignment_2026-11-09.json) dokumentiert ihre Herleitung.
- Die zunächst mögliche 180°-Verwechslung wurde mit konkreten Nutzerangaben aufgelöst:
  **hinter** den Tischen steht eine hohe weitere Roboterzelle aus item-Profilen;
  **vorne** sind zunächst etwa zwei Meter freie Fläche. Die passende Scan-Richtung
  ist bereits eingestellt (+Y zur hohen Profilrahmen-Zelle, −Y zur freien Fläche).
- Der Nutzer konnte die abstrakte A/B-Draufsicht nicht eindeutig zuordnen.
  Bei weiteren Rückfragen besser konkrete reale Gegenstände/Bezugspunkte benennen.
- Nur `uwa-cell-scan` wurde neu gestartet; Simulation, Modellmaße, Robotermontagen,
  Greifer/Kameras und laufende Benutzer-RViz-Ansicht wurden nicht zurückgesetzt.
- Grenzen: Keine metrische Kalibrierung. Die vorläufige Modell-Tischhöhe 0,90 m
  ergibt bei diesem Scan-Fit ca. **0,132 m Bodenversatz**. Reale Höhe noch messen;
  die aktuelle Scan-Schätzung allein ist kein Auftrag, das Modellmaß zu ändern.
  Abweichende Armstellungen zwischen Aufnahme und Simulation sind erwartbar.
- Prüfung: 200.000 endliche Punkte, publizierter Maßstab und Welt-TF entsprechen
  der YAML, genau ein Publisher. Beide bestehenden Dienst-PIDs (Simulation/RViz)
  blieben erhalten. RViz meldet 200.000 dargestellte Punkte und Transform „Ok“.
  **24 vorhandene Offline-Tests bestanden**; protobuf meldet eine Deprecation-Warnung.
- Belege: `setup/logs/uwa-scan-alignment-{estimate,verification}.json`,
  `uwa-scan-alignment-landmarks.png`, `uwa-scan-aligned-rviz.png` und zugehöriges Log
  im Workspace. Analyseprogramme lagen temporär unter `/tmp/uwa-scan-alignment`.

### Scan-Bereinigung, Nutzerauftrag 2026-11-09

- Anforderungen: Keine Punkte weiter als **4 m vom Zentrum zwischen den Robotern**;
  die aufgenommenen Roboter entfernen, damit keine doppelten Arme neben den
  simulierten Robotern stehen.
- Umgesetzt als Kugelradius im Weltkoordinatensystem um den Mittelwert der vier
  Basispositionen, aktuell **[0; 0; 0,90] m**. `scan.crop_center: null` berechnet
  diesen Punkt aus Tisch-/Montageposen; alternativ ist ein expliziter Punkt möglich.
- Acht feste `scan.exclude_boxes` blenden die vier aufgenommenen Arme und ihre
  Basisbereiche aus. Die Aufnahmeposen unterscheiden sich von den Simulationsposen;
  deshalb keine dynamischen Modell-TFs als Entfernungsmasken verwenden.
- Grobe räumliche Masken, keine semantische Roboterdetektion. Sie können direkt
  angrenzende Punkte im selben Volumen mit ausblenden und sind nach einer neuen
  Aufnahme oder Registrierung erneut zu prüfen. Tischflächen und die meisten
  flachen Tischobjekte bleiben durch die Höhenbegrenzung erhalten.
- Modul `scan_filter.py`, Aufruf einmal im Scan-Publisher nach der Skalierung;
  nur die Auswahl wird in Weltkoordinaten berechnet. Publizierte Punkte bleiben
  im bisherigen Scan-Frame. Roh-PLY und Importcache unverändert.
- Konfiguration und Validierung: `crop_radius`, `crop_center`, `exclude_boxes`
  unter `scan`; Radius `null` bzw. leere Maskenliste schalten die Filter ab.
- Ergebnis für die aktuelle Aufnahme: **200.000 → 154.458 Punkte**. Entfernt:
  **27.133** außerhalb des Radius und **18.409** innerhalb der Roboter-Masken.
- Liveprüfung: größter Radius **3,999784 m**, keine veröffentlichten Punkte in
  den Masken, endliche Koordinaten, genau ein Publisher. Rohcache-SHA256 und
  Simulations-/RViz-Dienst-PIDs unverändert. Nur `uwa-cell-scan` neu gestartet.
- RViz-Sichtprüfung: 154.458 Punkte, Transform und Anzeige „Ok“, keine doppelten
  aufgenommenen Arme mehr; Umgebungsgeometrie und Tische sichtbar.
- **44 Offline-Tests bestanden**, inklusive 11 neuer Filter-/Validierungsfälle:
  Weltkoordinaten und Radiusgrenze, Farberhalt, bewegte Tische, feste Masken,
  Überlappungen/leere Ausgabe und ungültige Konfiguration. Eine bestehende
  protobuf-Deprecation-Warnung bleibt.
- Belege im Workspace: `setup/logs/uwa-scan-cleanup-{counts,tests,verification}.*`,
  `uwa-scan-cleaned-rviz.{png,log}` und `uwa-scan-cleanup-regions.png`.
- Parallel aktive ChArUco-Arbeit über `work/` abgestimmt; keine Board-, Werkzeug-,
  Roboter- oder Simulationsstartänderungen durch diese Bereinigung.

## Behobene Probleme und Entscheidungen

| Datum | Beobachtung / Entscheidung | Ergebnis |
|---|---|---|
| 2026-11-06 | Gazebo-Wrapper und Clock-Bridge beendeten sich nicht sauber | Direkter GUI-Client; eigener kleiner Clock-Adapter; gezielte Dienststeuerung |
| 2026-11-06 | Nur diese RViz-Konfiguration erlaubte kein Drehen/Zoomen | Fehlende `Tools`-Liste ergänzt; echte Maus-/Mausrad-Ereignisse geprüft |
| 2026-11-06 | Weißer Außenrahmen am ansonsten gewünschten Icon | Mit Imagegen transparent gemacht; Motiv und dunkelblaues Feld erhalten |
| 2026-11-09 | App zeigte keine Wolke, manuell gestarteter Scan schon | Scan fehlte im normalen Desktop-Start; Start und RViz-Aktion laden ihn jetzt automatisch |
| 2026-11-09 | Nutzer wünscht dauerhaftes Festhalten der Gespräche | Workspace-/Projekt-AGENTS und diese Übergabe angelegt; fortlaufende Pflege vereinbart |
| 2026-11-09 | Icon-Klick scheint nichts zu starten, obwohl alle drei Dienste und Fenster laufen | Vorher nur „läuft schon“; nun Wiederherstellen/Aktivieren der vorhandenen Zell-Fenster ohne Neustart |
| 2026-11-09 | Punktewolke deutlich gegenüber dem Modell verdreht | Grober Ebenen-/Rechteck-Fit; Vorderseite über freie Fläche und hintere Profilrahmen-Zelle identifiziert; keine Kalibrierungsbehauptung |
| 2026-11-09 | Ferne Scanpunkte und doppelte aufgenommene Arme stören | 4-m-Weltradius und feste Scan-Roboter-Masken; nur Referenzpublisher neu geladen |

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

## Statische OAK4-Übersichtskamera (2026-11-09)

- **Wichtige Nutzerpräzisierung:** später einen Tisch absichtlich verschieben;
  Tisch-zu-Tisch-Pose und tatsächliche Bewegung messen, Fehler kompensieren.
  Beide Tischboards bleiben fest montiert. Option: kleine OAK auf rechtem Tisch
  sieht nur das gegenüberliegende Board. Tischfeste Kameramontage und variable
  Tischpose unbedingt getrennt behandeln, Bewegung nicht in Kalibrierung absorbieren.
- Neuer [Kalibrier-/Messansatz](docs/table_tracking_calibration.md): OAK sieht
  beide Boards -> relative Boardpose durch inv(T_C_BL)@T_C_BR, Weltpose der
  Kamera fällt heraus. Tischmontagen der Boards für definierte Tischframes ergänzen.
  Für OAK auf rechtem Tisch Montage X einmal separat bestimmen; danach bleibt X
  bei Tischbewegung konstant. Unbekannte Montage plus unbekannte Tischrelation
  sind aus einer einzigen gegenüberliegenden Boardansicht nicht getrennt schätzbar.
- Nutzer schlägt bekannte stationäre Wrist-Kameras und ein zusätzliches mobiles
  Kalibrierboard im gemeinsamen Sichtfeld vor. Als bevorzugter erster Ansatz
  empfohlen: lokale Kamera-Kamera-Transformation über viele Halteposen, dann
  bekannten FK-/Hand-Auge-/Tischbezug nutzen; weder Tischboards noch Kameras
  müssen sich bewegen. Alternative: UR hält Board für automatisierte Eye-to-Hand-
  Schätzung inklusive unbekannter Werkzeug-Board-Montage. Empfehlungen, noch
  kein Implementierungs-/Messfahrtauftrag. Frühere Konzeptannahmen entsprechend
  als eingeschränkt markiert; keine Dienste/Hardware/Simulationsposen verändert.

- Beratungsfrage zur empfohlenen Kalibrierung statischer Kameras:
  [Konzeptvorschlag](docs/static_camera_calibration_plan.md) festgehalten.
  Factory-Intrinsics für Bildmodus/Fokus prüfen, feste Tischboards als Referenz
  und zur Verbindung beider Tischgruppen, Zusatzkameras über gemeinsame/registrierte
  Targets, anschließend räumlich vielfältige gemeinsame Schätzung und unabhängige
  Validierung. Referenzbeziehung zum realen `world` definieren/vermessen, keine
  angenommenen Gazebo-Posen als Hardware-Messwerte. Dies ist eine Empfehlung,
  noch kein genehmigter Implementierungs-/Messfahrtauftrag oder Kalibrierergebnis.

- Nutzerangabe: OAK4-D auf einem Stativ neben den Tischen, derzeit rechts,
  nach unten auf die Tischplatten; Montage noch offen. Gewünscht ist Überblick
  über die ganze Szene bei genügend ChArUco-Detail. Dafür Simulation zum
  Vergleichen von Position, Höhe, Blickrichtung und Auflösung verwenden.
- Umgesetzt als eigene statische Gazebo-Entität `uwa_oak_overview`, außerhalb
  der Zell-URDF. Bestehende Zell-/Wrist-/Greifer-/Controllerkonfiguration erhalten;
  keine Gelenkbefehle und kein Zellneustart durch diese Aufgabe.
- Nutzerkorrektur: reales Stativ maximal **2 m**. Zwei zusätzliche OAK-Kameras
  verfügbar, falls tote Winkel ergänzend abgedeckt werden müssen. Die erste
  unbeschriftete Kamera per USB identifiziert: EEPROM **OAK-D Pro AF**, SDK
  **OAK-D-PRO-AF**, RVC2/DM9098, IMX378-Autofokus + zwei OV9282. Zweite Kamera
  noch ungeprüft; frühere gemeinsame Bezeichnung OAK-D-S2-FF ist überholt.
  Keine konkreten Zusatzkameraposen festgelegt. Diagnose im OAK-Repo-Handover.
- Aktuelle zentrale Konfiguration `overview_camera` in `cell_layout.yaml`:
  optisches Zentrum Welt[1.8,-0.8,2.0]m, Ziel[0,-0.1,0.95]m, etwa28,5° nach unten,
  nominell67,3° horizontal,4000×3000@3Hz Simulationszeit. Nicht kalibriert.
- Neue2m-Pose live geprüft: alle Tisch-Ecken geometrisch im Bild, vier Arme und
  Tischplatten im geprüften Bild sichtbar,12/24 Ecken links/rechts erkannt,
  RMS0,691/0,042px. Links wenig Reserve; Zusatzkameras für tote Winkel/Details
  sind eine Erweiterungsoption. Keine Garantie für alle Armstellungen.
- Mehrere Kandidaten verglichen: mittig rechts zu wenig linke Erkennung,
  starke Frontdiagonalen durch Arme verdeckt.6k lieferte CameraInfo, aber kein
  erfolgreich empfangenes RGB im Zeitfenster;5k ebenfalls nicht erfolgreich.
  Daher bei4k geblieben. Keine Behauptung einer Hardwaregrenze daraus.
  Belege `setup/logs/uwa-oak-2m/`, finale JSON/Bilder dort unter `final/`;
  neue Pose und Höhenlimit mit13 Offline-Tests geprüft. Aktiver Layoutpfad
  wieder zentrale Quelldatei. Kein Zellneustart und keine Arme durch uns bewegt.
- Getrennt vom echten Kameratreiber/SDK. RGB-Pinhole-Näherung, primitive Gehäuse-
  und Stativdarstellung. Keine Tiefenkanäle, realistische Verzeichnung,
  Rolling-Shutter-Verzerrung, Rauschen oder Autofokus simuliert.
- Starter `scripts/overview.sh start|view|reload|coverage|check`. Neue Zellstarts
  starten den Kameraknoten; zur laufenden Zelle wurde er separat über
  `uwa-cell-overview` ergänzt. Sperre pro Benutzer/Partition verhindert zwei
  Besitzer. `cell.sh stop` beendet auch Kamera und separaten Bildbetrachter.
- Pose-/Optikänderungen über `reload` ersetzen nur die Kamera und aktualisieren
  TF/Marker. Nach Anpassung der YAML kein Roboterneustart nötig. Erfolgreich
  zunächst mit2,6m/3m geprüft; diese Versuche sind nach der Nutzerkorrektur
  historisch. Aktueller Stand ist die oben dokumentierte2m-Pose.
- Themen `/uwa_cell/oak_overview/rgb/image_raw` und `camera_info`, optischer TF
  `world -> oak_overview_rgb_optical_frame`. RViz-Config ergänzt um Gehäuse,
  Stativ und Frustum-Marker auf `/uwa_cell/oak_overview/markers` (latched).
  Marker/TF ursprünglich empfangen: zehn Marker, damalige Weltposition[1.8,0,3.0].
- Historischer3m-Prüfstand: bei4k Marker-Minimalseite links/rechts
  ca17,6/28,4px. Sichtfeldrechnung prüft keine Verdeckungen. Echte Erkennung:
  Ausgangspose18/24 Ecken, RMS0,069/0,061px; niedrigere Variante20/24 Ecken,
  RMS0,054/0,096px. Beide Boards jeweils im selben Bild erkannt. Zahlen sind
  Momentaufnahmen, keine Genauigkeits-/Sichtbarkeitsgarantie für alle Armposen.
- Gefundene Grenze: OpenCVs Standard-Minimum3% Bildkante verwirft kleine Marker
  im4k-Gesamtbild. Neuer optionaler Parameter an `detect_pose` belässt den
  Wrist-Standard0,03; Overview verwendet32px minimalen Umfang. Kein GT-ROI oder
  bekannte Kamerapose zum Fit verwendet. Bild-/CameraInfo-Frame und Größe geprüft.
- Build abgeschlossen,70 passende Offline-Tests bestanden; bisherige
  Beschreibungs-/Scan-/Wrist-/ChArUco- und Kalibrierkern-Tests eingeschlossen.
  Belege unter `setup/logs/uwa-oak-overview-*`, Anleitung in
  [docs/oak_overview.md](docs/oak_overview.md). Simulationslivebild geöffnet.
- Grenze: Stativ ist derzeit visuell, ohne Gazebo-/MoveIt-Kollision. Separate
  Gazebo-Modelle gelangen nicht automatisch in die bestehende PlanningScene.
  Kollisionskörper vor entsprechendem Planungs-/Hardwareeinsatz ergänzen.
- Parallele Aufgabe `handeye-diagonal` gesehen: keine Zell-/Scan-Neustarts oder
  Armtests durch OAK-Aufgabe. Automatische Wrist-Hand-Auge-Kalibrierung um die
  externe OAK zu erweitern und reale Welt-Extrinsics zu bestimmen ist Folgearbeit.

## Automatische Hand-Auge-Kalibrierung (2026-11-09)

- **Aktueller Folgeauftrag:** diagonale Paare statt ausschließlich eines Arms:
  links vorne + rechts hinten, danach links hinten + rechts vorne. Die jeweils
  anderen Arme zuvor seriell zur Seite parken. Die frühere Einzelarmreihenfolge
  bleibt in der GUI mit ausgeschalteter Option **Diagonalpaare** bzw. CLI
  `--sequential` verfügbar. Der folgende ursprüngliche Genauigkeitsnachweis
  wurde noch mit dem Einzelarmablauf aufgenommen.
- Paarmodus: gemeinsame zukünftige Startzeit und Dauer beider Trajektorien;
  volle MoveIt-Szene für die Wege plus getrennte Hüllräume aller Kollisionskörper
  über beide Wege, mit 80 mm zusätzlichem Puffer je Arm. Die Freigabe bleibt auch
  bei unterschiedlichem Fortschritt nominal getrennt; keine pauschale
  Reichweitenannahme ersetzt diese Prüfung. Einrichtung und Rückfahrt seriell.
- Anfangs-Boardansichten aus der zentralen YAML dienen zum Wiederanstellen
  geparkter Arme. Die gemessenen tatsächlichen Sitzungsstartstellungen werden
  erst nach Abschluss aller Gruppen wiederhergestellt; Stopp/Fehler halten
  sämtliche aktiven Ziele an der aktuellen Stelle und sperren folgende Fahrten.
- Neuer Paar-Nachweis: **79 aktuelle Offline-Tests bestanden**, vollständiger
  40×4-Lauf `setup/calibration/20261109_133357_7e1130` bestanden; echte parallele
  native Gelenkbewegung in beiden Diagonalpaaren beobachtet. Mindestens 0,307 m
  bzw. 0,372 m Abstand der konservativen nominalen Hüllräume. Wartearme stationär
  (< 1,4e−11 rad Abweichung); alle Rückkehrstellungen < 1,5e−11 rad Fehler.
  [Paar-Prüfbericht](docs/handeye_diagonal_validation_2026-11-09.json).
- Paarlauf: maximale Kameraextrinsics-Abweichung **0,078 mm / 0,030°**;
  relative Basispose links **0,092 mm / 0,0231°**, rechts **0,085 mm / 0,0247°**.
  Basisabstände links **1349,987 mm**, rechts **1349,987 mm**. Fit/Validierung
  bleiben pro Arm 32/8 und relative Posen weiterhin pro linkem/rechtem Tisch.
- Gemeinsames Pause/Fortsetzen und anschließender Stopp beider Controller in
  **0,46 s** bestätigt: `setup/logs/uwa-diagonal-pause-stop.json`.
  Paar-Profil aktiviert, rohe/kalibrierte TFs und Rückfall bei ungültiger Qualität
  sowie kollidierendem Kandidaten geprüft: `uwa-diagonal-profile-check.json` im
  gleichen Logverzeichnis. GUI-Lebenszeichenverlust während simultaner Fahrt
  stoppt beide nach **2,33 s** einschließlich Timeout, paralleler Aufnahmestopp
  bestätigt Stillstand nach **0,30 s**. Danach keine weitere Fahrt/Aufnahme.
  `uwa-diagonal-{disconnect,capture}.json`; alter Einzelarmmodus mit echtem
  GUI-Stopp ebenfalls bestanden (`uwa-diagonal-legacy-gui-stop.json`).
- Vier Pakete gebaut; Zellprüfung bestätigt neun aktive Controller, zum Layout
  passende ursprüngliche Basen und stabile physische Gazebo-Verankerung.
  Das Paarprofil wird beim Start automatisch wiederhergestellt. **Diagonalpaare**
  standardmäßig aktiviert; geänderte Auswahl/Messzahl/Modus nach Vorbereitung
  sperren den Start bis zur passenden erneuten Vorbereitung.

- Nutzerauftrag: genehmigten Plan vollständig in der Simulation umsetzen;
  eigene Qt-GUI, 30–50 verschiedene Stellungen pro Arm (Standard 40), links/rechts
  getrennte relative Basen, unbekannte Kameraextrinsics und explizite Übernahme.
- Neue Pakete `uwa_cell_calibration_msgs` und `uwa_cell_calibration`. Start neben
  der bestehenden Zelle: `ros2 launch uwa_cell_calibration calibration.launch.py`.
  Anleitung: [docs/automatic_handeye.md](docs/automatic_handeye.md).
- Vollständiges MoveIt-Modell mit vier Gruppen und allen Kollisionskörpern;
  lokale quintische Wege mit maximal 0,10 rad/s und 0,20 rad/s² werden vollständig
  gesampelt geprüft. Blockierte Wege werden verworfen, keine OMPL-Umwegsuche.
  Deterministische Kugelkappenansichten mit acht Reserveposen bei 40 Messungen.
- Datensatz: rohe und annotierte Bilder, CameraInfo, Bild-/Objektpunkte,
  zeitlich passende Gelenkwerte und `T_base_link_tool0` unter Workspace
  `setup/calibration/`. Keine Sitzungsdaten ins Repository übernehmen.
- Fit ausschließlich aus Bildern und Werkzeugkinematik: Park-Initialisierung,
  robuste gemeinsame Bildeckenverfeinerung von `X` und `Y` in `M_i X C_i=Y`.
  Bei 40 Stellungen 32 Fit + acht vorab bestimmte, unabhängige Validierungen.
  Keine nominellen Extrinsics / Ground Truth im Fit. Boardpose erst für die
  abgeleiteten absoluten Tischkoordinaten erforderlich.
- Backend und Qt6-GUI getrennt; nicht befehlsfähiger Planungs-/Fit-Prozess,
  eigener Walltime-Watchdog, Besitzer-Lebenszeichen, Controller-Abbruch mit
  Abbremsparametern, Stillstandsbestätigung und Gazebo-Pause als Rückfall.
  Kein automatisches Zurückfahren nach Stopp oder Fehler. Geprüfte Rückfahrt zur
  gemessenen Startstellung nach regulärem Abschluss (im Paarmodus nach allen Gruppen).
- Übernehmen erzeugt ein versioniertes Profil und `calibrated/`-TF-/MoveIt-Modell.
  Physische Gazebo-Montagen und der ursprüngliche TF-Baum bleiben erhalten.
  Kandidatenprüfung vor atomarer Profilaktivierung; altes Profil bei Fehler behalten.
- Prüfnachweise: vier Pakete gebaut, **57 Offline-Tests bestanden**
  (`setup/logs/uwa-handeye-all-tests-final.log`). Vollständige Sitzung
  `setup/calibration/20261109_122753_b901ad`: **40 Aufnahmen je Arm**, jeweils
  32 Fit + acht Validierung, alle Qualitäts- und Ground-Truth-Ziele bestanden.
  [Datierter Bericht](docs/handeye_validation_2026-11-09.json).
- Kameraextrinsics-Fehler: links vorne **0,130 mm / 0,0345°**, links hinten
  **0,049 mm / 0,0306°**, rechts vorne **0,073 mm / 0,0279°**, rechts hinten
  **0,047 mm / 0,0304°**. Validierungs-Reprojektion 0,075–0,122 px medianer RMS.
- Relative Basispose links **0,640 mm / 0,0533°** Fehler, Abstand **1350,012 mm**;
  rechts **0,128 mm / 0,0269°**, Abstand **1349,989 mm**. Park-Bootstrapintervalle
  des Abstands links 1349,736–1350,809 mm, rechts 1349,629–1350,664 mm.
- `setup/logs/uwa-handeye-profile-check.json`: Rückkehrfehler aller Armgelenke
  < 1,4e−11 rad; getrennte rohe/kalibrierte TFs stimmen mit ihrem jeweiligen Modell
  überein. Schlechte Qualität und ein absichtlich kollidierendes Kandidatenmodell
  behalten vorheriges Profil und Modell; gültige Reaktivierung erfolgreich.
  Gespeichertes Profil wird beim Backend-Neustart wieder geladen.
- Echte GUI-Knöpfe live geprüft: Stopp während Planung, tatsächlicher Fahrt und
  Aufnahme; Stillstand bei Fahrt/Aufnahme nach rund **0,30 / 0,29 s** bestätigt.
  Eingefrorenes GUI-Lebenszeichen trotz weiterlaufendem ROS-Thread stoppt nach
  rund **2,27 s** einschließlich Lease-Frist. Keine folgende Bewegung/Aufnahme.
  Direkte Gazebo-Pause bestätigt und anschließend Welt erfolgreich fortgesetzt.
  Logs/JSON: `setup/logs/uwa-handeye-gui-{planning,exercise,capture,freeze,world-pause}.*`.
- GUI zeigt Livebilder und die vollständige Ergebnistabelle in getrennten Tabs,
  bei unverändert erreichbaren Steuerknöpfen. Statusmeldungen verwenden eine
  Steady-Clock und bleiben auch bei pausierter Simulationszeit verfügbar.
- Nur die besitzende GUI fordert bei verlorener Backend-Verbindung automatisch
  die Weltpause an. Beobachterfenster dürfen eine laufende Sitzung nicht durch
  ihre eigene verzögerte Verbindung unterbrechen; Profilwiederherstellung hat
  noch keinen GUI-Besitzer und versendet keine Fahrbefehle.
- Beim ersten Freeze-Test trat erst nach erfolgreicher Stillstandsbestätigung
  ein Prozessabsturz beim Beenden auf. ROS-Executor-Threads werden nun vor der
  Node-/Kontextzerstörung beendet; wiederholter Freeze-Test beendet sich sauber.
- Behobene Simulationsbesonderheit: passive Robotiq-Mimic-Geschwindigkeiten
  können trotz Stillstand stark rauschen. Für den Bewegungsstopp alle
  angetriebenen Gelenke prüfen und zusätzlich unerwartete Gelenkpositionsänderungen
  überwachen; vor Fahrbefehlen ein stabiles Geschwindigkeitsfenster verlangen.
- Grenzen: Simulation mit idealen Intrinsics und angenäherter Kamerageometrie;
  keine reale Stoppsystem-/Hardwarefreigabe. Bootstrapwerte sind
  Wiederholungsstreuung, keine Garantie absoluter Genauigkeit.

## Offene Ziele / noch nicht freigegebene Genauigkeitsannahmen

1. Echte Tischhöhe und Montageposen messen, Basisorientierungen kalibrieren.
2. Individuelle UR-Kinematikdateien übernehmen, sobald verfügbar.
3. Vorhandene grobe Scan-Ausrichtung metrisch kalibrieren, insbesondere reale
   Tischhöhe und Bodenversatz klären. Keine unbestätigte Montagekalibrierung
   automatisch als wahr übernehmen.
4. MoveIt über die nun vorhandene Kalibrier-Kollisionsprüfung hinaus für allgemeine
   und kooperative Bewegungsplanung ergänzen.
5. Später explizit geplante Hardware-Anbindung und Synchronisation untersuchen.

Die Liste beschreibt offene Arbeitspakete, keinen Auftrag, sie ohne weitere
fachliche Abstimmung sofort alle umzusetzen. Aktuelle Konfigurationswerte und
Bedienung haben Vorrang vor überholten Gesprächsständen.
