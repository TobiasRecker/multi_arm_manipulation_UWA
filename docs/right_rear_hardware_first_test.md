# Erster realer Wrist-Camera-/Hand-Auge-Test

Stand: 2026-11-10, Australia/Perth. Nutzerziel: zunächst ausschließlich
**right_rear**, hinten rechts, **192.168.8.170**. Das ist eine Vorgehensanleitung;
die automatische Kalibrierroutine ist weiterhin ausschließlich für Simulation
implementiert. Die parallel entwickelte Hardware-GUI ersetzt diese Integration
und ihre Prüfung nicht.

## 1. Kamerabild ohne Roboterbewegung

Die Wrist Camera hängt normalerweise per USB am UR-Controller. Für den ersten
Test Verkabelung erhalten und den vom Robotiq-URCap angebotenen HTTP-Bildabruf
verwenden. Im Browser öffnen:

<http://192.168.8.170:4242/current.jpg?type=color>

Alternativ ein Bild speichern, ohne ROS oder Robotertreiber zu starten:

```bash
mkdir -p ~/UWA_ws/setup/calibration/hardware_checks/right_rear
curl --noproxy '*' --fail --show-error --connect-timeout 3 --max-time 8 \
  'http://192.168.8.170:4242/current.jpg?type=color' \
  -o ~/UWA_ws/setup/calibration/hardware_checks/right_rear/wrist.jpg
```

Der Hersteller beschreibt **das zuletzt aufgenommene Bild**, keinen garantierten
Live-Videostream. Aktualität gegen die Kameravorschau am Teach Pendant prüfen,
z. B. mit einem bewegten Gegenstand im Sichtfeld bei stillstehendem Arm. Ein
neuer HTTP-Abruf oder PC-Empfangszeitstempel beweist kein neues Kamerabild.
Für Kalibrierung `type=color`, ohne eingeblendete Achsen/Annotationen, verwenden.

Bei Verbindungsfehlern zuerst Controller-Erreichbarkeit, Vorschau und
Robotiq-URCap-Version am Pendant prüfen. Eine fehlende Antwort beweist keinen
Kameradefekt. Ältere Robotiq-Beiträge nennen zusätzlich `/captureimage`, dessen
Verhalten versionsabhängig ist. Dieser Aufruf wurde hier nicht ausgeführt;
keine ungeprüften Capture-/Fokus-/LED-Kommandos in ein laufendes Programm einbauen.

**Lesender Versuch vom 2026-11-10:** PC192.168.8.209 über WLANwlp88s0f0,
Route zum Controller vorhanden. HTTP fehlgeschlagen mit `No route to host`,
Dashboard29999 ebenfalls Timeout. Kein Bild und keine aktuelle Zustandsantwort
erhalten. Ursache offen; frühere erfolgreiche Erreichbarkeit ist historisch.
Bericht: `$UWA_WS/setup/logs/right-rear-wrist-2026-11-10/report.json`.
Keine Treiber gestartet, keine Power-/Brake-/Programm-/Remote-/Kameraeinstellungen
oder Bewegungen geändert.

Eine alternative direkte USB-Verbindung zum PC wird von Robotiq als Webcam-/
`usb_cam`-Ansatz beschrieben. Sie erfordert eine geänderte Verbindung; Fokus,
Belichtung und LEDs lassen sich darüber laut Hersteller nicht entsprechend
steuern. Für den ersten Test daher den vorhandenen Controller-Anschluss nutzen.

## 2. Bildgeometrie und reales Modell vorbereiten

- Rechtes ChArUco-Board aus der vorhandenen PDF maßhaltig drucken: 40mm Quadrate,
  28mm Marker, 7×5 Felder, rechte IDs50–66. Eben auf eine starre Unterlage am
  Tisch befestigen und während beider rechten Messreihen nicht verschieben.
- Tatsächliche Bildgröße, Beschnitt und eventuelle Entzerrung des HTTP-Bildes
  prüfen. Für genau diesen Bildmodus passende Intrinsics und Verzerrung bestimmen
  oder verlässlich übernehmen. Nominelles Simulations-FOV/CameraInfo sind keine
  reale Kalibrierung. Doppeltes Entzerren vermeiden.
- Fokus für die Messentfernungen einstellen und während Intrinsics- und
  Hand-Auge-Aufnahme unverändert halten; Belichtung/Beleuchtung reproduzierbar.
- Individuelle UR-Werkskinematik auslesen und im Hardwaremodell verwenden.
  Offiziell muss dafür der Roboter eingeschaltet sein (idle genügt); diese
  Anleitung schaltet ihn nicht ein. `base` und `base_link` unterscheiden:
  URDF enthält die feste180°-Drehung. Für den Fit wird `T_base_link_tool0`
  gebraucht, kein unkonvertierter TCP mit aktiviertem Greifer-/Werkzeugoffset.

## 3. Erste Messreihe manuell, danach automatisieren

Empfehlung für die Erstinbetriebnahme: Posen vom Bediener am Teach Pendant
anfahren; ein eigener Hardware-Aufnahmemodus liest Bild und zeitlich passende
Gelenke/Flanschpose. Nach bestätigtem Stillstand und frischem Bild aufnehmen.
Dieser Aufnahmemodus ist **noch zu implementieren**, ebenso die verlässliche
Frische-/Zeitzuordnung des HTTP-Bildes. Empfangszeit allein genügt nicht.

Zunächst Einzelbild und Boarderkennung prüfen, danach30–50 verschiedene
Ansichten (Standard40), mit Kippungen um mehrere Achsen und verschiedenen
Abständen. Reine Translation oder nur eine Drehachse sind unzureichend.
Intrinsics bleiben im Hand-Auge-Fit fest, unabhängige Prüfstellungen beibehalten.
Der vorhandene Solver kann für dieses Datenformat wiederverwendet werden.

Für right_rear allein werden `T_tool0_camera` und `T_base_link_board` geschätzt.
Eine absolute Tischpose braucht zusätzlich eine bekannte Boardmontage im Tisch.
Die relative Basispose rechts benötigt anschließend right_front mit demselben
starr befestigten Board; dafür ist dessen absolute Tischpose nicht erforderlich.
Die Simulations-Ground-Truth ist keine Referenzmessung der echten Zelle.

Erst nach diesem Test automatisch fahren: Hardwarebackend an echte UR-Controller
anbinden, Echtzeit statt `/clock`, reale Zustände aller relevanten Hindernisse,
Werkzeug/TCP/Nutzlast und Kollisionsgeometrie prüfen; Stopp/Verbindungsverlust
gegen das reale UR-System testen. Die Gazebo-Pause des bisherigen Backends hat
auf echte Hardware keine Wirkung. Erste automatische Fahrt nur right_rear;
die übrigen Roboter werden dafür nicht automatisch geparkt.

## Quellen

- [Robotiq: Bilder über den UR-Controller abrufen](https://robotiq.zendesk.com/hc/en-us/articles/4403928641427-Retrieving-Robotiq-Wrist-Camera-pictures-on-a-computer).
- [Robotiq: Webcam-/ROS-Anbindung und Grenzen](https://robotiq.zendesk.com/hc/en-us/articles/1500000318602-Can-we-use-the-Robotiq-Wrist-Camera-on-ROS).
- [UR: Robotervorbereitung und individuelle Werkskinematik](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_robot_driver/ur_robot_driver/doc/installation/robot_setup.html).
