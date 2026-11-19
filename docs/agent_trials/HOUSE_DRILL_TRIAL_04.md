# Gemini-Test 04 · Doppeltes Haus, Lochkreis und fester Stift

Im VS-Code-Terminal mit dem bereits angemeldeten Antigravity-Konto starten:

```bash
cd /home/rosmatch/UWA_ws
python3 src/multi_arm_manipulation_UWA/tools/start_gemini_trial.py --case house-drill --mode=auto
```

Der Starter öffnet eine frische Unterhaltung in einem separaten Checkout
des aktuellen Commits. Er kopiert Prompt, Übergabe und Geometrie in den
Sitzungsordner. Das Terminalprotokoll liegt unter
`setup/agent_trials/house_drill_gemini_20261119/session-…/`.
Für eine neue Sitzung in der IDE-Erweiterung `--prepare-only` verwenden
und den erzeugten Prompt aus dem ausgegebenen Repo starten.

Auf ROSmini fiel Antigravity CLI 1.5.12 beim ersten Versuch wegen der
AppArmor-Konfiguration von `auto` auf `default` zurück. Der Starter
warnt in diesem Fall. Bei Bedarf direkt mit `--mode=accept-edits` starten.
Dieser Modus übernimmt Dateiedits im Test-Checkout automatisch.

Der CLI-Starter legt jetzt Logger und `trial/artifacts` an. Er lädt eine
Konfiguration nur für diese Sitzung und schreibt `antigravity.log` in
den Sitzungsordner. Die abgegrenzte Freigabe deckt Logger-Einträge, eine
Dateiliste und `mkdir` direkt unter `trial/artifacts` ab, jeweils in den
im erzeugten Prompt genannten Aufrufformen. Die globale Allow-Liste wird
für diesen Lauf durch die Sitzungsregeln ersetzt. Vorhandene Ask- und
Deny-Regeln werden übernommen. Modellläufe, Python-Probes und Tests
verwenden weiterhin die normale Freigabe des gewählten CLI-Modus.
[Antigravity-Freigabemodi](https://antigravity.google/docs/cli/modes) ·
[Berechtigungen](https://antigravity.google/docs/permissions?tab=cli) ·
[Hooks](https://antigravity.google/docs/hooks?tab=cli)

Der erste Seitenkreis bleibt bei 22 mm Radius. Auf der Unterseite wird
das Haus linear um Faktor zwei skaliert. Die sechs axialen Stellen liegen
im Abstand von je 60° auf einem vollständigen Lochkreis Ø150 mm.
Sein Mittelpunkt liegt in der Mitte der äußeren Hausabmessungen.
So bleibt das gesamte Haus innerhalb des Kreises und der Abstand eines
Lochmittelpunkts zur nächstliegenden Hauskante beträgt mindestens 15 mm.
Als Testannahme gilt 3 mm geometrische Zustelltiefe bei 15 mm Vorabstand.
Das größere Haus wurde im isolierten Checkout als einzelne Unterseiten-
Aufgabe ausgeführt. Der vorhandene FK-/Zeitaudit bestätigt acht Kanten
und Rückkehr im 0,1-rad/s-Profil. Die Kombination mit Zustellungen und
abschließendem Kreis bleibt die Aufgabe des Agenten.

Auf der Gegenwand bleibt der Stift beim Zeichnen des 22-mm-Radius-Kreises
fest im Weltframe. Die Haltearme bewegen den Karton mit festen Griffen
und gemeinsamer Zeitbasis. Eine Punktprüfung an 129 Kreispositionen hat
im Vormodell eine mögliche Geometrie gezeigt. Der Nachweis für Anfahrt,
vollständig zeitparametrierte Kreisbahn und Rückzug gehört zum Agententest.
Falls diese Variante im Suchbudget scheitert, kann der Agent die anderen
geprüften Teile abgeben und den bewegten Stift als Teilresultat kennzeichnen.

[Prompt](PROMPT_HOUSE_DRILL_TRIAL_04.md) ·
[Agentenübergabe](HOUSE_DRILL_HANDOFF.md) ·
[Maße und Phasenanforderungen](house_drill_spec.json)

## Auswertung

Der erzeugte Startprompt enthält den Aufruf für Prüfung und Abgabe.
Beispiel aus dem UWA-Workspace nach Ende der Planungsstufe:

```bash
python3 src/multi_arm_manipulation_UWA/tools/finish_gemini_trial.py PFAD_ZUR_SITZUNG run01
```

Der Aufruf verwendet die beiden Prüfer aus dem Hauptrepo. Der
Aufgabenaudit rekonstruiert die Stiftspitze aus den Gelenkbahnen und prüft
Hauskanten, sechs axiale Zyklen, die Kreise, festen Stift, Griffrelationen
und Rückkehr. Der zweite Audit prüft unter anderem Geschwindigkeit,
Beschleunigung, Ruck und die Bindung ans Episodenprotokoll. Die
Viewer-Prüfung liest das eingebettete JSON direkt, vergleicht Programm,
Ergebnis-Hash, Phasen und Zeitachse und prüft die axialen Renderer-Daten.
Geometrie-, Kollisions- und Kontaktphysiknachweise bleiben getrennt.

Bei Python-Änderungen führt der Aufruf die vorhandenen Tests für
Pfadgeometrie, Box-CLI und Episoden aus. Der Agent ändert keine Tests oder
Audits. Änderungen daran erscheinen als Fehler in der Abgabe. Bericht,
vollständiger Patch, Prüf-JSON und Logs liegen zusammen unter
`trial/verification/run01-…/`. Der Aufruf beendet den Trial bei `PASS`.
Bei `FAIL` bleibt der Trial für eine Korrektur offen. Frühere Prüfversuche
bleiben erhalten. Einen abgeschlossenen Lauf kann man mit
`--review-output PFAD_ZUM_NEUEN_ORDNER` erneut auswerten.

Für Entwicklungsgeschwindigkeit den Terminalstart aus `observer.json`
bis `trial_end` in `trial/events.jsonl` messen. Im CLI-Log die Zeit von
`Surfacing tool confirmation` bis `Responding to tool confirmation` für
denselben Schritt erfassen. Die Differenz zur Gesamtzeit enthält weiter
Lesen, Bearbeiten und Befehlslaufzeiten.
