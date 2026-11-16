# Vierarm-Kollisionswächter und PTP-Vergleich

- Status: **abgeschlossen – Simulation implementiert und ausgewertet**, 2026-11-13.
- Nutzerauftrag umgesetzt: unabhängiger10-Hz-Nachbarwächter, verriegelter Paarstopp,
  gemeinsame PTP-Schnittstelle, RRTConnect und unabhängiger CF-Feldplaner,
  reproduzierbarer Vergleich. Hardware ist eine separate Ausbaustufe.
- Ausschließlich ROS2 Lyrical, Domain64, Partition `uwa_cell_sim`, LOCALHOST.
  Keine Hardwarekommandos; fremde Greif-/Tracking-/Digitalisierungsarbeiten erhalten.
  Nutzer-Neustartpause erledigt; spätere Fortsetzung ausdrücklich erlaubt.

## Ergebnisse

- Offline300/300:30Aufgaben×5Seeds×2Methoden,10s Querybudget. RRT102/125 gültige
  Zielversuche, CF115/125 erfolgreich; je25absichtlich ungültige Ziele abgewiesen.
  Insgesamt pro Methode150Versuche; sämtliche Fehlschläge bleiben im Datensatz.
  Nachbar-Kreuzungen3/25gegen15/25. Aussage nur für die eingefrorene Suite.
- Agentenempfehlung: freie PTPs vorläufig mit Feldansatz wegen höherer Erfolgs-
  quote, RRT als Referenz. Keine Nutzerfestlegung/keine allgemeine Rangfolge.
- Alle217erfolgreichen Offline-Pläne durch55verschiedene vollständige Start-/
  zeitparametrierte Bahnen in Gazebo repräsentiert; identische Wiederholungen
  ausdrücklich verlinkt. **Alle55Zielbahnen begonnen,53erfolgreich,2gestoppt**.
  Verlinkte Fahrten: RRT100/102, CF115/115 erfolgreich.
- Zwei tatsächliche RRT-Ausführungsfehler in Kreuzung03 bleiben kanonisch:
  Seed0: Greifer0,05835rad/s über Betriebsgrenze0,05rad/s;
  Seed1:152ms Zustandsverarbeitungslücke, betroffene Arme verriegelt.
  Erste Cleanup-Bestätigung fehlte bei Seed1, erneuter expliziter Stopp bestätigte
  alle vier Ressourcen und gemessene Ruhe; Post-Review im Originaldatensatz.
- Frühere Anfahrabbrüche, Entwicklungsstände und Unterbrechungen vollständig
  erhalten. Bericht inventarisiert118Versuche/18Fehlschläge über unterschiedliche
  Entwicklungsbedingungen; diese nicht als homogene neue Testserie ausgeben.
- Hauptnachweise unter `setup/logs/uwa-motion-comparison-v4/`:
  `report.html`, `report.png`, `report.attempts.json`, `summary.json`,
  `runtime-manifest.json`, `validation-audit.json`, vollständige Einzelresultate.
  Audit: eine Kollisionssignatur/ein Mesh-Satz, geplantes vmax0,05rad/s,
  amax0,09976rad/s², maximaler aufgezeichneter erfolgreicher Endfehler0,461mrad.
- Abgeschlossene Artefakte/Bedienung: Paket `uwa_cell_motion`,
  `docs/four_arm_motion.md`, README-Verweis, AGENTS-Regeln und HANDOVER-Ergebnis.

## Implementierung und Abnahme

- Konservative Vollkörperhüllen für68modellierte Körper/216Kugeln, einschließlich
  offener Greiferfinger, Wrist und Kameras. AABB-Scheiben decken Volumen ab;
  Oberflächenabstände und Bewegungshebel sämtlicher betroffener Glieder.
- Vier Paarungen LF/RF, LF/LR, RF/RR, LR/RR. Geometrie10Hz monotone Wanduhr,
  unabhängiger Supervisor50Hz, Paarleases/Heartbeat und persistierende
  Ressourcen-Haltecontroller. Mehrfachfehler vereinigen betroffene Arme;
  Datenverlust sperrt Nachbarschaften. Teilreset unabhängiger Arme möglich.
  Topic-Kommandos/erneute Aktivierung erfasst, kein automatischer Wiederanlauf.
- Gemeinsame vollständige Startzustände und deterministische Zielauflösung,
  kartesisch explizites `world`-Frame. Native OMPL-RRTConnect und unabhängige
  CF-Rollouts ohne RRT-Fallback, gemeinsame Direktweg-/Wartekoordination.
  MoveIt/FCL-Endprüfung nach Quintik-Timing; diskrete Prüfung≤5mrad, kein CCD.
  Einzelarm-Geometriekorridor, Mehrarmphasen mit gemessenen Barrieren und
  Restwegprüfung gegen gestoppte/bremsende Arme.
- Unbeanspruchte Greifertriebe an gemessener Pose halten, vorhandene Besitzer
  nicht verdrängen. Stillstand der unabhängigen Antriebe prüfen, passive
  Mimic-Solvergeräusche nicht als Antriebsbewegung ausgeben. Fehlende/NaN-Daten
  sperren. Offene Anschläge: gemessen bis5,1µrad Positionszittern; Werkzeugruhe
  ≤10µrad Span/300ms und Betriebsgeschwindigkeitsgrenze, Armruhe3mrad/s.
  Echte langsame Bewegung besteht Gegenprobe nicht. Alte5-mrad/s-Zwischenregel
  überholt; keine Lockerung von Frische/Kollision/Betriebsgeschwindigkeit.
- **66Motion-Pytests PASS,70mit4CTest-Wrappern**; zusätzlich36gezielte Gazebo-
  Modell-/Overview-Tests PASS. Explizite QoS-Callbacks, Clock und Nachrichten-
  empfang trotz entfernter unbenutzter Standard-Warncallbacks geprüft.
- Finale vollständige Liveabnahme PASS:
  `setup/logs/uwa-motion-live-guard-check-executor-acceptance.json`.
  0,04756rad/s vor Fault;85ms bis erste Armspeed≤3mrad/s,129ms knappe Paarlease,
  400ms Wächterverlust bis Ressourcenhalt. STOPPED verlangt zusätzlich300ms
  gemessene Historie. Paarumfang/unabhängige Weiterfahrt, Mehrfachfehler,
  Topic-/Aktivierungssperre, Datenverlust/Teilreset, Pause/STATE STALE,
  Wächterausfall und verriegelte Wiederkehr PASS. Einzelbeobachtungen,
  keine garantierten Worst-Case-/Hardwarewerte.
- Gegenseitige Ausfalldiagnose und separate RViz-Verlustmarker löschen alte
  Kugeln. Ressourcenbesitz nicht als Stillstand ausgeben. Stoppadapterverlust
  bei bereits gehaltenen Armen geprüft, keine aktive Ausfall-Stoppgarantie.
  RViz-Bilder `uwa-motion-rviz-held-final.png` / `uwa-motion-rviz-guard-lost.png`
  geprüft. Kompakte Zeilen umgehen überbreite Leerzeichen. Verlust-Snapshot-
  helfer stürzte erst nach gespeichertem Bild beim Beenden ab; Guard fortgesetzt.
- Profiling:9,66→4,16Mio Aufrufe/6s nach Weglassen unbenutzter rclpy-QoS-
  Warnwaitables; reale Wächter-CPU46→42Prozent eines Kerns. Transport-QoS,
  explizite Callbacks, Frische/Watchdogs unverändert. Kein Nachweis, dass alle
  nichtdeterministischen Zustandslücken verschwunden sind. Quellenrevisionen
  samt Prüfungen im Laufzeitmanifest, frühere Rohdaten nicht überschrieben.

## Endzustand und Grenzen

- Vergleichsdienst beendet, keine Fahrt mehr aktiv. `uwa-cell-sim` und
  `uwa-cell-motion` laufen; vier Ressourcen gehalten, stabile Antriebe gemessen.
  Checkpoint `setup/logs/uwa-motion-final-checkpoint.json`, alter Neustart-
  Checkpoint verweist auf Abschluss. Keine automatische Weiterfahrt.
- Einheitlicher Fahrmodus ohne Bildrendering (`image_sensors:=false`), Kamera-/
  Werkzeugkörper, Inertien, Kinematik/TF und OAK-CAD erhalten. Kollisionssignatur
  cdeff888…461504 und Mesh-Hashes identisch; normale Zellvorgabe Bilder an.
- Vorläufige Welt-/Tischanker, visual-only OAK-Stativ/Karton und nicht modellierte
  Anbauten bleiben Grenzen. Reale Stoppreserve, produktive Greiferregelung und
  Hardwareanbindung sind nicht durch diesen Simulationsvergleich abgenommen.
