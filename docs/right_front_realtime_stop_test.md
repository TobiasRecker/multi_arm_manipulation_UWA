# Vorbereiteter Reaktions- und Stopptest: right_front

Stand: 2026-11-17. Vorderer rechter UR **192.168.8.103**. Nach der ursprünglichen
Vorbereitung hat der Nutzer die Durchführung, den freien/unbeladenen Bereich,
Not-Halt-Zugriff und nötigen ROS-Programmstart ausdrücklich bestätigt.

## Aktueller Stand nach drei Realversuchen

Das ausdrücklich gewünschte neue Profil
`uwa_cell_motion/config/hardware_right_front_stop_test.yaml` ist im vorhandenen
Schutzdienst aktiv. Überwachte Grenze **nur RF-q6: 0,1 rad/s**, alle übrigen
physischen Achsen weiterhin 0,003 rad/s. Das Fahrkommando bleibt bei 0,003 rad/s,
Beschleunigung 0,006 rad/s² und maximalem q6-Zielversatz 0,03 rad. Die bestehende
5%-Überwachungstoleranz bleibt erhalten (Auslösung oberhalb 0,105 rad/s für q6);
die Reserve berücksichtigt denselben Wert.

Die vorhandene Rechnung `per_body_joint_caps_v2` trennt Kommandotempo und
überwachte Einzelachsgrenzen. Vollständiger neuer Plan mit FCL, Körperreserven,
40-mm-Modellpuffer und unveränderten Fristen/Stoppannahmen bestanden. Kein
Absenken der Reserve, um die höhere Grenze freizugeben.

- Versuch03: ursprüngliches Profil. Tatsächliche kleine Bewegung, aber Guard
  meldet q6 0,004729 rad/s über 0,003; daher Stopp vor dem absichtlichen Trigger.
  Unglätteter 500-Hz-Peak 0,021313 rad/s. Kein Reaktionszeitmesspunkt vorhanden.
- Versuch04: neues Profil. Absichtlicher Supervisor-Stopp nach bestätigter
  Bewegung ausgelöst und ACK erhalten; kein Geschwindigkeits-/Geometriefehler.
  RF-Hold im passiven Trace nach etwa49ms sichtbar, Guard bestätigt RF im
  Stillstandsfenster nach etwa619ms. Beides ist **keine physische Bremszeit**.
  Der Runner behandelte die erwartete Action-Cancellation als Fehler; native
  Aufnahme endet49,9ms nach Anforderung, vor ausreichend langem Niedrig-
  geschwindigkeitsfenster. Deshalb keine belastbare Bremszeit/-strecke ausgeben.
- Versuch05 nach gezielt geprüftem Recorderfix: **PASS**, eigener Stopp/ACK,
  gemessener Stillstand, Hold und Verriegelung bestätigt. Kein Guardfault.
  8.078 native Samples mit lückenlosem2ms-Geräteraster, Aufnahme bis940,8ms
  nach Anforderung. Median-q6-Geschwindigkeit davor0,001728rad/s.
  Empfangsbasierter20%-Abfall nach14,79ms; erstes mindestens20ms langes Fenster
  mit allen sechs Gelenkgeschwindigkeiten≤0,0002rad/s ab30,86ms. Strengeres
  Quiet-/Hold-/Latch-Fenster nach939,23ms bestätigt. Keine dieser Größen ist
  eine qualifizierte allgemeine Reaktions-/Bremsgrenze. Größte Empfangslücke
  im gesamten Lauf22,41ms; Geräteraster allein ist keine Latenzgarantie.
  Analysierter q6-Nettoverlauf nach Anforderung nur4,77µrad und damit unter
  der beobachteten Encoderstreuung: daraus keine genaue Bremsstrecke ableiten.
  Nach dem ersten niedrigen20msFenster folgen noch kurze gemeldete Schwellen-
  überschreitungen (q6bis175,7ms, q5bis384,8ms);31ms daher nicht als dauerhaften
  Stillstand bezeichnen. Durchgehend unter der Schwelle bis Aufnahmeende erst
  ab386,84ms; bestätigtes strenges QuietWindow390,78–936,90ms.
- Unabhängige anschließende1,2sNativekontrolle: alle4stationär/RUNNING/NORMAL,
  ros.urpPLAYING und Reverse verbunden. RF bleibt im Supervisor verriegelt
  und gehalten; keine Rückfahrt oder erneuter Reset nach dem Versuch.

Die1,2sKontrolle oben gehört zu04. Nach05 bestätigt der vollständige native
Messlauf selbst das strenge Stillstandsfenster; abschließend alle4URs erneut
RUNNING/NORMAL/PLAYING mit Reverse-Verbindung. RF bleibt gehalten/verriegelt.
Kein Reset oder Rückweg nach05; das neue Profil bleibt aktiv.

Artefakte `setup/realtime/right-front-stop-20261117-{03,04,05}/`: Plan, Original-
Executionrecord, angewendete Trajektorie, passive Interlockspur, Programmstatus
und unabhängige Endkontrolle.03 enthält zusätzlich Rohkurven/Diagnose.04 enthält
`analysis.json` mit ausdrücklich fehlenden Bremsmetriken. Originaler Fehlerstatus
bleibt erhalten; die Recorderkorrektur macht04nicht PASS.05ist der separate
erfolgreiche Nachweis. 29gezielte Offline-Regressionen, py_compile und diffcheck
PASS: nur passender eigener Actionabbruch wird bis zur vollständigen passiven
Messung weiterbeobachtet; neue Schutz-/Frische-/Observerfehler bleiben Fehler.
Effektives Kommandotempo zusätzlich gegen ein höheres optionales Commandfeld
abgesichert. Quellenfixhash separat unter04/source-fix-after-attempt04.json.

Beim Start des scharfen Dienstes führten zunächst fehlende Hardware-/Watchdog-
Nachweise zu nativen Programmstopps aller4. Nach stabilen Daten kontrollierter
Startupreset und vom Nutzer genehmigtes PLAY. Profilwechsel erfolgte geordnet
mit bestätigten Holds/Stillstand. Keine Power-/Brake-/Greiferaktion.

## Vorgesehener Versuch

Der bestehende `tools/hardware_stop_probe.py` wird wiederverwendet, ebenso
Hardwareplaner und Supervisor. Ursprünglich `hardware_commissioning.yaml`,
seit Nutzerkorrektur das oben beschriebene separate Testprofil.
Vollständige Kollisionsprüfung und bestehende Stoppreserve bleiben erhalten.

- Nur das letzte Handgelenkgelenk q6 / wrist_3 von right_front bewegen.
- Maximal +0,03 rad ≈ 1,72°, höchstens 0,003 rad/s ≈ 0,172°/s,
  Beschleunigung höchstens 0,006 rad/s².
- Nach mindestens 80 ms unabhängig bestätigter Bewegung mit mindestens
  0,0012 rad/s und 0,0005 rad Versatz den Supervisor-Stopp anfordern.
- Anschließend Stillstand, Hold und Verriegelung prüfen. Keine automatische
  Rückfahrt, kein Reset und kein Greiferbefehl.
- Unbeladen; andere Arme bleiben stationäre Hindernisse. Power, Brake und Play
  gehören nicht zum Testablauf.

Der komplette geplante Weg hätte 18,75 s Dauer. Der Versuch soll ihn durch den
Stopp während der Bewegung unterbrechen.

## Messung verbessert

Der unabhängige RTDE-Beobachter war bisher auf 20 Hz begrenzt. Er unterstützt
jetzt optional 1–500 Hz; der Standard bleibt für alle bisherigen Nutzer und
laufenden Wächter bei 20 Hz. Für diesen Probe wird `--sample-hz 500` verwendet.
Die Bewegungsbestätigung nutzt ein Zeitfenster und funktioniert bei beiden
Raten. Keine operative Frist, Geschwindigkeitsschwelle oder Bremsannahme wurde
zum Bestehen gelockert. Es entsteht kein zweiter Roboterschreiber.

## Tatsächlich durchgeführte Vorprüfung

Artefakte relativ zum Workspace: `setup/realtime/right-front-stop-20261117-02/`.

Alle vier Arme wurden nativ und ausschließlich lesend geprüft:
RUNNING/NORMAL, gemeldete Geschwindigkeit höchstens 0,0002 rad/s.
Der right_front-Ausgabestrom liefert tatsächlich 500 Hz: Geräteintervall
Median und Maximum jeweils 2,000 ms; größte beobachtete Empfangslücke 2,788 ms
im etwa einsekündigen Datensatz. Die anderen Arme wurden mit 20 Hz gelesen.
Das ist ein Stillstands- und Kadenzenachweis, kein Bremsnachweis.

`plan.json` ist erfolgreich: gemessene Ausgangsgelenke, Werkskinematik,
zentraler Montageabstand von 99,1 cm, volle Greiferöffnungshüllen, FCL und
Paarreserven geprüft. Planungszeit 22,5 ms. Montage- und Weltanker bleiben
vorläufig; Modellprüfung allein belegt keinen freien physischen Arbeitsraum.
`preview.html` zeigt Gelenk- und Zeitkurven, `native-state.json` die Messwerte.

Der erste Aufruf (01) scheiterte vor dem Nativezugriff am relativen
Xacro-Modellpfad. Der korrigierte absolute Pfad wurde in 02 erfolgreich geprüft;
das Fehlerprotokoll bleibt erhalten.

Bei der Prüfung lief `uwa-hardware-motion.service` **monitor-only**. Er wurde
nicht umgestellt. Vor einer Ausführung braucht der bestehende Schutzpfad seine
abgestimmte Scharfschaltung und stationäre Freigabe. Keinen zweiten Schutzdienst
starten. Parallel laufende UR- und Kalibrierarbeiten müssen übergeben werden.

## Spätere Durchführung

1. Nutzerbereitschaft, freie unbeladene Hand-/Greiferzone, Not-Halt-Zugriff und
   exklusive Armübergabe bestätigen. Bestehenden Schutzpfad übernehmen und seine
   Frische, Signatur und Bereitschaft prüfen. Keine pauschale Reset-/Play-Aktion.
2. Bei geänderten Ausgangsposen die lesende Vorbereitung erneuern:

   ```bash
   source src/multi_arm_manipulation_UWA/scripts/control_env.bash
   python3 src/multi_arm_manipulation_UWA/tools/prepare_right_front_stop_test.py \
     --config src/multi_arm_manipulation_UWA/uwa_cell_motion/config/hardware_right_front_stop_test.yaml \
     --output /tmp/right-front-stop-preparation-new
   ```

   Dieses Werkzeug erzeugt nur Beobachtungen und Plan. Der Runner verwirft
   einen um mehr als 2 mrad geänderten Iststart sowie Modell-, Inventar- oder
   Zeitplanänderungen. Es gibt keine automatische Fahrt zur alten Startpose.
3. Vor Aktivierung den vorhandenen passiven Interlockrecorder starten und
   DDS-Discovery abwarten:

   ```bash
   python3 src/multi_arm_manipulation_UWA/tools/trace_hardware_interlock.py \
     --seconds 90 --output /tmp/right-front-stop-interlock-new
   ```

4. **Erst nach einem gesonderten Ausführungsauftrag** den Probe starten.
   Bei erneuerter Vorbereitung den Planpfad entsprechend ersetzen:

   ```bash
   python3 src/multi_arm_manipulation_UWA/tools/hardware_stop_probe.py \
     /tmp/right-front-stop-preparation-new/plan.json \
     --sample-hz 500 --output /tmp/right-front-stop-execution-new.json --execute
   ```

   `--execute` ist Pflicht. Keine automatische Wiederholung oder
   Geschwindigkeitssteigerung. Nach Stopp oder Fehler den gemessenen Endzustand
   und die Primärursache prüfen; Recovery und Rückfahrt bleiben getrennt.

## Auswertung

Die Auswertung arbeitet ausschließlich auf der gespeicherten Datei:

```bash
python3 src/multi_arm_manipulation_UWA/tools/analyze_right_front_stop_test.py \
  /tmp/right-front-stop-execution-new.json --output /tmp/right-front-stop-analysis-new.json
```

Sie trennt:

- Anforderung bis zu einem beobachteten Geschwindigkeitsabfall um 20 %;
- Anforderung bis niedrige Geschwindigkeit an allen sechs Gelenken
  (höchstens 0,0002 rad/s über 20 ms);
- nach Anforderung beobachteten q6-Weg;
- spätere Hold-/Latch-Bestätigung mit stabilem Stillstandsfenster.

Die 20-ms-Beobachtung ist keine operative Stillstandsfreigabe. Der bestehende
Runner verlangt weiterhin sein mindestens 0,45 s langes ruhiges Messfenster.
Geräte- und Empfangsintervalle werden mit ausgegeben. Rückläufige Zeitstempel,
fehlende Vorbewegung und ungültige Daten werden abgewiesen.

Empfangszeiten enthalten Netzwerk- und Pufferlaufzeit; ein 2-ms-Messraster ist
keine 2-ms-Garantie. Ein 20%-Abfall ist eine beobachtbare Schwelle, nicht der
wahre Bremsbeginn. Der Weg nach Anforderung enthält Reaktion und Bremsen.
Die Supervisor-Serviceanforderung misst zunächst den verwendeten
Software-Stopppfad; sie umfasst keine vorgelagerte geometrische Fehlererkennung
und ist nicht mit einem reinen nativen Servostopp gleichzusetzen.
ACK oder Controllerbesitz belegen keinen physischen Stillstand.
Der Versuch qualifiziert weder Not-Halt noch beladene Bremsgrenzen.

## Softwareprüfung

235 Motiontests und der Lyrical-Motionbuild sind erfolgreich. Neue Prüfungen
umfassen den Bewegungstrigger bei 500 Hz, Ratenvalidierung und synthetische
Stoppauswertung. Im ersten Sandboxlauf: 234 PASS, ein lokaler Fake-Servertest
wegen Socketberechtigung FAIL; im anschließenden vollständigen Hostlauf 235 PASS.
Logs: `setup/logs/uwa-right-front-stop-{tests-host,build}.log`.
Diese Mockprüfungen ersetzen keinen realen Stopptest nach der RT-Umstellung.
