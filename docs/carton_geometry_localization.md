# Direkte Kartongeometrie,26.11.2026

Der Livepfad `localization_method: mesh_landmarks` benötigt keinen
Aufdruck-/Texturabgleich. Er verwendet vier eindeutig benannte Modellpunkte:
die oberen Enden der vier senkrechten **äußeren Eckfalten des ganzen
Kartons**. Das sind andere Punkte als die früher verlangten oberen/unteren
Ecken einer einzelnen Vorderwand. Laschenspitzen und ausgeschnittene
Wandmitten sind keine Landmarken.

Gemini erhält zuerst die Übersicht und fordert mit `locate_box` einen
nativen Detailausschnitt an. Nach diesem Bildwechsel beziehen sich alle
normalisierten `[y,x]`-Punkte auf den neuen Ausschnitt. Die jeweilige
native Fensterzuordnung wird gespeichert. Der ursprüngliche Auftrag
benennt die Punkte, Ausschlüsse und Sichtbarkeitsbedingung bereits konkret.

`check_geometry` ist ein begrenzter JSON-Aufruf an den lokalen Runner.
Gemini kann höchstens drei Messungen anfordern und anschließend nur eine
Kennung einer bestandenen Messung mit `submit` übernehmen. Das gibt Gemini
keinen Shell-, Dateipfad-, ROS- oder Roboterdienstzugang. Der bisherige
image-only-ACP-Client weist andere Werkzeugaufrufe weiterhin ab. An das
Modell gehen nur Bildpunkte und Messreste, keine absoluten Roboterposen.
Alle Rohantworten werden vor der Schemaauswertung gespeichert.

Die lokale Rechnung verwendet die vorhandene Kamerareferenz, die feste
Tischauflage und die tatsächlichen Eckhöhen aus dem bestehenden Mesh.
Eine der vier Mesh-Ecken ist rund3,93mm niedriger. Die unregelmäßige obere
Wandkontur wird nicht als perfektes Rechteck angepasst. Projektionsstrahlen
werden mit diesen Höhen geschnitten, dann eine aufrechte starre Lage in
der Tischebene bestimmt. Zyklische Punktzuordnungen werden geprüft;
90° wird nicht als Kartonsymmetrie freigegeben.

Die neue endliche Einzelbildprüfung verwendet höchstens10mm Rest je
Modellecke sowie höchstens10mm Zentrum-/2° Winkelstreuung beim Weglassen
je eines Punktes. Das ersetzt die alte Textur-RMS-/Zweihypothesenprüfung;
es ist keine Behauptung unabhängiger Messungen oder absoluter Genauigkeit.
Kein vorgeschlagener Ausreißer wird still entfernt. Meshgeometrie und
Wandstärke sind weiterhin bildbasierte Annahmen. Die Prüfung liefert
Restfehler und klare Ablehnungsgründe pro Beobachtung.

Bei zwei akzeptierten Ansichten gelten weiter30mm Zentrum und3° Winkel,
mit180°-Symmetrie. Die OAK4-Pose bleibt unverändert die metrische Quelle;
es wird nicht gemittelt. Ganze Folge einschließlich Wiegehub offline
prüfen und reguläre Motion Review verwenden.

## Tiefe

`depth_geometry: true` nimmt vor den nativen Fotos einen ruhenden
`rgbd_hq`-Datensatz mit demselben Fokus auf. Er kombiniert 4×4
Stereo-Bilder einschließlich des IR-Blocks und 3×6 Farbbilder auf
dem entzerrten RGB-Gitter. Die 8K-Pipeline startet erst danach und
bleibt für Registrierung und frisches Einfahrfoto offen.

Tiefe wird mit ihrer eigenen tatsächlichen1280×960-Projektion und D=0
ausgewertet, nicht über8K-Pixelindizes. Eine endliche kamerabezogene
Tisch-/Innenbodenmessung und die sichtbare Board-Rückprojektion werden
getrennt protokolliert. Die Tiefe verändert die native RGB-Pose nicht.
Fehlende Tiefenpixel werden nicht gefüllt; fehlende Innenbodentiefe ist
keine zusätzliche Positionsmessung. Zwischen historischen Aufnahmen wird
keine Gleichzeitigkeit behauptet. Kein pauschaler Tiefenoffset.

## Nachweis

Die zuvor verworfene Schräglage aus Lauf
`0c5cd4e9ea474e7a95517ededa3bfd3a` besteht jetzt beide Ansichten:
maximaler Eckrest OAK4 2,714mm, OAK Pro0,313mm;
Kameravergleich22,602mm/0,03909°. Das sind interne Modell-/Bildreste,
keine unabhängig gemessene absolute Lokalisierungsgenauigkeit.
Protokolle unter `setup/tasks/carton-geometry-20261126/` im Workspace.

Vollständige Folge an diesen Archivdaten offline bestanden unter
`complete-plan-qualified/`; keine reale Fahrt daraus. Der Wiegeplan
berücksichtigt bekannte horizontale dünne Markerplatten bis zur bestehenden
5-mm-Aufweitung als Auflage. Kontakt ist ausschließlich während der
monotonen senkrechten Trennung erlaubt; nach Freifahrt wieder geprüft.
Höhere/dickere oder geneigte Platten erhalten keine Ausnahme. Keine neue
Tischmarge und keine Ausnahme gegen Arme oder Greifer.

82 gezielte Geometrie-/Ablauf-/Quellenbindungs- und Kameraprüfungen bestanden.
Auf N100 Wiegeplaner und Task-Ablaufhelfer mit Vorgängerhash und Sicherung
aktualisiert; die gebundenen Geometriequellen liegen dort zur Hashprüfung.
Der Geometriepfad verlangt seine eigenen Quellen statt der alten Texturdatei.
Echte N100-Dateiladerprüfung mit60 Dateien, beiden Anfahrphasen und gemeinsamem
Hub bestanden, ohne Hardwarebefehl. Keine N100-Dienste neu gestartet.
Neue Lokalisierung und Kameraverarbeitung laufen weiterhin auf ROSmini.
