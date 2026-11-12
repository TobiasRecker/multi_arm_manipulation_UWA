# Erste Auswertung der mobilen Board-Fotos, 12.11.2026

**Die Fotos sind brauchbar und liefern bereits eine erste relative OAK-Pose zur
vorderen rechten Wrist-Kamera. Eine validierte Kalibrierung ist das noch nicht.**
Alle 18 Originaldateien der sechs Benutzer-Fotosets stimmen mit ihren gespeicherten
SHA256-Werten überein. Der PC-Absturz hat diese Dateien somit nicht verändert.
Die Auswertung liest ausschließlich lokale Daten; keine Kamera-/Roboterdienste
wurden gestartet, keine Arme bewegt und kein Kalibrierprofil aktiviert.

## Vorhandene Daten

Session: `setup/calibration/three_camera_mobile/20261112_155233_897f400a/`.
Zeiten in Australia/Perth; Zeilen enthalten nur Benutzeraufnahmen, keine früheren
automatisierten GUI-Testsets.

| Aufnahme | Vorne rechts | Hinten rechts | OAK | Verwendung |
|---|---:|---:|---:|---|
| 15:57:44 | 11/24 | 24/24 | 12/24 | Teilansicht, zusätzliche Diagnose |
| 15:59:05 | 24/24 | 24/24 | 24/24 | Fit |
| 16:03:42 | 24/24 | 22/24 | 24/24 | Fit |
| 16:11:47 | 24/24 | 24/24 | 24/24 | Fit |
| 16:12:46 | 24/24 | 24/24 | 22/24 | Zurückgehaltene Prüfung |
| 16:14:34 | 24/24 | 24/24 | 24/24 | Zurückgehaltene Prüfung |

Damit sind **fünf gemeinsame Sets verwendbar**, drei davon vollständig mit allen
72 Ecken. Die beiden Prüfansichten wurden chronologisch festgelegt und im
`protocol.json` gespeichert, bevor Kameraposen berechnet wurden. Ihre Ecken gehen
nicht in den Fit ein; keine Aufnahme wurde nach ihrem Reprojektionsfehler entfernt.

Optikprofile stimmen innerhalb der Session überein: vorne2592×1944/Fokus435,
hinten2592×1944/Fokus388, OAK8000×6000/Fokus116. Die individuellen Kamera-IDs
für den relativen Fit wurden ebenfalls geprüft. Die Wrist-Fokuswerte stammen
aus Konfigurations-Readbacks; tatsächliche V4L2-Linsen-/Belichtungswerte werden
während des nativen Bursts derzeit nicht zusätzlich zurückgelesen.

Innerhalb jedes Wrist-Bursts
wurden erstes und letztes natives Bild erneut auf das mobile Board untersucht:
mediane Eckenverschiebung0,056–0,157px, größte Einzelverschiebung0,456px. Das ist
kein auffälliger Bewegungshinweis über diese etwa0,13s; es beweist weder fehlende
Bewegungsunschärfe noch Stillstand über die gesamte Dreieraufnahme.

Auch die Gelenk-Endpunktproben sind konsistent: Differenz vor/nach einem Set
maximal0,000105rad; Spannweite aller Vorher-Proben pro rechtem Arm unter0,0001rad.
Dies ist kein Nachweis kontinuierlichen Stillstands zwischen allen Belichtungen.

## Erste relative Kamerapose

Verwendet wurden vorhandene Front-HD-Intrinsics bei435 und die OAK-Werksintrinsics
für den passenden Linsenwert116, skaliert auf8000×6000. Beide bleiben fest.
Für hinten wurde **keine VGA-Matrix auf HD umgerechnet**: passende geprüfte
HD-Intrinsics bei388 fehlen weiterhin. Die hinteren Fotos sind dafür wertvolle
neue Rohdaten, werden aber noch nicht für einen behaupteten präzisen Fit verwendet.

Der Fit schätzt eine gemeinsame Transformation OAK↔Front-Wrist aus drei
Trainingsansichten; je Ansicht wird die mobile Boardpose mitgeschätzt. Fehler
beider Kameras werden durch ihre jeweilige Brennweite normiert und robust
optimiert. Initialisierung aus bildbasierter planarer PnP, ohne nominelle
Roboter-/OAK-Posen und ohne Simulation-Ground-Truth.

**Unabhängige Konsistenzprüfung der zwei unbenutzten Ansichten:**

| Prüfung | 16:12:46 | 16:14:34 |
|---|---:|---:|
| Unterschied der einzeln geschätzten relativen Translation zum Fit | 5,85mm | 7,40mm |
| Unterschied der relativen Rotation zum Fit | 0,361° | 0,576° |
| Board aus Frontbild in OAK-Bild projiziert, RMS | 10,29px | 6,53px |
| Board aus OAK-Bild in Frontbild projiziert, RMS | 8,00px | 1,28px |

Die Millimeterwerte sind **interne Konsistenzunterschiede**, kein vermessener
Positionsfehler der echten OAK. Abweichungen können u.a. aus Optikmodell,
planarer Posenschätzung, Boardgeometrie und Zeitversatz stammen; keiner dieser
Beiträge wurde hier als Ursache isoliert. Die vorhandene Front-Kalibrierung ist
ausdrücklich unterhalb ihrer automatischen Qualitätsgrenze übernommen worden.

Die vorläufige Transformation ist vollständig unter
`setup/calibration/three_camera_evaluation_20261112/diagnostic_v1/result.json`
gespeichert: **T_oak_optical_right_front_optical** bildet Punkte vom optischen
Frame der vorderen rechten Wrist-Kamera in den optischen OAK-Frame ab.
Die Frontkamera liegt darin ungefähr bei[-0,713;-0,014;0,646]m in OAK-Koordinaten.
Das ist keine Welt-/Tischpose. Es wird kein TF ausgesendet und keine permanente
Konfiguration geändert. Ergebnis ausdrücklich `diagnostic_only:true`,
`passed:false`, `calibration_applied:false`.

## Was zusätzliche Fotos verbessern können

Die fünf guten Ansichten haben etwa26,2° maximale Trennung der Boardnormalen.
Die Boardmitten verteilen sich in der vorläufigen OAK-Geometrie über ungefähr
22×16×12cm. Es gibt also wirkliche Lagevariation, keine bloßen Wiederholungen.
Allerdings bleibt das Board in einem begrenzten Bildbereich. In der OAK sind
die Felder bereits rund163–226px breit; Auflösung ist hier nicht der erste Engpass.

Für den nächsten Aufnahmeblock sind **etwa15–20 weitere unterschiedliche
gemeinsame Ansichten** ein sinnvoller praktischer Zielwert, keine mathematische
Garantie: Board nach links/rechts und oben/unten kippen, seitlich verschieben und
mehrere Abstände nutzen. Reines Drehen innerhalb der Boardebene oder viele
Wiederholungen derselben Lage ergänzen weniger neue Geometrie. Alle Kameras
sollten das ganze Muster mit etwas Rand sehen; bis DONE stillhalten.

Zur Kalibrierung der individuellen Intrinsics dürfen zusätzliche Ansichten auch
separat pro Kamera entstehen, in denen die anderen das Board nicht sehen.
Größere Bildabdeckung und Abstand-/Neigungsvariation sind dafür besonders
relevant. Neue unabhängige Prüfansichten vor dem nächsten Fit festlegen;
die bisherigen beiden nicht schrittweise zur Optimierung des Fits verwenden.

## Reproduktion und Nachweise

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 -m uwa_cell_control.board_photo_evaluation \
  --output "$UWA_WS/setup/calibration/three_camera_evaluation_20261112/new_run"
```

Das Zielverzeichnis muss neu sein; Originalbilder und Protokolle werden nicht
überschrieben. Das Werkzeug ist rein offline und startet keine ROS-Hardware.

Ergebnisse in `.../diagnostic_v1/`: `protocol.json` mit Rollen/Hashes,
`result.json`, `image-audit.json`, `coverage.png`. Gesamtübersicht der Fotos:
`setup/calibration/three_camera_evaluation_20261112/all_sets.jpg`.
Fünf Tests mit bekannter synthetischer Geometrie prüfen Transformationsrichtung,
unabhängige Bildprojektion, unveränderten Fit bei fehlerhaften Prüfbildern,
ungültige Geometrie und die Erkennung veränderter Originaldateien.
