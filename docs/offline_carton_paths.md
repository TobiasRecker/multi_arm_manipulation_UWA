# Schritt 3: feste Greifziele am Avocado-Karton

[Interaktive Bahnansicht öffnen](../../../setup/research/offline-carton-paths-20261117/case03/viewer.html).
Die Datei in einem Browser öffnen. **Play preview** startet die Modellanimation,
der Schieber erlaubt einzelne Zeitpunkte. Mit Ziehen drehen, mit dem Mausrad
zoomen. **Joint solution 1–3** zeigt verschiedene Gelenklösungen und Wege zu
**denselben vier TCP-Posen**. Die Kiste und Zielkreuze bleiben unverändert.

## Aufgabe und Modellannahmen

Nutzerauftrag17.11.: jeder UR soll die ihm nächstgelegene Ecke des bekannten
Avocado-Kartons gerade von oben greifen. Die ursprüngliche Nullstellung
`[0,0,0,0,0,0]` schneidet im Modell mit linkem vorderem Handgelenk/Greifer die
rechte Tischplatte. Nach diesem Nachweis wählte der Nutzer ausdrücklich für
alle vier Arme `[0,-90,0,-90,0,0]` Grad. Die verworfene Nullstellung lässt sich
im Viewer gesondert anzeigen; von ihr wird keine Bahn erzeugt.

Das bestehende Asset `carton_avocado_v1` bleibt an seiner bestehenden
bildbasierten Modellpose; es wird nur für diese Offlineplanung ausdrücklich
als statisches Mesh-Hindernis in das Kollisionsmodell aufgenommen. Weder
gemeinsame Szene noch laufende Simulation werden verändert. Maße ungefähr
404×342×163mm, angenommene Wandstärke2,5mm. Hinterer Basisabstand99,1cm;
Montage-/Objektregistrierung bleiben vorläufig. Modellpose und URDF sind im
Ergebnis eingefroren, Mesh-Hashes vor erneuter Verwendung geprüft.

Die Zuordnung erfolgt nach dem kleinsten horizontalen Abstand zwischen Basis
und oberer Ecke. In dieser Szene ist sie eindeutig, jede Ecke erhält genau
einen Arm. Abweichende Layouts mit mehrfach zugeordneter Ecke werden abgewiesen.
Es gibt **eine einzige feste Zielpose pro Arm**, keine austauschbaren Aufgabenposen.

Für diesen geometrischen Test ist der nominale Greifmittelpunkt15mm unterhalb
der oberen Ecke angesetzt. Die Greiferachse zeigt senkrecht nach unten, die
Schließrichtung diagonal über die Ecke. Der nominale TCP liegt145mm entlang
der lokalen +Z-Achse der Greiferbasis, wie im vorhandenen geometrischen
Greifansatz. Das ist kein physisch kalibrierter Greif-TCP. Die Greifer bleiben
offen. Erreichbarkeit und Freiraum sind keine Bestätigung eines tragfähigen
Eckgriffs; Schließen, Kontakte, Kräfte, Verformung und Hub sind nicht getestet.

## Erzeugte Wege

1. Multistart-IK liefert verschiedene Gelenkstellungen für dieselbe feste Pose.
   Gemeinsame Endstellungen werden mit voller Szene, bestehenden
   Nachbarreserven und statischer Mindestreserve aller sechs Armpaare geprüft.
2. Von jeder geeigneten Zielkonfiguration wird die IK120mm senkrecht nach oben
   fortgesetzt. Dadurch bleibt die IK-Verzweigung während der abschließenden
   Abwärtsbewegung erhalten; Sprünge werden abgewiesen.
3. Eine Gelenkbewegung verbindet den aufrechten Start mit dieser Vorgriffpose.
   Bei Scheitern werden zusätzliche Gelenkzwischenpunkte versucht. Danach
   folgt die senkrechte120mm-Annäherung mit konstanter Orientierung.
4. Eine gemeinsame quintische Fortschrittsfunktion pro Einzelprimitive sorgt
   für Geschwindigkeit und Beschleunigung null an den Abschnittsgrenzen.
   Der Übergang ist C2, mit einem Halt an der Vorgriffpose. Die kartesische
   Annäherung verwendet einen kubischen Gelenkspline durch die IK-Stützstellen.
   Die geglättete Kurve wird zusätzlich auf Geraden-/Orientierungstreue geprüft.

Dies sind **MoveJ-/MoveL-artige geometrische Planungsprimitive**, keine
Ausführung nativer UR-Funktionen und kein Nachweis ihrer identischen Interpolation.
Die gespeicherten Kurven sind nicht als ausführbare Controllertrajektorien
freigegeben (`executable:false`). Die nominale Zeitabschätzung nutzt das
vorhandene langsame Planungsprofil; der Viewer läuft standardmäßig20-fach.
Das verändert nur die Wiedergabe, nicht die gespeicherten Zeiten oder Kräfte.

## Was geprüft wurde

Jede Einzelbahn wird gegen Selbstkollision, Tische, die Kiste und die festen
Basiskörper aller Roboter geprüft. Die beweglichen Teile der anderen Arme
sind dabei noch keine zeitlich koordinierten Hindernisse. Gemeinsame
Zielstellungen sind separat voll geprüft. Eine zusätzlich berechnete
Gleichzeitig-starten-Diagnose berücksichtigt dann wieder alle vier Arme.

Die Prüfpunkte liegen auf der tatsächlich geglätteten Kurve. Die Abtastung wird
verfeinert, bis auf dem Prüfgitter höchstens0,005rad Gelenkunterschied zwischen
benachbarten Punkten auftreten. Das ist eine **diskrete Prüfung**, kein Beweis
über das kontinuierliche überstrichene Volumen zwischen den Punkten.
Die Abtastung der gemeinsamen Zeitdiagnose beträgt höchstens0,1s.

Ergebnis des eingefrorenen Beispiels:

- Je12IK-Kandidaten,20.736gemeinsame Endkombinationen vollständig untersucht;
 18bestehen die Modell-/Reserveprüfung. Vollständigkeit nur innerhalb dieser
  behaltenen Kandidaten, nicht für sämtliche IK-Lösungen.
- Acht erfolgreiche Einzelbahnen: links vorne2, links hinten2, rechts vorne3,
  rechts hinten1. Daraus zwölf kompatible vollständige Bahnzusammenstellungen.
- Eine weitere links-hinten-IK-Verzweigung scheitert bei allen drei versuchten
  Gelenkrouten an statischer/Selbst-/Kistenkollision. Die Ablehnungen bleiben
  im Ergebnis erhalten; daraus folgt keine allgemeine Unmöglichkeit der Route.
- Unabhängige dichtere Nachrechnung:32.784Einzelbahnzustände bestehen.
  Größter beobachteter Gelenkschritt0,002312rad, Positionsabweichung von der
  vorgeschriebenen Geraden höchstens0,000508mm. Das ist numerische
  Modellgenauigkeit, keine physische Positioniergenauigkeit.
- Die vorgeschlagene Bahnzusammenstellung hat220,7s nominale Gesamtdauer bei
  gleichzeitigen Starts und Warten am jeweiligen Ziel. Von2.208geprüften
  Zeitpunkten verletzen423die Paarreserven. Kleinster Armhüllabstand155,8mm;
  keine FCL-Kollision an diesen Prüfpunkten. **Noch keine abgestimmte gemeinsame
  Trajektorie.** Orange Zeitleistenabschnitte markieren diese Konflikte.

88gezielte Pythonfälle und nativer Vorfiltertest bestanden, davon sieben neue
Tests für diese Stufe.20Browser-Bedienszenarien und identische End-TCPs in allen
drei Vorschauvarianten bestanden; Start und Ende visuell geprüft.
Logs: `setup/logs/uwa-carton-*`. Der erste Aufbauversuch scheiterte im nativen
Mesh-Lader; seine Logs und der unvollständige Fall bleiben erhalten. Der
erfolgreiche Modellaufbau verwendet eine explizite `file:`-Mesh-URI und hält die
nativen Modellbesitzer am Leben. Erfolgreicher Entwicklungsfall `case02`,
reproduzierbarer Endstand `case03`; keine gescheiterten Artefakte überschrieben.

## Reproduzieren

Motionpaket wie in [Schritt1](offline_goal_candidates.md#build-and-run) bauen.
Aus `~/UWA_ws`, mit frischen Ausgabepfaden:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/plan_carton_corner_paths.py \
  --layout setup/research/offline-carton-paths-20261117/case03/layout.yaml \
  --config setup/research/offline-carton-paths-20261117/case03/motion.yaml \
  --output-dir /tmp/uwa-carton-paths-new
python3 src/multi_arm_manipulation_UWA/tools/verify_carton_paths.py \
  /tmp/uwa-carton-paths-new --output /tmp/uwa-carton-paths-new/verification.json
python3 src/multi_arm_manipulation_UWA/tools/preview_carton_paths.py \
  /tmp/uwa-carton-paths-new --output /tmp/uwa-carton-paths-new/viewer.html
xdg-open /tmp/uwa-carton-paths-new/viewer.html
```

Ohne `--layout/--config` wird ein neuer Snapshot der aktuellen Standardwerte
verwendet. Kein ROS-Knoten, Simulator, Kamera- oder Roboterzugriff ist nötig.

Nächster Schritt4: Zeitkoordination dieser bekannten Einzelwege mit möglichen
Wartezeiten und Startversätzen, bei Bedarf andere IK-/Wegalternative. Danach
vollständige gemeinsame Prüfung. Gleichzeitig bewegte Basen bleiben ein
späterer Ausbau; dieser Fall verwendet feste Tisch-/Basislagen.
