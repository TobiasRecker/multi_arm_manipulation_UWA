# Automatische Hand-Auge-Kalibrierung

- Agent/Aufgabe: Codex, `handeye-automatic`.
- Status: **abgeschlossen**.
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
  Scan erhalten, RViz für die Tests vorübergehend gestoppt und wiederhergestellt.
  Nur Domain 64, keine Hardware.
- Nachweise: **57 Offline-Tests bestanden**; vollständiger 40×4-Lauf bestanden,
  je 32 Fit + acht Validierung. Kamerafehler maximal 0,131 mm / 0,035°,
  relative Basisfehler maximal 0,640 mm / 0,054°. Datierter Bericht unter
  `docs/handeye_validation_2026-11-09.json`.
- Echte GUI-Stopp-/Freeze-/Weltpausentests, Pause/Fortsetzen, getrennte TF-Bäume,
  Rückkehrstellungen, unveränderte Ground Truth und Profilrückfall geprüft.
  Profil beim erneuten Start automatisch geladen; zehn Ergebniszeilen und
  vier Livebilder geprüft. GUI für den Nutzer geöffnet.
- Gefundene Fehler: flüchtige Geschwindigkeitswerte bei stationären Gazebo-Gelenken;
  Stillstand nun über alle angetriebenen Gelenke in einem stabilen Fenster prüfen.
  Aufnahmefehler getrennt von Bewegungs-/Telemetriefehlern behandeln.
- Übergabe: README, AGENTS, HANDOVER und `docs/automatic_handeye.md` aktualisiert.
  Rohdaten und Profile bleiben unter Workspace `setup/calibration/` außerhalb Git.
  Keine weiteren Bewegungen oder Dienstneustarts durch diese Aufgabe geplant.
- Für spätere Szenenerweiterungen: MoveIt prüft die Zell-URDF plus Boden.
  Separat gespawnte Gazebo-Entitäten sind dort nicht automatisch Hindernisse;
  deren Kollisionskörper bei Bedarf explizit in die PlanningScene übernehmen.
