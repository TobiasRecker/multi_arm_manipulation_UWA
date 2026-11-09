# Maßstabgetreue Druckvorlagen

- Agent/Aufgabe: Codex, `charuco-print`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Auftrag: exakt dieselben beiden ChArUco-Boards wie in der Simulation drucken.
- Umfang: PDF-Erzeuger und zwei PDFs unter `output/pdf/`, Druckanleitung,
  README/HANDOVER. Bestehende Simulations-/Scanänderungen erhalten.
- Maße: Muster 280 × 200 mm, mit Rand 320 × 240 mm. A3 jeweils eine Seite;
  A4 je Board zwei gekachelte Seiten mit Überlappung, ohne Maßstabsänderung.
- Prüfung: Seitenmaße und Vektorgeometrie prüfen, PDF-Seiten rendern,
  gerenderte Marker-IDs/Ecken erneut durch OpenCV erkennen.
- Ergebnis: beide PDFs erstellt, alle sechs Seiten visuell geprüft. A3 sowie
  digital zusammengesetztes A4 erkennen je alle 17 Marker und 24 ChArUco-Ecken.
  Prüfbericht `docs/charuco_print_validation_2026-11-09.json`; Druckanleitung
  in README und `docs/charuco_calibration.md`, Handover aktualisiert.
- Dienste: keine Neustarts, keine Roboterbewegungen.
