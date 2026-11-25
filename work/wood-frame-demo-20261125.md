# Holzrahmen-Demo, 25.11.2026 AWST

Status: Browser und Gazebo abgeschlossen. Die Browserversion zeigt
26 Phasen und lokalisiert das Holz markerlos aus synthetischen OAK-Bildern.
Bei 340 mm Pfostenabstand sind beide Schraubzugänge und der Arbeitsarmtransfer
geprüft. Zwei rechte Haltearme und links hinten bewegen sich nominell
3,57 s gleichzeitig. Der versetzte und um 5° gedrehte Balken verwendet das
gleiche Rezept. Chromes Ansicht, Phasensprung, Rückspulen und Schraubzustände
sind geprüft. Der Verdeckungsfall liefert keine Pose; Hydrogen bestätigte
die Verdeckung in einem synthetischen Bild.

Ausgaben unter `setup/tasks/wood_frame_20261125/`. Die Referenzserie
`browser-gazebo-reference` bindet Gazebo an die erste abgenommene Bahn.
`gazebo-contact-03/result.json` dokumentiert vier Padkontakte, vier virtuelle
Schrauben und die bestätigte Fixierung. Nach Gripperöffnung und Rückzug
blieb die Balkenpose gleich, mit 0,83 mm und 0,39° Abweichung zum Soll.
Ein alter Karton-Szenentest meldet auch mit dem bestehenden Installationsstand
32,55 mm X-Versatz gegenüber 30 mm Akzeptanzgrenze. Der neue Auftrag ändert
weder dieses Asset noch die globale Layoutdatei. Nur eigene Simulationsprozesse
verwaltet. Reale Werkzeug-/Aufbauvermessung und Freigabe stehen separat aus.
Keine Hardwarebefehle oder Änderungen am aktiven Sicherheitsprogramm.
