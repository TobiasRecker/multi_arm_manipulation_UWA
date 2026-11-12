# Native Aufnahme der vorderen rechten Wrist-Kamera per SSH untersuchen

- Status: **abgeschlossen – natives5MP-JPEG erhalten, Farbe noch offen**,2026-11-12.
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

- Nach SSH-Aktivierung legitime Anmeldung, keine Zugangsdaten gespeichert.
  DirektesV4L2 MJPG2592×1944 nachgewiesen. Nur Kamera-runit-Dienst kurz stoppen;
  ersteS_FMT EBUSY, zweiter Versuch mit begrenztem Freigabe-Retry erfolgreich.
- JPEG2592×1944/332800Bytes/5038848Pixel lokal decodiert/SHA256 bestätigt,
  ohneUpsampling. Capture-C setzt640×480 zurück, Visiondienst wieder aktiv.
- Früher automatischer Restore während Initialisierung fehlgeschlagen;
  anschließend alle Originalfelder im Normalzustand vom PC wiederhergestellt,
  forceRefreshvergleich vollständig identisch. AutoLED-Setter15 trotz angewandtem
  Wert als Firmwareverhalten dokumentiert. Finalevidenz final-restoration.json.
- Datei controller-artifacts/native-2592x1944.jpg hat sichtbaren Grünstich,
  unretuschiert erhalten. Farbe/robustes allgemeinesTool offen; keine Anwendung
  alterVGA-Intrinsics auf5MP. Keine Robotermotion/Programm-/Treiberänderungen.
- SSH beendet, kein temporäres Capture-Skript mehr aktiv. Bericht
  docs/wrist_native_photo_2026-11-12.md, README/HANDOVER aktualisiert.
