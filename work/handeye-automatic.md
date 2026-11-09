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
- Implementiert: zwei ROS-Pakete, Park + robuste Bildeckenverfeinerung,
  getrennte Validierung, MoveIt-Kollisionsszene mit vier Gruppen, zeitparametrierte
  Messwege, Qt6-GUI, Action/Services, unabhängiger Watchdog und versionierte Modelle.
- Dienste: UWA-Simulation einmal für die Abbremsparameter neu gestartet;
  Scan erhalten, RViz für die Tests vorübergehend gestoppt und danach wiederherstellen.
  Nur Domain 64, keine Hardware.
- Nachweise: 51 Offline-Tests bestanden; CLI-Stopp, Clientverlust und Pause/Fortsetzen
  in der laufenden Simulation geprüft. Live-GUI mit vier Bildern geprüft.
- Gefundene Fehler: flüchtige Geschwindigkeitswerte bei stationären Gazebo-Gelenken;
  Stillstand nun über alle angetriebenen Gelenke in einem stabilen Fenster prüfen.
  Aufnahmefehler getrennt von Bewegungs-/Telemetriefehlern behandeln.
- Nächster Schritt: vollständiger Lauf 40 × vier, echte GUI-Stopp-/Freeze-Tests,
  Profil-/TF-Prüfung, Prüfergebnisse und Anleitung vervollständigen.
