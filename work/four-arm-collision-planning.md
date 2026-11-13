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

- Paket gebaut,45Offline-Tests PASS (vor neuer Paarlease-Prüfung). Native RRT-Schrittweite0,15rad statt
  ungeeigneter automatischer Extent-Skalierung. Frühe Entwicklungsdaten erhalten.
- Live-Gazebo-Stoppcheckv2 PASS: Paarstopp mit unabhängiger Weiterfahrt,
  Topic-/Reaktivierungssperre, Mehrfachfehler, Zustandsverlust, Wächterausfall
  und verriegelte Wiederkehr.118ms Fehler→Stillstand,450ms Watchdog→Hold.
- Vergleichv4 mit300Versuchen abgeschlossen; fünf neue Nachbarfälle mit
  nachgewiesener Kugelbahnüberschneidung, tatsächlichen Meshkontakt separat
  gespeichert. RRT102/125 gültige Zielversuche erfolgreich,CF115/125;
  je25absichtlich ungültige Ziele abgewiesen. Eingefrorene Suite im Paket.
- Gazebo-Replay der55verschiedenen erfolgreichen zeitparametrierten Bahnen
  läuft, identische Wiederholungen mit gemeinsamem Ausführungsnachweis verlinkt.
  Vollständige Einzelarmbahn mit gemessenem geometrischem Korridor statt
  unnötiger Rest-zu-Rest-Mikrophasen; Mehrarmbarrieren unverändert konservativ.
  SIGTERM-Cleanup mit tatsächlicher Bewegung/Persistenz der Halteverriegelung
  geprüft: setup/logs/uwa-motion-signal-check.json. Kein automatischer Reset.
- Beschleunigungsversuch5ms/RTF3 wegen STATE STALE vor Fahrt abgebrochen;
  Original1ms/RTF1 und Sim-Kameraraten10Hz wiederhergestellt. Weitere Fahrten
  unter normalen Einstellungen, für Replay temporär Kameraraten0,2Hz mit Trap.
- Auditkorrektur: näherungsabhängige Paarlease im unabhängigen Supervisor;
  letzter Abstand darf nicht unbesehen400ms Wächterausfall überbrücken.
  Hashgebundenes Protokollv2, Monotonzeit/Transportalter und20ms Pollreserve.
  Abschluss-Livetest/Build und endgültige Auswertung noch offen.
