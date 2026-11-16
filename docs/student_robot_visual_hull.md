# Studentischer Roboter: erster 3D-Formkandidat

Stand16.11.2026. Rein offline aus den bestätigten Fotos gerechnet; keine Kamera-,
Roboter-, Treiber- oder GPU-Aktion. Der Kandidat ist eine **fototexturierte
Außenhülle**, kein fertiges mechanisches CAD und kein vermessenes Materialmodell.
Das offene Gitter und verdeckte Innenräume sind damit nicht rekonstruiert.

## Ergebnis und Dateien

Lokaler Hauptordner:
`setup/digitization/student_robot_20261113/reconstruction_v1/asset_candidate/`.

| Datei | Inhalt |
| --- | --- |
| `model.glb` | Fototexturierter Entwurf, Meter, lokales +Z nach oben |
| `outer_envelope.stl` | Geschlossene äußere Hülle; keine Fertigungs-/Kollisionsfreigabe |
| `preview.png` | Zwei gerenderte Modellansichten, visuell geprüft |
| `asset.json` | Maße, Status, Board→Asset-Transform, Quellenhashes und Grenzen |
| `camera_models_snapshot.json` | Eingefrorene Bild-/Optik-/Posemodelle |
| `silhouette_annotations.json` | Bildgebundene Masken, Rollen, Voxel-/Auflageannahmen |
| `reconstruction.json`, `texture_report.json` | Berechnung, Prüfprojektionen und Texturzuordnung |

Hülle **452×320×316mm**, achsparallel im rechten Boardkoordinatensystem,
258220Dreiecke, watertight und positiv orientiert; GLB nach erneutem Einlesen
mit identischen Grenzen (Toleranz1µm geprüft). Die Außenlänge weicht von der
groben Nutzerangabe330mm ab: **offene Maßprüfung**, keine bestätigte Abmessung.
Weder Nutzermaße noch eine alte Objektpose wurden zum Erzwingen des Ergebnisses
verwendet. Die Diskretisierung beträgt4mm; das ist keine bewiesene Genauigkeit.

66,8% der Dreiecke erhielten Fototextur, übrige Flächen neutralgrau. Aufgrund
des sichtbaren Hintergrunds durch das reale Gitter ist diese Fotoerscheinung
keine gemessene Materialfarbe. Oben und an schrägen Flächen bleiben sichtbare
Textur-/Geometrieartefakte. Insbesondere existiert die geschlossene Kappe der
Hülle nicht als nachgewiesenes reales Bauteil. Kein STEP mit erfundenen Blechen,
Wandstärken, Schrauben oder Gelenken exportiert.

## Methode und Prüfdaten

Manuell markierte äußere Objektkonturen, mit Originalbildhash und expliziter
180°-Vorschauumrechnung gebunden. Die Innenlöcher des feinen Gitters wurden
nicht als gemessene Masken modelliert. Maskenüberlagerungen wurden visuell
geprüft: `reconstruction_v1/masks_review.jpg`.

- Fit: `r1`/`r4` jeweilsLR/RF/RR plus `r1_oak4`, sieben Ansichten.
- Prüfung: `r2`/`r3` jeweilsLR/RF/RR, sechs vorab reservierte Ansichten.
  Prüfbilder schneiden keine Voxel weg und liefern keine Texturen.
- LF bleibt entsprechend dem vorhandenen Optikvertrag metrisch ausgeschlossen.
  RFs ursprüngliches failed-Flag wird mitgeführt, nicht zuPASS umgeschrieben.
- Direkte beobachtete Boardposen und feste native K/D. Keine Roboter-FK,
  Hand-Auge-Matrix, nominellen Tischabstände oder Ground-Truth-Objektpose imFit.
- Schnitt der Silhouettenkegel,4mm-Gitter und deklarierte2px Maskentoleranz
  bei1000px Vergleichsbreite. Diskretisierungs-/Zeichenparameter, keine
  statistisch bestimmte Messunsicherheit.
- Erste freie Hülle berührte die untere Suchgrenze und wurde gestoppt. Danach
  Nutzerangabe „Unterseite auf Tischhöhe“ ausdrücklich als Auflagebedingung
  verwendet: Board und Auflage beiBoard-z0 koplanar angenommen. Papier-/Mount-
  Dicke ist nicht separat vermessen. Andere freie Suchgrenzen dürfen weiter
  nicht berührt werden; keine Außenmaße aus einem abgeschnittenen Suchraum.
- Der erste kubische Export war nicht wasserdicht. Separater Nachfolger mit
  konsistenter6-Tetraeder-Isosurface bei0,5 schließt die Oberfläche ohne
  Masken-/Optikänderung. Lineare Gitterinterpolation ist kein Subvoxel-Messnachweis.

Prüfsilhouetten-IoU **0,846–0,938**, Mittel0,905. Das ist Eingabekonsistenz;
die Projektion verwendet einen konservativen Ein-Zellen-Bildfußabdruck.
Keine subpixelgenaue Oberflächenprüfung und keine unabhängige Metrologie.
Überlagerungen: `reconstruction_v1/heldout_projection_review.jpg`.

Die Hüllenberechnung selbst dauerte5,41s, ohne Annotation, Texturierung,
Export und Agentenarbeit. Es ist kein Vergleich verschiedener Reasoning-Stufen.
Neun synthetische Mesh-/Vertragstests plus zwei Optikdiagnosetests prüfen
Transformationen, Maskenrotation/Löcher, Hash-/Metrikausschluss, unveränderte
Geometrie bei anderen Prüfbildern, explizite Auflage und geschlossene orientierte
Oberflächen auch bei diagonalen/randomisierten Voxelmustern.

## Reproduzierbare Offline-Schritte

Aus dem Workspace; jeden Lauf in einen **neuen** Ausgabeordner schreiben:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 -m uwa_cell_control.silhouette_mesh \
  --models setup/digitization/student_robot_20261113/job/prepared/camera_models.json \
  --annotations setup/digitization/student_robot_20261113/reconstruction_v1/silhouettes_support_v3.json \
  --output /tmp/uwa-student-hull
python3 src/multi_arm_manipulation_UWA/tools/texture_silhouette_mesh.py \
  --hull /tmp/uwa-student-hull
.venvs/oak-model/bin/python src/multi_arm_manipulation_UWA/tools/export_silhouette_asset.py \
  --hull /tmp/uwa-student-hull --output /tmp/uwa-student-asset
.venvs/oak-model/bin/python src/multi_arm_manipulation_UWA/tools/preview_digitization_asset.py \
  --asset /tmp/uwa-student-asset --output /tmp/uwa-student-asset/preview.png
```

Diese Werkzeuge fragen keine Hardware ab. Das ROS-Environment liefert nur die
lokalen Pythonmodule. Rohdaten/Masken/Kandidaten bleiben unter `setup/`, nicht imGit.
Der reguläre Job bleibt bei `NEEDS_INPUT`: Der eigenständige Prototyp ist noch
kein validierter Standard-Meshbackend und schaltet keine Pipelinefreigabe um.
Bestehende Simulationsassets wurden nicht ersetzt oder automatisch geladen.

## Nächste Qualitätsstufe

Zuerst Außenlänge unabhängig prüfen und die große Abweichung zur groben
Nutzerangabe aufklären; danach beobachtete Stützpunkte/Kanten und Mehransichts-
Konsistenz lokal auswerten. Das offene Gitter benötigt detaillierte Segmentierung
oder ein photometrisches Mehransichtsverfahren, zusätzliche sichtbare Innenflächen
gegebenenfalls einen neuen Auftrag. Die LF-Reparatur kann unabhängig nach der
[präzisen Kameradiagnose](left_front_camera_diagnosis_2026-11-16.md) erfolgen.
Ein neues LF-Profil nicht während eines gebundenen Fits überschreiben.

Das Verfahren folgt dem Visual-Hull-Prinzip und dessen Grenzen:
[Laurentini, 1994, Originalpublikation](https://iris.polito.it/handle/11583/1401917).
Ein weitergehender photometrischer Ansatz ist
[Kutulakos und Seitz, A Theory of Shape by Space Carving](https://www.cs.columbia.edu/~changyin/paper2read/SeitzICCV1999.pdf).
Eine solche Weiterentwicklung ist mit diesem Silhouettenprototyp noch nicht
nachgewiesen. Geometrie/Tracking/Manipulation bleiben unvalidiert.
