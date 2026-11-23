# Mit der Stiftspitze Kontakt suchen

`seek_contact` führt einen kraftabhängigen Schritt zwischen zwei geplanten
Bewegungen aus. Die rechten Arme halten den Karton in der bekannten
Zeichenpose. Der Arbeitsarm fährt zur Vorposition, tastet entlang der
Flächennormale und zieht sich vom erreichten Zustand zurück. Anschließend
parkt er und die Haltegruppe setzt den Karton ab.

## Rezept

[Erstes Aufgabenrezept](../uwa_cell_tasks/config/seek_contact.json).
`uv_m` liegt im lokalen Flächenrahmen des zentrierten Werkstücks,
`tool.length_m` misst von Tool0 bis zum äußersten Punkt entlang +Z.
Der Gazebo-Adapter nutzt den linken vorderen Arm der Zeichenpräsentation.
Der erste Lauf verwendet 5 mm Vorabstand, 8 mm Suchweg, maximal 20 mm/s und
eine Auslöseschwelle von 2 N. Die Werte sind Simulationsparameter.
Das Profil des Home-Laufs stellt für den Transport bis zu 1 rad/s je
Armgelenk und den im Lauf verwendeten Pad-Reibwert 20 ein.

## Bedienung auf ROSmini

Aus dem Workspace mit einem **neuen** Szenen- und Laufverzeichnis arbeiten.
Die beiden Szenen nacheinander verwenden, da der Gazebo-Weltname gemeinsam ist.

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
base="$UWA_WS/setup/tasks/house_drill_home_20261120_01"
case_dir="$UWA_WS/setup/tasks/seek_contact_example/nominal"
skill="$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_tasks/config/seek_contact.json"
ros2 run uwa_cell_tasks cell_task prepare --output "$case_dir/scene" \
  --layout "$base/layout05.yaml" --config "$base/profile.yaml" \
  --drawing-recipe "$base/fixed-drawing-recipe.json" --skill-recipe "$skill"
ros2 launch uwa_cell_tasks grasp.launch.py scene:="$case_dir/scene" \
  layout:="$base/layout05.yaml" namespace:=/uwa_grasp_seek_example
```

Im zweiten Terminal dieselbe Umgebung und die Variablen setzen und starten.

```bash
ros2 run uwa_cell_tasks cell_task run --scene "$case_dir/scene" \
  --output "$case_dir/run" --namespace /uwa_grasp_seek_example \
  --layout "$base/layout05.yaml" \
  --reference "$UWA_WS/setup/tracking/models/carton_avocado_v1/reference.npz"
```

Die drei bestehenden Bild-/Planreviews über
`tools/inspect_manipulation_review.py` bedienen. Für die vorstehende
Oberfläche bei `prepare` zusätzlich `--surface-offset-mm 2` angeben.
Ein lokaler 24-mm-Quadrataufsatz gehört zur Gazebo-Kontaktgeometrie.
Beide Versuche verwenden dieselbe Sollwand und dasselbe Skill-Rezept.

## Kraft und Ergebnis

Das feste Sensorgelenk zwischen Tool0 und Stift liefert die übertragene
Kraft in seinen eigenen Achsen. Positives Z misst die vom Arm auf das
Werkzeug übertragene Druckkraft. In der Vorposition wird diese Komponente
tariert. Das erste gültige 10-ms-Fenster oberhalb oder auf der Schwelle
löst die Stornierung des laufenden Suchziels aus. Der gemeinsame
Controller behält die Halterziele. Erst nach seiner Abschlussantwort wird
der Rückzug aus den tatsächlich gemessenen Gelenkpositionen geprüft und gesendet.

`seek-result.json` enthält Ergebnis, Treffer und Übergabepose im zentrierten
Werkstückrahmen, Spitzendruckkraft und Nachlauf. `seek-force-trace.json`
enthält Kraft und TCP-Weg mit Zeitstempeln aus der Physik. Der direkte
Spitze-Wand-Kontakt wird separat ausgewertet. Ein regulär abgefahrener
Suchweg ohne Schwellentreffer beendet den Schritt mit `travel_exhausted`.
Fehlende Messabdeckung, Bedienabbruch und Controllerfehler haben eigene
Ergebnisse. Die nächste Bewegung setzt einen bestätigten Treffer voraus.
