# Vorbereiteter Reaktions- und Stopptest: right_front

Stand: 2026-11-17. Auftrag: Vorbereitung am vorderen rechten UR,
**192.168.8.103**. In dieser Vorbereitung wurde keine reale Bewegung ausgeführt.

## Vorgesehener Versuch

Der bestehende `tools/hardware_stop_probe.py` wird wiederverwendet, ebenso
Hardwareplaner, Supervisor und das unveränderte `hardware_commissioning.yaml`.
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
     --config src/multi_arm_manipulation_UWA/uwa_cell_motion/config/hardware_commissioning.yaml \
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
     setup/realtime/right-front-stop-20261117-02/plan.json \
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
