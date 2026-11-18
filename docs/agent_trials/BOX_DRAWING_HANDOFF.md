# Kurzübernahme: kooperatives Boxzeichnen

**Für neue Varianten nach dem Gegenwand-Trial** reicht die Flächenfolge
für den [Aufruf mit `--faces`](../box_drawing_pilot.md#flächenfolge-mit-automatischer-präsentation).
`present_surface` sucht die Haltepose selbst und legt Vorschau und
Ablehnungsgründe ab. Der folgende Ablauf dokumentiert den ursprünglichen
Versuch zur Erweiterung des Modellcodes.

Stand18.11.2026. Workspace `/home/rosmatch/UWA_ws`, Repo
`src/multi_arm_manipulation_UWA`. Regeln in Workspace-/Repo-AGENTS.md gelten;
lokale Änderungen erhalten. Nur **file-only Kinematikmodell**, ohne Geräte,
ROS-Nodes oder Dienstneustarts. Der Entwicklungslauf wird separat vom
Roboterepisodenprotokoll gemessen: [TRACE_PROTOCOL.md](TRACE_PROTOCOL.md).

## Aufgabe und vorhandener Stand

`right_front`+`right_rear` halten die Box mit festen Objekt→TCP-Transforms;
`left_front` führt den virtuellen Stift, `left_rear` bleibt geparkt.
Bisher je Kreis auf Längswand **y_max** und Boden **z_min**, Radius25mm.
Ergänze die gegenüberliegende Längswand **y_min** durch weitere Boxdrehung.
Flächenbezeichnungen gelten im Objektframe. Keine neue Zeichnung im offenen
Deckelbereich und kein Kreis nochmals auf derselben Wand.

Start ist eine angenommene In-air-Fixture, offene Greifer, kein gemessener
Kontakt. Stift: Tool0+Z300mm. Modell-/Rechen-/reale Ausführungszeit trennen;
Kraft und Griff-/Verlustereignisse sind hier UNKNOWN.

## Direkte Einstiegspunkte

| Datei im Repo | Zweck |
|---|---|
| `uwa_cell_tasks/uwa_cell_tasks/box_drawing.py` | `policy`, `DrawingModel`, `compile_pilot`; gespeichertes Pythonprogramm und Modelladapter |
| `tools/box_drawing_pilot.py` | `run`, `summary`, `history`, phasenbezogenes `feedback` |
| `uwa_cell_tasks/uwa_cell_tasks/pilot_episode.py` | Ereignisse, Quellen, Feedback, fehlende Messungen |
| `tools/verify_box_drawing_pilot.py` | separater FK-/Zeit-/Episodenaudit |
| `tools/box_drawing_viewer.html` | Offlineanimation und Feedbackexport |
| `docs/box_drawing_pilot.md` | Bedienung, Prüfumfang, Fehlversuche, Nutzerfeedback |

Referenzen relativ zum Workspace:
- Eingabe: `setup/research/offline-carton-sides-20261117/standard/smoothed/result.json`.
- Startvorlage: `setup/tasks/box_drawing_pilot_20261117/overlap01/` mit
  `policy.py`, `result.json`, `independent-audit.json`, `viewer.html`, `episode/`.
- Alternative Halteposition: derselbe Ordnerstamm, `closer01/`.
- Übersicht: `feedback-comparison01/viewer.html` unter demselben Stamm.

`overlap01` benötigte49,84s, `closer01`68,07s historische Modellzeit.
Diese Referenzen nutzen0,35rad/s; aktuelle Projektvorgabe ist0,1rad/s.
Neue Läufe an0,1rad/s binden, keine weitere eigenmächtige Reduktion und keine
Ausnahme aus den alten Konstanten ableiten. Zeitvergleich nur bei gleichem Profil.

## Arbeitsablauf

1. Messprotokoll initialisieren, Regeln und diese Einstiegspunkte lesen;
   passende HANDOVER-Abschnitte über `Code-as-Policy`/`Feedbackzyklus` finden.
2. Einmal Referenzartefakte/Audit prüfen; Modellgrenzen und Revision notieren.
3. Kleine Änderung an Programm und nötigen Skills; schnellen plausiblen
   Vorschlag erzeugen. Neue Ausgaben nur unter dem eigenen Trialordner.
4. Geometrie/Interpolation aller Arme und Stift prüfen, Vorschau zeigen;
   zum Abschluss gezielten unabhängigen Audit und passende Tests ausführen.
5. Artefakte, Fehler/Reparaturen, verbleibende Grenzen und Zeiten ablegen.

Umgebung vom Workspace: `source src/multi_arm_manipulation_UWA/scripts/env.bash`.
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` für Rechenaufrufe.
CLI-Hilfe: `python3 "$REPO/tools/box_drawing_pilot.py" --help`.
Ein neuer Lauf: `run --source "$WS/setup/research/offline-carton-sides-20261117/standard/smoothed/result.json" --output "$TRIAL/artifacts/run01" --variant overlap`.
Dieser heutige Aufruf erzeugt weiterhin nur zwei Flächen; für y_min erweitern.

## Bekannte Erweiterungsstellen und Abnahme

`SURFACES`, `tip_target` und die Flächenprüfung in `phase` sind zweiflächenfest;
der Audit hat ebenfalls eine y_max/sonst-z_min-Fallunterscheidung. Beides
explizit für y_min erweitern. `reorient_together` ist auf80°/z_min festgelegt;
`return_together` kennt nur den letzten Hinweg. Viewer, Programmmetadaten und
Prüfer müssen dieselbe dritte Fläche darstellen. Kein blindes Ersetzen80→180.

Erhalten: starre Haltegruppe mit gemeinsamer Zeitbasis, alle sechs Armpaare,
Selbst-/Tisch-/Objekt-/Stiftprüfung, glatte Übergänge und unveränderte Griffe.
Boxpose und freie Arbeitsarmbewegung dürfen angepasst/koordiniert werden;
zusätzliche Positionierung mitrechnen. Umgreifen nicht still einführen.
Erfolg: drei getrennte vollständige Kreisreferenzen, belegte Flächenzuordnung,
geprüfter kompletter Weg inklusive Rückzug/Rückweg, Viewer und Episodenbericht.
Scheitert eine Route, konkreten Fehler samt Zustand/Versuch erhalten; ein
lokaler IK-Abbruch ist kein Unlösbarkeitsbeweis. Keine Prüfgrenzen lockern.

Dies ist ein Toolkit mit agentengesteuerter Programmänderung, kein universeller
Compiler und keine bereits trainierte Gesamtpolicy. Kollisions-BC-Datensätze
sind ein separates Projekt; sie müssen für diesen Test nicht neu erzeugt werden.
