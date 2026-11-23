# Kartonfahrt mit Aufgabenfreigabe

## Am Arbeitsplatz

**UWA Robot Power → Motion review** öffnet die englische Freigabeansicht.
Das vorhandene Startmenü auf ROSmini verwendet den N100. Bei einer offenen
Entscheidung meldet sich das Tray-Symbol und öffnet die Anfrage. Das Schließen
des Fensters lässt die App im Tray. **Quit** beendet sie und widerruft die
bekannte Bereichsfreigabe.

1. Vor Ort den freien Bereich prüfen und für die Arbeitssitzung freigeben.
   Beim Betreten oder Umbauen den Bereich widerrufen. Der Widerruf läuft über
   den N100. Bei unterbrochener Verbindung zeigt die GUI an, ob der N100 den
   Widerruf angenommen hat. Der Hardware-Not-Halt ist vor Ort wirksam.
2. Für den tischgestützten Kartongriff Vertrauen und Höchsttempo einstellen.
   *Unsure* fragt nach jedem Fahrplan, *Familiar* erlaubt automatisch niedriges
   und *Confident* zusätzlich mittleres Risiko. Der Agent beschreibt Arme,
   Kontakt, Abstand und verbleibende Unsicherheit. Hohes Risiko geht an die
   Bedienperson. Vertrauen steigt nur durch deren Eingabe.
3. Bei einer Anfrage den geplanten Ablauf in RViz abspielen oder mit dem
   Zeitschieber durchgehen. Die Übersicht nennt gemeinsame und serielle
   Abschnitte. Aufnahmezeit und vergrößerbares Einfahrbild erscheinen bei der
   Kontaktentscheidung. **Approve**, **Reject** und **Request new plan** gelten
   jeweils für die angezeigte Version. Ein erneuter Start nach Verbindungsabbruch
   liest zuerst den N100-Status.
4. Die beiden Höchstwerte gelten gleichzeitig. 100 % entsprechen 250 mm/s
   Translation am Werkzeug und 0,3 rad/s je Gelenk. 33⅓ % entsprechen 83⅓ mm/s
   und 0,1 rad/s. Eine bewilligte Testreihe legt Namen und kleinsten
   Prozentwert fest. Der Agent darf innerhalb dieses Bereichs absenken.
   Die Bedienperson bestätigt jede Erhöhung, auch nach Ende der Testreihe.
   Änderungen am Tempo verwerfen offene Freigaben und entziehen einer aktiven
   Ausführung die bisherige Freigabe.

## Programmbibliothek im Browser

**UWA Robot Power → Program library** öffnet die englische Übersicht im
Browser auf ROSmini. Die App startet den Server lokal beim Öffnen. In
**Supported carton grasp → Open program** stehen die Phasen und Startoptionen.
**Run offline demo** führt die vorhandene analytische OAK4-Registrierung am
archivierten Standardbild aus, plant Anfahrt und Einfahrt aus gespeicherten
Gelenkdaten und prüft den sichtbaren Kartonrand in zwei separaten
Wrist-Aufnahmen. Fortschritt, Ergebnisse und die drei Bildvorschauen erscheinen
im Laufstatus. Die Wrist-Aufnahmen gehören zu einem früheren Vorgriff.

Die Bibliothek lässt sich auch ohne Power-Fenster vom Workspace starten.
Für den eingerichteten N100-Livepfad die aktive Optikdatei übergeben.
`http://127.0.0.1:8780` ist dann die Adresse auf ROSmini.

```bash
python3 src/multi_arm_manipulation_UWA/scripts/skill_library_server.py \
    --live-config setup/skill_library/live-carton.json
```

Für eine reine Offline-Bibliothek den Parameter `--live-config` weglassen.
Nach einem Wechsel des Servermodus die Browserseite neu laden. Die
Schaltfläche **Start program** folgt der Live-Konfiguration dieser Instanz.

Im Offline-Webtest vom 19.11.2026 wurde die verschobene Kartonlage aus einem
echten OAK-Bild neu registriert. Die 16 sichtbaren Board-Ecken bestätigten die
Kamerareferenz. Der Planer fand für beide Phasen eine gemeinsame Bahn,
44,0 s nominelle Armfahrt. Registrierung, Planung und Wrist-Auswertung
zusammen liefen in diesem Test in 38,4 s. Der vordere Wrist-Prüfpunkt lag
außerhalb des Bilds, hinten war die gelbe Kante messbar. Die Wrist-Auswertung
fordert deshalb eine Sichtprüfung an. [Webtest und Ergebnis](../../../setup/tasks/uwa_program_library_check_20261119/verified.json)

### Ablauf an der realen Zelle

Das separate Library-Programm **OAK4 camera calibration → Start calibration**
erfasst einmalig die festen Tischboards mit dem
ChArUco-Fotomodus. Das rechte Board und die zum Standardfoto passenden
Intrinsics bilden die Kamerareferenz für diesen Kartonablauf. Die Bibliothek
zeigt die Ablaufzeit in AWST. Die Referenz gilt zwölf Stunden ab der Aufnahme.
Bei verstellter Kamera oder verschobenem Tischboard vor einem Greiflauf
erneut das [Kalibrierprogramm](camera_library_program.md) starten. Ein neuer Kalibriervorgang ersetzt die
vorherige Sitzung. Bis eine gültige Referenz vorliegt, ist **Start program**
deaktiviert. Der Kalibriervorgang benötigt nur die OAK4.
Die Kartondetailseite verlinkt über **Open camera calibration** darauf.

**Start program** prüft Arbeitsbereich und Tempo. Der N100 liest die
External-Control-Bereitschaft der beiden rechten Arme und sendet bei Bedarf
Play für das geladene `ros.urp`. Dafür müssen Arbeitsbereich, Stillstand,
offene unbeladene Greifer und die bestehenden Haltezustände bestätigt sein.
Bei einer erforderlichen weiteren Vorbereitung meldet der Browser den
betroffenen Arm und dessen Zustand. Fehlt ein ROS-Lesedienst für einen
Greifer, nennt die Meldung den betroffenen Dienst.

Anschließend liest der N100 den gemessenen Zustand der Arme und Greifer.
ROSmini prüft die Eignung des Startzustands, bevor die OAK4 das aktuelle
Standardfoto erfasst. ROSmini bestimmt die
Kartonpose mit der gespeicherten Kamerareferenz, plant die Hochanfahrt
und offene Einfahrt und prüft beide Bahnen. Das statische Rezept wird bei
gleicher Modell- und Quellversion wiederverwendet. Der N100 übernimmt die
geprüfte Bahn mit unveränderten Sollwerten für **Motion review** und
Ausführung. Nach bestätigter offener Einfahrt reicht die Bibliothek eine
zweite aktuelle Aufnahme für die Kontaktfreigabe ein. Der Bediener
bewertet beide Anfragen in UWA Robot Power. Ein abgelehnter oder
abgebrochener Lauf endet am betreffenden Schritt.

### Hydrogen Low als Reserve für den Bildfit

ROSmini verwendet zuerst die festen Suchfenster. Wenn bereits erfolgreiche
Hydrogen-Fenster gespeichert sind und der aktuelle Tischbildausschnitt bei
derselben Kamerakalibrierung ähnlich aussieht, probiert ROSmini diese
Fenster zuerst. Für beide Varianten rechnet der vorhandene Posefit mit den
aktuellen nativen OAK4-Pixeln.

Fehlen im Standardfit genügend gültige, zusammenpassende Hypothesen,
schickt ROSmini einen verkleinerten Tischbildausschnitt und die
[feste Anweisung](agent_trials/PROMPT_CARTON_VISION.md) über Antigravity an
Gemini 4 Hydrogen Low. Das Modell liefert Bildrechtecke. ROSmini validiert
das JSON, leitet daraus Suchfenster ab und berechnet die Pose erneut.
Bei erfolgreichem Fit speichert ROSmini die Fenster und eine kleine
Helligkeitssignatur für spätere Aufnahmen. Im Laufordner zeigen
`registration-reused/` und `registration-hydrogen/`, welche Fenster
verwendet wurden. `hydrogen.json` enthält Modellantwort und gemessene Anfragezeit.

Die Reserve wird auf ROSmini durch `setup/skill_library/carton-hydrogen.enabled`
aktiviert und nutzt daneben `carton-hydrogen-windows.json`. Sie gilt für
Läufe mit aktueller ChArUco-Kamerasitzung.

### Lokale Konfiguration

Der erwartete lokale Konfigurationspfad ist `setup/skill_library/live-carton.json`.
Dieses Beispiel zeigt die Felder für die dokumentierte rechte Kartonlage.
`enabled` bei der Betriebsübernahme auf `true` setzen. Bildausschnitte beziehen
sich auf das native 8000×6000-Standardbild. Der Fokus kommt aus der verknüpften
Intrinsics-Datei. `camera_session` bezeichnet die vom Kalibrierprogramm
erstellte aktuelle Referenz. Archivläufe können weiter ihre ursprüngliche
`camera_reference_pose` mit zugehörigem `registration.json` verwenden.

```json
{
  "enabled": false,
  "intrinsics": "../calibration/oak_capture_proposal_20261118/calibration_candidate_v1/oak_pose_candidate.json",
  "roi": [2400, 2850, 5000, 5050],
  "face_roi": [2450, 3200, 5000, 5000],
  "camera_session": "carton-camera-session.json",
  "planar_texture": true
}
```

Der Webstart prüft die gemeinsame Version von Programm, Fahrprofil und
Trajektorienprüfer. Die Offline-Umgebung auf ROSmini kann bei getrennten
Controller-Builds die bereits eingesetzte N100-Version aus
`setup/skill_library/n100-checker/` an den Bahnbeleg binden. Bei Abweichung
meldet der Webstart die betroffene Komponente. Der N100 vergleicht die
gebundenen Daten mit seinem Laufzeitmodell, der aktuellen Freigabesitzung
und dem eingestellten Tempo. Beim Ausführen bleiben die Live-Prüfungen
für Iststart, Treiber und Schutzdienste aktiv.
Bei zu wenigen gültigen Textur-Fits versucht die planare Registrierung
denselben Ausschnitt mit lokaler Kontrastanpassung. Der Vergleich prüft
weiterhin die Bildpunkte, Tischauflage und Posenübereinstimmung.
Das ursprüngliche Fehlerfoto vom 19.11.2026 wurde damit offline auf N100
erfolgreich registriert. [Registrierungsnachweis](../../../setup/tasks/carton_web_registration_20261119/contrast-fallback/registration.json)
Der Pilot verlangt eine aktuelle Arbeitsbereichsfreigabe und die für den
Start notwendigen nativen Zustände aller vier Arme. **Start + ROS** ist
die getrennte Bedienaktion für die Programmbereitschaft. Der Gelenkzustand
umfasst pro Arm eine Messreihe für die bestehende Ruheprüfung. Den Stand
der Rechnerübergabe und die Zeitmessungen führt die [Übergabe](../HANDOVER.md).

FoundationPose ist ein separater RGB-D-Archivpfad mit Startmaske. Der
Weblauf verwendet die vorhandene analytische Registrierung. Das
Wrist-Skript `tools/check_carton_wrist.py` passt per Farbmaske eine Linie an
den gelben Rand an und vergleicht sie mit einem projizierten Zielpunkt. Für
eine automatische Kontaktentscheidung fehlen unter anderem sichtbare
Griffmitten und Backen. Die modellierte Sicht an der bereits gemessenen
offenen Einfahrt spricht dafür, die Kameraposition oder die Prüfpose zuerst
an der Zelle zu prüfen. Der reale Aufruf verwendet zur Kontaktentscheidung
das frische OAK-Einfahrbild. [Wrist-Sichtnachweis](../../../setup/tasks/uwa_program_library_check_20261119/wrist-entry-fov.json) · [FoundationPose-Datenpfad](foundationpose_titanpc.md)

## Gespeichertes Kartonprogramm

`carton-supported-v1` speichert das Griffdesign für denselben Avocado-Karton
und das rechte Armpaar. Die JSON-Datei hält die Griffhöhe relativ zur Wand und
die bevorzugten IK-Startwerte fest. Der Runner verwendet die vorhandene
Phasenfolge aus hoher Anfahrt, offener Einfahrt, Bildprüfung, Schließen und
HOLD. Kartonpose und Gelenkstart sind Eingaben pro Lauf. Bei einer neuen Pose
werden die Griffpunkte in Weltkoordinaten transformiert und die Anfahrt und
Einfahrt aus dem aktuellen Armzustand berechnet und geprüft. Die Freigabe
bezieht sich auf die dabei entstandene Bahnversion. [Programmdefinition](../config/carton_programs/carton-supported-v1.json)

### Zwei Posen im Offline-Vergleich

In beiden Fällen waren das gespeicherte Programm und der Vierarm-Snapshot
identisch. Bei der zweiten Eingabe wurde die registrierte Pose im Modell um
50 mm entlang Welt-X verschoben. Beide Griffpunkte folgten dieser Verschiebung.

| Objektpose | Planungszeit | Nominelle Hochanfahrt | Nominelle offene Einfahrt |
| --- | ---: | ---: | ---: |
| Aus archiviertem OAK-Bild | 22,07 s | 35,22 s gemeinsam | 8,78 s gemeinsam |
| Synthetisch um 50 mm verschoben | 21,68 s | 35,31 s gemeinsam | 8,79 s gemeinsam |

Die Modellschranke der Hochanfahrt lag bei 40,13 bzw. 42,04 mm bei
geforderten 40 mm. Aus diesen zwei Posen lässt sich noch kein Arbeitsbereich
ableiten. Die echte Bilderkennung und der Kontakt am verschobenen Karton sind
offen. Bei verdecktem Tischboard oder ungünstiger Sicht kann die Registrierung
weiterhin einen aktuellen Bildausschnitt oder eine bestätigte Kamerareferenz
benötigen. [Messwerte und Eingabe-Hashes](../../../setup/tasks/carton_program_reuse_20261119/comparison.json)

Die verschobene Variante lässt sich aus `~/UWA_ws` in der vorhandenen Mock-GUI
öffnen. Für die Archivpose `plus-50mm` durch `registered` ersetzen. Dann
**Motion review → Open RViz → Play preview** wählen.

```bash
python3 src/multi_arm_manipulation_UWA/scripts/ur_power_gui.py \
    --review-mock setup/tasks/carton_program_reuse_20261119/plus-50mm/gui-mock
```

Eine andere gespeicherte Pose lässt sich aus `~/UWA_ws` mit dem gleichen
Programm prüfen. `$snapshot`, `$pose` und `$new_run` bezeichnen den
gespeicherten Vierarmzustand, die Objektpose und ein neues Ergebnisverzeichnis.

```bash
source setup/lyrical_env.bash
python3 src/multi_arm_manipulation_UWA/tools/run_carton_cycle.py \
    --plan-only --program carton-supported-v1 --observations "$snapshot" \
    --object-pose "$pose" --output "$new_run"
```

`--plan-only` schreibt beide Bahnbündel und `workflow.json` mit Programmversion,
Eingabe-Hashes und Phasenstatus. Es verwendet das Pilottempo von 33⅓ % für
die Modellrechnung. Für eine Variante des Griffdesigns eine neue JSON mit
eigenem Namen und passender `program_id` unter `config/carton_programs/` ablegen
und die vollständige Anfahrt und Einfahrt prüfen. Für eine neue Kartonpose
genügt die geänderte Pose als Eingabe.

## Ablauf für den planenden Agenten

Der N100 verwaltet Entscheidungen in `~/.local/state/uwa-motion-review`.
Der bevorzugte Livepfad ist der Webstart auf ROSmini. Native OAK-Aufnahme, Metadaten
und zugehörige Intrinsics vorab wie im
[realen Kartonablauf](carton_supported_grasp.md) bereitstellen. Das
Registrierungsfoto nach der Bereichsfreigabe dieser Sitzung aufnehmen.
Für versetzte Kartons akzeptiert der Zyklus die bestehenden Registrierungsoptionen
`--roi`, `--face-roi` und `--camera-session` für eine gültige ChArUco-Referenz.
`--camera-reference-pose` bleibt für den bisherigen Referenzpfad verfügbar. Mit
`--verification-image` und `--verification-metadata` lässt sich eine zweite
aktuelle Aufnahme direkt gegen dieselbe Modelltextur prüfen. Jedes Bild muss
einen eigenen gültigen Auflagefit liefern; beide Posen müssen die bestehenden
Übereinstimmungsgrenzen erfüllen. Eine optionale `--photo-reference` dient nur
als Bildmerkmalsreferenz und liefert keine alte Objektpose zurück. Vor dem
Hardwarepilot muss der N100 den passenden Runner- und Guard-Stand
betreiben. Andere Fahranforderungen und die Bedienung am Pendant mit den
anwesenden Personen abstimmen.

```bash
python3 tools/run_carton_cycle.py --plan-only --output "$plan" --program carton-supported-v1 \
    --observations "$snapshot" --object-pose "$pose" --speed-percent "$active_speed"
```

Der Webrunner protokolliert die Übergabe der geprüften Bahnen und ihrer
Eingaben in `stage-receipt.json`. Ein manueller Liveempfänger auf dem N100
verwendet `--prepared-approach`, das ursprüngliche N100-Snapshot über
`--expected-observations` und die ursprüngliche Arbeitsbereichsfreigabe
über `--expected-scene-session`. Das frische Bild und die zugehörigen
Aufnahmedaten dienen der Bindung der aktuellen Kartonpose.
`risk` ist `low`, `medium` oder `high`. Ohne Einschätzung ist die Bedienperson
gefragt. Während
einer offenen Entscheidung wartet derselbe Prozess und prüft anschließend
den aktuellen Start. Beim manuellen Aufruf mit `--start-ros-programs`
liest der Pilot unmittelbar vor der Fahr- oder
Kontaktfreigabe den Dashboardzustand und die ROS-Reverse-Verbindungen aller
vier Arme. Laufen alle vorbereiteten Programme, gilt die normale Risikostufe
der Aufgabe. Brauchen einzelne Arme Play, zeigt die Anfrage deren Namen.
Der Bedienentscheid umfasst Play für diese Arme unter bestätigten unbeladenen
Holds sowie die angezeigte Aktion. Bei fehlender Verbindung oder anderem
Vorbereitungsbedarf meldet der Pilot die Ursache. Fällt später ein weiterer
Arm aus, erfordert dessen Start eine neue Freigabe.
Power, Bremsen und Programmvorbereitung bleiben im separaten Betriebsablauf.
`--path-budget-s` erhöht nur die verfügbare Offline-Rechenzeit, keine
Fahrgeschwindigkeit. Der Iststart ist die gemessene Eingabe je Lauf.
Eine Ablehnung oder Neuplanungsanforderung beendet
diesen Versuch. Für eine geänderte Bahn ein neues Ausgabeverzeichnis wählen.

Nach bestätigter offener Einfahrt ein **neues OAK4-Standardbild** zusammen
mit dessen tatsächlicher `metadata.json` vom Arbeitsplatz auf den N100
übertragen. Originaldateiname und gemeinsames Aufnahmeverzeichnis erhalten.
Die UTC-Zeit der Aufnahme muss hinter der Einfahrt liegen. Die
Arbeitsstation und der N100 müssen dafür übereinstimmende Wanduhren haben.
Mit `--visual-confirmed` bestätigt der Agent, dass er genau dieses Bild
auf offene Backen, Lage an den Wandseiten und Tischauflage geprüft hat.

```bash
python3 tools/run_carton_cycle.py --output "$run" --close-after-review --execute \
    --entry-image "$capture/standard.png" --entry-metadata "$capture/metadata.json" \
    --visual-confirmed --risk medium --reason "$observed_alignment"
```

Ohne `--visual-confirmed` geht die Bildentscheidung auch bei hohem Vertrauen
an die Bedienperson. Die GUI bindet Foto und Entscheidung an denselben
Auftrag. Nach dem Greifschluss bleibt die Gruppe im überwachten HOLD. Bei
möglichem Teilkontakt die tatsächlich gemeldeten Kontaktmitglieder im
Greiferbericht prüfen. Der Pilot endet hier.

Die Agentenschnittstelle für eine bereits vom Bediener bewilligte Testreihe
lautet `python3 tools/motion_review.py reduce --series-name "$series" --speed-percent "$lower"`.
`area`, `settings` und `decide` sind Bedienoperationen der GUI. Die Freigabe
ist eine Regel des Pilotablaufs. Berechtigte direkte Treiber- und
Pendantzugriffe existieren weiterhin.

## Welche Prüfungen wann laufen

Bei einer Sperre zeigt **UWA Robot Power → Safety log** die aufgezeichnete
Ursache und vorhandene Messwerte. **Save logs** sichert einen aktuellen
Bericht lokal. Über den Rechtsklick auf den Starter lässt er sich auch während
einer offenen Freigabesitzung separat öffnen. [Bedienung und Export](ur_power_gui.md#investigating-a-stop)

| Zeitpunkt | Befund und Verwendung |
| --- | --- |
| Entwicklung oder Profilwechsel | Mock-Fehlerfälle, Stoppvermessung und die Qualifikation eines höheren realen Betriebspunkts. Die strengere Ruheprobe aus der Stoppvermessung gehört hierhin. |
| Planung | Aktueller Start, Kartonpose und Werkzeuggeometrie, aufgabengerechte IK, vollständige Hochanfahrt und Einfahrt, Gelenk- und TCP-Grenzen der interpolierten Befehle. Versuch einer gemeinsamen Bahn, anschließend Prüfung der getrennt möglichen Armfortschritte und Stopps. Bei Engstellen werden Teilgruppen oder eine serielle Folge direkt im Plan gespeichert. |
| Freigabe | Ein N100-Entscheid zur ganzen Armfahrt, gegebenenfalls ein weiterer zum tatsächlichen Kontakt. Bahninhalt, Tempo und zulässiger Programmstart gehören zur Revision. Jeder Abschnitt kann genau einmal in der geprüften Reihenfolge gestartet werden. |
| Vor und während Bewegung | Frischer Iststart und native Zustände, Programm, Modell, Greifer, Ressourcenzuordnung und Betriebsruhe. Guard, Supervisor und Watchdog begleiten die Ausführung. Bahnabweichung, Geschwindigkeitsüberschreitung und unerwarteter Kraftwechsel bei der offenen Einfahrt können stoppen. |
| Stillstand und Leerlauf | Der Kartonpilot verwendet die bestehende Freigabe über Positionstrend und Positionsspanne. Bei Kontakt, möglicher Fremdbewegung oder unbestätigter Lage bleibt die Schutzpflicht aktiv. Ein freier Leerlauf setzt einen nachgewiesenen exklusiven Sperrmechanismus für sämtliche Fahrquellen voraus. Der reale N100 hat direkte ROS- und Pendantquellen. Dort bleibt der Schutz bewaffnet. |

Der Parallelprüfer verwendet die im Betriebsprofil gewählte Reservepolitik.
Bei `geometric_only` bleiben die vollständige Geometrieprüfung, der
40-mm-Modellpuffer und die Prüfung aller unabhängigen Armfortschritte aktiv;
es werden keine zusätzlichen Brems-/Latenzhüllen erzwungen. Bei `enforce`
werden diese Hüllen weiterhin berücksichtigt. Gemeinsame Gruppen erhalten
denselben Startzeitpunkt. Die realen Geschwindigkeits-, Frische-, Abweichungs-
und nativen UR-Stopps bleiben in beiden Modi aktiv.

Der Aufgabenprozess empfängt Driver-JointStates über einen eigenen Empfänger,
damit Geometriearbeit und Dienstaufrufe die Messhistorie nicht unterbrechen.
Gepufferte Daten müssen weiterhin ihre ursprünglichen Zeitstempel und die
unveränderten Frische-/Vergleichsgrenzen erfüllen; ein Empfängerfehler stoppt.
Die Reviewidentität bindet auch diesen Empfänger und den Uhrabgleich.

Die GUI-Prüfsumme bezieht sich auf die vorgelegten Sollbahnen. Eine Abweichung
eines realen Arms innerhalb seines geprüften Fortschrittskorridors ist möglich.
Die 40-mm-Modellreserve des aktuellen Kartonprofils ist geometrisch. Die neue
Parallelprüfung berichtet Mindestschranken und den Einfluss der Stoppannahmen.
Diese Modellgrößen sind keine gemessenen Bremswege. Näheres im
[Hardware-Schutzkonzept](four_arm_hardware_motion.md).

## Ergebnisse und lokale Reproduktion

Beide ROS-2-Lyrical-Pakete ließen sich bauen. Die [107 lokalen Tests](../../../setup/tasks/carton_motion_review_20261119/pilot-tests.xml) und zehn isolierte Freigabetests auf dem N100 bestanden. Auf dem N100 wurden GUI-Endpunkt und neue Bewegungssteuerung im realen Kartonauftrag übernommen. Die erste reale Vergleichsfahrt steht aus; aktuellen Betriebszustand und Nachweise nennt [die Übergabe](../HANDOVER.md).

Zwei fertig gefüllte Stores aus demselben Karton-Archivfall liegen auf ROSmini.
Aus `~/UWA_ws` öffnet dieser Befehl die Demo mit der gemeinsamen offenen
Einfahrt der rechten Arme.

```bash
python3 src/multi_arm_manipulation_UWA/scripts/ur_power_gui.py \
    --review-mock setup/tasks/carton_motion_review_20261119/gui-mock-parallel
```

1. In **UWA Robot Power · Mock review → Motion review** auf **Open RViz** klicken.
   RViz zeigt zuerst die Startpose. Im zweiten Fenster **UWA planned motion · …**
   auf **Play preview** klicken. Falls RViz das Fenster verdeckt, mit **Alt+Tab**
   wechseln. Der Zeitregler lässt sich auch bei pausierter Vorschau bewegen.
2. Im Parallelbeispiel fahren die rechten Arme zunächst einzeln zur Vorposition.
   Für die gemeinsame Einfahrt den Zeitregler auf etwa **24 von 47 Sekunden**
   schieben und **Play preview** klicken. **4× playback** beschleunigt die Anzeige.
3. Um auch die Entscheidung auszuprobieren, im Fenster **Mock review** oben
   **Release work area for session** klicken. Sobald **WORK AREA RELEASED**
   angezeigt wird und der offene Plan geladen ist, ist **Approve** verfügbar.
   Damit wird die Entscheidung lokal gespeichert. Die Vorschau lässt sich
   schon vor der Freigabe abspielen.

Für die Vorschau beim tatsächlichen Startwert das letzte Argument durch
`setup/tasks/carton_motion_review_20261119/gui-mock` ersetzen. Der Vergleich
zeigt die Wahl des Zeitplans anhand der konfigurierten Stoppannahmen:

| Archivfall | Modellbefund |
| --- | --- |
| Rechte Arme, 33⅓ % | Untere geometrische Abstandsschranke bei der Hochanfahrt 146 mm, bei der offenen Einfahrt 168 mm. Mit unabhängigem Stopp beider bewegter Arme ergibt sich für das geprüfte Paar jeweils eine untere Schranke von −145 mm bei geforderten 40 mm. Beide Phasen werden seriell vorgeschlagen. |
| Dieselben rechten Arme, Offlinebeispiel bei 10 % | Die Hochanfahrt bleibt seriell. Die Einfahrt passt gemeinsam, einschließlich Stoppannahmen mit mindestens 56 mm Modellabstand. Nominal 23,28 s gemeinsam gegenüber 46,53 s seriell **bei denselben 10 %**. |
| Archivierte Diagonalfahrt, links vorne und rechts hinten | Beide historischen Bahnen passen in eine gemeinsame Gruppe. 18,75 s nominelle Gruppenzeit, 37,50 s nacheinander. |

Die Modellwerte beschreiben die archivierten Startzustände und die vor der
Profilkorrektur zusätzlich erzwungenen Stopphüllen. Sie sind kein aktueller
Nachweis für serielle Planung unter `geometric_only`. Eine negative
untere Schranke bedeutet, dass der Nachweis für diese Variante scheitert.
Die Referenzdateien liegen im [lokalen Ergebnisordner](../../../setup/tasks/carton_motion_review_20261119/).

`workflow.json` enthält Wanddauer je Phase, Wartezeit auf Entscheidungen,
deren Herkunft und Zeit seit Workflowstart bis zur ersten beobachteten
Bewegung. Die Phasen `high` und `entry` verwenden getrennte native
Gelenkmessungen für Dauer und Überlappung. Es zählen aufeinanderfolgende
Samples mit mindestens einem Gelenk über 0,003 rad/s und höchstens 0,15 s
Abstand. Fehlende Daten werden ausgewiesen. Den Zeitvergleich mit denselben
Start- und Endzuständen und demselben Tempowert durchführen.

Vom Arbeitsplatz aus lässt sich ein vorhandenes Paar geprüfter
`--prepare-reviewed`-Bündel im isolierten Mock-Store anzeigen:

```bash
python3 tools/motion_review.py --store "$mock_dir" replay \
    --high-bundle "$high_bundle" --entry-bundle "$entry_bundle"
python3 scripts/ur_power_gui.py --review-mock "$mock_dir"
```

Im Mock hat das Power-Fenster keine Verbindung zu Robotersteuerungen. RViz
nutzt eine eigene lokale Vorschaudomain 74. Für die Bedienung des N100 stehen
die [Installationsvarianten](../../../setup/n100/ur-runtime/README.md)
zur Verfügung.
