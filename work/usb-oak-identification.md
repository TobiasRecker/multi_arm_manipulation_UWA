# Zusatzkamera per USB identifizieren

- Agent/Aufgabe: Codex OAK-Gespräch, `usb-oak-identification`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Auftrag: unbeschriftete, gerade angeschlossene Kamera identifizieren.
- Ergebnis: EEPROM `OAK-D Pro AF`, SDK `OAK-D-PRO-AF`, RVC2; IMX378 AF und
  zwei OV9282. Keine OAK-D-S2-FF für dieses konkrete Gerät bestätigt.
- Bereiche: ausschließlich Inventarangaben in AGENTS/HANDOVER/README/Overview-
  Anleitung korrigieren. Keine Simulation, Modelle, Kameraposen oder Arme ändern.
- Parallel: `handeye-diagonal` aktiv; dessen Dateien und Dienste erhalten.
- EEPROM-/Sensordaten lokal in `setup/oak4/usb-identification/`, USB-Zugriff
  mittels gezielter udev-Regel eingerichtet. Gerät wieder geschlossen,
  keine Flash-/Reset-/Kalibrieränderung. Inventar/Anleitung korrigiert.
