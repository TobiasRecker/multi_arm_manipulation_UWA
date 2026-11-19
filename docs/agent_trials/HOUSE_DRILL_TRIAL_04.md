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

Auf ROSmini meldet Antigravity CLI 1.5.12 bei der aktuellen
AppArmor-Konfiguration einen Ausfall seiner Terminal-Sandbox und fällt
von `auto` in den Standardmodus zurück. Im laufenden Test ist
`accept-edits` aktiv. Damit werden Dateiedits automatisch angenommen.
Für wiederkehrende Aufrufe kann man bei der Freigabe **always allow in
this conversation** für den konkret geprüften Befehl wählen. Bei einem
neuen Start lässt sich `--mode=accept-edits` direkt angeben. Der Starter
warnt nun beim bekannten AppArmor-Fallback und schreibt den Hinweis
in `observer.json`. Maßgeblich bleibt die tatsächliche Statuszeile.
[Antigravity-Freigabemodi](https://antigravity.google/docs/cli/modes) ·
[Berechtigungen](https://antigravity.google/docs/permissions?tab=cli)

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

Im ausgegebenen Sitzungsordner liegen nach dem Lauf `trial/report.md`,
`trial/changes.patch`, Zeitprotokoll, Viewer und Modellergebnis. Der
Prüfer im **Hauptrepo** rekonstruiert die Stiftspitze aus den Gelenkbahnen
in Welt- und Kartonkoordinaten:

```bash
cd /home/rosmatch/UWA_ws
source src/multi_arm_manipulation_UWA/scripts/env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  src/multi_arm_manipulation_UWA/tools/check_house_drill_trial.py PFAD_ZUM_ERGEBNISORDNER
```

Das Prüfprogramm verlangt die acht doppelten Hauskanten, sechs
durchgehende axiale Zustellzyklen, beide vollständigen Kreisreferenzen,
feste Griffrelationen und Rückkehr aller Gelenke. Für den letzten Kreis
prüft es zusätzlich die sechs unveränderten Gelenke des Stiftarms und
die Ausrichtung der Gegenwand. Eine bloße Visuallinie oder ein aus
dem früheren Versuch übernommener bewegter Stift genügt diesem Test nicht.
Geometrie-, Kollisions- und Kontaktphysiknachweise sind getrennt.
