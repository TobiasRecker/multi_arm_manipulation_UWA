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
`usb_cam`-Ansatz beschrieben. Sie erfordert eine geänderte Verbindung. Robotiq
garantiert dafür keine umfassende Steuerung von Fokus/Belichtung/LEDs; ein
Anwender im Herstellerforum berichtet jedoch ausdrücklich von erfolgreicher
Fokussteuerung per OpenCV/USB. Das ist noch kein Nachweis für unser Gerät.
Für den ersten Test daher den vorhandenen Controller-Anschluss nutzen.

### Bildqualität: Sensor und HTTP-Bild unterscheiden

**Nachprüfung am 2026-11-10 erfolgreich:** derselbe HTTP-Endpunkt lieferte
HTTP200, ein decodierbares JPEG mit **640×480Pixeln**, 83379Bytes. Frühere
Erreichbarkeitsfehler sind damit historische Beobachtungen, kein aktueller
Nachweis eines dauerhaften Defekts. Bericht/Bild unter
`setup/logs/right-rear-wrist-2026-11-10/quality_check.{json,jpg}`.
Keine Einstellungen oder Roboterdaten verändert. Bildfrische dabei nicht
nachgewiesen; das empfangene Bild zeigt Pendant/Tisch/Arm, kein ChArUco-Board.
Das Display ist stark überbelichtet; eine konkrete Fokusursache ist daraus
nicht zuverlässig ableitbar.

Laut **2019-Robotiq-Handbuch** unterstützt die Kamera maximal2560×1920Pixel
(etwa5MP) bei2fps, alternativ640×480 bei maximal30fps, und eine Flüssiglinse
mit Fokusbereich70mm bis unendlich. FullHD1920×1080 ist damit weder die
maximale Sensorauflösung noch der hier beobachtete HTTP-Modus. Ob ein bestimmter
FullHD-Modus verfügbar ist, muss am tatsächlichen Aufnahmepfad geprüft werden.
Der HTTP-Endpunkt darf nicht als5MP-Rohbildschnittstelle behandelt werden.
Robotiqs älteres Supportarchiv nennt keine API zum Ändern der HTTP-Auflösung;
keine erfundenen `width`-/`height`-/`focus`-URL-Parameter verwenden.

Fokus am Pendant im Robotiq-Dialog für **Teach Object / Select Model** bzw.
**Configure Model / Cam Locate** prüfen (Bezeichnungen versionsabhängig).
Die2019-Anleitung beschreibt Kamera-/Zahnradsymbol unten links im Kamerabild,
Fokus, Auto/Manual sowie **Retake** zum erneuten Fokussieren. Einstellungen im
Configure-Model-Schritt können die vorherigen Einstellungen überschreiben.
Ein JPEG-GET ist kein dokumentierter Autofokus-Trigger.

Zum Prüfen kontrastreiches Board in der gewünschten Messebene verwenden,
Fokus/Belichtung dort einstellen und danach für Intrinsics und Hand-Auge-Reihe
konstant halten. Bei veränderlichen Entfernungen geeigneten Schärfebereich
wählen; bei Fokusänderung die Gültigkeit der Intrinsics erneut prüfen.
Höhere echte Auflösung separat über unterstützte Kameramodi bzw. einen
untersuchten USB-Aufnahmepfad prüfen;5MP über HTTP oder USB nicht ungeprüft
versprechen. Hochskalieren des640×480-Bildes liefert keine neuen Details.

### Fokus vom PC und Umrechnung aus Entfernung

**Aktualisierung2026-11-10:** NutzerarchivUCC1.11.3 lieferte jetzt die konkrete
interne HTTP-Schnittstelle. GET`/getcamerasettings` und`/getcamerasettingsdetails`
auf right_rear erfolgreich; POST-Setter und Fokus-Trigger im Client nachgewiesen,
noch nicht ausgeführt. Originalregler0…1023, API-Wert=`1023−Reglerwert`.
Siehe[Archivbefund](wrist_urcap_analysis_2026-11-10.md). Die folgenden Aussagen
über noch nicht gefundene Netzwerksetter beschreiben den vorherigen Recherchestand.

**Umsetzung am selben Tag:** Fokus-Schreiben, Fokus-only-Trigger und eigenes
Qt-Bildfenster inzwischen an right_rear geprüft. Bedienung:
[Kamerafenster](wrist_camera_focus.md). Die vorherige Einschränkung „noch nicht
ausgeführt“ ist für diese Kamera durch den dortigen Prüfnachweis ersetzt.

Nutzerpräferenz vom2026-11-10: Fokus möglichst per Skript/PC-Schieberegler
bedienen, nicht bei jedem Versuch am Pendant. Eine zwingende physische
Pendantbedienung lässt sich aus der fehlenden öffentlichen API nicht ableiten.

- **Bestehende Controller-Verbindung:** HTTP-Bildabruf nachgewiesen, aber bisher
  kein dokumentierter Netzwerk-Fokussetter gefunden. Ein nächster technischer
  Schritt wäre die lesende Prüfung des zur installierten URCap-Version
  gehörenden erzeugten `.script`/Kameraprogramms auf Fokus-/Kamerafunktionen.
  Interne Funktionen sind versionsabhängig; ihre externe Nutzbarkeit erst prüfen.
  In dieser Recherche keine Controllerdateien ausgelesen oder Skripte gesendet.
- **Direktes USB am PC:** ein Anwender beschreibt Fokussteuerung per OpenCV im
  Robotiq-Supportforum; Robotiq bezeichnet Direkt-USB-Steuerung als nicht offiziell
  unterstützt. Tatsächliche Controls mit V4L2 abfragen und Bildwirkung prüfen,
  bevor ein Schieberegler als funktionsfähig ausgegeben wird. Keine Wertebereiche
  oder `CAP_PROP_FOCUS`-Unterstützung für unser Exemplar voraussetzen. Der damals
  verlinkte Beispielcode war beim Abruf2026-11-10 nicht mehr verfügbar (HTTP404).
- **Entfernung:** die gewünschte Schärfeebene kann durch einen Abstand beschrieben
  werden, der elektronische Fokusstellwert ist aber nicht automatisch in Metern.
  V4L2 definiert die Einheit von `FOCUS_ABSOLUTE` ausdrücklich nicht. Für eine
  Flüssiglinse wird die optische Wirkung elektronisch geändert. Eine Zuordnung
  `Stellwert = F(Abstand)` braucht Herstellerdaten oder eine gemessene Kennlinie;
  keine lineare Umrechnung aus einem UI-Wert behaupten.
- **Sinnvolle Umsetzung:** zuerst nachgewiesener Fokussetter, dann Livebild und
  Schieberegler. Optional Schärfeoptimierung in einer festen Board-ROI mit frischen
  Bildern und unveränderter Belichtung; nicht die gesamte Szene/den nahen Greifer
  optimieren. Für eine Distanzkennlinie mehrere bekannte Boardentfernungen und
  jeweils optimalen Stellwert messen. Danach kann ein bekannter geschätzter
  Kamera-Board-Abstand als Startwert für die Regelung dienen.

Für die eigentliche Hand-Auge-Messreihe Fokus konstant halten. Änderungen können
Intrinsics/Verzeichnung ändern; automatisches Nachfokussieren pro Pose setzt ein
passend erweitertes Kameramodell bzw. getrennt kalibrierte Fokusprofile voraus.

### Woher kommt die `.script`-Datei? Zugriffsvoraussetzungen

Ein grafisches PolyScope-Programm liegt als `.urp` vor. PolyScope erzeugt daraus
URScript; eine bereits erzeugte Datei hat üblicherweise denselben Basisnamen
mit Endung `.script`, z.B.`Kameratest.urp`/`Kameratest.script`, unter`/programs`
oder in einem Unterordner. Ob diese Datei für ein bestimmtes Programm bereits
vorliegt, muss geprüft werden. Zum Lesen einer vorhandenen Datei wird das
Programm nicht ausgeführt. Ein fehlendes Kameraskript ist kein Anlass, ein
unbekanntes Programm zu starten. USB-Export einer vorhandenen Datei ist ebenfalls
möglich. Quelle: offizielle UR-URScript-/Dateitransfer-Anleitungen.

**Zugriffsprüfung2026-11-10:** SSH auf192.168.8.170 antwortet. Anmeldung als
`root` mit vorhandenen Standard-SSH-Schlüsseln abgewiesen; danach ein einzelner
Versuch mit dem öffentlich dokumentierten Hersteller-Standardkennwort ebenfalls
abgewiesen. Das beweist nicht eindeutig ein geändertes Passwort (auch eine
Zugriffsrichtlinie wäre möglich). Keine Authentifizierung erfolgreich, kein
Remote-Dateiverzeichnis gelesen, keine Programme oder Einstellungen verändert.
Hostschlüssel nur in temporärer Datei`/tmp/uwa-wrist-controller-known-hosts`.
Keine weiteren Passwortversuche.

Für die weitere Untersuchung wird ein funktionierender SSH-/SFTP-Zugang oder
eine lokal bereitgestellte Kopie des vorhandenen Kameraskripts und gegebenenfalls
des installierten Robotiq-URCap benötigt. Passwörter/Schlüssel nicht in
Projektdokumenten speichern; Zugang kann vom Nutzer lokal eingerichtet bzw.
Dateien können mit lokal eingegebenem Passwort heruntergeladen werden.

Für PolyScope5.10 und neuer beschreibt UR die Kennwortänderung am Pendant unter
Hamburger-Menü → Settings → Password → Admin: aktuelles Kennwort, neues Kennwort,
Bestätigung, Apply. Es geht um das Admin-/Linux-root-Kennwort, nicht das Safety-
oder Betriebsmodus-Kennwort. Das aktuelle Admin-Kennwort wird benötigt;
laut UR gibt es keine eingebaute Passwortwiederherstellung. Im Menü Security →
Secure Shell die erlaubte Authentifizierung prüfen: bei reinem Schlüsselmodus
reicht eine Kennwortänderung für den Login nicht. Ein Public-Key-Import über
Manage Authorized Keys ist eine Alternative ohne geteiltes Kennwort. Keine
Kennwort-/SSH-Änderung durch diesen Agenten ausgeführt. Quelle:
[UR: Secure setup ab PolyScope5.10](https://www.universal-robots.com/articles/ur/cybersecurity/secure-setup-of-ur-cobots/).

Der Schlüsselimport benötigt ebenfalls Admin-Entsperrung. Laut neuester
Nutzerangabe ist das Admin-Kennwort unbekannt; daher ist dieser Weg aktuell keine
unmittelbare Lösung. Die oben neu nachgewiesenen Kamera-HTTP-Abfragen benötigen
keinen SSH-Login.

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

- [UR: URScript und aus PolyScope erzeugte `.script`-Dateien](https://www.universal-robots.com/br/developer/urscript/).
- [UR: SSH-Dateizugriff](https://docs.universal-robots.com/tutorials/urscript-tutorials/ssh.html).
- [UR: SFTP und Programme unter `/programs`](https://docs.universal-robots.com/tutorials/urscript-tutorials/ftp.html).

- [Robotiq-Forum: Anwenderbericht zur OpenCV-Fokussteuerung über direktes USB](https://dof.robotiq.com/discussion/2434/how-does-one-control-led-lights-on-robotiq-wrist-camera-via-opencv-in-python-script).
- [Linux-V4L2: Fokuscontrols, Einheit nicht definiert](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/ext-ctrls-camera.html).

- [Robotiq-Handbuch2019: technische Daten und Fokus](https://assets.robotiq.com/website-assets/support_documents/document/UserManual_Camera_20191106.pdf).
- [Robotiq2019: Kameraeinstellungen und Fokusbedienung](https://assets.robotiq.com/website-assets/support_documents/document/online/Vision_System_e-Series_HTML5_20190313.zip/Vision_System_e-Series_HTML5/Content/Vision_System-Instructions-Manual-06-2017/5.%20Object_Teaching.htm).
- [Robotiq-Supportarchiv: HTTP-Auflösung/API-Grenzen](https://dof.robotiq.com/discussion/275/wrist-camera-live-image).

- [Robotiq: Bilder über den UR-Controller abrufen](https://robotiq.zendesk.com/hc/en-us/articles/4403928641427-Retrieving-Robotiq-Wrist-Camera-pictures-on-a-computer).
- [Robotiq: Webcam-/ROS-Anbindung und Grenzen](https://robotiq.zendesk.com/hc/en-us/articles/1500000318602-Can-we-use-the-Robotiq-Wrist-Camera-on-ROS).
- [UR: Robotervorbereitung und individuelle Werkskinematik](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_robot_driver/ur_robot_driver/doc/installation/robot_setup.html).
