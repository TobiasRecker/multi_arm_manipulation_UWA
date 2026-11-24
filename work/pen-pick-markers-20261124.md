# Stiftaufnahme: Erkennung und Druckbogen

## OAK-Pro-Bildprüfung, 24.11.2026

- Status: Bildprüfung abgeschlossen. Nutzer hat zwei30mm-Marker am Stift angebracht:
  oben und auf der Seite senkrecht zu den beiden Greifflächen.
  Aktuelles natives OAK-Pro-Bild prüfen; IDs und Sichtbarkeit messen.
- Nur vorhandener N100-Kamerapfad, keine Roboteraktion und keine fremde
  Kamerasitzung beenden. Bestehende Schutz-/Druckarbeiten erhalten.
- Aktuelles natives Foto17:41AWST,4056×3040/Fokus112 mit dem vorhandenen
  N100-Einzelfotopfad aufgenommen. Geräte-ID18443010314F3B1300, Factoryhash
  unverändert, Kamera geschlossen und Lease freigegeben. Keine Roboterbefehle.
- Beide Marker auf Originalpixeln als DICT_4X4_100 erkannt: oben97, seitlich96.
  Kanten97:60,3/74,5/66,0/73,8px;96:41,8/75,0/42,5/75,3px.
  Beide IDs gehören jetzt zum Stift/Adapter, auch wenn97 im Druckbogen
  ursprünglich als Halter beschriftet war. Keine zusätzliche Halterreferenz.
- Rohfoto/Metadaten, native Ecken und180°-Anzeigedetail unter
  `setup/tasks/pen_pick_20261124/20261124-pen-markers-oakpro-01/`.
  Einzelbild-Sichtbarkeit belegt; metrische Pose, Marker-zu-Greifpose und
  Robustheit bei anderen Blickrichtungen/Verdeckung noch offen.

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
