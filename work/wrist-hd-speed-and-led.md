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

- Stand18:28: RF-LED-Dienst aktiv, gemeinsamer Guardian
  `uwa-wrist-led-policy.service` installiert/aktiviert. LF/RR-HDs nach deren
  abgeschlossenen Reihen gezielt neu geladen, LED-Enrollment läuft. LR bleibt
  für `left-rear-hd-intrinsics` vollständig ausgenommen (eigene eingefrorene
  Ressourcen); keine Beleuchtungsänderung mitten in dessen Messdatensatz.
- Firmwarebefund: `lightingMode` ist zwischen Setter und forceRefresh nicht
  identisch. Manueller Setter2 wird als1 zurückgemeldet, bei Intensität0 und53.
  Deshalb expliziter manueller Nutzungswert (Standard30%=53/175), erfolgreiche
  Setterantwort UND tatsächliche Intensität erforderlich; übrige Felder streng.
  Getter1 als Setter1 zurückspielen schaltet aus/zerstört den Wert: separater
  Managed-Restore-Shim, ursprünglicher gemeinsamer Kamera-Worker unverändert.
- Vergleich mit identischer30%-Beleuchtung: bisher18,2206s, schnell15,2709s
  (−16,19%). Je24Ecken und Laplacewerte32,67–32,98 bzw32,79–33,06.
  Frühe erfolglose LED-/Restoreversuche bleiben als Diagnose archiviert;
  Kamera danach Normal/Fokus435/60000µs/LED0 bestätigt. Keine Armfahrt.
