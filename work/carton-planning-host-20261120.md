# Kartonprogramm auf ROSmini planen

- Status abgeschlossen, 20.11.2026, 13:12 AWST. Zuständig ist der Agent für den
  Weblauf und dessen Bahnübergabe.
- Nutzerentscheidung: N100 ist der Steuerhost für die UR-Treiber,
  Regelung, Ausführung und den Live-Schutz. ROSmini übernimmt OAK-Auswertung,
  Bahnplanung und Offline-Prüfung. Größere Aufgaben bei Bedarf auf titanpc.
  Das statische Rezept darf versionsgebunden wiederverwendet werden.
- Bereiche: Webrunner, Rezeptcache, Transport der geprüften Bündel,
  Kartonrunner und Dokumentation. Native Messung zuerst, Zustand auf
  ROSmini auswerten und nur bei gültigem Start Foto und Planung aufrufen.
- Offline nachgewiesen: ROSmini 6,738 s gegen N100 44,804 s für dasselbe
  12:47-Foto. Alle 19 Versuchsergebnisse gleich. Warmes Rezept 0,465 s.
  Zwei kartonbezogene Bahnphasen und Transport mit Archivdaten geprüft.
- Archivprüfung erfolgreich. Der Webworker bestimmte die Pose aus dem Bild, prüfte
  beide Bahnen und stellte die 57 Übergabedateien mit kaltem Cache in
  27,95 s bereit. Der N100 akzeptierte das geprüfte Modell, den exakten
  Prüferstand und beide parallelen Bahnphasen auch mit externem Rezeptcache.
  Lesender Vorlauf aus der realen Zelle meldete drei Arme im Zustand
  `POWER_OFF` und endete am Zustandsabschnitt.
- Empfänger mit Sicherung auf dem N100 installiert, Standalone-Webserver
  auf ROSmini aktualisiert. Dauerhafter Stand und Nachweise in [HANDOVER](../HANDOVER.md).
  Die reale End-to-End-Fahrt bleibt offen.
