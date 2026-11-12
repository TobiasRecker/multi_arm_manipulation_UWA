# Globales Kalibrierprofil und OAK-Boardprüfung

- Status: **abgeschlossen**,2026-11-12,Hauptagent.
- Auftrag: bestandene linkeRear-Kalibrierung global aktivieren, dann natives
  OAK8K-Foto aufnehmen und rechte/linke/mobileChArUco-Boards prüfen.
- Versioniertes neuesBündel; gültige bestehendeRechtsparameter erhalten,
  fehlgeschlageneFront-HD-/VGA-Extrinsics nicht aktivieren. NominaleWeltanker
  erhalten. Keine Hardwarefahrt, Power/Brake/Play oder Hardwaretreiberneustarts.
- Bereiche: description/config/calibration,Standardlayout,gezielteTests,
  Dokumentation/AGENTS/HANDOVER; OAK-Snapshot/Detektion lokal untersetup/.
- ExklusivenOAK-Zugriff prüfen; nur eigenenLive-Dienst ggf.kurz pausieren und
  wiederherstellen. Keine Simulation dafür stoppen. Rohfotos nicht insGit.
- Prüfung: Hashes/Transformationen/K-D im gemeinsamen Modell,Consumer-/MoveIt-
  Regression,Build; echte8000×6000Dimensionen und drei getrennterBoard-ID-Sätze.

- Ergebnis: hardware_20261112_v1 validiert/global installiert; siebenTests PASS,
  LinkeOptik/K-D/Boardframe konsistent, Welt-/Gehäuse unverändert. AlteProfile
  und fremdeFront-HD-Diagnose erhalten; keine Hardwarebefehle oderNeustarts.
- Echtes8000×6000Foto+Bericht+Annotation lokal; dreiBoards je17Marker/24Ecken
  vollständig erkannt. Keine OAK-Extrinsics geschätzt, Gerät wieder geschlossen.
- AGENTS/HANDOVER/README/applied_calibrations sowieOAK-HANDOVER gepflegt.
