# Minimalbetrieb: realer Betriebswechsel und Funktionsprüfung

- Status: abgeschlossen, 24.11.2026, Australia/Perth; Hauptagent dieses Chats.
- Nutzer beauftragt ausdrücklich den realen Betriebswechsel und die
  Funktionsprüfung des gebauten Minimalbetriebs.
- Durchgeführte Dienständerungen ausschließlich auf N100: alten
  `uwa-hardware-motion.service` zuerst beenden, danach vier Treiber geordnet
  ersetzen; separaten C++-Schutzdienst ohne Watchdog/ExecStopPost starten.
  Der alte ExecStopPost sendet beim Beenden einmalig nativen Programm-STOP.
- Kandidat: `/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
  Dienstdefinitionen, Safety Log und Quellenbindung vor Änderung sichern.
- Vorbefund: alle vier URs RUNNING/Safety NORMAL, `ros.urp` STOPPED;
  alte Wächter aktiv. Reviewstore enthält Arbeitsbereichsfreigabe.
- Prüfung: zwei kleine, vorab vollständig geometrisch geprüfte gemeinsame
  Vierarm-Handgelenkfahrten, Software-Pause und ausdrückliches Resume unter
  Erhalt derselben Goals. Bestehende0,1rad/s-/0,2rad/s²-Planungsgrenzen.
  Keine Greiferaktionen, Kollisionen oder absichtlich erzeugten Datenfehler.
- Telemetrie dient ausschließlich dieser beauftragten Funktionsmessung;
  keine zusätzlichen Laufzeitwächter installieren.
- Bedienung: sichtbare Minimal-GUI und dauerhafte Launcherbindung; tatsächliche
  GUI-Klicks über vorhandene Accessibility-Schnittstelle bevorzugt.
- Nachweise: `setup/tasks/minimal-cutover-20261124/` im Workspace,
  auf N100 Kandidat `validation/`.

## Ergänzter Änderungsvorbehalt,24.11.2026

Nutzer verlangt vor jeder künftigen Änderung am Sicherheitsprogramm eine
ausdrückliche Genehmigung, sobald eine Verlangsamung oder allgemeine Performancekosten
möglich sind oder Funktionen ohne unmittelbaren Hardwareschutz ergänzt werden.
Auch schützende Änderungen mit möglichen Performancekosten sind eingeschlossen.
In Workspace-/Projekt-`AGENTS.md` und beiden Übergaben festgehalten;
Dokumentationspflege abgeschlossen, keine Codeänderung und keine Dienstneustarts.

## Übernahme und Endzustand

- 18:02AWST alten Dienst zuerst beendet, danach vier Treiber. Geprüftes
  Quellenmanifest vollständig korrekt; alte Unitdefinitionen und Profilbindung
  unter `n100-validation/cutover-backup/` gesichert. Keine Sperrdatei gelöscht.
- Alle vier Treiber mit `UWA_PROTECTION_BACKEND=minimal`, Kandidaten-Workspace
  und Kandidaten-Install gestartet. Zunächst beide JTCs inaktiv, einmalige
  explizite Pause schaltete alle Arme auf CollisionHold.
- **Start + ROS** über die sichtbare Original-GUI ausgeführt. Alle vier
  `ros.urp` anschließend PLAYING, Reverse-Verbindungen aktiv, Safety NORMAL.
- Persistenter N100-Dienst seit18:14:31AWST:
  `~/.config/systemd/user/uwa-minimal-protection.service`,
  Invocation `f440e62ec5724c279e6f029a5deb4231`, aktiviert für `default.target`,
  Linger=yes, Restart=no, kein ExecStopPost. Unveränderte Binärdatei/Modell
  gegenüber der bestandenen Fahrt. Kein Rechnerneustart als Test durchgeführt.
- Nach belegter Dienstbereitschaft im Leerlauf einmal ausdrücklich Resume
  angefordert. Endquittung: alle vier Controller bestätigt, factor1,
  action_active=false; vollständige Kollisionsdaten, keine Warnung/Kollision.
  Programme weiterhin PLAYING/ROS-ready, Arme an den Ausgangspositionen.
  Letzter separater passiver Snapshot: maximale Abweichung zur geplanten
  Ausgangspose0,00008369rad, keine Befehle gesendet.
- ROSmini-Startmenü und Safety-Log-Aktion dauerhaft auf dieselbe Runtime
  gebunden. Normale GUI ohne Testadapter wieder geöffnet. Keine Greiferaktion,
  keine Geschwindigkeits- oder native UR-Konfigurationsänderung.

## Reale Funktionsprüfung18:11AWST

- Aus dem neuen passiven RTDE-Snapshot vollständig offline vorbereitet:
  q6 LF−0,1, LR+0,1, RF+0,1, RR−0,1rad, danach exakt zurück. Je Gruppe
  1,875s nominell, Spitze0,1rad/s und0,164222rad/s² bei bestehender0,2-Grenze.
- Bestehender unabhängiger Fortschrittsnachweis über alle vier Arme:
  kleinste Abstandsuntergrenze203,41mm gegenüber40mm.110 zusätzliche
  C++-Zustands-/Fortschrittskombinationen auf beiden Rechnern kollisionsfrei.
  Hostabhängige Meshpfade mit bereits bewiesener kanonischer Modellbindung
  remappt; Gruppen/Trajektorien gegenüber ROSmini exakt unverändert.
- `physical-functional-02/result.json`: success=true. Vier ursprüngliche
  Action-UUIDs während Pause erhalten; alle Phasen eingefroren, factor0.
  Über1,03564s tatsächliche fortschreitende Messwerte größte Positionsspanne
  0,00028777rad. Ausdrückliches Resume setzte dieselben vier Ziele fort.
- Hinfahrt und unmittelbar anschließende zweite Aufgabe/Rückfahrt erfolgreich,
  acht reguläre Action-Ergebnisse erfolgreich, neue vier UUIDs nur für die
  zweite Aufgabe. Kein Reset und keine neue globale Freigabe dazwischen.
- Größte Rückkehrabweichung über24Armgelenke0,00007987rad. Native Skalierung
  bei allen Armen1,0. Greiferregister vorher/nachher identisch.
- Dashboard vor/nach der Fahrt: alle vier Programme PLAYING/ROS-ready.
  Keine false-Programmmeldung während der Aufzeichnung. Im ersten passiven
  Bool-Snapshot fehlt noch RR, weshalb das rohe Hilfsfeld
  `native_program_links_unchanged` null bleibt; dies nicht in true umschreiben.
- Stop/Resume über temporären Treiber für Qt-Mausereignisse im tatsächlich
  sichtbaren Produktionsfenster, belegt durch `gui-actions.jsonl` und Screenshots.
  Desktop-AT-SPI lieferte bei dieser Qt-Version keine Widgetkinder. Keine
  Backend-Serviceaufrufe als physische Desktopklicks ausgeben. Temporären
  Treiber nachher beendet und600er-Unixsocket entfernt; Desktop-Accessibility auf den
  vorgefundenen Wert zurückgesetzt.

## Prüfumfang und verbleibende Grenzen

- Erster Versuch `physical-functional-01` scheiterte vor ROS-Verbindung und
  vor sämtlichen Bewegungsbefehlen an einem relativen Xacro-Ausgabepfad.
  Zweiter Aufruf mit absolutem Pfad bestand. CLI-Auflösung dauerhaft korrigiert
  und durch eine reine Dateiregression abgedeckt.
- Die erste Leerlauf-Resume-Abfrage unmittelbar nach Installation traf auf
  die noch nicht verfügbare Service-Discovery; kein Befehl wurde gesendet.
  Nach Lesen des aktuellen Journals/Bereitschaft einmal ausdrücklich gesendet.
  Keine Stoppkaskade, keine native Programmunterbrechung daraus.
- Neun ergänzende Datei-/CLI-Prüfungen und zwölf Safety-Log-Prüfungen bestanden. Vorherige168Python- und
  sechs C++-/Viermanager-Prüfungen bleiben die Softwarebasis.
- Nachweis kleiner unbeladener Handgelenkpfade. Keine absichtlich reale
  Kollision oder Datenfehler, kein maximaler Bremsweg- oder Dauerlastnachweis.
  Keine zusätzlichen Laufzeitwächter aus der Testmessung übernehmen.
- Bei Kernneustart im pausierten Zustand bleibt der Controller lokal pausiert,
  der neue Kern rekonstruiert die alte globale Sitzung nicht. Bewusst erneut
  Pause anfordern, Quittungen prüfen und gegebenenfalls Resume bedienen;
  kein automatisches Resume installieren.

Abgeleitete Auswertung aus unveränderten Rohdateien:

| Arm | Größte gemessene Gelenkgeschwindigkeit | Beobachteter q6-Nachlauf ab erster Kern-Pausemeldung |
|---|---:|---:|
| left_front |0,103400rad/s|0,013741rad|
| left_rear |0,101971rad/s|0,012916rad|
| right_front |0,101851rad/s|0,012555rad|
| right_rear |0,101384rad/s|0,012502rad|

Die Nachlaufwinkel verwenden interpolierte Startmesswerte und enden vor Resume;
sie sind keine zugesicherte Bremsweggrenze. Erste Faktor-null-Quittungen nach
0,509–0,587s, Kernstatus aller vier nach0,654s. Kein exakter physikalischer
Stillstandszeitpunkt daraus ableiten. Nominell20Hz; gespeicherte native Intervalle
bis0,200s, im Pausenfenster bis0,100s, Recorder-Callback-Lücken bis ungefähr0,38s.
Das native Quellalter in gespeicherten Kernpaketen lag höchstens bei0,0521s;
keine Kollisionsdatenwarnung. Kleinster live modellierter Nachbarabstand215,681mm.
Details/Hashes: `n100-validation/physical-functional-02/derived-observation.json`.

## Zentrale Dateien

- `offline-current-four-arm/functional-test.json`, `functional-test-n100.json`:
  geprüfte identische Bewegungsgruppen mit Hostbindung.
- `n100-validation/physical-functional-02/{result.json,telemetry.jsonl}`:
  rohe reale Messung und Action-/Controllerdaten.
- `physical-functional-02.console.jsonl`, `gui-actions.jsonl`,
  `gui-snapshot-last.png`: tatsächlich ausgeführte Qt-Bedienaktionen/Anzeige.
- `n100-validation/final-{protection-status.json,power-status.jsonl,protection-unit.txt}`
  und `persistent-service-binding.txt`: permanenter operativer Endstand.
- `n100-validation/final-native-snapshot.json`: abschließende passive Positionen.
- `deployment-file-tests.log`:9/9 ergänzende Dateiprüfungen bestanden.
- `safety-log-tests.log`:12/12 Prüfungen bestanden. Die Protokollansicht bindet
  jetzt explizit den aktiven Kandidaten und liest `uwa-minimal-protection.service`;
  GUI-Pause/Resume bleibt im lokalen semantischen `gui.log`. Nur lesende
  Diagnose-/GUI-Dateien angepasst, kein neuer Monitor oder Kernwechsel.
- `final-safety-report.json`: gegen das reale N100-Journal geprüft; zwei
  explizite Software-Pausen und zwei Kernstarts, keine alte Wächterquelle als
  aktiven Minimaldienst ausgegeben. Die GUI sendet den aktuellen lokalen
  Kollektor lesend über stdin; kein Diagnostik-Overlay an der gebauten Runtime.
- Lokaler standardisierter Diagnoseexport mit106Dateien inklusive tatsächlichem
  GUI-Audit, Rohmessungen und dauerhaftem Endzustand:
  `setup/logs/uwa-control/exports/20261124_182352_3_dfb796a8_1795515832698227294.tar.gz`.
  SHA256 `2c8b7bb855b781b1a71c2841a125d495ba1b95065042712b5257fe047d40e30d`.
  Roh-Ergebnis im Archiv hashgleich geprüft, keine Exportwarnung.
  `latest-export.txt` zeigt auf diesen aktuellen Export; kein Upload.
