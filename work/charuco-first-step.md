# ChArUco-Boards und erste Posenprüfung

- Agent/Aufgabe: Codex, `charuco-first-step`
- Status: **aktiv**
- Aktualisiert: 2026-11-09, Australia/Perth
- Auftrag: Board je Tischmitte, alle Kameras initial darauf richten,
  OpenCV-Boardpose und Vergleich mit Simulations-Ground-Truth; Dokumentation pflegen.
- Bereiche: neue ChArUco-/Kinematik-/Prüfmodule und Tests; Board-Xacro;
  `cell_layout.yaml` nur Boardeinstellungen und Roboter-Anfangsstellungen;
  `configuration.py`, Launch, Setup/Abhängigkeiten; README/AGENTS/HANDOVER/THIRD_PARTY.
- Vorbestehender fremder Diff: `cell_layout.yaml` enthält eine grobe Scanregistrierung.
  Diesen Scanblock erhalten; seine Kalibrierung ist kein Teil dieser Aufgabe.
- Gemeinsame Ressource: UWA-Simulationsdienst wird nach Build/Offlineprüfung
  für neue Boardgeometrie und Anfangsstellungen neu gestartet. Keine Hardware.
- Zwischenstand: Boardtexturen/Frames, bildbasierte PnP-Schätzung, erster
  Tisch-/Relativbasisvergleich und IK-Helfer implementiert. Vier Zielansichten
  in die zentralen Anfangsstellungen übernommen. Beide Pakete gebaut;
  **33 Offline-Tests bestanden**, inklusive perspektivischer Bilderkennung.
- Nächster Schritt: jetzt Live-Neustart und Prüfung aller vier Gazebo-Bilder.
  RViz vor dem Uhrenreset kurz schließen und anschließend wiederherstellen;
  separaten Scan-Publisher und seine Registrierung erhalten.
