# Wrist Camera: native Auflösung und Belichtung

- Status: **abgeschlossen** (Versuche und Helligkeitssteuerung; native Auflösung offen).
- Datum: 2026-11-10, Australia/Perth.
- Nutzer bestätigt Fokusfenster; wünscht Foto in voller Auflösung sowie
  Helligkeits-/Belichtungssteuerung. Ausschließlich Kamera right_rear.
- Umfang: bestehendes UCC-Archiv statisch weiter untersuchen; aktuelle Fokus- und
  Kameraeinstellungen sichern. Auflösung lesend prüfen, begrenzte Kameratests
  durchführen und Bedienfenster erweitern. Benutzerfokus erhalten.
- Bereiche: Kamera-HTTP-Client/Qt-Fenster und zugehörige Tests/Anleitungen.
  Daten unter Workspace setup; keine Robotermotion, Controller-/Simulationsneustarts.
- Parallel aktive hardware-parking-Arbeit berücksichtigen; deren Dateien erhalten.
- Ergebnis: reale Belichtungs-/Gain-/LED-Steuerung und UI implementiert, sechs
  lokale Tests, Build und echte Qt-Knöpfe/Speichern/Restore bestanden. Fokus404/
  Manual im abschließenden Helligkeitstest erhalten. Geprüftes Fenster geöffnet.
- Vollauflösungsversuche: Kamera-OperationMode/capture quittiert, Exportpfad
  führt zu kurzem automatisch behobenem Dienstausfall, alternativer Pfad bleibt
  VGA. Moduswechsel setzt Fokus zurück; Benutzerfokus danach wiederhergestellt.
  Keine HD-Funktion freigegeben, keine Roboter-/Treiber-/Firmwareänderungen.
- Bericht/Bedienung docs/wrist_resolution_exposure_2026-11-10.md,
  Nachweise setup/calibration/wrist_resolution_exposure/20261110/ und
  setup/logs/uwa-wrist-appearance-window/. Gemeinsame Doku laufend aktualisiert.
