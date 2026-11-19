# Nikolaushaus · Einstieg für Gemini

Der Starter nennt die absoluten Pfade zur separaten Quellkopie und zum
Trial. Starte dort ohne alten Chatkontext. Die Quellkopie ist dein
Arbeitsbereich. Die bekannten Laufartefakte und früheren Agentensitzungen
gehören nicht zum Auftrag.

Freigegebene Modellquelle:
`/home/rosmatch/UWA_ws/setup/research/offline-carton-sides-20261117/standard/smoothed/result.json`.
Die in der Eingabe gebundenen Modelle und Abhängigkeiten werden aus dem
bestehenden Workspace gelesen. Übernimm die Umgebung aus
`/home/rosmatch/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash`
in der jeweiligen Shell. Setze für Rechenaufrufe
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. Führe den Python-Einstieg
aus deiner eigenen Quellkopie aus. Der Vorab-Lauf und die Audits
benötigen weder einen ROS-Knoten noch Gazebo oder echte Geräte.

| Einstieg in der Quellkopie | Zweck |
|---|---|
| `docs/box_drawing_pilot.md` | CLI, `present_surface`, Zwischenvorschau, Ergebnisformat und Greifbezug |
| `tools/box_drawing_pilot.py` | Einstiegs-CLI |
| `docs/examples/nikolaus_surface_path.json` | Geprüfte Punktfolge für `--tool-paths` auf `z_min` |
| `uwa_cell_tasks/uwa_cell_tasks/box_drawing.py` | Zeichenbahn, Anfahrt, Prüfung und gemeinsamer Rückweg |
| `tools/check_nikolaus_trial.py RUN` | Vorhandener FK-/Zeitaudit für die Hausaufgabe |
| `tools/agent_trial.py`, `docs/agent_trials/TRACE_PROTOCOL.md` | Stufenprotokoll und Rohdaten |

Verwende den vorhandenen Prüfer für das Haus aus den tatsächlich
gespeicherten Gelenkinterpolanten. Geprüfte Kanten und Zeichenflächen müssen im
Ergebnis nachvollziehbar sein. Haltearme bleiben beim Zeichnen in
derselben Stellung. Die neue Bahn muss am Ende das Zurückfahren mit
denselben Griffen erlauben. Die HTML-Kollisionshüllen beziehen sich
auf den nominell offenen Kinematikgriff.

Das Ergebnisformat soll wie bisher `result.json` mit `initial_state`,
`program`, `grasp_offsets`, `holder_tcp_offsets`, `dimensions_m` und
`phases` speichern. Jede Phase hat `id`, `face`, `drawing`, `duration_s`
und einen `segment` wie im Original. Markiere nur Striche als
`drawing: true`. Mehrere direkt anschließende Phasen für die acht
Kanten sind zulässig. Der Viewer soll die Form aus den Modellpunkten
auf dem Karton anzeigen. Alte Kreisprogramme bleiben lauffähig.

1. Verwende den vorbereiteten Logger. Falls die IDE-Variante ihn noch
   braucht, initialisiere ihn mit `--task box-nikolaus-03`. Die Stufen
   `orient`, `adapt` und `plan` nutzen.
2. Lauf und Viewer in einen neuen Ordner unter `TRIAL/artifacts/`
   schreiben. Fehlversuche und sichtbare
   Berechtigungsabfragen mit Auswirkungen auf den Ablauf dokumentieren.
3. Schließe die Planungsstufe und führe den Prüf- und Abgabeaufruf aus
   dem Startprompt aus. Er führt die vorhandenen Audits und bei
   Codeänderungen die betroffenen Tests aus und schreibt Patch und Bericht.
