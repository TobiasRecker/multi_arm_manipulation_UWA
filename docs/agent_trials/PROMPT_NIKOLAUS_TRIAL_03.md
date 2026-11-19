Du bist der frische Gemini-Agent für den dritten UWA-Test. Lies
`../context/NIKOLAUS_HANDOFF.md` aus deinem Arbeits-Repo.

Zwei rechte Arme halten den Avocadokarton. Links vorne zeichnet zuerst
einen Kreis mit 22 mm Radius auf die zugewandte Längswand (`y_max`),
dann ein **Haus vom Nikolaus auf die Unterseite (`z_min`)**, schließlich
einen zweiten 22-mm-Kreis auf die Gegenwand (`y_min`). Das Haus ist ein
Quadrat mit beiden Diagonalen und einem Spitzdach. Zeichne es in einem Zug
und fahre jede der acht Kanten genau einmal. Links hinten bleibt geparkt.
Am Ende kehren alle 24 Armgelenke in ihren Modellstartzustand zurück.

Koordinaten in mm im zentrierten Kartonframe, in der Unterseitenebene
`z=-Kartonhöhe/2`. A=(-20,-20), B=(20,-20), C=(20,20), D=(-20,20),
E=(0,40). Zeichne A→B→C→E→D→C→A→D→B. Eine Pause an einer Ecke ist
zulässig, ein Abheben oder weiterer Strich innerhalb des Hauses nicht.

Verwende den vorhandenen Oberflächenpfad in der separaten Quellkopie.
Verwende die vorhandene Flächenpräsentation, Grifftransformationen und Kollisionsprüfungen.
Behalte die Grenze 0,1 rad/s bei. Die virtuelle Stiftspitze muss die
Hauskanten in der wirklichen Modellbahn abfahren. Eine Zeichnung als
zusätzliche Grafik im Viewer erfüllt den Auftrag nicht. Übernimm keine
alten Ergebnisdateien. Erzeuge den Lauf aus der angegebenen Modellquelle
und deinem neuen Aufgabenprogramm. Der Versuch bleibt im Dateimodell.

Liefere neuen Viewer und gespeicherte Gelenkinterpolanten. Verwende für
Audit, Quelldiff und Bericht den Prüf- und Abgabeaufruf aus dem
Startprompt. Alte Kreisläufe müssen weiterhin prüfbar sein. Erfasse
Entwicklungszeiten, Befehlsausgaben und Fehlversuche im Trialordner.
