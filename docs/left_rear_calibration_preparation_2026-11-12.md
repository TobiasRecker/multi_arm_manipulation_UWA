# Links hinten: Kalibrierung vorbereiten

Stand2026-11-12. Ziel **left_rear=192.168.8.169**, konfigurierter UR7e,
Seriennummer20265701623. Individuelle Werkskinematik bereits im gemeinsamen
Messprofil vorhanden. Vorherige rechte Kalibrierergebnisse bleiben erhalten.

## Nachgewiesen

- Dashboard und reines RTDE-Lesen erreichbar; Seriennummer/Software5.25.0.130258
  entsprechen dem gespeicherten Inventar. Ethernet-PC192.168.8.209/enp87s0.
- Nach ausdrücklichem Nutzerauftrag MATCH-Prepare ausgeführt: POWER_OFF nach
  RUNNING, Bremsen gelöst, Safety NORMAL und Remote. **Keine Fahrziele gesendet.**
  Vier Bewegungscontroller links hinten inaktiv; vorhandene rechte Treiber und
  ursprüngliche GUIs erhalten. Zusätzliches eigenes Beobachterfenster beendet.
- Wrist-HTTP unter Port4242 liefert640×480-JPEGs; drei unterschiedliche
  decodierte Bilder nachgewiesen. Readback Fokus439Auto, Belichtung33333µsAuto,
  Gain16. Kein ChArUco-Board im aktuellen Bild erkannt. Kameraeinstellungen
  nicht verändert; Fokus nach erster echter Boardansicht passend festlegen.
- Nutzer bestätigt ursprüngliches linkes40mm-Tischboard(A3/1:1) ungefähr an
  der Modellposition und unverändertes aufrechtes Home links vorne. Das mobile
 38mm-A4-Board wird hierfür nicht verwendet. Linke Marker-IDs0–16.
- Hardware-Kalibrier-CLI für alle vier Arm-IDs geöffnet; erster MoveIt-/IK-Weg
  links hinten offline geprüft, rechte Arme unverändert.25 passende Tests
  bestanden, einschließlich CLI-Auswahl und Lyrical-Startup-Warnpfaden.

## Noch offen

`ros.urp` wurde geladen und meldete zwischenzeitlich nativ **PLAYING**; dabei wurde
`/programs/tobias.installation` mitgeladen. **External Control ist nicht bestätigt**:
ROS `robot_program_running=false`, keine eingehende Verbindung an PC52001–52004,
obwohl alle vier Listener vorhanden sind. Nutzer um Prüfung des tatsächlich
ausgeführten External-Control-Knotens und seiner **aktiven** Installation gebeten:
Host192.168.8.209, Port52002. PLAYING allein ist kein Nachweis der Verbindung.

Abschließender Lesestand während der erbetenen Pendantprüfung:
links hinten RUNNING/**Local/STOPPED ros.urp**, Safety NORMAL. Beide rechten
Arme POWER_OFF/Local. Während dieser Konfigurationsprüfung keine erneuten
automatischen Startversuche. Der genaue Snapshot steht in `final-readiness.json`.

Hinten rechts steht noch Local/POWER_OFF und liefert sechs Nullwinkel.
Vorne rechts liefert ausgeschaltet nicht-null Encoderwerte, bleibt für den
finalen frischen Kollisionsstand aber ebenfalls zu prüfen. Keine ausgeschalteten
Nullwerte als tatsächliche Hindernispose übernehmen. Nutzer um Remote/aktuellen
Zustand hinten rechts gebeten. Dessen Programmstart ist hierfür nicht nötig.

## Vorbereitete Artefakte

Unter `setup/calibration/hardware_handeye/left_rear_20261112/`:

- `preparation/`: Dashboard-/RTDE-/ROS-Zustände, Kamerabilder/Readbacks,
  `manual-states.json` ausschließlich für bestätigtes links-vorne-Home und
  `preparation-plan.json` mit dem weiteren Ablauf.
- `design_preview/plan.json` und `preview.png`: erste nominelle Boardansicht,
  etwa34,1s. **Nicht ausführbar**: beide rechten Hindernisstellungen sind in
  dieser Entwurfsvorschau ausdrücklich unbestätigt. Historische rechte Posen
  dienen nur der Darstellung; keine reale Fahrfreigabe ableiten.

Vorgeschlagen für die spätere Reihe:41 Gesamtansichten(erste+40 weitere),
33 Fit/8 vorher reservierte Prüfungen, `wide` für Bildabdeckung. Eigene
Intrinsics/Kameramontage für links hinten; keine Werte der rechten Kameras fitten.
Noch keine Messsitzung begonnen, keine automatische Rückfahrt.

Sobald External Control und alle Hindernisstellungen geklärt sind, **neu planen**:

```bash
cd ~/UWA_ws
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control handeye_hardware plan-view --arm left_rear \
  --manual-states setup/calibration/hardware_handeye/left_rear_20261112/preparation/manual-states.json \
  --output setup/calibration/hardware_handeye/left_rear_20261112/approach
ros2 run uwa_cell_control park_arm preview \
  setup/calibration/hardware_handeye/left_rear_20261112/approach/plan.json
```

Diese Befehle senden keine Fahrt. Erst konkrete Vorschau und tatsächlichen
Fahrbereich prüfen/freigeben; dann erste Pose anfahren, echtes Boardbild/Fokus
prüfen und erst anschließend die vollständige Reihe aus dieser Pose planen.

## Behobener Startfehler

Das vorhandene MATCH-Skript
`mur_robot/mur_launch_hardware/scripts/ur_startup_enable.py` verwendete die unter
Lyrical entfernte Logger-Methode `warn`, wodurch die Diagnosebehandlung selbst
mit AttributeError abbrach. Auf `warning` umgestellt; zwei Offline-Regressions-
tests üben die tatsächlich betroffenen SetMode-/Timeout-Pfade ohne Hardware aus.
Keine Stopps/Schutzfunktionen oder Rücksetzregeln geändert.

Die erste ROS-Programmladeantwort überschritt den auf3s gesetzten Dashboard-
Timeout und trennte dessen Client. Direkte native Ladeantwort mit längerer
Wartezeit: `Loading program: /programs/ros.urp, /programs/tobias.installation`.
Danach geladenen Pfad geprüft, Clientverbindung erneut aufgebaut und den vom
Nutzer beauftragten Play-Befehl nativ bestätigt(`Starting program`). Das ist
kein Nachweis des weiterhin fehlenden External-Control-Links. Keine pauschalen
Treiber-/ROS-Neustarts und keine Schutzstoppquittierung ausgeführt.
