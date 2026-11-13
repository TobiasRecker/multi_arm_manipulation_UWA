# HD-Aufnahmezeit und nutzungsabhängige Wrist-LEDs

- Status: **abgeschlossen; LR-Rollout seit12.11. COMPLETE, alle vier Kameras verwaltet**, 2026-11-12, Hauptagent dieses Gesprächs.
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

- Abschlussprüfung: Paketgebaut,45gezielte TestsPASS; ein Python-Fork-Warnhinweis
  im isolierten Crash-Test, keine fehlgeschlagenen Prüfungen. Reale zwei Viewer /
  ersterCrashweiteran / letzterCrashLED0 bestanden. Echte Qt-Vorschau samt
  LED-Knopfdruck und normalem Schließen bestanden; Intensität0, Fokus435/60000
  unverändert. Screenshot/JSON im Diagnoseverzeichnis. GUI jetzt --arm für alle
  vier IDs, keine irreführende feste Right-Rear-Beschriftung bei anderer Kamera.
- Echte bestehende ROS-HD-Dienste LF/RR bestanden (13,57s/24,39s), jeweils
  single-switch-VGA-/1/15s-Nachweis, vollständigerRestore und nachAntwortLED0.
  CB3-Vergleich legacy16,522s/fast13,714s (−17,00%). Ursprünglicher Helper bleibt
  vorhanden; 32-Bit-Fasthelfer separat, keine gcc-Installation auf Robotern.
- LR-Reihe läuft weiterhin unverändert, zuletzt33/41 inFahrt. Automatischer
  Rollout in setup/wrist_lighting/pending/left_rear.json wartet auf Besitzer-
  Abschlussstatus und freienNativeLock. PhaseCOMPLETE wird erst nach altem
  Kameradienststopp, neuem Kameradienststart und bestätigtem LED0 geschrieben.
  Keine weiteren Eingaben erforderlich; keine Arm-/Treiber-/Programmkommandos.
- Andere aktuelle Arbeit: Offline-Analyse `object-scan-swept-volumes` durch
  Digitalisierungsagenten; keine dessen Scanwege/Controller verändert.
- Doku docs/wrist_speed_led_2026-11-12.md, README/AGENTS/HANDOVER aktualisiert.

- Nachprüfung13.11.: Guardianaktiv, alleNutzungssperrenfrei undalle4LEDs im
  realenReadback0 (vor/nachAus-Befehl). KeineaktiveKameranutzung, keineArmaktion.
  NeuerNachweis setup/wrist_lighting/idle_check_20261113/verified_off.json.
