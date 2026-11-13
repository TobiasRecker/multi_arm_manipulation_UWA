# Vierarm-Kollisionswächter und PTP-Vergleich

- Status: **in Arbeit**, 2026-11-13, Hauptagent.
- Auftrag: unabhängiger 10-Hz-Kugelwächter, nur vier Nachbarpaare,
  verriegelter Paarstopp; RRTConnect und unabhängige zirkulare Felder offline
  planen und unter gleichen Bedingungen in Simulation vergleichen.
- Nutzerentscheidungen: Warten/zeitversetztes Fahren erlaubt, nur betroffenes
  Paar stoppen, zunächst PC-/ROS-Kommandos, Simulation zuerst, kein CDF in v1.
- Bereiche: neues Paket `uwa_cell_motion`, eigene Anleitung/Tests und
  AGENTS/HANDOVER. Lokale Scan-Diffs und reale Hardwarearbeit erhalten.
- Keine Hardwareaktionen. Gemeinsame Simulation vor Bewegungsprüfung auf
  Nutzung prüfen; eigene Testprozesse gezielt verwalten. Geplante Neustarts:
  zunächst keine vorhandenen Dienste; neuer Wächter erst nach Build/Test.
- Nachweise und Grenzen werden nach den tatsächlichen Prüfungen ergänzt.

## Zwischenstand

- Paket gebaut,32Offline-Tests PASS. Native RRT-Schrittweite0,15rad statt
  ungeeigneter automatischer Extent-Skalierung. Frühe Entwicklungsdaten erhalten.
- Live-Gazebo-Stoppcheckv2 PASS: Paarstopp mit unabhängiger Weiterfahrt,
  Topic-/Reaktivierungssperre, Mehrfachfehler, Zustandsverlust, Wächterausfall
  und verriegelte Wiederkehr.118ms Fehler→Stillstand,450ms Watchdog→Hold.
- Vergleichv2 mit300Versuchen abgeschlossen; Kreuzungskategorie bei strenger
  Nachprüfung unzureichend, deshalb neue explizit verifizierte Fälle vorbereiten.
  Drei kurze Replay-Bahnen PASS; weiterer Replay vor Fahrt wegen verriegelter
  Startbedingung nach Zeitfaktorwechsel abgebrochen, Zeitfaktor1 wiederhergestellt.
- Geplanter nächster Schritt: Ursachenhistorie/Startreihenfolge prüfen,
  Kreuzungsfälle und abschließende Vergleichs-/Replay-Nachweise vervollständigen.
