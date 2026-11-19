Du bist der frische Gemini-Agent für den vierten UWA-Test. Lies
`../context/HOUSE_DRILL_HANDOFF.md` und `../context/house_drill_spec.json`
aus deinem Arbeits-Repo. Setze die Aufgabe in deiner separaten Quellkopie
im Offline-Kinematikmodell um.

1. Rechts vorne und rechts hinten halten den Avocadokarton mit festen
   Grifftransformationen. Links hinten bleibt geparkt. Links vorne zeichnet
   den 22-mm-Radius-Kreis auf der zugewandten Längswand `y_max` wie bisher.
2. Auf der Unterseite `z_min` zeichnet links vorne das Haus vom Nikolaus
   mit **doppelter linearer Größe**. Nutze den Linienzug aus der Vorgabe.
   Das Quadrat ist 80 × 80 mm groß und die Dachspitze liegt 120 mm über
   seiner Basis. Zeichne alle acht Kanten in einem Zug.
3. Führe auf derselben Unterseite sechs **virtuelle axiale Zustellungen**
   auf einem geschlossenen **Lochkreis Ø150 mm** aus. Abstand der Positionen
   auf dem Kreis: 60°. Für jede Position: anfahren, Werkzeugachse auf
   die nach innen gerichtete Flächennormale ausrichten, senkrecht
   zustellen und wieder ausfahren. Der geometrische Vorschub reicht
   3 mm unter die Modellfläche, der Vorabstand beträgt 15 mm. Diese
   Zahlen definieren die Simulationsprobe.
4. Der letzte Kreis (`y_min`, Radius 22 mm) soll möglichst in umgekehrter
   Rollenverteilung entstehen. Der linke Vorderarm hält den Stift beim
   ganzen Kreis im Weltframe fest. Die beiden Haltearme bewegen den
   Karton gemeinsam so, dass relativ zum Karton ein voller Kreis entsteht.
   Anfahrt und Rückzug bleiben eigene Phasen. Wenn du diese Variante im
   vorhandenen Suchrahmen nicht gültig planen kannst, liefere die
   geprüften Teile und die konkreten Ablehnungsgründe. Ein ersatzweise
   bewegter Stift ist als Teilresultat auszuweisen. Alle 24 Armgelenke
   kehren am Ende in die Ausgangsstellung zurück.

Nutze das Toolkit für die vorhandenen Funktionen und implementiere
die fehlende Integration für axiale Zustellung und Kartonbewegung.
Die Nachweise müssen aus den gespeicherten Gelenkinterpolanten entstehen.
Markierungen auf einem Viewer allein sind kein Bahnbeleg. Behalte das
gemeinsame 0,1-rad/s-Profil und die geometrischen Prüfungen bei.
Der Test umfasst keine ROS- oder Gazebo-Dienste und keinen Gerätezugriff.

Protokolliere den Offline-Modellaufruf und speichere Modellergebnis,
Viewer und Suchdiagnose in deinem Trial. Nutze anschließend den vom
Starter angegebenen Aufruf für Prüfung und Abgabe. Verwende die
vorhandenen Prüfungen. Entwickle oder ändere keine Tests und Audits.
Erkläre relevante Ablehnungen oder Teilresultate in der Schlussmeldung.
