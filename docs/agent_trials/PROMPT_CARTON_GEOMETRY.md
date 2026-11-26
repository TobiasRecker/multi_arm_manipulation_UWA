Lokalisiere den offenen Avocado-Karton anhand seiner GEOMETRIE im Foto.
Es geht um alle vier oberen äußeren Ecken des GANZEN Kartons, nicht um
die vier Ecken einer einzelnen bedruckten Wand.

Gesuchte Punkte: oberes Ende jeder der vier senkrechten äußeren
Karton-Eckfalten, wo jeweils zwei Wände zusammentreffen. Verbinde diese
vier Punkte gedanklich einmal um die Öffnung. Nimm nicht die Spitze
einer gelben Lasche, nicht den ausgeschnittenen Mittelrand einer Wand,
nicht eine Stelle auf dem Innenboden und nicht einen Schatten auf dem Tisch.
Die vier Ecken können im Bild stark unterschiedliche Höhen haben. Der
Karton hat unregelmäßige Wandränder; sie werden NICHT als Rechteck geprüft.
Wenn eine nötige Ecke verdeckt/unsicher ist, melde uncertain statt zu raten.

Koordinaten: [y,x], Ursprung links oben im beigefügten Bild, ganze Zahlen
von 0 bis 1000 pro Bildseite. Vier Punkte in zyklischer Reihenfolge
um die Öffnung; Startpunkt beliebig. Keine Welt- oder Roboterkoordinaten.

Zuerst fordere eine Detailansicht des ganzen Kartons an:
{"action":"locate_box","box_2d":[y_min,x_min,y_max,x_max]}
Du erhältst dann einen neuen, scharfen Ausschnitt aus dem nativen Foto.
Alle danach angegebenen Punkte beziehen sich auf dieses NEUE Bild. Die
ursprüngliche Übersicht reicht zum Finden, die Detailansicht zum Markieren.

Du kannst unseren rein lokalen Geometrieprüfer selbst aufrufen. Er benutzt
die vorhandenen Eckhöhen aus dem Kartonmesh, die Kameraeinmessung und die
Tischauflage. Er vergleicht keine Aufdruckmerkmale. Dazu antworte genau:
{"action":"check_geometry","rim_corners_2d":[[y,x],[y,x],[y,x],[y,x]]}
Der lokale Runner führt diesen begrenzten Aufruf aus und gibt Bildreste,
Geometriereste und eine Kennung zurück. Die Rückprojektion ist selbst
eine Schätzung: Verschiebe eine echte Bildecke nicht bloß auf ihre Vorhersage.
Kontrolliere jeden vorgeschlagenen Punkt am ursprünglichen Foto.

Nach einer bestandenen Prüfung und deiner Sichtkontrolle antworte genau:
{"action":"submit","measurement_id":"Kennung aus dem Prüfresultat"}
Wenn es nicht eindeutig klappt:
{"action":"uncertain","reason":"kurzer sichtbezogener Grund"}

Maximal drei Geometrieaufrufe. Antworte ausschließlich als JSON. Benutze
keine anderen Werkzeuge, keine Dateien, keine Shell und keine Roboterdienste.
