# Vier URs für ROS vorbereiten

Vom UWA-Workspace (`~/UWA_ws`) aus:

```bash
python3 src/multi_arm_manipulation_UWA/scripts/ur_bringup.py --status
python3 src/multi_arm_manipulation_UWA/scripts/ur_bringup.py --apply
```

Ohne Argumente liest das Skript nur. `--apply` ist der ausdrückliche
Bedienbefehl für die **echte Zelle**: Der Arbeitsbereich muss für Einschalten,
Bremsenlösen und Programmstart frei sein. Der Befehl wird nicht beim
Login oder automatisch durch einen Treiberstart ausgeführt. Am PC sind
Python mit PyYAML und `ss` (iproute2) nötig. Die Statusabfrage benötigt
keinen ROS-Launch und keine ROS-Umgebungsvariablen.

Für Agenten und Skripte:

```bash
python3 src/multi_arm_manipulation_UWA/scripts/ur_bringup.py --status --json
python3 src/multi_arm_manipulation_UWA/scripts/ur_bringup.py --apply --arm left_front --arm right_rear --json
```

Ohne `--arm` werden alle vier Arme aus `config/hardware_inventory.yaml`
verwendet. JSON meldet je Arm `code`, `message`, ggf. `manual_action`,
den letzten gelesenen Zustand, einen etwaigen Treiberstartversuch und die gesendeten Dashboard-Befehle mit Antworten.
Exit-Code **0** heißt: alle ausgewählten Arme bereit. **1**: mindestens
einer nicht bereit, Gründe pro Arm. **2**: Aufruf oder Konfiguration
fehlerhaft. **130**: abgebrochen; danach den tatsächlichen Zustand neu lesen.
Ein Agent meldet die Bedienerschritte aus `manual_action` und prüft danach
mit einem neuen Aufruf. Der Status ist eine Momentaufnahme.

## Ablauf

1. Per Dashboard Seriennummer, PolyScope, Robotermodus, Sicherheitszustand
   und Programm abgleichen. Bei den drei e-Series zusätzlich Remote Control
   prüfen; links vorne ist CB3 und hat diesen Umschalter nicht.
2. Fehlende lokale ROS-Treiber für vorbereitbare Arme über den bestehenden
   Hardware-Launch starten. Vorhandene Treiber werden weiterverwendet. Neu
   gestartete Treiber laufen nach Ende des Skripts als temporäre systemd-
   Benutzerdienste `uwa-ur-driver-<arm-mit-bindestrichen>.service` weiter.
   Schlägt der lokale Start fehl, wird der betroffene Arm nicht eingeschaltet.
3. Falls nötig, das fest eingetragene **`/programs/ros.urp`** laden. Dieses
   Programm muss in der Zelle das vorgesehene External-Control-Programm
   bleiben. Der Dashboard Server kann den Dateiinhalt nicht prüfen.
4. Die Antriebe einschalten, auf `IDLE` warten und die Bremsen lösen, falls
   nötig. Jeweils am UR nachlesen. Ein bereits laufendes oder pausiertes
   anderes Programm wird nicht gestoppt oder überschrieben; das gilt auch
   für ungespeicherte Änderungen an einem gestoppten Programm.
5. Ein gestopptes `ros.urp` starten, sobald der lokale UR-Treiber auf dem
   zugeordneten Script-Sender-Port lauscht. `ready` erfordert gleichzeitig
   `RUNNING`, `PLAYING` für die Inventardatei und eine aktive TCP-Verbindung
   von der IP dieses Arms zum Reverse-Port seines lokalen ROS-Treibers.
   Ein bereits verbundener Arm wird nicht neu gestartet. Ein laufendes
   `ros.urp` ohne Reverse-Verbindung wird gemeldet, ohne es zu stoppen
   oder neu zu starten.

Der Ablauf kann Arme versetzt vorbereiten. Ein blockierter Arm wird gemeldet;
der nächste Arm wird separat geprüft. Es gibt keinen automatischen Rollback
und keine Wiederholung eines Befehls bei unklarem Ergebnis. Der Prozess
schaltet keine Bewegungscontroller um und sendet keine Fahrziele.
`ready` bestätigt Programm und Verbindung; eine
Bewegungsfreigabe erfolgt weiter im zuständigen Ablauf.

## Wenn jemand vor Ort eingreifen muss

| Meldung | Handlung |
| --- | --- |
| `local_control` | Am Teach Pendant auf **Remote Control** umschalten. Falls die Option fehlt: **Settings → System → Remote Control** prüfen. |
| `unreachable` | Steuerung physisch einschalten bzw. Ethernet und Dashboard Server prüfen. Ein ausgeschalteter Controller ist über TCP nicht aufweckbar. |
| `safety_blocked`, `confirm_safety` | Ursache, Sicherheitsanzeige und ggf. Installation vor Ort prüfen. Stopps und Sicherheitsabfragen quittiert das Skript nie. |
| `program_in_use`, `unsaved_program` | Vorhandenes Programm und Änderungen am Pendant prüfen und bewusst speichern, beenden oder verwerfen. |
| `load_rejected`, `play_not_confirmed` | Am Pendant `ros.urp`, die zugehörige Installation und den External-Control-Knoten prüfen. |
| `ros_driver_missing`, `ros_driver_start_failed`, `ros_not_connected` | In **UWA Arms → Hardware → Start drivers** die fehlenden Treiber starten bzw. Logs und External-Control-Host/Script-Port prüfen. |

Herstellerreferenz: [Dashboard für CB3](https://www.universal-robots.com/articles/ur/dashboard-server-cb-series-port-29999/)
und [Dashboard für e-Series](https://www.universal-robots.com/manuals/EN/HTML/SW5_25/Content/prod-dashboard/Dashboard_table.htm).
