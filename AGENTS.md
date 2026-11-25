# Arbeitsregeln für die UWA-Roboterzelle

## Holzrahmen-Demo, Nutzerentscheidung 25.11.2026

- Reihenfolge der Übertragung ist Browser, Gazebo, reale Zelle. Zwei Arme
  tragen den Querbalken gemeinsam und setzen ihn mit gleichem Überstand vor
  zwei fest montierte Pfosten. Der dritte Arm fährt während des Transports
  vor und setzt pro Verbindung zwei Schrauben. Vor dem Realbetrieb richtet
  der Bediener Werkzeug und Schrauben vor dem Lauf her.
- Zuerst Bilderkennung ohne Marker am Holz. Spiegelungen und umgedrehte
  Balkenseiten sind gleichwertig, wenn sie dieselbe Quadergeometrie einnehmen.
  Gemini 4 Hydrogen über Antigravity unterstützt schwierige Bildbefunde;
  metrische Pose und Freigaben kommen aus der lokalen Auswertung und Prüfung.

## Genehmigungspflicht für Änderungen am Sicherheitsprogramm, 24.11.2026

Vor der Umsetzung einer Änderung am Sicherheitsprogramm ist die **ausdrückliche
Genehmigung des Nutzers** erforderlich, sobald mindestens eine Bedingung zutrifft:

- Die Änderung könnte die Ausführung verlangsamen.
- Die Änderung könnte allgemein Performance kosten, etwa zusätzliche Rechenzeit,
  Speicher, I/O oder Netzlast verursachen.
- Die Änderung ergänzt Funktionen, die nicht dem unmittelbaren Hardwareschutz dienen.

Die Bedingungen gelten jeweils für sich (ODER). Auch unmittelbar dem Hardwareschutz
dienende Änderungen mit möglichen Performancekosten benötigen diese Freigabe.
Geplante Änderung und mögliche Auswirkungen vorher konkret benennen; bei unklarer
Performancewirkung ebenfalls vorher genehmigen lassen. Keine pauschale Ausnahme
für kleine Prüfungen, Wächter oder Diagnostik. Bereits ausdrücklich für die konkrete
Änderung erteilte Freigaben gelten weiter und müssen nicht erneut eingeholt werden.
Diese Regel betrifft das Sicherheitsprogramm, nicht reine Dokumentationspflege.

Konkrete Nutzerfreigabe25.11.2026: nach eigenem erfolgreich bestätigtem
Programmladen den Übergang CONFIRM_SAFETY/NORMAL innerhalb des bestehenden
30-s-Ladezeitfensters mit bestehendem250-ms-Abstand abwarten und den GUI-Hinweis
sachlich korrigieren. Zusätzliche Dashboard-Abfragen nur während dieses Übergangs;
dauerhafte/native Sperren weiter melden. Keine Freigabe weiterer Überwachung.

## Minimales Hardware-Schutzkonzept, Nutzerentscheidung 24.11.2026

Der Nutzer hat das alte UWA-Schutzkonzept ausdrücklich verworfen und die
Umsetzung des neuen Plans beauftragt. Diese Entscheidung ersetzt widersprechende
frühere Anforderungen an UWA-Guards, Supervisoren, Watchdogs und Ablaufmonitore.

- C++-Kern auf N100: Geometriekollisionen gegen Tisch, andere Arme und sich
  selbst prüfen; gemeinsame manuelle oder geometrisch ausgelöste Arm-Pause.
- Alle vier Arme pausieren. Originaltrajektorien bleiben für ausdrückliches
  Resume erhalten. Laufende Greiferaktionen nicht ändern; Greifer ausschließlich
  als vollständige Öffnungsgeometrie berücksichtigen.
- Fehlende/veraltete Kollisionsdaten ausschließlich deutlich warnen, kein
  automatischer Stopp. Keine Manager-/Hold-/Stillstands-/Geschwindigkeits-/
  Kraft-/Greifer-/Besitzheartbeat-Wächter in den neuen Ausführungspfad übernehmen.
- 40 mm zwischen den vier Nachbararm-Hüllen erhalten; Vollzell-FCL für alle
  sechs Armpaare, Selbst-/Tischkollisionen mit bisherigen Ausnahmen. Keine neue
  Tischmarge oder dynamische Stoppreserve ergänzen. FCL-Kontaktgrenze ist kein
  Nachweis eines Live-Stopps vor Berührung.
- Nach Geometrie-Pause nur freien Weg fortsetzen oder einen ausdrücklich
  geprüften Rückzug aus der bereits verletzten Abstandsmarge ausführen.
  Kein pauschaler Kollisions-Override; kein automatischer Rückzug aus realer
  FCL-Durchdringung. Ersatzbahn vor Resume im pausierten Controller annehmen.
- Native UR-Sicherheit und bestehende Planungs-/Befehlsgrenzen unverändert;
  keine eigenmächtige Tempoänderung. Normale Controllerantworten bleiben
  Ausführungsergebnisse, keine neue globale UWA-Stoppkaskade daraus ableiten.
- Robot Power/Motion Review bleiben. Stop unabhängig von laufender GUI-Aktion
  erreichbar und auf Englisch mit deutlich sichtbarem Text rückmelden.
- Der aktive Backendpfad ist seit dem beauftragten Betriebswechsel24.11.2026
  `UWA_PROTECTION_BACKEND=minimal`. N100-Runtime:
  `/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
  Dauerhafter Dienst `uwa-minimal-protection.service`, `Restart=no`, ohne
  ExecStopPost. Alte Wächter beendet; keine Mischaktivierung. Historische
  Wächterregeln unten beschreiben den abgelösten Altbetrieb.
- Reale Vierarm-Prüfung24.11.: zwei gemeinsame q6-Aufgaben hin/zurück bei
  unverändertem0,1rad/s-Sollmaximum erfolgreich; GUI-Pause und ausdrückliches
  Resume mit denselben vier Action-UUIDs. Nachweise und Grenzen in
  [Betriebswechsel](work/minimal-real-cutover-20261124.md).

Bei Fehlern in UR-Treibern auch den offiziellen Quellstand von Universal Robots auf eine passende Korrektur prüfen (Nutzerwunsch vom 24.11.2026).

## Kraftreferenz und Wiegehub am Karton, Nutzerauftrag 24.11.2026

- Nutzerfreigabe25.11.: gezielte SET-Befehle zur Greiferdiagnose sind
  ausdrücklich erlaubt. Bestehende Rohwertfreigaben beibehalten; für den
  aktuellen Kartonablauf FOR0/SPE16.

- Vor dem Greifschluss die unbelasteten Handgelenkkräfte beider rechten URs
  speichern; anschließend gemeinsam20mm anheben und die zusätzlichen
  vertikalen Kräfte im gemeinsamen Weltframe auswerten. Masse aus ihrer
  vorzeichenrichtigen Summe bestimmen, Lastanteile getrennt anzeigen;
  keine50/50-Verteilung voraussetzen. Gesamte Folge vor der Anfahrt planen.
- Nutzerangabe: Karton leer, geschätzt500g bis1kg, keine präzise Waage.
  Dies ist keine gemessene Vergleichsmasse oder Akzeptanzgrenze.
- Endliche Aufgabenmessung, keine Änderung am Sicherheitsprogramm und kein
  neuer Kraft-/Schlupfwächter. Messstreuung von absoluter Genauigkeit und
  plausibler Lastübernahme von einem Nachweis aller vier Padkontakte trennen.
  Keine unbelastete Referenz aus einem bereits geschlossenen Griff ableiten.

## Kartongriff mit zweiter OAK-Perspektive, Nutzerauftrag 24.11.2026

- Nutzerfreigabe25.11.: Für den kamerübergreifenden Kartonvergleich bis
  einschließlich3° Winkelabweichung akzeptieren. Dies ersetzt die frühere
  strikte2°-Grenze. OAK4-Pose als alleinige metrische Quelle,30mm Zentrum,
 180°-Symmetrie und Einzelbildkriterien weiterverwenden.

- Neuere Nutzerentscheidung24.11.: OAK4 als bevorzugte metrische Quelle
  verwenden, keine Mittelung mit der USB-OAK. Bei zwei gültigen Posen die
  Zentren im gemeinsamen Zellframe vergleichen und Abweichungen bis
  einschließlich30mm akzeptieren.180°-Symmetrie berücksichtigen; obige
  Winkelgrenze bis3° und Einzelbildkriterien erhalten. OAK4-Pose einschließlich
  Armtransformationen unverändert an die Planung geben. Die Einschätzung,
  dass OAK4 genauer sei, ist eine Nutzerbewertung, kein neuer Messnachweis.
  Diese Entscheidung ersetzt die frühere gleichgewichtete Mittelung und
  die bisherige10-mm-Grenze des kamerübergreifenden Vergleichs. Bei nur
  einer gültigen Einzelpose gelten die bisherigen Zusatzbild-/Rückfallregeln.

- Nutzerkorrektur24.11.: Alle vier Kartonwände sind bedruckt. Für den
  tischgestützten Griff180°-äquivalente aufrechte Kartonposen als dieselbe
  Aufgabenlage behandeln; keine künstliche Vorder-/Rückseitenidentität
  verlangen. Vor dem Kameravergleich die zweite Pose um den
  geometrischen Kartonmittelpunkt zur Darstellung der Hauptkamera zuordnen.
  Keine90°-Symmetrie für den nicht quadratischen Karton ableiten. Echte
  verbleibende Lageabweichungen und die vollständige Bahnprüfung beibehalten.

- Nutzer erlaubt ausdrücklich, für diese Zweikamera-Kartonauswertung aktuelle
  Karton-Bildausschnitte und Projektionsoverlays an Gemini Hydrogen über das
  vorhandene Antigravity-Konto zu senden. Dies gilt auch für die gezielte
  OAK-Pro-Nachmessung und die Anwesenheits-/Verdeckungsprüfung.
- **Supported carton grasp** um die gegenüberliegende USB-OAK-D Pro AF
  (kurz OAK Pro) erweitern. Zwei unabhängig gültige und übereinstimmende
  Kartonposen ursprünglich mitteln; durch obige OAK4-Vorrangregel ersetzt.
  Bei nur einer gültigen Pose die zweite Ansicht mit
  erweiterter Gemini-Auswertung gezielt auf Anwesenheit am projizierten Ort
  prüfen; deren schwache Messung nicht zum Mitteln verwenden.
- Bei Verdeckung genügt weiterhin die bisher ausreichend sichere Einzelpose.
  Klare Widersprüche von fehlender Sicht/fehlender Messung unterscheiden.
  Gerätekennung, Fokusoptik, native Bildorientierung und Referenzen je Kamera
  getrennt halten. Mittelung nicht als nachgewiesene Genauigkeitsverbesserung
  ausgeben. Bedienung und konkrete Auswahlregeln: [Zweikamera-Kartongriff](docs/carton_multiview.md).

## Nutzerfreigabe zur gemessenen Gelenkgeschwindigkeit, 24.11.2026

- Für den Kartonablauf15% Toleranz über der geplanten Gelenkgrenze verwenden.
  Bei0,1rad/s Sollmaximum akzeptieren der allgemeine Gelenkwächter und die
  zusätzliche Pilotprüfung Messwerte bis einschließlich0,115rad/s; darüber
  stoppen. Profilparameter `measured_joint_speed_tolerance_ratio: 0.15`.
  Dies ändert die früher genannte gemessene Auslöseschwelle für dieses Profil,
  nicht die0,1rad/s-Planungs-/Befehlsgrenze. TCP-Grenze, Geometrie, Frische,
  Stillstand und native UR-Sicherheit bleiben separat unverändert.

## Kameraabläufe, Nutzerauftrag 24.11.2026

- Fotopfade in Programmen auf unnötige Kamera-Neustarts prüfen. Bei
  wiederholten Bildern mit denselben Optikeinstellungen die native Pipeline
  für den Ablauf offen halten und je Aufnahme ein frisches Bild anfordern.
  Im Kartonprogramm je ein aktuelles Vollbild zur Registrierung und nach
  bestätigter offener Einfahrt. Bei der separaten Tischboard-Kalibrierung
  zuerst das bekannte Fokusprofil verwenden und den Fit an zurückgehaltenen
  Markern prüfen.

## Gemeinsame Kalibrieransichten, Nutzerauftrag 23.11.2026

- Beide externen Kameras mit den gemessenen optischen Posen im kalibrierten
  Gazebo-Layout und den Zellvisualisierungen darstellen. Gemeinsamer
  Bezug ist das rechte feste Tischboard. Auch die gedrehte Montage der
  USB-OAK folgt der optischen Pose im nativen Bildrahmen.

- Nutzerauftrag23.11.: Beobachtungsziele und gesamte Sechskamera-Aufnahme-GUI
  als **Multi-camera calibration capture** in die Program Library aufnehmen.
  Pro Start neue Anfahrwege aus aktuellen Gelenken prüfen, seriell fahren,
  danach die GUI öffnen. Separates **Open capture GUI** ohne Roboterfahrt.
  Die taskbezogenen0,09rad/s für diese Kamera-Anfahrten beibehalten.
  Bestehende Kamerasitzung wiederverwenden. Gemeinsame Datenerfassung von
  gelöster Kalibrierung und der separaten OAK4-Zwölfstundenreferenz unterscheiden.

- Nutzerentscheidung vom 23.11.2026. Für die beiden externen Farbkameras ist
  das rechte feste Tischboard (Frame `right_charuco`) vorerst der gemeinsame
  Bezugspunkt. Die optischen Kameraposen und ihre relative Transformation
  mit der jeweiligen Fokusstellung und nativen Bildorientierung angeben.

- Für die Sechs-Kamera-GUI alle vier Wrists und beide OAKs während der
  aktiven Sitzung aufnahmebereit halten. Laut Nutzer gibt es währenddessen
  keine andere Kameranutzung. Ein Klick soll je Kamera ein frisches natives
  Bild sichern. Die Wrist-Dienste erst bei Freigabe der Kameras wiederherstellen.

- Nutzerauftrag vom 23.11.2026 zur Markerprüfung: Jedes gespeicherte
  Kamerafoto aus UWA Camera Capture automatisch mit Gemini Hydrogen in
  Antigravity prüfen. OpenCV misst am unveränderten Original. Gemini
  kontrolliert die Bildbefunde und kann bei schwierigen Ansichten eine
  gezielte Nachmessung anfordern. Codex vergleicht die ersten Fotos
  unabhängig, die laufende Auswertung verwendet das Antigravity-Konto.

- Vier Handkameras sollen die Mitte zwischen den Tischen aus möglichst
  großem, noch für das mobile A4-ChArUco-Board brauchbarem Abstand sehen.
  Gemeinsames Kalibriervolumen, Markerauflösung und zugänglichen Raum
  berücksichtigen. Zielgruppe: vier Handkameras, Ethernet-OAK4 und USB-OAK
  am N100. Endstellungen von geprüften Anfahrwegen unterscheiden.
- Bestehende, vom Nutzer übernommene Armbasisbindungen verwenden. Eine
  Aufnahmefolge mit bewegtem Board bei festen Armen von einer unabhängigen
  Hand-Auge-Bestimmung mit verschiedenen Armstellungen unterscheiden.
- Folgeauftrag23.11.: Nach abgeschlossenem N100-Betriebswechsel alle vier
  Arme **nacheinander** in diese geprüften Beobachtungsposen fahren. Danach
  die vorhandene Aufnahme-GUI um die N100-USB-OAK erweitern und öffnen.
  Diese Reihenfolge ist für diesen Auftrag ausdrücklich gewünscht.
- Nutzerfreigabe23.11. nach realem Geschwindigkeitsstopp: für genau diese
  vier Kamera-Anfahrten Sollgeschwindigkeit **0,09rad/s** verwenden. Aktive
  Überwachung und bestehendes Hardwareprofil bleiben bei0,1rad/s. Keine
  pauschale Tempoänderung für andere Aufgaben daraus ableiten.

## Rechneraufteilung für reale URs, 20.11.2026

- Nutzerentscheidung: N100 betreibt die UR-ROS-Treiber, Regelung, Ausführung
  und den Live-Schutz. Er liefert Zustandsdaten und prüft unmittelbar für die
  Ausführung erforderliche Voraussetzungen. ROSmini übernimmt OAK-Auswertung,
  Bahnplanung und Offline-Planprüfung. Größere Offline-Aufträge gehen bei
  Bedarf in den eigenen Container auf titanpc.
- Statische Modelle dürfen mit Versions- und Eingabebindung wiederverwendet
  werden. Die aktuelle Kartonpose und der reale Gelenkzustand bleiben
  Eingaben je Lauf. Die vom Bediener geprüfte Bahnrevision wird unverändert
  an die Ausführung übergeben.

## Schrittvertrauen im Kartonprogramm, 23.11.2026

Der Nutzer möchte für bereits ausdrücklich geprüfte oder erfolgreich ausgeführte
Schritte des Library-Programms die Unsicherheit um eine Stufe absenken.
Vorhandene Freigaben einbeziehen und die vom Bediener gewählte Vertrauensstufe
beibehalten. Die Prüfung des aktuellen Einfahrbildes gehört weiterhin zum Kontakt.

## Bedarfsabhängiger UR-Programmstart, 19.11.2026

- Nutzerwunsch 23.11.2026 für **Supported carton grasp**. Bei einer
  Sperre im Laufstatus die betroffene Phase, die Arme und die konkret
  fehlende Bestätigung nennen. Fehlende anfängliche Holds von einem
  Verlust der Holds während der freigegebenen Fahrt unterscheiden.

Kartonpilot auf dem N100: Beim manuellen Pilotpfad mit optionalem Play vor
der Fahrt den wirklichen Bedarf verwenden. Die Zustimmung ist an die
angezeigten Arme und die Revision gebunden.

- Nutzerentscheidung 20.11.2026: **Start program** im Browser beauftragt
  für den unbeladenen Kartonablauf auch reguläres Play von `ros.urp` für
  die beiden rechten Arme bei Bedarf. Der N100 prüft dies vor Foto und
  Planung anhand der Arbeitsbereichsfreigabe und der bestehenden
  Haltezustände. Bewegungs- und Kontaktfreigabe bleiben separat.
- Die Altersgrenze der bestätigten Hold-Konfiguration im Kartonprofil
  beträgt auf Nutzerauftrag seit 20.11.2026 1.000 ms. Die Änderung betrifft
  die Bestätigung der Hold-Parameter. Die anderen Fristen sind separat
  konfiguriert oder im Guard definiert.

- Nutzerentscheidung 20.11.2026: Reguläres Beenden von `ros.urp` und
  Standby nur durch den Nutzer oder auf seine ausdrückliche Aufforderung.
  Ein laufendes Programm bleibt bei normalem Ablauf, Leerlauf und
  Schließen von Browser oder GUI verfügbar. Bestehende Schutzstopps sind
  davon getrennt. Bei unerwartetem `STOPPED` den Auslöser im N100-Safety-Log
  zuordnen und nachvollziehbar benennen.
- Nutzerentscheidung 20.11.2026: Vom Nutzer vorgenommene Änderungen an
  der UR- und N100-Konfiguration nur auf seinen ausdrücklichen Auftrag
  zurücksetzen. Bei Diagnosen den tatsächlich vorgefundenen Stand verwenden.

## Anschauliches Gazebo-Video, Nutzerauftrag 24.11.2026

- Karton-Zeichnungsdemo mit zwei Haltearmen und einem Arbeitsarm als hübsches
  Video nativ mit Gazebo rendern. Nutzer schlägt etwa15 Bilder je Sekunde
  Ablaufzeit und unmittelbar zweifache Exportgeschwindigkeit vor.
- Entstehende werkstückgebundene Zeichen-/Bohrspuren wie in der
  Browservorschau farblich hervorheben: Gelb für Zeichnen, Rot für virtuelle
  Bohrstellen. Visuelle Spuren nicht als realen Materialeingriff ausgeben.
- Gespeicherte geprüfte Bahnen dürfen für die Videoansicht wiederverwendet
  werden. Renderwiedergabe von erneuter Kontaktphysik unterscheiden.

## Reaktive Aufgabenschritte in Gazebo, 23.11.2026

- Agenten sollen geplante Bewegungen mit wiederverwendbaren, rezeptgebundenen
  Prozessreaktionen kombinieren können. Erster Skill ist das Antasten mit
  virtuellem Handgelenksensor und anschließendem geplanten Rückzug.
- Für diesen Suchvorschub sind bis zu 20 mm/s vereinbart. Anfahrt, Rückzug
  und Transport nutzen das schnelle Gazebo-Profil. Zwei reguläre Vorführungen
  mit nomineller und 2 mm vorstehender Oberfläche sind vereinbart.

## Nutzerentscheidung zur Gazebo-Simulation, 19.11.2026

- Geplante Bahnen ausschließlich offline prüfen. Gazebo dient der Wiedergabe
  und Kontaktphysik. Keine Laufzeitwächter, Gelenkgrenz-, Geschwindigkeits- oder
  Stillstandstests, auch nicht für passive Finger. Keine Fehler- oder
  Sicherheitstests in Gazebo.
- Simulierte Padkontakte dürfen den Greifvorgang auslösen. Manuelle
  Aktionsstornierung und reguläre Controllerantworten gehören zur Bedienung.
  Die getrennte reale UR-Schutzkette nur nach ihrer eigenen Freigabe ändern.

- Keine weiteren Wächter oder Tests ohne vorherige ausdrückliche Einwilligung
  des Nutzers hinzufügen. Bestehende Offline-Planprüfung weiterverwenden.
- Für Bewegungen immer das höchste aktuell zulässige und für die Aufgabe
  genehmigte Tempo nutzen. Keine zusätzliche Streckung zur besseren
  Beobachtbarkeit. Wenn ein anderer gebundener Grenzwert den Weg bestimmt,
  den konkreten Grenzwert nennen.
- Gazebo darf mit bis zu **1 rad/s je Armgelenk** geplant und abgespielt
  werden. Diese Freigabe gilt für die Simulation. Für echte URs gelten ihre
  separaten Freigaben und Geschwindigkeitsprofile.
- Am 20.11.2026 bestätigte der Nutzer das schnelle Gazebo-Zeichnungsprofil
  `carton_drawing_fast.yaml` als Standard für künftige vergleichbare Demos.
  Mit bis zu 1 rad/s je Armgelenk und Echtzeitfaktor 1 als Ziel wiederverwenden.

## Aufgabenbezogene Freigabe im Kartonpiloten, 19.11.2026

- Die Programmbibliothek führt seit20.11.2026 das eigene Programm
  `oak4-camera-calibration-v1` / **OAK4 camera calibration**. Es nutzt nur die
  Kamera und veröffentlicht die gemeinsame rechte Boardreferenz für12Stunden
  ab Aufnahme. Andere Programme lesen dieselbe Sitzung; Nutzung verlängert
  die Frist nicht. Bei Kamera-/Boardverstellung neu kalibrieren. Diese
  Sitzung von globaler Intrinsics-/Basisprofiländerung unterscheiden.

- Nutzerentscheidung 20.11.2026. Das Kartonprogramm nutzt eine separate
  ChArUco-Kamerareferenz zum rechten Tischboard für zwölf Stunden ab Aufnahme.
  Nach Verstellen von Kamera oder Board neu kalibrieren. Bei gültiger Referenz
  keine erneute Tischboardprüfung im Kartonfoto. Die aktuelle Kartonpose und
  das offene Einfahrbild für die Kontaktentscheidung weiter verwenden.

- Bestätigte Korrektur19.11.: Auch der Parallelprüfer muss die aktive
  `stopping_reserve_policy` respektieren. Unter `geometric_only` keine
  dynamischen Brems-/Latenzhüllen über ein internes `enforce` wieder einführen.
  Vollständige Geometrie-/Fortschrittsprüfung und bestehende Laufzeitstopps
  erhalten; `enforce` behält seine zusätzlichen Stoppreserven.

- Nutzer bekräftigt am 19.11.2026 für den Kartonablauf: Die beteiligten Arme
  sollen zeitgleich fahren, soweit der konkrete Modellnachweis gelingt.
  Einen seriellen Rückfall nicht als Erfüllung dieses Wunsches behandeln;
  den tatsächlichen Blocker erklären. Dies erhöht keine Geschwindigkeiten
  und hebt keine Kollisions-, Frische- oder nativen Stopps auf.

- Der Planungsagent bewertet den konkreten Auftrag anhand der beteiligten
  Arme, Abstände, Kontaktabsicht und verbleibenden Unsicherheiten. Die englische
  GUI auf ROSmini verwaltet das vom Nutzer gesetzte Vertrauen pro Aufgabe.
  Menschliche Entscheidungen und automatische Agentenentscheidungen getrennt
  protokollieren. Unbekannte Aufgaben beginnen bei „unsicher“.
- Arbeitsbereich vor Ort einmal je Sitzung freigeben. Beim Betreten oder Umbau
  widerrufen. Hohe Anfahrt und ganze offene Einfahrt vorab zusammen planen.
  Parallelität anhand tatsächlich möglicher Fortschrittsunterschiede prüfen.
  Zeigen und fahren dieselbe Version. Vor Greifschluss das tatsächliche
  Einfahrbild dieser Ausführung auswerten. Kontakt oder möglicher Teilkontakt
  bedeutet weiterhin HOLD.
- Neues gemeinsames Tempolimit für diesen Piloten: 100 % entsprechen 250 mm/s
  Translation am TCP und 0,3 rad/s je Armgelenk. Bei 33⅓ % beginnen. Ein Agent
  darf innerhalb einer vom Nutzer benannten Testreihe und Untergrenze absenken.
  Jede Erhöhung ausdrücklich vom Nutzer bestätigen lassen. Diese Präzisierung
  der bisherigen Geschwindigkeitsregel gilt für den Piloten.
- Einrichtung und lokale Vorschau stehen in [der Bedienanleitung](docs/carton_motion_review.md).

## Längere Rechenaufträge auf titanpc (2026-11-19)

- GPU-intensive und größere, länger laufende CPU-Aufträge gemäß Nutzerwunsch
  bevorzugt in Containern auf **titanpc** ausführen. Das gilt für Offline-
  Planung, Batch-Kollisionsprüfungen, Datensatzgenerierung, Vision und
  Training. Aktuelle Rechnerlast prüfen und nur benötigte Eingaben stagen.
  Jobstatus und Ergebnisse bis zum Abschluss verfolgen. Setup und Aufruf
  stehen in der [titanpc-Anleitung](../../setup/titanpc/README.md).
- Auf ROSmini kurze interaktive Prüfungen und Bedienoberflächen betreiben.
  Echtzeitausführung und Live-Wächter gehören zum realen UR-Steuerhost.
  Compute-Container sind für Datei-/Offlineaufträge. Bei fehlendem Zugriff
  oder Containerbedarf den konkreten Blocker nennen. Gemeinsame Workstation
  und bestehende FoundationPose-Umgebung erhalten.

- Nach Greifschluss bestätigte Kontaktmitglieder auch dann vorab als HOLD-only-
  Gruppe festhalten, wenn die abschließende Arm-/Programmprüfung fehlschlägt.
  Fehlerzustand nicht als unbeladen behandeln; kein automatisches Öffnen,
  Reset/Play oder unabhängiges Armziel. Aktueller realer Kontaktstand19.11.
  steht ganz oben in HANDOVER.md.

## Physisches Zeichenwerkzeug (2026-11-19)

- Nutzer bestätigt25.11.: linkes festes Tischboard seit der übernommenen
  Basiszuordnung weder bewegt noch verändert. Stiftaufnahme lokal auf dieses
  Board beziehen; aktuelle linke Boardpose aus demselben nativen Stiftbild
  bestimmen. Übernommene Basisanbindungen und gemeinsamen rechten Kamerabezug
  anderer Programme dafür nicht umschreiben.

- Nutzerhinweis und Offline-Nachweis25.11.: Bei der Stiftaufnahme die beiden
 180°-äquivalenten Greiforientierungen vor der Auswahl vergleichen. Nicht die
  erste geometrisch gültige Orientierung allein wegen ihrer Suchreihenfolge
  übernehmen. Kurzer Gelenkweg bleibt der vollständigen Anfahr-/Einfahr-/
  Aushebeprüfung untergeordnet; kein pauschaler Symmetrie-Kollisionsoverride.

- Nutzerauftrag24.11.2026: eigenes Library-Programm nach Vorbild Supported
  carton grasp, aber Stiftaufnahme mit **left_rear**. OAK-Pro/OpenCV zuerst,
  Gemini als Fallback für schwierige Bildbefunde, danach vollständige
  Bahnplanung und Greifen/vertikale Entnahme. Gemini darf hierfür aktuelle
  Stiftbilder über das vorhandene Antigravity-Konto auswerten; metrische
  Markerecken und Pose lokal bestimmen. Anleitung `docs/pen_grasp_library.md`.
- Nutzer bestätigt24.11.: beide schwarzen30mm-Quadrate mittig aufgeklebt,
  Außenkante mitLineal30mm nachgemessen, Stift vollständig eingesetzt.
  Zunächst war die Kappe auf dem Stift; für den hier vorbereiteten CAD-
  Programmstand hat der Nutzer sie abgenommen und den Stift wieder eingesetzt.
  Reale Montage-/TCP-Genauigkeit von diesen Nutzerangaben getrennt halten.
- Nutzerziel24.11.2026: den real auf dem Tisch bereitgestellten Stift aus
  dieser Aufnahme als weiteres Teilprogramm der Program library greifen.
  Erste beauftragte Etappe: Eignung markerloser Erkennung einschätzen und
  einen mehrfach belegten A4-ArUco-Druckbogen bereitstellen. Nutzer montierte
  anschließend zwei30mm-Marker am Stift: oben und seitlich senkrecht zu den
  Greifflächen. OAK-Pro-Foto24.11. bestätigt obenID97 und seitlichID96,
  beide gehören zum Stift/Adapter. Die ursprüngliche Druckbogenbeschriftung
  „Halter“ für97 bestimmt nicht die tatsächliche Montage. Metrischer
  Markerbezug zur Greifpose ist noch offen. Stand in `hardware/marker_tool/README.md`.
- Nutzer wünscht einen Greifadapter am COS-Whiteboardmarker für den
  Robotiq 2F-85 und eine Tischaufnahme mit Spitze nach unten, vertikaler
  Entnahme und Einführschräge für die Rückgabe. Verdrehung sowohl
  im Greifer als auch in der Ablage berücksichtigen. CAD unter
  `hardware/marker_tool/`. Reale Stiftspitze nach Montage einmessen.
- In Gazebo/RViz stehen zwei eigene visuelle Assets auf dem linken
  Tisch bereit: `marker_station` und `cos_marker_docked`. Deren Pose
  ist provisorisch. Für Handhabungsaufgaben Kontakt-/Kollisionsmodelle,
  Greifpose und TCP bewusst abgleichen; eine sichtbare Entität ist
  noch kein physisch greifbares Werkzeug.

## Zweite Übersichtskamera links (2026-11-19)

- Nutzer wünscht die USB-OAK am N100 hoch gegenüber der Ethernet-OAK4.
  Konkretisierung19.11.: vorhandenes 1.200-mm-Edelstahlrohr Ø19 mm als
  Säule, vier bereits vorhandene Tischbohrungen durchschrauben. Lange
  Rohrführung, geringer Materialeinsatz, Tischfuß vor Kamerakopf.
  Entwurf und Druckteile unter `hardware/oak_d_pro_left/`. Bei der
  späteren Modellierung Kamera und Mast an den linken Tisch binden.

## Hinteres Armpaar als Offline-Lehrer (2026-11-17)

- Nutzer schlägt left_rear/right_rear statt der rechten beiden Arme vor,
  um mit näheren Basen schwierigere Karton-Kollisionsfälle zu erhalten.
  Vermutung über bisher geringe Schwierigkeit als Hypothese behandeln.
  Zunächst Offline-Griffstarts/Referenzen, keine reale Gruppenumschaltung.
  Feste Objektgriffe und gemeinsames Zeitgesetz wiederverwenden; ungültige
  IK, native FCL-Kontakte und reine Hüllenverletzungen getrennt ausweisen.
- Nutzer beginnt am 18.11. mit der Visualisierung der kollidierenden Referenz.
  Im gemeinsamen 3D-Viewer die gemeldeten Kollisionskörper hervorheben und die
  ungefähre Markierung aus den Hüllen als solche beschriften. Die Ansicht
  gegen den archivierten Kontaktzustand und das ursprüngliche Modell prüfen.
- Schritt 2 für dieselbe Referenz bestätigt. Der Lehrer darf die Zwischenbahn
  in Position und Orientierung korrigieren. Gemeinsame Kartonbahn, feste
  Greiftransformationen, Start und Ziel bilden den Vergleichsrahmen. Die
  zeitparametrierte Trajektorienprüfung ist der nächste Schritt.
- Für aussagekräftigere zielgerichtete Beispiele nach Nutzeranregung vom
  18.11. gültige, voneinander verschiedene Start- und Zielposen wählen. Die
  kollidierende Referenz und der Ausweichweg haben dasselbe feste Ziel. Nach
  der Konfliktregion muss noch ein Wegstück bis dorthin folgen. Viewer bei
  solchen Beispielen am Start öffnen und die Zielpose direkt anwählbar machen.
- Schritt 3 am 18.11. für die Seitenvariante bestätigt. Gefrorene Geometrie
  gemeinsam für beide Arme zeitparametrieren, mit der aktuellen 0,1-rad/s-
  Grenze, Griffschluss-, Endpunkt- und vollständiger Modellkollisionsprüfung.
- Schritt 4 am 18.11. bestätigt. Kleine Pilotserie mit freien Kontrollen und
  Modellkollisionen bei gültigen, getrennten Start- und Zielposen. Nur nach
  bestandener Zeit- und Exportprüfung als BC-Beispiele exportieren. Verwandte
  Starts desselben Archivankers bei späteren Datensplits zusammenhalten.

## Programmierpipeline mit Demonstrationen und Sprache (2026-11-17)

- Für agentenfreie Wiederholung wünscht der Nutzer am 19.11. eine lokale
  Webbibliothek auf ROSmini, die mit UWA Robot Power startet. Programme in
  Übersicht und Detailansicht zeigen und vom Detail starten. Im Programm den passenden Pose-Algorithmus
  und die Prüfung der tatsächlichen Ausrichtung vorsehen. Kameradiagnose,
  Bedienentscheid und nachgewiesene automatische Freigabe klar benennen.
  Den vorhandenen N100-Ausführungspfad und die Zellfreigaben benutzen.
- Nutzerziel vom 19.11.: bewährte Abläufe als benannte Programme speichern.
  Neue Posen desselben Werkstücks sind Eingaben für das bestehende Programm.
  Griffpunkte, Phasen und aufgabenbezogene Konfiguration wiederverwenden. Aus
  der aktuellen Objektpose und dem aktuellen Gelenkstart die konkrete Bahn
  automatisch ableiten und mit den bestehenden Prüfungen bewerten. Beim
  Kartonpiloten sind Bilderkennung, planbare Posen und realer Kontakt getrennt
  nachzuweisen. Bedienung in `docs/carton_motion_review.md`.
- Nutzerentscheidung vom 20.11.: Gemini 4 Hydrogen Low als Reserve für
  abgelehnte Karton-Bildfits. ROSmini übergibt einen verkleinerten
  Tischbildausschnitt und die feste Bildanweisung. Erfolgreiche Suchfenster
  dürfen bei gleicher Kamerakalibrierung und ähnlicher Aufnahme lokal
  wiederverwendet werden. Die Pose wird je Lauf aus den aktuellen
  Originalpixeln mit der vorhandenen geometrischen Prüfung berechnet.
- Nutzerauftrag 23.11.2026. Hydrogen soll bei einem verworfenen Kartonfit
  das gemessene Ergebnis und ein Overlay erhalten und gezielt eine weitere
  Messung anfordern können. Bildregion oder Vorderwandecken dürfen die
  Merkmalsuche führen. Der lokale Fit verwendet die native Aufnahme und
  die vorhandenen Kriterien für Tischauflage, Projektion und Übereinstimmung.
- Nutzerziel: schnelles einfaches LLM soll mit wiederverwendbaren Bausteinen
  möglichst zügig ein Aufgabenprogramm erstellen. Optional ein bis zwei
  erklärte Teleoperations-/Handführungsbeispiele mit Kameras, UR-Posen und
  Kräften nutzen; vollständiges Training einer Gesamtpolicy ist kein Ziel.
- Pilotbeginn bestätigt17.11.: Box halten und Kreise zeichnen. Erste Auswertung
  bewusst auf verfügbare Ausführungsdaten beschränken: Dauer, Kraftmaximum,
  Fehlgriffe/Neuansätze, Objektverlust, Agenteneingriffe plus subjektives
  Nutzerfeedback mit Phasenbezug. Detaillierte automatische Strichbild- oder
  Produktqualitätsoptimierung ist später optional, keine Einstiegsvoraussetzung.
  Fehlende Beobachter als UNKNOWN statt Null; Nutzermeldung und Messung trennen.
- Erstes Pilotfeedback: Umkonfiguration vor Unterseitenkreis hinterfragen;
  höhere/nähere Boxpose oder Umstellen während Boxdrehung prüfen. Anfangs-
  und Endzustände beim Zeitvergleich gleich halten, zusätzliche Positionierung
  mitrechnen. Freier Arbeitsarm darf mit der Boxgruppe gleichzeitig fahren;
  deren gemeinsame Objekt-/Zeitbindung erhalten und alle Arme neu prüfen.
  Beispiele aus diesem Feedback nicht als generelle Erreichbarkeitsregel übernehmen.
- Präzisierung17.11.: **Code as Policy für Gesamtaufgaben**, z.B. zwei Arme
  halten/drehen den Karton, dritter stapelt oder zeichnet auf dessen Seiten.
  Der32-Aufgaben-/21-Bahnen-Pilot ist separate Kollisionsvermeidung, kein
  Lernstand dieses Aufgabenprogrammiersystems.
- Bevorzugte Entwicklungsinteraktion: Agent führt zunächst in Simulation vor,
  Nutzer bewertet sprachlich oder korrigiert perTeleop. Handführung nur bei
  Bedarf als zusätzliche Quelle; Erkennung des Bedarfs nicht als gelöst annehmen.
  Langfristiges Lernen aus eigenen Ausführungen **und** manuellem Feedback
  für wiederkehrende Industrie-/Bauaufgaben einplanen; Code/Skills/Parameter
  und belegte Erfahrungen können ohne vollständiges Policytraining wachsen.
- Dieses Aufgabenlernen vom bestehenden BC-Vergleich für numerisch optimierte
  Objektbahnen unterscheiden. Aus wenigen Demos keine allgemein gültigen
  Toleranzen, Kraftgrenzen oder Steifigkeiten ableiten; Herkunft von Sprache,
  Messung und technischen Annahmen erhalten. Gemeinsame Objektsteuerung pro
  tragender Gruppe gilt auch für Demonstration und Retargeting.
- Nutzerauftrag18.11.: Übertragbarkeit an einem anderen Agenten testen;
  kurze Übergabe und Prompt unter docs/agent_trials/. Entwicklungsschritte,
  Toolausgaben, Dauer und Fehler über tools/agent_trial.py protokollieren.
  Entwicklungszeit von robotischer Modell-/Ausführungszeit trennen; Restzeit
  außerhalb geloggter Befehle nicht als gemessene Denkzeit ausgeben. Nicht
  gewrappte Tools/Chat zusätzlich notieren/exportieren, Fehlversuche erhalten.
- Auswertung18.11.: bei `python3 -`/Patch-/Shell-Standardeingaben den Inhalt
  mit `agent_trial.py run --stdin-file DATEI|-` archivieren; argv allein
  dokumentiert diese Bearbeitungen nicht. Roh-Exitcodes von fachlichen
  Ablehnungen, erwarteten Suchergebnissen und Aufruffehlern unterscheiden.
  Ein erfolgreicher Agententest belegt die konkrete Übertragung, noch keine
  allgemeine Eignung eines schnellen einfachen LLM oder langfristiges Lernen.
- Gegenwand-Trial (Nutzerauftrag 18.11.): vorhandene Kreise auf y_max und
  z_min erhalten und y_min mit 25 mm Radius ergänzen. Rechte Haltegruppe
  starr halten, left_front zeichnet, gesamter Hin- und Rückweg im
  file-only Modell mit 0,1 rad/s und denselben Prüfschwellen auswerten.
  Entwicklung getrennt nach TRACE_PROTOCOL.md protokollieren.
- Nutzer bestätigt18.11. den Ausbau des Offline-Bausteins `present_surface`.
  Für neue Boxzeichnungsvarianten die Flächenfolge vorgeben und die
  Halteposensuche im Toolkit nutzen. Vorläufige Transferansicht und vollständig
  geprüften Modelllauf unterscheidbar anzeigen. Ablehnungsstufe und lokale
  Ursache erhalten. Bedienung in docs/box_drawing_pilot.md.
- Nutzerauftrag19.11. zur Greifhöhe: Beim Übertragen vom HTML-Piloten nach
  Gazebo oder auf reale Arme die Greifgeometrie im selben Kartonframe
  vergleichen. Bezugspunkt (Tool0, virtueller TCP oder Padfläche),
  Fingerstellung, Wand/Rand und Quelle der Grifftransforms dokumentieren.
  Vertikale Werkzeughöhe und kleinsten Abstand Pad→Karton gesondert
  prüfen. Hüllen in der HTML-Vorschau sind Visualisierung von
  Modellgeometrie. Für die Kontaktplanung den zur jeweiligen Umgebung
  gebundenen Griff verwenden und die Bahn damit neu prüfen. Die
  52/55 mm aus dem ersten Vergleich sind ein Fallbefund und kein
  universeller Korrekturwert. Nachweis in HANDOVER.md.
- Bei einem Kompatibilitätstest den Zweck klar benennen. Aufruf eines
  bestehenden Bausteins und Entwicklung einer neuen Aufgabe messen
  unterschiedliche Fähigkeiten. Den Nikolaushaus-Test vom 19.11. in
  separater Quellkopie starten und die neue Form aus der gespeicherten
  Gelenkbahn prüfen. Alte Ergebnisordner bleiben außerhalb des
  bereitgestellten Kontexts. Details in docs/agent_trials/.
- Nutzerauftrag19.11.: harmlose wiederkehrende Freigaben im Gemini-Test
  vorab behandeln. Logger und Artefaktordner im Starter vorbereiten,
  automatische Shellfreigaben an die isolierte Sitzung und wörtliche
  Befehle binden. Freigabewartezeit aus CLI-Ereignissen getrennt von
  Entwicklungswandzeit, Rechenzeit und Roboter-Modellzeit auswerten.
- Nutzerauftrag19.11.: für den schnellen Modellvergleich ein eigenes,
  auf zügige Codeausführung ausgelegtes Modell testen. Für den ersten
  direkten Vergleich dieselbe Aufgabe mit Hydrogen und Neon jeweils auf
  `High` verwenden. Zeitpunkt der ersten gültigen Modellbahn und der
  fertigen Abgabe getrennt erfassen.
- Nutzerauftrag19.11.: gebündelte Prüfung und Abgabe als Standard für neue
  Gemini-Aufgaben. Isolierte Quellkopie mit `tools/start_gemini_trial.py`,
  Hydrogen High als Modellvorgabe und Abschluss über
  `tools/finish_gemini_trial.py` mit passendem Aufgabenaudit, Viewer-Prüfung,
  Bericht und vollständigem Patch. Gemini verwendet vorhandene Tests und
  entwickelt, ergänzt oder ändert keine eigenen. Bei Python-Änderungen
  gezielt prüfen. Die vollständige Regression gehört zur Übernahme in das
  gemeinsame Toolkit. Neue Fälle erhalten ihre eigenen Prüfkriterien.
- Nutzerpräzisierung19.11. für Haus-/Bohrdemo: Ablauf zuerst mit
  Gazebo-Nachweis beurteilen, bevor der Nutzer der Übertragung auf die
  reale Zelle vertraut. Offline-FK/Ansicht, Kontaktphysik mit getragenem
  Werkstück und tatsächlichen Bohrprozess getrennt belegen.
- Nutzerpräzisierung19.11.: Zeichnen als reversibler Test für allgemeine
  werkstückbezogene Bahnen. Zielanwendungen sind unter anderem Kleben,
  Farbauftrag, Sägen/spanende Bearbeitung und Schaumauftrag am gehaltenen
  Fenster. Axialer Vorschub entlang einer Flächennormale ist ein eigener
  Pfadtyp für Bohren und Schrauben. Geometrie und realen Werkzeugeingriff
  getrennt beschreiben. Bewegungen des freien Arbeitsarms beim Rückweg
  aus der letzten Arbeitspose koordinieren und denselben Modellprüfungen
  unterziehen. Bedienung in docs/workpiece_paths.md.
- Piloteinstieg ist bestätigt; weitere Architekturvarianten bleiben Empfehlungen,
  keine pauschale Hardwarefreigabe. Erster file-only Modellstand/Bedienung:
  docs/box_drawing_pilot.md. Forschungsbericht:
  docs/programming_pipeline_lbd_review_2026-11-17.md.
  Präzisierter Entwurf: docs/interactive_code_policy_learning.md.

## Reale Bedienabläufe ohne Diagnosekaskaden (2026-11-18)

- Nutzerwunsch vom 23.11.2026 zur realen Vierarmzelle: Für jede Überwachung
  die konkrete Gefahr, den Betriebszustand, die erforderliche Reaktionszeit
  und die Folge eines Ausfalls benennen. Verwaltungsabfragen im Stillstand
  und ihre N100-Last kritisch prüfen. Die Antwortzeit der Controllerliste
  getrennt von Ressourcenbesitz, Reglerfunktion und gemessener Bewegung
  beurteilen. Zusätzliche Wächter bedürfen ausdrücklicher Zustimmung.
  Unveränderte Armpaare sollen keine vollständige Abstandsrechnung auslösen.
  Für kleine Encoderänderungen darf die Rechenarbeit sinken, wenn der
  tatsächliche Mindestabstand und das auslösende Körperpaar nachweislich
  mit der Vollrechnung übereinstimmen. Vorübergehende Ausfälle beim Lesen
  von Greifer- und Anzeigedaten tolerieren. Eine Wiederholung gilt für die
  Leseabfrage. Eine verspätete Nachricht erneuert weder die ursprüngliche
  Gerätebeobachtung noch die Freigabe eines Fahr- oder Greifbefehls.
  [Prüfung und Reparaturstand](work/n100-ueberwachung-20261123.md).

- Bei einem konkreten Abbruch zuerst den aktuellen N100-Bericht aus **Safety log** oder dem passenden lokalen Export lesen und den betroffenen Versuch über dessen Workflowpfad zuordnen. Den aktiven [N100-Wächterstand](../../setup/n100/ur-runtime/README.md#guard-protokoll-auf-dem-n100) verwenden. Den aktuellen Interlockstatus vor einer Fahrt separat prüfen.

- Nutzerwunsch vom 19.11.2026: Die Ursache wiederkehrender Sperren in **UWA Robot Power** sichtbar machen. Bei der Auswertung Zeitpunkt, betroffene Arme, Auswirkung und vorhandene Messwerte zur Schwelle heranziehen. Mehrere Meldungen desselben Vorfalls und eigenständige Auslösungen unterscheiden.

- Nutzer empfindet die Zahl der Test-/Diagnoseläufe im laufenden realen Griff
  als zu hoch. Bereits geprüfte Pläne in den kurzen Ausführungspfad übernehmen;
  keine zusätzliche Testreihe oder neue Überwachung allein vor jedem Start.
  Bei technischem Abbruch den konkreten Blocker nennen und gezielt beheben.
  Bestehende native Sicherheit, Kollisions-/Frische-/Haltprüfungen erhalten.
- Betriebsanbindung und Testwerkzeuge in Erklärungen klar unterscheiden.
  UWA Robot Power bedient Start + ROS/Standby; reines Fensterschließen soll
  laut aktuellem Code keine dauerhaften Treiber beenden. Breite ROS-Signal-
  beendigung nicht ohne Nachweis dem Schließen dieses Fensters zuschreiben.

- Serielle Hardwareaufträge: Arm-/Aktions-/Read-Schnittstellen möglichst vor
  regulärem Programmstart aufbauen und über Armwechsel behalten. Wiederholter
  Graphauf-/abbau korrelierte am N100 mit Manager-RPC-Frischefehlern. Jedes
  Status-Read muss weiterhin frisch vom Gerät kommen; keine Frischegrenze
  durch Statuscaching umgehen. Nach realem Kontakt nur HOLD, kein Startup.

- Nach manueller Gelenkbewegung bei gestopptem External-Control-Programm
  vor Play bestehende Haltesollwerte neu an die echte Pose binden. CollisionHold
  speichert seine Position beim Aktivieren; ein alter Sollwert darf nach
  Kabelabwicklung/Handbewegung nicht zurückgesendet werden. Neubindung nur
  explizit unbeladen, nativ STOPPED/Normal, stationär und mit passenden frischen
  Driver-/Istwerten; vorhandene Stopps/Latches nicht dadurch aufheben.
- Nutzer wickelte19.11. RF-Basiskabel durch manuelle Drehung von nahe-360° nach
  nahe0° ab. Diesen neuen Winkelumlauf als Start verwenden und Kabelführung
  bei Konfigurations-/Homeentscheidungen mit berücksichtigen; kein Replay des
  alten Umlaufs allein wegen numerisch ähnlicher Werkzeugpose.

## Explizit freigegebene Ruhebewertung,19.11.2026

- Erweiterung durch Nutzer: dieses Ruheprofil auch künftig nutzen; weitere
  großzügigere Ruhebewertung ist erlaubt. Änderungen fachlich begründen und
  dokumentieren. Das ist keine Freigabe höherer Fahrgeschwindigkeiten oder
  lockerer Kollisions-/Datenfrischegrenzen.

- Nutzer bestätigt Aktivierung von `hardware_carton_supported_trend.yaml` für
  den aktuellen Kartonablauf. Armruhe aus linearer Gelenkpositionsentwicklung
  und identischer Positionsspanne0,0005rad/0,5s bewerten; rohe qd-Spitzen bleiben
  sichtbar und unterliegen unverändert dem0,1rad/s-Geschwindigkeitswächter.
  Hardware-Frische/Kollision/nativeUR-Sicherheit bleiben unverändert.
- Peakbewertung bleibt Default andererProfile. Keine allgemeine Erlaubnis,
  beliebige Stoppgrenzen zu lockern. NeueProfilbindung vor realer Fahrt prüfen.

## Geschwindigkeiten für reale Roboter: dauerhafte Nutzervorgabe (2026-11-18)

- **Keine weitere Geschwindigkeitsreduktion ohne ausdrückliche Aufforderung
  des Nutzers.** Die zuletzt vereinbarte Geschwindigkeitsgrenze beibehalten;
  aktueller Stand für die realen UWA-Arme: 0,1 rad/s.
- Keine eigenmächtigen niedrigeren Kommandogrenzen, langsameren Ersatzprofile,
  zusätzlichen Reserven mit Temposenkung oder gezielte Zeitstreckung. Frühere
  Langsamprofile sind kein Anlass, die aktuelle Nutzerentscheidung zu übergehen.
- Ist ein angeforderter Ablauf unter den bestehenden Bedingungen nicht
  ausführbar, den konkreten Konflikt melden, statt unbemerkt langsamer zu fahren.
  Native Sicherheitsstopps und die geometrische Kollisionsüberwachung bleiben
  bestehen. Keine pauschale Freigabe über0,1rad/s daraus ableiten.

## OAK-Neukalibrierung und Aufnahmefeedback (2026-11-17)

- Nutzerziel 20.11.: Den Kartonablauf gegenüber kleinen Änderungen der
  OAK-Lage im Bild robuster machen. Temperatur ist eine mögliche Ursache.
  Als technische Lösung fest angebundene, dauerhaft sichtbare Marker für
  die laufbezogene Kameraregistrierung prüfen. Die übernommenen
  Roboterbasen sind davon getrennt. Stand im HANDOVER.

- Verbindliche Nutzerentscheidung18.11.: vorhandene Basisanbindungen ALLER
  vier URs einschließlich left_front als **fest übernommen** behandeln.
  Alte Kalibrierproblem-/Unter-Schwellen-/diagnostic-only-Hinweise nicht mehr
  als aktuelle Einschränkung der Basisanbindung in Berichten, GUIs oder
  Übergaben verwenden. Erst bei konkret beobachteten Problemen erneut
  untersuchen. Nutzerentscheidung von alten Messresultaten unterscheiden;
  Originalberichte erhalten. Aktives Basisprofil hardware_20261118_base_fixed_v1.

- Fokusziel laut Nutzer18.11.: vorderes UND hinteres festes Tischboard
  gemeinsam scharf abbilden. Fokusauswahl an beiden statischen Referenzen
  beurteilen, nicht allein am mobilen Brett. Aktuell107 nach nativem Vergleich
  bei unveränderter Montage; genaue Prüfdaten und Profilbindung in HANDOVER.

- Präzisierung18.11.: Ziel bleibt die OAK-Pose gegenüber Roboterbasen/Welt.
  Intrinsicsprüfung bei geändertem Fokus als Hilfsschritt klar davon trennen;
  reine OAK-Bilder eines frei bewegten Boards liefern keine Weltanbindung.
  Weitere Pose-Aufnahmen mit allen fünf Kameras speichern; mobile Ansichten
  benötigen gemeinsame Sicht von OAK und mindestens einer angebundenen Wrist-
  Kamera, nicht zwingend allen fünf. Unveränderte eingemessene Tischboards sind
  ebenfalls Anker. Boarddetektion allein belegt keine gemeinsame Referenz.

- NeuesteAnweisung18.11.: fürdiegezeigteAufnahmeanfahrtzusätzlicheberechnete
  dynamischeStoppreserveentfernen, KommandosundüberwachteArmgelenkgrenzen
  auf0,1rad/ssetzen. ExpliziterProfilmodus `stopping_reserve_policy: geometric_only`.
  GeometrischeKollisionsprüfung/40mmModellpuffer, Daten-/Heartbeatüberwachung,
  Hold-/StoppfunktionundUR-eigeneSicherheitbleibenaktiv. Keineautomatische
  nativeSicherheitsquittierung. VorherigeAnnahmenerzwingenkeinlangsamesTempo
  mehrindiesemModus; keinequalifizierteBremswegabsicherungbehaupten.
  AndereProfilebleibenstandardmäßigenforce; ModusimStatusundLogausweisen.

- Nutzerkorrektur18.11.: zuerst zügig einen plausiblen Pfadvorschlag erstellen,
  inRViz/andererAnimationzeigen undBedienerbewertungabwarten. Keineumfangreichen
  Wiederholungsprüfungen/RegressionsläufevorjedemVorschlag. FürdieseVorschau
  einegrundlegendeModell-Kollisionsprüfunggenügt; Vorschlagvonphysischer
  Ausführungsfreigabeunterscheiden. BestehendeUR-/Laufzeitsicherheitbeibehalten.
  BeiPOWER_OFF/NulltelemetriezuletztgültigenMessstartalsHistoriekennzeichnen,
  keinenNullstartalsaktuelleArmstellungausgeben.

- LF-q6 am17.11. nach angehaltener Aufnahmeanfahrt: native Geschwindigkeit
  bis0,044rad/s bei kleinem Positionshub; Nutzer bestätigt reale kleine Rucke.
  Nicht ungeprüft als Messrauschen filtern oder Stillstandsschwelle erhöhen.
  Nutzer erlaubt ausdrücklich ausschließlichLF-Standby plusPower/Brake/ROS-
  Neustart zur Diagnose; vor Fahrt erneut echten ruhigen Zustand nachweisen.

- Historie17.11.: Nutzer hält auch9,2min für vier Anfahrten für unzweckmäßig
  und schlägt0,1rad/s vor, mit eigenem Nothaltzugriff. Seit18.11. ist0,1rad/s
  tatsächlich verwendet und als beizubehaltende Grenze bestätigt (siehe oben).
  Daraus keine gemessene Stoppqualifikation ableiten.

- Nutzer beauftragt17.11. nach dem unzweckmäßigen72min-Anfahrvorschlag eine
  allgemeine Reserveüberarbeitung. Kommandotempo und einzelne überwachte
  Gelenkgrenzen trennen; ruhende Arme nicht ungeprüft als bewegungsfrei annehmen.
  Neuer opt-in-Modus `per_body_joint_caps_v2`, docs/stopping_reserve.md.
  Offline-/Mocknachweis nicht als reale Stoppqualifikation ausgeben.

- Nutzer hinterfragt17.11. einen zusätzlichen17,3cm-Abstand bei bereits großen
  Kollisionshüllen. Hüllenradius, freier Oberflächenabstand, Modellunsicherheit
  und dynamische Stoppannahmen getrennt ausweisen. Den profilabhängigen
  Ingenieurwert nicht als gemessenen festen Mindestabstand darstellen;
  Hüllengeometrie nicht doppelt zählen.

- Nutzer vermutet eine versetzte OAK und möchte zuerst die aktuelle Sicht/Montage
  beurteilen, danach vier UR-Aufnahmestellungen und die Fünfkamera-GUI.
  Alte OAK-Extrinsics nicht als aktuelle Registrierung verwenden. Neue Fahrwege
  anhand frischer Zustände prüfen, historische Sichtstellungen sind nur Ziele.
- Aufnahme-GUI: großer dauerhafter RECEIVED/RUNNING/DONE/FAILED-Text, HOLD STILL
  bis Abschluss aller Prüfungen, Fortschritt je Kamera; vollständige gespeicherte
  Sätze, verwendbare Sätze und Einzelbilder getrennt zählen. Live-/Pausemeldungen
  dürfen das letzte Aufnahmeergebnis nicht verdrängen. Englisch und hoher Kontrast.

## Forschungsziel bewegte Basen und vier URs (2026-11-16)

- Neueste Präzisierung: zunächst ausschließlich **Offlineplanung**, vollständige
  Wege aller Arme/Basen als bekannt annehmen; keine externen Störungen oder
  reaktive Online-Regelung als aktuellen Entwicklungsumfang hinzufügen.
- Gemeinsame Samplingplanung ausdrücklich als Vergleich gewünscht; persönlicher
  Schwerpunkt des Nutzers ist Zielkonfigurationsauswahl mit mehreren Kandidaten,
  glatte Einzelwege möglichst über bewährte MoveJ/MoveL-Funktionen und anschließende
  Priorisierung/Zeitkoordination. Ein moderner lernbasierter Vergleich gewünscht.
- Nutzer berichtet schlechte Erfahrungen mit cuRoboV1; Ursache noch unbekannt.
  V2-Verbesserungen aus Quellen von eigenen Integrationsergebnissen unterscheiden.
- Nutzerziel: kollisionsfreie Bahn- und Trajektorienplanung für vier URs mit
  veränderlichen relativen Basislagen. Ausdrücklich auch **gleichzeitige Basis-
  und Armbewegungen** berücksichtigen, nicht nur Umstellen vor der Planung.
- Zwei bewegliche Tische mit je zwei starr montierten Armen sind das erste
  Fallbeispiel; langfristig vier mobile Manipulatoren. Bewegungsfreiheitsgrade,
  Antriebsmodell und Verfügbarkeit vorgegebener Basisbahnen bleiben zu klären.
- Auftrag17.11.: Plan als PDF festhalten und mit Schritt1 beginnen: mehrere
  Zielkonfigurationen je UR aus expliziten Aufgabenposen/Alternativen erzeugen.
  Offline-CLI `cell_goal_candidates`, Anleitung docs/offline_goal_candidates.md.
  Kinematische Kandidaten von gemeinsam modellgeprüften Endstellungen trennen;
  beides ist noch kein Bahn-/Ausführungsnachweis. Keine reale Bewegung oder
  Umrüstung allein aus diesem Forschungsziel ableiten.
- Auftrag17.11. nach positiver Viewer-Rückmeldung: Schritt2, gemeinsame
  Zielauswahl, umsetzen. Mehrkriterielle Auswahl getrennt von Bahn-/Zeitplanung;
  Gelenkverschiebung ist kein Nachweis von Bahnlänge oder Ausführungsdauer.
  Suchgrenzen/Pareto-Geltungsbereich nennen, Alternativen für folgende Planer
  erhalten; keine Vollständigkeit der IK oder globale Optimalität behaupten.
  Synthetische Zielalternativen als Demonstration kennzeichnen.
- Korrektur17.11.: Für Schritt3 feste Greifpose jeArm an seiner nächstgelegenen
  Ecke des Avocado-Kartons, Annäherung senkrecht vonoben. Nicht zugleich
  Zielposen und IK-Konfigurationen variieren; Nutzer fand dies verwirrend.
  GewünschterNullstart kollidiert imModell; Nutzer wählt nachPrüfung ausdrücklich
  [0,-90,0,-90,0,0]Grad füralle4. ReineOfflinebahnprüfung, keinGriff-/Hubnachweis.
- Auftrag17.11.: Eckanflugtrajektorien selbst zehnfach beschleunigen und prüfen,
  nicht nur die HTML-Wiedergabe. Gemeinsame Zeitskalierung aller vier Arme;
  v×10/a×100/Ruck×1000 auswerten. Alte vorsichtige Profilgrenzen nicht als
  physische UR-Maxima darstellen. Viewer-Wiedergabe (bisher20×) klar von
  Trajektoriengeschwindigkeit trennen; schneller Vergleich zunächst Echtzeit.
- Auftrag17.11.: alle vier Eckanflüge (nach Rückfrage ausdrücklich alle4)
  hinsichtlich Beschleunigung/Ruck glätten, Geschwindigkeit grundsätzlich okay,
  Geometrie möglichst erhalten. Zeitgesetz zuerst verbessern; räumliche
  Änderungen metrisch nachweisen. Individuelles Retiming verändert relative
  Armstellungen über Zeit und verlangt neue gemeinsame Kollisionsprüfung;
  Invarianz gilt nur für eine gemeinsame Zeitabbildung aller Arme.
- Nutzerstandard17.11.: für weitere Offline-Anfahrbeispiele standardmäßig
  die geprüften glatten Zeitgesetze verwenden, nicht erst nachträglich anbieten.
  Gilt für freie Anfahrt, nicht für unabhängiges Retiming tragender Greifverbünde.
  Nächster Test: jeUR eine eindeutige Seitenmitte statt Ecke; nächstgelegene
  oder zweitnächste Seite, bei Konkurrenz eindeutige gemeinsame Zuordnung
  innerhalb dieser zwei Optionen mit minimaler Summe horizontaler Abstände.
  Keine stille Verdrängung auf die drittnächste Seite. Anflug weiterhin
  von oben, Backen quer zur Seitenwand; feste Ziele und neues gemeinsames Prüfen.
- Erweiterung17.11.: nach dem Griff ohne Loslassen/Umgreifen gemeinsam tragen.
  Beispiel: anheben,20cm seitlich versetzen, absetzen. Gewünscht sind möglichst
  kleine Abweichungen vom logischen Pick-and-Place-Profil, bevorzugt durch
  Objektorientierung, nötigenfalls kurze räumliche Umwege. Zunächst Konzept/
  Literatur/Offlineplanung; keine neue reale oder Kontaktphysik-Ausführung.
  Parallelrobotermodell prüfen. Bei starren Griffen gemeinsame Objektbahn und
  gemeinsames Zeitgesetz; Einzelarmglättung/-wartezeiten danach nicht übertragen.
  Bewegte Basen bleiben spätere zusätzliche Planungsvariablen. Für den ersten
  Offlineversuch Richtung laut Nutzer anhand Erreichbarkeit wählen; Versuchs-
  annahmen10cm Hub, waagerechter Karton,±15°Yaw. Keine allgemeine Freigabe
  dieser Parameter für andere Objekte oder physische Transporte ableiten.
- Präzisierung17.11.: Nutzer bestätigt insbesondere die fünf Schritte der
  Objektbahnplanung; zunächst lernende Verfahren zurückgestellt (durch den
  folgenden Vergleichsauftrag konzeptionell erweitert). Deterministische
  Gradienten/Suchrichtungen für Objektrotation und Positionskorrektur bevorzugt.
  Gemeinsame Jacobikinematik und Singularitätsbewertung untersuchen; TSR als
  passende Constraintbeschreibung berücksichtigen, nicht als Gradientoptimierer
  ausgeben. Keine qualifizierten Singularitätsschwellen aus Einzelproben ableiten.
- Erweiterung17.11.: lernbasierten Vergleich für starren Objekttransport
  konzeptionell und anhand Literatur untersuchen. Nutzeridee: Zielversatz oder
  kurze Zieltrajektorie plus MRS-Zustand → nächste gemeinsame Objektbewegung;
  numerisch optimierte Lösungen als Trainingsdaten, zunächst festes Objekt und
  feste Griffe. Netzstruktur und RL sind offen, keine Trainings-/Hardwareaktion
  beauftragt. Deterministischer Ansatz bleibt Referenz; Policy-Rollouts können
  vollständig offline erfolgen. Greifmatrix allein enthält keine Armgeometrie.
- Folgeauftrag17.11. zum Lernen: BC ausdrücklich gewählt, zunächst guten Lehrer
  und aussagekräftige Lernbeispiele entwickeln. Einstieg mit zwei Armen an den
  gegenüberliegenden kurzen Kartonseiten, Translation und insbesondere
  Orientierung variieren/optimieren. Langfristiges Montagebild: zwei Arme
  halten Teil1, ein Arm Teil2, ein Arm Werkzeug; kein gemeinsamer Vierarmgriff
  als allgemeine Montageannahme. Vorerst Offlineplanung, kein reales Greifen.
  Starre Kopplung und gemeinsames Retiming gelten pro tragender Gruppe;
  andere Arme und Objekte bleiben Kollisionsgeometrie. Training folgt erst
  auf Lehrer-/Beispielprüfung, keine bereits trainierte BC-Policy behaupten.
- BC-Datengeneration17.11.: Nutzer wünscht mehr Teacher-Beispiele, gleichzeitig
  mehrachsige Rotation und Translation. Reine3D-Translations-/3D-Rotations-
  und gemischte6D-Aufgaben untersuchen; getrennte Netze nur als offene Option,
  nicht als Nutzerentscheidung festhalten. Referenzaufgabenklasse von erlaubten
  Ausweichfreiheiten trennen. Ganze Aufgabenfamilien vorab inTrain/Validierung/
  Test aufteilen; nahe Varianten und Nachbarpunkte einerBahn nicht verteilen.
- BC-Startvielfalt17.11.: Nutzer bemängelt ähnliche Abläufe durch nahezu
  gleichen Ausgangszustand. Deutlich verschiedene Objektstartlagen und
  passende Armkonfigurationen einbeziehen, nicht nur Ziel-/Zwischenbahnen
  variieren. Startpose, IK-Zweig und gewünschte Bewegungsrichtung getrennt
  auswerten; gleiche/nahe Startfamilien über alle Varianten im selben Split.
- BC-Schwierigkeit17.11.: Nutzer fordert gezielt Referenzwege, die ohne
  Planung kollidieren, und schnellere Datengeneration. Tatsächliche FCL-
  Kollisionen, Hüllenüberlappung und reine Mindestabstandsverletzung getrennt
  berichten. Gültige Start-/Zielzustände und zunächst einfache direkte
  Referenzverbindungen bevorzugen; teure Lehreroptimierung erst nach Screening.
  Viele benachbarte Samples nicht als viele unabhängige Lernaufgaben zählen.
- BC-Episoden17.11.: Nutzer wünscht freie Kontrollbahnen und viele enge/
  kollidierende Referenzen. Längere Zielketten: erst Ziel erreichen, dann vom
  tatsächlich erreichten Zustand weiter; keine stillen Resets/IK-Wechsel.
  Arbeitsraum auch außerhalb der Mitte abdecken. Tischkollisionen vermeiden.
  Ganze Episoden und verwandte Start-/Ziel-Familien bei späteren Splits
  zusammenhalten. Lange Episode allein garantiert keine hohe Schwierigkeit.
- Offline-Objekttransport17.11.: zuerst unverändertes Idealprofil prüfen;
  bereits ausreichende Bahn nicht allein zur Demonstration verändern. Getrennte
  Zusatzabstandsversuche klar als solche kennzeichnen. Um Kartonmittelpunkt
  rotieren, nicht um STL-Eckursprung. Alle24Gelenke gemeinsam zeitparametrieren
  und tatsächliche Interpolanten auf feste Grifftransformationen prüfen.
  Bewegtes Objekt in Kollisionsszene aktualisieren, keinen festen Kartonrest
  oder pauschale Objekt-/Tisch-/Greiferausnahmen übernehmen. Numerisch erfüllte
  Griffzwänge bei offenen Fingern sind kein Kontakt-/Tragfähigkeitsnachweis.
- Bei variabler Basislage alle potenziell kollidierenden Paare berücksichtigen;
  die bisherige feste Vier-Nachbarpaar-Auswahl nicht ungeprüft übertragen.
  Kollisionsprüfung, globale Planung, zeitliche Koordination und lokale
  Reaktion getrennt bewerten. Szenenabhängige CDF-Kontaktbank vom
  szenenunabhängigen punktkonditionierten Originalansatz unterscheiden.

## Anschauliche HTML-Vorschauen (Nutzerwunsch 2026-11-16)

- Nutzer findet die eigenständige CDF-HTML-Animation hilfreich und wünscht
  solche bedienbaren Übersichten häufiger bei passenden Bewegungs-/Geometrie-
  Aufgaben. Play/Pause, Zeitschieber und frei drehbare Ansicht bevorzugen.
  Modellanimation, Physiksimulation und reale Bewegung deutlich unterscheiden.
- Bei CDF-Darstellungen Gelenkradian und kartesische Meter trennen. Ungerichtete
  CDF-Farbwerte nicht als Kollisionsmaske ausgeben. Bei niedrigdimensionalen
  Schnitten fixierte Gelenke nennen; projizierte6D-Bahnen sind kein Bahnverlauf
  auf genau diesem Schnitt. Abstand zur Kontaktmenge des ganzen modellierten
  Arms von TCP-Abstand unterscheiden.

## Startmenü-App UWA Robot Power (2026-11-16)

- Nutzerauftrag19.11. umgesetzt: **UWA Robot Power** bleibt als GUI auf
  ROSmini; alle4realen Treiber, Live-Zustandserfassung/Guard/Supervisor/Watchdog,
  Greifer und Ausführung laufen auf N100/miniminiPC192.168.8.5 in isoliertem
  `~/uwa-ur-runtime`, Domain66/LOCALHOST. User hat alle4External-Control-Hosts
  auf N100 umgestellt, Ports unverändert. ROSmini-Hardwaredienste sind aus;
  nicht parallel starten. Startmenüeintrag auf `--n100` installiert. SSH zu
  diesem Steuerhost ist für die Runtime beauftragt; keine URScript-/Armsteuerung
  per SSH auf den URs. Aktueller Kartonstand im HANDOVER.
- Kurze Pausen: [UWA Robot Power](docs/ur_power_gui.md). **Standby** stoppt
  das konfigurierte `ros.urp` und schaltet die Antriebe ab; **Start + ROS**
  nutzt den bestehenden UR-Startablauf. Sichtbare Einzelresultate, englische
  GUI. Steuerbox und Pendant bleiben an. Öffnen und Refresh sind rein lesend.
  Keine Shutdown-, Sicherheitsquittierungs- oder Fahrbefehle in der App.

## Gemeinsamer UR-Start für Agenten (2026-11-16)

- Für lesende Zustandsprüfung und ausdrücklich beauftragte Vorbereitung der
  echten Zelle den gemeinsamen Einstieg [UR Bringup](docs/ur_bringup.md)
  verwenden: `python3 scripts/ur_bringup.py --status --json`, bei genehmigtem
  Start `--apply`. `manual_action` je Arm an den Bediener weitergeben.
- `--apply` verwendet vorhandene ROS-Treiber und startet fehlende lokale
  Treiber über den MATCH-Hardware-Launch. Anschließend lädt der Befehl bei
  Bedarf das Inventarprogramm, schaltet ein, löst die Bremsen und startet
  External Control. Kein Quittieren von Stopps, kein Umgehen von Local
  Control oder UR-Sicherheit, keine Fahrziele. Erfolg verlangt laufendes
  `ros.urp` und die passende ROS-Reverse-Verbindung. Der separate
  ROS-Treiber-Launch allein führt weiterhin keine Dashboard-Schreibaktion aus.

## Kameraeinstellungen (Nutzerkorrektur2026-11-17)

- Einmal brauchbar gewählte Fokus-/Belichtungseinstellungen dürfen bestehen
  bleiben; keine routinemäßige vollständige Rückstellung nach jedem Foto.
  Tatsächliche Werte und Intrinsicsbindung speichern, geteilte Nutzung/Leases
  erhalten. Kamera-Dienst/Format müssen weiter funktionsfähig zurückkommen.

## Aufgabenbezogene Konfigurationswahl (Nutzerkorrektur19.11.2026)

- Vor numerischer Optimierung logisch prüfen, ob die Armkonfiguration für die
  ganze Aufgabe geeignet ist. Eine isoliert erreichbare/kollisionsfreie
  Vorposition genügt nicht: insbesondere nachfolgenden Absenk-/Greifweg vor
  der realen Anfahrt prüfen.
- Bei Tischgriffen ist „Ellenbogen unten“ häufig ungünstig. „Handgelenk innen“
  ist tendenziell schlechter, wenn das Handgelenk dadurch näher an einen
  Nachbarroboter kommt. Kontextabhängige Heuristiken, keine universellen
  Verbote oder Ersatz für Modell-/Kollisionsprüfung.
- Konkretes reales Kartonbeispiel: RF mit positivem physischem Ellbogenzweig
  erreichte die hohe Pose, konnte aber die Absenkbahn bei beibehaltenem
  Nachbarpuffer nicht abschließen. Für diese aktuelle Kartonrezeptur den
  zuvor erfolgreichen negativen Ellbogenzweig nutzen; Signum von sin(q_elbow)
  statt bloßes Vorzeichen des mehrumdrehigen Encoders verwenden. RR-Pose vom
  Nutzer als gut bestätigt; bei dieser Korrektur nicht mit umkonfigurieren.
- Danach verbleibende Gelenkreserven, Manipulierbarkeit/Singularitätsnähe,
  Handgelenk-/Nachbarabstände, Wegaufwand und Konfigurationskontinuität
  vergleichen. Maße, Einheiten/Skalierungen und Auswahlbegründung speichern;
  Rangheuristiken nicht als Sicherheitsqualifikation darstellen.

## Modulare Manipulation und starre Greifverbünde (2026-11-13)

- Gemeinsame Greifer-API seit17.11.: eigenes Paket `uwa_cell_gripper_control`,
  Anleitung [ROS-Greifersteuerung](docs/gripper_ros_api.md). Für alle vier Arme
  Python `GripperClient.open()`, `close_gripper(force_raw=...)`,
  `set_opening(percent,...)`; ROS-Action `/uwa_hardware/<arm>/gripper/operate`,
  Status-/Capabilities-Services daneben. Keine eigenen Socket-Schreiber starten.
- `uwa-grippers.service` läuft zunächst MONITOR ONLY. Explizites `scripts/grippers.sh
  enable max_force_raw:=...` nimmt Einzelaufträge an, aktiviert/bewegt aber
  beim Start nichts. Bestehende minimale Kraftgrenze0 bleibt Default. Alte und
  neue ROS-Endpunkte teilen eine Gerätesperre und einen einzelnen Writer.
- Kraft ist ausdrücklich Rohwert0–255, Öffnung nomineller Registerhub0–100%,
  keine kalibrierten N/mm. Aktivieren separat; Exit/Armstopp/Cancel niemals als
  automatische Öffnung interpretieren. Details, Grenzen und Mocknachweis in
  der Anleitung. Bestehende Hardware-Zugriffsabsprachen erhalten.
- Nutzer bestätigt am17.11. ausdrücklich: Rohkraft und relative Öffnung reichen
  zunächst; anschließende Präzisierung: Datenblatt-Sollwerte inmm/N sind als
  nominelle Komforteingabe gewünscht, ohne zwingende eigene Kalibrierung.
  `set_width_mm()` und `close_gripper(force_n=...)` übersetzen beim2F-85
  nominell85mmHub bzw.linear20–235NaufRohwerte. Kraftumrechnung ausdrücklich
  Näherung, keine exakte Herstellerkennlinie/physische Kraftgrenze; Servercaps
  bleiben wirksam. Sollwerte, verwendete Rohwerte und gemessene Istwerte trennen.

- Nutzer erlaubt17.11. OAK-Szenenchecks selbständig, z.B.ob Karton amPlatz.
  Vorhandenen Kameradienst/Lease nutzen und andere Agenten-/Gerätenutzung
  erhalten. Bei geteilter UR-Nutzung vor Controller-/Greifer-/Fahraktionen
  tatsächliche Übergabe abwarten. Nutzer bestätigt17.11. für diesen Kartontest
  „Jetzt frei“; dies ersetzt die frühere Fremdbelegung, nicht die noch offenen
  technischen Nachweise für den beladenen Greifverbund.

- Hardwarestand17.11.: beide rechtenGreifer über gemeinsameROS-API einzeln
  leer raw0→128→0/SPE16/FOR0 geprüft; anschließendMONITOR ONLY/offen. Gemeinsamen
  Greiferdienst wiederverwenden, keinezweitenSocketwriter/Adapter. Leerfahrt
  istkeinN-/mm-/Loadedstopnachweis. TransportfreierObjektreferenzkern und
  Offline-Pregraspweg ersetzenkeinengekoppeltenHardware-Kommandopfad.
- Nutzerfreigabe17.11. für diesen konkreten Karton-Realtest: Schutzprofile für
  unbeladene Anfahrten wechseln, einschließlich kurzer Programmstopps aller4URs
  und anschließender Wiederverbindung unterHolds. Erster geprüfterSchrittRF
  mitKommando.015rad/s/Monitor.03,150mmVorposition, andereArmegehalten.
  JeweilsneueModell-/Stoppreserveprüfung; keineallgemeineHardwarefreigabe oder
  automatischeWiederaufnahmebeladenerFehlversuche daraus ableiten.

- Neuer Auftrag16.11.: langsamen Realtest des Zweiarm-Kartongriffs vorbereiten;
  Nutzer startet URs erst auf Bereitschaft. Während Vorbereitung keine Power-,
  Bremsen-/Programm-, Fahr- oder Greiferbefehle. Realbackend/Greifer/Geometrie
  prüfen; Simulationsnachweise nicht als Realgreifnachweis übertragen.

- Nutzerangaben16.11.: leerer Karton500g;50N beziehen sich auf eine einzelne
  Backe/Wandkontaktfläche. Als Belastungsreferenz behandeln, nicht als
  gemessene Bruchgrenze oder Summe über mehrere Backen.

- Nutzeralternative16.11.: zuerst direkte simulierte Kraftmessung auf Robustheit
  prüfen. Nur bei unbrauchbaren Werten UR-Basis in eigener Simulation optional
  auf passive Linearachse mit Feder, Dämpfung und Ruhelage setzen und Auslenkung
  auswerten. Keine solche Lagerung nötig, wenn direkte Messung genügt. Nicht als
  unabhängig vom selben Physikmodell validierte Referenz ausgeben; Basisbewegung
  in Welt-/TCP-Kinematik berücksichtigen. Einachsige Lagerung erfasst eine
  Belastungsrichtung; Rückstellung zunächst passiv über Federruhelage prüfen.
- Nutzerpräzisierung16.11.: Simulation als Experimentierumgebung zum Ausloten
  schneller Abläufe und ihrer Grenzen verwenden. Bahn-Geschwindigkeit,
  Beschleunigung und Ruck variieren, Kollisionen/Kräfte/Antriebsbelastungen/
  Schlupf/innere Verspannung auswerten; gescheiterte virtuelle Versuche erhalten.
  Bisherige langsame Inbetriebnahmegrenzen nicht als physische Leistungsgrenze
  ausgeben. Explorationsprofile getrennt von bisherigen Prüfnachweisen führen.
- Ziel ist ein schneller simulierter Ablauf und daraus ein realer Ablauf mit
  Reserve für unmodellierte Effekte. Simulationsmaximum/pauschaler Tempoabschlag
  allein beweisen keine Hardware-Sicherheit; Übertragung benötigt Realabgleich.
  Keine pauschale Hardwarefahrfreigabe aus diesem Konzept ableiten. Modell- und
  Numerikfehler von tatsächlichen Belastungsgrenzen unterscheiden. Replaytempo
  ändert keine physikalischen Kräfte; Grenztests in tatsächlicher Kontaktphysik.
- Nutzer möchte agentbedienbare wiederverwendbare Skills mit Voraussetzungen,
  Ergebnisprüfungen, Abbruchverhalten und versionsgebundenen Prüfnachweisen.
  Erste Anwendung: beide rechten URs greifen leeren Karton, heben kurz an und
  setzen ab; zuerst Simulation mit Kontaktphysik, Chat/CLI/RViz. Agent darf im
  konkreten Auftrag selbst prüfen/fortsetzen; keine pauschale Hardwarefreigabe.
- Bedienung neuer Manipulationsaufträge: projektspezifischen Skill
  `.agents/skills/uwa-manipulate/SKILL.md` und aktuellen Prüfnachweis lesen.
  Verfügbarkeit eines Skills ist kein Nachweis eines erfolgreichen Kontaktgriffs.
- Ab bestätigtem Griff ausschließlich gemeinsames Objekt/virtuelles Objektframe
  kommandieren, feste Objekt→TCP-Transformationen der beteiligten Arme. Prinzip
  aus match_cooperative_handling wiederverwenden; keine getrennte Planung oder
  unabhängige Zeitparametrierung tragender Arme. Andere Arme bleiben außerhalb.
- Grenzen/Stopps auf gesamten Greifverbund übertragen; Greifkraft bei Armstopp
  erhalten. Keine automatische Öffnung, Rückfahrt oder Wiederaufnahme. Relative
  Greiftransformationen nicht nachführen, um Schlupf zu verdecken. Verbiegen/
  gezieltes Verspannen ist keine Aufgabe dieser ersten starren Betriebsart.
- Erfolg mit Kontaktphysik setzt echten getragenen Karton voraus; künstliches
  Anheften ist kein Haltekraftnachweis. Masse/Reibung und starres Kartonmodell
  als Simulationsannahmen kennzeichnen, keine Hardwaregenauigkeit daraus ableiten.

## Vierarm-Kollisionswächter und PTP-Vergleich (2026-11-13)

- Realnachweis17.11.: 4Armeparallelbewegt, Geometriecallbackim100msBudget;
  vollständigerWegwegen nativerGeschwindigkeitspeaksabgebrochen. Künftige
  KommandogeschwindigkeitvonüberwachterBetriebsgrenzeunterscheiden; keine
  ungeprüfteFilterung/Rohwertunterdrückung zumBestehen. RealeStoppparameter
  bleibenunqualifiziert, Fehlversuche imVergleich erhalten.
- POWER_OFFkannnachSteuerungsstartnativeRTDE-q=0liefern, obwohldieArmeanders
  stehen. SolcheWerte nichtalsphysischeStartposeverwenden; vorFahrprüfung
  gültigenBetriebszustand/frischeEncoderwerte undDriver-FK-Abgleich verlangen.
- RobotiqRealzugriff17.11.: ACKaufPOS/SPE/FOR-SammelbefehlistkeinParameter-
  Nachweis. FOR/SPEeinzelnsetzen undbeidebestätigen, bevorPOSgeändertwird;
  GTOkannvomvorigenBefehllatchedsein. Alle4offen/Parameterzurückgelesen,
  RohwerteweiterhinkeineKraft-/ÖffnungskalibrierungoderbeladeneGreiffreigabe.

- Nutzerfreigabe17.11.: nach erneutemOAK-Foto bei unbrauchbaremBoardfit99,1cm
  Basisabstand verwenden. NurAbstand als Nutzerakzeptanz übernehmen; keine
  neue aktuelle6D-Kalibrierung behaupten. ZentralesLayoutjetztx±0,4955m,
  Orientierungen/Y/Zvorläufig, laufendeWelten nicht automatischversetzen.
- Nutzer beauftragt unbeladenenlangsamenq1-/q6-Stoppversuch und fragt nach
  vollständigemGreiferöffnen. Greiferaktivierung kann Finger übervollständigen
  Wegbewegen; Leerraum prüfen. Keine N-Zuordnung ausRobotiqRohwerten ableiten.
  LangsameresInbetriebnahmeprofil darf abgeleiteteStoppwege überniedrigere
  durchgesetzteBewegungsgrenzen reduzieren; Modellreserve/Frische nicht lockern.

- Nutzer-Messbezug16.11.: hintere Basis-Montagezentren laut Zollstock100cm,
  Greifer offen und ungefähr20cm Spalt; frühere30cm-Schätzung ersetzt.
  Nominales Modell90cm ist damit abzugleichen. Vorhandene Tischboard-/Basis-
  Kalibrierungen und gemeinsame OAK-Sicht zur relativen Vermessung verwenden;
  bekannte Boardbefestigung und passende K/D prüfen. Keine Armstellungen an
  fragliche nominale Weltanker anpassen oder Wächtergrenzen zum Freigeben senken.

- Nutzerauftrag16.11.: kleinen realen gleichzeitigen Vierarmweg bei laufendem
  Wächter testen, nur auf vorgeprüftem freiem Weg zur Messung von Rechenzeit,
  Takt und Zustandsalter. Keine absichtliche Kollision/Annäherung daraus ableiten.
  Bewegungsüberlappung anhand echter Gelenkgeschwindigkeiten belegen; identische
  Zielversandzeit ist kein Nachweis. Reale Stoppreserve bleibt getrennte Abnahme.

- Nutzerauftrag16.11.: zuerst konservativen Arm-Hüllquader-Vorfilter für
  boolesche Planungs-Abstandsprüfungen umsetzen. Ganze Kugelvolumina/Tools
  und unveränderte Mindestabstände umfassen; Überlappung nur als Kandidat
  behandeln. Exakte Nächstabstände/Gradienten und Wächterstatus nicht durch
  Hüllabstände ersetzen. Gleichheit zu bisheriger Prüfung und echte Laufzeit
  nachweisen; Modelldaten unverändert, eingefrorene Geometrie nur mit gültiger
  Zustands-/Abhängigkeitsbindung wiederverwenden.
- Nutzerwunsch17.11.: die entwickelte hierarchische Kollisionsprüfung bei
  künftigen Wegprüfungen verwenden und Berechnungsdauer nennen. Annahmehier:
  Arm-AABB-Vorfilter; Bestätigungangefragt, nichtmitCDF-Planergleichsetzen.
  Neuerper_body_joint_caps_v2-PlanungszweignutztjetztauchdiesenVorfilter:
  jedesKugelvolumenumeigenenStoppwegaufweiten, ganzeArmhüllebilden,
  beiunklarerTrennungunveränderteFeinprüfung. ExakteWächterabständeerhalten.
  RechenzeitfürModellaufbau, Planung/EndprüfungundrealeFahrzeitgetrenntnennen;
  EinzelbenchmarknichtalsallgemeineLaufzeitgarantieausgeben.

- Nutzerauftrag: unabhängiger10Hz-Kugelwächter für genau LF/RF, LF/LR,
  RF/RR, LR/RR; Diagonalen aus dieser Paarüberwachung ausnehmen. Greifer
  einschließlich offener Finger und Wrist-Gehäuse in die Kugelhüllen aufnehmen.
- Abstandsunterschreitung verriegelt das betroffene Paar, keine pauschale
  Vierarmabschaltung bei einer einzelnen Paarverletzung und keine automatische
  Wiederaufnahme. Datenverlust betrifft die zugehörigen Nachbarschaften;
  Gesamtausfall des Wächters hat keine überwachten freien Paare mehr.
- Erste Stufe Simulation64/uwa_cell_sim; Nutzererweiterung16.11.: Hardware-
  Adapter implementieren und in Mock67 prüfen, reale Anbindung Domain66.
  Bestehende Simulation-only-Sperre erhalten. Kein realer Fahr-/Power-/Brake-/
  Play-Auftrag allein aus Implementierung ableiten. Hardware-Not-Halt von
  Softwarestopp unterscheiden; reale Stoppreserven separat messen.
- Hardwarebackend standardmäßig MONITOR ONLY ohne Controller-/Programm-
  Schreibaktionen. Arming/Provision/Reset/Execute explizit getrennt. Direkte
  Output-RTDE-Gerätefrische, individuelle Werkskinematik, sechs echte Gelenke
  je Manager; Ressourcenbesitz und native STOP-Antwort sind kein Stillstand.
  Supervisor und separater Watchdog, kein automatischer Wiederanlauf/Play.
- Unbekannte reale Greiferöffnung durch Hülle über gesamten modellierten
  Öffnungsbereich abdecken, keine fingierte Greifertelemetrie. Nur interne
  gekoppelte Robotiq-Hüllpaare explizit ausnehmen; externe Tool-/Kamera-/Arm-
  Paare erhalten. Vorläufige Weltanker und ungemessene Stoppreserve sichtbar.
  Anleitung docs/four_arm_hardware_motion.md; Mock-Nachweise sind keine reale
  Brems-/Latenzabnahme. Bestehende manuelle UWA-/MATCH-Bediengates unverändert.
- PTP vorab planen; zeitversetzte Starts/Warten sind erlaubt. RRTConnect und
  unabhängige zirkulare Felder mit derselben Zielauflösung/Endprüfung vergleichen,
  kein versteckter RRT-Fallback im Feldansatz. Nutzererweiterung16.11.: CDF
  wieder aufnehmen, erster Paper-/Code-Nachbau für einen bewegten UR mit drei
  eingefrorenen Armen als starre Hindernisse. Zunächst offline/Simulation,
  Original-CDF in Gelenkradian von kartesischem Abstand unterscheiden; gleiche
  volle MoveIt-Endprüfung behalten. Noch keine Multiarm-/Hardware-CDF-Freigabe.
- CDF-Prototyp: nichtparametrische szenenabhängige Kontaktbank + logarithmischer
  Gelenkraum-QP. Datenvorbereitung getrennt von Onlineplanung/Endprüfung messen;
  geänderte Fremdarm-/Greiferzustände invalidieren die Bank. Kein Franka-Netz
  oder kartesisches SDF als fertig trainiertes UR-CDF ausgeben. Min-/Präfix-CDF
  bleibt Näherung, FCL/Selbst-/Werkzeug-/Tischprüfung und Wächter erhalten.
  Anleitung docs/single_ur_cdf.md, CLI cell_cdf; kein Hardware-CDF-Execute.
- Vergleich30Aufgaben×5Seeds×2Verfahren,10s Planungsbudget. Fehlschläge behalten;
  Planungszeit, Validierungszeit, geplante und tatsächlich gemessene Fahrzeit
  trennen. Anleitung docs/four_arm_motion.md, Paket uwa_cell_motion.
- Laufzeit-Stoppreserve auch bei Wächterausfall erhalten: Supervisor darf die
  letzte geometrische Abstandsreserve nicht durch unbedingtes Ausschöpfen des
  Heartbeat-Timeouts verbrauchen. Paarabhängige Lease/Transportalter prüfen.
  Sim-Nachweise unter normaler Physik(RTF≤1) führen; Beschleunigung separat
  nachweisen. Nicht ausgewählte PTP-Arme bleiben gemessen stationäre Hindernisse.
- Geometrische10Hz-Prüfung und Watchdog-Reserve auf dieselbe monotone Echtzeit
  beziehen; langsame/pausierte Gazebo-Zeit darf die Prüfungen nicht verlangsamen.
  Pausierte Quellzustände bleiben STATE STALE und erfordern bewussten Reset.
  Native/Python-Grenzprüfung gemeinsam mit1e-8rad numerischer Toleranz führen,
  echte Grenzüberschreitungen weiter ablehnen.
- Bewegungsbenchmarks dürfen Bildrendering mit image_sensors:=false abschalten;
  dabei Kamera-/Werkzeugkörper, Inertien und TF erhalten und identische
  Kollisionssignatur/Mesh-Hashes nachweisen. Keine Frische-/Stoppgrenzen wegen
  renderbedingter Pausen lockern und keine Geometrie zur Beschleunigung löschen.
- Stillstand in Gazebo: Arme weiterhin≤3mrad/s; offene Greiferanschläge zeigen
  gemessen bis5,1µrad Zittern bei5,1mrad/s Peak. Werkzeug-Ruhe deshalb über
  ≤10µrad Positionsspanne im300ms-Fenster und eingehaltene Betriebsgeschwindig-
  keit(0,05rad/s) bestätigen. Echte langsame
  Werkzeugbewegung darf diese Prüfung nicht bestehen; Hardware neu bestimmen.
- Motion-Knoten erhalten explizite QoS-Callbacks/Transport-QoS; unbenutzte
  Standard-Warncallbacks wegen gemessenem rclpy-Waitset-Aufwand der1kHz-Simuhr
  vermeiden (`uwa_cell_motion.node.MotionNode`). Empfangsfrische und unabhängige
  Watchdogs bleiben maßgeblich; CPU-Optimierung ist kein Fristgarantienachweis.
- Hardware-Überwachung24.11.2026: Controllerliste, Hardwarekomponenten und
  Hold-Parameter nur beim Verbindungs-, Wechsel-, Reset-, Wiederanlauf- oder
  Zustandsereignis lesen. In ruhendem bestätigtem Hold keine periodischen
  Verwaltungs-RPCs. Supervisor und Watchdog laufen mit20Hz; Guard-RTDE,
  Geschwindigkeits-, Kollisions-, Halte- und native Rückfallprüfungen ohne
  separaten Nutzerauftrag unverändert erhalten. Hardware-Watchdog darf keine
  zweite vollständige Manager-Inventarprüfung aufbauen; sein Rückfall bleibt
  unabhängig und nativer.
- Candidate pilot.3avMfmBY am24.11.2026 nicht übernehmen: Live-Stopp lief
  mit nativen Quittungen, ließ aber links vorne/rechts hinten ohne vollständige
  Hold-Bestätigung und führte zu `ARM STOP ADAPTER UNAVAILABLE`. Bewährten
  20-ms-Takt und periodischen Verwaltungsprüfpfad erhalten; erneute
  Aktivierung ausschließlich nach eigenem Betriebswechsel und belastbarem
  Vierarm-Stoppnachweis.
- Vereinfachter Hardwarestand24.11.2026: der unabhängige Watchdog sendet im
  Hardwarebetrieb nur den native STOP und betreibt keine zweite StopPort-
  Managerabfragkette. StopPort-Leser laufen nur bei aktiver Verriegelung
  oder expliziter Freigabe, nicht im ruhenden unbelasteten Zellenzustand.
  Controllerbesitz, Hardwareplugin und Hold-Parameter werden weiterhin bei
  Stop-, Wechsel- und Resetübergängen geprüft; diese Änderungen ersetzen
  keine nativen UR-Stops oder die RTDE-/Stillstandsüberwachung.
- RViz-Verlustalarme unabhängig vom Geometrieprozess anzeigen und alte Kugeln
  löschen. Ressourcenbesitz nicht als gemessenen Stillstand ausgeben. Kurze
  Zeilenumbrüche verhindern überbreite Leerzeichen des aktuellen Text-Renderers.

## Native HD-Intrinsics hinten links (2026-11-12)

- Jetzt 41Ansichten/33Fit/8Prüfung bestanden, eigene physische Kamera
  06561F1400090106 bei2592×1944/Fokus406 manuell. Empfohlener Export:
  `setup/calibration/hardware_handeye/left_rear_hd_20261112/result_v2/`;
  `selected_result.json` in der Sitzung verweist darauf.
- Hier Brown5 mit k3=0: unveränderter erster freier PASS-Fit in result_v1
  hat nicht monotone Extrapolation außerhalb der beobachteten Ecken. Beide
  Versionen erhalten, keine Flags umschreiben. Physikalisch plausiblere
  Extrapolation ist keine gemessene Genauigkeit der äußeren Bildränder.
- Keine automatische globale Aktivierung oder neuer Hand-Auge-Fit; bisheriges
  VGA406-/Hand-Auge-Profil bleibt erhalten. HD-/VGA-Bildquelle getrennt halten.
  [Nachweis](docs/left_rear_hd_intrinsics_2026-11-12.md).

## Native HD-Intrinsics hinten rechts (2026-11-12)

- Eigene 2592×1944-K/D bei Fokus388 manuell jetzt PASS: 41 Ansichten,
  33 Fit / 8 vorab ausgeschlossene Prüfung. Ergebnis und ROS-CameraInfo unter
  `setup/calibration/hardware_handeye/right_rear_hd_20261112/result_v1/`;
  Nachweis `docs/right_rear_hd_intrinsics_2026-11-12.md`.
- Nur für Kamera01D1111A00090912 / nativen HD-Modus / Fokus388 verwenden.
  Keine automatische globale Aktivierung oder neue Hand-Auge-Kalibrierung;
  bestehendes Rear-VGA404-Profil bleibt unverändert. VGA-/HD-K/D nicht mischen.
  Eckenabdeckung und unabhängige Reprojektion sind keine absolute Weltgenauigkeit.

## Wrist-Aufnahmezeit und Beleuchtung (Nutzerauftrag 2026-11-12)

- Wrist-LEDs aller vier Arme nur während Fotoaufnahme oder genutztem
  Videostream einschalten; im Leerlauf ausschalten. Parallele Kameranutzer
  berücksichtigen, aktive fremde Messreihen nicht durch LED-Wechsel stören.
- HD-Beschleunigung mit gemessenen Zeitanteilen und Bildvergleich begründen;
  native Auflösung, fokusgebundene Profile, Frische-/Kontrollnachweise und
  bestätigte Wiederherstellung erhalten. Qualitätsgleichheit nicht vermuten.
- Umsetzung: `WristCamera.activity()` um ganze Videonutzung legen; einzelne
  HTTP-Bilder, HD-Fotos und Kalibrier-Capture sind erfasst. Shared-Lock-Nutzung
  erhalten, fremde Viewer nicht beim Schließen eines Fensters ausschalten.
  Guardian `uwa-wrist-led-policy.service`, Profile unter setup/wrist_lighting/.
  Manueller Nutzungswert standard30%, idle0. Getter-/Setter-LED-Modi sind auf
  diesen UCC-Versionen verschieden; erfolgreiche manuelle Setterantwort und
  tatsächliche Intensität prüfen, Getter1 nicht als Setter1 zurückspielen.
- LR-Rollout ist abgeschlossen; alle vier Kameras sind in der LED-Nutzungsregel
  erfasst. Vor Kamera-Dienstwechseln weiterhin fremde Messreihen und freie
  Nutzungssperren prüfen. Keine Arm-/Treiber-/Programmaktion aus LED-Arbeit.
  Am13.11. im Leerlauf bei allen vier Kameras LED0 real bestätigt.
  Details docs/wrist_speed_led_2026-11-12.md. Fremde direkte HTTP-/Pendant-
  Clients sind ohne Nutzungsmeldung nicht durch diesen PC erfassbar.

## Ausdrücklich übernommene vorläufige OAK-Registrierung (2026-11-12)

- Historischer OAK-Stand12.11.: **hardware_20261112_v3**. User akzeptiert die
  erklärte erste OAK↔Front-Wrist-Schätzung für erste Versuche; SHA-gebundene
  Annahme im Profil, Original-`passed:false` niemals umschreiben. Roboterfits
  ausv2 unverändert; neue Rear-HD388-Intrinsics separat geprüft, noch nicht aktiviert.
- OAK-Weltpose mit gemessenem Front-q, Werks-FK und übernommener Hand-Auge-
  Matrix abgeleitet, Welt-/Basisanker bleibt vorläufig. OAK-Stativ **raumfest**;
  spätere Tischverschiebung darf es nicht mitnehmen. Neue Weltbasisvermessung
  erfordert explizite Neuregistrierung. Anleitung docs/oak_preliminary_adoption_2026-11-12.md.
- Gazebo und TF/Marker verwenden dieselbe akzeptierte optische Pose; reale
  Referenz `real_oak4_rgb_optical_frame` ist kein LIVE-Bildnachweis. Jetty/Ogre2
  unterstützt hier Brown-Verzeichnung nicht: Sim-OAK-Pinhole und D=0 ehrlich
  deklarieren, physische Rational14-K/D separat erhalten. Stativ weiterhin
  visual-only, kein neu hinzugefügtes Kollisionshindernis. Nur Kamera neu laden,
  keine Arme zurücksetzen oder echte Hardwaredienste dafür neu starten.

## Neue Kalibrierung links vorne (2026-11-12)

- Historische Messung: 41 Ansichten, eigene VGA-Intrinsics und Hand-Auge bestanden
  (640×480, Fokus245 manuell). Relative Basislage zu hinten links über dasselbe
  feste Board bestimmt. [Nachweis](docs/left_front_calibration_2026-11-12.md).
  Basisanbindung seit Nutzerentscheidung18.11. fest übernommen;
  Ursprungsmessung unter dem verlinkten Nachweis erhalten.

- Nutzer beauftragt eigene Kamerakalibrierung und Position des UR5left_front.
  Linkes40mm-A3-Board lautNutzer seitLeftRear-Kalibrierung unverändertbefestigt;
  relativeLF/LR-Basislage daraus bestimmbar, absoluteWeltankerweiterunvermessen.
- Vorbereitung/Status: work/left-front-calibration.md, Messdaten getrennt unter
  setup/calibration/hardware_handeye/left_front_20261112/. FremdeK/D undalte
  Links-Home-Annahmen nicht verwenden; alle4Arme liefern jetztLive-Gelenke.
- CB3links vorne i686/32bit ohnegcc: vorhandenernativerHD-Bootstrap scheitert
  vorKameramodusänderung; funktionierendeHTTP-VGA vonungeprüftemHD unterscheiden.

## Gemeinsame mobile Board-Aufnahme (2026-11-12)

- Nutzer bestätigt mobilesA4-Board IDs75–91 für rechteWristkameras+OAK4.
  App **UWA Camera Capture**, `scripts/camera_capture.sh`, Anleitung
  `docs/three_camera_capture.md`. Kamera-only, keine impliziteArmfahrt/Power/Play.
- Fotos über vorhandenenNative-Wrist-/OAK-Fotopfad, keineHQ-Mittelung eines
  beweglichenBoards. OAK-SDK-Vorschau vorFoto schließen UND gemeinsame
  Dateisperrefreigabe abwarten; `oakctl`-Wrapperende allein genügt nicht.
  Pause gibt nur eigeneVorschau frei, keinefremdenKameraprozesse stoppen.
- Fokusprofil `config/three_camera_capture.yaml`, Originalsicherung und
  vollständigerReadback beiWiederherstellung. NativeHD/VGA/Fokusprofiletrennen;
  RR-HD388 jetzt separat validiert, siehe obiger Ergebnisstand.
  Keine automatischenFits/Aktivierung aus der Aufnahme-GUI.
- Kontrast-/Textfeedback, Live-/Snapshot-/STALE-/Bildaltertrennung. Preview-
  ErkennungkeinGenauigkeitsnachweis, Dreierfotos nichtbelichtungssynchron.
  Bilder/Boardkorrespondenzen/Sitzungsberichte nurunter setup/calibration/.


## Vorhandener statischer HQ-Tiefenmodus (2026-11-12)

- HQ-Snapshot in RViz: `bash src/oak_camera_calibration/tools/oak4_photo.sh view-depth`
  aus Workspace. Eigene Domain65-Ansicht, Standardwolke optional; Datum/STATIC
  sichtbar, keine Kameraoffenhaltung und kein world-/Zelltransform. Nur Aufnahmen
  mit tatsächlicher rektifizierter `projection.K` anzeigen, keine Factory-K raten.

- Für statische Tiefenschnappschüsse den bestehenden Fotodienst verwenden:
  `bash src/oak_camera_calibration/tools/oak4_photo.sh capture --mode depth_hq`
  aus Workspace; ROS `/oak4/depth/capture_hq`, Trigger, Domain65/LOCALHOST.
- Native1280×800-Mono-Stereo,16Frames/Median mit Gültigkeits-/Stabilitätsmasken,
  keine Lochfüllung, Rohframes/Metadaten in `setup/oak4/depth/`. Belichtung/Gain
  beider Monos gehalten; RGB-ISO100 nicht als Tiefeneinstellung behaupten.
- Teilt Kamera-/Transaktionssperre und Dienst `uwa-oak4-photo.service` mit RGB.
  Kamera/Szene stillhalten, keine Roboterfahrten auslösen. Weniger Streuung ist
  kein Genauigkeitsnachweis; Maskierung kann die gültige Fläche verringern.
- Anleitung: OAK-Repo `OAK4_DEPTH.md` (Aufruf/Format/Grenzen/echte Prüfergebnisse).

## Vorhandener OAK4-HQ-Fotodienst

- Für physische OAK-Fotos den [wiederverwendbaren Fotodienst](../oak_camera_calibration/OAK4_PHOTOS.md)
  verwenden: aus Workspace `bash src/oak_camera_calibration/tools/oak4_photo.sh capture`.
  ROS-Domain65/LOCALHOST, `/oak4/photo/capture_hq` als Trigger; Standard/Vergleich
  und Status ebenfalls vorhanden. Installiert: `uwa-oak4-photo.service` (user).
- 48MP8000×6000, HQ ISO100/max90ms/achtFrames, gegateter10fps-Sensorbetrieb.
  Bilder und tatsächliche Frame-/Belichtungs-/Fokusdaten in `setup/oak4/photos/`.
  Kamera/Szene stillhalten; kein automatischer Robotermove/Stillstandsnachweis,
  kein RAW und kein Ersatz einer fokusgebundenen Kamerakalibrierung. Exklusiven
  Kamerazugriff beachten, keine fremden Live-/ROS-Dienste automatisch stoppen.

## Bildbasierte Objektdigitalisierung (2026-11-12)

- Nutzer16.11.: bei ausgeschlossener Kamera konkrete Diagnose für parallele
  Bearbeitung dokumentieren: physische Identität, Fokus/Auflösung, exakt genutzte
  Kalibrierdatei, Messwerte, bekannte Modellgrenzen und offene Ursachen trennen.
  Original-/aktive K/D während gebundener Rekonstruktion nicht überschreiben;
  Diagnose-/Fitvarianten separat mit Quellenhash. LF-Anleitung
  docs/left_front_camera_diagnosis_2026-11-16.md.
- Eigenständiger CPU-Silhouettenprototyp seit16.11. erzeugt nur äußeren
  fototexturierten Formkandidaten. Gitterlöcher/Innenräume nicht aus geschlossener
  Hülle behaupten; watertight ist kein Material-/CAD-/Kollisionsnachweis.
  Anleitung docs/student_robot_visual_hull.md, Pipeline-Standardbackend weiter
  unvalidiert. Keine automatische Aktivierung in Simulation/Tracking.
- Nutzerwunsch13.11.: Digitalisierungsdurchlauf deutlich beschleunigen und
  geringeren Reasoning-Aufwand ermöglichen, geprüfte Qualität/Sicherheit
  erhalten. Wiederholbare Schritte in Runner/Formvorlagen/Prüfcode kapseln,
  schnelle Agentenausführung von neuer Geometrie-/Fehlerentwicklung trennen.
  Erste Runner-Version scripts/digitize.sh, docs/digitization_workflow.md;
  für Routinedurchläufe .agents/skills/uwa-digitize/SKILL.md lesen. Noch keine
  Modellumstellung. Fehler/Tracking-LOST nicht zugunsten Tempo
  umdeuten; tatsächliche Durchlaufzeit und Qualität vergleichbar messen.
- Aktueller Test: studentischer Roboternachbau, Nutzermaße330×300×330mm,
  ausgeschaltet/unbeweglich und Auflagehöhe bestätigt. Komplexe Meshroute;
  keinen Quader/L als fertige Rekonstruktion ausgeben. Ausschaltpause13.11.
  seit Nutzerbestätigung16.11. aufgehoben; alte Fehlerdaten unverändert erhalten.
  Neue Hardwarestarts brauchen frische Zustände/Wegprüfung; historischer
  RTDE-Snapshot ist keine aktuelle Fahrfreigabe. docs/student_robot_digitization.md.
  Nach ausdrücklicher Freigabe lokale UR-Treiber mit UDPv4 neu gestartet und
  ros.urp per Stop/Play verbunden, keine Power-/Brake-Aktion. Aktueller Dienst
  uwa-ur-drivers-udp-20261116.service, Clients FASTDDS_BUILTIN_TRANSPORTS=UDPv4.
  Nutzer danach am Nothalt/freie Fahrbereiche bestätigt;3modellgeprüfte
  Vierarm-Fahrten ausgeführt.20bestätigteBilder,4Standpunkte jeWrist/1OAK.
  GUI/Runner während letzter Fotoaufnahme unerwartet Exit143; letzter Satz
  wegenStillstandsfehler verworfen, rein kameraseitig erfolgreich wiederholt.
  Ursprünglichen Prozess nicht als COMPLETE ausgeben. AlleMotioncontroller
  inaktiv/Stillstand nachgeprüft, Kamera-Restore und LED0 aller4bestätigt.
  Für künftige Fahrten persistente überwachte Prozessführung/Abbruchpfad klären;
  kein automatischer Wiederanlauf. Mesh-/Trackingstufe weiter offen.

- NVIDIA-Compute seit13.11. ausdrücklich verfügbar: gemeinsame Workstation
  titanpc/192.168.2.137, aktuell WLAN. Vorhandene Nutzerumgebungen, Dienste,
  Systempakete und Treiber erhalten; keine Neustarts oder fremde Bereinigung.
  FoundationPose zunächst in eigenem Ordner/eigener Umgebung auf Datenlaufwerk
  prüfen, Last und freien Platz beachten. Keine Robotersteuerung über diesen
  Rechner. Stand und Bedienung in docs/foundationpose_titanpc.md nachführen.
  Seit16.11. realer statischer Karton-Replay mit manueller Startmaske geprüft,
 640×480-Arbeitsbilder und korrekt skaliertes K verwenden.1280×960 erreicht
  aktuelles45%-GPU-Speicherlimit; nicht pauschal erhöhen. Keine Szene-/Boardpose
  des Assets als Schätzprior. ROS-Livebackend/Genauigkeitsabnahme weiterhin offen.

- Weiteres Nutzerobjekt13.11.: L-Konstruktion aus PTFE und Aluminium, eigene
  Asset-ID ptfe_l_assembly_v1. Nutzerangaben20×20mm-Profile/10mm-Platten von
  geschätzten Außenmaßen300×177×181mm unterscheiden. Keine fremde Karton-
  Szeneinstanz ersetzen. Fotoasset fertig; Texturtracker auf diesem Objekt noch
  LOST, keine übertragene Karton-Trackingfreigabe. docs/ptfe_l_assembly.md.
- Kamera-only-Fünfersets können ausdrücklich --telemetry-source rtde nutzen,
  falls ROS-Treiber fehlen: nur Ausgabefelder timestamp/actual_q/actual_qd,
  unabhängiger Stillstandsprozess und unveränderte Prüfgrenzen. Kein Start von
  Treibern, Programmen oder Bewegung; ROS bleibt Standard. Fehlversuche erhalten.

- Nutzerziel13.11.: bekannte Assets mit6DoF-Pose wiederfinden; langsame möglichst
  genaue statische Lokalisierung vor Greifen und schnelle dynamische Verfolgung
  getrennt anbieten. CPU-Prototyp auf Mini-PC erhalten; zusätzlicher NVIDIA-
  Rechner seit13.11. für isolierte Versuche beauftragt (siehe oben). Backend
  austauschbar halten, keine FoundationPose-Funktionsfähigkeit auf Intel behaupten.
- CPU-Prototyp uwa_cell_tracking, docs/object_tracking.md: direkte Kamerapose
  im unveränderten Assetframe, keine bekannte Szenen-/Boardpose als Schätzprior.
  VALID ist visuelle Konsistenz, keine Manipulations-/Millimetergenauigkeitsfreigabe.
  Bildalter/LOST/Mehrdeutigkeit zeigen, bei Verlust keine alte Pose neu publizieren.
  StatischerBurst setzt Kamera-/Objektruhe voraus. Nur Kameraaktionen, keine
  automatische Armfahrt oder Wiederaufnahme pausierter Planungsarbeit.

- Nutzerauftrag13.11.: texturierten Karton als wiederverwendbares Asset in der
  virtuellen Zelle an seiner beobachteten Stelle darstellen. Versionierte
  Modell-/Texturdateien unter description/assets, Instanzen zentral in
  cell_layout.yaml/scene_objects; Pose aus rechterBoardreferenz ableiten,
  keine parallele Weltpose raten. Gazebo/TF/RViz teilen dieselbe Berechnung.
  Zunächst statisches Visual ohne automatische Kollisions-/Planungsaktivierung,
  laufenden Vergleich nicht ändern; Grenzen der Rekonstruktion erhalten.
  Anleitung docs/carton_scene_asset.md, Nachladen ohne Zell-/Armneustart.

- Reale automatische Scans: Kamera-/SDK-/Bildarbeit in eigenem Prozess halten,
  ROS-Stopp-/Zustandswächter davon unabhängig. Keine GIL-/Bildlast im Fahrprozess.
  GUI-Verlust verriegelt den Lauf auch während Fotos; keine automatische
  Wiederaufnahme nach diesem Stopp. Fehlgeschlagene Fünfersets nicht nachträglich
  als bestätigt ausgeben; einzelne gültige Wrist-Fotos getrennt erhalten.


- Nutzer beauftragt echten Scan mit allen vier Armen parallel und bleibt am
  Nothalt. Dafür neue besser getrennte Ziele prüfen; die zuvor ungeklärten
  hinteren Zusatzwege nicht ungeprüft gleichzeitig starten. Runner/GUI:
  docs/parallel_object_scan.md, scripts/object_scan.sh, keine implizite Power/Play.
- Nach beobachtetem Ethernet-Linkverlust lieferten Hardware-Broadcaster weiter
  JointStates aus Cache. Für automatische Hardwarefahrten zusätzlich echte
  Gerätekommunikation prüfen; ROS-Empfangsfrische allein genügt nicht.
  Alte/geänderte Originalsnapshots nicht zum Ausführen freigeben, neu planen.

- Nutzer möchte zur Beschleunigung virtuelle Trennebenen zwischen den Armen und
  maximale Überschreitungen über ganze Wege prüfen. Ganze Kollisionskörper und
  Zwischenbewegung einbeziehen; zeitunabhängige Bewegungsräume statt nur gleicher
  Fortschrittszeiten vergleichen. Ergebnis nur für die exakt geprüften Wege,
  keine allgemeine Arbeitsraum-/Hardwarefreigabe daraus ableiten.
- Offline-CLI scan_separation, docs/scan_separation.md: Mittellinienüberschreitung,
  zusätzliche räumliche Trennung und „nicht nachgewiesen“ unterscheiden. Bei
  ungeklärten Paaren ursprüngliche Reihenfolge/Stillstand erhalten; keine
  Kollisionsprüfung oder nativeUR-Sicherheit aus dieser Analyse heraus deaktivieren.

- Nutzer präzisiert den Ablauf: zuerst OAK-Foto, grobe Objektlage/-maße daraus,
  dann UR-Ansichten planen. Aktueller neuer Karton steht **zwischen beiden
  Tischen**, Unterseite auf Tischhöhe; alte rechte-Tisch-Kartonpläne sind dafür
  überholt. Nutzermaße40×30×20cm sind grobe Angaben, keine Messfreigabe.
- Erste Umsetzung docs/object_scan.md: OAK-Bootstrap noch mit explizit geprüften
  Objektecken; keine vollautomatische Segmentierung behaupten. Planungsreserve
  getrennt von Endmaßen/Unsicherheit behandeln. Planer erzeugt keine Armkommandos.
- Fünfkamera-Aufruf scripts/object_capture.sh nutzt beide40mm-Boardidentitäten und
  kontinuierlichen Stillstandsaudit. Unterschiedliche Boardframes nur über eine
  beobachtete gemeinsame Bildreferenz verbinden (OAK, falls beideBoards sichtbar,
  sonst expliziter Mehransichtsfit von Kameras, die beideBoards sehen), nicht über
  nominelle Tischabstände. Direkt dasselbe sichtbareBoard bevorzugen. Bilder ohne
  passende native K/D nicht metrisch verwenden. Bestehenden Dreikamera-Aufruf erhalten.
- Mehransichts-CAD seit13.11.: docs/carton_multiview_2026-11-13.md. Optik passend
  zu Identität/Fokus/nativeAuflösung mit Quellenhash datensatzlokal einfrieren;
  separate HD-Ergebnisse müssen dafür nicht global aktiviert werden. Widersprüche
  zwischen Kameras sichtbar behalten, problematische Ansichten nicht in ein
  vermeintlich genaueres Mittel zwingen. Zurückgehaltene Objektpixel dürfen weder
  Geometriefit noch ihre Prüfkamerapose beeinflussen; statische OAK-Wiederholungen
  nicht als unabhängige neue Blickrichtungen zählen. Kontur-Nachzeichnung und
  normierte/vereinfachte Details von mehransichtig vermessener Geometrie trennen.

- Nutzerwunsch vom 2026-11-12: vier Wrist-Kameras plus OAK auf einen gemeinsamen
  Objektbereich ausrichten, fünf Fotos pro Schritt und optional kleine zusätzliche
  Bewegungen. Literaturverfahren prüfen; Konzept docs/five_camera_reconstruction.md.
  Bestehende Posen auf jeweils eigene Boards beweisen keine gemeinsame Objektsicht.
  Kleine TCP-Verschiebungen ersetzen keine vollständige Kollisions-/Wegprüfung.
  Kameraextrinsics je Aufnahme bestimmen; bewegte Kameras sind kein starres Rig.

- Erste assistierte Pipeline `digitize_box`, Anleitung docs/object_digitization.md.
  Gespeicherte Dreier-Farbfotos, sichtbares metrischesTischboard, passendeK/D,
  explizite geprüfte Eckpunkte und parametrischer Geometriefit. KeineTiefe beim
  Auftrag „nur Bilder“ hinzunehmen, keineArmfahrt alleinfürDigitalisierung.
- Intrinsics müssen zu Kamera/Fokus/Bildgröße passen; aktuell Rear-HD388 im
  ersten Kartonversuch nur visuell geprüft. Boardpose jeBild neu schätzen;
  keine ungemessenen alten Roboter-/Weltposen als Aufnahmezustand verwenden.
- Verdeckte Details/Wandstärken alsAnnäherung kennzeichnen; Bildfitresiduen
  und reineAnnotationssensitivität nicht als absolute Genauigkeit ausgeben.
  STEPmm/STLm unterscheiden, Exportframe rechtshändig+Zoben. Keine automatische
  Kollisions-/Kalibrierprofilaktivierung; Rohbilder/Sitzungen nurunter setup/.

## Vor der Arbeit

- [ACTIVE_WORK.md](ACTIVE_WORK.md) und aktive Einträge unter `work/` lesen.
  Eigene Aufgabe dort vor Änderungen eintragen und laufend aktualisieren;
  Statusdatei je Aufgabe verwenden, fremde Einträge erhalten. Dienstneustarts
  und gemeinsame Dateibereiche nennen, bestehende Diffs vor Edits erneut prüfen.
- [HANDOVER.md](HANDOVER.md) enthält Ziele, Entscheidungen, bekannte Grenzen und
  Prüfnachweise; [README.md](README.md) enthält Bedienung und Build-Anweisungen.
- Die übergeordneten Workspace-Regeln gelten zusätzlich.
- `HANDOVER.md` bei relevanten Anforderungen, Korrekturen, Entscheidungen und
  Ergebnissen parallel aktualisieren; dauerhafte Arbeitsregeln hier ergänzen.
  Diese laufende Dokumentation ist ein ausdrücklicher Nutzerwunsch vom 2026-11-09.
- Neue Entscheidungen mit Datum festhalten und widersprechende alte Angaben
  bereinigen. Momentaufnahmen laufender Prozesse nicht als dauerhafte Fakten behandeln.

## Fachliche Leitplanken

- UR-konfigurierte Sicherheitsebenen zusätzlich zur MoveIt-Kollisionsgeometrie
  berücksichtigen. C400-Stopp der ersten realen Reihe wurde vom Nutzer als
  solche Ebene bestätigt. Keine Ebene/Schutzfunktion zum Durchfahren ändern
  oder Stopps automatisch quittieren. Aktueller ausdrücklich gewünschter
  Pausen-/Fortsetzungsstand steht in HANDOVER.md; neue Planung erst nach
  erneuter Nutzeranweisung und aktueller Zustandsprüfung.
  Native Protective/Safety Stops können `robot_program_running=true` behalten:
  automatische Fahrabläufe müssen zusätzlich tatsächliches `safety_mode`
  beobachten und wartende eigene Actions canceln/deaktivieren. Nicht auf einen
  langen Action-Timeout warten und keine automatische Quittierung/Weiterfahrt.
  NORMAL/REDUCED zulässig; manuelle GUI-Operationen bekommen dadurch keine
  neuen Dashboard-/Remote-/Armzahl-/Besitz-Freigabegates.

- Nutzerziel vom 2026-11-10: Simulation und die beiden rechten gemessenen URs
  gleichzeitig in RViz darstellen. `uwa_cell_visualization` überträgt nur die
  beiden JointState-Eingänge von Domain66 nach64, niemals Kommandos/Services/
  Actions. Reale Anzeigeframes/Gelenke ausschließlich mit `real_`-Präfix;
  Simulations-Topics/TFs nicht überschreiben. Zielzeitstempel auf die Anzeige-
  Simulationsuhr umsetzen, originale Hardware-Nachrichten unverändert lassen.
  Fehlende/veraltete Daten zeigen, keine erfundenen Null-/Initialposen anzeigen.
  Montageposen aus zentralem Zelllayout bleiben vorläufig, keine automatische
  Kalibrierung behaupten. Anzeige darf Hardware nicht einschalten/bewegen.
- Ziel ist der digitale Zwilling der echten UWA-Zelle mit vier UR-Armen auf
  zwei beweglich positionierbaren Tischen. Plattform: ROS 2 Lyrical / Gazebo Jetty.
- Geometrie, Tischposen, Montageposen und Anfangsstellungen kommen zentral aus
  `uwa_cell_description/config/cell_layout.yaml`; keine parallelen Zahlenkopien
  als zusätzliche Konfigurationsquelle einführen.
  Nutzerauftrag2026-11-11: gemessene gültige Teilkalibrierungen gemeinsam nutzen.
  Standard-Loader verwendet `cell_layout_calibrated.yaml` als dünne Referenz auf
  diese Geometrie plus `config/calibration/hardware_20261112_v3/profile.json`.
  Rohes Nominalmodell bleibt explizit ladbar. Drei Werkskinematiken sowie
  validierte VGA-Intrinsics/Hand-Auge beider Rear-Arme bleiben erhalten.
  Neuester Nutzerauftrag2026-11-12 nach erklärtem Qualitätsfehler: Front-HD-
  Intrinsics und Hand-Auge ausdrücklich übernehmen. Profilv2 verwendet sie mit
  `operator_accepted_below_threshold`, nativen2592×1944 und Fokus435Manual.
  Fehlgeschlagene `passed:false`-Ergebnisse niemals als PASS umschreiben.
  Ausnahme nur pro exakt SHA256-gebundenem Artefakt mit konkreter dokumentierter
  Nutzerentscheidung; ohne diese gelten die bisherigen Qualitätsgrenzen weiter.
  Integrität, endliche Werte, starre Transformationen und Beobachtungszahlen
  bleiben auch bei ausdrücklicher Übernahme geprüft. Keine neue Basis-/Weltpose.
  Posenreferenzen sind keine aktuellen Hinderniszustände/Fahrfreigaben. Keine
  absolute Basis-/Tischpose aus nur ungefähr bekannter Boardlage ableiten.
- Weltachsen: X rechts, Y hinten, Z oben. Montageposen beziehen sich auf
  **URDF `base_link`**, nicht auf den um 180° gedrehten UR-`base`-Frame.
- Die aktuellen Kabelrichtungen und Yaw-Werte aus der Übergabe erhalten.
  Sie ersetzen die ursprüngliche pauschale Front-/Heck-Ausrichtung.
- Tischhöhe und Montagewinkel bleiben Schätzungen bis zur Kalibrierung.
  Scan-Daten dürfen nicht stillschweigend zu kalibrierten Posen erklärt werden.
- 24 eindeutige Armgelenke, vier native Arm-Trajektoriencontroller und ein gemeinsamer
  Controller-Manager unter `/uwa_cell` beibehalten. Seit 2026-11-09 ergänzen vier
  Robotiq-2F-85-Greifer je einen eigenen Controller und fünf gekoppelte Fingergelenke.
- Wrist-Camera-Linse gegenüber dem UR-Werkzeug-I/O-Anschluss montieren:
  im UR-`tool0`-Frame auf +Y. Werkzeugparameter zentral in der Layout-YAML pflegen;
  primitive Kamerageometrie und nominelle Optik nicht als kalibriertes CAD ausgeben.
- Statische OAK4-D als Übersicht auf einem Stativ rechts neben der Zelle:
  `overview_camera` in derselben Layout-YAML verwenden, Pose/Look-at/FOV als
  Designannahmen behandeln. Ihre eigene Gazebo-Entität/TF lässt sich ohne
  Zellneustart neu laden. Keine Kamera-Designänderung darf Arme zurücksetzen.
  Nutzerkorrektur vom 2026-11-09: vorhandenes Stativ erreicht **höchstens 2 m**;
  aktuelle Montagevorschläge daran ausrichten. Die früheren 3-/2,6-m-Posen
  sind nur historische Designversuche, keine umsetzbare Standardmontage.
  Zwei zusätzliche OAK-Kameras sind laut Nutzer für tote Winkel verfügbar.
  Die erste wurde per USB als **OAK-D Pro AF (RVC2)** identifiziert (2026-11-09);
  die frühere Vermutung „beide OAK-D-S2-FF“ ist überholt. Zweites Modell noch
  ungeprüft. Montage/Einsatz offen; keine Kalibrierung der Zusatzkameras voraussetzen.
  Beide ChArUco-Boards aus echten Bildern prüfen; reine Sichtfeldprojektion
  beweist weder fehlende Verdeckung noch kalibrierte Genauigkeit. Das bisher
  nur visuelle Stativ ist kein Hindernis in der MoveIt-PlanningScene.
  Seit2026-11-12 Kamera-Visual aus Nutzerarchiv oak4-pro-3d-model.zip,
  reduzierte Meter-Meshes unter meshes/visual/oak4_pro; eigene Stativgeometrie.
  Beide Ansichten verwenden overview_visuals.py. Optische Pose/K-D bei reinem
  CAD-Wechsel erhalten; CAD-zu-Optik-Anker und Stativ bleiben visuelle Näherungen.
  Nur Übersichtsentität neu laden, keine Zelle/Armzustände dafür zurücksetzen.
- ChArUco-Boards zentral je Tisch und Kameras initial darauf ausrichten.
  Nutzerauftrag24.11.2026: professionellen Neudruck ohne Bindung an DIN-A-
  Formate einschließlich größerer Platten beurteilen. Außenmaß, aktive
  Musterfläche und Feld-/Markermaß getrennt angeben. Größenempfehlungen
  sind noch keine beschlossene Umstellung der vorhandenen Boardreferenzen.
  Folgeauftrag24.11.: PRO-v1-Druckdaten zu den empfohlenen Maßen erstellen.
  Eigene Druckdefinition `config/print_designs/charuco_professional_v1.json`
  mit DICT_5X5_250 verwenden; keine aktive Kalibrierung durch den PDF-Auftrag
  umstellen. Bedienung und Druckprüfung: `docs/charuco_professional_print.md`.
  Separates mobiles UR-Board seit2026-11-11: A4-Holzträger mit plan aufgeklebtem
  Papier, Definition `uwa_cell_description/config/mobile_charuco_a4.yaml`.
  7×5 Felder38mm/Marker28mm, DICT_4X4_100 IDs75–91. Nicht mit den40mm-
  Tischboards/IDs0–16 bzw.50–66 verwechseln; diese bleiben unverändert.
  Werkzeug-zu-Board-Montage ist unbekannt, Druckvorlage ist keine Kalibrierung.
  Präzisiertes Nutzerziel (2026-11-09): einen Tisch absichtlich bewegen und
  relative Tischpose/Bewegung messen und kompensieren. Boards bleiben starr
  an ihren Tischen; ihre weltfesten Posen dürfen nicht vorausgesetzt werden.
  Kameramontagen zu ihrem Träger getrennt von veränderlichen Tischposen schätzen.
  Option: OAK auf rechtem Tisch schaut auf linkes Board. Montage ist relativ zum
  rechten Tisch konstant, auch wenn dieser bewegt wird. Zur Einmessung ein
  separates bewegliches Board verwenden, Tischboards dafür nicht versetzen.
  Raumfeste Kamera, tischfeste Kamera und Tisch-zu-Tisch-Messung unterscheiden;
  Simulation-Ground-Truth bleibt unabhängig von der bildbasierten Schätzung.
  Referenzen für diese Kalibrierung sind `left_table_top` / `right_table_top`.
  OpenCV-Musterframe: Ursprung an der Musterecke ohne Rand, Z in die Platte.
  Bildschätzung und Ground-Truth-Vergleich getrennt halten; keine Ground Truth
  zur Auswahl/Initialisierung der PnP-Lösung verwenden. Bekannte Hand-Auge-
  Transformation nicht als aus einer Einzelansicht neu kalibriert bezeichnen.
- Simulation isoliert betreiben: Domain 64, lokale Discovery, Partition `uwa_cell_sim`.
  Physisches Inventar getrennt in `config/hardware_inventory.yaml`:
  `right_rear`=192.168.8.170, `right_front`=192.168.8.103,
  `left_rear`=192.168.8.169 (Nutzerzuordnung/Lesetest2026-11-11),
  `left_front`=192.168.8.2 (Nutzerzuordnung/UR5-Identität2026-11-12), OAK4=192.168.8.238.
  LinksFrontCB3/PolyScope3.15 hat keine e-Serie-Remote-Abfrage; ein unbekannter
  Dashboardbefehl ist kein Beleg fürLocal. FehlendeURCap/Programmkonfiguration
  undRTDE-Inputbelegung tatsächlich klären, nicht perUR-Sicherheitsänderung umgehen.
  Nutzerzählung „erster/zweiter“ ist zufällig; nur stabile Arm-IDs verwenden.
  Kabel laut Nutzer am2026-11-10 ersetzt. Roboterrouten geprüft über Ethernet
  enp87s0, PC192.168.8.209. Keine aktive Sonderbehandlung für die frühere
  Funkanbindung, historische Messwerte nicht in Ethernetwerte umdeuten.
  Nutzerziel vom 2026-11-10: reale Hand-Auge-Erprobung zuerst ausschließlich
  `right_rear`; Bildzugriff und manuell aufgenommene Messreihe vor automatischen
  Hardwarefahrten prüfen. Bestehender Kalibrierbackend bleibt Simulation-only;
  HTTP-Bildempfang ist kein Nachweis eines frischen Belichtungszeitpunkts.
  Nutzerpräferenz desselben Tages: Wrist-Fokus möglichst vom PC per Skript/
  Schieberegler steuern. Fehlende öffentliche API nicht als grundsätzliche
  Unmöglichkeit ausgeben; USB-Anwenderberichte von am Gerät geprüfter Funktion
  unterscheiden. Fokusstellwerte nicht ohne Kennlinie als Meter interpretieren.
  Seit demselben Tag Kamera-Schreibtest/Qt-Fokusfenster für right_rear genehmigt
  und umgesetzt: Kameraeinstellungen sichern, ausschließlich Fokus ändern,
  Bildwirkung/Readback prüfen; keine Robotermotion daraus ableiten.
  Folgeauftrag erlaubt zusätzlich Belichtungs-/Gain-/LED-Regler und begrenzte
  native Foto-Versuche. Helligkeitsänderungen dürfen den Benutzerfokus nicht
  überschreiben. Kameramoduswechsel können Fokus zurücksetzen; sichern und
  ausdrücklich wiederherstellen. Hochskalierung nie als native Auflösung ausgeben.
  Seit2026-11-12 nativer5MP-ROS-Bilddienst für right_front real geprüft:
  `docs/wrist_hd_service.md`. SSH bleibt auf diesen ausdrücklich beauftragten
  Kamerapfad begrenzt; Hardware-GUI/Armsteuerung bleibt SSH-frei. Keine Kennwörter
  speichern. HD/VGA-/physische Kamera-ID undFokus nicht innerhalb eines Fits
  mischen,HD-Intrinsics neu schätzen. Empfangszeiten nicht als Belichtungszeiten
  ausgeben. WährendHD-Transaktion Telemetrie weiterverarbeiten,Originalkamera-
  zustand/Normal vollständig bestätigen und bei Fehler kein Messbild akzeptieren.
  CB3 vorne links: nativen i686-Kameradienst gemäß `docs/wrist_hd_service.md`
  starten; tatsächliche Sensorwerte während der HD-Bursts verifizieren.

  Seit 2026-11-09 ist MoveIt-Kollisionsprüfung für die automatische Kalibrierung
  umgesetzt. Allgemeine kooperative Planung und Hardware-Anbindung bleiben Folgearbeit.
- Automatische Hand-Auge-Kalibrierung: unbekannte Kameraextrinsics aus mehreren
  Stellungen schätzen, nominelle Montagen ausschließlich zum Planen verwenden.
  Validierungsbilder vor Aufnahme festlegen und nie zum Fit verwenden. Ground
  Truth erst nach dem Fit getrennt vergleichen. Linkes/rechtes Tischpaar getrennt.
  Bildzahlvergleiche innerhalb derselben physischen Kamera bei konstantem
  Optikprofil und gleichen, vom Fit ausgeschlossenen Prüfbildern durchführen.
  Gleicher Kameratyp an verschiedenen Armen ist kein Nachweis gleicher
  individueller Intrinsics oder Montage; Arm-/Kamera-/Bildzahleffekte trennen.
  Hardware-CLI seit2026-11-12 für alle vier Arm-IDs; left_rear verwendet das
  linke40mm-Tischboard(IDs0–16), nicht das mobile38mm-A4-Board. Fokus und
  Intrinsics je physischer Kamera neu bestimmen, keine rechten Profile kopieren.
  Nutzer hat für die konkrete Vorbereitung links hinten ausdrücklich automatisches
  Einschalten/Bremsenlösen/Laden/Starten über vorhandenen MATCH-/Dashboard-Ablauf
  beauftragt. Dafür bei erreichbarem Remote-UR keinen unnötigen manuellen
  Pendantstart verlangen. Dies ist keine Freigabe neuer Arm-Fahrziele. Local-
  Umschaltung/fehlende aktive URCap-Konfiguration nicht vom PC umgehen.
- Nutzerkorrektur2026-11-12: diagonale reale Arme dürfen unabhängig parallel
  arbeiten; Front-HD muss nicht auf links hinten warten. Nutzerangabe zur
  physischen Zelle: diagonal reicht die Reichweite nicht zum Berühren. Dies
  ist eine Bedienerangabe, keine gemessene geometrische Kalibrierung. Neue
  Hardware-Messbatches benennen genau `independent_diagonal_arm` und nehmen
  nur dieses Roboterpaar aus MoveIt-Kollisions-/Stillstandsabhängigkeiten aus.
  Paare: left_rear↔right_front bzw.left_front↔right_rear. Selbst-,Tisch-,Greifer-,
  Kamera- und andereArmkollisionen bleiben geprüft, gleichseitiger Tischpartner
  bleibt stationär überwacht. NativeUR-Safety/STOP unverändert. Vorige pauschale
  Einarm-/„erstlinks fertig“-Reihenfolge ist für diagonalePaare damit überholt.
- Genehmigte Bedienung: eigene Qt-GUI für die Kalibrierung mit Vorbereitung,
  Start, Pause/Fortsetzen, jederzeit erreichbarem Stopp und explizitem Übernehmen.
  rqt bleibt die manuelle Zellsteuerung. Seit dem Folgeauftrag vom 2026-11-09
  standardmäßig links vorne + rechts hinten, danach links hinten + rechts vorne
  parallel kalibrieren; andere Arme vorher seriell zur Seite parken. Alle Wege
  gegen die vollständige MoveIt-Szene und getrennte gepufferte Bewegungsräume
  prüfen; blockierte Wege ablehnen. Stopp/Pause betreffen das gesamte aktive Paar.
  Einzelarmmodus bleibt als Auswahl erhalten; keine automatische Rückfahrt nach Stopp.
- Übernommene Kalibrierung ausschließlich als versioniertes Profil und separates
  `calibrated/`-TF-/Planungsmodell aktivieren. Physische Gazebo-Montagen und
  Ground-Truth-Modell erhalten. Ergänzung2026-11-11: Nutzer beauftragt explizit
  die gültigen real gemessenen Teilparameter auch als Simulationsstandard;
  dies erfolgt über obiges zusätzliches Profil, ohne das Nominalmodell zu ändern.
  Simulierte Nachkalibrierungen je Modellprofil getrennt speichern, frühere
  ideale Simulationsfits niemals als reale Messungen laden. Optikfit misst
  keinen Gehäusekörper: nominelle Kamera-Kollisionskörper nicht daraus versetzen.
  Keine automatische Rückfahrt nach Stopp/Fehler.
  Sitzungen/Rohbilder unter `$UWA_WS/setup/calibration/` nicht einchecken.

- Nutzerauftrag2026-11-12: Kamera-SSH ohne wiederholtePasswortdialoge, dedizierte
  Schlüssel unter~/.ssh; `wrist_hd.SSH` verbindet automatisch mitstriktemHostvertrauen.
  Drei e-SerieURsEd25519,CB3LinksFront eigenerRSA3072wegenOpenSSH6.0,kompatibler
  Signaturmodus nurfürdiesenHost. KeineKeys/PasswörterinsGitoderLogs. SSH bleibt
  aufbeauftragteKameraoperationenbegrenzt,HardwareGUI/ArmsteuerungSSH-frei.

## Verbindliche Bedienerwartungen

- Folgeauftrag2026-11-10: erste reale Bildpose und Intrinsics-/Hand-Auge-Test
  ausschließlich right_rear. Nutzer bestätigt rechtes A3-Board1:1 und100mm
  Kontrollstreifen, keine bekannte passende Wrist-Intrinsics-Kalibrierung.
  Separate Hardware-Aufnahme auf Domain66, Simulationsbackend nicht umbiegen.
  Reale Intrinsics aus tatsächlich verwendetem Bildmodus/festem Fokus fitten;
  nominelles K/optische Montage nur zur Planung. Vorab markierte Validierungs-
  bilder aus Intrinsics- und Hand-Auge-Fit ausschließen. Echte JPEGs, erkannte
  Punkte, Kamerazustand und gemessene Werkskinematik-Flanschpose speichern.
  HTTP-Empfang/wechselnde Payloads sind keine garantierten Belichtungszeitstempel.
  Nutzer hat nach Vorschau eine40-Ansichten-Hardwarefolge ausdrücklich freigegeben;
  diese Einzel-Erprobung nicht als generelle Bewegungsfreigabe verallgemeinern.
  Ergebnisse separat versionieren und nicht ungefragt als aktive TF übernehmen.

- Nutzerauftrag2026-11-10: vor Hardware-Kamerakalibrierung andere Arme seriell
  parken, zunächst nur right_front per generischem Skript testen. Linke Arme
  laut Nutzer bereits aufrecht in Default Home: nominell [0,-90,0,-90,0,0]°,
  als Nutzerangabe kennzeichnen, keine Encodermessung behaupten. Parkwerkzeug
  plan/preview/execute trennt konkrete Wegprüfung von Realfahrt; MoveIt-Szene
  und tatsächliche rechte JointStates verwenden. Fehlende Hinderniszustände
  niemals still aus Simulationsposen zu realen Messungen machen. Nur einen Arm
  bewegen, keine automatische Heim-/Rückfahrt nach Abbruch. Vorschau Domain68,
  keinerlei Kommandobrücke zu Hardware66/Mock67/Gazebo64. Kalibrierbackend
  selbst bleibt Simulation-only, bis separat beauftragt/integriert.

- Nutzerauftrag2026-11-10: MuR-artiges manuelles Jogging, zunächst right_rear,
  mit demselben IntegratedCartesianAdmittanceController/J-PARSE. Nachgiebigkeit
  standardmäßig AUS: admittance und wrench_twist_gain null, keine FT-Pflicht.
  Gainänderungen des on_init-Plugins durch inaktives Neuladen anwenden, nicht
  bloß als dynamische ROS-Parameter setzen. Hold-to-jog/Loslass-Stopp, Base-Frame,
  keine automatische Fahrt durch Öffnen des Dialogs oder Aktivieren des Reglers.

- Nutzerhinweis vom 2026-11-10: Monitor mit schwachem Kontrast. Klickannahme
  deutlich hervorheben, nicht nur durch subtile Standard-Buttonzustände.
  Dauerhafte Rückmeldung mit großen Textlabels RECEIVED/RUNNING/DONE/FAILED,
  Aktionsname, Verlauf/Fehlerdetail und Laufzeitanzeige. Automatische Statuspolls
  dürfen ein manuelles Fehlerergebnis nicht überschreiben. Bedienung auf Englisch.
- Nutzerwunsch vom 2026-11-10: UR-GUI vollständig **Englisch**, einschließlich
  Beschriftungen, Tooltips, eigener Meldungen und Startmenüeintrag **UWA Arms**.
  Gesprächssprache bleibt Deutsch. **Save logs** muss während laufender
  Operationen erreichbar bleiben und aktuelle Sitzung/Prozessausgaben/zugehörige
  ROS-Logs lokal mit Status-Snapshot exportieren. Eindeutige Sitzungsordner,
  keine bloß gekürzte Bildschirm-Logkopie; älteren übernommenen Treiberkontext
  kennzeichnen. Exporte unter `setup/logs/uwa-control/exports/`, neuester Pfad
  in `setup/logs/uwa-control/latest-export.txt`. Keine Roboterbefehle beim Export.
- Nutzerauftrag vom 2026-11-10: lokale Vierarm-Vorbereitung und vereinfachte
  eigene UWA-GUI mit Armauswahl oben links, ohne SSH/rsync/mobile Infrastruktur.
  Gemeinsamer UR-Start und Controller bleiben im MATCH-Repo (`match_ur_hardware`,
  `mur_control`, `mur_launch_hardware`); `uwa_cell_control` referenziert sie.
  Physische Konfiguration ausschließlich aus `config/hardware_inventory.yaml`.
  App **UWA Arms**: Mock als Standard in Domain67, Hardware in Domain66,
  jeweils lokale Discovery; Mock-Treiber/-Clients strikt von Hardware trennen; kein
  automatisches Power/Brake/Play beim Treiberstart. Vorhandene Ein-Gegenarm-
  Kollision nicht als vollständigen Vierarm-Kollisionsschutz darstellen.
  Neueste Nutzerkorrektur vom 2026-11-10: zusätzliche UWA-Sicherheitsgates
  entfernen. Keine Armzahl-, Dashboard-NORMAL/Remote/RUNNING/PLAYING-, exakte
  Programmpfad- oder GUI-Treiberbesitz-Sperre vor manuellen Operationen.
  Keine eigene Netzwerk-/Latenz-Sperre einführen. Native UR-/Treiber-
  Ablehnungen und vorhandene Kollisionsalgorithmen erhalten. Insbesondere keine
  UR-Sicherheitsfunktionen umgehen oder Stopps automatisch quittieren.
  Standardauswahl bleibt hinten rechts (`right_rear`). Automatische Regressionen
  verwenden Mock und senden keine realen Power/Brake/Play/Ziele. Davon getrennt
  hat der Nutzer am selben Tag den konkret in RViz geprüften Hardware-Parkweg
  für right_front ausdrücklich freigegeben; diese Einzel-Erprobung dokumentieren.
  Laufende andere Hardwaretreiber erhalten.
  Technische Profil-/Portprüfung, Schutz gegen doppelte Treiberinstanzen und
  Aufräumen eigener Prozesse erhalten. Bedienung: `docs/ur_control_gui.md`.
- Die App **UWA Cell Simulation** soll mit normalem Klick Gazebo, rqt, RViz
  **und den Scan-Publisher** starten. Auch ihre Aktion **RViz öffnen** lädt den Scan.
  Den früheren App-Standard ohne Scan nicht wieder einführen.
- Der direkte Terminal-Launch darf weiterhin ohne Scan starten; die Simulation
  muss auch bei fehlendem Drive/Scan funktionieren.
- Wiederholte App-Aufrufe sollen vorhandene Dienste weiterverwenden und weder
  doppelte Publisher erzeugen noch die laufende Simulation unnötig zurücksetzen.
  Bereits geöffnete Fenster wiederherstellen/nach vorne holen; „Dienst aktiv“
  allein erfüllt die sichtbare Bedienerwartung beim erneuten Icon-Klick nicht.
- RViz muss explizite Kamera-Werkzeuge enthalten: `MoveCamera` als erstes Tool,
  außerdem Interact, Select, FocusCamera und Measure. Orbit-Drehen und Zoom müssen funktionieren.
- Das App-Icon gefällt dem Nutzer. Außenrand transparent lassen, das dunkelblaue
  abgerundete Feld und das Vier-Roboter-Motiv erhalten. Den weißen Rand nicht zurückbringen.
- Originalscan auf Google Drive belassen; keine PLY-Dateien oder Scan-Caches einchecken.
- Scan-Bereinigung: 4 m Kugelradius in Weltmetern um den Mittelpunkt der vier
  Roboterbasen; die aufgenommenen Roboter durch feste Scan-Masken ausblenden.
  Masken nicht an die aktuellen bewegten Modell-TFs koppeln. Bei Änderung der
  Scanregistrierung die Masken neu prüfen; Rohdaten und Importcache erhalten.

## Prüfen und übergeben

- Build, Umgebungsvariablen und Prüfkommandos aus der README verwenden.
- Passend zur Änderung prüfen: bei Layoutänderungen Modell/TF, bei Controlleränderungen
  zusätzlich Simulation und gezielte Bewegungen, bei App-Änderungen den **installierten**
  Desktop-Eintrag statt nur einen manuell gestarteten ROS-Knoten testen.
- Eine aktivierte PointCloud-Anzeige oder „Status: Ok“ allein beweist keinen Scan-Empfang:
  Publisher, empfangene Punkte und den Transform zur Welt prüfen.
- Bei Änderungen an Setup/Startmenü die nötige Installation konkret durchführen
  und die Bedienung in der README mitpflegen. Bestehende lokale Änderungen erhalten.
- Dokumentation: belegte Erfolge mit Datum/Logpfad und offene Einschränkungen nennen;
  keine neuen Tests oder Hardware-Freigaben behaupten, die nicht erfolgt sind.

## Karton-Seitenlage (Nutzerauftrag 2026-11-16)

- Bestehende Zweiarm-Simulation um 90°-Drehung des Kartons um seine Längsachse
  erweitern; Öffnung zur Kamera und in dieser Orientierung auf Tisch absetzen.
  Vorhandene Manipulationspipeline möglichst wiederverwenden. Arbeitsannahme:
  Kamera ist die feste OAK-Übersicht; keine neue Hardwarefreigabe.
- Volle Hebe-/Dreh-/Absetzgeometrie vor Einfahrt prüfen; reine 30mm-Translation
  ist kein Prüfnachweis einer Vierteldrehung. Drehzentrum als Objektpunkt
  erhalten, Objekt→TCP-Offsets bleiben eingefroren. Tisch-/Selbstkollisionen
  und Stoppreserven auch beim Absenken erhalten.
- Vor Arbeiten an SHA-gebundenen Taskquellen laufende Greifwelten über Host-
  Prozesssicht prüfen: sandboxed `ps` kann andere Prozesse ausblenden. Neue
  Quellen invalidieren bestehende Szenen, auch ohne Neustart ihrer Prozesse.

## Simulierter Geschwindigkeits-/Kraftvergleich (Nutzerauftrag2026-11-17)

- Nutzer möchte denselben geplanten Ablauf schrittweise beschleunigen und
  Kontaktkräfte zunächst bei5×Robotergeschwindigkeit vergleichen. Tatsächliche
  Physik ausführen, nicht bloß die Replaygeschwindigkeit ändern.
- Exakte gemeinsame Zeitkompression: t/5, v×5, a×25, Ruck×125; keine unabhängige
  Retimung tragender Arme. Greifvorspannung, Masse/Reibung und Physikschritt für
  den Vergleich festhalten. Welche Bewegungsabschnitte tatsächlich gemessen
  wurden und welche bereits an Reserven scheitern, ausdrücklich unterscheiden.
- Kräfte in vergleichbaren Bewegungsfenstern auswerten; nicht Greif-/Warte- und
  Bewegungsphasen beliebig in ein Maximum mischen. Einzelne beobachtete Läufe
  von Wiederholstatistik und realer Belastbarkeit unterscheiden.

- Seit 19.11. gelten Stoppreserven in der Simulation ausschließlich als
  Offline-Planungsmodell. `simulation_stop_reserve_mode` betrifft die
  Planprüfung. Die alten Kontakt-/Schlupf-/Frische- und Gruppenwächter in
  Gazebo sowie die damaligen höheren Simulations-Wächterraten sind überholt.
  Die historische Echtzeitvorbereitung ging von 350 ms/2 rad/s² im
  Simulationsmodell und 1300 ms/0,2 rad/s² im Real-Commissioning aus.

- RT-Folgeauftrag17.11.: KernelinstallationundUR-Echtzeitrechteausdrücklich
  erlaubtundabgeschlossen; NeustartnachNutzeransage, nichtautomatisch.
  InstallierterRT7.0.0-43-realtimewirdStandardboot, Generic43/42alsFallback.
  BenutzerspezifischePAM-/user@1000-/UR-Dienstlimits99/unlimitedbereit,
  laufendeTreibernichtneu gestartet. NachBoot tatsächlicheLimits/Scheduling
  prüfen, keinenLatenz-/BremsnachweisalleinausInstallationableiten.

- Nutzerauftrag17.11.: Reaktions-/Bremstestbevorzugtamright_frontvorbereiten,
  keineAusführungalleinausdieserVorbereitung. Bestehendensingle-q6Probe
  wiederverwenden, optionaler500HzOutput-Beobachter; Default20HzdesWächters
  erhalten. Softwarestopppfad/EmpfangslatenzvonphysischemBremsbeginntrennen.
  Detailsdocs/right_front_realtime_stop_test.md; Armübergabe/Kalibrierungbeachten.

- Folgeauftrag17.11.: kleinen realen RF-q6-Test durchführen; Nutzer bestätigt
  freie/unbeladene Übergabe und Not-Halt-Zugriff, danach nötigen ROS-Programmstart
  aller4. Nach Geschwindigkeitsstopp überwachte Grenze ausdrücklich auf0,1rad/s
  erhöhen. Konkretes Profil `hardware_right_front_stop_test.yaml`: nur RF-q6
 0,1, übrige Achsen0,003 und Fahrkommando weiter0,003rad/s. Keine pauschale
 0,1rad/s-Fahrfreigabe für alle Arme; neue Körper-/Achsreserve vollständig prüfen.
  Reale Messfehler/fehlenden Nachlauf nicht als Bremsnachweis ausgeben.
