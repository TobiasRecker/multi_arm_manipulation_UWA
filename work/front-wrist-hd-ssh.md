# Native Aufnahme der vorderen rechten Wrist-Kamera per SSH untersuchen

- Status: **in Arbeit**,2026-11-12.
- Nutzer nennt neuesten Kamera-URCap-Stand und ermöglicht vorübergehenden
  legitimen SSH-Zugang zu right_front192.168.8.103. Kennwort wird weder hier
  noch in Quellcode/Logs gespeichert. Ziel: tatsächliches natives Vollbild,
  keine hochskalierte Vorschau.
- Zunächst nur lesende HTTP-/SSH-Diagnose: tatsächliche Version, Kamerazustand,
  USB/UVC-Modi, aktive Kameraprozesse/Aufnahmetools. Vor Kameramodusänderungen
  Fokus/Belichtung/LED sichern, anschließend ausdrücklich wiederherstellen.
- Keine Robotermotion, Dashboard-Programm-/Power-/Brake-/Resetbefehle und keine
  Treiber-/Simulationsneustarts. Andere aktive left-rear-Kalibrierarbeit erhalten.
- Bereiche: eigene Testdaten unter setup/calibration/wrist_hd/right_front_20261112/,
  eigene Anleitung/Prüfscripte, gezielte README/HANDOVER-Aktualisierung.
- Lesebefund: UCC4.1.0.164735/CQ0-1.4.0 tatsächlich aktiv, HTTP640×480,
  Fokus435Manual/60000µsManual/Gain16/AutoLED0 vollständig gesichert. Keine
  bisherigen Parameteränderungen. SSH22 Connection refused, Kennwort nicht
  verwendet; Aktivierung durch Nutzer am Pendant erfragt. Neue HTTP-API und
  Kameraliste/SettingsDetails lokal gesichert, keine freie HD-Option gefunden.
