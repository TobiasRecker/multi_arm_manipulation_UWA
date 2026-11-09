# Statische OAK4-Übersichtskamera

- Agent/Aufgabe: Codex in OAK-Gespräch, `oak-overview`.
- Status: **aktiv**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Auftrag: OAK4-D rechts neben den Tischen auf einstellbarem Stativ in Gazebo;
  beide Tische/Roboter überblicken, ChArUco-Details sichtbar halten. Pose noch offen.
- Bereiche: neuer Layoutblock `overview_camera`, neue Kamera-/Stativ-/Analyse-
  Module und Tests, additive Launch-/Setup-Integration; README/AGENTS/HANDOVER.
  Wrist-/Hand-Eye-Implementierung und deren bestehende Diffs bleiben erhalten.
- Parallel aktiv: `handeye-automatic`; keine Simulation neu starten, keine Arme
  bewegen. Kamera als separate statische Gazebo-Entität und eigene TFs hinzufügen;
  Änderungen ihrer Pose dürfen später ohne Zellneustart möglich sein.
- Nächste Schritte: Sichtfeld/Pixelauflösung planen, neue Kamera bauen, Bilder
  und ChArUco-Erkennung prüfen. Nur eigene Kameraentität/Dienste steuern.
