# Kollidierende Referenzen statt überwiegend freier Demonstrationen

Stand: 17.11.2026. Der Nutzer kritisiert zu langsame Datengeneration und zu
wenig anspruchsvolle Bahnen. Das ist für die jüngsten Armbeispiele berechtigt:
die korrigierten Referenzen mit15,8 bzw.5,6mm Abstand verletzen die gewählte
20mm-Bedingung, enthalten aber keine FCL-Kontaktkollision. In den letzten
13+4 akzeptierten Bahnen gab es keine FCL-Kollision der Referenz. Im älteren
32-Aufgaben-Piloten hatten neun akzeptierte Bahnen zunächst FCL-Kollisionen,
überwiegend Karton/Umgebung.

## Neue Vorauswahl

`tools/mine_teacher_collisions.py` verwendet die eingefrorenen Quellen und
die geprüfte Startbank des vorherigen Versuchs. Pro Objektstart werden bis
zu drei gültige IK-Kombinationen genutzt. Eine Modellinstanz bleibt für
mehrere Kandidaten erhalten. Höchstens zwei CPU-Worker, je ein BLAS-Thread,
niceness10; keine Hardware, ROS-Nodes oder Dienste.

Im Modus `direct` verbindet eine lineare Position und die kürzeste SO(3)-
Rotation Start und Ziel. Es gibt keine Zwischenrotation oder künstliche
Auslenkung. Die Zielgelenkstellung wird auf dem vom Start fortgesetzten
IK-Zweig ermittelt; die IK-Lösung einer anderen Zielbank wird nicht kopiert.
Optional werden weitere deterministische Zielpositionen und große
Zielorientierungen erzeugt.

Ein Kandidat kommt erst für den Lehrer infrage, wenn:

1. der Start gültig ist und die IK über die Referenz fortgesetzt werden kann;
2. der tatsächlich erreichte Endzustand FCL, Abstände, Griffschluss,
   Gelenkgrenzen und Konditionsschwelle erfüllt;
3. mindestens ein innerer Referenzzustand eine FCL-Kollision aufweist.

Das61-Punkte-Raster dient als Suchfilter, nicht als Freigabe. Kollisionsfreie
Stichproben beweisen keine kontinuierlich freie Bahn. Positive Lehrerlösungen
brauchen weiterhin die dichte Prüfung des tatsächlichen Interpolanten.
Kontaktzeugen enthalten Pose, Gelenkwinkel und native FCL-Linknamen. Die
vorhandene Python-Bindung kann Contact-Objekte nicht vollständig konvertieren;
deshalb werden die nativen Kontaktmeldungen pro Zeuge gespeichert und geparst.

Die Kategorien werden getrennt geführt:

- `FCL_COLLISION`: nativer Kontakt im verwendeten Modell, zusätzlich nach
  tragenden Armen, anderen Armen, Selbst-, Objekt- und Umgebungskontakt getrennt;
- `ARM_HULL_OVERLAP`: negative Arm-Kugelhüllendistanz ohne nachgewiesenen FCL-Kontakt;
- `MARGIN_ONLY`: positive Hüllendistanz unter20mm;
- `NO_FCL_OR_ARM_MARGIN_HIT`: im Suchraster kein solcher Treffer; kein vollständiges Gütesiegel;
- ungültiger Start, IK-Fehler und ungültiger Endzustand: keine positiven Demonstrationen.

Native Kontaktlabels aus bis zu vier Zeugen pro Bahn sind keine vollständige
Liste aller Kontaktarten. Die bestehende Kollisionsgeometrie und konservative
Hüllen bleiben Modellannahmen, keine physische Kontaktmessung.

## Gemessene Ergebnisse

Ordner: `setup/research/teacher-collision-mining-20261117/`.

| Lauf | Kandidaten | Suchzeit | Ergebnis |
|---|---:|---:|---|
| `run01`: vorhandene Start-/Zielposen direkt verbinden |184|29,61s|89ohne FCL-/Armabstandstreffer,54IK-Fehler,41ungültige Endzustände|
| `run02`: zusätzlich32breite Orientierungsziele je Start-IK |920|80,74s|107ohne Treffer,723IK-Fehler,89ungültige Endzustände,1FCL-Kollisionsfall|
| `local02`: bekannte Engstelle mit stärkerer Zwischenrotation |4|siehe summary.json|vier Hüllenüberlappungen, keine FCL-Kontaktkollision|

`run02` enthält die184Verbindungen des ersten Laufs; diese Zahlen nicht als
1.104unabhängige Kandidaten addieren. Die Suchraten betragen hier6,2 bzw.
11,4Kandidaten/s einschließlich wiederverwendeter Modellinitialisierung.
Das sind **keine Raten akzeptierter Lehrerbahnen**. Der zweite Lauf zeigt
gerade, dass breite Zufallsziele eine schlechte Ausbeute haben.

Zum Vergleich: Die Medianzeiten pro akzeptiertem Fall der bisherigen drei
Datensätze liegen bei18,8s,12,1s und60,9s. Sie enthalten unterschiedliche
Anteile Optimierung und dichter Prüfung und sind keine reine Solverstatistik.
Ein schneller Filter spart unnötige Lehrerlösung/Prüfung für ungeeignete
Kandidaten; die Kosten einer schwierigen gültigen Demonstration bleiben.

Der echte Kontaktfall `north-ik3-random-011` besitzt gültige Endzustände.
Rechter vorderer Ober-/Unterarm kollidieren während der direkten Verbindung
mit `right_table_plate`. Der aktuelle Lehrer meldet dennoch
`REFERENCE_CONSTRAINTS_CLEAR`: Arm/Umgebung ist bislang keine eigene
Steuerungsbedingung seiner Optimierung. Die abschließende FCL-Prüfung
verwirft die Bahn. **Kein positives BC-Beispiel wurde daraus exportiert.**

Die erste Nachprüfung traf zusätzlich einen Rundungsfehler des Zeitgesetzes:
Fortschritt minimal über1führte zu einer Ausnahme. Der neue Mining-Adapter
begrenzt ausschließlich Abweichungen≤1e−12; größere Bereichsfehler bleiben
Fehler. Alte gebundene Quellen sind unverändert. `recheck01` bestätigt danach
die unveränderte negative Bahn mit2.108Zeitprüfpunkten und266FCL-Fehlpunkten.
Die Such-/Lehrerfehlschläge bleiben vollständig erhalten.

`recheck01/viewer.html` zeigt diese **ungelöste kollidierende Referenz**.
Sie darf nicht mit einer korrigierten Lehrerlösung verwechselt werden.
Build, vier gezielte Pythonprüfungen und acht Browserprüfungen PASS;
Screenshot `recheck01/collision-proof.png` visuell geprüft.
Die vier lokalen Kontaktproben mit2,6–3,8facher Zwischenrotation ergeben
negative Kugelhüllendistanzen bis etwa−16,7mm, aber keinen nativen FCL-Kontakt.
`local01` hatte diese noch unter `MARGIN_ONLY` eingeordnet; `local02` verwendet
die präzisierte Kategorie `ARM_HULL_OVERLAP`. Beide Laufstände sind erhalten.

## Konsequenz für die Datengeneration

Vor einer Massenproduktion sollte der Lehrer die erforderlichen
Kollisionsarten tatsächlich korrigieren können, insbesondere Arm/Umgebung.
Bei festgefahrener lokaler Optimierung kann zusätzlich eine globale
Objektbahnplanung als Initialisierung nötig sein. Das ist noch nicht umgesetzt.

Danach: gezielt um nachgewiesene Kontaktgrenzen variieren, beide Enden gültig
halten, geeignete Lösungen als Initialisierungen wiederverwenden und die
Ausbeute **akzeptierter kollisionsauflösender Aufgaben pro Rechenzeit** messen.
Ein Hauptanteil solcher Aufgaben und ein kleiner Anteil bereits freier
Kontrollaufgaben ist sinnvoller als nur sehr viele beliebige Bewegungen.
Der freie Anteil verhindert, dass unnötiges Ausweichen zum Standard wird.

Gewünschte Referenzverfolgung und globale Start-Ziel-Planung bleiben getrennte
Experimente: Eine vorgegebene kollidierende Zwischenrotation kann ein gutes
Vermeidungsbeispiel sein, obwohl der direkte Start-Ziel-Weg frei wäre. Sie
belegt dann keine anspruchsvolle globale Routenfindung.

Der Mining-Pool ist bewusst keinem Trainings-/Testsatz zugeordnet. Geteilte
Start-/Zielzustände, IK-Geschwister und perturbierte Varianten müssen vor
einer Aufteilung nach Abstammung gruppiert werden. Mehrere hundert Punkte
derselben Bahn sind keine mehreren hundert unabhängigen Aufgaben.

## Bedienung

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/mine_teacher_collisions.py \
  setup/research/two-arm-diverse-starts-20261117/run01 \
  --output-dir setup/research/teacher-collision-mining-20261117/new-run \
  --random-targets 32 --teachers 2
```

`--teachers 0` führt nur das Screening aus. `--mode local-reference` prüft
die vier vorgegebenen Zwischenrotationsverstärkungen. `--candidate-record`
prüft einen gespeicherten Kandidaten erneut in einem neuen Ausgabeordner.
Geänderte Quellen/Parameter verlangen einen neuen Ordner; die jeweiligen
`mining-source.py`-Kopien bewahren den Code früherer Nachweise.
