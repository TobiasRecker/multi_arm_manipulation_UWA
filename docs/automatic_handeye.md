# Automatische Hand-Auge-Kalibrierung in der Simulation

Die Pakete `uwa_cell_calibration` und `uwa_cell_calibration_msgs` führen
überwachte Messfahrten aus. Sie schätzen die unbekannte Kameramontage jedes
Arms und die relative Lage der beiden Roboter auf demselben Tisch. Die linke
und rechte Tischgruppe werden getrennt ausgewertet. Die Routine verbindet
sich ausschließlich mit der isolierten Simulation (Domain 64, Partition
`uwa_cell_sim`). Eine reale UR-Anbindung ist nicht enthalten.

## Start und Bedienung

Nach dem Build aller vier Repository-Pakete die Zelle wie gewohnt starten.
Nach erstmaliger Installation der Kalibrierung die Zelle einmal neu starten,
damit ihre Armcontroller die neuen Abbremsparameter laden. Der Backend prüft
dies vor der Vorbereitung.

```bash
cd ~/UWA_ws
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 launch uwa_cell_calibration calibration.launch.py
```

Dieser Launch startet Backend und Qt6-GUI als getrennte Prozesse. Gazebo,
Scan und die bisherige Zellsteuerung laufen unabhängig weiter. Ein weiterer
Launch verbindet seine GUI mit einem bereits laufenden Kalibrierbackend.
Ein abweichendes `layout:=/absolute/path/cell_layout.yaml` wird nur beim
ersten Backend-Start berücksichtigt und muss zur laufenden Zelle passen.

1. In rqt die manuelle Trajektorienausgabe deaktivieren. Alle Arme und Greifer
   müssen stillstehen. Bereits geparkte Arme sind im Paarmodus zulässig;
   die Vorbereitung prüft die Rückpositionierung zur konfigurierten Boardansicht.
2. Roboter wählen, standardmäßig alle vier. Die Messzahl ist von 30 bis 50
   einstellbar, Standard 40. **Diagonalpaare** ist standardmäßig aktiv;
   ausgeschaltet bleibt der bisherige Einzelarmmodus ohne Parkfolge verfügbar.
3. **Posen vorbereiten** prüft Telemetrie, Controller, Sichtfeld, Kinematik,
   Kollisionswege und Rotationsvielfalt. Pro Arm werden acht oder mindestens
   20 % zusätzliche Reserveansichten gespeichert. Zu wenige gültige Ziele
   verhindern den Start. Während der Planung zeigt die GUI geprüfte Ziele
   und die Zahl ausgeschlossener Kandidaten.
4. **Start** parkt zuerst links hinten und rechts vorne nacheinander zur Seite.
   **Links vorne + rechts hinten** bewegen sich anschließend gemeinsam und
   nehmen ihre jeweiligen Boards parallel auf. Danach parken diese beiden,
   während **links hinten + rechts vorne** zur Boardansicht fahren und parallel
   messen. Bei einer Teilmenge werden nur ausgewählte Arme der beiden Gruppen
   vermessen; andere Arme werden dennoch bei Bedarf geparkt. Setupwege bleiben
   seriell. Die GUI zeigt beide aktiven Arme, Parkzustand, Schritt und Zähler je Arm.
5. **Pause** bremst alle aktiven Controller ab. Erst nach bestätigtem Stillstand
   aller Arme wird **Fortsetzen** möglich. Der unterbrochene Zielweg wird aus dem
   tatsächlichen Zustand neu geprüft und die Aufnahme gegebenenfalls wiederholt.
6. **STOPP** verriegelt weitere Befehle und bricht die Sitzung ab. Bereits
   gespeicherte Daten bleiben erhalten. Es gibt nach Stopp oder Fehler keine
   automatische Rückfahrt. Eine neue Fahrt erfordert erneutes Vorbereiten.
7. Nach regulärem Abschluss beider Gruppen folgt für alle umpositionierten Arme
   eine erneut kollisionsgeprüfte serielle Rückfahrt zur tatsächlich bei
   Sitzungsstart gemessenen Stellung. Im Einzelarmmodus bleibt die Rückfahrt
   nach jedem Arm erhalten. Anschließend
   werden Schätzung, unabhängige Validierung und Ground-Truth-Abweichungen
   getrennt im Tab **Ergebnisse** angezeigt; **Livebilder** bleibt verfügbar.
8. **Ergebnis übernehmen** ist eine ausdrückliche Aktivierung des bestandenen
   Ergebnisses im Stillstand. Der Dialog beschreibt das getrennte Modell.

**Simulation pausieren** fordert den Stopp an und pausiert Gazebo zusätzlich
direkt über Gazebo Transport, unabhängig vom ROS-Backend. Die Welt kann danach
bewusst in Gazebo fortgesetzt werden; die abgebrochene Kalibriersitzung läuft
dadurch nicht wieder an.

Ohne GUI, beispielsweise für einen reproduzierbaren Prüfstandlauf:

```bash
ros2 launch uwa_cell_calibration calibration.launch.py gui:=false
# In einem zweiten Terminal nach dem gleichen env.bash:
ros2 run uwa_cell_calibration calibration_cli --samples 40
# Optional ausdrücklich auch das bestandene Profil aktivieren:
ros2 run uwa_cell_calibration calibration_cli --samples 40 --apply
# Nur ein Arm / eine andere Messzahl:
ros2 run uwa_cell_calibration calibration_cli --robots left_front --samples 30
# Bisheriger Einzelarmablauf ohne Parken anderer Arme:
ros2 run uwa_cell_calibration calibration_cli --samples 40 --sequential
```

## Planung und Aufnahme

Die reproduzierbaren Halton-Kandidaten liegen auf einer Kugelkappe um die
Boardmitte. Kameradistanz, Blickrichtung, Neigung und Rollwinkel variieren.
Die nominelle Kameramontage wird hierfür als Planungshilfe verwendet. Die
vollständige Musterfläche einschließlich Rand muss mit Sicherheitsrand im
Bild liegen; das echte Bild muss danach nochmals erfolgreich erkannt werden.

Der getrennte Planungsworker verwendet die installierte MoveIt-Python-
Bibliothek (`moveit.core`): `RobotModel`, vier SRDF-Armgruppen, `RobotState`
und `PlanningScene`. Er prüft die Kollisionsgeometrie der Tische, Boardplatten,
Arme, Greifer, Kameras und des Bodens gemeinsam. Absichtlich berührende
starre Montageflächen und Gelenknachbarn stehen in der Allowed Collision
Matrix; die übrigen Arme bleiben Hindernisse. Der dekorative Board-Musterlink
hat keine eigene Kollisionsgeometrie, seine darunterliegende Platte schon.

Die Verbindungen sind quintisch zeitparametrierte lokale Gelenkwege und
werden mit MoveIt über den gesamten Verlauf geprüft, mit höchstens 0,005 rad
Gelenkschritt und höchstens 0,1 s Zeitschritt. Sie halten 0,10 rad/s und
0,20 rad/s² ein. Blockierte Verbindungen werden verworfen. Diese Version
sucht keine OMPL-Umwege. Vor
jeder Ausführung erfolgt die Prüfung erneut vom tatsächlichen Gelenkzustand.
Passiv gekoppelte Greifergelenke berechnet MoveIt aus dem angetriebenen Gelenk.

Parkstellungen werden per IK seitlich über den jeweiligen Montagebereich
berechnet und anhand erreichbarer kollisionsgeprüfter Wege ausgewählt. Es wird
keine Kamerablickrichtung beim Parken erzwungen. Für die aktive Gruppe dienen
die zentralen `initial_positions` als Boardansicht; alle Anfahrwege werden
ebenfalls geprüft. Parkziele, Reihenfolge und Paar-Zertifikate stehen im Plan.

Beide Trajektorien eines Diagonalpaars bekommen dieselbe Dauer und denselben
zukünftigen ROS-Startzeitstempel. Vor dem Versand müssen die Zustände weiterhin
still und passend sein; beide Controller müssen rechtzeitig vor dem Start
bestätigen. Zusätzlich umschließen konservative Hüllboxen alle Kollisionskörper
jedes Arms über seinen vollständigen geplanten Weg. Sie erhalten **80 mm Puffer
je Arm** und müssen getrennt bleiben. Damit hängt die Trennung der nominalen
Wege nicht von identischem Bewegungsfortschritt ab; auch ein bereits stehender
Partner wird berücksichtigt. Überschneidende Hüllräume verhindern die Fahrt,
selbst wenn ein exakt synchroner Verlauf kollisionsfrei wäre. Dieses Kriterium
ersetzt keine Hardware-Sicherheitsbewertung.

Die tatsächliche Reichweite wird nicht pauschal aus dem Roboternamen abgeleitet.
Die Freigabe bezieht sich auf Modell und geplante Bewegungsräume. Die beiden
Arme erreichen eine Stellung gemeinsam und stehen beide mindestens 0,5 s still;
die Auswahl aus fünf frischen Bildern erfolgt dann gleichzeitig pro Kamera.
Scheitert nur eine Aufnahme, bleibt der erfolgreich aufgenommene Partner stehen,
während der andere sein Bild wiederholt oder eine geprüfte Reservepose anfährt.

Nach Zielerreichung (maximal 0,02 rad Gelenkfehler) und mindestens 0,5 s
Stillstand in Simulationszeit werden fünf frische gültige Bilder gesammelt.
Mindestens zwölf nicht kollineare ChArUco-Ecken und höchstens 1 px PnP-RMS
sind erforderlich. Das schärfste Bild anhand der Laplace-Varianz wird
gespeichert. Ein Bildzeitstempel wird nur mit passendem TF und einem
Gelenkdatensatz innerhalb von 40 ms akzeptiert. Fehlende TFs werden innerhalb
des Aufnahmefensters abgewartet. Nach drei erfolglosen Aufnahmeversuchen
ersetzt eine Reservepose das Ziel und übernimmt dessen Fit-/Validierungsrolle.
Bewegungs- und Telemetriefehler lösen stattdessen einen Stopp aus.

## Schätzung und Koordinatenrichtungen

`T_A_B` bildet Koordinaten aus B nach A ab. Pro Roboter sind die aus der
Gelenkkinematik gemessenen Werkzeugposen `M_i = T_base_link_tool0(i)` und
die bildbasierten Boardposen `C_i = T_camera_optical_board(i)` bekannt.
Geschätzt werden gemeinsam:

```text
X = T_tool0_camera_optical
Y = T_base_link_board
M_i · X · C_i = Y
```

OpenCV `calibrateHandEye(..., CALIB_HAND_EYE_PARK)` initialisiert die Schätzung.
Anschließend optimiert SciPy beide Transformationen gemeinsam gegen die
gespeicherten Bildecken mit robuster `soft_l1`-Verlustfunktion. Intrinsics und
Verzerrung aus CameraInfo bleiben fest. Mehr als 20 % Fit-Ausreißer oder
unzureichende unabhängige Rotationen führen zur Ablehnung.

Die Fit-/Validierungsrollen stehen bereits in `plan.json`, vor jeder Aufnahme.
Jede fünfte angenommene Halton-Ansicht wird zurückgehalten, ihre Rolle bleibt
bei der kürzeren Fahrreihenfolge unverändert. Damit ergeben sich bei 40
Stellungen **32 Fit- und acht unabhängige Validierungsbilder**. Bei anderen
Messzahlen sind es 20 % Validierungsbilder, abgerundet (mindestens sechs).
Validierungsbilder ändern weder die Schätzung noch deren Ausreißerauswahl.

Pro Tisch ergibt sich:

```text
T_front_base_rear_base = Y_front · inv(Y_rear)
Basisabstand [mm]      = 1000 · norm(T_front_base_rear_base.translation)
T_table_top_base       = T_table_top_board(config) · inv(Y)
```

Die relative Basispose benötigt keine bekannte Boardlage im Tisch. Die
zusätzlich ausgegebene absolute Tischpose hängt von dieser konfigurierten
Boardlage ab. `base_link` ist gegenüber dem UR-`base` um 180° gedreht;
die Ergebnisse beziehen sich ausdrücklich auf `base_link`. Der Boardframe
ist die OpenCV-Musterecke gemäß [Boardanleitung](charuco_calibration.md).

Der Solver importiert weder Layout noch nominelle Kameramontagen oder
Welt-TFs. Ground Truth wird erst nach seiner Rückgabe separat ausgewertet.
Qualitätsfreigabe verlangt:

- ausreichend viele unterschiedliche Stellungen und Rotationen um mindestens
  zwei unabhängige Achsen,
- medianen Validierungs-Reprojektions-RMS ≤ 1 px,
- Boardkonsistenz der Validierungsposen ≤ 5 mm Translation und ≤ 0,5° Rotation
  als RMS.

Ein aktivierbares Profil muss 30–50 tatsächlich erfasste unterschiedliche
Stellungen je enthaltenem Roboter nachweisen; kürzere diagnostische Teilfits
können berechnet, aber nicht aktiviert werden.

100 Park-Bootstrap-Ziehungen liefern Kamerastreuung, relative Posestreuung
und ein 95%-Quantilintervall des Basisabstands. Das beschreibt die
Wiederholungsstreuung des vorliegenden Datensatzes, keine nachgewiesene
absolute Messgenauigkeit. Die simulierten Kameras haben ideale nominelle
Intrinsics; reale Optik, Boardplanheit und echte UR-Kinematik sind gesonderte
Fehlerquellen einer späteren Hardwareversion.

## Dateien und aktive Profile

Jede Vorbereitung erzeugt ein eigenes Verzeichnis unter
`$UWA_WS/setup/calibration/<Datum_Uhrzeit_ID>/`:

```text
plan.json                         Ziele, Reserven, Rollen, Wege, Modellfingerprint
left_front/sample_000_raw.png      unverändertes Kamerabild
left_front/sample_000_annotated.png erkannte Achsen / Ecken
left_front/sample_000.json         Punkte, Intrinsics/CameraInfo, Zeit, Gelenke, M_i, C_i
... weitere Aufnahmen / Roboter ...
result.json                       Schätzung und unabhängige Qualitätswerte
ground_truth_validation.json      ausschließlich der nachträgliche GT-Vergleich
```

Nachträgliche Auswertung ohne Zellverbindung:

```bash
ros2 run uwa_cell_calibration calibration_solve "$UWA_WS/setup/calibration/<Sitzung>"
```

Der Offline-Solver schreibt `result.json` neu mit den bildbasierten Ergebnissen.
Bei vorhandenem `plan.json` übernimmt er anschließend dessen Modellfingerprint
und leitet die Tischposen ab. Vorherige Live-Ergebnisse gegebenenfalls kopieren.
Sitzungen, Rohbilder und lokale Profile liegen außerhalb des Quell-Repositories
und werden nicht eingecheckt.

Übernehmen validiert Qualität, starre Transformationen, Modellfingerprint und
den aktuellen Stillstand. Erst wenn ein neues kalibriertes MoveIt-Modell
erfolgreich geladen und kollisionsgeprüft ist, wird ein eigenes versioniertes
Profil und atomar `profiles/active.json` geschrieben. Fehler behalten das
vorherige Profil und Modell. Eine Teilkalibrierung ergänzt ein bestehendes
kompatibles Profil für andere Arme. Beim Backend-Start wird das aktive kompatible
Profil nach Empfang der Zelltelemetrie wieder geladen; unpassende Profile
werden abgewiesen.

Das aktive Modell veröffentlicht:

- `/uwa_cell/calibrated/robot_description` (transient local),
- TF-Links mit Präfix `calibrated/`, beispielsweise
  `calibrated/left_front_base_link` und `calibrated/left_front_wrist_camera_optical_frame`.

Beide Bäume teilen nur den Referenzframe `world`. Gelenknamen bleiben für die
Controller unverändert. Neue Kalibrierwege verwenden anschließend das
kalibrierte Planungsmodell. Die Gazebo-Geometrie, physischen Montagen,
ursprüngliche Beschreibung und ursprünglichen Ground-Truth-TFs werden dabei
nicht ersetzt und die Zell-Simulation wird nicht neu gestartet.

## Überwachung und ROS-Schnittstellen

Unter `/uwa_cell/calibration`:

| Schnittstelle | Typ | Zweck |
|---|---|---|
| `prepare` | `PrepareCalibration` Service | Roboter, Messzahl, Besitzer-ID, `diagonal_pairs` (Standard true); startet Vorbereitung asynchron |
| `run` | `RunCalibration` Action | geprüfte `plan_id`, Feedback, Ergebnis, Abbruch |
| `pause`, `resume`, `stop` | `std_srvs/Trigger` | bewusste Steuerung und verriegelter Stopp |
| `pause_world` | `std_srvs/Trigger` | zusätzliche Gazebo-Pause |
| `apply` | `ApplyCalibration` Service | Ergebnisdatei, Besitzer-ID; startet Profilprüfung |
| `heartbeat` | `std_msgs/String` | Besitzer-Lebenszeichen, 5 Hz |
| `status` | `std_msgs/String` JSON, transient local | Phase, Fortschritt, Qualität und Ergebnis |
| `<robot_id>/image_annotated` | `sensor_msgs/Image` | Liveerkennung |

Ein Dateilock verhindert mehrere Backends. Eine aktive Operation sperrt
weitere Sitzungen. Ein Lebenszeichen gehört zur vorbereitenden GUI oder zum
CLI-Client; andere GUIs können beobachten und stoppen. Nur eine responsive
GUI hält ihren Besitz aufrecht, ein noch laufender ROS-Thread allein reicht
nicht. Mehr als 1,5 s ohne Besitzer, veraltete Gelenke/Simulationszeit,
rückwärts springende Zeit, Kameraverlust, Controllerfehler, fremde
Trajektorientopics und unerwartete Bewegung anderer Gelenke lösen den Stopp aus.
Fremde Action-Ziele werden über verdrängte Controllerziele bzw. unerwartete
Bewegung erkannt; die Routine beansprucht keine exklusive Sperre fremder ROS-
Programme. Manuelle rqt-Ausgabe deshalb vor dem Start deaktivieren.

Der Stopp sperrt den Versand unter demselben Lock wie das Absenden eines
Trajektorienpaars, storniert **beide** Ziele einschließlich spät bestätigter
Ziele und wartet auf alle Ergebnisse sowie gemessenen Stillstand. Ein Fehler
eines Controllers stoppt die gesamte Gruppe. Die Armcontroller bremsen
stornierte Ziele kontrolliert ab; mindestens 0,5 rad/s² konfigurierte
Abbremsung wird vor der Sitzung geprüft. Wird der Stillstand nicht innerhalb 1,5 s
bestätigt, wird die Gazebo-Pause angefordert und deren Antwort ausgewertet.
Planung und Optimierung laufen in einem eigenen Prozess ohne Befehlsclients;
dessen Abbruch kann die Bewegungsüberwachung nicht blockieren.

Ist wegen eines Transportfehlers unklar, ob ein Controller ein Ziel angenommen
hat, wird dies nicht als Leerlauf gewertet: die Weltpause greift und eine neue
Sitzung bleibt bis zur Klärung bzw. einem Controller-/Zellreset gesperrt.
`motion_events.jsonl` protokolliert versendete Gruppen, gemeinsame Startzeiten,
Dauern und Hüllraumabstände; Sitzungsrohdaten bleiben außerhalb Git.

Dies ist ein überwachter Softwarestopp für die Simulation. Eine spätere
Hardwareversion braucht die reale UR-Anbindung und deren Stoppsystem.

## Prüfen

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
OPENBLAS_NUM_THREADS=1 python3 -m pytest \
  "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_gazebo/test" \
  "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test" -q
```

Die synthetischen Tests verwenden andere, dem Solver unbekannte Kamera- und
Basisposen sowie verrauschte Bildpunkte. Sie prüfen Richtungen, Ausreißer,
Degeneration, unabhängige Validierung, Kollisionsgeometrie, Grenzen,
Geschwindigkeiten und getrennte Modelle. Liveprüfungen benötigen eine freie
Zelle ohne andere Messfahrt; sie bewegen ausschließlich den linken vorderen Arm:

```bash
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/live_gui_check.py" --exercise
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/live_gui_check.py" --freeze
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/live_gui_check.py" --planning
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/live_gui_check.py" --capture
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/live_gui_check.py" --world-pause
ros2 run uwa_cell_calibration calibration_cli --robots left_front --stop-after 1
ros2 run uwa_cell_calibration calibration_cli --robots left_front --pause-after 3 --resume-after 2 --stop-after 12
```

Vollständigen 40×4-Datensatz offline prüfen und bei unverändert zurückgekehrten
Armen die Live-Profilprüfung ausführen:

```bash
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/check_completed_session.py" \
  "$UWA_WS/setup/calibration/<Sitzung>" --output /tmp/handeye-acceptance.json
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_calibration/test/live_profile_check.py" \
  "$UWA_WS/setup/calibration/<Sitzung>" --output /tmp/handeye-profile-check.json
```

Der [Prüfbericht vom 2026-11-09](handeye_validation_2026-11-09.json) dokumentiert
den bestandenen vollständigen Lauf: maximal 0,131 mm / 0,035° Kamerafehler und
0,640 mm / 0,054° relativer Basisfehler gegen Ground Truth. Die synthetischen
und Offlineprüfungen umfassen 57 bestandene Tests. Das sind Nachweise in der
Simulation, keine Genauigkeitsfreigabe für die reale Zelle.

Den datierten Stand der tatsächlich ausgeführten Prüfungen und ihrer Grenzen
enthält [HANDOVER.md](../HANDOVER.md). Referenzen:
[OpenCV Hand-Auge-Kalibrierung](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html),
[MoveIt Python API und Planning Scene](https://moveit.picknik.ai/main/doc/examples/motion_planning_python_api/motion_planning_python_api_tutorial.html).
