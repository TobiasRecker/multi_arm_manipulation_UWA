# Reale erste Aufnahmepose und Hand-Auge-Messreihe

- Status: **pausiert auf ausdrücklichen Nutzerwunsch** (2026-11-10;
  Fortsetzung voraussichtlich2026-11-11 nach seiner Sicherheitsebenen-Anpassung).
- Datum: 2026-11-10, Australia/Perth.
- Nutzer möchte nach erfolgreichem Front-Parken right_rear in erste Bildpose
  bewegen und anschließend die entwickelte Hand-Auge-Routine real erproben.
- Zunächst echte Zustände/Bild und vorhandene Intrinsics/Frische des HTTP-
  Bildpfads prüfen. Rechte Front-Parkpose erhalten, linke Arme laut Nutzer
  nominell Home, kein anderer Arm wird bewegt.
- Bereiche: getrennte Hardware-Aufnahme/Planung in uwa_cell_control mit
  Wiederverwendung von MoveIt-Modell, MATCH-Ausführung und bildbasiertem Solver.
  Bestehenden Simulationsbackend nicht auf Domain66 umbiegen. Neue Profile/
  echte Messdaten nicht als Simulationsergebnisse aktivieren.
- Vorläufige optische Montagen nur für Design/Planung verwenden. Keine
  nominellen Simulations-Intrinsics als reale Kalibrierung behandeln.
- Dienste: zunächst keine Neustarts, kein Power/Brake/Play. Konkrete Pose/Weg
  vorbereiten und prüfen; vorhandene Hardwaretreiber/GUIs erhalten.
- Nutzer bestätigt A3/1:1/100mm, Board etwa wie Modell; keine bekannten Intrinsics.
  URCap-Herstellerkalibrierung und eigene ChArUco-Route erklärt. UR-Werkskinematik
  beider rechter Arme rein lesend geholt, Inventar darauf referenziert.
- Erste Annäherung nach Freigabe unterbrochen: Shell lief nach negativer Link-
  Prüfung weiter, standardmäßiger rclpy-SIGINT machte Cleanup-Kontext ungültig.
  Rear ausdrücklich deaktiviert; spätere Zustände zeigen fast vollständigen
  freigegebenen Weg. Ruhige Pose bei0,0331rad Restfehler übernommen, FCL-Check gut.
  Signalfehler korrigiert und echtes ros2-run-Prozessgruppen-SIGINT im Mock
  bestanden (Cancel/Deaktivieren/Nachdrift0). Kein Power/Brake/Play durch Agenten.
- Erste echte Beobachtung gespeichert:24/24 Ecken, Fokus404/Manual erhalten,
  drei aktualisierte Payloads, echte Gelenke/Flanschpose.31 gezielte Tests gut.
- Nach separater RViz-Freigabe läuft nun40-Ansichten-Folge nur right_rear,
  native Verbindungs-/Telemetrie-/Kollisions-/Bild-/Fokusprüfungen je Schritt.
  Datensatz unter setup/calibration/hardware_handeye/right_rear_20261110/;
  Logs uwa-handeye-hardware-run.log. Ergebnisse/Handover nach Lauf ergänzen.
- Lauf unterbrochen bei Bewegung zu sample_009 durch nativen SchutzstoppC400A0.
  sample_000 bis sample_008 erhalten:9 akzeptierte Bilder, alle24/24 Ecken,
  davon8 Fit/1 Validierung. Kein fertiges Intrinsics-/Hand-Auge-Ergebnis.
  Native Action wurde gecancelt und Rear-Bewegungscontroller deaktiviert;
  kein automatisches Quittieren, kein Rückweg, keine Sicherheitsparameter geändert.
- Nutzer bestätigt Ursache: konfigurierte Sicherheitsebene im UR, die er
  aktuell nicht deaktivieren kann; er will sie morgen verschieben. Ausdrücklich
  heute nicht weiterfahren. Stand unter paused_state.json im Datensatz sichern.
- Morgen nach neuer Nutzeranweisung aktuelle Zustände/Fokus/Boardlage und
  native Ebenenkonfiguration prüfen, Restwege neu planen. Alten Batch nicht
  direkt erneut starten: bestehende Bilder würden absichtlich abgewiesen;
  Fortsetzung mit frischer Sitzung oder explizit geprüfter Wiederaufnahme.
