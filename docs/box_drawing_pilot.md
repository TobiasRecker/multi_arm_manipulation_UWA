# Box halten und zeichnen: erster Code-as-Policy-Pilot

Stand17.11.2026. Nutzer bestätigt den Pilotbeginn und präzisiert die erste
Auswertung: **verfügbare Ausführungsdaten und subjektives Feedback** genügen.
Dauer, beobachtete Kraftmaxima, Fehlgriffe, Neuansätze, Objektverlust und
Agenteneingriffe erfassen. Automatische Strichbild-/Produktqualitätsbewertung
ist eine spätere Option, keine Voraussetzung für den Einstieg.

## Erster Nutzerfeedbackzyklus: weniger Umkonfiguration oder weniger Wartezeit

Der Nutzer hinterfragt den Wechsel vor dem Unterseitenkreis und schlägt
eine günstigere Haltepose oder gleichzeitige Bewegung vor. Die Rückmeldung
ist an `run08/transfer_to_z_min` gespeichert. Zwei neue Varianten sind
vollständig modellgeprüft und mit dieser Feedbackquelle verknüpft:

| Variante | Gesamte Modellzeit | Größter LF-Gelenkhub beim Übergang |
|---|---:|---:|
| run08, bisher seriell |66,858s|165,40°|
| overlap01, gleiche Boxposition, gemeinsamer Übergang/Rückweg |49,837s|165,40°|
| closer01, Box8cm näher zumLF, gemeinsamer Übergang/Rückweg |68,073s|33,66°|

`overlap01` spart17,022s/25,46%Modellzeit durch Überlappung. `closer01`
vermeidet den großen Wristwechsel, benötigt unter denselben v/a/Ruck-Grenzen
aber etwas länger. Das Hin-/Zurückversetzen der Box ist mitgerechnet.
Alle Varianten starten und enden mit denselben24Armgelenkwerten; es wurde
kein günstigerer Anfangszustand still eingesetzt. Die Originalgriffe und
Kreisreferenzen bleiben gleich.

Vergleich öffnen:

```bash
xdg-open setup/tasks/box_drawing_pilot_20261117/feedback-comparison01/viewer.html
```

Die alte Umkonfiguration entstand aus der seriellen Aufgabenkomposition und
der Wahl des LF-IK-Zweigs. Der nähere Zweig kollidiert beim Ansetzen mit
`left_front_forearm_link`/`left_front_wrist_2_link`. Daraus folgt keine
allgemeine Notwendigkeit eines großen Zweigwechsels; die nähere Boxpose
liefert eine durchgängige Alternative. Höhere Boxposen und weitere Startzweige
wurden als Stichproben untersucht; der Vergleich oben enthält nur die
vollständig ausgeführten Modellprogramme.

Reproduktion: beim `run`-Befehl unten `--variant overlap` oder
`--variant closer_coordinated` und optional `--feedback-from RUN08` ergänzen.
Dabei RUN08 durch den tatsächlichen run08-Pfad ersetzen. `--variant baseline`
bleibt der Standard, um die ursprüngliche Referenz nicht still zu ersetzen.
NeueAusgabeordner verwenden. Beide neuen Varianten haben separate
`independent-audit.json`;35/39Browserprüfungen und7Vergleichsprüfungen
bestanden, Screenshots sind visuell geprüft.

## Aktueller Funktionsstand

Ein gespeichertes Python-Aufgabenprogramm wird gegen einen transportfreien
Modelladapter ausgeführt. Zwei rechte Arme halten einen gemeinsamen virtuellen
Karton; `left_front` führt einen virtuellen Marker, `left_rear` bleibt geparkt.
Anfangszustand ist eine explizite in-air-Modellfixture mit offenen Greifern,
16cm über der Ausgangslage des Assets. Anfahrt, Greifen und physisches Tragen
sind weitere Integrationsschritte.

Die erste Vorführung bearbeitet **zwei benannte Flächen**, Längswand `y_max`
und Unterseite `z_min`. Die Kreisradien betragen25mm. Der Marker liegt nominell
300mm entlang Tool0+Z; sein Körper hat3mm Radius und eine6mm-Kegelspitze.
Diese Geometrie ist ein virtuelles Werkzeug, keine vermessene Halterung.
Die übrigen Seiten bleiben außerhalb dieses ersten Teilversuchs.

Das tatsächlich gespeicherte und ausgeführte Programm:

```python
def task(api):
    api.draw_face("y_max")
    api.rotate("present_bottom", 80.0)
    api.draw_face("z_min")
    api.park_worker()
    api.rotate("return_box", 0.0)
```

`draw_face` führt Annäherung, Kreis und Rückzug aus. Ein geprüfter freier
Gelenktransit wählt den passenden IK-Zweig für die Unterseite; Annäherung und
ganzer Kreis werden schon bei der Auswahl berücksichtigt. Vor der letzten
Boxdrehung geht der Arbeitsarm in seine freie Ausgangsstellung zurück.
Alle Bewegungen verwenden die vorhandenen glatten Zeitgesetze. Tragende Arme
behalten feste Objekt→TCP-Transformationen und ein gemeinsames Zeitgesetz.

Backend: **kinematic_model**, ohne ROS-Nodes, Controllerkommandos oder
Kontaktphysik. Die eingezeichneten Spuren visualisieren die Werkzeugreferenz.
Der Episodenstatus `MODEL_SEQUENCE_COMPLETE` bezeichnet genau diesen Umfang.
Kraft, Fehlgriffe, Neuansätze und Objektverlust bleiben **UNKNOWN**. Bestehende
Simulationen, Treiber und Kameradienste werden nicht verändert.

## Vorschau und Bedienung

Vom Workspace aus:

```bash
xdg-open setup/tasks/box_drawing_pilot_20261117/run08/viewer.html
```

Die englische, kontrastreiche Vorschau bietet Play/Pause, Zeitregler,
Phasenauswahl, Orbit/Zoom, Rollen, Ausführungsdaten und den Programmtext.
Wiedergabe1× ist Modellzeit;3×/10× beschleunigen nur die Ansicht.

Im Bereich **Your feedback** Phase wählen und Originaltext eingeben.
**Export feedback JSON** lädt eine Datei herunter. Das schreibt noch nichts
in den lokalen Episodenspeicher. Die Rückmeldung anschließend importieren:

```bash
python3 src/multi_arm_manipulation_UWA/tools/box_drawing_pilot.py feedback \
  setup/tasks/box_drawing_pilot_20261117/run08 \
  --file /absoluter/Pfad/box-drawing-feedback.json
```

Alternativ denselben vom Nutzer tatsächlich geäußerten Text mit `--text` und
`--phase return_box` speichern. `--phase overall` gilt für die gesamte Aufgabe.
Ein Feedbackexport aus einer anderen Episode oder mit unbekannter Phase wird
abgewiesen. Rückmeldungen nach Abschluss verändern das Ausführungsergebnis
nicht und erzeugen keine automatische Programmänderung. Die HTML-Vorschau
enthält den ursprünglichen Stand; spätere Rückmeldungen zeigt die CLI:

```bash
python3 src/multi_arm_manipulation_UWA/tools/box_drawing_pilot.py summary \
  setup/tasks/box_drawing_pilot_20261117/run08
python3 src/multi_arm_manipulation_UWA/tools/box_drawing_pilot.py history \
  setup/tasks/box_drawing_pilot_20261117
```

Auch Feedback direkt im Gespräch kann der Agent anschließend derselben Phase
zuordnen und über diese Schnittstelle speichern. Es wird kein Nutzerfeedback
als Beispiel erfunden oder stellvertretend eingetragen.

## Episoden und schlanke Auswertung

Jeder Lauf besitzt `policy.py`, `program.json`, Ergebnis oder Fehlerbericht
sowie `episode/episode.json`, `events.jsonl` und `summary.json`. Ereignisse
tragen Quelle, Phase und bei Modellschritten Modellzeit. Manifest und
Ereignisfolge werden perHash gebunden; Rückmeldungen bleiben im Originaltext.

Der Speicher trennt:

- **Dauer:** Modellzeit, gemessene Rechenzeit und spätere tatsächliche
  Ausführungsdauer. Wiedergabe-/Pausenzeit ist keine Roboterzykluszeit.
- **Ereignisse:** erkannte Fehlgriffe/Neuansätze/Objektverluste und
  Agenteneingriffe. Null bedeutet nur bei ausdrücklich vorhandenem Beobachter
  „kein Ereignis registriert“; ohne Beobachter steht `null`/UNKNOWN.
- **Nutzermeldungen:** subjektive oder nachträglich berichtete Ereignisse
  bleiben getrennt von automatisch erkannten Messungen.
- **Kraft:** beobachtete Normmaxima pro Sensor, Bezugsframe und Bezugspunkt.
  TCP- und Backenkraft werden nicht vermischt. Sequenzlücken bleiben sichtbar;
  ein Maximum aus vorhandenen Samples behauptet keine vollständige Abdeckung.

Die Kraft-/Ereignisschnittstellen sind für spätere Ausführungsadapter
vorbereitet. In dieser Stufe liefert nur das Modell Phasenergebnisse und die
Programmsteuerung ihre eigenen Eingriffe. Es gibt noch keinen angeschlossenen
Kontakt- oder Hardwaredetektor und keinen schnellen Kamerarecorder.

Verworfene Planungszweige und Entwicklungsfehler bleiben Diagnoseinformation.
Sie werden nicht nachträglich als Eingriffe während einer tatsächlich
ausgeführten Roboteraufgabe gezählt. `history` liefert einen kompakten Abruf
früherer Ergebnisse und Korrekturen für den nächsten Entwicklungsauftrag.
Automatische Codeverbesserung und Teleopübernahme sind weitere Ausbauschritte.

## Reproduktion und Prüfung

Neue Modellvorführung in einen noch nicht vorhandenen Ausgabeordner:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  src/multi_arm_manipulation_UWA/tools/box_drawing_pilot.py run \
  --source setup/research/offline-carton-sides-20261117/standard/smoothed/result.json \
  --output setup/tasks/box_drawing_pilot_repeat
```

Die CLI lädt ihre neuen Pythonmodule direkt aus dem Quellbaum. Gemeinsame
native Kontaktplugins werden dafür nicht neu installiert. Die vorhandene
Lyrical-Umgebung liefert Modell-/MoveIt-/Kinematikabhängigkeiten.

Geprüft werden tatsächliche Gelenkinterpolanten mit≤20ms Raster und≤0,01rad
Gelenkänderung je Schritt: FCL für vorhandene Roboterszene/bewegtes Objekt,
alle sechs Armpaarhüllen mit20mm Abstand, Griffschluss und virtuelle Marker-
Körper gegen Boxhülle, Armhüllen und Umgebungshüllen. Diskrete Modellprüfung,
keine kontinuierliche Kollisionsgarantie, dynamische Stopp- oder Lastprüfung.
Die vorhandenen Modelllücken visueller Links bleiben bestehen.

Ein separater Audit rekonstruiert FK, beide Halteframes, Kreisreferenzen,
geparkten Arm, Phasenanschlüsse, Zeit-/Episodenbezug und Ableitungsspitzen
aus den gespeicherten Interpolanten, ohne die DrawingModel-API zu verwenden:

```bash
python3 src/multi_arm_manipulation_UWA/tools/verify_box_drawing_pilot.py \
  setup/tasks/box_drawing_pilot_repeat \
  --output setup/tasks/box_drawing_pilot_repeat/independent-audit.json
```

Die Ergebnisse früherer Versuche bleiben erhalten: run01 scheiterte an der
virtuellen Markerspitzengeometrie; run02/03 am Unterseitenübergang, run04 an
einer Selbstkollision des Arbeitsarms beim Ansetzen. Diagnose nennt
`left_front_forearm_link`/`left_front_wrist_2_link`. run05 führte beide Kreise
aus, scheiterte aber bei der Boxrückdrehung am noch im Schwenkraum stehenden
Marker. run06/07 absolvieren den vollständigen korrigierten Modellablauf;
run08 ergänzt die korrigierte Phasenauswahl der Vorschau und bindet die
verwendeten Implementierungen und Modelldaten.

run08 besteht mit zehnPhasen/66,858sModellzeit,3358Prüfzuständen und
230,818mm minimalem Armhüllabstand. Der separate Audit besteht mit1510FK-
Zuständen und2001Ableitungsproben jePhase. 13Softwaretests,39Browserchecks
und visuelle Screenshotkontrolle bestanden. Prüfnachweise befinden sich als
`independent-audit.json`, `browser-check.json`, `browser-dom.html` und
`preview.png` imLaufordner. Die Browserprüfung hat kein echtes Nutzerfeedback
eingetragen. Alle Aussagen beziehen sich auf den bezeichneten Modellumfang.

## Nächster Schritt

Zuerst die Sequenz und das subjektive Nutzerfeedback bearbeiten. Danach den
Mehrrollenablauf an Kontaktphysik und vorhandene Ausführungsbeobachter
anschließen, sodass echte Ausführungsdauer, Kraft und Griff-/Verlustereignisse
an derselben Schnittstelle eintreffen. Detaillierte automatische Strichbild-
oder Qualitätsoptimierung bleibt optional.
