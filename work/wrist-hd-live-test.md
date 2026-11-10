# Einmaliger HD-Kameratest

- Status: **abgeschlossen** (Versuch; HD-Foto nicht erhalten).
- Datum: 2026-11-10, Australia/Perth.
- Nutzer gibt Kamerazeitfenster frei; anderer Agent arbeitet laut Nutzer an
  Bahnplanung. Auftrag: eingegrenzten HD-Modul-/Pufferpfad praktisch prüfen.
- Umfang ausschließlich right_rear-Kamera: Einstellungen sichern, eigenes
  Kamerafenster gezielt pausieren, Zustände prüfen, HD-Ausgabe/Pixelmaße messen,
  Einstellungen in finally wiederherstellen; keine Roboterbewegung oder Treiber-
  /Programm-/Bahnplanungsänderung. Vorhandene fremde Diffs erhalten.
- Bereiche: eigener Kamera-Testhelfer, Tests/Befunddokumentation; Rohbilder und
  Reports unter setup/calibration/wrist_hd. Kein URCap-Update/SSH erforderlich.
- Ergebnis: temporäres Barcode-Modul akzeptiert, process49156 fehlgeschlagen,
  Lizenz true. Lesende Nachprüfung nurVGA-Anzeigequelle; ohne bestätigtenHD-Puffer
  kein erneuter nativer Export. Ursache nicht abschließend geklärt.
- Restore in beiden Sitzungen erfolgreich, Werte404/Manual,60000µs/Manual,
  Gain16,LED53Manual. Kein Dienstausfall, keine Robotermotion. Kamerafenster
  wieder geöffnet, Livebild bestätigt. Drei lokale Fehlertests bestanden;
  docs/wrist_hd_probe_2026-11-10.md und README/HANDOVER aktualisiert.
