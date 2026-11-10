# UWA Arme: lokale UR-Vorbereitung

Stand: 2026-11-10. ROS 2 Lyrical / Ubuntu 26.04.

Im Startmenü **UWA Arme** öffnen oder im Workspace:

```bash
bash src/multi_arm_manipulation_UWA/scripts/control.sh
```

Die App startet im **Mock-Modus**, zunächst ohne Treiber. Oben links die vier
Arme auswählen, dann **Treiber starten**. Der Controller-Tab zeigt die geladenen
Controller. Dort lassen sich Admittanz oder Trajektoriencontroller für Mock
aktivieren; die rqt-Gelenksteuerung bietet manuelle Mock-Ziele. Admittanz-Test
bedeutet hier Aktivierung/Deaktivierung des Plugins, keinen nachgewiesenen
Kraftregelungs- oder Kollisionsversuch. **STOPP** deaktiviert Bewegungscontroller
aller von diesem Fenster gestarteten Arme, unabhängig von der aktuellen Auswahl.
Treiber beenden und Fenster schließen räumen die eigenen Prozessgruppen auf.

Die GUI enthält keine SSH-/rsync-/MiR-/Lift-/Batterie- oder entfernte
Hostverwaltung. Sie erbt nicht von der umfangreichen MuR-GUI.

## Aufteilung der Software

| Aufgabe | Implementierung |
| --- | --- |
| Gemeinsamer UR-only-Start, Profile, Operationen | `match_mobile_robotics_jazzy/ur_robot/match_ur_hardware` |
| Admittanz, J-PARSE, vorhandene Kollisionsalgorithmen | `mur_control/IntegratedCartesianAdmittanceController` im MATCH-Repo |
| Einschalten/Bremsen und expliziter Programmstart | vorhandenes `mur_launch_hardware/ur_startup_enable.py` |
| Dashboard-Leseabfrage und Prozess-Fallback | vorhandene Qt-unabhängige Helfer aus `match_mur_gui` |
| Vierarmauswahl, Bedienung, UWA-Launch | `uwa_cell_control` in diesem Repo |
| IPs, Modelle, Ports, Werkskalibrierung, Programmzuordnung | `config/hardware_inventory.yaml` |

Die bestehenden MuR-Launches und Controlleralgorithmen wurden nicht verändert.
Insbesondere wird `mur_620.launch.py` mit seiner automatischen UR-Bereitstellung
nicht als UWA-Start verwendet. Der neue Adapter benutzt UR-Treiberkomponenten
und lädt pro Arm fünf Broadcaster aktiv und vier Bewegungscontroller **inaktiv**.
Pro Arm existiert ein Manager `/uwa_hardware/<arm>/controller_manager` mit sechs
eindeutig präfixierten Gelenken. Die rohen, noch nicht registrierten TF-Bäume
bleiben je Arm auf eigenen `tf`-/`tf_static`-Topics.

**Domain 66 / lokale Discovery** für Mock und Hardware; keine Umschaltung der
Gazebo-Zelle (Domain 64) oder OAK-Tests (Domain 65). Mock und Hardware dürfen
nicht gleichzeitig mit denselben Arm-Namespaces laufen. Launch-Sperren verhindern
doppelte Adapter-Instanzen pro Arm/Domain. Gazebo wird durch diese App nicht gestartet.

## Hardware-Vorbereitung: getrennte, explizite Schritte

Zunächst eigene Mock-Treiber beenden, dann oben rechts **Hardware** wählen.
Links sind ohne bekannte IP deaktiviert. Aktuelle Zuordnung:

| Arm | Modell | IP | Reverse | Script sender | Trajectory | Script command |
| --- | --- | --- | --- | --- | --- | --- |
| links vorne | UR5 | unbekannt | 51001 | 51002 | 51003 | 51004 |
| links hinten | UR7e | unbekannt | 52001 | 52002 | 52003 | 52004 |
| rechts vorne | UR5e | 192.168.8.103 | 53001 | 53002 | 53003 | 53004 |
| rechts hinten | UR5e | 192.168.8.170 | 54001 | 54002 | 54003 | 54004 |

1. **Status prüfen** liest Dashboard und ROS-Controllerstatus. Keine
   Sicherheitszustände werden quittiert oder automatisch zurückgesetzt.
2. **Treiber starten** startet lokale Treiber, Dashboard und Statushelfer.
   Kein automatisches Einschalten, Bremsenlösen oder Abspielen eines Programms.
3. **UR bereitstellen** ist ein ausdrücklicher Hardwarebefehl zum Einschalten
   und Bremsenlösen. Er verlangt Remote-Modus, NORMAL-Sicherheitsstatus und
   inaktive Bewegungscontroller. Er startet kein Programm.
4. **External Control starten** verlangt zusätzlich den exakten geladenen
   Programmpfad in `external_control_program`. Dieser Wert ist zunächst leer;
   dadurch wird ein unbeabsichtigtes Starten eines beliebigen Programms abgelehnt.

Am Pendant muss zuvor ein geeignetes External-Control-Programm eingerichtet
und geladen sein. Die URCap benötigt die aktuelle PC-IP (zuletzt per WLAN
192.168.8.209) und den **eigenen Script-sender-Port** aus der Tabelle, beispielsweise
54002 für hinten rechts. Nicht allen Armen denselben Standardport 50002 geben.
Remote-Modus und Sicherheitsfreigaben werden am Pendant hergestellt. Kein
Headless-Injizieren oder automatisches Entsperren durch die UWA-GUI.

Für jeden realen Arm die eigene Werkskinematik auslesen und den Pfad unter
`kinematics_file` hinterlegen. `null` verwendet nominelle UR-Kinematik und ist
keine vermessene Kalibrierung; niemals eine MuR-UR10-Datei für UWA übernehmen.
Die Tisch-/Basisregistrierung und gemeinsame kalibrierte Hardware-TFs folgen
getrennt. Der bestehende automatische Hand-Auge-Backend bleibt Simulation-only.

**Noch nicht umgesetzt:** Die vorhandene Admittanz-Kollision berücksichtigt
einen Gegenarm und feste Sperrboxen, keine vollständige UWA-Szene mit vier
Armen, beiden Tischen, Greifern und Kameras. Deshalb verweigert dieser Adapter
zunächst sämtliche Hardware-Bewegungsaktivierung, einschließlich Trajektorien.
Die Plugins sind vorbereitet, aber diese Integration ist vor realer Nutzung
noch zu erstellen und zu validieren. Mock-Erfolg bestätigt Softwareabläufe,
keine reale Kollisions- oder Kraftregelungssicherheit.

Der rote Knopf ist ein **Softwarestopp**, kein Hardware-Not-Halt. Er bricht
eigene laufende Vorbereitung ab, deaktiviert Controller und fordert im
Hardwaremodus Dashboard-Programm-Stopp an; Fehler erscheinen im Protokoll.
Die Mehrarm-CLI arbeitet Arme derzeit nacheinander ab. Netzwerk-/Service-
Timeouts können den Stopp verzögern; keine garantierte Vierarm-Stoppzeit.
Beim Schließen werden eigene Programme vor dem Treiberabbau ebenfalls gestoppt,
aber nicht automatisch ausgeschaltet. Fremd gestartete Treiber werden von
diesem Fenster nur angezeigt, nicht als eigene übernommen.

Der PC verwendet vorübergehend WLAN. Die frühere Erreichbarkeitsmessung ist
keine Echtzeitqualifikation; zuletzt war beim separaten Wrist-Kameratest der
Controller nicht erreichbar. Echte Treiber, Power/Brake/Play und Bewegungen
wurden im Rahmen dieser GUI-Implementierung **nicht ausgeführt**.

## Build und direkter Launch

```bash
source setup/lyrical_env.bash
colcon --log-base log_lyrical build --build-base build_lyrical \
  --install-base install_lyrical --symlink-install \
  --packages-select match_ur_hardware uwa_cell_control
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 launch uwa_cell_control arms.launch.py arms:=right_front,right_rear mode:=mock
```

Der direkte Launch startet keine GUI und stellt keinen UR automatisch bereit.
`mode:=hardware` ist eine explizite Auswahl; nicht parallel zum Mock derselben
Arme verwenden. Desktop-Eintrag nach Umzug des Workspace erneuern:

```bash
python3 src/multi_arm_manipulation_UWA/scripts/install_control_desktop.py
```

## Prüfnachweise, 2026-11-10

- Zwei Pakete unter Lyrical gebaut: `setup/logs/uwa-control-build.log`.
- Zehn Offline-Tests: Profil-/Portvalidierung, Controllerparameter ohne
  ROS-inkompatible YAML-Aliase, getrennte Prepare/Play-Gates, Sperre echter
  Bewegungsaktivierung vor ROS-Start und GUI-Auswahl/Bedienzustände.
- GUI-/ROS-Integration mit vier echten Mock-Komponenten: 24 eindeutige endliche
  Gelenkzustände; alle Bewegungscontroller zunächst inaktiv, vier bestehende
  Admittanz-Plugins aktiviert, nach GUI-Stopp alle wieder inaktiv, eigene
  Treiberprozesse sauber beendet. `setup/logs/uwa-control/mock-gui-validation.json`.
- Sichtprüfung: `setup/logs/uwa-control/mock-controller-gui.png`.
- Installierten Desktop-Eintrag mit `desktop-file-validate` geprüft und mit
  `gtk-launch uwa-control` gestartet; X11-Fenster registriert. Starter bereinigt
  inkompatible GTK-Pfade aus dem VS-Code-Snap für die Host-Qt-Installation.
- Keine realen Arme eingeschaltet, Bremsen gelöst oder bewegt.

Laufende GUI-Meldungen liegen unter `setup/logs/uwa-control/gui.log`, ROS-Logs
unter `setup/logs/uwa-control/ros/`. Die Logs enthalten auch die behobenen
ersten Mock-Startversuche; der JSON-Bericht beschreibt den abschließenden Test.
