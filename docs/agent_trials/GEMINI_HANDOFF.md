# Zweiter Agententest · Einstieg für Gemini

Workspace `/home/rosmatch/UWA_ws`, Repo
`src/multi_arm_manipulation_UWA`. Der Startprompt enthält den absoluten
Ausgabeordner. Initialisiere ihn mit `agent_trial.py init`. Der Elternordner
existiert bereits. Hinweise zur Erfassung stehen im [Traceprotokoll](TRACE_PROTOCOL.md).
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

1. Initialisiere den Logger möglichst früh mit `--task box-gemini-02`.
   Trage Client/Modell unter `--agent` ein, soweit du sie sicher kennst.
   Nutze die Stufen `orient`, `adapt`, `plan`, `verify`, `deliver`.
   Halte merkliche Wiederholungen, Fehlversuche und Nutzerhilfen fest.
2. Erzeuge den Lauf über die vorhandene CLI. Die Planung kann mehrere
   Minuten dauern. Für Zwischenstand eignen sich `presentation-search.json`
   und `preview-*.html`. Kandidatenvorschauen kennzeichnen ausstehende Prüfungen.
3. Prüfe das gespeicherte Programm und den separaten Audit. Erwartet werden
   Flächenfolge und Radius aus dem Auftrag, Rückkehr aller 24 Armgelenke,
   Modellgrenze 0,1 rad/s und vollständiger Modelllauf. Die im Ergebnis
   gespeicherten Hüllenabstände beziehen sich auf das Modell.
4. Schreibe `TRIAL/report.md` mit Ergebnisstatus, Pfaden zu Viewer und
   Audit, Zeiten der Planung und des Modellablaufs, Treibern der Wartezeit,
   Fehlversuchen, manueller Hilfe und Toollücken. Nenne auch ohne Fehler,
   ob du den Aufruf allein aus der Übergabe ableiten konntest.
   Unbeobachtete Kontaktgrößen als unbekannt kennzeichnen.
5. Schließe die letzte Stufe und rufe `finish` mit dem tatsächlichen
   Ergebnisstatus auf. Der Logger misst Stufenwandzeit. Die Zeile
   „Restzeit“ umfasst auch Lesen, Chat, Bearbeitung und Warten.
