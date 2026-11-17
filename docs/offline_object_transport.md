# Vier Arme transportieren einen Karton

Stand17.11.2026: erster deterministischer Offline-Transport aus der letzten
[Seitenmitten-Greifkonfiguration](offline_carton_sides.md), ergänzt um eine
gradientengeführte Anpassung der Objektorientierung. Lernverfahren bleiben
zurückgestellt. Alle vier Arme behalten feste Objekt→TCP-Transformationen.

## Ergebnis ansehen

Aus dem Workspace:

```bash
xdg-open setup/research/offline-object-transport-20261117/final/viewer.html
```

Die eigenständige HTML-Datei benötigt keinen Server. **Case** wählt Idealtransport
oder Zusatzabstandsversuch. **Play preview**, Zeitschieber, Ziehen/Drehen und
Mausrad/Zoom funktionieren wie bisher. Wiedergabe startet mit echter Modellzeit1×.
Die Kiste bewegt sich jetzt zusammen mit den vier Armen. Objektachsen zeigen
die Orientierung; die weiße Linie zeigt die unveränderte Mittelpunktbahn.

| Eigenschaft | Idealprofil | Zusatzabstandsversuch |
|---|---:|---:|
| Hub / horizontaler Versatz | 10cm / 20cm Welt−X | identisch |
| Dauer | 17,532s | 15,332s |
| maximale zusätzliche Hochachsendrehung | 0° | 6,017° |
| Änderung der Mittelpunktbahn | 0mm | 0mm |
| Mindestabstand aller sechs Arm-Hüllpaare | 32,676mm | 31,321mm |
| geforderter Abstand | überall20mm | 20–60mm, entlang der Bahn variabel |
| kleinster Überschuss über die jeweilige Forderung | 12,676mm | 0,499mm |
| kleinster skalierter Einzelarm-Singulärwert | 0,08878 | 0,13015 |
| geprüfte Zeitpunkte, höchstens5ms Abstand | 3510 | 3070 |

Die Richtung hat der Nutzer ausdrücklich anhand Erreichbarkeit wählen lassen.
Welt−X besteht die kontinuierliche IK-Fortsetzung aus dem vorhandenen Griff.
Welt+X/±Y scheitern mit diesem Solver und diesen Startzweigen. Das beweist keine
globale Nichterreichbarkeit mit anderen Greifkonfigurationen.

Das Idealprofil ist bereits ausreichend frei und bleibt deshalb unverändert.
Der zweite Fall fordert absichtlich mehr Abstand:
`d_required(s) = 0.020 + 0.040 sin²(πs)` in Metern. Ohne Drehung verletzt die
Bahn diese Forderung an97/241 geometrischen Prüfpunkten. Mit Drehung besteht
sie. Der global kleinste Abstand kann dennoch kleiner werden, weil dort eine
geringere Forderung gilt. Es wurde keine zuvor kollidierende Bahn gerettet.

Die etwas kürzere Dauer des Drehversuchs entsteht aus den veränderten Gelenk-
verläufen und deren Ableitungsgrenzen. Sie ist kein Nachweis einer zeitoptimalen
Lösung; das Optimierungsziel minimiert Rotation und deren Rauigkeit.

## Gemeinsame Kinematik und Suchrichtung

Das Objektframe liegt im Kartonmittelpunkt. Das ursprüngliche STL-Frame liegt
an einer unteren Ecke und wird nur für die Meshposition verwendet. Drehungen
erfolgen dadurch tatsächlich um den Mittelpunkt.

Für jeden Arm wird aus seiner geometrischen TCP-Jacobimatrix `J_i` die Beziehung
`J_i qdot_i = A_i V_O` aufgebaut. Alle Geschwindigkeiten sind in Weltachsen:
`V_O = [v; ω]`, `A_i = [I, −skew(p_TCP_i−p_O); 0, I]`. Bei regulärem `J_i`
liefert `K = stack(solve(J_i,A_i))` eine24×6-Abbildung vom Objekttwist auf die
Gelenkgeschwindigkeiten. Die Grifftransformationen bleiben unverändert.

Die Kugelhüllen liefern analytische Punkt-Jacobimatrizen. Aus dem jeweils
nächstgelegenen Kugelpaar folgt der lokale Abstandsgradient:
`∂d/∂X = nᵀ (J_point_A − J_point_B) K`. Dessen sechste Komponente sagt, ob eine
kleine Drehung um Welt+Z den Abstand vergrößert oder verkleinert. Beim Wechsel
des nächstgelegenen Paars ist der Mindestabstand nur stückweise differenzierbar.

Die Yaw-Bahn ist ein quintischer B-Spline mit sechs freien inneren Koeffizienten;
Start-/Endwinkel sind null. Koeffizientengrenzen±15° begrenzen über die
Konvexhülleneigenschaft auch den gesamten Winkelverlauf. SLSQP nutzt die
analytischen Gradienten aller sechs Arm-Paarabstände,121Kollokationspunkte und
0,5mm Zusatzpuffer. Der gezeigte Zusatzversuch konvergiert in19Iterationen.

Das ist ein lokaler erster Optimierer: Translation, Basisbewegung und IK-Zweig-
wechsel sind noch keine Suchvariablen. Objekt-/Umweltkollisionen und
Singularitätsindikatoren werden als Abnahmeprüfung behandelt, derzeit noch
nicht als differenzierbare Nebenbedingungen. Bei Verletzung wird das Ergebnis
verworfen. Ein Erfolg des Optimierers allein genügt ausdrücklich nicht.

## Glättung und Prüfung

Je Bewegungsphase werden101IK-Konfigurationen aller24Gelenke gemeinsam
interpoliert. Ein einziges C3-Zeitgesetz pro Phase sorgt für synchronen
Griffverbund. An den geometrischen Knicken zwischen Hub, Transfer und Senken
stehen alle Arme kurz vollständig still; Geschwindigkeit, Beschleunigung und
Ruck sind dort null. Experimentgrenzen:0,45rad/s,0,4rad/s²,2rad/s³.

Die tatsächliche24D-Interpolation wird geprüft, nicht nur ihre IK-Stützstellen:

- FCL mit bewegtem Kartonmesh, vorhandener Umwelt-/Selbstkollisionsgeometrie;
  kein fester Kartonrest und keine neuen pauschalen Kontaktausnahmen.
- Alle sechs Arm-Hüllpaare, Gelenkgrenzen und feste Objekt→TCP-Transformationen.
- Skalierte Einzelarm-Jacobimatrizen `diag(2,2,2,1,1,1) J_i`, entsprechend
  einer charakteristischen Länge0,5m, mit experimenteller Mindestschwelle0,05.
- Analytische Gelenkableitungsgrenzen über Bernstein-Hüllen und Kettenregel;
  zusätzliche dichte Auswertung der Ableitungen.

Der größte numerische Griffschlussfehler beträgt2,47e−9m. Das beschreibt
lediglich die Konsistenz des Rechenmodells. Die unabhängige Prüfung vergleicht
an Start/Mitte/Ende beider Varianten alle sechs Poseableitungen mit zentralen
IK-Differenzen: maximalerK-Fehler2,63e−9, Abstandsgradientfehler1,97e−9.
Ein absichtlich20mm abgesenkter Karton kollidiert korrekt mit dem Tisch und
ist nach Rücksetzen wieder frei.

Ein früherer Optimierungsversuch mit61Punkten ohne Zusatzpuffer bestand die
feinere241-Punkt-Prüfung nicht. Er bleibt als negatives Ergebnis unter
`optimization-0.04.json` erhalten. Die abschließende≤5ms-Prüfung des verfeinerten
Verfahrens besteht. Diskrete Prüfung ist dennoch kein kontinuierlicher Beweis.

Die Singularwerte beschreiben hier primär die Kondition der einzelnen
Arm-Jacobimatrizen. Sie sind weder eine universelle Parallelroboter-
Singularitätsqualifikation noch ein Maß für Traglast, Griffsteifigkeit oder
innere Kräfte. Die vollständige Zwangs-/Kraftstruktur bleibt separat zu betrachten.

## Reproduktion

Vom Workspace aus, nach Build von `uwa_cell_motion`:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/plan_object_transport.py \
  setup/research/offline-carton-sides-20261117/standard/smoothed/result.json \
  --output-dir setup/research/offline-object-transport-repeat
python3 src/multi_arm_manipulation_UWA/tools/verify_object_transport.py \
  setup/research/offline-object-transport-repeat/result.json \
  --output setup/research/offline-object-transport-repeat/independent-check.json
```

Das Ausgabeziel muss neu sein. Standardmäßig wird neu optimiert. Optional
`--optimization-file setup/research/offline-object-transport-20261117/optimization-refined.json`
verwendet bereits ermittelte Koeffizienten als Kandidat; die neue IK-, Grenzen-,
Kollisions- und Trajektorienprüfung bleibt vollständig erforderlich.
`result.json` bindet Eingabe, Modelle, Meshes und verwendeten Planungscode über
Hashes. Originalquelle und ihre referenzierten Vorstufen müssen erhalten bleiben.
Die Ergebnisse bleiben ausdrücklich `executable: false`.

Build und35Tests in fünf gezielten CTest-Suiten (`motion_object_transport`,
`motion_smooth_paths`, `motion_carton_sides`, `motion_carton_paths`,
`motion_path_speed`) bestehen. Der Browser prüft28Bedien-/Darstellungsfälle;
Kontrollbild und Prüflog liegen beim Endartefakt. Prozesslogs:
`setup/logs/uwa-object-transport-*`.

## Reichweite und nächster Ausbau

Weiterhin offene Finger und hypothetisch starre Griffe, feste Basen,
nominal3mm Abstand des Kartons vom Tisch an Start und Ende. Keine Kontaktphysik,
kein tatsächlich getragenes Objekt und kein physisch unterstütztes Absetzen.
FCL verwendet die vorhandenen Kollisionsgeometrien; einige visuelle Finger-/
Kameralinks besitzen dort keine eigenen Kollisionsmeshes. Die Arm-Paarprüfung
ergänzt die vorhandenen Kugelhüllen, ersetzt aber keine vollständige physische
Geometriekalibrierung. Keine ROS-Knoten oder Hardwarebewegungen gestartet.

Die alte konservative Stoppreservediagnostik wird bei allen Zeitpunkten
überschritten und separat in der Vorschau angezeigt. Sie ist keine geometrische
Kollision; ihr Bestehen wird durch diese Offlineplanung nicht behauptet.

Der nächste Ausbau kann dieselben Gradienten auf kleineXYZ-Abweichungen in
einem Objektkorridor anwenden, mit starker Strafe für Abweichung vom Idealprofil.
Dazu kommen differenzierbare Umweltabstände und gezielte engere Beispiele.
Bewegte Basen erweitern später die Kettenkinematik und Planungsvariablen.
