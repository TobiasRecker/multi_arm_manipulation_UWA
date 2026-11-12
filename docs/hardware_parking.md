# Wartepose vor der Kamerakalibrierung

**Modellstand2026-11-11:** Neue Pläne verwenden standardmäßig das
[gemeinsame Messprofil](applied_calibrations.md), einschließlich individueller
Werkskinematiken. Gespeicherte Parkziele sind benannte Referenzen; alte Wege
mit altem Inventar-/Layoutfingerprint werden nicht wiederverwendet. Vor einem
neuen Weg aktuelle Zustände und das aktuelle Kollisionsmodell verwenden.

Stand2026-11-10. Ein generisches Werkzeug parkt **genau einen ausgewählten Arm**;
erster Hardwarekandidat ist **right_front =192.168.8.103**. Beide linken Arme
stehen laut Nutzer bereits aufrecht in Default Home. Das ist als nominelle
Nutzerangabe `[0,−90,0,−90,0,0]°` dokumentiert, nicht als Encodermessung.
Hinten rechts wurde manuelles reales Jogging vom Nutzer erfolgreich bestätigt.
Der automatische Kalibrierbackend bleibt Simulation-only.

## Ablauf

Aus `~/UWA_ws`:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control park_arm plan --mode hardware --arm right_front \
  --manual-states setup/calibration/parking/left_home.json \
  --output setup/calibration/parking/right_front_hardware
ros2 run uwa_cell_control park_arm preview \
  setup/calibration/parking/right_front_hardware/plan.json
```

`plan` liest die konfigurierten JointState-Quellen und schreibt `states.json`,
`plan.json`, `preview.png` und die dazugehörigen lokalen Modellressourcen. Es
aktiviert keinen Controller, sendet keine Fahrt und schaltet keinen UR ein.
Ohne beobachtete/angegebene Stellung eines Arms darf dessen Layoutpose nur in
einer ausdrücklich **nicht ausführbaren Vorschau** auftauchen. Der bewegte Arm
benötigt immer aktuelle Live-Gelenkstände. `--snapshot` dient Offline-/Mock-Tests;
falscher Modus und Mockdaten in Hardwareplänen werden zurückgewiesen.

Die Vorschau verwendet eine eigene **Domain68**, echte Hardware66, Mock67 und
Gazebo64 bleiben getrennt. Sie startet nur RobotStatePublisher und RViz; keine
Kommandobrücke. Animation läuft vierfach beschleunigt in einer Schleife.
Mit dem Schließen dieses RViz-Fensters endet der Vorschauprozess samt eigenem
Publisher. Die PNG zeigt nur Gelenkketten; RViz zeigt vollständige Geometrie.

Nach Prüfung der konkreten Pose und des freien realen Fahrbereichs:

```bash
ros2 run uwa_cell_control park_arm execute \
  setup/calibration/parking/right_front_hardware/plan.json
```

Mit zusätzlichem `--check-only` prüft dasselbe Kommando aktuelle Startstände
und vollständigen Weg, ohne Controller zu wechseln oder eine Action zu senden.

Das führt ausschließlich den gespeicherten Pfad am gespeicherten Modus/Arm aus.
Vorher werden Inventar-/Planhash, aktuelles Layout, aktuelle Startstände und alle
Wegpunkte erneut geprüft. Geänderte Startstände brauchen einen neuen Plan.
Kein automatisches Power/Brake/Play: Treiber und External-Control-Programm müssen
bereit sein. Vorne rechts PC192.168.8.209/Port53002; hinten rechts Port54002.
Bei Treiberneustart kann ein erneuter bewusster Programmstart am UR nötig sein.

**Ctrl+C** im Ausführungsterminal fordert Abbruch und Deaktivierung des eigenen
Bewegungscontrollers an. **STOP** der UWA-Arme-GUI kann den ausgewählten Arm
ebenfalls stoppen. Das sind Softwareaktionen, kein Hardware-Not-Halt. Das Skript
kehrt nach Stopp/Fehler nicht automatisch zurück und bewegt keinen zweiten Arm.

## Modell und Regler

Das Werkzeug verwendet die vorhandene vollständige MoveIt-Zell-Kollisionsszene
aus `uwa_cell_calibration`, das zentrale Layout und die UR-Typen/Kinematikdateien
aus dem Hardwareinventar. Tischmaße/Montageposen/Werkzeuge sind weiterhin
vorläufig. Personen, lose Objekte und nicht modellierte Aufbauten werden nicht
erkannt. Nominell offene Greifer sind Bestandteil des Modells; ihre tatsächliche
Konfiguration und der reale Fahrbereich müssen zum Modell passen.

Ein IK-Suchlauf sucht das Werkzeug kompakt zur jeweiligen Tischaußenseite,
etwa0,25–0,40m seitlich und0,50–0,65m über der Basis. Er hält Gelenkänderungen
klein und erzwingt keine neue Werkzeugorientierung. Als Alternative kann
`--target-deg=q1,q2,q3,q4,q5,q6` eine explizite Gelenkpose vorgegeben werden.
Die Gelenkreihenfolge ist immer Schulter-Pan, Schulter-Lift, Ellenbogen,
Handgelenk1/2/3. Bezeichnungen in ROS-Nachrichten werden darauf abgebildet.

Der akzeptierte Weg ist eine **lokale quintische Gelenkverbindung**, an maximal
0,005rad Gelenkschritten und mindestens alle0,1s gegen alle vier Arme, Werkzeuge,
Tische und Boden in MoveIt geprüft. Das ist keine OMPL-Umwegplanung. Blockierte
Wege werden abgelehnt; das Skript fährt keinen ungeprüften Ersatzweg.
Standardlimits0,05rad/s und0,10rad/s²; zusätzliche Begrenzungen im nativen
UR-Treiber bleiben wirksam. Das sind Modellprüfungen, keine Garantie realer
Kollisionsfreiheit bei unkalibrierten oder unvollständigen Geometriedaten.

Die generische Ausführung bleibt im MATCH-Adapter `match_ur_hardware.trajectory`.
Punkt-zu-Punkt-Parken verwendet den nativen skalierten UR-JointTrajectoryController,
Mock den normalen JTC. Nur der Controller des ausgewählten Arms wird gewechselt;
der Admittanzregler bleibt für manuelles Jogging verfügbar. Aus dem Parkskript
werden keine Dashboard-/Bremsen-/Power-/SSH-Kommandos gesendet.
Ein erfolgreiches Parken lässt den nativen JTC die erreichte Stellung halten.

Während der Fahrt werden die Live-Daten aller beobachteten Arme überwacht.
Ausfall länger0,5s oder Bewegung eines als stationär geplanten Arms über0,015rad
führt zu Action-Abbruch und eigener Controllerdeaktivierung. Vor der Fahrt sind
höchstens0,01rad Abweichung vom geplanten Start erlaubt, am Ziel0,03rad.
Manuelle Home-/Pendantangaben können nicht live überwacht werden; diese Arme
müssen unverändert stehen bleiben. Diese Anforderungen prüfen die Gültigkeit
des konkreten Pfads und ersetzen keine zuvor entfernten Dashboard-Freigabegates.

## Andere Arme und manuelle Stellungen

`--arm` unterstützt alle vier stabilen Arm-IDs. Ohne IP wird kein Hardwarearm
gestartet oder erraten. Linke IPs später ins zentrale Inventar eintragen, dann
bevorzugt auch deren echte JointStates lesen. Manuelle Zustände sind JSON:

```json
{
  "left_front": {
    "unit": "deg", "positions": [0, -90, 0, -90, 0, 0],
    "source": "user_nominal_home", "recorded_at": "2026-11-10 user report"
  }
}
```

`source: manual_pendant` ist für tatsächlich am Pendant abgelesene Zahlen,
`user_nominal_home` für ausdrücklich angegebene nominelle Home-Posen. Einheiten
sind Pflicht. Live-Messungen haben Vorrang vor manuellen Angaben. Keine solchen
lokalen Sitzungs-/Zustandsdateien ins Git übernehmen.

## Prüfungen und Hardwarestand

- Zwei Pakete gebaut: `setup/logs/uwa-parking-build.log`.
- 23 gezielte Offline-/MoveIt-/GUI-/Adaptertests bestanden:
  `setup/logs/uwa-parking-tests.log`.
- Vollständiger Mock-Parkpfad in Domain67 ausgeführt: etwa38,35s, Endabweichung
 1,1e−16rad, andere simulierte Armzustände unverändert. Anschließender Ausfall
  eines Hindernis-Zustandsstroms während tatsächlicher Mock-Fahrt stoppt und
  deaktiviert den Controller, gemessene Nachdrift0rad:
  `setup/logs/uwa-parking-live.json` und `uwa-parking-mock-{execute,cancel}.log`.
- Vorderer alter Manager publizierte sechs Nullen trotz aufgebauter Reverse-
  Verbindung. Output-only RTDE-Lesetest lieferte echte Winkel. Nur diesen alten
  Front-Launch ohne aktiven Bewegungscontroller ersetzt; beide rechten Treiber
  inaktiv neu gestartet. Frische ROS-Winkel stimmen danach mit RTDE überein.
  `setup/logs/uwa-parking-ready-joints.json` und `uwa-parking-{front,rear}-rtde.json`.
- **Erster Realtest erfolgreich**, nach ausdrücklicher Prüfung/Freigabe der
  konkreten RViz-Vorschau durch den Nutzer. Gespeicherter Weg etwa61,81s bei
  0,05rad/s und0,10rad/s²,620 MoveIt-Zwischenstände. Native skalierte JTC-Action
  SUCCEEDED/0, Endfehler maximal **0,0000356rad**. Hinterer rechter Arm während
  der Beobachtung höchstens0,000101rad Änderung (Messrauschen); linke Arme wurden
  nicht kommandiert und bleiben mangels Netzwerkdaten nur als Nutzer-Home bekannt.
- Nominelles tool0-Ziel im Modell **[0,8504,−0,6741,1,5500]m**; kein Nachweis
  kalibrierter kartesischer Genauigkeit. Gelenkziel in Grad:
  `[-283.049166,-104.221739,85.111850,-89.934257,-114.930279,-133.975544]`.
  Gespeicherte Winkel nicht modulo360 normalisieren: das kann einen anderen
  Gelenkweg erzeugen. Wiederholungen immer aus aktuellem Zustand neu planen.
- Ein erster Versuch brach ohne relevante Bewegung an der nativen Pfadtoleranz
  ab: Nach Treiberneustart fehlte die Reverse-Verbindung trotz DashboardPLAYING.
  Nutzer führte Stop→Play aus; danach53001/53003/53004 verbunden und natives
  robot_program_running=true. Derselbe freigegebene Weg wurde erfolgreich
  wiederholt. Keine Toleranzen erweitert, kein anderer Weg ausgeführt.
- Prüfnachweise: `setup/logs/uwa-parking-hardware-attempt2.log`,
  `uwa-parking-hardware-motion2.json`, `uwa-parking-final-{status,joints}.json`.
  Plan, Nutzerfreigabe, Vorschau und `execution_result.json` unter
  `setup/calibration/parking/right_front_hardware/`. Vorne rechts hält danach
  der aktive skalierte JTC; hinten rechts alle Bewegungscontroller inaktiv.
  Eigene Vorschau beendet, Hardware-GUI/Treiber geöffnet belassen.
- Keine automatische Hardware-Kamerakalibrierung gestartet. Native Logs enthalten
  weiterhin gelegentliche500Hz-Loop-Overruns und nicht fatale Typesupport-/MoveIt-
  Loggingwarnungen. Der Test beweist die einzelne Parkfahrt, keine garantierte
  Echtzeitfähigkeit oder allgemeine kooperative Bewegungsplanung.
