# Zweiarm-Objekttransport als Lehrer für Behavioral Cloning

Stand: 17.11.2026. Der Nutzer hat BC als Vergleich gewählt: zuerst einen
prüfbaren Lehrer und gute Beispiele entwickeln, danach das Netz trainieren.
Der Einstieg verwendet zwei Arme an gegenüberliegenden kurzen Kartonseiten.
Für zusätzliche mehrachsige Beispiele gibt es jetzt eine
[Datengeneration mit 3D-/6D-Familien und BC-Export](teacher_dataset_6d.md).
Das spätere Montagebild ist modular: zwei Arme halten Teil1, ein weiterer
Teil2, der vierte ein Werkzeug. Diese letzten beiden Aufgaben sind noch nicht
modelliert; aktuell stehen die übrigen Arme als Hindernisse im Arbeitsraum.

## Vorschau und Umfang

Vom Workspace aus:

```bash
xdg-open setup/research/two-arm-object-teacher-20261117/run02/viewer.html
```

**Example / variant** schaltet zwischen Referenz und Lehrerlösung. Play/Pause,
Zeitschieber, Orbit/Zoom und ein gestrichelter Referenzkarton ermöglichen den
Vergleich. Fehlgeschlagene Referenzen sind ausdrücklich sichtbar. Standard
ist eine gültige Lehrerlösung und Wiedergabe1×. Die Tabelle zeigt die Prüfung
der gesamten Trajektorie; SAMPLE CLEAR gilt nur für das aktuelle Bild.

Dies ist Offlinekinematik mit hypothetisch starren Griffen, offenen Fingern und
festen Basen. Kein physisches Tragen, keine Kontaktphysik, keine Kraftregelung,
keine reale Bewegung und noch kein trainiertes Netz. Die Modellpose startet
8cm oberhalb der bisherigen Karton-Tischpose. Die kinematische Fortsetzung
dorthin initialisiert den Versuch, ist keine geprüfte Anfahr-/Greiftrajektorie.

## Greifgruppe und Modell

- Kartonmaß aus bestehendem Asset: etwa404×342×163mm. Die kurzen Seiten sind
  `x_min` und `x_max`, also die Enden der längeren horizontalen Objektachse.
- `right_front` übernimmt `x_min`, `right_rear` übernimmt `x_max`. Individuelle
  Tool→TCP-Transformationen werden verwendet, keine fremden Gelenkwinkel kopiert.
  Der bestehende obere Seitenmittelgriff bleibt geometrisch definiert.
- Die beiden linken Arme bleiben in der bisherigen aufrechten Startstellung.
  Ihre komplette vorhandene Geometrie bleibt in der Prüfung. Alle sechs
  Armpaare werden ausgewertet, einschließlich der beiden bewegten Arme.
- Der bisherige `ObjectTransport` unterstützt nun eine auswählbare tragende
  Gruppe; ohne Angabe bleibt die Vierarmvariante erhalten. Gemeinsames Objekt,
  feste Objekt→TCP-Transformationen und ein Zeitgesetz gelten pro Greifgruppe.

## Referenz und Optimierung

Eine Aufgabe definiert Welttranslationsvektoren `goal_m` und `excursion_m`
sowie Weltachsen-Rotationsvektoren in Grad (`goal_rotation_vector_deg`,
`rotation_vector_deg`). Rotationsvektoren sind keine Eulerwinkel.

Die Referenz ist linearer Zielfortschritt plus `sin²(πs)`-Auslenkung. Rotationen
erfolgen um den Kartonmittelpunkt. Der Lehrer ergänzt sechs innere quintische
B-Spline-Kontrollpunkte mit jeXYZ und einem3D-Rotationsvektor. Die Korrektur
wird auf SO(3) mit der Referenzrotation zusammengesetzt; Start und Endpose
bleiben exakt fest. Es werden keine unabhängigen Armwege nachträglich retimed.

Die Translation ist je Kontrollkomponente auf±12cm, die Rotation je Komponente
auf±35° begrenzt. Dies sind Versuchsparameter, keine universellen Roboterdaten.
Bei mehreren Rotationskomponenten ist die Norm nicht auf35° beschränkt.
Die Kosten gewichten normierte Positions-/Orientierungskorrektur und Glätte.
Sie optimieren weder global noch direkt die kürzeste Ausführungsdauer.

Der Ablauf prüft zuerst die Referenz, sucht nötigenfalls unter wenigen
deterministischen Startvorschlägen mit zusätzlichem Hub und verringerter
Zwischenrotation und verbessert diese mit sequentiellen QPs, Trust-Region und
Schrittrücknahme. Der beste zulässige Zwischenstand bleibt erhalten, auch wenn
spätere Schritte scheitern. `BEST_FEASIBLE_ITERATE` bedeutet keine Konvergenz
zu einem globalen oder nachgewiesen lokalen Optimum. IK-Versagen oder kein
gefundenes Ergebnis sind keine Unlösbarkeitsbeweise.

Optimierungsbedingungen:

1. Alle Arm-Paarabstände über bestehende Kugelhüllen, analytische Gradienten
   aus Punkt-Jacobimatrizen und gemeinsamer12×6-Objekt→Gelenk-Abbildung.
2. Karton gegen Armkörper: signierte Punkt/Quader-Abstände minus Kugelradien,
   analytische Ableitung für bewegtes Objekt und bewegte Arme. Finger, Kamera
   und Wrist3 werden nur aus diesem Steuerungsersatzmodell ausgeschlossen;
   die vorhandene FCL-Prüfung bekommt keine neuen Kontaktausnahmen.
3. Karton-Hüllquader gegen vorhandene Umgebungshüllquader über trennende Achsen,
   mit numerischen Posegradienten. Positive Werte sind konservative
   Trennebenenabstände, negative Werte kein exakter Mesh-Penetrationsbetrag.
4. Gelenkgrenzen, feste Endpunkte und fortgesetzter IK-Zweig. Selbstkollision
   und skalierte Jacobikondition werden zusätzlich bei der Abnahme geprüft.

Abnahmegrenzen:20mm Armabstand,3mm Objekt-Hüllabstände. Die Optimierung
verwendet1mm zusätzlichen Puffer auf121Stützstellen; dieser ersetzt keine
Nachprüfung. Ein globaler Mindestabstand allein erklärt keine Kollision
zwischen Objekt und Unterarm oder eine Selbstkollision.

## Trajektorie und Prüfkriterien

201gemeinsame IK-Stützstellen ergeben einen quintischen Gelenkspline für alle
12tragenden Gelenke. Ein gemeinsames C3-Zeitgesetz begrenzt v/a/Ruck auf
0,45rad/s,0,4rad/s²,2rad/s³ und setzt alle drei Ableitungen an beiden Enden null.
Analytische Obergrenzen werden durch unabhängige dichte Ableitungsproben ergänzt.

Der tatsächliche Interpolant wird mit höchstens5ms Abstand geprüft:
bewegtes Kartonmesh in FCL, Umwelt-/Selbst-/Objektkollision, alle sechs
Armpaarhüllen, Objekt-Hüllabstände, Gelenkgrenzen, unveränderte geparkte Arme
und feste Griffe mit1µm/10µrad numerischer Toleranz. Die Singularitätsschwelle
0,05 nutzt eine charakteristische Länge0,5m und ist ein Versuchsindikator,
keine Last-/Parallelroboterqualifikation. Diskrete Prüfung ist kein
kontinuierlicher Kollisionsbeweis. Stoppreserven bleiben unqualifiziert.

Die vorhandene Kollisionsgeometrie besitzt teilweise nur visuelle Links;
vorhandene Hüllen ergänzen sie, sind aber keine physische Geometriekalibrierung.
Der Karton-Hüllquader umfasst auch den leeren Innenraum und kann deshalb
physisch freie Lösungen konservativ verwerfen.

## Beispiele und Nachweise

Der Beispielsatz enthält eine Verschiebung zu einem neuen Ziel mit35°
Welt-Z-Endrotation, zwei starke Zwischenrotationen ungefähr um die lange
Kartonachse (Welt-Y) mit Rückkehr zur Startpose sowie einen erhaltenen
IK-Fehlerfall. Eine verringerte Zwischenrotation ist keine erfolgreiche
Ausführung der ursprünglichen100°-Zwischenvorgabe; diese ist eine weiche
Referenz. Harte Endorientierungen werden dagegen nicht verändert.

Eine erste verworfene Lösung beseitigte Armabstands- und Tischprobleme,
kollidierte aber weiterhin mit beiden Unterarmen. Die FCL-Diagnose unter
`setup/research/two-arm-object-teacher-20261117/contact-diagnosis.log` belegt
dies. Daraufhin wurden Objekt/Armkörperbedingungen ergänzt. Weitere negative
Optimierungs- und IK-Versuche bleiben in den Protokollen des Forschungsordners.

Ergebnis des vollständigen Laufs `run02`:

| Fall | Referenz | Geprüftes Ergebnis | Maximale Korrektur Position / Orientierung | Dauer |
|---|---|---|---:|---:|
| Zielversatz(10,3,1)cm +35°Welt-Z-Endrotation | bereits frei | unverändert, minArmabstand200,25mm |0mm /0°|4,863s|
| Welt-Y-Zwischendrehung−100° mit15cmX-Auslenkung | Armabstand5,17mm; Objektkollisionen | korrigiert, minArmabstand109,78mm |50,40mm /26,06°|20,353s|
| Welt-Y-Zwischendrehung+70° mit15cmX-Auslenkung | Objekt-/Umweltkollisionen | korrigiert, minArmabstand230,82mm |30,58mm /0,98°|18,482s|
| Welt-Z-Zwischendrehung+100° ohne Translation | IK-FortsetzungRR scheitert | erhaltenes negatives Beispiel |—|—|

Der−100°-Fall erreicht nach Korrektur ungefähr−74°Welt-Y-Zwischenrotation,
nicht−100°. Die unzulässige Referenz bleibt sichtbar. Die korrigierten Fälle
erhalten mindestens4,050/4,021mm Karton/Umgebung-Hüllabstand; der schwierigere
Fall mindestens4,120mm Karton/Armkörper-Hüllabstand. Das sind Modellwerte.
Die Prüfungen der drei akzeptierten Interpolanten umfassen974/4072/3698
Zeitpunkte≤5ms; maximaler numerischer Griffschlussfehler1,45e−9m/1,35e−9rad.
Kein Rückschluss auf physische Genauigkeit. Die maximale Gelenkänderung
zwischen Prüfpunkten liegt unter2mrad.

Die lokale Optimierung benötigte im Einzelversuch86,4s bzw.80,1s; inklusive
beider Trajektorienprüfungen und Vorschauvorbereitung115,4s bzw.107,0s.
Das ist keine Laufzeitstatistik. Die normierten Korrekturkosten sanken von
0,961auf0,379 bzw.0,0961auf0,0338 gegenüber den zulässigen Initialisierungen.
Der schwierige Fall verwendet den besten zulässigen Zwischenstand, der andere
meldet lokale Konvergenz. Globale Optimalität wird nicht behauptet.

Die Ergebnisse stehen in `run02/result.json`; `independent-check.json` bindet
sie perHash. An neun Zuständen wurden12×6-Kinematik, alle sechs Paarableitungen
und Objekt/Armkörperableitungen mit zentralen Differenzen gegengeprüft:
maxFehler5,51e−11/5,36e−10/4,01e−10 in jeweiligen Ableitungseinheiten.
Bei sechs Perturbationen wechselte die nächste Objekt-Kugel: das Minimum
ist dort nicht differenzierbar. Die unabhängige Prüfung verfolgt deshalb
das jeweils analytisch abgeleitete Kugelfeature fest und protokolliert diese
Wechsel separat; sie behauptet keine eindeutige Ableitung an einer Bindung.
Zusätzlich20.001Ableitungsproben je akzeptiertem Fall, Endpunkt-/Parkarmprüfungen
und absichtliche Karton/Tisch-Kollision bestanden.

Build und28gezielte Pythonprüfungen PASS; alte Vierarm-Gradienten-/Negativprüfung
unter `four-arm-regression.json` ebenfallsPASS. Browserprüfung80ChecksPASS,
Screenshot visuell kontrolliert (`run02/preview-midpath.png`). Frühe negative
Proben und ein abgebrochener CLI-Lauf bleiben erhalten. Gültige Beispiele
werden allein anhand der abschließenden Prüfung akzeptiert, nicht anhand
eines Solverflags.

## Reproduktion und nächste Datengeneration

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/plan_two_arm_teacher.py \
  setup/research/offline-carton-sides-20261117/standard/smoothed/result.json \
  --output-dir setup/research/two-arm-teacher-repeat --maxiter 35
python3 src/multi_arm_manipulation_UWA/tools/verify_two_arm_teacher.py \
  setup/research/two-arm-teacher-repeat/result.json \
  --output setup/research/two-arm-teacher-repeat/independent-check.json
```

Ausgabeordner müssen neu sein. `--tasks` lädt eine JSON-Liste im obigen
Aufgabenschema. `--candidate-report` übernimmt nur Kontrollpunkte aus einem
früheren Bericht mit gleichen Aufgaben; die gesamte IK-/Zeit-/Geometrieprüfung
wird erneut ausgeführt. Quellartefakt, Meshes, Modell und verwendete
Kernquellen werden über Hashes gebunden. Alle Ergebnisse sind `executable:false`.

Dies ist ein kleiner überprüfter Ausgangssatz, noch kein Trainingsdatensatz
und kein statistischer Benchmark. Als nächstes ganze Start-/Ziel-/Drehfamilien
systematisch variieren, Lehrererfolge und Fehlertypen getrennt behalten und
Testfamilien vor dem Training zurückhalten. Zunächst gleichen Greifverbund
und gleiche Geometrie verwenden; später andere Basenlagen und bewegte
Montagepartner hinzufügen. Ähnliche Nachbarpunkte derselben Bahn dürfen nicht
zufällig auf Training und Test verteilt werden.
