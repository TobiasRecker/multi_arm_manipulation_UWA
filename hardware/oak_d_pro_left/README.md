# Tischhalterung für das 19-mm-Kamerarohr

Stand 2026-11-19. Links an der Roboterzelle soll eine OAK-D Pro AF (RVC2)
auf dem vorhandenen **1.200 mm langen Edelstahlrohr Ø19 mm** sitzen.
Der Fuß nutzt die vier vorhandenen Tischbohrungen und wird durch die
Tischplatte mit Scheiben und Muttern verschraubt. Dieser Entwurf ersetzt
den Vorentwurf mit 40-mm-Vierkantmast und Tischklemmen.

[CAD-Vorschau mit Lochbild](rohrhalter-vorschau.png) ·
[STEP für Onshape und andere CAD-Programme](rohrhalter-19mm.step) ·
[STL für den Druck](rohrhalter-19mm.stl) ·
[STL für die Passprobe](passprobe-19mm.stl)

## Geometrie

| Merkmal | Maß |
|---|---:|
| Tischbohrungen laut STEP-Vorlage | 4 × Ø9 mm, Raster 98 × 98 mm |
| Rohrachse zur nächstgelegenen Schraubenreihe | 67,45 mm in Richtung Tischkante, mittig zwischen den Schrauben |
| Außenmaße des Fußes | 124 × 201 × 145 mm |
| Höhe der Führung über Tisch | 145 mm |
| Einstecktiefe mit integriertem Anschlag | 141 mm |
| Abstand der beiden M5-Klemmschrauben | 113 mm |
| Innen-Ø an beiden Klemmzonen | 19,4 mm |
| Innen-Ø zwischen den Klemmzonen | 21,4 mm |

Zwei Rippen stützen die Hülse quer zur Rohrachse in Richtung der beiden
nahen Schraubpunkte. Die mittlere Rippe und die gegabelten Stege binden
die hintere Schraubenreihe an. Die vier Schraubauflagen sind 8 mm dick.
Zwei M5-Schrauben ziehen die geschlitzten Klemmbereiche am Rohr zusammen.
Die entlastete Mittelbohrung erleichtert das Einsetzen des Rohrs über
die gesamte Länge. Ein Einlaufkonus hilft beim Ansetzen.

Die ursprüngliche Führung war 50 mm tief. Der neue Fuß hat mit
141 mm Einstecktiefe rund die 2,8-fache Führung und mit 203,5 cm³
gegenüber 289,8 cm³ etwa 30 % weniger CAD-Volumen. Der tatsächliche
Filamentbedarf hängt von Wandlinien, Füllung und Material ab. Die lange
Führung begrenzt das Spiel an der Einspannung. Oberhalb bleiben rund
1,06 m freies Rohr, dessen Biegung von der Wandstärke abhängt.

## Passprobe und Montage

1. **Tischseite prüfen.** Abstand der kantennahen Bohrungsreihe zur Kante
   direkt messen. Mindestens **87 mm** sind erforderlich, damit die
   Unterseite am Hülsenfuß vollständig aufliegt. Für bündigen Aufbau
   einschließlich der Klemmohren sind **90 mm** erforderlich. Bei 100 mm
   bis zur nahen Reihe liegt die Rohrachse etwa 32,6 mm innerhalb der
   Kante. Unter der Platte Platz für die Scheiben und Muttern prüfen.
2. **Kurze Passprobe drucken.** Das 24 mm hohe Prüfstück entspricht
   dem Klemmbereich. Rohrdurchmesser an mehreren Stellen und in zwei
   Richtungen messen und dann ausprobieren, ob sich das Rohr von Hand
   einschieben und mit einer M5-Schraube spielfrei klemmen lässt.
   Der Standard von 19,4 mm ist ein Druckstartwert. Bei Bedarf die
   Bohrung mit `--bore` anpassen.
3. **Fuß aufrecht drucken.** Die flache Montagefläche liegt in der STL
   bei Z = 0. Für einen PETG-Prototyp sind 0,2 mm Schichthöhe, 6
   Wandlinien und 40 % Füllung Startwerte. Im Slicer die gerampten
   Klemmohren und horizontalen M5-Löcher kontrollieren. Die M5-Löcher
   haben oben ein spitzes Dach für die Druckbarkeit. Bohrung und Schlitz
   nach dem Druck vom Grat befreien.
4. **Durchschrauben und klemmen.** Bei bestätigten Ø9-mm-Tischlöchern
   sind vier M8-Durchgangsschrauben mit Scheiben oben und breiten Scheiben
   oder Gegenleisten unten vorgesehen. Schraubenlänge nach gemessener
   Tischstärke plus 8 mm Fuß sowie Scheiben und Sicherungsmuttern wählen.
   Für die Rohrklemmung sind zwei M5 × 45 mm mit Scheiben und
   Sicherungsmuttern vorgesehen. Beide gleichmäßig anziehen, bis das
   Rohr spielfrei sitzt. Die Ohren sollen dabei Abstand voneinander
   behalten. Nach dem Setzen der Verbindung erneut auf Spiel prüfen.
5. **Sitz und Freiraum prüfen.** Bei stillstehenden Armen zuerst das Rohr
   allein montieren. Seitliches Spiel am Fuß sowie Durchbiegung am
   Rohrende getrennt prüfen. Vor Montage der Kamera den Freiraum von
   Mast und Klemmen zu den linken URs prüfen. Erst mit stabiler mechanischer
   Lage Kamerakopf und Zellenregistrierung festlegen.

Das tatsächliche Lochbild, die Passung, die Tragfähigkeit der Tischplatte
und die Schwingung im Zellbetrieb sind vor Ort noch zu prüfen.
Der Kamerakopf am oberen Rohrende ist ein eigener Arbeitsschritt.
Die vorhandene [Kameralochschablone](oak-rear-hole-template.stl) bildet
weiterhin das Rückseitenraster der OAK-D Pro AF ab. Der frühere
[USB-Sattel](usb-cable-saddle.stl) passt auf das 40-mm-Vierkantprofil
des alten Entwurfs.

## CAD und Reproduktion

Koordinaten der Vorlage `Rohrhalter.step` gedreht in Drucklage
`(x, y, z) = (STEP x, STEP z, −STEP y)`. Unterseite Z = 0.
Tischlochachsen bei X = ±49 und Y = −13 bzw. +85 mm.
Rohrachse bei X = 0, Y = −80,45 mm. Die Tischkante ist in der Vorlage
nicht modelliert. Der STEP-Export und beide STL-Volumenkörper wurden
eingelesen und auf Gültigkeit bzw. Geschlossenheit geprüft.

Das Modell entsteht mit OpenCascade aus
[make_table_mount.py](make_table_mount.py). Auf ROSmini vom Workspace aus:

```bash
.venvs/oak-model/bin/python \
  src/multi_arm_manipulation_UWA/hardware/oak_d_pro_left/make_table_mount.py \
  --bore 19.4 --output /tmp/uwa-oak-mount
```
