# Stiftaufnahme: Erkennung und Druckbogen

- Status: erste Etappe abgeschlossen, 24.11.2026 (Australia/Perth), Hauptagent.
- Nutzerziel: Stift aus dem gemeinsam entworfenen Halter als weiteres
  Teilprogramm der Program library greifen. Erste Etappe: markerlose
  Erkennung einschätzen und bei sinnvoller Markernutzung einen mehrfach
  belegten A4-Druckbogen erstellen.
- Bereiche: `hardware/marker_tool/`, `scripts/print_pen_markers.py`,
  `output/pdf/`, AGENTS.md/HANDOVER.md. Bestehende Motion-Diffs erhalten.
- Keine Dienstneustarts, Kameraübernahme, Fahr- oder Greiferaktion geplant.
- Vorläufige Empfehlung: plane, starre ArUco-Montage am Adapter; eigener
  Marker am Halter optional. Aktuelle Bildsichtbarkeit und reale metrische
  Greifgenauigkeit noch nicht geprüft. PDF-Decodierung offline prüfen.
- Ergebnis: einseitiges A4-PDF mit26Markern, vier Größen und IDs92–99,
  4mm Weißrand, Schnittmarken, 50mm Kontrollstrecke und Druckanleitung.
  Visuell geprüft; alle26Marker aus dem fertigen300dpi-Render im Gesamtblatt
  und einzeln korrekt decodiert. Nachweis und Metadaten neben dem PDF.
- Anleitung und Übergabe aktualisiert. Keine Dienste oder Hardware verändert.
  Ausführbares Library-Teilprogramm und reale Montage-/Bildprüfung bleiben
  nächste Etappen; keine fertige Stiftaufnahme behaupten.
