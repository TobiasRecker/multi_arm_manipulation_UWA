# Auswertung des Nikolaushaus-Tests

19.11.2026. Gemini hat die Zeichenbahn in seiner separaten Quellkopie
erweitert. Der Dateimodelllauf enthält das Nikolaushaus auf `z_min`
und die beiden Seitenkreise mit 22 mm Radius. Der Prüfer aus dem
Hauptrepo bestätigt die acht Kanten, den vollständigen Rückweg und
0,097667 rad/s maximale Gelenkgeschwindigkeit bei 0,1 rad/s Grenze.
Geminis eigener Audit ließ sich bytegleich wiederholen. Mit dem
erweiterten Prüfer besteht auch der archivierte Drei-Kreis-Lauf.
Die 16 Implementierungshashes entsprechen den Dateien, die beim Lauf
verwendet wurden. Die dichte Kollisionsprüfung stammt aus dem
aufgezeichneten Modelllauf.

[Animation](../../../../setup/agent_trials/nikolaus_gemini_20261119/session-eop62x8b/trial/artifacts/nikolaus_run01/viewer.html) ·
[Bericht des Agenten](../../../../setup/agent_trials/nikolaus_gemini_20261119/session-eop62x8b/trial/report.md) ·
[Nachprüfung](../../../../setup/agent_trials/nikolaus_review_20261119/owner-audit.json)

## Was am Ende passiert

Der Nutzer beobachtet eine unerwartete Bewegung des Zeichenarms gegen
Ende. In der Animation kann man dazu direkt **Return box** anwählen.
Die Tabelle verwendet die Zeitachse des Modells.

| Phase | Modellzeit | Bewegung des Zeichenarms |
|---|---:|---|
| `return_standoff_z_min` | 68,67–70,70 s | Nach dem Rückzug 40 mm parallel zur Unterseite von B zurück nach A |
| `retract_y_min` | 225,50–227,67 s | 60 mm gerader Rückzug von der Gegenwand |
| `return_from_y_min` | 227,67–374,52 s | Während die Box zurückdreht, folgt der Zeichenarm exakt seinem alten Weg zurück zur Vorpose von A |
| `return_box` | 374,52–406,41 s | Anfahrt zur Unterseite rückwärts. Handgelenk 1 dreht −172,83°, Handgelenk 3 dreht +130,64° |

Die letzten beiden gemeinsamen Gelenkpfade sind an jeder Stützstelle
identisch zu den jeweiligen Hinwegen in umgekehrter Reihenfolge.
In `return_box` läuft die Stiftspitze dadurch auf einem Bogen von
rund 384 mm bei einem direkten Abstand der Endpunkte von 113 mm.
Die letzte große Handgelenkbewegung ist ein Rückweg durch eine
frühere Vorpose, die der Zeichenarm zu diesem Zeitpunkt nicht mehr
für die Aufgabe braucht. Die Rückkehrlogik ist vom ursprünglichen
Toolkit geerbt. Gemini hat den 40-mm-Umweg nach dem Haus hinzugefügt,
damit das offene Ende B wieder zum vorherigen Vertrag an A passt.
Während des Bogens ist der Stift im Modell bereits abgehoben.

Sieben einfache Varianten, mit denen der Zeichenarm während derselben
Halterbahnen direkt parkt, wurden im Offline-Screen verworfen. Das
Stiftmodell trat in die Kartonhülle ein. Die Versuche decken lineare
und glatte Gelenkübergänge mit unterschiedlichen Start-/Endpunkten
des Fortschritts ab. Ein neuer Rückweg braucht einen geprüften
Ausweichweg oder andere Zwischenzustände.

[Messwerte der Rückfahrt](../../../../setup/agent_trials/nikolaus_review_20261119/review-evidence.json) ·
[Abgelehnte Direktwege](../../../../setup/agent_trials/nikolaus_review_20261119/direct-park-probe.json)

## Wo Zeit blieb

| Stufe | Wandzeit | Geloggte Befehle aktiv |
|---|---:|---:|
| Orientierung | 2:50 min | 3,11 s |
| Anpassung | 7:39 min | 1,82 s |
| Planung | 2:49 min | 71,52 s |
| Prüfung | 5:04 min | 10,39 s |
| Abgabe | 1:03 min | 0,12 s |
| Gesamt | 19:25 min | 86,96 s |

Anpassung und Prüfung beanspruchten zusammen rund zwei Drittel der
aufgezeichneten Wandzeit. Die Restzeit umfasst auch Lesen, Bearbeiten,
Antigravity-Aktionen und Warten. Die Modellrechnung des Hauptlaufs
bestand im ersten Versuch. Der einzige gewrappte Fehllauf war eine
falsch gequotete Shellvariable beim Aufruf der Tests.
Die Roboter-Modellzeit beträgt 406,41 s, davon 178,74 s für die letzten
beiden Rückwege. Hin- und Rückbewegung für die Gegenwand dauern
zusammen 293,69 s. Die Vorschau taucht im Protokoll während der
Planung auf, die Zeit bis zur tatsächlichen Anzeige wurde nicht
einheitlich erfasst.

[Stufenprotokoll](../../../../setup/agent_trials/nikolaus_gemini_20261119/session-eop62x8b/trial/summary.md)

## Wo das Framework am meisten helfen kann

1. **Neue Formen als Pfaddaten.** Gemini musste Modell, CLI, Viewer und
   Prüfer anfassen. Der Diff umfasst fünf Dateien mit 462 Einfügungen
   und 77 Entfernungen. Ein Pfadbaustein für Linienzüge und Kreise kann
   Objektframe, Liniensegmente, Pen-down, Einstiegs- und Ausstiegspose
   einheitlich beschreiben. Planer und Viewer lesen diesen Vertrag.
   Der Prüfer rekonstruiert die Stiftbahn aus den Gelenken und vergleicht
   sie mit Sollkanten bzw. Sollkreis. Eine Form wie das Haus sollte
   als Punktfolge in den Auftrag passen.
2. **Rückweg aus der tatsächlichen Ausstiegspose.** Den Zeichenarm nach
   dem letzten Strich freifahren und seinen Weg zur Parkpose gemeinsam
   mit der Box-Rückfahrt planen. Die beiden tragenden Arme bleiben
   an denselben starren Objektbezug gekoppelt. Modellzeit, Gelenkweg
   und Abstand des Stiftkörpers zum Karton sind geeignete Kriterien.
   Der geprüfte umgekehrte Hinweg bleibt eine Rückfalloption.
3. **Schnellere Abnahme und besseres Timing.** Wiederverwendbare
   Audit- und Viewer-Prüfungen griffbereit machen sowie Zeitmarken
   für erste Vorschau, Planerende und Freigabewartezeiten erfassen.
   Eine kurze Umgebungskontrolle im Starter kann den Shell-Aufruffehler
   vermeiden. Die vorliegenden Zeiten sprechen dafür, zuerst den
   Integrationsaufwand zu senken, bevor wir den Planer beschleunigen.

Geminis Quellkopie und der gespeicherte Diff bleiben als überprüfbare Referenz erhalten. Die
Framework-Änderungen sind aus dieser Auswertung abgeleitet.
