# Auswertung des Gegenwand-Trials

18.11.2026. Der andere Agent hat die Aufgabenerweiterung im Kinematikmodell
erfolgreich umgesetzt. Die Übergabe funktioniert für diesen einen Test;
das Ziel „schnelles einfaches LLM programmiert hauptsächlich mit fertigen
Bausteinen“ ist damit noch nicht nachgewiesen. Zu viel geometrische Suche
und Anpassung des Modellcodes blieb beim Agenten.

Quelle: [Originalbericht](../../../../setup/agent_trials/box_away_face_20261118/trial01/report.md),
[Zeitprotokoll](../../../../setup/agent_trials/box_away_face_20261118/trial01/summary.md),
[fertiger Viewer](../../../../setup/agent_trials/box_away_face_20261118/trial01/artifacts/run06/viewer.html).
Eigene Nachprüfung: [Evidenz](../../../../setup/agent_trials/box_away_face_review_20261118/review-evidence.json),
[FK-/Zeitaudit](../../../../setup/agent_trials/box_away_face_review_20261118/audit.json),
[Browsertest](../../../../setup/agent_trials/box_away_face_review_20261118/browser-check.json),
[Screenshot](../../../../setup/agent_trials/box_away_face_review_20261118/preview.png).
Trace, Programme und Modellergebnis des Original-Trials bleiben erhalten.
Der erneut ausgeführte Audit erzeugt dessen abgeleitete Episodenzusammenfassung
neu; die eigenen Prüfberichte liegen im separaten Reviewordner.

## Ergebnis und Nachweis

- `right_front`/`right_rear` halten, `left_front` zeichnet, `left_rear` parkt.
  Der Audit bestätigt drei vollständige, getrennte 25-mm-Kreise auf
  `y_max`, `z_min`, `y_min` und die Rückkehr aller 24 Gelenke.
- Gegenwandpose: 160° Längsrollung relativ zur Ausgangspose, zusätzlich 55°
  Welt-Yaw und (+70, −50, +180) mm Translation. Translation führt die Drehung;
  der Arbeitsarm bewegt sich währenddessen mit. Diese Kombination ist ein
  belegter Fall, keine allgemeine Regel für Kartons oder andere Griffstarts.
- 13 Phasen, 397,286 s Modellzeit, maximale auditierte Geschwindigkeit
  0,096576 rad/s bei 0,1 rad/s Grenze. Die beiden Gegenwand-Transfers belegen
  zusammen 293,689 s. Die frühe 0,35-rad/s-Zweiflächenreferenz ist kein fairer
  direkter Zeitvergleich.
- Produktionsprüfung laut gespeicherten Artefakten: 19.882 Prüfzustände,
  ≤20 ms Raster, 50,201 mm kleinste Armhüllenlücke bei 20 mm Schwelle.
  Prüfcode für feste Griffe, FCL, alle sechs Armpaare und Stift blieb aktiv.
- Den separaten Audit erneut ausgeführt: PASS mit identischem Ergebnis-Hash,
  1.963 FK-Zuständen und 2.001 Ableitungsproben pro Phase. Dies ist eine
  erneute FK-/Zeit-/Episodenprüfung; die Kollisionsprüfung wurde nicht separat
  neu implementiert oder vollständig wiederholt.
- Viewer jetzt zusätzlich in echtem Headless-Chrome geprüft: zwölf Prüfungen
  bestanden, darunter drei Zeichenphasen, Rückwege, Play/Seek, Canvas und
  Inhalt des Feedbackexportes. Screenshot visuell geprüft. Der Exporttest
  fing einen Test-Download ab; kein Nutzerfeedback wurde in die Episode geschrieben.
- Die fünf fachlichen Dateien aus `source-sha256.txt` stimmen mit dem
  aktuellen Checkout überein. AGENTS/HANDOVER haben sich seitdem durch
  parallele Arbeiten verändert. Historische Quellen und Modell bleiben
  an ihre eigenen Hashes gebunden.

Der Start bleibt eine angenommene In-air-Fixture mit offenen Greifern und
virtuellem Stift. Kräfte, Schlupf, Fehlgriffe und reale Ausführungszeit sind
UNKNOWN. Der erfolgreiche Dateimodelllauf enthält kein physisches Greifen
und kein neues menschliches Feedback (`feedback_count = 0`).

## Wo die Entwicklungszeit blieb

Gemessen ab Logger-Initialisierung bis dessen Abschluss, ohne Vorlauf und
nachgelagerte Diffkorrektur. Alle 80 Befehls-Start-/Endereignisse mit ihren
Einzeldateien und Rohtextpfaden gegengeprüft; keine offenen Befehle.

| Bereich | Wandzeit | Anteil |
|---|---:|---:|
| Orientierung und Referenzsichtung | 15,53 s | 1,4 % |
| Benannte Anpassungsstufen | 34,56 s | 3,0 % |
| `plan`, `plan02`, `plan03` | 967,28 s | 85,2 % |
| Abschlussprüfung | 33,55 s | 3,0 % |
| Bericht/Abgabe | 83,24 s | 7,3 % |
| Außerhalb benannter Stufen | 0,71 s | 0,1 % |
| **Gesamt** | **18 min 54,88 s** | **100 %** |

Die Planung enthält auch Bearbeitung und Reparaturen, weil parallele Scans
den Stufenwechsel verhinderten. Die Tabellenzeile ist deshalb keine reine
Solverlaufzeit. Vereinigung aller Befehlsintervalle: 9 min 41,64 s;
übrige Wandzeit: 9 min 13,24 s. Das sind weder CPU-Auslastung noch gemessene
LLM-Denkzeiten. Client-/Modellname, Tokenzahl und Kosten sind unbekannt.

Beispiele für lange Befehle: `scan-yaw` 339,10 s ohne gefundenen Kandidaten,
`candidate06` 158,39 s einschließlich Modellprüfung und Artefaktausgabe.
Diese Befehle liefen teilweise parallel; ihre Zeiten nicht addieren oder
als direkt einsparbare Gesamtzeit ausgeben. Die fertige Vorschau ist im Trace
erst nach 16 min 57,81 s als Artefakt notiert. Ein früherer gezeigter Vorschlag
ist durch die vorliegenden Daten nicht belegt.

## Elf Exitcodes ungleich null sind nicht elf Programmierfehler

| Kategorie | Anzahl | Befund |
|---|---:|---|
| Geometrie-/Fortsetzungsfehler fertiger Kandidaten | 3 | `candidate02`: IK-Sprung; `candidate04`: Griffzwang zwischen Knoten; `candidate05`: keine geprüfte Fortsetzung |
| Suchläufe ohne Kandidat im jeweiligen Suchraum | 3 | `scan`, `scan-reverse`, `scan-yaw`; Exit 1 im Skript vorgesehen |
| Aufruf-/Pfadfehler | 3 | Variante im CLI vergessen, `20361117` statt `20261117`, hier nicht unterstütztes `tail -25` |
| Browserumgebung | 1 | Chrome `setsockopt` durch Sandbox blockiert; damals nur DOM-/Canvas-Stubs geprüft |
| Statusabfrage während laufendem Scan | 1 | abschließendes `test -f …/result.json` noch falsch; kein Planerabbruch |

Zusätzlich wurden ein ungültiger Notiztyp `context` und abgewiesene
Stufenwechsel erwähnt. Diese Logger-Aufruffehler gehören nicht zu den elf
gewrappten Kindprozessfehlern. Fehlerbilder und lokale IK-Abbrüche belegen
keine generelle Unlösbarkeit der 180°-Präsentation.

## Konsequenzen für das Toolkit

| Priorität | Änderung | Beleg und gewünschte Wirkung | Stand |
|---|---|---|---|
| 1 | Geprüften Skill `present_surface` mit Halteposen-/Routensuche anbieten | Mehrere eigens geschriebene Scans und Änderungen an IK-/Spline-Anbindung; das LLM sollte Ziel, Kriterien und Budget angeben und strukturierte Diagnosen erhalten | nächster fachlicher Ausbau |
| 2 | Aufgabenparameter durchgehend in einem Vertrag führen | Oberfläche, CLI-Auswahl, Policy, Prüfer und Viewer mussten gemeinsam ergänzt werden; neue Aufgabe soll primär Flächenfolge/Radius/Rollen konfigurieren | offen |
| 3 | Schnelle Vorschau und vollständige Abnahme als explizite Schritte | Erste belegte Vorschau erst nach knapp 17 min; früh einen plausiblen Vorschlag mit klarem Prüfstatus zeigen, abschließende Prüfung beibehalten | offen |
| 4 | Inputs und Änderungen lückenlos zu Befehlen binden | Acht `python3 -`-Aufrufe archivieren den Bearbeitungscode nicht; weitere `cat >`-Aufrufe haben dieselbe Lücke | `--stdin-file` implementiert |
| 5 | Wiederverwendbare Erfahrung mit Geltungsbereich speichern | Gefundene Route, negative Versuche und unveränderte Kreisphasen sind wertvoll; bloße feste Szenenkonstanten bilden noch kein langfristiges Lernen | Fall liegt vor, Abruf-/Auswahlmechanismus offen |

Der erste Ausbau sollte einen kleinen, klaren Vertrag erhalten:
Eingabe sind Objekt-/Griffzustand, Zielfläche, Stiftgeometrie, aktuelle
Grenzen und Suchbudget. Ausgabe sind Kandidaten mit gemeinsamem
Objekt-/Arbeitsarmweg, Prüfstatus, Dauer und begründeten Ablehnungen.
Das LLM setzt anschließend die Schritte der Gesamtaufgabe zusammen.
Die konkrete 160°-/55°-Route kann als Startkandidat dienen, bleibt aber
bei verändertem Modell oder Start erneut zu prüfen.

Für langfristiges Lernen den Fall samt Modellhash, Grifftransforms,
Werkzeug, Startzustand, Grenzen, gefundenem Weg und Fehlerklassen abrufbar
halten. Nutzerkorrekturen und später gemessene Ausführungsereignisse getrennt
ergänzen. Nicht aus einem lokalen IK-Fehler „180° geht nie“ lernen.
Dieser Trial prüfte Codeübertragung; Demonstrationslernen, Teleop-Korrektur
und Verbesserung aus wiederholter realer Ausführung bleiben ungetestet.

Die Laufzeit der Roboteraufgabe kann später ein Auswahlkriterium sein.
Für den nächsten Entwicklungsschritt hat die Entlastung des LLM von
geometrischer Such- und Reparaturarbeit Vorrang.

## Direkt umgesetzt und geprüft

`tools/agent_trial.py run --stdin-file DATEI|-` archiviert Eingabebytes
einschließlich Größe und SHA256 und speist genau diese Kopie in den
Kindprozess. Ohne Option steht ausdrücklich `inherited_unrecorded` in den
Metadaten. [Traceprotokoll](TRACE_PROTOCOL.md) mit Beispiel aktualisiert;
Diff gegen Eingangsrevision/Snapshots und Abschlussreihenfolge präzisiert.
Die vorhandenen Trialdaten bleiben unverändert und werden nicht nachträglich
als vollständiger Trace ausgegeben.

Zehn gezielte Loggertests bestanden, einschließlich leerer/binärer Eingabe,
CLI-Heredoc, Fehler-/Timeout-/Unterbrechungserfassung und Parallelzeiten.
Der andere Agent hatte zuvor 20 Pilot-/CLI-/Loggertests bestanden; diese
historische Angabe ist von den jetzt erneut ausgeführten Tests getrennt.
Keine Hardware-, Kamera- oder Dienstaktion.
