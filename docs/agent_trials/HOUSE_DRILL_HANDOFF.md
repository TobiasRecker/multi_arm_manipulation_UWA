# Übergabe für Haus, Lochkreis und festen Stift

Verwende den vom Starter genannten Repo- und Trialpfad. Eingabedaten stehen
in `../context/house_drill_spec.json`. Die Datei beschreibt den Auftrag
und die Geometrie. Die bestehende Box-CLI versteht bereits die
Haus-Punktfolge, die beiden neuen Bewegungsarten sind deine Aufgabe.
Frühere Agentenläufe und fertige Ergebnisordner gehören nicht zur Aufgabe.

Modellquelle gleichermaßen für alle Stufen:
`/home/rosmatch/UWA_ws/setup/research/offline-carton-sides-20261117/standard/smoothed/result.json`.
Vor Modellaufrufen die bestehende Umgebung aus
`/home/rosmatch/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash`
laden. `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` setzen. Bei eigenen
Python-Probes die Paketpfade aus deiner Quellkopie vor das bestehende
`PYTHONPATH` setzen und den bestehenden Wert anhängen. Die Python-Tools
aus deiner **Quellkopie** starten. Arbeits- und Prüfdateien liegen im
Trialordner. Dienste oder Plugins müssen dafür nicht gestartet werden.

| Einstieg in der Quellkopie | Zweck |
|---|---|
| `docs/workpiece_paths.md` | Flächenkoordinaten, JSON-Punktfolge, axialer Referenzbaustein |
| `tools/box_drawing_pilot.py` | Vorhandener Kommandozeileneinstieg |
| `uwa_cell_tasks/uwa_cell_tasks/workpiece_paths.py` | `SurfaceFrame`, `SurfacePolyline` und `AxialFeed` |
| `uwa_cell_tasks/uwa_cell_tasks/box_drawing.py` | Flächenpräsentation, fest gekoppelte Haltearme, gemeinsames Zeitgesetz, optionale Rückwegsuche |
| Prüf- und Abgabeaufruf im Startprompt | Vorhandene Bahnaudits, Viewer-Prüfung, gezielte Tests und Abgabe |
| `tools/agent_trial.py`, `docs/agent_trials/TRACE_PROTOCOL.md` | Schrittzeiten, Befehle und Rohtexte |

## Bewegungsanforderungen

- Auf der Unterseite gilt `u = Objekt+X`, `v = Objekt−Y` und
  `normal = Objekt−Z`. Der Lochkreismittelpunkt liegt im Mittelpunkt
  der äußeren Hausabmessungen. Die sechs Positionen nach JSON-Vorgabe
  nummerieren: `site=1` für 30°, dann jeweils +60°. Bearbeitungsreihenfolge
  1 bis 6. Jede Zustellung hat eine durchgehende Werkzeugachse nach
  innen und eine während des jeweiligen Zustellzyklus stationäre Box.
- Die Zustellungen sind ausschließlich geometrische Modellvorgänge.
  Verifiziere begrenzte Spitzeneindringung an der jeweiligen Stelle.
  Falls das Modell eine Ausnahme für die beabsichtigte Spitzeneindringung
  braucht, binde sie ausschließlich an diese Stelle, den axialen
  Prozessschritt und die spezifizierte Tiefe. Arm- und Haltergeometrie,
  übriger Werkzeugkörper, Umgebungsprüfung und alle freien Übergänge
  bleiben vollständig geprüft. Der Lauf erfasst keine Bohrkraft.
- Der letzte Kreis wird im Werkstückframe geprüft. Gleichzeitig muss
  der TCP des Arbeitsarms im Weltframe mitsamt Werkzeugorientierung
  und allen sechs Armgelenken konstant bleiben. Rechte Halter behalten
  ihre festen Griffe und ein gemeinsames Zeitgesetz. Die Gegenwand bleibt
  zur Stiftachse ausgerichtet. Auch die
  Annäherung und das Freifahren müssen in der Modellbahn geprüft sein.
- Markiere axiale Phasen im üblichen `result.json` mit
  `operation: axial_approach | axial_feed | axial_retract`, numerischem
  `site` (1 bis 6), `face: z_min` und `drawing: false`.
  Je Stelle: Vorabstand → Oberfläche → Zieltiefe → Vorabstand.
  Beide Seitenkreise und die Kanten des Hauses haben `drawing: true`.
  Pro Phase wie bisher die gemeinsamen 24-Gelenk-Interpolanten speichern.
  Behalte für diesen Modellvergleich den Tool0-Spitzenversatz von
  300 mm entlang Tool+Z. Halter- und Modellbindungen bleiben im Bericht.

## Ablauf und Rückgabe

1. Falls der Starter den Logger vorbereitet hat, direkt mit `start orient`
   beginnen. Sonst mit `--task box-house-drill-04` initialisieren.
   Stufen `orient`, `adapt` und `plan` erfassen.
   Rechenbefehle samt stdout/stderr wrappen, Editoren und Freigaben
   bei Bedarf als Notizen ergänzen. Keine Befehle für Zelle oder Kamera.
2. Projektänderungen und Tests nur in der eigenen Kopie. Beginne mit
   einem kleinen nachprüfbaren Vorschlag. Ergebnis und Viewer unter
   `TRIAL/artifacts/` ablegen. Erzeuge die sichtbaren Axial- und
   Kreisphasen aus den tatsächlichen Bahnkoordinaten.
3. Planungsstufe schließen und den Prüf- und Abgabeaufruf aus dem
   Startprompt ausführen. Er verwendet die vorhandenen Tests und Audits,
   prüft die eingebetteten Viewer-Daten und erzeugt `report.md` und
   `changes.patch`. Bei bestandener Prüfung schließt er das Protokoll ab.
   Tests und Audits unverändert lassen. Bei einem Fehler den Befund nutzen,
   um gezielt die Modelllösung nachzubessern.
