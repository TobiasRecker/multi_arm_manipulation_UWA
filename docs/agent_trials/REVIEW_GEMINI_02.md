# Auswertung des zweiten Agententests

19.11.2026. Der protokollierte Lauf mit Gemini 4 Neon (High) hat den
22-mm-Kreis auf allen drei geforderten Flächen im Kinematikmodell erzeugt.
Alle 24 Gelenke kehren in die Ausgangsstellung zurück, der linke hintere
Arm bleibt geparkt. Die gespeicherte maximale Geschwindigkeit beträgt
0,096583 rad/s bei der vereinbarten Grenze von 0,1 rad/s.

[Bericht und Artefakte](../../../../setup/agent_trials/box_gemini_20261119/session-50t0fawy/trial/report.md) ·
[Entwicklungszeiten](../../../../setup/agent_trials/box_gemini_20261119/session-50t0fawy/trial/summary.md) ·
[Audit](../../../../setup/agent_trials/box_gemini_20261119/session-50t0fawy/trial/artifacts/run01/independent-audit.json)

## Was der Trace belegt

- Der aufgezeichnete Befehl `plan-run01` ruft die vorhandene Offline-CLI
  mit der gebundenen Modellquelle, der verlangten Flächenfolge und
  `--radius-mm 22` auf. Laufzeit 82,086 s. Die Rohdaten zeigen die
  Fortschrittsmeldungen, zwei neue Vorschauen, die verworfene direkte
  180°-Route, die Prüfung des Umwegs und das abschließende Ergebnis.
  Die Suche hat den bekannten Umweg als Kandidaten neu berechnet. Er
  steht bereits im bereitgestellten Planer und durfte wiederverwendet werden.
- Die gespeicherten Gelenkinterpolanten und die Programmdaten sind exakt
  gleich zur lokalen Vorabprüfung mit denselben 22-mm-Eingaben. Die
  Ergebnisdateien unterscheiden sich im URDF-Hash und in den protokollierten
  Suchzeiten. Der wiederholbare Planer erklärt die identische Bahn.
- Der gespeicherte Audit wurde erneut auf einer temporären Kopie des
  Modellergebnisses ausgeführt. Der erneut ausgegebene Audit stimmt
  bytegenau mit Geminis Audit überein. Er prüft gespeicherte
  Quellen, FK, Gelenkzeitgesetze, Rückkehr und Episode. Die ursprüngliche
  dichte FCL-Prüfung ist als Teil des Planerlaufs belegt.
- Im aufgezeichneten Verlauf gibt es keinen Hinweis auf eine Übernahme
  alter Ergebnisdateien. Die Aufzeichnung deckt sichtbare Aktionen und
  gewrappte Befehle ab. Geminis schnelle Lösung belegt die Bedienung
  des vorhandenen Toolkits. Der vorige Test mit neuem Modellcode stellt
  eine andere Entwicklungsaufgabe dar.

## Zeiten und kleinere Lücken

Der Trace misst 344,544 s ab Logger-Initialisierung (5:45 min).
Vom Start der CLI bis zum Loggerabschluss vergingen etwa 6:59 min.
Terminal-Endzeit ist in der Beobachterdatei bisher offen. Modellzeit:
395,080 s. Der Planer benötigte 82,086 s Befehlswandzeit, der Audit
1,017 s. Es gab einen gewrappten Inspektionsfehler durch einen falsch
angenommenen JSON-Schlüssel und einen zusätzlich notierten ungültigen
Logger-Notiztyp. Planung und Audit bestanden im ersten Aufruf.
Für eine durchgehende Erfassung von Skripten über stdin ist
`--stdin-file -` erforderlich. Der Starter hat die tatsächlich
verwendeten Gemini-Unterlagen neben Geminis engerem Logger-Snapshot
selbst gesichert. Die Antwort zum Greifbezug nennt die richtigen
Modellannahmen und fehlenden realen Padmessgrößen. Kontingente und
innere Denkzeit sind aus dem Trace nicht abzuleiten.
