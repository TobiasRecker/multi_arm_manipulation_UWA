# Zweiarm-Teacher: unterschiedliche Ausgangszustände

Stand17.11.2026. Der Nutzer weist darauf hin, dass die bisherigen Abläufe
trotz unterschiedlicher Ziele praktisch immer aus derselben Situation starten.
Der [erste 3D-/6D-Pilot](teacher_dataset_6d.md) variierte den Start nur um
ungefähr1cm und wenige Grad. Der neue Versuch trennt deshalb Objektstartpose,
zugehörige Armkonfiguration und gewünschte Bewegung.

Anschließende Nutzerkritik zur Schwierigkeit und Laufzeit:
[Kollisionssuche und Grenzen des aktuellen Lehrers](teacher_collision_mining.md).
Die unten beschriebenen Armkorrekturen verletzen vor der Korrektur den
Mindestabstand, zeigen aber noch keine FCL-Kontaktkollision.

## Startsuche und Aufgaben

Zwölf Familien werden vorab mit Weltpositionsversatz, Rotationsvektor und
Train-/Validierungs-/Testzuordnung festgelegt. Sie umfassen unterschiedliche
Höhen, seitliche Lagen, Neigungen und Yaw-Winkel. Je Familie gibt es eine
reine Translations- oder Rotationsaufgabe und eine gemischte6D-Aufgabe.
Damit stehen24Versuche vor jeder Erreichbarkeitsprüfung fest.

Für jede Startpose werden pro Arm zehn deterministische IK-Initialisierungen
versucht. Lösungen, die sich nur um volle Gelenkumdrehungen unterscheiden,
zählen nicht als verschiedene Zweige. Anschließend werden die gefundenen
Lösungen beider Arme kombiniert und gemeinsam geprüft: FCL, alle sechs
Armpaare, Objekt/Umgebung, Objekt/Armkörper, Gelenkgrenzen, Kondition und
numerischer Griffschluss. Ein starrer Objektgriff lässt nicht beliebige
unabhängige Armstellungen zu.

Aus den gültigen Kombinationen wird die mit dem kleinsten Armhüllabstand
ausgewählt, um engere Situationen einzubeziehen. Die bisherigen Abnahmegrenzen
bleiben bestehen. Pro Objektpose wird damit **eine** Armkombination für beide
Aufgaben genutzt; mehrere gefundene Kombinationen sind noch kein Datensatz
mit mehreren trainierten Zweigen für dieselbe Pose. Alle Startkandidaten und
Fehler bleiben in `starts/*.json` erhalten. Die begrenzte IK-Suche ist nicht
vollständig und ein Fehlschlag beweist keine Unerreichbarkeit.

Diese Starts sind unabhängig initialisierte, hypothetisch starre Griffe.
Es wird **keine Anfahrt aus der alten Pose und kein IK-Zweigwechsel während
eines bestehenden Griffs** behauptet. Entlang jeder neuen Bahn bleiben die
Grifftransformationen und der gewählte kontinuierliche IK-Zweig erhalten.
Basen, Karton, Greifpunkte und beide geparkten linken Arme bleiben gleich.

## Datensatz und Prüfung

Ganze Startfamilien bleiben zusammen, auch wenn von derselben Pose
unterschiedliche Bewegungen starten. Das prüft später andere Startlagen
strenger als eine Aufteilung von Bahnpunkten. Die neue Aufteilung gilt für
diesen Versuch; alte und neue Datensätze nicht ungeprüft zusammenführen.

Die bisherige52D-Beobachtung enthält Objektpose, Gelenkwinkel, Ziel und
Referenzausblick. Damit sind unterschiedliche Ausgangskonfigurationen für
das Netz unterscheidbar. Die Greifmatrix wäre bei gleichen Griffpunkten
allein dafür nicht ausreichend. Aktionen bleiben geometrische6D-Schritte
mitΔs=0,01, keine Geschwindigkeitskommandos. Nur vollständig akzeptierte
Bahnen liefern die100BC-Übergänge je Aufgabe.

Abnahme wie bisher: tatsächlicher gemeinsamer Gelenkinterpolant mit≤5ms
Prüfabstand, zusätzlich101Exportzustände, FCL, Abstände, Griffschluss,
Kondition und gemeinsame v/a/Ruck-Grenzen. Der Reviewer rekonstruiert die
BC-Labels und prüft20.001Ableitungszeitpunkte sowie jeden Anfangszustand
erneut. Das bleibt eine diskrete Modellprüfung ohne Kontaktphysik/Hardware.

## Reproduzierbare Quellen trotz paralleler Arbeiten

Der Launcher kopiert beim ersten Aufruf die benötigten Python-Pakete und
Werkzeuge nach `frozen-source/`. Worker und Reviewer verwenden diese Kopie;
deren Hashes und die tatsächlich geladene Planungskonfiguration werden im
Manifest gespeichert. Modell und Meshes bleiben zusätzlich gebunden.
Ein erneuter Aufruf verwendet dieselbe Kopie und setzt fehlende Ergebnisse
fort. Für geänderten Code, neue Aufgaben oder Parameter einen neuen
Ausgabeordner verwenden. Der alte Pilot wird dadurch nicht überschrieben.

Installierte ROS-/MoveIt-/NumPy-/SciPy-Bibliotheken und Ressourcen sind nicht
als vollständiges Containerimage eingefroren. Die Modell-/Konfigurations-
prüfungen bleiben deshalb auch beim Fortsetzen aktiv.

## Ergebnisse vom17.11.2026

Die Startsuche findet neun gültige Objektposen aus zwölf vorgegebenen
Familien. Pro gültiger Pose gibt es2–12geprüfte IK-Kombinationen. Drei
Startfamilien liefern keinen akzeptierten Zustand; sechs zugehörige
Trajektorienversuche bleiben deshalb `START_INVALID`.

Der Hauptlauf `run01` liefert **13gültige Bahnen aus acht Startlagen**
(vierTranslation, vierRotation, fünfMischung),1.300BC-Übergänge. Fünfweitere
Aufgaben scheitern an der kontinuierlichen Referenz-IK. Eine zunächst gültige
Startpose (`centre_high`) liefert daher noch keine gültige Folgebahn.

Die tatsächlich vertretenen acht Startlagen umfassen32×32×10cm, maximal
34,76cm Abstand untereinander und125°Orientierungsunterschied. Jede liegt
mindestens13,4cm vom alten Anker entfernt. Alle neun gültigen Startkandidaten
zusammen umfassen32×32×14cm; diese größere Zahl nicht mit der Abdeckung
der akzeptierten Bahnen verwechseln. Kleinster Start-Armhüllabstand58,91mm,
kleinster Abstand entlang gültiger Hauptlaufbahnen32,22mm. Eine Referenz
wird korrigiert; dieser Hauptlauf enthält noch keine Armabstandsverletzung.

Darauf folgt ein **separater Diagnoseversuch `encounters01`** an den beiden
Starts `east_high` und `positive_tilt`: sechs vorab festgelegte Aufgaben mit
1,4-/1,8-/2,2-facher Zwischenrotation bei unverändertem Start und Ziel.
Startbank und ursprüngliche Splitzuordnung werden mit Eltern-Hashes
übernommen. Dies ist eine nach Sichtung ausgewählte Engstellendiagnose,
kein unabhängiger statistischer Blindtest.

| Fall | Referenz-Armabstand | Geprüfter Armabstand | Maximale Positions-/Orientierungskorrektur |
|---|---:|---:|---:|
| `east_high`, Zwischenrotation×1,8 |15,82mm|21,00mm|2,05mm /1,17°|
| `east_high`, Zwischenrotation×2,2 |5,64mm|21,00mm|4,74mm /3,48°|

Beide Engstellen betreffen **right_front gegen right_rear**, also die
tragenden Arme. Die Referenzen verletzen den geforderten20mm-Hüllabstand;
sie zeigen keine FCL-Kontaktkollision. Die Korrektur beseitigt diese
Abstandsverletzung bei festen Endpunkten. Zwei weitere Aufgaben sind bereits
gültig; eine scheitert an der Konditionsschwelle und eine an der IK-Fortsetzung.
Ergebnis:4/6gültige Bahnen, davon zwei korrigiert, weitere400BC-Übergänge.

Zusammen17zusätzliche gültige Bahnen/1.700Übergänge. Noch kein Netztraining.
Die Aufteilung ist weiterhin ungleichmäßig: Im Hauptlauf fehlt ein positives
gemischtes Trainingsbeispiel; die neuen Armkorrekturen erben `test` von
`east_high`. Die Aufgaben eignen sich zunächst zur Lehreranalyse. Für einen
vollständigen Trainings-/Evaluationskorpus weitere Familien ergänzen und die
Abstammung beim Zusammenführen der Piloten berücksichtigen.

Build und18gezielte Tests PASS; beide Exportaudits einschließlich dichter
Ableitungsprüfung PASS. Hauptlauf23.729Zeitprüfpunkte≤5ms, zusätzlich101
Exportzustände je gültiger Bahn. Wiederaufnahme beider Läufe ohne
Neuberechnung erfolgreich.199Browserchecks für Startvielfalt und73für
Engstellen PASS, beide Screenshots visuell geprüft. Startposition und
Orientierung relativ zum ursprünglichen Anker stehen ausdrücklich in der
Anzeige; laufende Rotationsänderung separat relativ zum ausgewählten Start.

## Bedienung

Vom Workspace aus:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/generate_diverse_teacher_dataset.py \
  setup/research/offline-carton-sides-20261117/standard/smoothed/result.json \
  --output-dir setup/research/two-arm-diverse-starts-20261117/run01 --workers 2

python3 src/multi_arm_manipulation_UWA/tools/review_diverse_teacher_dataset.py \
  setup/research/two-arm-diverse-starts-20261117/run01

xdg-open setup/research/two-arm-diverse-starts-20261117/run01/viewer.html
```

Optional `--bank-only` prüft zunächst nur die Startkonfigurationen. Anschließend
derselbe Aufruf ohne diese Option für die Trajektorien. Höchstens zwei
CPU-Worker mit niceness10 und je einem BLAS-Thread; keine ROS-Nodes oder
Roboter-/Kamera-/Dienstaktionen. `start-coverage.json` beschreibt alle gültigen
Starts, `export-audit.json` zusätzlich nur die tatsächlich in akzeptierten
Bahnen vertretenen Starts. `summary.json` enthält auch alle Fehlversuche.

Engstellendiagnose und deren Galerie:

```bash
python3 src/multi_arm_manipulation_UWA/tools/probe_teacher_arm_encounters.py \
  setup/research/two-arm-diverse-starts-20261117/run01 \
  --output-dir setup/research/two-arm-diverse-starts-20261117/encounters01
python3 src/multi_arm_manipulation_UWA/tools/review_diverse_teacher_dataset.py \
  setup/research/two-arm-diverse-starts-20261117/encounters01
xdg-open setup/research/two-arm-diverse-starts-20261117/encounters01/viewer.html
```
