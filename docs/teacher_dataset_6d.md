# 3D- und 6D-Lehrerbewegungen für Behavioral Cloning

Stand: 17.11.2026. Erweiterung des [Zweiarm-Lehrers](two_arm_object_teacher.md).
Zunächst Datengeneration und Prüfung; noch kein Netztraining.
Die anschließende [Erweiterung mit deutlich unterschiedlichen Startlagen
und IK-Konfigurationen](teacher_start_diversity.md) adressiert den nahezu
gleichen Ausgangszustand dieses ersten Piloten.

## Empfehlung zur gemeinsamen Policy

Ein gemeinsames Netz mit einer sechsdimensionalen Bewegungsaktion ist der
erste Vergleichskandidat. Translation und Rotation wirken auf dieselben
Armstellungen und Kollisionsabstände. Auch wenn nur eine Verschiebung
gewünscht ist, kann eine vorübergehende Drehung der passende Ausweg sein;
umgekehrt kann eine gewünschte Drehung zusätzlichen Hub benötigen.

Deshalb drei **Referenzaufgabenklassen**, aber durchgehend sechs erlaubte
Korrekturfreiheiten: `translation3d`, `rotation3d`, `mixed6d`. Reine Aufgaben
trainieren Nullkomponenten und erleichtern die Diagnose. Drei unabhängige
Netze sind eine spätere Ablation, falls das gemeinsame Modell messbar
schlechter lernt. Eine harte Umschaltung zwischen Netzen bräuchte zusätzlich
eine Regel für Mischfälle und Übergänge. Dies ist eine technische Empfehlung,
keine bereits durch Training belegte Überlegenheit.

Planner-Demonstrationen in eine gemeinsame Policy zu destillieren entspricht
beispielsweise dem Grundaufbau von [Neural MP](https://neuralmotionplanner.github.io/).
Dessen Ergebnisse gelten nicht automatisch für unseren geschlossenen
Zweiarm-Griff. Auch dort ist eine zusätzliche Optimierungs-/Prüfstufe Teil
des Ansatzes; BC allein ist kein Kollisionsfreiheitsnachweis.

## Festgelegter Pilot

`tools/generate_teacher_dataset.py` erzeugt deterministisch mit Seed20261117:

| Referenzklasse | Familien | Varianten je Familie | Aufgaben | Train / Validierung / Test |
|---|---:|---:|---:|---:|
| 3D-Translation |4|2|8|4 /2 /2|
| 3D-Rotation |4|2|8|4 /2 /2|
| Gemischte 6D-Bewegung |8|2|16|8 /4 /4|

Alle drei aktiven Translations- bzw. Rotationskomponenten werden gleichzeitig
variiert. Ziel- und Auslenkungsrotationsvektor sind nicht parallel: damit
ändert sich die Rotationsachse über den Verlauf. Rotationen sind Weltachsen-
Rotationsvektoren auf SO(3), keine unabhängig addierten Eulerwinkel.
Die Rotation erfolgt um den Kartonmittelpunkt.

Die Aufgaben verwenden weiterhin linearen Zielfortschritt plus eine
`sin²(πs)`-Zwischenauslenkung. Start und Ziel bleiben fest, die Zwischenreferenz
ist weich. Dies sind bewusst entworfene, ähnliche Bahnformen, keine umfassende
Abdeckung aller 6D-Trajektorien. Für Rotation und Mischfälle gibt es kleinere
und stärkere Auslenkungen bis ungefähr100° um Welt-Y; manche können scheitern.
Zielversätze liegen bei wenigen Zentimetern. Startverschiebungen variieren
innerhalb ungefähr1cm, Startorientierungen um wenige Grad.

Alle32Aufgaben einschließlich ihrer Familienzuordnung und Splits werden
**vor dem Lösen** in `manifest.json` festgeschrieben. Beide nahen Varianten
einer Familie bleiben zusammen. Fehlgeschlagene Aufgaben werden weder
heimlich ersetzt noch als positive Beispiele exportiert. Die Trennung
verhindert das Verteilen benachbarter Bahnpunkte/Varianten über die Splits;
mit nur16Familien ist sie noch kein belastbarer Generalisierungstest.

Andere Startposen entstehen durch IK-Fortsetzung von der bisherigen8cm
erhöhten Ankerpose. Der resultierende Anfangszustand wird geometrisch geprüft.
Die Initialisierung ist weiterhin **keine Anfahr-, Greif- oder Hubtrajektorie**.
Feste Basen, gleiche Griffe, gleiches Objekt, beide linken Arme geparkt.

## Abnahme und Wiederaufnahme

Jede Aufgabe protokolliert Startprüfung, Referenzprüfung, Optimierung und
die Prüfung des tatsächlichen gemeinsamen Gelenkinterpolanten. Die bisherige
Abnahme bleibt erhalten: maximal5ms Prüfabstand, FCL mit bewegtem Karton,
alle sechs Armpaare,20mm Armhüllabstand,3mm Objekt-Hüllabstände, feste Griffe,
Gelenkgrenzen, Konditionsschwelle und gemeinsame v/a/Ruck-Grenzen.

Nur `VALIDATED` liefert positive BC-Übergänge. `START_INVALID`,
`REFERENCE_IK_FAILED` und `NO_VALIDATED_TRAJECTORY` bleiben in der Auswertung.
Insbesondere Referenz-IK-Versagen ist eine Grenze des aktuellen lokalen
Ablaufs, kein Beweis, dass keine andere Bahn existiert.

Das Manifest bindet Quelle, Code, Modell und Meshes per Hash/Signatur.
Ein identischer Aufruf setzt fehlende Fälle fort; fertige Fälle werden nicht
neu gerechnet. Veränderte Parameter/Quellen verlangen einen neuen Zielordner.
Akzeptierte NPZ-Dateien besitzen eigene SHA256-Werte. Pro Fall wird atomar
geschrieben. Höchstens zwei lokale CPU-Prozesse, niceness10, je ein BLAS-Thread;
keine ROS-Nodes, Geräte- oder Dienstaktionen.

## BC-Datenschnittstelle

Pro akzeptierter Bahn100Übergänge mit festem **geometrischem** Fortschritt
`Δs=0,01`. Das ist kein100Hz-Controller und keine Geschwindigkeit. Die
zeitparametrierte Ursprungstrajektorie bleibt zusätzlich im Fallbericht.
Die100Übergänge sind stark korreliert und keine100unabhängigen Aufgaben.

Beobachtung, insgesamt52Werte:

| Bereich | Inhalt |
|---|---|
| `0:12` |12Gelenkwinkel der tragenden Arme, Reihenfolge im Manifest|
| `12:15` |Objektmittelpunkt in Weltkoordinaten, Meter|
| `15:21` |erste Rotationsmatrixspalte, dann zweite Spalte|
| `21:27` |Weltpositionsfehler zum Ziel und `Log(R_goal R_currentᵀ)`, Meter/Radiant|
| `27:28` |aktueller Bahnfortschritt `s`|
| `28:52` |vier6D-Fehler zur gewünschten Referenz bei `s+0,025/0,05/0,10/0,20`, bei1gekappt|

Aktion, sechs Werte: `p_next − p_current` und `Log(R_next R_currentᵀ)`.
Rekonstruktion: `R_next = Exp(δr) R_current`. Auch Gelenkwinkel und Objektposen
vor/nach jedem Schritt sind für spätere Prüfungen gespeichert.

Der Referenzausblick enthält **keine Lehrerkorrekturen**. Er unterscheidet
verschiedene gewünschte Wege zum selben Ziel. Ein nur zielkonditionierter
Datensatz braucht dagegen eine konsistente Regel, welche Route der Lehrer
für denselben Zustand und dasselbe Ziel bevorzugt. Die aktuelle Schnittstelle
ist bewusst referenzkonditioniert und benötigt einen verfügbaren Bahnfortschritt.

Die Exportpunkte liegen auf einem anderen Raster als die Zeitprüfung und
werden zusätzlich auf Kollision, Abstände, Griffschluss, Kondition und
Gelenkgrenzen geprüft. Rohdaten bleiben in SI-Einheiten; eine spätere
Normalisierung ausschließlich auf dem Trainingssatz bestimmen. Für variable
Basen, zusätzliche Teile oder bewegte andere Arme fehlen derzeit die
entsprechenden Szeneneingaben. Die Greifmatrix allein ersetzt diese nicht.

`review_teacher_dataset.py` rekonstruiert unabhängig die Beobachtungsfelder,
die Aktionskomposition und den Bezug zum Gelenkinterpolanten. Es prüft außerdem
20.001Ableitungszeitpunkte pro akzeptierter Bahn und erzeugt eine HTML-Galerie.
Geometrische Prüfergebnisse stammen weiterhin aus dem gemeinsamen Modell;
keine unabhängige Physik- oder Hardwarevalidierung wird behauptet.

## Bedienung

Vom Workspace aus:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  src/multi_arm_manipulation_UWA/tools/generate_teacher_dataset.py \
  setup/research/offline-carton-sides-20261117/standard/smoothed/result.json \
  --output-dir setup/research/two-arm-teacher-dataset-20261117/pilot02 \
  --maxiter 30 --workers 2

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  src/multi_arm_manipulation_UWA/tools/review_teacher_dataset.py \
  setup/research/two-arm-teacher-dataset-20261117/pilot02

xdg-open setup/research/two-arm-teacher-dataset-20261117/pilot02/viewer.html
```

`--prepare-only` schreibt/prüft das Manifest ohne Bahnberechnung.
`summary.json` enthält Versuche und Annahmen je Kategorie/Split.
`train.json`, `validation.json`, `test.json` verweisen ausschließlich auf
akzeptierte `cases/*.npz`. Jede `cases/*.json` bewahrt den vollständigen
Lehrerlauf einschließlich Fehlern. `export-audit.json` bindet die geprüften
Fallberichte und Daten. Die Galerie bietet alle akzeptierten Bewegungen,
Referenzumriss, Play/Pause, Zeitschieber und frei drehbare Ansicht.

## Ergebnis des Piloten `pilot02`

| Referenzklasse | Versuche | Akzeptiert | Davon korrigierte Referenzen | Referenz-IK gescheitert |
|---|---:|---:|---:|---:|
| 3D-Translation |8|8|0|0|
| 3D-Rotation |8|5|5|3|
| Gemischte6D-Bewegung |16|8|5|8|
| Gesamt |32|21|10|11|

21gültige Bahnen ergeben2.100Übergänge:1.200Train,500Validierung,400Test.
Alle32Fälle sind abgeschlossen; keine Aufgabe wurde ersetzt. Neun der zehn
korrigierten Referenzen hatten FCL-Kollisionen, eine verletzte nur den
geforderten Objekt/Umgebung-Abstand. Die gültigen Rotationsfälle benötigen
9,5–21,1mmPositionskorrektur trotz reiner Drehreferenz. Im stärkeren gemischten
Fall sind es maximal46,4mm/11,3°Korrektur; die feste Endpose bleibt erhalten.

**Abdeckungslücken:** Beide reinen Rotations-Testaufgaben scheitern an der IK;
diese positive Testgruppe ist leer. Die akzeptierten gemischten Testbahnen
sind bereits frei, prüfen also noch kein erlerntes Ausweichen. Alle zehn
Korrekturfälle dieses neuen Satzes betreffen Karton/Umgebung. Selbst in deren
Referenzen beträgt der kleinste Arm-Paarhüllabstand196,4mm; es gibt hier
keine neuen engen Arm/Arm-Begegnungen. Der frühere−100°-Lehrerfall mit
Arm-/Objektarmkollision bleibt separat im ursprünglichen Beispielsatz.
Der neue Pilot allein reicht deshalb noch nicht zum Training/Bewerten einer
allgemeinen Zweiarm-Kollisionsvermeidung.

Prüfnachweise:

- Insgesamt48.859Zeitpunkte mit maximal5ms Abstand und2.121zusätzliche
  Exportzustände geprüft. Akzeptierte Bahnen insgesamt244,14sModellzeit.
- Kleinste gültige Hüllabstände:201,48mmArm/Arm,3,611mmKarton/Umgebung,
 107,87mmKarton/Armkörper. Numerischer Griffschlussfehler höchstens
 1,34e−9m/1,53e−9rad, keine Aussage über physische Genauigkeit.
- Unabhängige Exportrekonstruktion und je20.001Ableitungszeitpunkte PASS,
  `export-audit.json`. Keine neue geometrisch unabhängige Prüfung behauptet.
- Build und15gezielte Pythonprüfungen PASS; Wiederaufnahme erkennt alle32
  abgeschlossenen Fälle und identische Bindungen.309Browserprüfungen PASS,
  Screenshot `preview-midpath.png` visuell geprüft.
- Unterbrochener Vorgänger `pilot01`: zu breite Versionsbindung erfasste eine
  parallele Änderung des unbenutzten Hardwarezustandslesers. Zehn gespeicherte
  positive Einzelfälle bleiben historisch, wurden nicht in `pilot02` übernommen.
  Im finalen Lauf sind19relevante Algorithmus-/Modellquellen gebunden.

## Nächster fachlicher Schritt

Nach Auswertung dieses Piloten gezielt zusätzliche Start-/Zielbereiche,
wechselnde Annäherungsrichtungen und Engstellen ergänzen. Dabei insbesondere
genügend tatsächlich korrigierte Bahnen sammeln; viele freie Referenzen
allein lehren kaum Kollisionsvermeidung. Vor größerem Training außerdem prüfen,
ob ähnliche Eingaben konsistente Lehreraktionen erhalten. Später vollständige
Policy-Rollouts und Zustände neben der Demonstrationsbahn testen: geringer
Fehler auf einzelnen BC-Schritten genügt nicht als Nachweis stabiler Rollouts.
