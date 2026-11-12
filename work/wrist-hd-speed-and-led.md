# HD-Aufnahmezeit und nutzungsabhängige Wrist-LEDs

- Status: **in Arbeit**, 2026-11-12, Hauptagent dieses Gesprächs.
- Nutzerauftrag: HD-Fotoworkflow auf Beschleunigung ohne nennenswerte
  Qualitätseinbußen prüfen/testen; LEDs aller vier Wristkameras ausschließlich
  während Fotoaufnahme oder Videonutzung einschalten.
- Parallel aktiv: RR-HD-Messreihe und LF-HD-Fortsetzung. Deren eingefrorenen
  Kamerapfad und Beleuchtungsprofile während Messreihen nicht ändern. Eigene
  Kameratests zunächst nur right_front/left_rear nach frischer Prozessprüfung.
- Bereiche: Wrist-HTTP-/HD-Client, Kamera-Worker, Vorschau-/Capture-Einbindung,
  gezielte Tests und Dokumentation. Keine Kalibrierprofile/Armfahrten.
- Zunächst Zeitanteile messen, vollständigen Restore und native Bildqualität
  erhalten. Installation/Neustarts nur eigener Kameradienste im Leerlauf;
  keine Roboter-/Simulations-/Treiberneustarts.

- Live-Befund 18:07: RR-Serie abgeschlossen, LF-Fortsetzung wird parallel
  gestartet. Zusätzlich erweitert ein anderer Agent `board_capture.py` und
  `board_capture_gui.py` auf fünf Kameras. Eigene kleine LED-Context-Ergänzungen
  dort erhalten; keine Umstrukturierung dieser Dateien.
- Isolierter Speedtest RF: redundante native VGA-Rückschaltung weggelassen,
  stattdessen tatsächlich vom Visiondienst gesetztes VGA anschließend geprüft.
  Erster Versuch 12,31s statt 15,58s im direkt vorigen Originaldurchlauf.
  Noch kein Default und keine Änderung eingefrorener LF-Workerressourcen.
