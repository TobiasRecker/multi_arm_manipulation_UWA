# Dreiarmprobe ohne Werkzeug

Nutzerauftrag26.11.2026: Nach abgeschlossenem Kartongriff die bereits in
Gazebo gezeigte Haus-/Kreis-/Axialfolge für reale Arme vorbereiten. Der
linke Vorderarm fährt leer mit; keine Stiftaufnahme. Ein mathematischer
Punkt300mm entlang Tool0+Z ersetzt die virtuelle Stiftspitze. Er ist keine
reale Werkzeuggeometrie, kein Kontakt und kein Materialeingriff.

`tools/prepare_carton_air_demo.py pack` bindet einen abgeschlossenen
Library-Wiegehub, dessen Kartonmodell und eine aktuelle Vierarmaufnahme.
Rechter Iststart muss zum erfolgreichen20-mm-Hub passen. Die beiden
Handgelenke müssen auf eine gemeinsame aktuelle Kartonpose schließen.
Inhaltsgebundene Modellkennung vergleicht Mesh-Hashes statt rechnerabhängiger
Dateipfade. Die ursprüngliche pathabhängige Kennung wird nicht blind umgangen.

Referenz sind54 tatsächlich abgeschlossene Gazebo-Phasen aus
`setup/tasks/house_drill_home_20261120_01/run05/drawing-trajectories/`.
Kartongeometrie und Werkzeugbezug werden aus dem damaligen Zellmodell
rekonstruiert; die neuen Halter behalten ihre aktuellen festen Griffe.
Der übrige linke Arm steht derzeit nahe der Stiftaufnahme und behindert die
Unterseitenpräsentation. Eine vorgeschaltete Parkfahrt wird deshalb mit
dem aktuell gehaltenen Karton geprüft. Vor einer tatsächlichen Parkfahrt
muss bestätigt sein, dass dieser Greifer leer ist. Die reine Offline-
Hypothese ist keine Freigabe oder Behauptung eines unbeladenen Arms.

Zusätzlich zu den54 Referenzphasen werden die aktuelle Kartonpose und die
Arbeitspräsentation durch zwei geprüfte Ausrichtphasen verbunden. Eine
bloße Welttransformation der neuen53°-Kartonpose würde den Arbeitsarm um
1,23m von seiner Basis weg verlangen. Die freie Anfahrt vergleicht mehrere
IK-Zweige sowie direkte und aufgerichtete Gelenkwege einschließlich der
vollständigen Zwischengeometrie. Die Arbeitslage kann als expliziter
`--work-offset x y z` verschoben werden; kein Einlernen alter Gelenkwinkel.

`draft` ist ausschließlich eine grobe Verwerfungsprüfung auf titanpc.
Das Artefakt bleibt ausdrücklich `executable:false`, auch bei bestandenem
Entwurf. Reale vollständige Greiferöffnungshüllen und Selbst-/Umgebungs-
kollisionen werden geprüft, ebenso40mm an den vier Nachbararmpaaren.
Eine separate getragene Kartonhülle berücksichtigt nominale Padkontakte;
die nominalen Fingerstellungen werden nicht als gemessene Stellungen
ausgegeben. Keine Tisch-/Arm-/Greiferkollision wird pauschal freigegeben.

Eine spätere Ausführung erfordert erst die dichte Prüfung der tatsächlichen
Controllerinterpolation,0,1rad/s-/TCP-/Beschleunigungsgrenzen, feste
Griffrelationen, geometrischen Aufgabenbahnen und aller Anschlüsse sowie
die Freigabe der konkreten versionierten Realbahn in Motion Review.
`tools/qualify_carton_air_demo.py` bereitet hierfür die Dateiqualifikation
vor: gemeinsame ganzzahlig gerundete Controllerzeiten, reale Gelenk-/TCP-/
Beschleunigungsgrenzen, Endpunkte in Ruhe, feste Griffrelationen und Vergleich
der virtuellen lokalen Werkzeugbahn mit den archivierten Controllerbahnen.
Auch dieses Artefakt bleibt `executable:false`; es ist kein Ausführungszugang.

In den aktuellen Entwürfen parkt der Arbeitsarm vor beiden großen
Kartonpräsentationen und der ersten Rückdrehung. Beide Tragarme bleiben
gemeinsam geführt. Danach wird der leere Arbeitsarm erneut zur jeweiligen
Fläche gefahren. Die Gegenwand hat eine freie Drehlage um ihre Normale:
eine solche Präsentationsänderung erhält ihre Normale und den Kartonmittelpunkt.
Eine zusätzliche, ausdrücklich protokollierte Lageänderung nur der letzten
Präsentation verändert die vorherige Unterseitenlage nicht. Bei großen
Übergängen können direkte räumliche Interpolation und begrenzte Ausweichbögen
als neue Kandidaten geprüft werden; keine alte Gelenkfolge wird blind abgespielt.

`--regrasp-reference-branch` bezeichnet ausschließlich eine hypothetische
zukünftige Neuaufnahme mit anderen Halterkonfigurationen. Startart und
Nichtausführbarkeit werden ausdrücklich protokolliert. Diese Werte dürfen
niemals als Fortsetzung des aktuell schwebend gehaltenen Kartons ausgegeben
oder ohne tischgestützte Neuaufnahme an Controller gesendet werden.
Gemeinsamer nomineller Zeitbezug allein ist kein Nachweis der realen
Griffkopplung bei großen Drehungen. Der bestehende Return-to-Home-Stand
hat dafür noch kein `loaded_sync`-Profil. Seine begrenzte3-mm-Absenkung
qualifiziert keine großen Transport-/Drehbewegungen dieser neuen Aufgabe;
eine solche Qualifikation darf nicht durch diesen Entwurf vorgetäuscht werden.
Der Entwurf öffnet keine Greifer und kehrt nach seinem Schlussabstieg
zunächst zur gehaltenen Ausgangshöhe zurück; er setzt den Karton nicht
automatisch ab. Keine Änderungen am Schutzdienst oder an Controllern.
