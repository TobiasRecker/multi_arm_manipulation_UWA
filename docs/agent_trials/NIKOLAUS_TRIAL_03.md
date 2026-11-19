# Dritter Test mit Gemini · Haus vom Nikolaus

Starte aus einer normalen VS-Code-Terminalsitzung mit dem bereits
angemeldeten Konto:

```bash
cd /home/rosmatch/UWA_ws
python3 src/multi_arm_manipulation_UWA/tools/start_gemini_trial.py --case nikolaus
```

Für einen direkten Start im Antigravity-Automatikmodus
`--mode=auto` anhängen. Der gewünschte Modus steht anschließend in
`observer.json` unter `mode_requested`. Ob Antigravity ihn aktivieren
konnte, zeigt die Statuszeile der CLI. Falls Konto oder Terminal-Sandbox
den Modus nicht unterstützen, kann Antigravity auf den Standardmodus
zurückfallen. Ohne Option entscheidet die bestehende Client-Konfiguration.
[Antigravity-Freigabemodi](https://antigravity.google/docs/cli/modes)

Der Starter legt pro Versuch ein eigenes Verzeichnis an und öffnet dort
eine frische Unterhaltung in einer separaten Quellkopie des aktuellen
Commits. Die Quellkopie enthält keine bisherigen Ergebnisordner und hat
kein Git-Remote. Modellquelle und installierte ROS-Module bleiben
gemeinsame Eingaben. Die Verzeichnistrennung schützt den Arbeitsbaum
und erleichtert den Quelldiff. Zugriffe per absolutem Pfad unterliegen
weiter den Berechtigungen des Clients. Vergangene Sessions und
Ergebnisse werden der neuen Unterhaltung nicht als Kontext übergeben.

Die ersten und letzten Kreise behalten 22 mm Radius. Auf der Unterseite
zeichnet der Agent ein Nikolaushaus mit acht Kanten in einem Zug.
Der ursprüngliche Versuch verlangte eine neue Implementierung. Neue
Läufe verwenden den vorhandenen Oberflächenpfad und den gebündelten
Prüf- und Abgabeaufruf aus dem Startprompt.
Haltegeometrie, Modellquelle, Rollen und Gelenkgrenze bleiben der
Vergleichsrahmen.

[Prompt](PROMPT_NIKOLAUS_TRIAL_03.md) · [Agentenübergabe](NIKOLAUS_HANDOFF.md)

Mit `--prepare-only` erzeugt der Starter stattdessen Quellkopie und Prompt
für eine neue Sitzung in der VS-Code-Erweiterung. Öffne das ausgegebene
`Repo:` als Ordner und übergib den erzeugten `prompt.md` vollständig.
Beim CLI-Weg werden sichtbare Terminalausgaben und Zeiten aufgezeichnet.
Für vergleichbare Befunde Modell und genutzten Freigabemodus festhalten.

## Abnahme nach dem Lauf

Im ausgegebenen Sitzungsordner befinden sich Bericht unter
`trial/verification/`, Trace, Ergebnis und Viewer. Bei Bedarf kann der Bedientest die tatsächlichen
Gelenkbahnen zusätzlich mit dem Prüfer aus dem **Hauptrepo** auswerten:

```bash
cd /home/rosmatch/UWA_ws
source src/multi_arm_manipulation_UWA/scripts/env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  src/multi_arm_manipulation_UWA/tools/check_nikolaus_trial.py PFAD_ZUM_ERGEBNISORDNER
```

Der Prüfer nimmt die Unterseitenpunkte aus der FK des gespeicherten
Gelenkinterpolanten. Er fordert die acht geraden Kanten in vorgegebener
Reihenfolge, die Unterseitenebene, beide Seitenkreise, die feste Haltung
beim Zeichnen und die Rückkehr zum Modellstart. Die geometrische Toleranz
des separaten Prüfers beträgt 0,5 mm. Kollisionsprüfung, Viewer,
Quelldiff und Zeitprotokoll bleiben eigene Nachweise des Trials.
Die CLI und geloggte Befehle getrennt zeitlich betrachten.

Die Quellkopie und der Offline-Einstieg wurden mit dem vorhandenen
22-mm-Kreis auf `y_max` geprüft. Der unabhängige Prüfer akzeptiert einen
synthetischen exakten Hauszug und lehnt den vorherigen Drei-Kreis-Lauf ab.
Der tatsächliche Hauslauf bleibt die Aufgabe des neuen Agenten.
