# Vierarm-Kollisionswächter und PTP-Vergleich

- Status: **wieder in Arbeit nach Nutzerfreigabe**, 2026-11-13, Hauptagent.
  Neustart abgeschlossen; Nutzer hat Fortsetzung ausdrücklich beauftragt.
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
- Fortsetzung nach Neustart: keine Gazebo-/motion-Dienste aktiv. Eigene
  Zellsimulation64/uwa_cell_sim neu starten, zuerst ergänzten Paarlease-Test
  abnehmen, danach die27offenen Replay-Bahnen. Andere Arbeitsaufträge erhalten.
- Fortsetzungsprüfung PASS: vollständiger Live-Stoppcheck einschließlich
  knapper Paarlease, Datei `setup/logs/uwa-motion-live-guard-check-complete.json`.
  Fehler→Stillstand182ms, knappe Paarlease→Paarhold127ms, gesamter
  Wächterverlust→Vierarmhold281ms. Topic-/Aktivierungssperre, Mehrfachfehler,
  Zustandsverlust, verriegelte Wiederkehr und unabhängiger Teilreset PASS.
  Normaler motion-Dienst danach gestartet; Replay setzt28vorhandene Erfolge fort.
-29.Bahn bestätigt, anschließend Vorbereitung wegen numerischer Greifer-
  Nullstellung(-7e-14rad) abgewiesen: nativer Prüfer nutzte0 statt gemeinsamer
  1e-8rad Grenztoleranz. Angeglichen; Regression akzeptiert -1e-13, verwirft
  echte Überschreitung -1e-5. Fehlversuch/Diagnose erhalten. Offline-Suite hat
  exakte nominelle Greiferwerte; deren Abfragegeometrie wird nicht geändert.
- Stillstand-CLI an dieselben unabhängigen Antriebe wie Wächter/Hold angeglichen;
  passive Gazebo-Mimic-Geschwindigkeitsgeräusche hatten die Bestätigung trotz
  aktiver Holds unnötig verhindert. Fehlende/ungültige Antriebsdaten bleiben
  gesperrt, Meldung lautet ausdrücklich measured drive standstill.
-31Bahnen bestätigt. Folgende Vorbereitung durch Paarlease bei CPU-bedingt
  langsamer Simulationszeit vorsorglich gestoppt; Rohversuch in
  development-before-wall-timer/ erhalten. Korrektur Protokollv3: Geometrie-
  timer mit10Hz monotoner Echtzeit statt Simulationszeit, passend zu Leases
  und Stoppbudget. Keine Grenz-/Timeoutlockerung. Pausequellen werden weiter
  geprüft und als STATE STALE verriegelt. Gezielter Pause-Livetest ergänzt;
  anschließend normaler Replay mit denselben Modellen/Abfragen fortsetzen.
- Protokollv3 abgenommen: geprüfte Grundstellungsfahrt PASS, danach kompletter
  Livecheck in `setup/logs/uwa-motion-live-guard-check-steady-wall.json` PASS.
  Prüfung läuft bei pausierter Quelle weiter und verriegelt STATE STALE.
  Beobachtete Latenzen63ms Abstandsfault→Stillstand,132ms knappe Paarlease,
  321ms Wächterverlust→Hold; einzelne Beobachtungen, keine garantierte Obergrenze.
  Ressourcen-/Topic-Sperre, unabhängige Weiterfahrt und Teilreset weiterhin PASS.
  Replay nach explizitem Reset fortgesetzt;53automatische Prüfungen bestanden.
- Startsequenz korrigiert: Steuer-/Resetservices erst nach Controller-
  Vorbereitung anbieten; frühe Reset-Callbacks dürfen nicht im provisorischen
  SingleThread-Spin der Parameterabfrage laufen. CLI-Reset wartet auf frische
  Guard-/Supervisor-Meldungen, ohne vollständige Armzustände zu fordern
  (Teilreset bleibt möglich). Unmittelbarer Start/Reset/Replay erneut geprüft.

## Zwischenstand

- Neustart-Checkpoint: **28/55** verschiedene erfolgreiche Planbahnen in
  Gazebo bestätigt,27noch offen. Offlinevergleich300/300 fertig. Zustand und
  Fortsetzungsdaten: `setup/logs/uwa-motion-reboot-checkpoint.json`, aktueller
  Gelenkschnappschuss `setup/logs/uwa-motion-paused-before-reboot.json`.
- Letzter Lauf stoppte vor Zielbewegung in blocked_direct_03: vorangehend
  bewegter Hindernisarm war noch nicht vollständig eingeschwungen. Rohversuch
  in `executions/development-before-obstacle-settling/` erhalten. Executor
  wartet jetzt vor dem Start auf100ms gemessene Ruhe(≤0,003rad/s), danach
  vollständigen Start erneut gegen2mrad prüfen. Laufende Überwachung bleibt
  strikt; auch nicht kommandierte Greifertriebe eingeschlossen. Kein Auto-Reset.
- Alle vier Resource-Holds/Stillstand vor Pause bestätigt; eigener
  `uwa-cell-motion`-Dienst kontrolliert gestoppt. Gazebo1ms/RTF1 bestätigt,
  Kamera-Originalraten restauriert. Keine eigene Fahrt mehr aktiv.
- Nach Nutzerfortsetzung Simulation64/uwa_cell_sim und motion.sh starten,
  frische Zustände/Modellgleichheit prüfen, dann bewusster Reset und Replay
  fortsetzen. Nach Neustart keine ungeprüfte Wiederherstellung der alten Pose;
  Replay fährt eigene Starts durch geprüfte Vorbereitung an. Der ergänzte
  knappe Paarlease-Livetest und die Endauswertung stehen noch aus.

- Paket gebaut,50Offline-Tests PASS (CTest53 einschließlich3Wrapper), auch
  letzte Übergangs-/Greiferkorrekturen installiert. Native RRT-Schrittweite0,15rad statt
  ungeeigneter automatischer Extent-Skalierung. Frühe Entwicklungsdaten erhalten.
- Live-Gazebo-Stoppcheck mit Protokollv2 PASS: Paarstopp mit unabhängiger Weiterfahrt,
  Topic-/Reaktivierungssperre, Mehrfachfehler, Zustandsverlust, Wächterausfall
  und verriegelte Wiederkehr.125ms Fehler→Stillstand,419ms Watchdog→Hold.
  Teilreset/WeiterfahrtRR bei fehlendemLF-Zustand ebenfalls PASS.
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
  Protokollv2-Livetest PASS, gezielter besonders knapper Lease-Test ergänzt;
  endgültige Auswertung und Vollständigkeit der Gazebo-Ausführung noch offen.
