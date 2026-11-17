# Vorbereitung: Echtzeitkernel, schnellere Prüfung und Reaktionsmessung

Stand 2026-11-17. Auftrag ist **Vorbereitung**, keine Kernelinstallation,
kein Neustart, keine Änderung laufender Hardwarewächter und kein Bremsversuch.

## Befund auf ROSmini

Ubuntu26.04.1, laufender Kernel `7.0.0-43-generic`, PREEMPT_DYNAMIC,
`CONFIG_PREEMPT_RT` nicht gesetzt. Aktuelle Sitzung: rtprio0, memlock8MiB.
`rt-tests`/`cyclictest` fehlen. Lokale APT-Auflösung für
`ubuntu-realtime rt-tests` erfolgreich; RT-Kernel7.0.0-43 verfügbar.
Ubuntu26.04 liefert ihn im Hauptarchiv, ohne eigenen Kernelbau oder Pro-Zugang:
[offizielle Installation](https://ubuntu.com/real-time/docs/how-to/enable-real-time-ubuntu/).

Alle Artefakte relativ zum Workspace: `setup/realtime/preparation-20261117/`.
`host-audit.json` enthält Paketauflösung und Sitzungsgrenzen. Der20s-Python-
Wecktest im normalen Scheduler hatte bei2msPeriode p99≈437µs, max≈2836µs,
5 übersprungene Termine. Das ist **kein cyclictest**, keine garantierte Grenze
und kein gemessener UR-Reaktionswert.

## Konkreter Umstellungsplan (noch nicht ausgeführt)

1. Gemeinsame Workstation freigeben, Roboterbetrieb vorher geordnet beenden;
   Boot-/Treiberkompatibilität (DKMS, Secure Boot) prüfen. Aktuellen generischen
   Kernel als Rückfall erhalten. Keine GRUB-/IRQ-/CPU-Isolationsänderung bündeln.
2. Offizieller Paketweg für Ubuntu26.04:

   ```bash
   sudo apt update
   sudo apt install ubuntu-realtime rt-tests
   ```

3. Vorbereitete benutzerspezifische Limits prüfen und installieren:

   ```bash
   sudo install -m 0644 setup/realtime/preparation-20261117/99-uwa-realtime.conf.pending /etc/security/limits.d/99-uwa-realtime.conf
   ```

   Betrifft ros­match: rtprio99, memlock unlimited. Neu anmelden;
   systemd-Benutzerdienste zusätzlich anhand ihres tatsächlichen
   `LimitRTPRIO`/`LimitMEMLOCK` prüfen. Keine Dienste automatisch neu starten.
   Die lokale URCL-Pipeline fordert für ihren Producer die maximaleFIFO-Priorität.
   Niemals komplette Python-/GUI-Prozesse pauschal auf FIFO99 anheben.
   [UR-Echtzeitkonfiguration](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_client_library/doc/real_time.html).
4. In abgestimmtem Zeitfenster neu starten, RT-Kernel auswählen. Danach
   `uname -r`, `/sys/kernel/realtime`, Kernelconfig und Sitzungs-/Dienstlimits
   erneut erfassen. Bei Boot-/Treiberproblemen im GRUB den erhaltenen
   generischen Kernel auswählen. Rücknahme der neuen Limits durch Entfernen
   ausschließlich der neu angelegten `99-uwa-realtime.conf` und Neuanmeldung.
5. Vorher/nachher denselben begrenzten cyclictest im gleichen Lastzustand
   durchführen, erst danach längere Lastmessungen. Beispiel für einen kurzen
   Einzelthreadtest nach Installation:

   ```bash
   sudo cyclictest --mlockall --threads=1 --priority=80 --interval=2000 --duration=1m --quiet
   ```

   Kurztests und längere Maxima getrennt bewerten. Keine künstliche Last parallel
   zu laufender realer Manipulation. CPU-/IRQ-Zuordnung erst anhand dieser Daten
   gezielt festlegen; vorhandenes Simulations-CPU-Profil reserviert keine CPUs.
   [Canonical-Messanleitung](https://ubuntu.com/real-time/docs/how-to/measure-maximum-latency/).

## Schnellere Wächterprüfung vorbereitet

Kontakt-Simulation: neuer expliziter Taskparameter
`simulation_guard_rate_hz` (10–100Hz; abweichend von10 nur Exploration).
Er steuert **denselben** Wert im Timer und im Reaktionswegbudget des Planers.
Standard10Hz erhalten. Guardstatus enthält Evaluationszeit, Intervall,
vorherige vollständige Callbackzeit, Periodenbudget und Überlaufzähler.

Profile `simulation-guard-{25,50,100}hz.yaml` liegen in den Artefakten;
alle mit weiterhin erzwungener Stoppreserve, unveränderten Frische-/Bremswerten.
Neue Szenen vorbereiten, keine vorhandenen SHA-gebundenen Szenen überschreiben.
Zuerst25Hz, dann50Hz bei genügend gemessener Laufzeitreserve testen.
100Hz bleibt Kandidat, keine automatische Aktivierung.

300 gespeicherte belastete Modellzustände: Sphere-/FCL-Geometrie median3,552ms,
p994,495ms, max4,813ms. **Offline-Geometrie allein**, ohne ROS, Kontakte,
Marker und Betriebssystempausen; keine Laufzeitqualifikation. Ausgangsdaten und
Reproduktionsskript: `geometry-benchmark.{json,log}`, `benchmark_geometry.py`.

Der reale HardwareGuard hat bereits `rate_hz` als Timerparameter und eigene
Zeitdiagnose. Keine zweite Implementierung und keine Änderung seines aktiven
Profils erforderlich. Schnellere reale Raten zuerst monitor-only mit explizitem
Profil prüfen, dann bei abgestimmter Übergabe in unbeladenen Versuchen.

| Profil | Prüfperiode | Zustandsalter im Plan | Stopplatenz | Bremsannahme |
|---|---:|---:|---:|---:|
| letzter Kontakt-Simulationsversuch |100ms|150ms|100ms|2rad/s²|
| reales hardware_commissioning.yaml |100ms|200ms|1000ms|0,2rad/s²|

Die früher genannten350ms gelten also für die Simulation. Im realen langsamen
Inbetriebnahmeprofil sind1300ms angesetzt. Beides sind konservativeAnnahmen,
keine nachgewiesenen UR-Grenzen. Nur10→25Hz spart60ms Periodenanteil;
10→50Hz spart80ms. Frische und Stopplatenz werden nicht automatisch kleiner.

## Messwerkzeuge und vollständige Reaktionskette

`tools/prepare_realtime.py` hat vier getrennte, nicht schreibende Betriebsarten:
Hostaudit, Python-Jitterprobe, passiverROS-Recorder, Offline-Kettenauswertung.
Ausgabepfade müssen neu sein; bisherige Evidenz wird nicht überschrieben.

```bash
python3 src/multi_arm_manipulation_UWA/tools/prepare_realtime.py audit --output /tmp/rt-audit-new.json
python3 src/multi_arm_manipulation_UWA/tools/prepare_realtime.py jitter --seconds 30 --output /tmp/rt-jitter-new.json
```

Recorder erst vor dem Scharfschalten starten, Discovery setzen lassen. Er
abonniert nur JointStates, Guard und Supervisor; keine Services, Actions oder
Kommandopublisher. Domain muss explizit zur geladenen Umgebung passen:

```bash
# Standard-Simulationsumgebung zuvor laden; keine Domain für Hardware ändern.
python3 src/multi_arm_manipulation_UWA/tools/prepare_realtime.py record --domain 64 --namespace /uwa_grasp_validation --seconds 60 --output /tmp/sim-reaction-new.jsonl
```

Für spätere rein passive Hardwaremessung vorhandene Hardwareumgebung/Domain66,
Namespace `/uwa_cell` verwenden. `trace_hardware_interlock.py` aus der parallelen
Hardwarearbeit zusätzlich wiederverwenden: erhält Watchdog-/Portübergänge und
nativeStopanforderungen. Sein1HzSnapshot ist kein hochfrequenter Gelenktrace;
der neueRecorder ergänzt vollständige empfangeneGelenksamples.

Zu korrelierende Messpunkte (gemeinsame Trial-ID):

| Stufe | Quelle / noch benötigte Instrumentierung |
|---|---|
| state_received | Zeit am tatsächlichen Wächtereingang; Recorderempfang ist nur Zusatzbeobachtung |
| guard_started / guard_finished | Callback-Instrumentierung; Evaluationszeit/Intervalle bereits verfügbar |
| stop_dispatched | Zeit an tatsächlich verwendeter Kommandoschnittstelle; Request/ACK/Controllerbesitz getrennt |
| deceleration_observed | Gelenkgeschwindigkeit aus hochfrequentem Trace, Schwelle/Rauschen und Beobachtungsauflösung dokumentieren |
| standstill_observed | erster Geschwindigkeitsabfall und bestätigtes Stillstandsfenster getrennt berichten |

NativeStopereignisse aus der anderen Arbeit zeigen derzeit Anforderungszeit
und ACK, noch keinen vollständigen Dispatch-/Bremsverlauf. Diese fehlenden
Messpunkte vor dem späteren Versuch ergänzen; **passive Topicmessung allein
beweist keine vollständige Reaktionszeit**. Robotereigene Zeitstempel zunächst
gegen den Host abgleichen, nie blind ROS-/Gazebozeit, Controllerzeit und
CLOCK_MONOTONIC subtrahieren. Beobachteter Fall ist keine Worst-Case-Garantie.

Die Offlineauswertung erwartet JSONL proStufe mit
`trial_id`, `boot_id`, `clock: "host_monotonic"`, `stage`, `time_s`.
Sie lehnt fehlende/doppelte Stufen, gemischte Boot-IDs/Uhren und Zeitrückläufe ab:

```bash
python3 src/multi_arm_manipulation_UWA/tools/prepare_realtime.py analyze --input /tmp/stop-events.jsonl --output /tmp/stop-analysis-new.json
```

Bremswinkel zusätzlich aus q am Dispatch und am Stillstand sowie dem gesamten
qd-Verlauf auswerten, nicht aus ACK-Latenz ableiten. Erst unbeladen jeArm und
danach synchronerVerbund; beladeneVersuche erstnach dem dafür nötigen
Geometrie-/Kontakt-/Kommandopfadnachweis. UnterschiedlicheGeschwindigkeiten,
Posen, Lasten und gestörteZustellung getrennt messen. NeueBudgets anhand
beobachteterMaxima plus begründeterReserve festlegen; nicht allein aus p99.

## Prüfnachweise dieser Vorbereitung

121 TasktestsPASS, LyricalTaskbuildPASS. ErsteTestcollection fand ein neues
Modul aus parallelerArbeit noch nicht in derInstallation; nachBuild alleTestsPASS.
Ratevalidierung und gleiche Planungsrate geprüft. Recorder in isolierter
Mock-Domain67 mit synthetischen25Hz-Daten geprüft:198Guardpakete,
keineRobot-/Service-/Actionkommandos; synthetische3ms sind keinHardwaremesswert.
Kettenauswertung an synthetischen Zeiten inklusive Fehlerfällen geprüft.
KeineKernel-/System-/Dienständerung, keineechteBewegung oder Hardwaremessung.
Logs: `setup/logs/uwa-realtime-prep-*`, Artefakte wie oben.
