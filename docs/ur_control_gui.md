# UWA Arme: direkte UR-Treiberbedienung

Stand: 2026-11-10, ROS 2 Lyrical / Ubuntu 26.04.

Startmenü **UWA Arme**, Aktion **Hardware · hinten rechts**, oder:

```bash
bash src/multi_arm_manipulation_UWA/scripts/control.sh --mode hardware --arms right_rear
```

Normaler App-Start bleibt Mock, Standardauswahl nur hinten rechts. Der neue
Fenstertitel lautet **UWA · Direkter UR-Test**. Es werden keine Treiber, Bremsen,
Programme oder Bewegungsziele automatisch gestartet.

## Bedienung

1. **Status prüfen** zeigt Dashboard- und ROS-Status rein informativ.
2. **Treiber starten** verwendet erkannte vorhandene Treiber oder startet eigene.
   Fehlende IPs bleiben unkonfiguriert; keine IP raten.
3. **Broadcaster / Controller laden** holt einen fehlgeschlagenen Spawner-Start
   nach. Fünf Broadcaster werden aktiviert, vier Bewegungscontroller inaktiv
   geladen. Ein schon aktiver Controller wird dabei nicht absichtlich deaktiviert.
4. **Gelenkwinkel lesen** empfängt JointState ohne Dashboard- oder Programmprüfung.
   Der Tab zeigt rad und Grad; ohne Daten eine konkrete Fehlermeldung.
5. **UR bereitstellen** benutzt den vorhandenen UR-SetMode-Helfer zum Einschalten
   und Bremsenlösen. Kein impliziter Programmstart. Der UR entscheidet selbst,
   ob der Befehl in seinem aktuellen Zustand erlaubt ist.
6. **Geladenes UR-Programm starten** startet das am Pendant geladene Programm;
   die UWA-GUI verlangt keinen bestimmten Inventarpfad mehr. Das passende
   External-Control-Programm vorher am Pendant wählen.
7. Im Controller-Tab Admittanz oder Trajektoriencontroller auswählen bzw.
   deaktivieren. Hardware verwendet den nativen skalierten UR-Trajektoriencontroller,
   Mock den normalen. rqt kann ohne vorgeschaltete GUI-Statusfreigabe geöffnet werden.

**Entfernt auf ausdrücklichen Nutzerwunsch:** zusätzliche Armzahlgrenze,
Aktivierungslock, Dashboard-NORMAL/Remote/RUNNING/PLAYING-Vorprüfungen, exakter
Programmpfadvergleich, Forderung inaktiver Controller vor Bereitstellung,
GUI-Besitzpflicht für Bedienung und rqt-Statussperre. Der Inventareintrag
`external_control_program` ist nur noch eine optionale Notiz, kein Gate.
WLAN wird nicht gesperrt. Fehlende ROS-Services, Ressourcen-/Interface-Konflikte
und Ablehnungen vom UR/Treiber werden weiterhin als Fehler angezeigt.

Native UR-Sicherheitsmechanismen, der vorhandene UR-Controller-Stopper,
Reglergrenzen und Kollisionsalgorithmen bleiben unverändert. Die Kollisionsoption
ist in den aktuellen UWA-Profilen weiterhin deaktiviert; es besteht keine
vollständige Vierarm-/Tisch-/Werkzeug-Kollisionsprüfung. Diese Änderung schaltet
keine UR-seitige Funktion ab und quittiert keine Schutzstopps automatisch.

**STOPP** betrifft die Auswahl und alle eigenen Arme. Beim Schließen wird kein
zusätzlicher Dashboard-Stopp mehr gesendet; eigene gestartete ROS-Prozesse werden
beendet. Ein neues Fenster darf bestehende Treiber bedienen, beendet aber fremde
Treiberprozesse nicht. Ein altes Fenster, das laufende Treiber besitzt, daher
geöffnet lassen, bis diese Treiber bewusst beendet werden sollen.

## Aufbau und Hardware

Gemeinsame Treiber-/Controllerlogik bleibt in MATCH: `match_ur_hardware`,
`mur_control/IntegratedCartesianAdmittanceController` (Admittanz/J-PARSE),
`mur_launch_hardware/ur_startup_enable.py` und Qt-unabhängige MuR-GUI-Helfer.
`uwa_cell_control` liefert die schlanke Oberfläche; kein SSH/rsync/MiR/Lift.
Gazebo-Start und bestehende MuR-Defaults wurden nicht verändert.

Inventar: `config/hardware_inventory.yaml`. Je Arm eigener Manager unter
`/uwa_hardware/<arm>/controller_manager`, sechs präfixierte Gelenke und eigene
rohe TF-Topics. Domain 66/localhost, getrennt von Gazebo 64 und OAK 65.

| Arm | IP | Script-sender-Port |
| --- | --- | --- |
| hinten rechts | 192.168.8.170 | 54002 |
| vorne rechts | 192.168.8.103 | 53002 |
| links vorne / hinten | unbekannt | 51002 / 52002 |

External-Control-URCap benötigt die aktuelle PC-IP (zuletzt WLAN192.168.8.209)
und den passenden Script-sender-Port. Pro Arm folgen Reverse/Script/Trajectory/
Command den Portbasen51000/52000/53000/54000 +1/+2/+3/+4. Eigene Werkskinematik
unter `kinematics_file` hinterlegen; null bedeutet nominell und nicht kalibriert.
Keine MuR-UR10-Kalibrierdateien übernehmen.

JointState liest der native Treiber aus RTDE `actual_q`, unabhängig von einem
laufenden External-Control-Programm. Dafür muss der Joint-State-Broadcaster
aktiv sein und die RTDE-Verbindung Daten liefern. Im vorhandenen Hardwarelog
sind fehlgeschlagene Spawner (13:48/13:49), Verbindungsfehler30001/30004 und
spätere RTDE-Reconnects belegt. Der aktuelle lesende8-s-Test empfing keine
Gelenkwinkel; funktionierender Hardwareempfang ist damit noch nicht nachgewiesen.
Die neue Nachladefunktion vermeidet dafür einen kompletten Treiberneustart.

Build aus Workspace wie zuvor mit `--packages-select match_ur_hardware uwa_cell_control`
und Lyrical-Build-/Install-/Log-Verzeichnissen. Desktop-Eintrag nach Umzug erneuern:
`python3 src/multi_arm_manipulation_UWA/scripts/install_control_desktop.py`.

## Nachweise

- Bisherige Ein-/Zweiarm-Sperrtests sind durch diesen Nutzerauftrag überholt.
- 14 aktuelle Offline-Tests bestanden: `setup/logs/uwa-direct-tests.log`.
- Build: `setup/logs/uwa-direct-build.log`.
- Live-Mock-Integration bestanden, einschließlich fehlendem Controller nachladen
  und erneutem Laden ohne Änderung aktiver Broadcaster; separat unter `/uwa_mock_validation`, ohne Eingriff in
  laufende `/uwa_hardware`-Treiber: `setup/logs/uwa-direct-live.log` und
  `setup/logs/uwa-control/mock-gui-validation.json`.
- Lesender Hardwareversuch: `setup/logs/uwa-direct-readonly-joints.json` (keine Daten).
- Keine realen Power-/Brake-/Play-/Bewegungsbefehle durch den Agenten.
