# Zweiter Agententest · Einstieg für Gemini

Workspace `/home/rosmatch/UWA_ws`, Repo
`src/multi_arm_manipulation_UWA`. Der Startprompt enthält den absoluten
Ausgabeordner und die isolierte Quellkopie. Falls der Starter den Logger in
der IDE-Variante noch nicht vorbereitet hat, initialisiere ihn mit
`agent_trial.py init`. Hinweise stehen im [Traceprotokoll](TRACE_PROTOCOL.md).
Verwende die Workspace- und Repo-Regeln für diese Dateimodellaufgabe.

| Einstieg | Zweck |
|---|---|
| [Boxzeichnungs-Pilot](../box_drawing_pilot.md#flächenfolge-mit-automatischer-präsentation) | Vorhandener Einstieg `tools/box_drawing_pilot.py run --faces …`, Radius, Vorschau und Modellbericht |
| `tools/verify_box_drawing_pilot.py RUN --output DATEI` | Separater FK-, Zeit- und Episodenaudit |
| [Greifhöhen-Abgleich](../../HANDOVER.md#greifhöhe-im-html-piloten-und-in-der-kontaktgeometrie-2026-11-19) | Herkunft und Bezugsframes des offenen HTML-Griffs und der Gazebo-Kontaktreferenz |
| [Traceprotokoll](TRACE_PROTOCOL.md) | Schrittzeiten, Befehle, Rohtexte, Fehler, Notizen, Abschluss |

Quelle aus dem Workspace:
`setup/research/offline-carton-sides-20261117/standard/smoothed/result.json`.
Aus dem Workspace vor den Modellaufrufen `source src/multi_arm_manipulation_UWA/scripts/env.bash`.
Plane mit `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. Der Lauf bleibt offline
und benötigt keinen ROS- oder Gazebo-Dienst. Verwende einen neuen Ordner
unter `TRIAL/artifacts/`. Kartonflächen im Objektframe: zugewandte Längswand
`y_max`, Unterseite `z_min`, Gegenwand `y_min`.

1. Verwende den vorbereiteten Logger oder initialisiere ihn mit
   `--task box-gemini-02`. Nutze `orient`, `adapt` und `plan`.
   Halte merkliche Wiederholungen, Fehlversuche und Nutzerhilfen fest.
2. Erzeuge den Lauf über die vorhandene CLI. Die Planung kann mehrere
   Minuten dauern. Für Zwischenstand eignen sich `presentation-search.json`
   und `preview-*.html`. Kandidatenvorschauen kennzeichnen ausstehende Prüfungen.
3. Notiere kurz, was die Hüllenabstände im Modell bedeuten und welche
   Kontaktgrößen unbekannt sind. Schließe die Planungsstufe und führe den
   Prüf- und Abgabeaufruf aus dem Startprompt aus. Er prüft Flächenfolge,
   Radius, Rückkehr, Zeitgesetz und Viewer, schreibt den Bericht und
   schließt den Trial bei `PASS` ab. Bei `FAIL` prüfe die genannte Fundstelle.
