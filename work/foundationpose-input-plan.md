# Fehlende Eingaben für reale FoundationPose-Versuche

- Status: **abgeschlossen – Bestandsprüfung und Empfehlung dokumentiert**,
  2026-11-16 (Australia/Perth), Hauptagent.
- Auftrag: vorhandene Informationen und sinnvollsten Beschaffungsweg erklären;
  derzeit Konzept/Bestandsprüfung, keine Freigabe einer Aufnahme oder Implementierung.
- Bereiche: gezielter Ergänzungsabschnitt docs/foundationpose_titanpc.md und
  HANDOVER.md. Bestehende Diffs/aktive UR-Vorbereitung/Greifarbeit erhalten.
- Keine Kamera-/UR-/GPU-Abfragen, keine Dienstneustarts oder Installation.
- Quellen: vorhandene OAK-/Asset-Dokumentation, Luxonis ImageAlign/Sync/
  Depth-Align-Beispiel und offizieller FoundationPose-Demoeinstieg.
- Empfehlung: vorhandene K/Meshes übernehmen und prüfen; feste OAK mit
  entzerrtem, ausgerichtetem, zeitgeprüftem RGB-D-Paket, manuelle Initialmaske.
  Erst statischer Replay, dann aufgezeichnete Bewegung, WLAN-Livepfad und
  separate Basisregistrierung. Vorschlag klar von umgesetzten Nachweisen trennen.
