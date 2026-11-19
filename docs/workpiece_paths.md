# Werkzeugbahnen relativ zum Werkstück

Ein Werkstück, das von zwei Armen gehalten wird, hat einen gemeinsamen
Werkstückframe. Positionen und Orientierungen einer Werkzeugbahn beziehen
sich darauf. Der dritte Arm erhält daraus seine Werkzeugposen, während
beide Greifer ihre festen Objekt-zu-TCP-Transformationen behalten.

Für jede ebene Arbeitsfläche genügen der Ursprung, die Richtung `u`
und die Einheitsnormale nach außen. `v = normal × u`. Die Spitze des
Modellwerkzeugs zeigt mit lokalem +Z in Richtung `−normal`. Positionsdaten
sind in Metern. Der Basisframe der Roboter beschreibt anschließend nur,
wie der aktuelle Werkstückframe in der Zelle steht.

| Bewegungsart | Geometrische Referenz | Beispiele |
|---|---|---|
| Oberfläche abfahren | Punkte `(u,v)`, gerade Segmente oder Kreis | Zeichnen, Kleberaupe, Farbe, Dichtstoff, Fensterschaum entlang einer Fuge |
| Führen entlang einer Bearbeitungslinie | Kontur und Werkzeuggestalt relativ zum Werkstück | Sägen oder spanende Bearbeitung mit einer später definierten Eingriffstiefe und Werkzeugorientierung |
| Axial zustellen | Ein Punkt `(u,v)`, Außennormale, Vorabstand und Tiefe | Ansetzen und axialer Vorschub zum Bohren oder Schrauben |
| Frei verfahren | Ausgangspose, geprüfter Freiraum und Zielpose | Anfahren, Freifahren, Parken, Wechsel auf eine andere Fläche |

Beim Fräsen oder Sägen kann die Kontur einen zusätzlichen Tiefenversatz
und eine prozessabhängige Werkzeugorientierung brauchen. Beim Einschäumen
eines Fensters kann die Tasche oder Fuge über mehrere Flächen laufen.
Solche Fälle teilen die Werkstückreferenz und das Prinzip der Bausteine.
Die erste Implementierung des Boxpiloten nimmt jeweils einen Linienzug
in einer seiner drei ebenen Flächen entgegen.

## Ausprobieren im Boxpiloten

Mit `--tool-paths DATEI` ersetzt eine Folge von Flächenpunkten den bisherigen
Kreis auf ausgewählten Flächen. Flächen ohne Eintrag behalten ihren
Kreis. Neue Punktfolgen benötigen keine Änderung im Planer, Viewer oder
FK-Audit. Der [Beispieldatensatz](examples/nikolaus_surface_path.json)
beschreibt die acht Linien des Hauses. Für `z_min` zeigt die Normale in
Objekt−Z und `v` damit in Objekt−Y.

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  src/multi_arm_manipulation_UWA/tools/box_drawing_pilot.py run \
  --source setup/research/offline-carton-sides-20261117/standard/smoothed/result.json \
  --output setup/tasks/workpiece_paths_new/run01 \
  --faces y_max z_min y_min --radius-mm 22 \
  --tool-paths src/multi_arm_manipulation_UWA/docs/examples/nikolaus_surface_path.json \
  --replan-return
```

Der Planer fährt die Kanten über dieselbe Flächenpräsentation und
dichte Modellprüfung ab wie die bisherigen Kreise. Beim offenen Zug
erfolgt der Rückzug am tatsächlichen Endpunkt. Für den bestehenden
Übergangsvertrag fährt der Arm im Sicherheitsabstand zur Vorpose
zurück. Diese freie Bewegung ist im Artefakt separat bezeichnet.
Die eingebettete Bahn stammt aus den tatsächlichen Modellpunkten.
Ein Hash bindet die Formdaten an die Episode. Der separate
`verify_box_drawing_pilot.py` prüft die Kanten, Anschlüsse, stationären
Halter während des Auftrags und Rückkehr aus den Gelenkinterpolanten.

`--replan-return` sucht aus der tatsächlichen letzten Vorpose eine
alternative Bahn für den freien Arbeitsarm. Die Box folgt der
ursprünglichen Rückweggeometrie. Der Arbeitsarm hält sich am Anfang
an die bewährte Bahn und wechselt nach einer geprüften Stelle gleitend
in seine Parkpose. Die nächste Boxdrehung läuft mit geparktem Arm.
Kandidaten müssen im Modell kürzer sein und dieselben Kollisions-,
Griff- und Zeitprüfungen bestehen. Die tatsächliche Auswahl und
Ablehnungen stehen in `planning_diagnostics`. Bei ausgeschöpfter
Suche wird der ursprüngliche Rückweg vollständig geprüft und verwendet.

## Axialer Zustellbaustein

`AxialFeed.reference(frame)` liefert vier geometrische Referenzen.
Vorpose bei `+Abstand`, Oberfläche bei `0`, Zieltiefe bei `−Tiefe`
und Wiederkehr zur Vorpose. Die Werkzeugachse bleibt währenddessen
auf `−normal`. Die Ausrichtung funktioniert auch für geneigte Flächen.
Diese Referenzen beschreiben die gewünschte Geometrie. Der aktuelle
Boxpiloten-Adapter hat einen virtuellen Stift und nimmt in der
Aufgabendatei Oberflächenlinien an.

Für Kleben, Schäumen, Sägen, Bohren und Schrauben kommt je ein
Prozessbaustein dazu. Er koppelt den Werkzeugzustand an den
Bahnfortschritt, etwa Dosieren an Vorschub oder Schraubendrehung an
axialen Weg. Geometrische Kollisionsprüfung unterscheidet den
freigegebenen Kontaktbereich der Werkzeugspitze von Werkzeugkörper,
Halterpartnern und Umgebungsobjekten. Prozesse brauchen darüber hinaus
Erfassung der tatsächlichen Werkstückpose und Werkzeugkalibrierung,
prozessabhängige Kraft-/Drehmomentgrenzen und eine definierte Reaktion
auf Abweichungen. Der Baustein für irreversiblen Eingriff erhält einen
eigenen Freigabepunkt. Aufgezeichnete Zeiten, beobachtete Kräfte und
Abweichungen lassen sich wie bisher phasenbezogen dokumentieren.
