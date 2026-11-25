# Pick pen from holder

Eigenes Programm `pen-left-rear-v1` in **UWA Robot Power → Program library**.
Es verwendet ausschließlich **left_rear** für die Stiftaufnahme. Der Nutzer
hat am24.11.2026 die mittige Montage beider Marker und den vollständigen Sitz
bestätigt sowie die schwarze Außenkante mit30mm nachgemessen. Für diesen
Programmstand ist die Kappe abgenommen, wie im entworfenen Halter vorgesehen.

## Bedienung

- **Inspect pen** nimmt ein frisches natives OAK-Pro-Bild auf und bestimmt die
  Markerpose. Es sendet keine Arm- oder Greiferbefehle.
- **Plan pickup only** liest zusätzlich die aktuelle Vierarmkonfiguration vom
  N100 und prüft die gesamte Anfahrt, Einfahrt und Entnahme offline auf ROSmini.
  Es sendet ebenfalls keine Arm- oder Greiferbefehle.
- **Start program** verwendet dieselben aktuellen Eingaben und vollständigen
  Planprüfungen. In **Motion review** zuerst die Anfahrt/Einfahrt prüfen. Der
  Greifer wird an der Vorposition aktiviert/geöffnet. Nach der Einfahrt zeigt
  eine zweite Kontaktprüfung ein frisch aufgenommenes OAK-Pro-Bild. Diese
  Freigabe umfasst Schließen und das zuvor geprüfte senkrechte Ausheben.

Left rear vorher in **UWA Robot Power** betriebsbereit machen. Den bestehenden
Arbeitsbereich freigeben. Das Programm startet keine UR-Programme und führt
keine Power-/Brake-/Sicherheitsquittierung aus. Das neue Aufgabenvertrauen ist
von dem des Kartonprogramms getrennt; die erste Bewegung und der erste Kontakt
werden ausdrücklich geprüft. Die Freigabe ist an die konkrete Revision gebunden.

Nach erfolgreicher Entnahme bleibt der Arm oben mit geschlossenem Greifer.
Meldet der vorhandene Schließabschluss keinen Objektkontakt, endet die
Aufgabe vor dem Hub mit `NO_OBJECT_CONTACT`. Objektkontakt allein beweist
weiterhin keine tragfähige Klemmung oder tatsächliche Stiftanwesenheit.
Bei Fehlern wird kein möglicherweise belasteter Greifer automatisch geöffnet,
kein Griff wiederholt und keine alternative ungeprüfte Bahn ausgeführt.
Der Workflow protokolliert Aktivieren, Öffnen und Schließen einzeln mit
Ergebnis oder Fehler und der letzten vorhandenen Action-Rückmeldung.
Greifer-Timeouts im aktualisierten Transport nennen den Parameterschritt,
Sollwerte und zuletzt gelesene Register; es werden dafür keine zusätzlichen
Geräteabfragen eingeführt. Der Transport muss auf dem Steuerhost geladen sein;
der lokale Quellstand allein aktualisiert keinen laufenden Greiferdienst.

**Approved** gibt die geprüfte Aufgabe frei; ein bestehender Software-Stopp
braucht zusätzlich das ausdrückliche **RESUME**. Vor einem neuen Armkommando
wartet das Stiftprogramm die vorhandene Resume-Bestätigung und vollständige
Freigaberampe links hinten ab. „Waiting for the left-rear controller to
confirm operator RESUME“ bezeichnet diesen Übergang, keine neue Reviewfrage.

## Wahrnehmung

USB-OAK-D Pro AF `18443010314F3B1300`, Fokus112, native4056×3040; die
Ethernet-OAK4 ist ein anderes Gerät. Die fokusgebundenen Intrinsics und die
bestehende zwölfstündige USB-Kamerasitzung werden übernommen. Für die
Stiftpose wird seit25.11. **das linke Tischboard im aktuellen Stiftbild**
als lokaler Bezug verwendet: mindestens12 Marker und Prüf-RMS<2px. Der
Nutzer bestätigt dieses Board als unverändert seit der Basiszuordnung.
Die linke Referenz wird pro Lauf mit Bild-/Quellhash gespeichert; fehlt ihr
Nachweis, erfolgt kein stiller Rückfall auf den widersprüchlichen rechten
Bezug. Keine globale Kalibrierung oder Basisbindung wird dabei geschrieben.

Marker97 liegt oben,96 auf der Seite senkrecht zu den Greifflächen. Beide sind
`DICT_4X4_100`,30mm einschließlich schwarzem Rand.97 gehört hier zum Stift,
auch wenn der Druckbogen diese ID ursprünglich als Halter beschriftete.

OpenCV versucht native Kantenanpassung, native Subpixelmessung und lokale
Kontrastanhebung. Die PnP-Auswertung prüft beide ebenen CAD-Flächen gemeinsam
und berücksichtigt die vier möglichen Druckrotationen je Marker. Die mittige
Klebung ist eine bestätigte Montageannahme, keine unabhängige Vermessung.
Erste Qualitätswerte: RMS höchstens2,5px, einzelne Ecke höchstens5px, aufrechte
Lage innerhalb8°. Zusätzlich muss die nominale Stiftspitze zur Sitzhöhe am
linken Tisch passen. Dies sind Bild-/Planeingangsprüfungen, keine neuen
Laufzeitwächter für Roboter oder Greifer.

Bei fehlender oder unplausibler Messung erhält Gemini Hydrogen über das
vorhandene Antigravity-Konto das aktuelle Bild und den lokalen Fehler. Der
Nutzer hat diesen Fallback für das Stiftprogramm beauftragt. Gemini liefert
nur einen Bildausschnitt in der **nativen Sensororientierung**. OpenCV misst
dort erneut. Eine von Gemini erfundene metrische Pose, fehlende Markerecken
oder ein unzureichender lokaler Fit führen nicht zu einer Fahrt. Die reine
Anzeige wird wegen der invertierten Montage um180° gedreht.

Die native USB-Pipeline bleibt für Anfangs- und Einfahrbild derselben Fahrt
geöffnet. Vor dem Anfangsbild werden drei fortschreitende Vorschauframes mit
stabilem Belichtungsprodukt abgewartet. Andere Kamerasitzungen werden nicht
beendet. Originalbilder, Geräte-/Fokusdaten, Zeitgrenzen, Pixelkoordinaten,
Gemini-Antwort und SHA-Bindungen bleiben im Run-Ordner.

## Geometrie und Bewegung

- Ganze Folge vor der Anfahrt prüfen: Vorposition150mm oberhalb der Greiflage,
  senkrechte Einfahrt, Greifen, senkrechte Entnahme150mm.
- Adapterdatum wie im akzeptierten CAD: obere Fläche49mm, seitliche
  MarkerflächeY=15,5mm und MarkerzentrumZ=33mm. GreifreferenzZ=46mm nahe dem
  oberen Adapterende, damit die Backen den Halterrand freihalten. Robotiq-TCP
  nominell145mm ab Greiferbasis, weiterhin keine reale TCP-Einmessung.
- Beide um180° äquivalenten Greiferorientierungen und mehrere IK-Zweige vor
  der Auswahl nach Gelenkweg vergleichen und die Kandidaten vollständig prüfen.
  Ganze Folge und Freiräume entscheiden, danach Weglänge/Anfahrt. Kein
  Austausch des benannten Arms und kein unvollständiger Anfahrplan.
- Reale Werkskinematiken, alle sechs Armpaare, Selbst-/Tisch-FCL und bestehende
 40-mm-Nachbararmmargen weiterverwenden. Halter und Adapter aus dem akzeptierten
  STEP exportiert; frei liegender Stiftschaft konservativ als21mm-Zylinder.
- Die zusätzliche Offline-Szene verwendet für left_rear feinere konvexe
  Öffnungshüllen statt der groben50mm-Sphärenkachelung. **Der gesamte
  Öffnungsbereich bleibt enthalten**: Meshstützpunkte über den vollständigen
  Gelenkbereich, maximal0,02rad-Abstand und analytische Bewegungsinflation
  zwischen den Stützstellen. Die aktive Hardwaregeometrie bleibt unverändert.
- Nur beabsichtigte Pad-/Adapterkontakte und Stift-/Halterführung werden in
  dieser zusätzlichen Szene ausgenommen. Halter gegen Backen/Armkörper,
  freier Schaft gegen Greifer und alle fremden Körper bleiben geprüft.
- Getragenen Stift einschließlich Adapter für die gesamte Aushebebahn
  prüfen; RViz zeigt ihn während **lift** am Greifer.

Die genehmigte Gelenkgrenze bleibt0,1rad/s und die bestehende Beschleunigung
0,2rad/s². Der gemeinsame Regler steht derzeit bei einem Drittel: Werkzeug-TCP
höchstens83,3mm/s. Kontinuierliche C2-Zeitgesetze und die vorhandene Prüfung
wirklicher Controllerinterpolanten bestimmen das Tempo; keine Streckung zur
Beobachtung. Greifer wie im bestehenden freigegebenen API: rawFOR0/SPE16,
keine neue Kraft- oder Geschwindigkeitsfreigabe. Befehlsabschluss allein beweist
weder Haltekraft noch einen gegen Verrutschen gesicherten Stift.

## Quellen und Ablage

Definition: `config/pen_programs/pen-left-rear-v1.json`. Runner:
`tools/run_pen_program.py`, `tools/prepare_pen_grasp.py`, `tools/execute_pen_grasp.py`.
Das aktive Schutzbackend und ein expliziter Minimal-Runtime-Pfad werden wie
beim Kartonprogramm übernommen. Minimalbetrieb verwendet den gemeinsamen
Pausenadapter; keine alten Wächter werden dort erneut aufgebaut.

Ausführungshelfer werden nur im jeweiligen N100-Run-Verzeichnis bereitgestellt
und vor beiden Phasen per SHA geprüft. Der Run nutzt das bestehende
Review-Datenformat und dieselbe SQLite-Datenbank. Kein Runtime- oder
Schutzdienstwechsel gehört zur Programminstallation.

Ergebnisse unter `setup/tasks/uwa_program_library/<run-id>/`, zugehöriger
N100-Pfad in der Run-Ausgabe. Entwicklungs-/Bildnachweise:
`setup/tasks/pen_pick_20261124/`. Rohbilder bleiben außerhalb Git.

## Geprüfter Stand24.11.2026

Die vollständige Plan-only-Kette mit neuem OAK-Pro-Foto und tatsächlichem
N100-Start war erfolgreich (`library-plan-current-02`):1,5335px Pose-RMS,
27,678s Anfahrt,8,069s Einfahrt und8,069s Entnahme,43,817s gesamt. Die
analytischen Interpolationsspitzen liegen innerhalb0,1rad/s und0,2rad/s².
Weitere376 nicht auf dem Erzeugungsraster liegende Öffnungszustände über
acht Greiferkörper waren in den Hüllen enthalten. Portable RViz-Meshauflösung
und Wiedergabe-Timeline geprüft; kein visueller RViz-Nachweis behauptet.
Die tatsächliche Stiftaufnahme wurde bei dieser Programminstallation nicht
ausgelöst. Bedienoberflächenzugriff war nicht verfügbar; den aktiven
Programmeintrag und seine Aktionen über den lokalen HTTP-Katalog verifiziert.
59 gezielte Tests und die run-spezifische N100-Import-/Plandateiprüfung
bestanden; letztere erzeugte keine ROS-Clients oder Bewegungs-/Greiferbefehle.

Erster anschließender realer Lauf am24.11. erreichte die Vorposition, brach
jedoch bei der Greifervorbereitung vor der Einfahrt ab. Die Ursache der nicht
bestätigten Parameter ist noch offen; siehe [Diagnose](../work/pen-gripper-abort-20261124.md).
Die Diagnoseergänzung vom25.11. ist mit55 gezielten Offline-Tests geprüft und
der Transport auf dem wieder erreichbaren N100 geladen. Parameterproben bei
inaktivem Greifer bestätigten serverseitig FOR0/SPE16. Nach erneuter
Bereitschaft und ausdrücklicher Nutzerfreigabe bestand um15:18AWST ein
einzelner realer Aktivierungs-/Öffnungstest über die reguläre ROS-API:
ACT1/STA3/FLT0/OBJ3/POS3/PRE0/FOR0/SPE16. Der ursprüngliche Timeout trat
dabei nicht erneut auf; eine dauerhafte Ursachenbehebung ist nicht
nachgewiesen. Kein erfolgreicher realer Stiftgriff ist damit nachgewiesen.

Beim anschließenden vollständigen Lauf25.11. meldete der Nutzer einen
seitlichen Fehlgriff. Der Hub wurde nach angenommener Kontaktfreigabe trotz
fehlendem Objektkontakt ausgeführt; obige Aufgabenentscheidung korrigiert
dies für künftige Läufe. Die Zelle ist auf ausdrücklichen Auftrag pausiert.
Eine kürzere vollständig geprüfte symmetrische Orientierung ist offline
nachgewiesen. Der Bezug zum rechten Tisch widerspricht im Einfahrbild dem
linken Board um rund40mm seitlich. Ein aktueller lokaler linker Boardfit ist
vorbereitet und nach Nutzerbestätigung des unbewegten/unveränderten linken
Boards in der aktiven Programmdefinition eingeschaltet. Ein neuer realer
Versuch benötigt aktuelle Eingaben und Reviews.
[Diagnose und Einschränkungen](../work/pen-grasp-offset-20261125.md).
