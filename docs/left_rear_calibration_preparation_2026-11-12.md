# Links hinten: Kalibrierung vorbereiten

Stand2026-11-12. Ziel **left_rear=192.168.8.169**, konfigurierter UR7e,
Seriennummer20265701623. Individuelle Werkskinematik bereits im gemeinsamen
Messprofil vorhanden. Vorherige rechte Kalibrierergebnisse bleiben erhalten.

## Erste Pose erreicht und echtes Board geprüft

Nach ausdrücklicher Nutzerfreigabe für genau `approach_ready/plan.json` wurde
die34,173s-Bewegung ausschließlich links hinten ausgeführt. Native Action
erfolgreich(Result0); unmittelbarer größter Zielwinkel-Fehler0,0000158rad,
späterer Stillstandssnapshot0,0000513rad. Safety NORMAL, External Control true,
gemeldete Gelenkgeschwindigkeiten null. Skalierter JTC hält die erreichte Pose;
andere linke Bewegungscontroller inaktiv, keine automatische Rückfahrt.
Front-Endvergleich0rad, Rear-Endvergleich0,0000246rad gegenüber Wegstart;
dies sind Endvergleiche, keine kontinuierlich gemessenen Maximalwerte.

Fünf echte640×480-Bilder gelesen: das erste während Fokus-Einschwingen noch
unscharf, danach **viermal17/17 Marker und24/24 ChArUco-Ecken**, korrekte
linke IDs0–16. Sichtprüfung: gesamtes Muster im Bild, keine Musterverdeckung
im geprüften Bild. Fünf unterschiedliche decodierte Payloads. Autofokus-
Readback danach406Auto, Belichtung33333µsAuto/Gain16. Keine Kamerawerte
geschrieben. Diese Bilder sind **Diagnose, noch keine Fit-/Prüfaufnahmen**.

Artefakte `first_view_inspection/{inspection.json,frame_04.jpg,
frame_04_annotated.jpg}` sowie `preparation/first-view-{approval,execution.log,
completion.json}`. Eigene erledigte Domain68-Weganimation beendet; Hardware-
GUIs/drei Treiber bleiben erhalten. Das Log enthält nichtfatale
ROS-typesupport-Meldungen; tatsächliches Action-Ergebnis/Endwinkel separat geprüft.

Zusätzlich **nur geplant**: `batch_plan/batch.json`,40 weitere Ansichten mit
8 vorab bestimmten Prüfrollen, damit später41 Gesamtansichten/33Fit/8Prüfung.
Reine Bewegungsdauer709,57s, zusätzlich Stillstands-/Aufnahmezeiten. Noch keine
Reihe freigegeben/ausgeführt, kein sample000 und kein Intrinsics-/Hand-Auge-Fit.
Vor Messaufnahmen Fokus/Belichtung passend fixieren, sample000 stationär
erfassen und dann gesamte Folge per `run-series --check-only` sowie Vorschau
prüfen. Neue gesamte Fahrfolge erst nach eigener konkreter Freigabe ausführen.

## Vorbereitungsnachweis vor der ersten ausgeführten Fahrt

**Verbindung bestätigt:** ros.urp über MATCH erfolgreich gestartet,
`robot_program_running=true`, Safety NORMAL, alle vier linken Motioncontroller
inaktiv. Hinten rechts jetzt RUNNING mit echten Gelenkwerten. Vorne rechts
bleibt für die parallele Kameraarbeit ausgeschaltet; seine gemeldeten nicht-null
Winkel wurden über einen unabhängigen reinen RTDE-Leseclient gegengeprüft
(maximale Differenz4,5e−16rad), ohne Power-/Programm-/Kamerazustand zu ändern.

Frischer Plan **`approach_ready/plan.json`**,34,173s,343 Kollisionssamples,
vollständige MoveIt-Szene und aktuelle gemeldete Gelenke; links vorne bleibt die
vom Nutzer bestätigte nominelle Home-Angabe. `--check-only` erfolgreich.
RViz-Animation war in Domain68 offen; die anschließend freigegebene erste Fahrt
und Bildprüfung sind im aktuellen Abschnitt oben dokumentiert.
Kamera endet nominell bei Welt[-0,45;0,28;1,453]m, etwa55cm über dem Board.
Die damalige Freigabe galt nur der ersten Pose und Bildprüfung, keiner ganzen Reihe.

### Verbindungsfehler eingegrenzt

Der alte, seit dem Vortag laufende linke Manager hatte8998 offene Dateideskriptoren,
davon8967Sockets. Der Scriptserver protokollierte tatsächlich eintreffende
Verbindungen, verwarf aber deren FD8997/8998 wegen `FD_SETSIZE=1024`.
Damit war die URCap-Konfiguration nicht als Ursache belegt; vorherige
Konfigurationsfragen und fehlgeschlagene Startversuche unten sind Historie.

Nur den anhand PID/Argumenten/Prozessgruppe geprüften Links-Launcher nach
bestätigter Inaktivität sauber beendet und left_rear neu gestartet. Neuer
Manager48FDs, anschließender vorhandener MATCH-Start erfolgreich, External
Control true. Beide rechten Manageridentitäten unverändert. Die Ursache des
FD-Wachstums selbst ist noch nicht abschließend bestimmt; kein allgemeiner
Socketfehlerfix oder Langzeitnachweis behauptet. Logs/FD-Vergleich und
`after-driver-restart.json` unter `preparation/`.

Der neue linke Treiber läuft separat im Benutzerdienst
`uwa-left-rear-calibration-driver`; vorhandene GUIs können ihn weiterverwenden.
Keine Schutzstoppquittierung, keine Trajektorie und keine Kameraparameteränderung.

Die folgenden Abschnitte beschreiben den vorherigen Vorbereitungs-/Diagnosestand.

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

## Historische offene Verbindung vor dem Links-Neustart

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
