# Übernommene Kalibrierungen und Referenzposen

Stand2026-11-11. Der Nutzer hat die Speicherung und gemeinsame Verwendung der
ermittelten Posen/Kalibrierungen ausdrücklich beauftragt. Profil:
[`hardware_20261111_v1`](../uwa_cell_description/config/calibration/hardware_20261111_v1/profile.json).
Es wird mit `uwa_cell_description` installiert und enthält SHA256-Referenzen
auf unveränderte Ergebniskopien und individuelle UR-Kinematikdateien. Die
Rohbilder und ursprünglichen Sitzungsergebnisse unter `setup/calibration/`
bleiben erhalten. Deren historisches `activated:false` wird nicht umgeschrieben;
die spätere Übernahme ist durch dieses separate Profil dokumentiert.

| Teil | Übernommen | Grenze |
|---|---|---|
| Werkskinematik | left_rear, right_front, right_rear | links vorne noch nominal |
| Intrinsics K/D | right_rear640×480, Fokus404 manuell | Bildränder nicht unabhängig geprüft |
| Intrinsics K/D | right_front640×480, Fokus435 manuell | gilt für unveränderten Bildmodus/Fokus |
| Hand-Auge tool0→optical | right_rear | interne unabhängige Prüfung bestanden; keine absolute Genauigkeitszusage |
| Basis→Board-Relation | right_rear, als eigener Referenzframe | kein vermessener Welt-/Tischanker |
| Park-/erste Aufnahmeposen | beide rechten Arme, benannte Gelenkreferenzen | neu planen, nicht als Live-Zustand verwenden |
| Front-Hand-Auge | archiviert, **nicht angewendet** | Rotations-RMS0,652° überschreitet0,5° |
| Welt-/Tisch-/Basisrelation, OAK-Extrinsics | weiterhin nicht kalibriert | keine Messwerte erfinden |

## Verwendung

`load_layout()` verwendet jetzt standardmäßig
[`cell_layout_calibrated.yaml`](../uwa_cell_description/config/cell_layout_calibrated.yaml).
Diese Datei verweist auf die zentrale geometrische `cell_layout.yaml` und das
Messprofil; Tischmaße/Posen werden nicht dupliziert. Ein eigener Layoutpfad ist
weiterhin möglich. Für den vorherigen nominellen Simulator explizit
`layout:=…/uwa_cell_description/config/cell_layout.yaml` übergeben.

- **Gazebo und sein RViz-Modell:** individuelle Gelenkkinematik, validierte
  Kamera-K/D und Rear-Optikpose. Der Gazebo-Sensor und der optische URDF-Frame
  bekommen dieselbe Transformation. Kamera-/Greifergehäuse bleiben angenäherte
  Körper; ein optischer Fit vermisst deren Kollisionsgeometrie nicht.
- **Hardwareplanung/Parken/Kalibrierwege:** gleicher Modellgenerator und gleiche
  Werkskinematiken in der vollständigen MoveIt-Szene. Abweichende Kinematiken
  zwischen Inventar und aktivem Messprofil werden gemeldet. Neue Modellstände
  erfordern neue geprüfte Wege; alte Pläne nicht bearbeiten, um sie passend zu machen.
  Neue Aufnahmereihen verwenden vorhandene validierte K/D für die Zielprojektion
  inklusive Verzeichnung statt nominellem FOV. Die erforderliche Fokusposition
  wird mitgespeichert. Diese Planungswerte sind keine Beobachtungen für den Fit;
  eine erneute Intrinsics-Schätzung bleibt unabhängig und verwendet neue Bilder.
- **Gemessener RViz-Overlay:** gleiche UR-FK, Rear-Optik und gemessener Boardframe
  mit `real_`-Präfix. Nur Hardware-JointStates werden gelesen; keine Kommandobrücke.
- **Reale UR-Treiber/Jogging:** Inventar verweist auf dieselben archivierten
  Werksdateien. Die Bytes sind identisch zu den bereits verwendeten Dateien;
  laufende Treiber wurden nicht neu gestartet. Kein Power/Brake/Play/Fahrziel.
  Die bestehende J-PARSE-Laufzeit-Kollisionsoption bleibt deaktiviert: ein
  verbessertes MoveIt-Modell aktiviert keinen vollständigen Online-Zellenschutz.
- **Bildauswertung:** je Kamera exportierte `*_camera_info.yaml` mit K/D/R/P
  und gespeichertes Fokus-/Bildgrößenprofil. Keine Kameraeinstellung wird beim
  Laden geschrieben. Modus/Fokus und physische Kamera müssen zum Profil passen.
- **Simulations-Kalibrierbackend:** zusätzliche Fits je Messprofil unter
  `setup/calibration/profiles/measured_<Profilhash>/`; frühere ideale Simulator-
  Profile unter `profiles/active.json` bleiben für das Nominalmodell erhalten.

Normaler App-Start und neue Planaufrufe verwenden das Profil automatisch.
Bei bereits laufender Simulation wäre ein Neustart zur Änderung des physischen
Gazebo-Modells nötig; nicht während laufender Bewegungen durchführen. Diese
Übernahme hat keine reale Fahrt ausgelöst. Tisch-/Basisposen, initiale Gelenkziele,
OAK-Designpose, Scanregistrierung und Boardgröße wurden nicht aus dem Fit geändert.

## Posen wiederfinden

[`named_poses.json`](../uwa_cell_description/config/calibration/hardware_20261111_v1/named_poses.json)
enthält `right_front_park`, `right_rear_park`, `right_front_first_capture` und
`right_rear_first_capture`, jeweils mit sechs eindeutig benannten Gelenken in
Radiant, Quelle/Hash und Herkunft als früheres Ziel oder gemessener Snapshot.
Kein Eintrag wird automatisch zu einer Startstellung oder einer Fahrfreigabe.
Die Matrizen `T_base_board` und `T_tool0_camera` stehen im Rear-Ergebnisarchiv;
sie beziehen sich auf `base_link`, `tool0` und den OpenCV-Board-/Optikframe.

## Prüfung

Fünf Pakete gebaut.99 Offlineprüfungen umfassen
unveränderte Weltanker/Gehäuse, Hashfehler, abgelehnte Front-Extrinsics, Bildmodus,
Snapshots sowie konsistente FK in Simulation/MoveIt/Overlay und einen vollständig
kollisionsgeprüften Parkweg. Live-Gazebo: neun aktive Controller, fortschreitende
Zeit, endliche Gelenke, beide rechten640×480-Bilder, tatsächlich publizierte
K/D passend zum Profil und korrekte Rear-Optiktransformation. Nachweise:
`setup/logs/uwa-calibration-integration-{build,tests}.log` und
`setup/logs/uwa-calibration-integration-live.json`.

Die SDF-Kameraelemente folgen der
[offiziellen SDFormat-Kameraspezifikation](https://github.com/gazebosim/sdformat/blob/sdf16/sdf/1.12/camera.sdf).
Der Live-Vergleich prüft K/D und Frames, keine unabhängige Pixelverzeichnungsmessung
oder absolute Hardware-Zellgenauigkeit.

Der [zusammengefasste Prüfbericht](calibration_integration_validation_2026-11-11.json)
enthält die Livewerte und den Vergleich mit den gespeicherten realen FK-Matrizen
(sample000 beider rechter Arme: identisch). Der Backendstart blieb IDLE ohne
automatische Fahrt/Altprofilaktivierung. Die eigene Headless-Testsimulation und
der eigene Backend wurden nach der Prüfung beendet; der nächste normale App-
Start lädt das Messprofil mit den üblichen Oberflächen.
