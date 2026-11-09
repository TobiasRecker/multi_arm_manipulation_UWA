# Punktewolke begrenzen und Scan-Roboter entfernen

- Agent/Aufgabe: Codex, `scan-cleanup` (dieser Gesprächsfaden).
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Auftrag: Scan auf 4 m Abstand zur Zellmitte begrenzen und die aufgenommenen
  Roboter entfernen, damit nur die simulierten Arme sichtbar bleiben.
- Bereiche: ausschließlich Scan-Filter/-Publisher, Scanblock der Layout-YAML,
  Scanvalidierung in `configuration.py`, eigene Scan-Tests sowie README/HANDOVER.
- Überschneidungen: ChArUco-Aufgabe arbeitet parallel an `configuration.py`,
  Layout und Dokumentation. Änderungen hier nur im Scanbereich, bestehende Diffs
  unmittelbar vor Edits prüfen; keine Board-/Werkzeug-/Roboterwerte verändern.
- Dienste: nur `uwa-cell-scan` neu geladen; keine Simulationsneustarts oder
  Roboterbewegungen. Simulations-/Benutzer-RViz-PIDs blieben unverändert.
- Vorgehen: Filter im Weltkoordinatensystem nach Scan-Ausrichtung; statische
  Scan-Roboter über überprüfte räumliche Masken entfernen, nicht über die
  aktuell beweglichen Modellposen. Original und Rohcache unverändert lassen.
- Ergebnis: 4-m-Kugelradius um die vier Basen, acht feste Welt-Masken für die
  aufgenommenen Arme/Basen; 200.000 → 154.458 Punkte. Original/Rohcache erhalten.
- Prüfung: 44 Offline-Tests bestanden; tatsächlicher Scanradius <=4 m, keine
  Punkte in den Masken, ein Publisher. RViz zeigt bereinigte Szene und Tische.
- Dauerhafte Beschreibung und Belege nach README/HANDOVER übertragen.
- Keine weiteren Neustarts oder Bewegungen geplant.
