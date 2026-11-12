# Gemessene Kalibrierungen gemeinsam verwenden

- Status: **abgeschlossen**,2026-11-11, Hauptagent.
- Auftrag: bestimmte Posen/Kalibrierungen dauerhaft sichern und in Simulation,
  Visualisierung und Kollisionsprüfung verwenden. Kein neuer Bewegungsauftrag.
- Befund: Rear-Hand-Auge und beide rechten Intrinsics PASS; Front-Hand-Auge
  FAIL(0,652° >0,5°). Drei individuelle Werkskinematiken vorhanden. Keine
  vermessene Welt-/Tischverankerung und keine OAK-Extrinsics vorhanden.
- Bereiche: versioniertes installiertes Profil mit Quellen/Hashes, gemeinsamer
  Modellpfad für Simulation/Hardwareplanung/Overlay, Tests und Dokumentation.
  Nominalmodell als Rückfall erhalten; keine unbestätigten Basenverschiebungen.
- Keine Hardwaretreiber-/GUI-Neustarts, keine Power/Brake/Play/Ziele. Bestehende
  Simulation zuerst prüfen; keine laufenden Gelenkstellungen zurücksetzen.
- Prüfung: Profilvalidierung/Hashes/abgelehnte Front-Extrinsics, TF-/FK-
  Konsistenz zwischen Verbrauchern, MoveIt-Modell/Kollisionen, Build.
- Ergebnis: versioniertes installiertes Bündel hardware_20261111_v1,
  gemeinsamer Loader in uwa_cell_description, Standardlayout als Profilreferenz
  auf unveränderte Nominalgeometrie. Gültige Teilparameter angewendet, keine
  ungeprüften Front-Extrinsics/Weltanker übernommen. Vier benannte Gelenk-
  Referenzposen gespeichert; tatsächliche Park-Snapshots plus alte Ziele erhalten.
- Fünf Pakete gebaut,99 Offline-/MoveIt-Tests; reale gespeicherte FK beider
  rechter Arme exakt reproduziert. Live-Gazebo: neun aktive Controller,
  endliche Gelenke, laufende Uhr, zwei640×480-Streams mit passenden K/D und
  Rear-TF. Backend IDLE ohne altes Idealprofil, alle vier Kameras24 Ecken.
- Eigene Testsimulation/Backend wieder beendet, andere Dienste erhalten;
  keine Hardwarebefehle. Normaler nächster App-Start verwendet das Profil.
- Dokumentation docs/applied_calibrations.md, Prüfbericht
  docs/calibration_integration_validation_2026-11-11.json und HANDOVER/AGENTS
  aktualisiert. J-PARSE-Online-Kollisionsoption weiterhin aus, volle absolute
  Zell-/OAK-/Basis-/Tischkalibrierung weiterhin offen.
- Aufnahmeplanung ebenfalls angebunden: validierte K/D/Fokus als Planungsmodell,
  Projektion mit Verzeichnung, nomineller Rückfall ohne Profil. Neue Fits
  bekommen weiterhin ausschließlich ihre eigenen echten Bildbeobachtungen.
