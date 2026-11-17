# Gemeinsame ROS-Greifersteuerung für Agenten

Stand17.11.2026: `uwa_cell_gripper_control` stellt alle vier realen Robotiq-Greifer
über ROS2Lyrical bereit. Öffnen, Schließen und relative Öffnung sind **Actions**:
Sie dauern eine Weile und liefern Feedback sowie ein bestätigtes Ergebnis.
Status und Fähigkeiten sind **Services**. Ein Python-Client und eine CLI nutzen
dieselben ROS-Endpunkte; Agenten sollen nicht eigene Socket-Schreiber starten.

Die neue API wurde mit einem eigenen Loopback-Emulator in Domain67 geprüft.
Der reale Dienst läuft zunächst **MONITOR ONLY** und sendet nur GET-Anfragen.
Die Bereitstellung dieses Diensts hat keine Greifer oder Arme bewegt.

## Einheiten und derzeitige Grenzen

Der Nutzer hat am17.11.2026 ausdrücklich bestätigt, dass Rohkraft und relative
Öffnung für diese erste Version ausreichen. N/mm sind eine mögliche spätere
Erweiterung und keine Voraussetzung für die Verwendung dieser Schnittstelle.

- `force_raw`: expliziter Robotiq-Rohwert0–255. **Keine Newtonangabe**;
  auch0bedeutet nicht0N physische Greifkraft. Einstellung wird zurückgelesen.
- `speed_raw`: Rohwert0–255, keine kalibrierte Geschwindigkeit inmm/s.
- `opening_percent`: **Sollwert für den nominellen Registerhub**,100=offen,
 0=geschlossen. Umrechnung `position_raw=round((100-opening_percent)*255/100)`.
  Das ist keine gemessene geometrische Öffnungsweite. Millimeter-/Newton-
  Kennlinien sind noch nicht vorhanden und werden nicht erfunden.
- Am realen offenen Anschlag wurde POS3beiSoll0beobachtet. Die Hardware-
  Kollisionshülle deckt weiterhin den gesamten Öffnungsbereich ab; diese API
  ersetzt sie nicht automatisch durch eine kleinere Hülle.

Schließen endet regulär auch bei gemeldetem Objektkontakt. `contact_detected`
stammt aus dem nativen OBJ-Register; es beweist weder vier Auflagekontakte noch
einen tragfähigen Griff oder eine gemessene Klemmkraft. N/mm erfordern einen
gesonderten mechanischen Messabgleich. Der reale Kartonhub bleibt unqualifiziert.

## Start und Dienstbesitz

Aus `~/UWA_ws`:

```bash
bash src/multi_arm_manipulation_UWA/scripts/grippers.sh monitor
bash src/multi_arm_manipulation_UWA/scripts/grippers.sh status
bash src/multi_arm_manipulation_UWA/scripts/grippers.sh logs
```

Eigener Benutzerdienst `uwa-grippers.service`, Hardware-Domain66/LOCALHOST.
Dieser startet keine UR-Treiber, Programme oder Armantriebe. Starten, Öffnen
eines Clients und Beenden aktivieren oder öffnen keinen Greifer automatisch.
Der Wrapper erzeugt einen Sitzungsdienst; nach einem Rechnerneustart erneut
starten. Es wurde kein automatischer Hardwarestart beim Booten eingerichtet.

Für einen konkret freigegebenen Greiferauftrag die Befehlsannahme einschalten:

```bash
# Kein Fingerbefehl allein durch diesen Dienststart.
# Bestehende minimale Kraftgrenze bleibt0; höhere Rohkraft bewusst konfigurieren.
bash src/multi_arm_manipulation_UWA/scripts/grippers.sh enable \
  max_force_raw:=0 max_speed_raw:=32
```

Ein Auftrag mit beispielsweise `force_raw:20` benötigt eine ausdrücklich passend
gesetzte Obergrenze (`max_force_raw:=20` oder höher). Das ist kein20-N-Profil.
Der Dienst ersetzt nur seine eigene alte Instanz; fremde Adapter werden nicht
beendet. Neue und alte Adapter teilen die Gerätesperre
`/tmp/uwa-gripper-<uid>-<domain>-<arm>.lock`. Das schützt ROS-Adapter unter
derselben UID, nicht gegen beliebige externe Socket-Schreiber.

Alle vier Arme heißen `left_front`, `left_rear`, `right_front`, `right_rear`.
IP-Zuordnung kommt aus `config/hardware_inventory.yaml`. Für Mock gilt Domain67
und ausschließlich Loopback. Einen einzelnen Mock-Knoten starten:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
export ROS_DOMAIN_ID=67
ros2 run uwa_cell_gripper_control cell_gripper_node --mode mock \
  --arm left_front --mock-port 63352 --actuate --max-force-raw 32
```

## CLI: Status, öffnen, schließen, Öffnung setzen

Einmal die Hardwareumgebung laden:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear capabilities
ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear status
```

Folgende Aufrufe sind **echte Fingerbefehle**, sobald der Dienst Befehle annimmt.
Nur im passenden Nutzerauftrag verwenden; Öffnen kann ein gehaltenes Objekt
freigeben. Der gesamte Fingerweg muss frei sein. Alle Aufrufe sind einzeln;
kein impliziter Reset oder Aktivieren vor MOVE:

```bash
# Nur nötig, wenn der Greifer noch nicht aktiviert ist; kann Finger bewegen.
ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear activate

ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear open
ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear close --force-raw 0
ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear set-opening 50 \
  --force-raw 0 --speed-raw 16 --timeout 15
```

`close` verlangt eine ausdrücklich angegebene Kraft. Jeder Befehl kann
`--speed-raw`, `--force-raw` und `--timeout` nutzen. Rohwerte bleiben innerhalb
der beim Server gesetzten Grenzen; ein höheres Argument ändert diese nicht.
CLI-Exitcode0=bestätigtes Ergebnis,1=Fehler/unbestätigt; nicht blind wiederholen.

## Python-Funktionen

```python
from uwa_cell_gripper_control.client import GripperClient

with GripperClient("right_rear", mode="hardware") as gripper:
    print(gripper.capabilities())
    print(gripper.status())
    # Nur einzeln im freigegebenen Fingerauftrag aufrufen:
    result = gripper.open(speed_raw=16)
    result = gripper.set_opening(50, force_raw=0, speed_raw=16)
    result = gripper.close_gripper(force_raw=0, speed_raw=16)
```

`activate()` ist ein separater Aufruf. Alle Bewegungsfunktionen akzeptieren
`timeout_s` und optional `feedback=lambda status: ...`. Der Kontext beendet
nur den ROS-Client; `close()` am Client schließt die Verbindung, während
**`close_gripper()` die Finger kommandiert**. Es gibt keine automatische
Freigabe oder Rückfahrt beim Verlassen des Kontexts.

## ROS-Endpunkte und Nachrichten

Je Arm, beispielsweise `/uwa_hardware/right_rear/gripper`:

| Suffix | Typ | Bedeutung |
| --- | --- | --- |
| `/operate` | `uwa_cell_gripper_interfaces/action/GripperCommand` | Komfortbefehle |
| `/command` | `uwa_cell_gripper_interfaces/action/RobotiqCommand` | Kompatible rohe Registersteuerung |
| `/read` | `std_srvs/srv/Trigger` | Frischen Status lesen, JSON inmessage |
| `/capabilities` | `std_srvs/srv/Trigger` | Einheiten, Grenzen und Betriebsmodus, ohne Gerätezugriff |
| `/status` | `std_msgs/msg/String` | JSON bei Statusabfrage/Feedback, sonst1Hz; observed=falsebeiLesefehler |

Mock-Präfix: `/uwa_gripper_mock/<arm>/gripper`. `/operate`-Operationen:
OPEN=1, CLOSE=2, SET_OPENING=3, ACTIVATE=4. Beispiel für50%Registerhub:

```bash
ros2 action send_goal /uwa_hardware/right_rear/gripper/operate \
  uwa_cell_gripper_interfaces/action/GripperCommand \
  '{operation: 3, opening_percent: 50.0, speed_raw: 16, force_raw: 0, timeout_s: 15.0}' \
  --feedback
```

Das Ergebnis enthält `success`, `message`, `position_raw`, `contact_detected`
und `status_json`. Status zeigt unter anderem Register, `busy`, Einheiten,
Grenzen und `actuation_enabled`. Registerstatus ist sequenziell gelesen,
kein atomarer Messsnapshot und kein Nachweis physischer Greifkraft.

## Verhalten bei konkurrierenden Befehlen und Fehlern

- Höchstens ein akzeptierter Schreibauftrag je Arm, gemeinsam über beide
  Actions. Ein gleichzeitiger Auftrag wird abgewiesen, nicht vorgemerkt.
- FOR/SPE werden einzeln gesetzt und beide bestätigt, **bevor POS geändert
  wird**. Ein gelatchtes GTO kann schon auf eine neue POS reagieren.
- MOVE bei inaktivem/fehlerhaftem Greifer wird abgelehnt. ACTIVATE ist explizit.
- Verbindungsfehler, Fristüberschreitung und Gerätefehler liefern keinen
  erfundenen Erfolg. Ein beim Client abgelaufenes Ergebnis kann weiterhin am
  Gerät in Arbeit sein: Status prüfen, nicht automatisch erneut senden.
- Cancel wird derzeit abgewiesen. Es gibt noch keinen qualifizierten
  generischen Fingerstopp; Cancel bedeutet insbesondere nicht Öffnen.
- Armstopp, Nodeexit und Dienstende senden kein Öffnen/Reset/Force0. Das letzte
  Greifziel bleibt erhalten. Ein Software-Armhalt ist kein Hardware-Fingerhalt.

## Validierung und Stand

Zwei isolierte Pakete gebaut: Interfaces und Gripper-Control. Keine Task-/
Motionbibliotheken oder laufenden Simulationswelten dafür neu gebaut/gestartet.
13reineAPI-Prüfungen und echteROS-Mockintegration67mitLoopbackemulator bestanden:
explizitesAktivieren, Öffnen, relativeWeite, kontaktbeendetesSchließen mit
Rohkraft, getrennteParameterbestätigung, Kraftgrenzen, gegenseitigerAusschluss
beiderActions, Prozess-Lease, Monitor ohneWrites und Zielerhalt beimExit.

Nachweise `setup/research/gripper-ros-api-20261117/`, Build-/Testlogs unter
`setup/logs/uwa-gripper-api-*`. Die reale Erstöffnung vom17.11.ist getrennt in
[Hardware-Inbetriebnahme](hardware_commissioning_2026-11-17.md) dokumentiert.
Diese neue API-Implementierung enthält keine erneute reale Fingerbewegung.
Die Read-/Capabilities-Services aller vier echten Geräte wurden anschließend
über den neuen Client bestätigt (`hardware-readonly.json`, commands_sent=[]).
Ein erster Clientstart wartete zu kurz auf DDS-Discovery im großen Zellgraphen;
die Verfügbarkeitssuche wartet jetzt bis10s vor einer Anfrage. Geräte- und
Befehlsfristen bleiben unverändert. Kommandos wurden dabei nicht erneut gesendet.
