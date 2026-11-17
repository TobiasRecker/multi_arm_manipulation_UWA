# Kollisionsfreie Planung für vier URs mit beweglichen Basen

Stand: 16. November 2026. Ziel ist ein Vergleich klassischer und aktueller
Verfahren als Grundlage für die spätere Anwendung auf die UWA-Zelle.
**Nachfolgend präzisiert:** Aktueller Umfang ist ausschließlich Offlineplanung
mit bekannten Bewegungen aller Roboter/Basen. Die unten recherchierten MPC-/CBF-
Ansätze bleiben Literaturausblick, kein aktueller Implementierungsschwerpunkt.
Der Nutzer hat ausdrücklich **gleichzeitige Basis- und Armbewegungen** als
Ziel bestätigt. Zwei Tische mit je zwei starr montierten URs bilden das erste
Fallbeispiel; vier unabhängig mobile Manipulatoren sind der allgemeinere Fall.

Die aussichtsreichste Vergleichsstruktur besteht aus gemeinsamer Planung,
Einzelplanung mit zeitlicher Konfliktauflösung und gemeinsamer prädiktiver
Trajektorienoptimierung. CDF/GCDF ist darin eine alternative Abstands- und
Gradientenrepräsentation. Es ersetzt nicht automatisch globale Wegsuche,
Mehrroboterkoordination und Ausführungsüberwachung. Diese Einordnung ist unsere
technische Ableitung, keine bereits gemessene Rangfolge für bewegliche UWA-Basen.

## Bisherige Gespräche und vorhandene Ergebnisse

Die Recherche umfasst relevante lokale Originalgespräche unter
`~/.codex/sessions`, die Projektübergabe und die unten verlinkten Ergebnisse.
Damit ist keine Vollständigkeit aller früheren, gegebenenfalls nur in anderen
ChatGPT-Sitzungen gespeicherten Gespräche behauptet.

| Gespräch oder Arbeit | Inhalt und heutige Bedeutung |
|---|---|
| 13.11.2026, Kollisionsvermeidung für vier URs | Nutzer trennt einen einfachen 10-Hz-Abstandswächter von vorgeschalteter kollisionsfreier PTP-Planung. Potentialfelder, zirkulare Felder und CDF werden diskutiert. RRTConnect und ein unabhängiger CF-inspirierter Ansatz werden zum Vergleich beauftragt. |
| 16.11.2026, CDF wieder aufgenommen | Zunächst ein bewegter UR; drei Fremdarme als starre Hindernisse. Originalpaper und Originalcode als Referenz. |
| 16.11.2026, Darstellung und Rechenzeit | Kugelgeometrie von CDF unterscheiden; Gelenkradian von Metern trennen. Nutzer schlägt hierarchische Hüllen vor, anschließend wird der Arm-AABB-Vorfilter umgesetzt. |
| Aktueller Auftrag | Methoden und aktuelle Literatur zusammentragen, anschließend Anwendung auf veränderliche Basislagen. Auch während der Bewegung verändern sich die Basislagen. |

Originalbelege: lokaler Rollout
`2026/11/13/rollout-2026-11-13T11-15-13-01a1d2e6-f258-77b0-97f2-650527ff238a.jsonl`,
Benutzereinträge in Zeilen 14, 127, 5868, 6271, 6300 und 6536.

Bereits vorhandene Bausteine:

- [Vierarmplanung](four_arm_motion.md): gemeinsame OMPL-RRTConnect-Planung und
  unabhängiger CF-inspirierter Rollout, vollständige MoveIt/FCL-Endprüfung,
  zeitparametrierte Wege und gemessene Fortschrittsbarrieren bei der Ausführung.
  Vollständig bezieht sich auf die modellierte Szene; Welt-/Basisanker sind
  teilweise vorläufig und nicht als absolute Realgeometrie validiert.
  In der festen Suite von 30 Aufgaben × 5 Seeds × 2 Methoden waren unter je
  125 gültigen Zielversuchen 102 RRT- und 115 CF-Pläne erfolgreich. Je 25
  absichtlich ungültige Ziele wurden abgewiesen. Von 55 unterschiedlichen
  Gazebo-Zielbahnen wurden 53 abgeschlossen und zwei gestoppt. Das ist keine
  allgemeine Überlegenheit des Feldansatzes.
- [Einzelarm-CDF](single_ur_cdf.md): szenengebundene Kontaktbank und QP, keine
  trainierte UR-Netzrepräsentation. 27 Läufe umfassen nur zwei gültige Aufgaben
  und ein ungültiges Ziel, jeweils mit Wiederholungen und drei Verfahren.
  Die CDF-Vorbereitung kostete 12,14–17,65 s; der blockierte Fall anschließend
  0,546–0,554 s Planung beziehungsweise 3,13–3,21 s einschließlich Timing und
  Endprüfung. Diese historischen Zeiten liegen vor der AABB-Optimierung.
- [Hierarchische Prüfung](collision_prefilter.md): konservative Arm-AABBs
  vermeiden unnötige feine Kugelvergleiche. Bei identischer gespeicherter
  CDF-Bahn sank die Zeit einschließlich Endprüfung von 3,112 auf 2,304 s;
  Kontaktvorbereitung ist dabei nicht enthalten.
- Der unabhängige Wächter prüft vier damals ausdrücklich ausgewählte
  Nachbarpaare. Die vollständige FCL-Planungsprüfung enthält auch die
  Diagonalpaare. Die feste Vierpaarliste ist für variable Basislagen nicht
  ohne neue geometrische Begründung übertragbar.

Das aktuelle [URDF](../uwa_cell_description/urdf/cell.urdf.xacro) verbindet
die Tische über feste Gelenke mit `world`. Eine Layoutänderung zwischen
Aufgaben ist möglich; gleichzeitige Tisch- und Armtrajektorien sind damit noch
kein vorhandener Planungs-/Ausführungsfall. Die CDF-HTML-Ansicht ist eine
Modellanimation, kein Nachweis dynamischer Ausführung.

## Das Planungsproblem richtig formulieren

Vier UR-Arme besitzen 24 Armkoordinaten. Für zwei frei in der Ebene bewegliche
Tische kommen je Translation x/y und Drehung hinzu: **30 Konfigurationsvariablen**.
Bleibt ein Tisch fest, sind es 27; vier unabhängig planar mobile UR-Basen
ergeben 36. Das sind Modellannahmen ohne Greiferkoordinaten. Eine Führung auf
einer Schiene reduziert die Anzahl; vollständige räumliche Basisbewegung
erhöht sie. Nicht-holonome Fahrbedingungen schränken zulässige Geschwindigkeiten
ein und sind zusätzlich zur Konfigurationsdimension zu modellieren.

Mit Tischpose und festem Montageversatz gilt für jede UR-Basis B_i:

`T_world,B_i(t) = T_world,table_k(t) · T_table_k,B_i`.

Ein Kollisionsabstand hängt deshalb von beiden Armstellungen **und** den
Basislagen ab: `d_ij(q_i(t), q_j(t), B_i(t), B_j(t))`. Tischplatten, mobile
Unterbauten, Werkzeuge, Kameragehäuse und transportierte Objekte gehören zur
jeweiligen bewegten Geometrie. Ein stillstehender Gelenkzustand ist bei bewegter
Basis kein stillstehender Körper in der Welt.

Drei Aufgabenklassen müssen getrennt verglichen werden:

1. **Basisbahnen werden vorgegeben und sind zeitlich bekannt.** Gesucht werden
   Armtrajektorien in einer zeitabhängigen Szene. Raum-Zeit-Planung ist eine
   passende Referenz; bloßes Neuplanen in statischen Schnappschüssen reicht nicht.
2. **Basisbahnen dürfen mitgeplant werden.** Gesucht ist eine gemeinsame
   Basis-Arm-Trajektorie unter Antriebs- und gegebenenfalls Rollbedingungen.
   Dies ist Whole-Body-/kinodynamische Planung.
3. **Tische werden von außen bewegt, etwa von Hand.** Basisbewegung ist eine
   gemessene Störung mit begrenzter Vorhersage. Robuste Reserven und ein
   prädiktiver Reaktionsplan werden nötig. Ohne Grenzen der Störung kann ein
   Armplaner nicht jede Kollision verhindern; auch ein Armstopp hält den Tisch
   nicht an. Die Stopp-/Koordinationsmöglichkeit der Basis ist daher Teil des
   Anwendungskonzepts.

Noch offen sind tatsächliche Tischfreiheitsgrade, Motorisierung, verfügbare
Pose-/Geschwindigkeitsmessung und Vorhersage. Diese Unterschiede verhindern
eine endgültige Methodenwahl, aber nicht den vorliegenden Vergleich.

## Vier Ebenen mit unterschiedlichen Aufgaben

| Ebene | Zu beantwortende Frage | Typische Verfahren |
|---|---|---|
| Geometrie und Kollisionsprüfung | Sind Körper getrennt, wie groß ist der Abstand, ist ein ganzer Übergang frei? | AABB/BVH, Kugeln/Kapseln, konvexe Körper/Meshes, FCL, kontinuierliche Kollisionsprüfung, SDF/CDF |
| Räumliche Wegsuche | Wie kommen die Roboter um Hindernisse und durch enge Passagen? | PRM, RRTConnect, RRT*, gemeinsame oder entkoppelte Suche |
| Zeit und Koordination | Wer ist wann wo, wer wartet, welche Dynamikgrenzen gelten? | Raum-Zeit-Suche, Prioritäten, CBS, Zeitplanung, gekoppelte Trajektorienoptimierung |
| Laufende Ausführung | Wie wird auf Abweichungen und neue Bewegung reagiert? | MPC/MPPI, zeitabhängige CBFs, Neuplanung, unabhängige Überwachung |

Die Ebenen lassen sich kombinieren. Eine schnellere Distanzabfrage ist noch
kein schnellerer Gesamtplaner; ein schneller lokaler Regler ist noch kein
Verfahren, das eine erforderliche globale Umfahrung findet.

## Klassische Verfahren und ihre heutigen Erweiterungen

| Ansatz | Funktionsweise | Stärke für UWA | Grenze bei bewegten Basen |
|---|---|---|---|
| Arbeitsraumtrennung und Reservierung | Bereiche oder gemeinsam genutzte Volumina zeitlich exklusiv vergeben | Verständliche, günstige Referenz; funktioniert gut bei wenig Überlappung | Konservativ; Reservierungen müssen Weltbewegung der Tische einschließen |
| Geometrische Hüllhierarchie | Erst grobe vollständige Körper, dann feinere Link-/Meshprüfung | Modelltransparent und direkt an bestehendes FCL/AABB anschließbar | Löst keine Bahnplanung; Moment-AABBs beweisen keinen freien Zeitabschnitt |
| Gemeinsame Samplingplanung | Alle aktiven Roboter bilden einen zusammengesetzten Konfigurationsraum; RRT/PRM suchen darin | Kann gegenseitiges Ausweichen direkt ausdrücken; gute Referenz für vier Arme | Höhere Dimension und enge Passagen kosten Suche; dynamische Basen verlangen Zeit oder ein geeignetes Bewegungsmodell |
| Priorisierte Planung | Ein Roboter plant zuerst, andere meiden seine zeitliche Belegung | Weniger Suchdimension, relativ einfach und schnell | Prioritätsabhängig; kann scheitern, obwohl eine gemeinsame Lösung existiert |
| Konfliktbasierte Koordination | Zunächst Einzelbahnen; bei Konflikten zeitliche/räumliche Nebenbedingungen hinzufügen und betroffene Roboter neu planen | Rechnet gezielt an tatsächlichen Wechselwirkungen | Bei dichter Kopplung teuer; Graphengarantien gelten nicht automatisch für kontinuierliche UR-Dynamik |
| Bahnkoordination durch Warten | Einzelwege festhalten und ihre Fortschrittszeiten optimieren | Sauberer Vergleich für die Frage, wie viel reine Zeitkoordination löst | Findet keinen nötigen neuen Umweg; bei weiterfahrendem Tisch verschiebt sich auch ein wartender Arm |
| Trajektorienoptimierung | Wegstützstellen oder Splines unter Kollisions-, Ziel- und Dynamikbedingungen gemeinsam optimieren | Glatte Bewegungen; Basis-/Armkopplung und Greifzwänge integrierbar | Nichtkonvex, abhängig von Startlösung; mehrere Startlösungen oder globale Seeds helfen |
| Potentialfelder und zirkulare Felder | Lokale Zielanziehung, Abstoßung und tangentiales Ausweichen | Geringer lokaler Rechenaufwand; vorhandener CF-Vergleich nutzbar | Blockaden, lokale Minima und ungünstige Umläufe; kein allgemeiner globaler Vollständigkeitsnachweis |
| MPC und lokale CBF-Filter | Kurzen Zukunftshorizont wiederholt planen oder eine Sollaktion über Abstandsbedingungen korrigieren | Reagiert auf bewegte Tische/Fremdarme und Trackingfehler | Horizont, Vorhersage, Rechenfristen und Lösbarkeit begrenzen die Wirkung |

Primärquellen: [OMPL-Verfahren](https://ompl.kavrakilab.org/planners),
[FCL](https://github.com/flexible-collision-library/fcl),
[MoveIt-Kollisionsmodell](https://moveit.picknik.ai/main/doc/concepts/kinematics.html),
[CHOMP, 2009](https://www.ri.cmu.edu/pub_files/2009/5/icra09-chomp.pdf),
[STOMP, ICRA 2011](https://ieeexplore.ieee.org/document/5980280),
[TrajOpt](https://rll.berkeley.edu/trajopt/),
[ST-RRT*, ICRA 2022](https://arxiv.org/abs/2203.02176).
ST-RRT* behandelt bekannte dynamische Hindernisbahnen in Raum-Zeit;
seine Geschwindigkeitsbedingungen ersetzen nicht beliebige Drehmoment-,
Beschleunigungs- oder nicht-holonome Nebenbedingungen.

Die aktuelle Feldforschung ist ebenfalls relevant:
[Informed Circular Fields, 2024](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1447351/full)
verknüpft globale Information und reaktives Ausweichen. Unser vorhandener
CF-Rollout ist davon inspiriert, aber keine Reproduktion dieser Arbeit.

Zeitparametrierung verdient einen eigenen Vergleich:
[TOPPRA](https://hungpham2511.github.io/toppra/index.html) parametrisiert einen
vorgegebenen Pfad unter Geschwindigkeits-/Beschleunigungs- und weiteren
geeigneten Bedingungen. [Ruckig, RSS 2021](https://arxiv.org/abs/2105.04830)
erzeugt synchronisierte Bewegungen unter Ruckgrenzen. Beide sind für sich
kein Mehrroboter-Kollisionsplaner. Unabhängiges Retiming einzelner Arme kann
eine zuvor geprüfte zeitliche Koordination zerstören. Ein gemeinsames Retiming
eines gekoppelten Pfades erhält dessen Geometrie, aber nicht automatisch die
Sicherheit gegenüber extern zeitlich vorgegebenen Hindernissen. Änderungen der
Bahn durch Glättung oder Interpolation müssen erneut geprüft werden.

## Aktuelle Primärquellen mit besonderem Anwendungsbezug

Die Auswahl ist thematisch priorisiert, keine vollständige systematische
Literaturreview. Publikationsstatus und betrachtete Fassung stehen je Arbeit.
Neue Arbeiten ersetzen ältere Grundlagen nicht pauschal.

| Arbeit | Belegter Beitrag und Versuche | Einordnung für vier URs auf bewegten Basen |
|---|---|---|
| Li, Chi, Razmjoo, Calinon: [Configuration Space Distance Fields for Manipulation Planning](https://arxiv.org/abs/2406.01137), RSS 2024 | Gelenkraumabstände und Gradienten, Kontaktmengenfusion und neuronale Repräsentation; planare und Franka-Aufgaben | Grundlage unseres CDF-Themas; kein fertiger allgemeiner Vierarmplaner mit mobilen Basen |
| Shaoul, Mishani, Likhachev, Li: [Accelerating Search-Based Planning for Multi-Robot Manipulation by Leveraging Online-Generated Experiences](https://arxiv.org/html/2404.00143v1), ICAPS 2024 | xCBS/xECBS nutzen vorherige Sucherfahrung; Simulation bis zehn Panda-Arme | Sehr passende Koordinationsreferenz; Vollständigkeit/Suboptimalität beziehen sich auf das verwendete Suchmodell |
| Han, Park, Nam: [Stop-N-Go](https://arxiv.org/html/2410.07606v1), ICRA 2025 angenommen; betrachtete Preprintfassung Oktober 2024 | Suchbasierte Wartezeiten auf vorhandenen Einzelarmwegen, Vierroboteranordnungen | Einfache zeitliche Referenz; feste Wege können notwendige räumliche Ausweichmanöver ausschließen |
| Chi et al.: [Safe Dynamic Motion Generation in Configuration Space Using Differentiable Distance Fields](https://arxiv.org/abs/2412.16456), Preprint Dezember 2024 | Zeitabhängige CBFs mit Hindernisgeschwindigkeiten, QP, reale Franka-Versuche | Besonders wichtig für bewegte Fremdarme/Basen; lokale Reaktion ergänzt globale Planung |
| Patra, Sinha, Guha: [Kinodynamic Motion Planning for Collaborative Object Transportation by Multiple Mobile Manipulators](https://arxiv.org/html/2409.14910v2), Journal of Mechanisms and Robotics 2025 | Gemeinsame Basis-/Armplanung holonomer mobiler Manipulatoren für Objekttransport, Simulation und zwei reale Systeme | Geeignetes Architekturvorbild; projizierte Bodenhüllen ersetzen keine vollständige UR-Linkprüfung in 3D |
| Patra, Sinha, Guha: [Motion Planning of Cooperative Nonholonomic Mobile Manipulators](https://arxiv.org/html/2502.05462v2), ASME Letters in Translational Robotics; betrachtete arXiv-v2 Mai 2026 | Globale freie Korridore plus NMPC für Basis und Arm; fünf mobile Manipulatoren simuliert und zwei selbstgebaute Systeme real | Hohe Priorität für gleichzeitige Bewegungen und Rollbedingungen; kleinere Arme und vereinfachte Geometrie, kein Vier-UR-Nachweis |
| Parimi, Williams: [Diffusion-Guided Multi-Arm Motion Planning](https://proceedings.mlr.press/v305/parimi25a.html), CoRL 2025 | Gelerntes Einzelarmmodell und paarweise Konfliktreparatur, 3–8 Arme; auch vier UR5 mit Robotiq 2F-85 simuliert | Direkter morphologischer Bezug. Feste Basen; Pick-and-Place-Bewertung schließt bestimmte Behälter-/Objektfehler aus. Gelernte Vorschläge benötigen volle Szenenprüfung |
| Yulin Li et al.: [Fast and Safe Trajectory Optimization for Mobile Manipulators With Neural Configuration Space Distance Field](https://arxiv.org/abs/2601.18548), Preprint Januar 2026, v2 | GCDF für Translation und Rotation; gemeinsame Basis-/Armoptimierung mit neuronalen GPU-Abfragen und sequenzieller konvexer Optimierung; realer mobiler Manipulator | Besonders passende CDF-Erweiterung. Kein Nachweis mehrerer mobiler URs; Hindernispunktabtastung und Modellapproximation bleiben relevant |
| Evron, Goldsztejn, Suissa, Brafman: [MR-STORM: Scalable Multi-Arm Control By Distributed MPC](https://arxiv.org/html/2602.10114v2), IROS 2026 angenommen, v2 September 2026 | GPU-MPPI, Austausch vorhergesagter Bahnen, dynamische Prioritäten; vier UR5e/24 DOF simuliert, zwei G1-Arme real | Sehr passender Mehrarmvergleich, aber feste Basen und weiche Kollisionskosten. Keine strikte Kollisionsgarantie; Paper berichtet auch eine minimale Fingerberührung |
| Sundaralingam, Murali, Birchfield: [cuRoboV2](https://arxiv.org/abs/2603.05493), Technical Report 2026, v2 April | GPU-Trajektorienoptimierung, B-Splines, Drehmomentgrenzen, tiefenbasierte Distanzfelder; hochdimensionale Robotermodelle | Interessanter Rechenkern für ein zusammengesetztes Modell. Unabhängige GPU-Batches sind noch keine gekoppelte Vierarmplanung |
| Cui, Pu, Luo, Wang: [Feasibility Distance Fields for Heterogeneous Constraints in Robot Configuration Space](https://arxiv.org/abs/2609.24632), Preprint September 2026 | Gemeinsame Metrik verschiedener Zulässigkeitsbedingungen, blockweise Mehrrobotergradienten; UR5e-/Zweiarm-Simulation | Interessant für konsistente Multiarmkopplung; Approximation-/Vorzeichenfehler werden gemessen, keine fertige Hardwarelösung |

Die ICRA-2025-Annahme von Stop-N-Go ist durch die
[Mitteilung des Autoreninstituts](https://ee.sogang.ac.kr/eng/community/notice02.php?code=news_en&idx=2145&m=v&pNo=6)
belegt.

Neuester ergänzender Optimierungsbeitrag:
[cuRoboV2-Fast](https://arxiv.org/abs/2611.06913), Preprint vom 04.11.2026,
v2 vom 09.11.2026. Schwerpunkt schnelle drehmomentbegrenzte Bahnoptimierung und
Zeitparametrierung. Seine spezifischen GPU-Benchmarkzeiten sind keine
Vierarm-/mobile-Basen-Laufzeitprognose für unseren Rechner.

Für eine vertiefte CDF-Lektüre außerdem:
[One-Step MPPI mit CDF](https://arxiv.org/abs/2509.00836), Erstfassung 2025,
und [Neural Configuration-Space Barriers](https://natanaso.github.io/ref/Long_NCDF_TASE26.pdf),
akzeptierte IEEE-TASE-Autorenfassung 2026. Letztere kombiniert Planung mit
CDF-basierten freien Bereichen und robusten CBFs. Deren Aussagen bleiben an
Modell-, Unsicherheits- und Lösbarkeitsannahmen gebunden.

Öffentlicher Code: [Original-CDF](https://github.com/yimingli1998/cdf),
[GCDF](https://github.com/YulinLi0/GCDF),
[MR-STORM](https://roboworkshop.github.io/multi-robot-mpc/),
[Diffusion-Guided Multi-Arm](https://github.com/virajparimi/diff-mapf).
GCDF dokumentiert derzeit eine catkin-Baukette für den Planner. Daraus folgt
keine vorhandene ROS-2-Lyrical-Integration; die Portierung ist eigener Aufwand.

## Was CDF bei veränderlichen Basislagen tatsächlich ermöglicht

Ein Workspace-SDF misst räumlichen Abstand in Metern. Das ursprüngliche CDF
misst den Abstand einer Gelenkkonfiguration zur Kontaktmenge mit einem
räumlichen Punkt, bei reinen Drehgelenken in Gelenkradian. Es ist unsigned;
ein positiver Wert allein klassifiziert keine kollisionsfreie Konfiguration.
Die Originaldarstellung kann pro Roboter Punkt und Gelenkstellung als Eingabe
nutzen. Eine neue Hindernisanordnung verlangt deshalb nicht grundsätzlich
Neutraining. [Originaldefinition und Fusion](https://arxiv.org/html/2406.01137v1)

Unsere szenengebundene Bank aus konkreten Kontakten mit drei eingefrorenen
Armen hat diese Flexibilität noch nicht. Bewegte Fremdarme oder veränderte
Basisgeometrie machen diese Bank ungültig. Das ist eine Grenze des
[aktuellen Prototyps](single_ur_cdf.md), nicht des gesamten CDF-Prinzips.

**Technische Ableitung für UWA:** Ein Punkt eines anderen Arms wird im
Basisframe des betrachteten Arms abgefragt:

`p_ij(t) = inverse(T_world,B_i(t)) · T_world,B_j(t) · x_j(q_j(t))`.

Die Abfrage `CDF_i(p_ij, q_i)` bleibt roboterspezifisch wiederverwendbar.
Voraussetzung sind unveränderte Modellgeometrie/Kinematik und ein gültiger
Abfragebereich; B_i und B_j bezeichnen hier ausdrücklich UR-Basisframes.
Für gemeinsame Optimierung muss aber die Abhängigkeit von q_j, beiden
Basisposen und gegebenenfalls der Zeit mitgerechnet werden. Vier unabhängige
Regler, die jeweils alle anderen nur im aktuellen Zustand einfrieren,
ergeben damit noch keinen gemeinsamen vorausschauenden Planer.

Der bedingte Einzelarmabstand ist auch kein exakter Abstand im gesamten
30-dimensionalen System. GCDF berücksichtigt gemischte Translations- und
Rotationskoordinaten über eine gewichtete Metrik. Deren Gewichtung muss
explizit sein; Meter und Radian dürfen nicht willkürlich addiert werden.
Das zitierte GCDF-Paper verwendet ausdrücklich ein **signiertes** Feld;
die unsigned-Eigenschaft des ursprünglichen CDF gilt dafür nicht.
[GCDF-Definition](https://arxiv.org/html/2601.18548v2)
Auch GCDF für einen mobilen Manipulator löst die Koordination zweier
Tischgruppen erst nach einer geeigneten Erweiterung.

Für unseren unterschiedlichen UR5-/UR5e-/UR7e-Bestand sind Geometrie,
Werkskinematik und Werkzeuge zu berücksichtigen. Unveränderte Franka-Gewichte
oder ein einziges unvalidiertes Universalmodell genügen dafür nicht.

## Vorschlag für den späteren fairen Vergleich

Diese Stufen sind eine vorgeschlagene Untersuchungsfolge, kein bereits
beauftragter Implementierungs- oder Hardwarefahrplan.

1. **Gemeinsame Vergleichsszene und Referenzprüfung.** Zunächst feste
   Aufstellungen variieren, danach identische vorgegebene Tischbewegungen
   abspielen. Alle Methoden erhalten dieselben Start-/Zielzustände,
   Geometrien, Grenzen, Reserven und Beobachtungen. Auch Diagonalen werden
   als mögliche Kollisionspaare berücksichtigt. Grobe Hüllen dürfen sie nur
   zustands- beziehungsweise intervallabhängig begründet aussortieren.
2. **Drei Planungsfamilien vergleichen.** Gemeinsame RRTConnect-Referenz für
   ruhende Basen und Raum-Zeit-/kinodynamische Erweiterung für bewegte Basen;
   priorisierte/CBS-artige Planung mit Zeitkoordination; gemeinsame
   Trajektorienoptimierung mit anschließendem MPC. Vorhandene CF-Methode
   bleibt eine günstige lokale Vergleichsmethode.
3. **Abstandsrepräsentation gesondert variieren.** Im selben Optimierer
   klassische Geometrie-/SDF-Abstände gegen CDF/GCDF austauschen, soweit
   vergleichbare Bedingungen möglich sind. Dieselben physischen
   Abstandsvorgaben und dieselbe volle Geometrie-Endprüfung verwenden;
   Meter- und Radianschwellen nicht numerisch gleichsetzen.
   Damit lässt sich der Effekt des
   Feldes vom Effekt des Planers trennen. Kontaktgenerierung, Training und
   Szenenaktualisierung separat abrechnen.
4. **Basisbahnen mitoptimieren.** Nach bekanntem dynamischem Szenario die
   Basis als Entscheidungsvariable aufnehmen. Ein Tisch und seine zwei Arme
   bilden eine gekoppelte Einheit; vier Armagents dürfen nicht unabhängig
   widersprüchliche Bewegungen derselben Tischbasis anfordern.
5. **Ausführung und Unsicherheit untersuchen.** Verzögerte Posemessung,
   Trackingfehler, unerwartete Tischbewegung, Paketverlust und unterschiedliche
   Geschwindigkeitsreduktion der URs testen. Fortschritt gemeinsam beobachten;
   gleiche Zielversandzeit allein ist kein Synchronisationsnachweis.

Geeignete Aufgaben: freie PTPs, gleichzeitiger Zugriff auf die Mitte,
Armkreuzungen, enge Durchgänge, näher rückende/rotierende Tische, Zielbewegung
während Ausführung, gezieltes Warten/Rückziehen und unlösbare Fälle.
Gemeinsames Tragen ist ein eigener Aufgabentyp mit festen Objekt→TCP-
Transformationen und geschlossener kinematischer Kette. Dafür weiterhin das
Objekt gemeinsam planen, nicht tragende Arme unabhängig retimen.

| Messgröße | Warum sie getrennt erfasst werden muss |
|---|---|
| Gültig gelöste Aufgaben und Fehlertypen | Timeout, Blockade, unzulässiges Ziel und Kollisionsfund haben verschiedene Ursachen |
| Vorbereitungs-, Planungs-, Prüf- und Neuplanungszeit | Trainings-/Kontaktkosten und teure Endprüfung dürfen nicht im Onlinewert verschwinden |
| Median, hohe Quantile und schlechtester beobachteter Zyklus | Für laufende Regelung zählt mehr als die mittlere Rechengeschwindigkeit |
| Minimaler geometrischer Abstand und Reserven | Gelenkraum-CDF-Werte sind keine Millimeterfreiheit |
| Geplante und gemessene Gesamtdauer, Warteanteil | Schnelle Planung kann einen langsamen Gesamtprozess erzeugen |
| Weglänge, Beschleunigung, Ruck, gegebenenfalls Drehmoment | Glätte und ausführbare Dynamik sind eigene Qualitätsmerkmale |
| Modell-/Gradientenfehler, seltene Kollisionen, Intervallvalidierung | Eine schnelle Approximation muss gerade nahe Kontakt verlässlich beurteilt werden |
| CPU/GPU, Übertragung, Zustandsalter und Modellaktualisierung | Vergleich muss die tatsächlich verwendete Hardware und gesamte Verarbeitung enthalten |

Die bisherige diskrete FCL-Prüfung mit maximal 5 mrad Gelenkschritt ist kein
kontinuierlicher Kollisionsnachweis und begrenzt keine zusätzliche
Basisverschiebung. Die spätere Referenzprüfung braucht auch passende
Translations-/Rotationsgrenzen, konservative Zwischenbewegungsschranken oder
geeignete kontinuierliche Prüfung. FCL besitzt CCD-Funktionen; das Vorhandensein
dieser API beweist noch keine korrekte Prüfung der verwendeten artikulierten
Interpolation. [FCL-Funktionen](https://github.com/flexible-collision-library/fcl),
[OMPL MotionValidator](https://ompl.kavrakilab.org/stateValidation.html)

## Vorläufige Auswahl für die UWA-Anwendung

Die folgende Erstempfehlung ist durch die anschließende Nutzerpräzisierung
zugunsten von Offline-Zeitkoordination konkretisiert; siehe nächsten Abschnitt.

Als belastbare Referenz vorhandenes MoveIt/FCL und gemeinsame Samplingplanung
beibehalten. Als erste Koordinationsalternative priorisierte Raum-Zeit-Planung
mit Konfliktauflösung untersuchen. Für das eigentliche Ziel gleichzeitig
bewegter Basen und Arme gemeinsame Trajektorienoptimierung/NMPC priorisieren;
GCDF ist dafür eine besonders interessante alternative Distanzdarstellung.
MR-STORM und Diffusionsplanung sind zusätzliche Forschungsvergleiche.

Ein globaler Wegvorschlag, eine gekoppelte Optimierung und lokale Neuplanung
können in einer praktischen Lösung zusammenarbeiten. Beim wissenschaftlichen
Vergleich bleiben sie zunächst getrennt messbar. Unabhängige volle
Geometrieprüfung und Ausführungsüberwachung bleiben nötig; weder das Wort
„safe“ im Titel noch ein fehlerfreier kleiner Benchmark beweist die
Kollisionsfreiheit der realen beweglichen Zelle.

## Präzisierung auf Offlineplanung und gelernte Kollisionsmodelle

Nutzerentscheidung am selben Tag: gemeinsame Samplingplanung als Vergleich
vorsehen, Schwerpunkt auf mehreren aufgabengültigen Zielkonfigurationen,
glatten Einzelwegen und priorisierter beziehungsweise zeitlicher Konfliktlösung.
MoveJ/MoveL möglichst als bewährte Bewegungsfunktionen verwenden. Reaktive
Online-Regelung und unbekannte externe Störungen sind zunächst ausgeschlossen.
Ein moderner Vergleich bleibt gewünscht; schlechte cuRoboV1-Erfahrung ist eine
Nutzerangabe, deren konkrete Ursache noch nicht bestimmt ist.

Vorgeschlagene Architektur: Aufgabe → mehrere IK-/Greifkandidaten je Arm →
kompatible Zielkombinationen und wenige alternative Einzelwege → zeitliche
Koordination → vollständige Prüfung der finalen Trajektorien. Zielwahl und
Koordination müssen Rückkopplung erlauben: eine lokal günstige Zielstellung
kann andere Arme blockieren. Nicht jeder Konflikt ist durch Warten lösbar.

MoveJ ist Gelenkraumbewegung, MoveL TCP-Bewegung im Basisframe. Blending verändert
die Zwischenbahn. Eine beliebige optimierte Splinebahn wird durch ihre Endpose
als MoveJ-/MoveL-Befehl nicht reproduziert. Daher Primitive mit modellierten
Übergängen planen oder eine dichte Trajektorienschnittstelle verwenden; nicht
beides gleichsetzen. Die genaue PolyScope-Version und spätere Ausführung sind
separat abzugleichen. Eine weltgerade TCP-Bahn auf bewegter Basis ist im
Allgemeinen keine einzelne basisfeste MoveL-Bahn.
[UR MoveJ](https://www.universal-robots.com/manuals/EN/HTML/SW5_26/Content/prod-scriptmanual/all_scripts/movej_qa14v105t0r.htm),
[UR MoveL](https://www.universal-robots.com/manuals/EN/HTML/SW5_26/Content/prod-scriptmanual/all_scripts/movel_posea12v025t.htm),
[UR Blending](https://www.universal-robots.com/manuals/EN/HTML/SW5_24/Content/prod-usr-man/software/PolyScope/content/BasicProgNodes/commandtab_way_blend_traj.htm).

**Diskretisierung:** Workspace-Voxel eignen sich für konservative Raum-Zeit-
Reservierungen und Vorfilter. Ganze Link-/Werkzeugvolumina einschließlich
Zwischenbewegung berücksichtigen; TCP-Zellen genügen nicht. Grobe gemeinsame
Zellen können falsche Konflikte erzeugen. Für feste Einzelwege ist der
Koordinationsraum attraktiver: q_i(s_i), s_i in [0,1]. Für jedes der sechs
Armpaare eine Konfliktkarte über (s_i,s_j) berechnen. Planung sucht einen
monotonen gemeinsamen Fortschritt von (0,0,0,0) nach (1,1,1,1), unter
Geschwindigkeits-/Beschleunigungsbedingungen. Anhalten braucht Bremsweg;
Geschwindigkeit ist für dynamische Zulässigkeit zusätzlicher Zustand.
Bei extern zeitlich vorgegebenen Basisbahnen hängt der Konflikt zusätzlich
von t ab. Statische 2D-Fortschrittskarten allein reichen dann nicht.
[Stop-N-Go](https://arxiv.org/abs/2410.07606) und
[xCBS/xECBS](https://arxiv.org/abs/2404.00143) sind passende Referenzen.

**Lernmodell:** Die vorgeschlagene Sample→Abstand/Klasse-Idee ist überwachtes
Lernen, kein notwendiges Clustering. Geometrische Labels entstehen aus FK und
Distanzberechnung der Körper; bei allgemeinen Meshes nicht als einfache
geschlossene analytische Formel darstellen. Ein MLP oder ein Graphmodell passt
zu Gelenkzuständen meist unmittelbarer als ein CNN, dessen räumliche Struktur
erst eine Voxel-/Bildrepräsentation voraussetzen würde.

Abstandsregression liefert mehr Information als nur Kollisionsklassen. Ein
Modell d_hat_ij(q_i,q_j,T_i^-1 T_j) kann sechs paarweise Abstände liefern;
Selbst- und Umgebungskollisionen kommen getrennt hinzu. Bei fixer relativer
Basislage besitzt jede Paarabfrage zwölf Armkoordinaten statt 24 für alle Arme.
Relative Basispose als Eingabe erlaubt grundsätzlich auch bewegte Basen,
innerhalb des trainierten Bereichs. Werkzeuge/Greiferzustände müssen erfasst
oder konservativ umhüllt werden. Das ist unser Architekturvorschlag, kein
bereits trainiertes UWA-Modell.

Ein kartesisches Gelenkraster mit nur zehn Werten pro Gelenk hätte 10^24
Gesamtzustände. Daher Zufall-/gezieltes Sampling, Nachsampling nahe Kontakt,
schwierige Bahnabschnitte und getrennte Tests auf zurückgehaltenen Szenarien
verwenden. Wichtig sind übersehene Kollisionen, überschätzte Abstände und
Gradientenfehler nahe der Grenze. Gute mittlere Klassifikationsgenauigkeit
allein genügt nicht. Das Modell zunächst zur Suchführung/Bewertung einsetzen,
die finalen Übergänge geometrisch prüfen.

Ein gelerntes Modell des kartesischen Mindestabstands in Metern ist kein
Original-CDF: dieses misst Entfernung zur Kontaktmenge im Gelenkraum.
[DiffCo](https://arxiv.org/abs/2102.07413) ist eine direkte Referenz für einen
differenzierbaren gelernten Kollisionsproxy (nichtparametrisch, kein CNN).
[Diffusion-Guided Multi-Arm Planning](https://arxiv.org/html/2509.08160v1)
erzeugt dagegen Einzelarm-Bewegungsvorschläge und löst Konflikte mit einem
Zweiarmsmodell; es klassifiziert nicht bloß Zustände. Beide Ansätze lassen
sich als getrennte moderne Vergleichsvarianten untersuchen.

**cuRoboV2:** Der [Technical Report](https://arxiv.org/html/2603.05493v2)
beschreibt B-Spline-Optimierung, inverse Dynamik/Drehmomentgrenzen,
überarbeitete Kollisions-/Kostenarchitektur und Werkzeuge zur Modellkonfiguration.
Das adressiert konkrete V1-Schwächen, belegt aber weder die Behebung der
individuellen Nutzerprobleme noch eine fertige MoveJ/MoveL-Abbildung. V2 als
optionalem Vergleich eine kleine identische UWA-Suite geben, keine pauschale
Überlegenheit oder lokale Funktionsfähigkeit behaupten.

## Ergänzung 17.11.2026: vier Arme tragen dasselbe starre Objekt

Nutzerziel: nach dem Griff nicht loslassen/umgreifen. Als Beispiel Objekt
anheben,20cm seitlich versetzen und absetzen. Möglichst nahe am normalen
Pick-and-Place-Profil bleiben, bevorzugt Orientierung unterwegs ändern;
bei Bedarf kurze Positionsumwege. Hubhöhe, seitliche Richtung und erlaubte
Neigung noch offen. Folgendes ist ein Architekturvorschlag, kein neuer
berechneter Transport oder bestätigter Vierarmgriff.

### Modell und tatsächlich verbleibende Freiheiten

Mit Welt-Basispose B_i, Armvorwärtskinematik F_i(q_i), Objektpose X und
festem Objekt→TCP-Griff G_i gilt für jeden Arm B_i F_i(q_i)=X G_i.
Der Verbund ist kinematisch als Parallelmechanismus mit vier seriellen
Ketten sinnvoll modelliert. Unter voller starrer6D-Kopplung, festen Basen
und regulärer Kinematik ergeben30Koordinaten (24Gelenke+6Objekt) minus24
unabhängige Zwangsbedingungen lokal6Bewegungsfreiheiten. Aktuierungsredundanz
und mögliche innere Kräfte sind keine zusätzlichen freien Ellbogenbewegungen.
Ein6R-Arm hat bei festem TCP normalerweise keine kontinuierliche Nullraumfreiheit.
IK-Zweige gehören trotzdem zum Zustand; keine Sprünge zwischen Lösungen.
Mit bewegten Basen oder nichtstarren/unvollständigen Kontakten ändert sich
diese Zählung. Die zwei Tische erhalten nur ihre tatsächlich möglichen DOF.

Zeitliche Koordination bleibt als EIN gemeinsamer Fortschritt erhalten.
Unterschiedliches Retiming tragender Arme verletzt den Griff. In einer
statischen Umgebung beseitigt gemeinsames Langsamerfahren keine geometrische
Kollision; es hilft bei Ableitungs-/Kraftgrenzen. Zusätzliche dynamische
Hindernisse wären ein separates Raum-Zeit-Problem.

### Literatur mit konkretem Bezug

| Quelle | Beitrag | Übertragbarkeit |
|---|---|---|
| [Berenson et al., Task Space Regions, IJRR2011](https://publications.ri.cmu.edu/task-space-regions-a-framework-for-pose-constrained-manipulation-planning) | Posebedingungen und CBiRRT2 für constrained Manipulationsplanung | Klassischer globaler Vergleich; Korridore und feste relative TCP-Posen formulieren |
| [Jaillet/Porta, AtlasRRT, T-RO2013](https://www.iri.upc.edu/people/porta/Docs/tro13a.pdf) | Sampling/Expansion auf lokal parametrisierten Zwangsmannigfaltigkeiten | Geschlossene Ketten nicht mit beliebigen24D-Gelenksamples behandeln |
| [Bordalba et al., Direct Collocation Methods, T-RO2023](https://arxiv.org/abs/2304.12908) | Trajektorienoptimierung mit Verfahren gegen kinematischen Drift | Kettenschluss auch zwischen Stützstellen beachten; nicht nur weiche Strafkosten |
| [Kennel-Maushart/Coros, Payload-aware Trajectory Optimisation, RA-L2024](https://crl.ethz.ch/papers/Payload-aware_Trajectory_Optimisation_for_Non-holonomic_Mobile_Multi-robot_Manipulation_with_Tip-Over_Avoidance.pdf) | Gemeinsamer Transport mobiler Manipulatoren, Lastmodell, nicht-holonome Basen und Kippschutz | Besonders für spätere bewegte Tische/Basen; keine direkte Vier-UR-Integration |
| [Di Leva et al., Force and time-optimal trajectory planning, MMT2024](https://www.sciencedirect.com/science/article/pii/S0094114X24001563) | Zeit- und innere Kraftoptimierung für unilaterales Zweiarmgreifen, Experimente | Belegt zusätzliche Kraft-/Dynamikebene; anderes Kontaktmodell als voller starrer Vierarmgriff |
| [Lee/Kim, VAE-MPPI,2026](https://doi.org/10.7746/jkros.2026.21.3.363) | Gelernte Zwangsmannigfaltigkeit für nahe-zulässige Samples, GPU-KKT-Projektion für Kettenschluss | Modernes Vergleichskonzept; Dual-Panda/MuJoCo, keine Vier-UR-/Hardwarevalidierung. Kollisionskosten ersetzen keine finale Geometrieprüfung |

[Patra et al.2025](https://arxiv.org/abs/2409.14910) koppeln globale Planung
mit lokaler kinodynamischer Optimierung mobiler Arme/Basen; der Onlineanteil
ist nicht unser aktueller Umfang. [DG-MAP,CoRL2025](https://proceedings.mlr.press/v305/parimi25a.html)
erzeugt Einzelarmwege und löst paarweise Konflikte. Daraus folgt nicht die
Erhaltung eines gemeinsamen starren Griffs; dafür wäre eine andere gemeinsame
Repräsentation oder explizite Constraint-Projektion nötig.

### Empfohlene Offline-Pipeline

1. Greifzustand und konstante G_i festlegen. Der letzte Vierarm-Seitenfall
   endet mit OFFENEN Greifern: ein angenommener starrer Griff muss in einem
   Kinematikversuch ausdrücklich hypothetisch bleiben. Keine Kontaktdaten erfinden.
2. Zielpose und gemeinsamen Arbeitsraum prüfen, dann kontinuierliche IK aus
   dem Anfangszweig über den ganzen Transport. Falls unmöglich, frühere
   Greifkonfigurationswahl mit Transporttest bewerten; nicht mitten im Griff
   umkonfigurieren. Ein unerreichbares Ziel wird durch Umwege nicht erreichbar.
3. Referenzprofil aus Hub,20cmTranslation und Absetzen erstellen. Rotation
   um definierten Objektpunkt, z.B.Kartonmittelpunkt, nicht versehentlich um
   die STL-Ecke. Anfangs-/Endpose und letzte Absetzorientierung festhalten.
4. Zunächst Position des Objektpunkts fest, Orientierung in begrenztem Bereich
   optimieren (z.B.Yaw zuerst; Neigung nur nach Aufgabenverträglichkeit).
   Dann Positionskorridor stufenweise erweitern. Normalisierte Kosten für
   Positions-/Winkelabweichung, Weglänge, Gelenkglätte und Singularitätsnähe.
   Kollision/Kettenschluss/Gelenkgrenzen harte Bedingungen, keine weggewichtbaren
   Präferenzen. Nicht bloß jedenZeitschritt gierig reparieren: gesamten Weg lösen.
5. Lokaler Optimierer kann an Hindernisumgehungen scheitern. Objekt-SE(3)-Sampling
   mit fortgesetzterIK oder CBiRRT/AtlasRRT auf dem gemeinsamen Constraintsystem
   als globaler Fallback/Vergleich; danach annähernd kürzesten glatten Weg optimieren.
6. Alle24Gelenke aus derselben Objektbahn ableiten, EIN gemeinsames glattes
   Zeitgesetz anhand des begrenzenden Gelenks bestimmen. Zwischenpunkte der
   tatsächlich verwendeten Interpolation auf Kettenschluss und Kollision prüfen.
   Objekt bewegt sich in der Kollisionsszene mit; nur zulässige Pad-/Supportkontakte
   gezielt ausnehmen, niemals ganze Greifer-/Objektkollision pauschal abschalten.

Für einen modernen Vergleich zunächst paralleles Sampling von Objekt-Spline-
Parametern mit geometrischer Prüfung erwägen, später VAE/Diffusion plus harte
Projektion. Bei festen6R-Armen ist die Objektpose bereits eine natürliche6D-
Parametrisierung; ein gelerntes latentes Modell hat hier nicht automatisch
denselben Nutzen wie bei zwei redundanten7R-Armen.

Vergleichsfälle: ideale Bahn bereits frei; Ideallinie blockiert, Rotation
genügt; auch Positionsumweg nötig; Ziel außerhalb gemeinsamen Arbeitsraums.
Metriken: Erfolg, maximale Positions-/Winkelabweichung, Umweg, Mindestabstand,
Kettenschlussfehler, Gelenkreserve/Singularitätsnähe und geglättete Dauer.
Keine erzwungene Abweichung zeigen, wenn die Idealbahn schon frei ist.

Lokaler Bestand: `uwa_cell_tasks/core.py:GraspGroup` speichert feste
Objekt→TCP-Offsets, `planning.py:object_trajectory` leitet gemeinsame Bewegungen
aus Objektinterpolation ab. Beide sind auf das rechtePaar ausgelegt;
automatische Vierarm-Objektbahnoptimierung fehlt. Die Existenz der Zweiarm-
Kontaktversuche qualifiziert keine Vierarmfahrt. Für spätere physische
Übertragung kommen Kraftverteilung, Reib-/Kontaktgrenzen, Objektsteifigkeit
und gemeinsame Ausführung hinzu; unabhängige native MoveJ/MoveL-Aufrufe
garantieren den Kettenschluss nicht.
