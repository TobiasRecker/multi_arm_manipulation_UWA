# Automatische Hand-Auge-Kalibrierung

- Agent/Aufgabe: Codex, `handeye-automatic`.
- Status: **aktiv**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Auftrag: genehmigten Plan für Messfahrten, echte Hand-Auge-Schätzung,
  relative Basen, Qt-GUI, überwachten Stopp und explizite Profilübernahme umsetzen.
- Bereiche: neue Pakete `uwa_cell_calibration` / `uwa_cell_calibration_msgs`,
  kleine abwärtskompatible Erweiterung der ChArUco-Erkennung, Controller-
  Abbremsparameter, Tests und Dokumentation. Bestehende Diffs erhalten.
- Defaults: Simulation Domain 64; 40 Stellungen/Arm, 32 Fit + 8 Validierung;
  ein bewegter Arm; 0,10 rad/s und 0,20 rad/s²; kalibrierter TF-Baum getrennt.
- Dienste: für Controller-Konfiguration ggf. einmal UWA-Zelle neu starten;
  anschließend gezielte Messfahrten und Stopptests, keine Hardware.
- Nächster Schritt: Kalibrierkern, Schnittstellen und MoveIt-Planungsworker aufbauen.
