# Reale Wrist-Kamera: erste Sicht, Intrinsics und Hand-Auge

Stand2026-11-11. Test ausschließlich **right_rear192.168.8.170**. Vorne rechts
hält seine Parkpose; linke Arme laut Nutzer nominell Default Home, ohne
Live-Gelenkdaten. Bestehender Simulationsbackend bleibt Domain64; separates
Hardwarewerkzeug Domain66, Vorschau68, Mock67. Keine Kommandobrücke.

## Erste reale Reihe erfolgreich,2026-11-11

Die unterbrochene Reihe wurde nach der vom Nutzer angepassten Sicherheitsebene
mit beiden neu gemessenen rechten Armstellungen fortgesetzt. Alle41 Ansichten
mit24 Ecken gespeichert:33 für Fit und8 vorab reserviert für unabhängige Prüfung.
Keine Ausreißer ausgeschlossen. Modus640×480, fester manueller Fokus404.

| Prüfung | Ergebnis |
|---|---:|
| Intrinsics Fit-RMS |0,244px |
| Intrinsics Prüf-RMS, Median |0,222px |
| Hand-Auge Prüf-Reprojektion, Median |0,466px |
| Konsistenz der rekonstruierten Boardposition, RMS |2,660mm |
| Konsistenz der Boardrotation, RMS |0,246° |

Alle bestehenden Gütegrenzen bestanden. Die Werte beschreiben interne
Validierung, keine unabhängig vermessene absolute Genauigkeit. Ecken liegen
etwa im Bildbereich x140…431/y123…341; außerhalb davon sind insbesondere die
Bildränder noch nicht geprüft. HTTP liefert weiterhin keinen Belichtungszeitstempel.

Rohdaten und direkt auswertbare Dateien:
`setup/calibration/hardware_handeye/right_rear_20261110/`.
Versionierte Ergebniskopie mit SHA256-Manifest und Prüfgrafik:
`setup/calibration/hardware_handeye/right_rear_20261111/result_v1/`.
Enthält `intrinsics.json` und `handeye_result.json` (`T_tool0_camera` und
`T_base_board`). **Nichts automatisch aktiviert.** Rear hält die letzte
Aufnahmepose; Front-Bewegungscontroller inaktiv. GUI/Treiber bleiben offen.

## Intrinsics und Robotiq-URCap

Nutzer bestätigt A3-Druck1:1,100mm am Kontrollstreifen und rechtes ChArUco-Board
ungefähr an der Modellposition. Keine passende Intrinsics-Kalibrierung bekannt.
Für unsere Auswertung wird K/Verzeichnung aus den echten640×480-HTTP-Bildern
mit konstantem manuellem Fokus404 bestimmt. Simuliertes CameraInfo/nominelles
FOV werden ausschließlich zur Planung verwendet, nicht zum Fit.

Das Robotiq-URCap bietet **Installation → URCaps → Camera → Snapshot → Full
Calibration**. Laut [Handbuch,Abschnitte1.1.1/4.2](https://assets.robotiq.com/website-assets/support_documents/document/Wrist_Camera_Instruction_Manual_PDF_20210615.pdf)
bestimmt es Optik, Kameramontage und Arbeitsebene gemeinsam, mit eigenem
Robotiq-Muster. Passender Export für unseren HTTP-Modus noch ungeprüft; dieser
Assistent wurde nicht gestartet. Unsere eigene Intrinsics-Kalibrierung nutzt
[OpenCV/ChArUco](https://docs.opencv.org/4.x/da/d13/tutorial_aruco_calibration.html).

## Bedienung

Aus `~/UWA_ws`:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control handeye_hardware --help
ros2 run uwa_cell_control handeye_hardware plan-view --arm right_rear \
  --output setup/calibration/hardware_first_view/approach
ros2 run uwa_cell_control park_arm preview \
  setup/calibration/hardware_first_view/approach/plan.json
```

`park_arm execute <plan.json>` führt den konkret geprüften ersten Weg aus.
Danach eine ruhige Stellung erfassen:

```bash
ros2 run uwa_cell_control handeye_hardware capture --arm right_rear \
  --session setup/calibration/hardware_handeye/right_rear_20261110 \
  --sample-id sample_000 --role fit
ros2 run uwa_cell_control handeye_hardware plan-series --arm right_rear --count 40 \
  --output setup/calibration/hardware_handeye/right_rear_20261110/batch_plan
ros2 run uwa_cell_control park_arm preview \
  setup/calibration/hardware_handeye/right_rear_20261110/batch_plan/plan.json
ros2 run uwa_cell_control handeye_hardware run-series \
  setup/calibration/hardware_handeye/right_rear_20261110/batch_plan/batch.json \
  --session setup/calibration/hardware_handeye/right_rear_20261110 --check-only
```

Ohne `--check-only` startet das letzte Kommando die geprüfte Messreihe. Vorher
Vorschau/realen Fahrraum prüfen.40 weitere Ansichten plus erste Aufnahme,
8 vorab ausschließlich zur Validierung markiert. Diese8 Bilder fitten weder
Intrinsics noch Hand-Auge. Geometrie-/Inventar-/Startänderungen brauchen neue
Planung. Vorschauartefakte der Gesamtfolge sind nicht als eine durchgehende
Fahr-Action ausführbar; nur der Aufnahmeablauf fährt einzelne geprüfte Segmente.

Vor jeder Fahrt vollständige MoveIt-Kollisionsprüfung, Limits0,05rad/s und
0,10rad/s², aktuelle andere rechte Pose als festes Hindernis. Native
External-Control-Verbindung muss tatsächlich bestätigt sein; DashboardPLAYING
allein genügt nicht. Keine neuen Dashboard-Freigabegates für manuelle GUI-Tests.
**STOP** in der UWA-GUI oder **Ctrl+C** im Ausführungsterminal bricht ab.
Fehler deaktivieren den eigenen Bewegungscontroller; kein anderes Armkommando,
keine automatische Rückfahrt oder Power/Brake/Play-/Schutzstopp-Quittierung.
Nach normalem Abschluss bleibt die letzte Aufnahmepose stehen.

## Fortsetzung einer unterbrochenen Reihe

Nach Neustart aktuelle Gelenke lesen, Kameraoptik/Fokus wieder prüfen und
unveränderte Board-/Tisch-/Kameramontage sicherstellen. Eine neue Boardlage
erfordert eine getrennte Hand-Auge-Sitzung. Native Sicherheitsebenen bleiben
wirksam; ihre Lage ist derzeit nicht automatisch in MoveIt importiert.

`resume-series` erzeugt ausschließlich einen **neuen Plan** aus aktuellen
Stellungen zu den noch fehlenden Originalzielen. Vorhandene Bilder werden
nicht überschrieben; abgeschlossene Aufnahmen müssen ein gültiges Präfix
bilden. IDs, Fit-/Validierungsrollen und Ursprungsplan bleiben nachvollziehbar.

```bash
ros2 run uwa_cell_control handeye_hardware resume-series \
  setup/calibration/hardware_handeye/right_rear_20261110/batch_plan/batch.json \
  --session setup/calibration/hardware_handeye/right_rear_20261110 \
  --output setup/calibration/hardware_handeye/right_rear_20261111/resume_plan
ros2 run uwa_cell_control park_arm preview \
  setup/calibration/hardware_handeye/right_rear_20261111/resume_plan/plan.json
```

Danach `run-series <neues-batch.json> --session <ursprüngliche-Sitzung>` zunächst
mit `--check-only` verwenden. Erst nach Prüfung des neuen Weges ausführen.
Originalbatch und Rohbilder erhalten; keine automatische Schutzstoppquittierung.

## Größere Reihe mit breiterer Bildabdeckung

Für den vom Nutzer akzeptierten Front-Vergleich sind **62 Aufnahmen** vorgesehen:
`sample_000` als Fit-Ansicht plus61 geplante zusätzliche Ansichten, davon12
bereits vor der Aufnahme als Prüfung markiert. So entstehen50 Fit-/12 Prüfbilder.
Das Front-Profil wird separat aus seiner Kamera ermittelt; Rear-Intrinsics
werden nicht als Front-Kalibrierung übernommen.

```bash
ros2 run uwa_cell_control handeye_hardware plan-series --arm right_front \
  --count 61 --view-design wide \
  --output setup/calibration/hardware_handeye/right_front_20261111/batch_plan
```

Erst in einer wirklich erreichten, bildgeprüften Front-Aufnahmepose planen.
`wide` variiert zusätzlich die Boardposition im Bild, Abstand, Neigung und
Rollwinkel. FOV und optische Montage sind zunächst nur Planungsschätzungen;
real erkannte Ecken und konstante Optik werden bei jeder Aufnahme geprüft.
Standardplanung/Simulation bleiben unverändert; Standarddesign heißt `standard`.
Der Hardwarepfad erlaubt jetzt30…79 Zusatzansichten (31…80 inklusive erster
Aufnahme), die Hardware-Ergebnisvalidierung bis80 insgesamt. Pixel-/Pose-
Gütegrenzen und unabhängige Prüfung bleiben unverändert. Die Simulation hat
weiterhin ihre bisherige30…50-Anzahlgrenze.

Abschlussstand2026-11-11: Rear-Parkweg56,5s nach konkreter
Nutzerfreigabe erfolgreich gefahren, Endfehler0,0000296rad. Front-Kameradienst
nach Benutzerupdate wieder erreichbar, reale Front-Gelenkstände/External Control
bestätigt. Neue Front-Erstansicht79s plus ganze62-Bilder-Folge als kollisions-
geprüfte Gesamtvorschau vom Nutzer freigegeben. Erstpose erfolgreich erreicht,
24 Ecken und fester manueller Fokus435 über fünf Bilder/Hardware-Readbacks
bestätigt. Nach Kabelunterbrechungen alle62 Bilder aufgenommen. Intrinsics
bestanden, Hand-Auge wegen0,652° Rotations-RMS über0,5° nicht freigegeben.
Der [vollständige Front-Befund und20/33/50-Vergleich](front_calibration_2026-11-11.md)
dokumentiert Ergebnisse, Grenzen und Datenpfade; kein Profil aktiviert.
Offline-Designreferenz
unter right_front_20261111/design_preview/ ist ausdrücklich **nicht ausführbar**,
da Rear-Park-/Front-Aufnahmezustand dort erst als mögliche Folge angenommen ist.

Nach Abschluss den vorab vereinbarten Teilmengenvergleich ohne Hardwarezugriff
ausführen (gespeicherte Profile/Rohdaten bleiben unverändert):

```bash
python3 -m uwa_cell_control.count_comparison \
  setup/calibration/hardware_handeye/right_front_20261111 \
  --counts 20,33,50 \
  --output setup/calibration/hardware_handeye/right_front_20261111/count_comparison
```

Die vier festgelegten Teilmengenauswahlen behalten dieselben zwölf Prüfbilder;
der volle50er-Fit wird einmal berechnet. Alle Resultate/Fehler werden berichtet,
kein bestes Subset wird als aktives Profil ausgewählt.

## Aufnahme und Auswertung

Original-JPEG, annotiertes Bild, metrische ChArUco-Ecken, Kamerazustand, aktuelle
Gelenke und `T_base_link_tool0` werden pro Ansicht gespeichert. Individuelle
UR-Werkskinematik beider rechter Arme wurde mit dem offiziellen Werkzeug rein
lesend ausgelesen und im Hardwareinventar referenziert; kein Treiberneustart und
keine Änderung des Simulationslayouts dafür. Dateien liegen lokal unter
`setup/calibration/hardware_first_view/ur_kinematics/`.

Die Aufnahme verlangt Stillstand und unterschiedliche decodierte Bildpayloads.
Das ist ein Nachweis aktualisierter Bilder, **keine garantierte Belichtungszeit**:
HTTP liefert keinen Sensorzeitstempel. Diese Grenze steht in jedem Datensatz.
Fokus/optische Geometrie und manuelle Aufnahmeparameter bleiben fest; gewöhnliche
automatische Weißabgleichänderungen werden protokolliert. Bewegte/veraltete
Gelenke, fehlende Bildaktualisierung, Fokuswechsel oder zu wenige Ecken führen
zu keiner akzeptierten Messung und keiner weiteren Fahrt.

Intrinsics: mindestens20 Fit- und6 Prüfaufnahmen, ausreichende Kippungen und
Brennweiten-Beobachtbarkeit; zu unsichere oder schlecht validierte Lösungen
werden verworfen. Danach bestehender bildbasierter Hand-Auge-Solver mit festen
realen Intrinsics und echter Flanschkinematik. Nominale optische Montage oder
Simulations-Ground-Truth fließen nicht in den Fit ein.

```bash
# Gespeicherte Daten erneut offline auswerten:
ros2 run uwa_cell_control handeye_hardware fit \
  setup/calibration/hardware_handeye/right_rear_20261110 --intrinsics-only
ros2 run uwa_cell_control handeye_hardware fit \
  setup/calibration/hardware_handeye/right_rear_20261110
```

Erst nach erfolgreichem Fit entstehen `intrinsics.json` und `handeye_result.json`, ohne
automatische Aktivierung in TF/Hardware/Simulation. Einarmig werden
`T_tool0_camera` und `T_base_link_board` geschätzt. Relative rechte Basis-/
Tischpose erfordert später die zweite Kamera gegen dasselbe feste Board.
Vorläufige Montage-/Tisch-/Werkzeuggeometrie und linke Nutzer-Home-Stellungen
bleiben Grenzen der Kollisionsprüfung, keine Genauigkeitsgarantie.

## Nachweise und aktueller Stand

- 31 gezielte Tests bestanden: `setup/logs/uwa-handeye-hardware-tests.log`.
  Intrinsikfreie Erkennung, synthetische K-Wiedergewinnung, unabhängige
  Validierung, Datensatz-/Fokus-/Bildwiederholungs- und Wegprüfungen enthalten.
- Erster Startaufruf setzte nach negativer Verbindungsprüfung fort; Shell-
  Fehlerbehandlung korrigiert. ROS-Standard-SIGINT zerstörte den Kontext vor
  Action-Cancel. Eigene einmalige Python-Signalbehandlung hält ihn bis zum
  Cancel/Deaktivieren am Leben und toleriert doppelte ros2-run-Signale.
  Tatsächlicher Prozessgruppen-SIGINT während Mock-Fahrt erfolgreich getestet,
  Controller inaktiv/Nachdrift0rad: `uwa-first-view-sigint-live.log` und
  `uwa-parking-mock-sigint.log` im selben Logverzeichnis.
- Erste reale Annäherung unterbrochen, als die Verbindung verspätet entstand.
  Arm bereits nahe am Ziel; exakte Sollpose nicht als erreicht behaupten
  (0,0331rad größte Abweichung). Anschließend Zustand kollisionsgeprüft und
  Rear-Controller ausdrücklich deaktiviert. Ruhige erreichte Pose anhand echter
  Bilder als brauchbare erste Aufnahmesicht übernommen.
- Zunächst17, nach freiem Sichtfeld24/24 ChArUco-Ecken. Erste akzeptierte
  Aufnahme mit drei verschiedenen Payloads und festem Fokus404:
  `setup/calibration/hardware_handeye/right_rear_20261110/records/sample_000.*`.
- Nutzer hat erste Pose und anschließend komplette40-Ansichten-Folge anhand
  RViz ausdrücklich freigegeben. Batch-Fingerprint
  `80efa418b687052cf63d3010c608c3b4a91b16cdf5f07e630b30d60b8b3f8773`,
  Gesamtprüfung `--check-only` erfolgreich. Reine Bewegungszeit366,1s;
  Lauf bei sample_009 wegen nativem SchutzstoppC400A0 abgebrochen.
- **Historisch pausiert auf Nutzerwunsch,2026-11-10; Fortsetzung am2026-11-11 beauftragt.** Nutzer bestätigt eine konfigurierte
  UR-Sicherheitsebene als Ursache und will diese morgen verschieben.9 gültige
  Bilder (sample_000…008), alle24 Ecken,8 Fit/1 Validierung. Noch keine
  validierten Intrinsics-/Hand-Auge-Ergebnisse. Keine automatische Quittierung,
  Sicherheitsänderung oder Rückfahrt; Rear-Bewegungscontroller inaktiv.
  Exakter Zustand in `paused_state.json`, Einstieg siehe HANDOVER.md.
  Morgen aktuelle Posen/Ebene prüfen und neu planen, alte Bilder erhalten.
  Der alte Batch wird nicht direkt wiederholt; `resume-series` plant die
  ausstehenden32 Ziele neu. Aktueller Vorbereitungsstand siehe HANDOVER.md.
