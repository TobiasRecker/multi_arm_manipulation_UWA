# Vorbereitung: Echtzeitkernel, schnellere Prüfung und Reaktionsmessung

Stand 2026-11-17. Zunächst nur vorbereitet; im Folgeauftrag ausdrücklich
Kernelinstallation und UR-Treiber-Echtzeitrechte beauftragt und abgeschlossen.
**Nutzerneustart erfolgt; RT-Kernel und Ressourcenrechte aktiv (Nachprüfung siehe unten).** Keine laufenden UR-Treiber neu gestartet,
keine Hardwarewächter-/Bewegungsgrenzen geändert, kein Bremsversuch.

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

## Ursprünglicher Umstellungsplan (Installation/Rechte inzwischen erledigt)

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

## Historische Gazebo-Wächterraten und Realprofil

Die Profile `simulation-guard-{25,50,100}hz.yaml` dokumentieren die damals
untersuchten Frequenzen. Seit dem 19.11.2026 beschreibt der historische
Parameterschlüssel `simulation_guard_rate_hz` nur die angenommene Frequenz
für das Offline-Reaktionswegbudget.

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

Der passive Recorder unterstützt Hardware und Mock. Verwende das
für den jeweiligen Lauf eingerichtete ROS-Umfeld, eine explizite Domain 66
oder 67 und den passenden Namespace. `trace_hardware_interlock.py` ergänzt
Übergänge von Watchdog und Ports. Die Recorder senden keine Bewegungskommandos.

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

## Installation abgeschlossen, Neustart ausstehend (2026-11-17)

Installiert: ubuntu-realtime1.1.3, linux-realtime7.0.0-43.43.1,
linux-image-7.0.0-43-realtime, rt-tests2.9-1ubuntu1. APT ohne Fehler beendet,
dpkg-Audit leer. `CONFIG_PREEMPT_RT=y`; Initrd vorhanden, GRUB-SyntaxprüfungPASS.
Das Paket setzt `GRUB_FLAVOUR_ORDER="realtime"`; bei `GRUB_DEFAULT=0` verweist
der normale Ubuntu-Eintrag auf7.0.0-43-realtime. Generic43 und42 bleiben als
Rückfall erhalten. SecureBoot ist aktiv; sbverify zeigt für RT und laufenden
Generic dieselbe Canonical-Secure-Boot-Signing2022v1-Zertifikatskette. Tatsächlicher
RT-Boot/Secure-Boot-Startnachweis erstnachNeustart möglich.

Installierte Konfiguration (nur Ressourcenrechte, keine FIFO-Policy erzwungen):

- `/etc/security/limits.d/99-uwa-realtime.conf`: rosmatch rtprio99,
  memlock unlimited, soft/hard.
- `/etc/systemd/system/user@1000.service.d/50-uwa-realtime.conf`:
  Benutzer-Manager erbt nach seinem nächsten Start RTPRIO99/MEMLOCK infinity.
- Je `/etc/systemd/user/uwa-ur-driver-{left-front,left-rear,right-front,right-rear}.service.d/50-uwa-realtime.conf`:
  gleiche Rechte für die vier UR-Treiberdienste. Keine pauschale RT-Priorität
  für GUI/Python-Wächter und keine anderen Benutzer geändert.

System-/Benutzer-Daemonkonfiguration neu eingelesen, aber kein Dienstneustart.
Frischer harmloser PAM-Test:rtprio(99,99),memlock(-1,-1)PASS. Alle vier vorhandenen
ros2_control_node-PIDs13780/14185/14464/14787 unverändert mit bisherigen
Prozessgrenzen0/8MiB, wie beabsichtigt. Neue Rechte für diese Treiber erst beim
nächsten Start; Usermanager jetzt nicht neu starten, da andere Arbeit läuft.

Prüfdateien, APT-Logs, Ausgangssicherung und genaues Dateimanifest:
`setup/realtime/installation-20261117/`. `verification.json` enthält Bootziel,
Kernel-/Paket-/Signaturprüfungen; `limits-installed.json` die sechs neu angelegten
Konfigurationsdateien. Keine automatische Rücknahme/Neustartaktion angelegt.

Nach Nutzerfreigabe für den Neustart: zuerst laufende Zellarbeit abstimmen und
geordnet beenden. Danach Kernel (`uname -r`, `/sys/kernel/realtime`), tatsächliche
Prozesslimits und Thread-Scheduling der frisch gestarteten UR-Treiber prüfen;
erst anschließend die dokumentierten Latenztests durchführen. Ein Paket-/Rechte-
Nachweis ist noch keine gemessene Reaktionszeit oder Bremsqualifikation.

## Nach Neustart geprüft (2026-11-17)

Nutzer hat neu gestartet. LaufenderKernel7.0.0-43-realtime,
/sys/kernel/realtime=1 undCONFIG_PREEMPT_RT=y bestätigt. AktuelleSitzung sowie
tatsächlicherBenutzermanagerprozess habenrtprio99/99 undmemlockunlimited.
Alle4UR-Treiberinaktiv, keineControllerthreads: DieUR-Threadprioritätenwerden
erstnachseparatemTreiberstart geprüft. KeineStarts/Robotaktionen ausdieser
Statusprüfung. KeineLatenz-/Bremsqualifikation daraus ableiten. LesenderNachweis:
`setup/realtime/postboot-20261117/verification.json`.

## UR-Treiber anschließend gestartet und geprüft (2026-11-17)

Nach Nutzerstart laufen alle vier UR-Treiber. In jedem ros2_control_node
je zwei echte SCHED_FIFO-Threads mit Priorität50 bestätigt. Tatsächliche
Prozesslimits99/99 undmemlockunlimited. Die99istdieerlaubteObergrenze,
50dieaktuellgenutztePriorität; keinepauschaleHochsetzungnötig.
AllevierReverseverbindungenimStartjournalbelegt. ReinlesendePrüfung;
Latenz-/Bremsmessungenstehenweiteraus. FrühereInaktivitätsmeldungüberholt.
Nachweise: `setup/realtime/postboot-20261117/ur-driver-threads.json` und
`ur-realtime-startup.json`.

## Einzelarmtest vorbereitet

[Reaktions-/Stopptest right_front](right_front_realtime_stop_test.md):
aktuellerModellplan, nachgewiesener500HzOutput-Beobachter undOfflineauswertung.
NochkeineechteAusführung; bisherigerSchutzdienstbeobachtend, Armübergabeund
FreigabevorDurchführungseparat.
