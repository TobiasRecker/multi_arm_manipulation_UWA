# Virtuelle Trennwände und parallele Scanwege

Stand:12.11.2026. Die vorhandenen Scanwege des neuen Kartons wurden offline
analysiert; keine reale Bewegung, Kameraaufnahme oder Controlleränderung.
Das Werkzeug betrachtet **diese Wege**, nicht den gesamten erreichbaren Arbeitsraum.

## Ergebnis für den aktuellen Entwurf

Quelle: `setup/digitization/five_camera_design_20261112/new_carton_plan_current/`.
Alle68Kollisionskörper der vier Arme einschließlich Greifer und Kameras enthalten.
Die Auswertung verwendet20mm geforderten Abstand zwischen den Modellhüllen.
Dieser technische Startwert ist keine gemessene Schranke realer Montagefehler.

| Arm | Größte Überschreitung einer mittigen Paar-Trennebene über die Scanwege |
|---|---:|
| links vorne |0mm |
| links hinten |höchstens34,1mm Richtung rechts hinten |
| rechts vorne |0mm |
| rechts hinten |höchstens60,4mm Richtung links hinten |

Dies sind obere Schranken einschließlich Bewegung zwischen den Prüfpunkten.
An den tatsächlichen Prüfpunkten:32,5mm beziehungsweise58,9mm. Die Grenzkörper
sind hier Greiferfinger. Eine Ebenenüberschreitung ist weder automatisch eine
Kollision noch eine Freigabe, die Prüfung wegzulassen.

**Grundpositionierung:** Alle sechs Armpaare im Modell unabhängig vom Zeitversatz
getrennt. Fünf Paare trennen sich entlang der Basisverbindungsrichtungen; für
das hintere Paar ist eine gedrehte räumliche Ebene erforderlich. Kleinste
nachgewiesene Abstandsuntergrenze:28,6mm. Die vier Arme dürfen in diesem geprüften
Modell ihre unveränderten Anfangswege gleichzeitig beziehungsweise verzögert
ablaufen, auch wenn ein Arm unterwegs hält. Kein Hardwarebetrieb daraus aktiviert.

**Zusatzansichten:** Für das hintere Paar fehlt der20mm-Nachweis. Auch nach
Aufteilung in289Einzelkörperpaare bleiben linke Greiferfinger gegenüber dem
rechten `wrist_2_link` ungeklärt. Die konservativen Hüllen reichen dort nicht
zum Nachweis. Das ist **keine nachgewiesene reale oder Modellkollision**.
Alle übrigen Armpaare bleiben getrennt.

Daraus ergibt sich der vorbereitete Prüfablauf:

1. Alle vier Anfangswege parallel, anschließend Stillstand aller Arme und Foto.
2. Links vorne, links hinten und rechts vorne parallel durch ihre Zusatzansichten.
   Nach jeder Runde vollständiger Stillstand, dann Fotos; fertige Arme halten.
3. Rechts hinten anschließend durch seine vier Zusatzansichten. Die anderen
   drei stehen an ihren letzten, im ursprünglichen Plan geprüften Stellungen.

Die Reihenfolge des ungeklärten Paars links hinten → rechts hinten bleibt
vollständig erhalten. Nur nachgewiesen unabhängige Armketten werden umgeordnet;
alle Gelenkpunkte und Zeitparameter bleiben unverändert.

**Reine Modell-Fahrzeit:193,5 →80,9s, rund58% weniger.** Fotos, Stillstandszeiten,
Kommunikation und tatsächliche Controllergeschwindigkeiten sind nicht enthalten.
Es handelt sich um einen nicht ausführbaren Prüfplan, noch keinen integrierten
parallelen Hardwareablauf.

## Prüfmethode

Für jedes der sechs Basenpaare wird zunächst eine vertikale Ebene in der Mitte
zwischen seinen Basisursprüngen gebildet. Ihre horizontale Normale zeigt von
ArmA nachArmB. Für jeden Kollisionskörper wird über die komplette Trajektorie
sein größter Vorstoß Richtung dieser Ebene bestimmt.

- Meshes: alle Extrempunkte der originalen Kollisionsgeometrie, Skalierung und
  Kollisionsursprung berücksichtigt; konvexe Reduktion erhält dieselben
  Richtungsmaxima. Keine bloße TCP-/Gelenkpunktprüfung.
- Boxen, Kugeln und Zylinder: analytische Richtungsgrenzen. Für die zusätzliche
  Hüllensuche werden konservative Primitive-Einhüllungen verwendet.
- Exakte Richtungsmaxima an den Prüfpunkten werden von konservativen Grenzen
  zwischen den Punkten unterschieden. Die ursprünglichen monotonen quintischen
  Verbindungen einschließlich Position/Geschwindigkeit/Beschleunigung werden
  überprüft. Geänderte/inkonsistente Pfade werden abgewiesen.
- Zwischen zwei Punkten gilt pro Körper die Verschiebungsschranke
  `0,5 × Summe(R_j × |Δq_j|)`. `R_j` begrenzt den Abstand aller Körperpunkte
  von der jeweiligen Gelenkachse über die nachfolgenden Segmentlängen.
  Beim aktuellen Entwurf liegen die größten Zusatzpolster pro Arm bei etwa4–7mm.
- Getrennte vollständige Bewegungsräume beweisen die Modelltrennung für **beliebige
  relative Fortschritte**, statt nur bei gleichzeitigem Start oder gleichen Zeiten.
  Anfangs-/End-/Haltestellungen sind enthalten.
- Falls die mittige Ebene nicht genügt: versetzte/gedrehte räumliche Ebene suchen,
  dann gegebenenfalls Hüllen der einzelnen Kollisionskörper paarweise prüfen.
  Die direkte Stützabstandsprüfung einschließlich Zwischenpunktpolster liefert
  den Nachweis; ein erfolgreicher Optimierer allein genügt nicht.

Eine überlappende Projektion oder konvexe Hülle liefert lediglich „nicht bewiesen“.
Daraus wird keine physische Kollision erfunden. Umgekehrt ist das Ergebnis an
exakte Quellwege, URDF und Mesh-Hashes gebunden; neue Wege oder neue Montagen
benötigen eine neue Analyse.

## Benutzung

Aus dem Workspace nach Build:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control scan_separation \
  --plan /absolut/zum/Scanplan/report.json \
  --clearance-mm 20 \
  --output /absolut/zur/Analyse
```

Ausgabe:

- `separation.json`: Paar-/Phasenwerte, Extremstellen, Modellbindungen und Grenzen.
- `separation.md`: lesbarer Bericht.
- `parallel_review.json`: nicht ausführbarer Ablauf mit Verweisen auf unveränderte
  Quellschritte, Stillstands-/Fotobarrieren und Bewegungszeitvergleich.

Statische Übersicht:

```bash
python3 src/multi_arm_manipulation_UWA/tools/preview_scan_separation.py \
  --analysis /absolut/zur/Analyse/separation.json \
  --output /absolut/zur/Analyse/preview.png
```

Die Grafik zeigt konservativeXY-Hüllen einschließlich Zwischenpunktpolster und
je10mm Abstandspuffer. Eine Überlappung in der Draufsicht kann räumlich dennoch
getrennt sein. Die räumliche Prüfung im Bericht ist entscheidend.

## Grenzen und Prüfnachweise

Welt-/Basis-/Werkzeuggeometrie teilweise vorläufig. Greifer halten die ausdrücklich
aufgelisteten Modellwerte; es wurden keine realen Greiferstellungen erfasst.
Kabel, Personen und das bisher nur visualisierte Stativ fehlen im Kollisionsmodell.
Die20mm sind keine bewiesene Gesamtreserve für diese Modellabweichungen.
Selbst-/Tisch-/Objektprüfung und nativeUR-Sicherheit bleiben erhalten.
Vor einer echten Fahrt sind aktuelle Startzustände und konkrete Wege zu prüfen;
keine Safety-Quittierung und keine automatische Änderung der bestehenden Steuerung.

Build und12neue Tests plus bestehende Planungs-/Parktests geprüft: vollständige
Körper statt TCP, gekrümmte Zwischenbewegung, Meshskalierung, versetzte/gedrehte
Ebene, Zeitversatz, Einzelkörperhüllen, Quellpfadänderungen und Erhaltung der
Reihenfolge ungeklärter Paare. Ursprüngliche Arm-/Kameradienste nicht verändert.
Daten unter `setup/digitization/five_camera_design_20261112/separation_review/`;
installierter CLI-Lauf separat unter `separation_installed/`.

Die Scan-RViz-Vorschau verwendet jetzt Domain74; Domain73 bleibt für die separate
LR-Kalibriervorschau frei. Es wurde keine Vorschau-/Hardware-Instanz neu gestartet.
