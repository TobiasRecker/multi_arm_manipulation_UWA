# ChArUco-Boards und erste Posenprüfung

- Agent/Aufgabe: Codex, `charuco-first-step`
- Status: **abgeschlossen**
- Aktualisiert: 2026-11-09 11:25 AWST (Australia/Perth)
- Auftrag: Board je Tischmitte, alle Kameras initial darauf richten,
  OpenCV-Boardpose und Vergleich mit Simulations-Ground-Truth; Dokumentation pflegen.
- Bereiche: neue ChArUco-/Kinematik-/Prüfmodule und Tests; Board-Xacro;
  `cell_layout.yaml` nur Boardeinstellungen und Roboter-Anfangsstellungen;
  `configuration.py`, Launch, Setup/Abhängigkeiten; README/AGENTS/HANDOVER/THIRD_PARTY.
- Vorbestehender fremder Diff: `cell_layout.yaml` enthält eine grobe Scanregistrierung.
  Diesen Scanblock erhalten; seine Kalibrierung ist kein Teil dieser Aufgabe.
- Gemeinsame Ressource: UWA-Simulationsdienst für Boardgeometrie/Anfangsstellungen
  neu gestartet; Liveversuch abgeschlossen. **Keine weiteren Neustarts oder
  Bewegungen geplant.** RViz wieder geöffnet, Scan-Publisher erhalten.
- Zwischenstand: Boardtexturen/Frames, bildbasierte PnP-Schätzung, erster
  Tisch-/Relativbasisvergleich und IK-Helfer implementiert. Vier Zielansichten
  in die zentralen Anfangsstellungen übernommen. Beide Pakete gebaut;
  **33 Offline-Tests bestanden**, inklusive perspektivischer Bilderkennung.
- Live-Ergebnis: vier Kameras erkennen je 24 Ecken, zehn Bilder pro Kamera;
  relative Basisfehler pro Tisch ca. 1,9 mm / 0,17°. Alle neun Controller aktiv,
  tatsächliche Zellwurzel stabil. Mesh-Normalenfehler aus erstem Liveversuch behoben.
- Abschluss: finale Roh-/Erkennungsbilder und Bericht unter
  `setup/logs/uwa-charuco-final/`, datierte Zusammenfassung unter
  `docs/charuco_validation_2026-11-09.json`. Anleitung, README, AGENTS,
  HANDOVER und Drittquellen aktualisiert. 33 Offline-Tests bestanden.
  Fremde aktive Aufgabe `scan-cleanup` gesehen; ihre Filter/Scanparameter erhalten.
- Offen als Folgearbeit: mehrere Kalibrierstellungen und Schätzung unbekannter
  Hand-Auge-Transformationen; in diesem Auftrag nicht als erledigt behauptet.
