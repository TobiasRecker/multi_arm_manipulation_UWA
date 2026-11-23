# Start des tischgestützten Kartongriffs

Stand 23.11.2026, Startkorrektur, Logdiagnose und passive Vergleichsmessung
abgeschlossen. Die Ursache der früheren Telegrammlücke und der reale Griff
sind offen.
Codex untersuchte den Library-Lauf
`01fdc7a4a84c4fd4b580ccd949b15c09`, den Start unter unbeladenen Holds
und die Meldungen im Browser und Safety Log. Betroffen sind der Kartonstart,
die Ausführungsdiagnose und die Bedienanleitung. Kein Dienstneustart geplant.

Um 15:12:25 AWST scheiterte die erste Hochanfahrt vor dem ersten Ziel.
Im Phasenbericht sind Arm- und Fingerbefehle leer. Alle vier letzten
nativen Geschwindigkeitsvektoren waren null. Der Browser hatte zuvor beide
rechten Programme als bereits laufend erkannt und die Hold-Vorbereitung
übersprungen. Eine spätere lesende Supervisorabfrage ergab CLEAR mit null
verriegelten und null gehaltenen Armen bei bestätigten Manager-, Hardware-
und Hold-Konfigurationsmeldungen. Der alte Phasenbericht speichert das
Supervisorpaket des Abbruchzeitpunkts nicht.

Der N100 lädt die drei geprüften Kartonmodule. Rücksicherung in
`~/uwa-ur-runtime/review-candidates/carton-holds-2311.ZjClEXj2/previous`.
28 vorhandene Softwareprüfungen bestanden. Im Offline-Nachlauf der
gespeicherten Supervisorlage wurden ausschließlich die fehlenden Holds
angefordert. Bei bereits gehaltenen Armen blieben die Anfragen aus.
Die neue Safety-Log-Erfassung ordnet den alten Abbruch dem Originalworkflow
als „Blocked before phase command“ zu.
[Messwerte und Nachlauf](../../../setup/tasks/carton-holds-20261123/)

Neuer realer Browserlauf `ab48f95c01af4ae2bbfb8123b52033c6` auf
Nutzerwunsch um 15:26 AWST angestoßen. Alle vier Holds waren beim neuen
Start bereits bestätigt, beide rechten Programme liefen. Geprüfte
Parallelphasen hoch 41,113 s und offen 7,934 s. Fahrrevision
`5506221212b34d7aa9a6dc3e7c06e02b` zur Bedienentscheidung vorgelegt.

Die Freigabe wurde angenommen. Der Runner brach um 15:28:02 AWST beim
Verbindungsaufbau für die Hochanfahrt ab. Auch hier blieben beide Befehlslisten
leer. Die letztgemessenen Gelenkgeschwindigkeiten waren auf allen vier Armen
null. Der N100 protokollierte schon während der Vorbereitung um 15:26:19,152
den Verlust der Reverse-Verbindung von rechts vorne und um 15:26:19,202
die Guard-Verriegelung. Links vorne folgte innerhalb derselben Sekunde.
Im N100-Journal steht für dieses Fenster keine native STOP-Anforderung.
Die reale Planungsaufnahme enthielt bereits STOPPED für rechts und links
vorne. Die generische Offline-Planprüfung erlaubt das. Der aktualisierte
Library-Start prüft die beiden fahrenden Programme nochmals anhand der
nativen Rückmeldung vor dem Foto. Beide archivierten Zustände wurden über
diesen Pfad offline nachvollzogen.

Das auf Nutzerauftrag per SSH gelesene URControl-Protokoll von rechts vorne
zeigt auf der Roboteruhr um 08:26:02,481 „Request to kill non-existing thread“,
dann RUNNING → STOPPING → STOPPED und anschließend das Schließen des
`reverse_socket` durch die Steuerung. Der N100 sah einen überzogenen
Reglertakt erst nach dem Verbindungsabbruch (3,973 ms bei 2 ms Soll).
Diese Meldung beweist die Ursache des Programmendes nicht.
[Roboterprotokoll](../../../setup/tasks/carton-holds-20261123/right-front-urcontrol.log)
und [Treiberjournal](../../../setup/tasks/carton-holds-20261123/driver-second.txt).

Nach Ende des Kartonlaufs löste der Supervisor um 15:30:01,981 für rechts
hinten separat einen nativen STOP aus. Die Hardwarebestätigung war
222,679 s alt. Eine spätere lesende Abfrage bestätigte alle vier Holds und
Verriegelungen. Für beide rechten Arme war `ros.urp` gestoppt, die native
Safety meldete NORMAL. Der lokale Safety Log zeigt nun auch jüngere
Guard-Verriegelungen, wenn die Suche über die gesamten 24 Stunden ausläuft.
[Zeitfenster](../../../setup/tasks/carton-holds-20261123/journal-followup.txt) und
[Safety Log](../../../setup/tasks/carton-holds-20261123/safety-second-final.json).

Nach ausdrücklicher Zustimmung zur Protokollspeicherung über Dashboard
bestätigte die seriennummerngeprüfte rechte vordere Steuerbox `Log saved to disk`.
Der danach per SSH gelesene Pendantverlauf nennt um **08:26:02,551 Roboterzeit**
einen Timeout beim Warten auf ein Kommando auf `reverse_socket` und um
08:26:02,552 das Ende von `ros`. Derselbe Text steht im früheren Vorfall um
07:32:02,284 Roboterzeit. Der erste neue Eintrag entspricht dem
N100-Ereignis um 15:26:19 AWST. Der aktive rechte vordere Manager lief
mit 500 Hz, im geladenen Robotermodell standen `non_blocking_read=True`,
Reverse-Port 53001 und `robot_receive_timeout=0.04` Sekunden. Die genaue
Paketlücke und ihre Entstehung zwischen RTDE-Empfang, Treiberausgabe und
Netz sind nicht aufgezeichnet. Die Zehnminutenwerte der Ethernetfehler sind
null, die 21,99 % CPU-Leerlauf im selben Fenster sind ein Mittelwert.
Der nächste gezielte Nachweis braucht Zeitstempel des ausgehenden Reverse-
und eingehenden RTDE-Verkehrs. Auf dem N100 ist tcpdump vorhanden,
eine sudo-Abfrage für das Werkzeug verlangt interaktive Authentifizierung.
[Gespeicherter Pendantverlauf](../../../setup/tasks/carton-holds-20261123/right-front-history-flushed.txt)

Nutzerauftrag 23.11.2026 zur passiven Netzwerkaufzeichnung. Seit 16:11 AWST
erfasst tcpdump auf dem N100 maximal fünf Minuten die TCP-Kopfzeilen für
rechts vorne auf der Roboternetz-Schnittstelle `enp5s0`, isoliert auf
Reverse-Port 53001 und RTDE-Port 30004. Der Operator authentifizierte sich
im sichtbaren SSH-Terminal. Vor der Aufzeichnung meldete rechts vorne
`ros.urp` als STOPPED bei nativer Safety NORMAL. Der lesende Socketabgleich
ordnet den lokalen RTDE-Port 35586 dem Controller-Manager und 36450 der
Guard-RTDE-Verbindung zu.

Die Aufzeichnung reicht bis 16:16:03 AWST. Beim regulären Library-Lauf
`cd940bec4d5d4f16a58a92a3b1df3069` öffnete rechts vorne um 16:13:28 AWST
die Reverse-Verbindung. Es folgten 76.633 ausgehende TCP-Pakete mit Nutzdaten.
Der größte Abstand am N100-Messpunkt betrug **11,923 ms**, ohne beobachteten
Verbindungsabbau. Die RTDE-Verbindung des Treibers zeigte maximal **25,560 ms**,
etwa 3,5 s vor Aufbau der Reverse-Verbindung. Nach dem Messfenster meldete
das Dashboard beide rechten Programme PLAYING. Die Aufzeichnung endete am
Zeitlimit mit Status 137 und ohne tcpdump-Verluststatistik. Die gespeicherten
Zeitstempel decken das vorgesehene Fenster ab.
[Auswertung](../../../setup/tasks/carton-holds-20261123/reverse-capture.nRwLDebh/summary.json)

Der reale Lauf endete um 16:14:22 AWST bei der OAK4-Registrierung vor
der Fahrplanung. Standardfenster und Hydrogen-Fenster lieferten jeweils null
auf der Tischauflage gültige Fits. Der beste Standardversuch lag bei
6,599 px RMS und 6,5 px Grenze. Fokus 107 und 25 ms Belichtung waren wie
im erfolgreichen Bildfit vom 15:26-Lauf. ISO änderte sich von 229 auf 253.
[Bildfit](../../../setup/tasks/uwa_program_library/cd940bec4d5d4f16a58a92a3b1df3069/registration/registration.json)
