# UWA-Zelle – Ziele, Anforderungen und Übergabe

## Qualitätsaufnahmen der Program Library, 26.11.2026

Auf Nutzerwunsch greifen statische Qualitätsaufnahmen auf die OAK4-HQ-Modi
zu. **Object scan** nimmt einmal `rgbd_hq` auf. Bereits vorhandene Scans
mit einem älteren Übersichtsprofil erhalten die neue HQ-Übersicht beim
nächsten OAK4-Aufnahmeklick. Weitere OAK4-Detailbilder nutzen `hdr_hq`
(3×6 bei nativen 48 MP). **Supported carton grasp** nutzt `rgbd_hq` bei
`depth_geometry: true` als kamerabezogene Zusatzmessung vor der nativen
Poseaufnahme. Die Tiefenmessung verwendet ihr eigenes entzerrtes RGB-Gitter.
Die kalibrierten Pose-, Einfahr- und Freigabeaufnahmen nutzen ihre
bisherigen frischen Einzelbilder an den jeweiligen Aufgabenzeitpunkten.

Am realen Arbeitsplatz geprüft: **Object scan** über die tatsächlich
verwendete Capture-Aktion in einer separaten Testsitzung, Übersicht
1280×960 in 12,05 s, Detail 8000×6000 in 23,48 s. Bestellung des
Karton-Tiefendatensatzes separat erfolgreich, 16 Stereo- und 18 Farbframes
verifiziert. 60 gezielte Offline-Tests und 14 Subtests bestanden. Der
laufende Library-Webserver wurde bei freiem Auftragslock neu geladen.
Aktualisierter Katalog und der vorhandene Scan waren auf Port 34911
abrufbar. Prüfnachweis unter
`setup/tasks/library-hq-capture-20261126/validation.json`.
[Object scan](docs/object_scan_library.md) · [Karton-Tiefennachweis](docs/carton_geometry_localization.md)

## Fortsetzung als reale Dreiarmprobe ohne Werkzeug,26.11.2026

**Aktueller Abschlussstand dieses Arbeitsgangs:** Karton regulär freigegeben,
beide rechten Arme Home. Neue Neuaufnahme vor Bewegung am30mm-
Kamerazentrumsvergleich abgebrochen. Tiefen-/Zweikameradiagnose deutet auf
18–19cm statt der bildgeschätzten16,3cm Modellhöhe. Unabhängige Außenmaße
beim Nutzer angefragt; neues Luftprobe-Profil bis dahin deaktiviert.
Vollständiger Offline-Nachweis62Phasen und Cache-Wiederverwendung bestehen
für die bisherige Geometrie; noch keine vollständige reale Luftprobe.

Nutzer bestätigt erfolgreichen Kartongriff und beauftragt Haus-/Kreis-/
virtuelle Bohrfolge aus Gazebo. Rückfrage beantwortet: dritter Arm soll
leer mitfahren, nicht geparkt bleiben; keine Stiftaufnahme. Vorbereitung
und vollständige Offline-Prüfung beauftragt, konkrete neue Realbahn noch
nicht durch Motion Review freigegeben.

Library-Lauf7004b3c7e1f84e9dbd1733cc7645667b tatsächlich15:28:32AWST
abgeschlossen, Anfahrt und Kontakt vom Bediener in GUI freigegeben.
20-mm-Hub erfolgreich,0,509568kg, RF2,37803N/RR2,61913N
(47,588%/52,412%), BOTH_ARMS_LOAD_PLAUSIBLE. Empirisches Streuband
0,416094–0,603043kg ist kein absolutes Genauigkeitsintervall.
Aktuelle vierarmige Momentaufnahme mit dem Wiege-Endzustand bis auf
maximal0,000044rad übereinstimmend. Schutzstatus RUNNING, keine Konflikte,
keine aktiven Armziele. Nur gelesen, keine Bewegungs-/Greiferbefehle.
Neue Taskdaten `setup/tasks/carton-air-demo-20261126/` im Workspace.
Compute-Host erreichbar, TITAN RTX0%/175MiB,21GiB RAM verfügbar,
500,9GiB eigener Datenbereich frei. Längere Folgeplanung dort im Container.

Neuer rein dateibasierter Adapter `tools/prepare_carton_air_demo.py`,
Bedien-/Prüfgrenzen in `docs/carton_air_demo.md`. Alle Entwürfe ausdrücklich
`executable:false`, keine neue Runtimeinstallation, keine Greifer-/Armbefehle.
Vierarm-Start über bestehende Return-to-Home-Aufnahme inhaltlich gebunden:
Modellidentität ba2c9bcc8a5dd50f5594a0da09b5844fa2b49d3250c752a48181563a2d6a0790.
Erster lokaler Packversuch verweigerte korrekt den pfadabhängigen
Modellvergleich; anschließend dieselben Meshinhalte über bestehende
inhaltsgebundene Kennung auf N100/ROSmini bestätigt, kein Modellbypass.

Die zunächst auf den aktuellen höheren/weiter innen liegenden Griff
übertragenen Entwürfe scheiterten am Gegenwandübergang. Nutzer verlangt
anschließend ausdrücklich denselben Griff wie in der Simulation. Exakte
Objekt/Tool0-Transformationen und Halterzweige des abgeschlossenen
Gazebo-Laufs werden für eine **hypothetische tischgestützte Neuaufnahme**
verwendet, niemals als aktueller schwebender Istgriff ausgegeben.

Alle62 angepassten Phasen damit grob bestanden, Job
`carton-air-simskin-20261126-01`, Nachweis `simskin-result01/`.
Minimaler Nachbararmabstand48,624mm bei erhaltener40mm-Grenze.
Die bestehende30mm-Innenhülle an den kurzen Wänden ist eine konservative
Designhülle, keine physische Wanddicke. Ein zusätzlicher Hautmodellprüfer
verwendet die gebundene bestehende2,5mm-Assetgeometrie (Schätzung, nicht
vermessen) für den eigentlichen Kontakt. Nur Fingerspitzen dürfen diese
Haut berühren; Außenhülle prüft Arme, Handgelenke, Kameras und Umgebung.
Primäre vollständige Öffnungshüllen und alle Roboterpaarprüfungen bleiben.

`qualify_carton_air_demo.py` prüft tatsächliche JTC-Quintiken, gemeinsame
Nanosekundenzeiten,0,1rad/s,83,333mm/s,0,2rad/s², starre Griffbeziehung
bis0,1mm/1mrad und virtuelle lokale Aufgabenbahn bis0,25mm. Erste
Audits verwarfen Ausrichtung mit0,106mm sowie Gegenwandübergang mit
0,100285mm Griffabweichung. Übergangsknoten werden verdichtet;
kein Grenzwert und kein Tempo geändert. Keine reale mechanische
Synchronisierung großer Drehungen durch den Modellnachweis behaupten.

Vor der Rücksetzung frisches Foto geprüft; lose, unmodellierte Objekte
festgestellt und Arbeitsbereich im N100-ReviewStore ausdrücklich widerrufen.
Keine Bewegung/kein Greiferbefehl. Nutzer entfernt Balken, lose Ständer,
aufrechtes Schachbrett und Stifthalter; der Kamerahalter soll bleiben.
Nachaufnahme `clearance-photo/current-photo/standard.png` geprüft.
Konservative bild-/kalibrierungsbasierte Hülle des verbleibenden USB-
Kamerahalters unter `camera-holder-obstacle.json`: Weltbox
[-1,03;-0,17;0,90] bis[-0,70;0,17;2,30]m, **Schätzung, nicht vermessen**.
Nur in endlichen Offline-Aufgabenszenen, keine Änderung am Schutzdienst.
Statische Tischüberdeckung ignoriert; keine Roboter-/Kartonpaarfreigabe.
Die nun nötige freie Arbeitsarmumfahrung wird mit deterministischer
begrenzter RRT-Connect-Suche und denselben vollständigen Prüfungen gesucht.
Job `carton-air-qualified-20261126-05` vollständig bestanden,17:33:04AWST:
alle62 Phasen,72.218 Zustände der tatsächlichen Controllerinterpolanten,
minimaler Nachbarabstand46,789mm, maximaler starrer Grifffehler6,364µm,
maximale virtuelle lokale Bahndifferenz0,265µm. Modellabweichungen, keine
Hardwaregenauigkeit. Nominal1.759,958s bei unveränderten Geschwindigkeiten.
Dieser hypothetische Neuaufnahme-Nachweis bleibt `executable:false`;
neuer Istgriff und tatsächliche Anfahrt sind noch zu binden. Unveränderte
Bearbeitungsabschnitte sollen wiederverwendet werden; Nutzer hinterfragt
zu Recht wiederholte Vollprüfungen. Geänderte Anschlüsse separat prüfen.

Tischgestütztes Freigeben und Homefahrt konkret als `release-plan03`
geprüft:20mm Restspalt innerhalb der nutzergebundenen50mm-Freigabe;
kein beladener Armtransport. Beide ziehen nach Öffnen gemeinsam zurück,
danach unbeladene Homefahrten,100,250s nominal. Plan-SHA
`d950c2771701f5b9dc15626ab8ad8fb8dced4d2d346ef2048537e52d52c07268`.
Zusätzlicher Halternachweis `carton-release-holder-20261126-01` bestanden:
558/2155/2579 geprüfte Controllerzustände für Rückzug/RF-Home/RR-Home,
Karton-Falltube einschließlich vorhandener5mm-Positions-/3mm-Landehülle
außerhalb des Halters. Noch nicht ausgeführt; normale frische Aufnahme und
Motion Review bleiben. Arbeitsbereich noch widerrufen; Nutzer bestätigt
nur „Rest ist weg“, explizite Bestätigung des Verlassens ist angefragt.

Eigenes Rezept `carton-supported-simulation-v1` lokal vorbereitet, exakte
Referenzgriffe ohne bisherige11,25mm-Einwärtsverschiebung. Kraftreferenz,
FOR0/SPE16 und20mm-Wiegehub erhalten. Wiegehub des neuen Profils nutzt
Hautmodell plus Außenhülle; Legacyprofile unverändert. Neue optionale
Konfiguration `setup/skill_library/live-carton-simulation-grip.json`,
aktive Standardkonfiguration nicht umgestellt. Noch keine neue
N100-Installation oder Ausführungsanfrage.63 gezielte Tests bestanden
(`task-tests05.log`), einschließlich Referenzframes und gezielter
Halter-/statischer Kontakttrennung. Gesamte neue Anfahrt samt Hub muss
nach tatsächlichem Ablegen und neuer Lokalisierung frisch geprüft werden.

## Direkte Eckengeometrie eingebaut,26.11.2026

Nutzer bestätigt B/D in der alten Vorderwanddarstellung als fehlerhaft,
verlangt den verpflichtenden Aufdruckfit zu ersetzen und präzisen Erstprompt,
begrenzten Gemini-Zugriff auf die lokale Prüfung sowie Nutzung vorhandener
Modell-/Kalibrierdaten und Tiefe. Neuer Pfad umgesetzt und in beiden lokalen
Live-Konfigurationen `localization_method=mesh_landmarks` aktiviert;
primär `depth_geometry=true`. Vorherige JSON-Konfigurationen gesichert.
Bedienung, Geometriekriterien und Grenzen in
[direkter Kartongeometrie](docs/carton_geometry_localization.md).

Übersicht→locate_box→nativer Detailausschnitt→maximal3 check_geometry-Aufrufe
→submit einer bestandenen Kennung. Das ist ein lokales begrenztes JSON-
Werkzeugprotokoll, kein freier MCP-/Shell-/ROS-Zugang. Andere ACP-Werkzeuge
weiter gesperrt. Volle Rohantworten einschließlich Parserfehler gespeichert.
Vier obere äußere Eckfalten des ganzen Kartons statt Ecken einer einzelnen
Wand. Mesh-Eckhöhen einschließlich3,93mm Höhenunterschied verwendet.
Keine Texturmehrfachfits mehr im aktiven Pfad. Einzelbildkriterium nun
max10mm je Modelleckrest, Weglassprüfung max10mm Zentrum und2°; keine
unabhängige Genauigkeitsqualifizierung daraus.30mm/3° und OAK4-Vorrang bleiben.

Auf den zuvor gescheiterten nativen Bildern beide Ansichten erfolgreich:
OAK4 max2,714mm, OAK Pro max0,313mm Eckrest; gegen180° ausgerichteter
Kameravergleich22,602mm/0,03909°, OAK4 unverändert übernommen. Neue Verbindungslinien
sind in echte Rasterbilder eingezeichnet, unabhängig von der fehlerhaften
HTML-/SVG-Stildarstellung. Vorher/nachher unter
`work/carton-geometry-20261126/` im Workspace. A–D bezeichnen im neuen
Bild andere, eindeutig definierte Modellpunkte als im alten Wandbild.

Aktuelle8-Paar-RGB-D-Aufnahme Fokus107 um14:04AWST erfolgreich, tatsächliche
1280×960-Projektion gespeichert. Innenboden zeigt große Tiefenlöcher;
fehlende Daten nicht ergänzt oder in die RGB-Pose gemittelt. Die endliche
Tiefengeometrie protokolliert diesen Grund. Die Board-Projektionsprüfung
ist separat; verdecktes Board erzeugt keinen vorgetäuschten Tiefennachweis.

Erster vollständiger Offlineplan scheiterte im Wiege-Startmodell am Kontakt
weigh_carton/right_charuco_plate. Platte liegt im Modell2,95mm über Tisch;
die bestehende5-mm-Kartonhülle überschneidet die Auflage. Taskmodell nun
um streng qualifizierte horizontale dünne Markerplatten innerhalb dieser
bereits bestehenden Aufweitung ergänzt: Kontakt ausschließlich während
monotonen senkrechten Abhebens, danach wieder geprüft. Höhere/dickere oder
geneigte Platte weiter Hindernis. Keine zusätzliche Marge, kein Arm-/Greifer-
Kontakt ausgenommen, kein Schutzprogramm geändert.

`complete-plan-qualified/` mit Archivbildern/-Gelenken vollständig bestanden,
80 gezielte Tests bestanden. N100 vor Installation RUNNING, Daten verfügbar,
keine Kontakte, keine aktiven Armziele/Reviews. Nur prepare_carton_weigh.py
versionsgeprüft mit Backup installiert: alt a1824c60…, neu cd5a6d73…,
`n100-task-receipt.json`; keine Dienste neu gestartet/Hardwarebefehle.
Erster Installationsaufruf scheiterte vor jeder Änderung an der Eingabe;
korrigierte Übertragung und Receipt geprüft. Lokalen Library-Server mit
freier globaler Run-Lease am selben Port34911 neu geladen, GUI weiter offen.

Neuer normaler Library-Lauf `0f736e234ab8427b9cae38ba50b76f7c`,
Start14:29:05AWST, mit frischen RGB-D-/RGB-Aufnahmen und Gelenkdaten.
Dieser Lauf scheiterte vor jeder Fahrt an einer verbliebenen Legacy-
Quellenprüfung auf N100 (`register_carton_from_oak.py`). OAK4-Geometrie
war gültig (max8,135mm Eckrest), USB-Ecken diesmal verworfen. Bestehende
USB-Sichtbestätigung ergab gültigen single_confirmed-Pfad. Aktuelle Tiefe
im ausgewählten Innenboden0 gültige Pixel, im Tischbereich51308; keine
Zusatzposition aus diesen Löchern abgeleitet. Vollständiger Plan bestand.

Quellenbindung nun explizit nach localization_method: Geometrie verlangt
eigene Rechenmodule, Prompt, Asset/Mesh und Kamerasitzung, optional das
Tiefenmodul. Die alte Texturbindung bleibt für historische Texturprogramme
unverändert. Unbekannte Methode/fehlende Kamerasitzung werden abgewiesen.
Vorabprüfung prüft passende Dateien vor neuer Bildaufnahme. Alle neuen
Geometriequellen und Task-Ablaufhelfer versionsgeprüft mit Backup auf N100,
keine Dienste neu gestartet; Receipt `geometry-binding-receipt.json`.

Neue Dateiqualifikation an exakt gebundenen gespeicherten Bildern und
Ecken mit kompletter Offline-Neuberechnung: `binding-qualified/`.
Echter staged_approach- und checked_plan-Lader auf N100 bestanden:
60 Dateien, high/entry und ein gemeinsamer RF/RR-Hub. Explizit kein
aktueller Startnachweis und kein Hardwarekommando aus dieser Dateiqualifikation.
Beleg `n100-filecheck.log`.82 gezielte Tests bestanden, `final-all-regression.log`.

Webserver34911 wurde zwischenzeitlich beendet (SIGTERM), Robot Power blieb
offen. Nur den Library-Server am selben Port neu gestartet. Neuer normaler
Live-Lauf `7004b3c7e1f84e9dbd1733cc7645667b`, Start14:42:35AWST.
Nur diesen weiterverfolgen. Noch keine tatsächliche Kartonfahrt dieses
neuen Laufs bestätigt; keine neue Sicherheitsfreigabe erfunden.

Dieser Lauf wartet seit14:45:27AWST auf Motion Review
`e8e5f7b3765748e58a20d86e94afbc6d`, SHA
`c597c9164068542a3d4e05abb124da30200b014be28b50ea78cfd05e8a0901a1`.
Frische OAK4-Geometrie akzeptiert (max6,334mm Modelleckrest); USB diesmal
nur Sichtbestätigung, keine zweite metrisch akzeptierte Pose:
`single_confirmed`, OAK4 alleinige metrische Quelle. Vollständiger Plan
und N100-Quellenbindung bestanden. Hohe Anfahrt jedoch serieller Rückfall:
RF33,396s, RR46,912s; offene Einfahrt gemeinsam8,423s. Gemeinsamer20-mm-Hub
separat geplant1,279s. Gemeinsame hohe Bahn am Nachweis unabhängigen
Fortschritts gescheitert: konservative RF/RR-Abstandsuntergrenze−57,831mm
bei40mm Modellmarge. Das ist keine gemessene reale Durchdringung und
kein Beweis, dass jede alternative gemeinsame Bahn unmöglich ist.
Nutzer um konkrete Freigabe dieser88,731-s-Anfahrt oder weitere gemeinsame
Planung gebeten; keine Freigabe durch den Agenten gesetzt. Der Reviewtext
enthält noch den überholten allgemeinen Hinweis, die höhere Griffhöhe sei
nie auf Hardware gezeigt worden; tatsächlich ist der Erfolg25.11. dokumentiert.
Die aktuelle neue Pose/Bahn bleibt konkret zu prüfen. Quellen des laufenden
gebundenen Reviews deshalb nicht nachträglich verändert.

## Kartongewicht und neue Pose,26.11.2026

Der gestrige Library-Lauf `7d124f9a84e54252b3d7e0261e7ad981` ist laut
gespeichertem Ergebnis erfolgreich abgeschlossen: Motionreview17:26:28,
Kontaktreview17:27:32, gemeinsamer20-mm-Hub und Messung17:28AWST.
Masse0,508672kg, zusätzliche vertikale Last RF1,136545N/RR3,851825N,
Anteile22,78%/77,22%, je41Proben/Fenster. `BOTH_ARMS_LOAD_PLAUSIBLE`;
empirisches Streuband0,406280–0,611065kg kein Genauigkeitsintervall.
Kein unabhängiger Vierpad-/Schlupf-/Fremdkontaktnachweis. Nutzer bestätigt,
dass es gut funktioniert hat, meldet Arme in Home und Karton leicht bewegt,
und beauftragt Wiederholung. Gewichtsschätzung entsprechend erläutert.

Neue Vor-Ort-Bestätigung: Arbeitsbereich frei, leerer Karton direkt auf dem
Tisch, Buch entfernt.13:27AWST alle vier URs NORMAL/RUNNING/PLAYING mit
Reverse-Verbindungen, keine aktiven Ziele/Reviews, Schutzstatus RUNNING,
Kollisionsdaten verfügbar und keine Konflikte/Warnungen. Neue Review-Sitzung
an diese Arbeitsbereichsfreigabe gebunden, Tempo/Vertrauen unverändert.
Bestehender GUI-Library-Server auf `http://127.0.0.1:34911`, Backend minimal,
aktive Runtime unverändert. Browserzugriff weiterhin unavailable; keine
GUI-Klicks behaupten. Befunde `setup/tasks/carton-repeat-20261126/`.

Beide alten Kamerareferenzen abgelaufen. Reiner Library-Kalibrierlauf
`c11901ed0ab44e7384b3c125d085d1d1`13:28AWST: OAK4 erfolgreich17Marker,
1,21px Prüf-RMS, gültig bis27.11.01:28AWST. USB-OAK bei Fokus112 nur6Marker
statt mindestens12, trotz0,9075px Prüf-RMS nicht veröffentlicht. Aktuelles
USB-Bild zeigt den Karton vor großen Teilen des rechten Tischboards.
Keine Grenze gelockert/keine alte Referenz übernommen. Nutzer gebeten,
Karton vorübergehend aus der Board-Sichtlinie zu stellen; danach zweite
Referenz erneuern und Karton wieder in die gewünschte Testpose stellen.
Alternativ OAK4-only ausdrücklich als Auswahl angeboten, nicht gewählt.
Arbeitsbereich vor manueller Umpositionierung regulär widerrufen; keine
aktive Fahrt/Review. Nutzer bestätigt Karton zur Seite/Board frei/Bereich
verlassen. Zweiter reiner Kalibrierlauf `02bcb20918a54702b13431202295a284`
13:30AWST erfolgreich: je17Marker, OAK4 1,12px/USB0,999px Prüf-RMS.
Neue zwölfstündige Referenzen gültig bis27.11.01:30AWST. Nutzer gebeten,
Karton jetzt wieder in die gewünschte Testpose zu stellen und freien
Arbeitsbereich zu bestätigen. Keine neue Kartonfahrt/kein Greiferbefehl
in dieser Wiederholung bisher.

Nutzer bestätigt neue Pose/Bereich frei. Neue Review-Sitzung eingetragen,
normaler Library-Lauf `0c5cd4e9ea474e7a95517ededa3bfd3a`13:31:28AWST
mit aktuellen Bildern/Gelenken gestartet. Vor Planung ohne Bewegung
fehlgeschlagen: `Neither camera produced an accepted current carton pose`.
OAK4-Standardfit ohne Hypothese, drei vorhandene Hydrogen-/OpenCV-Runden
ergeben höchstens eine akzeptierte Hypothese (zwei nötig). Beste einzelne
unterstützte RMS5,807px bei bestehender6,375px-Grenze, übrige verworfen.
USB-Standard und Nachmessung ebenfalls ohne gültige Pose; zusätzlich
zweite Hydrogenantwort vom Status-/Bildkoordinatenparser verworfen. Ihr
Rohtext wurde nicht gespeichert; genaue fehlerhafte Stelle daher unbelegt.
Keine Grenz-
änderung oder hypothetische Pose an die Planung übergeben.

Drei zusätzliche endliche, visuell abgeleitete Frontwand-Entzerrungen
derselben OAK4-Aufnahme rein offline geprüft. Beste unterstützte Fehler
8,422/6,946/7,456px, jeweils oberhalb6,375px, keine übernommen. Protokoll
`setup/tasks/carton-repeat-20261126/rectification-results.jsonl`, alle
Bildbefunde erhalten. Kein Safety-, Planer- oder Registrierungsquellstand
geändert, keine neue Motion Review, kein Greiferkommando/Wiegehub. Nutzer
um Wahl gebeten: Bildauswertung für diese Schräglage weiter verbessern
(Karton stehen lassen), oder etwas zurückdrehen und Positionsversatz für
den Wiederholungsversuch beibehalten. Bestätigte letzte Masse bleibt0,509kg.

Nutzer fragt anschließend nach genauer Ursache und Gemini-Ein-/Ausgaben.
Interaktive Gegenüberstellung unter
`work/carton-gemini-explainer/gemini-kartonvergleich.html` im Workspace:
drei OAK4- und zwei USB-Runden, protokollierte JSON-Koordinaten, echte
gespeicherte Rückprojektionsbilder und lokale Messwerte. Erste gesendete
JPEGs aus unveränderten Quellen mit derselben Crop-/Thumbnail-/JPEG-Funktion
rekonstruiert und ausdrücklich so bezeichnet; Anzeige verkleinert. Spätere
OAK4-Runden erhielten das jeweilige verworfene Fitoverlay samt Messbericht.
USB-Runde2 erhielt nur den Bericht im bestehenden Bildgespräch, keine neue
Bilddatei. Zweite verworfene USB-Rohantwort fehlt, nur Parserfehler vorhanden.
Gemini meldete in allen gespeicherten Antworten found; Blocker ist die
nachfolgende metrische Bild-/Tischfitprüfung. Zwei Hypothesen bedeuten
Auswertungsvarianten pro Bild, nicht die zwei Kameras. Ursachenanteile von
Perspektive, Texturzuordnung und verformter Pappe noch nicht bewiesen.
Koordinatenabbildung und alle fünf Auswahlzustände der Darstellung geprüft;
kein Robot-/Kamerabefehl und keine Registrierungsänderung für diese Erklärung.

Nutzer bittet um schrittweise Erklärung: Bedeutung der vier Punkte,
Rückkopplung in Runde2 und Nutzen des nachgeschalteten Aufdruckfits.
Wünscht den verpflichtenden Aufdruckabgleich zu streichen, sofern Gemini
die für die Lokalisierung erforderlichen Daten liefert. Codebefund:
`front_quad_2d` wird derzeit nur zur perspektivischen Entzerrung verwendet,
danach unverändert Texturmerkmale gegen Modell und Tischauflage gefittet;
keine direkte metrische Eckenauswertung. Vier2D-Punkte plus vorhandene
Kamerakalibrierung, feste Tischauflage und definierte Kartongeometrie
ermöglichen prinzipiell einen eigenen geometrischen Lokalisierungspfad.
Dieser Pfad ist noch nicht implementiert/qualifiziert. Kein Aufdruckgate
ersatzlos entfernt und keine Fahrt ausgelöst. Gemini-Runde2 erhält den
besten verworfenen lokalen Modellversuch, keine bestätigte richtige Pose;
die Korrekturrunden sind keine unabhängigen Messungen.
Darstellung korrigiert: vier unveränderte Gemini-Wandecken A/B/C/D mit
Verbindung, robuste Themefarben und ausdrückliche Beschriftung als unsere
Einzeichnung von Zahlen. Verworfenen Eingabefit klar als unbestätigt markiert.
Alle fünf Auswahlzustände und Koordinatenabbildung erneut geprüft.

## Return to Home: Greifer inaktiv, 26.11.2026

Öffnungsreview `a4ef61404c954c1da568e76aac7fb426` um 12:55:34 AWST
freigegeben, um 12:55:38 in der Öffnungsphase abgebrochen. Beide Aktionen
wiesen den Auftrag beim Lesen der Robotiq-Register vor dem ersten SET ab.
Beide rechten Greifer meldeten in der anschließenden Abfrage ACT=0,
STA=0 und FLT=0, POS=226 vorne und POS=224 hinten. Keine Fingerbewegung
durch diesen Auftrag, kein senkrechter Rückzug und keine Homefahrt.
N100-Schutzstatus mit verfügbaren Daten und ohne Kollisionskonflikt.
`uwa-grippers.service` ist seit 25.11. 15:36 AWST aktiv, ohne Neustart
oder Journaleintrag am 26.11. Ursache der Deaktivierung offen.

Aktuelles OAK4-Bild zeigt den Karton zwischen den Fingern. Bediener
bestätigt, dass der Karton frei hängt und aus der aktuellen Höhe fallen
darf. Die geplanten rund 16 mm liegen unter den für diese Ablage
genehmigten 50 mm. Die Offline-Prüfung deckt das reguläre Öffnen aus dem
Griff ab. Die Robotiq-Aktivierung fährt durch die mechanischen Endlagen
und braucht eine gesonderte Freigabe mit freiem Fingerweg. Bis zur
Entlastung und Freigabe der Fingerwege vor Ort wurde keine Aktivierung
ausgelöst. Befunde unter
`setup/tasks/return_home_20261126/commissioning/open-failure/`.

Bei der Fortsetzungsprüfung um 13:03 AWST sind beide Greifer weiter
inaktiv (ACT=0, STA=0, FLT=0), unverändert bei POS=226 und POS=224.
OAK4 zeigt den Karton weiter im Griff. Kein offenes Review, keine
aktiven Armziele, kein vom N100 gemeldeter geometrischer Konflikt.
Foto unter `setup/tasks/return_home_20261126/commissioning/continue-crymhv_2/`.
Die reale Einzelaktivierung links hinten vom 25.11. enthält POS=0 vor
dem Schließen bis zum beobachteten POS=230 und endete bei POS=165.
Die Rückmeldungen belegen einen Schließhub im Kalibrierzyklus und
keinen Gleichlauf für zwei Geräte. Mit dem Karton zwischen den Backen
blieb die Fortsetzung lesend.

Bediener hat den Karton mit einem Buch abgestützt und die Aktivierung
beauftragt. Das neue OAK4-Foto zeigt die Unterlage und die beiden
Kartonwände weiterhin zwischen den Backen. Register und Schutzstatus
entsprechen der vorigen Abfrage. Für die Bergung vor Ort Robotiq **E-Open**
am jeweiligen Teach Pendant verwenden, bevor mit freiem Fingerweg die
Aktivierung über ROS erfolgt. Das Handbuch beschreibt E-Open als langsames
Öffnen mit geringer Kraft auch im inaktiven Zustand. Diese Funktion ist
nicht Teil der eingesetzten ROS-Greifer-API. Kein Aktivierungs- oder
Fahrbefehl gesendet. Foto unter
`setup/tasks/return_home_20261126/commissioning/supported-ow4w00fr/`.

Bediener meldete die Bergung erledigt. N100 um 13:12 AWST bestätigt für
beide rechten Greifer ACT=1, STA=3, FLT=0, POS=3, PRE=0 und Leerlauf.
Die Greifer sind bereits aktiv und offen. Das neue OAK4-Bild zeigt den
abgestützten Karton mit geöffneten Backen. Schutzstatus ohne gemeldeten
Konflikt, kein aktives Armziel oder offenes Review. Kein weiterer
Aktivierungs- oder Fahrbefehl gesendet. Foto unter
`setup/tasks/return_home_20261126/commissioning/cleared-oqv399zf/`.
Für die anschließende Rückfahrt die abgestützte Kartonlage und den
freigegebenen Arbeitsraum aktuell berücksichtigen.

Bediener beauftragte anschließend die Rückfahrt. Für das Buch und den
abgestützten Karton wurde aus der aktuellen OAK4-Aufnahme und der
bisherigen Kartonregistrierung eine stationäre Modellhülle verwendet.
Der Bildvergleich mit unveränderten Tischreferenzen ergab für fünf
Kartonmerkmale 0–5 px Verschiebung bei 1600 px Bildbreite. Die Hülle
beansprucht 10 mm zusätzlich je Seite und deckt Tischhöhe bis 23 mm
über der bisherigen Kartonbasis ab. Die Zugabe ist eine konservative
Modellannahme, keine Messung der Buchdicke. Aus frischen Vierarmständen
bestehen der gemeinsame senkrechte Rückzug um 150 mm (6,72 s) und der
gemeinsame Homeweg über die aufrechte Zwischenstellung (46,92 s).
Modelle, Foto, eingefrorener Plan und Prüfergebnisse unter
`setup/tasks/return_home_20261126/commissioning/open-recovery-xzBw30Q4/`.
Beide Greifer vor dem Review erneut offen und fehlerfrei bestätigt.
Beide Bahngruppen mit bildgebundener Evidenz in einem **Motion Review**
`7bacce5cb4c2419b9a5918f36a901661` auf N100. Freigabe am Bedienplatz.

Dieses Review wurde um 13:18:49 AWST freigegeben. Nach 41,6 s ohne
ausgewiesene UWA-Pause fehlte die Rückmeldung für den vorgesehenen
6,72-s-Rückzug. Beide Ziele waren vom Controller akzeptiert und blieben
nach dem Abbruch zunächst aktiv. Beide Arme waren zu diesem Zeitpunkt
innerhalb 0,006° der jeweiligen Startstellung. Kein Kollisionskonflikt,
Homegruppe nicht gesendet. Der Bediener meldete, dass **Play** an den URs
zunächst nicht gedrückt war. Nach Play liefen die verbliebenen Ziele ab.
Bei der gezielten Stornierungsabfrage war das vordere Ziel bereits beendet,
das hintere endete vor Bearbeitung des Stornos (Rückgabecode 3). Danach
beide ohne aktive Ziele und innerhalb 0,004° am vorgesehenen Rückzugsende.
Positionsnachweis in `after-play.json`, Stornierungsabfrage und alte
Ergebnisse im gleichen Laufordner. Der zweite Plan enthält nur die
verbleibende gemeinsame Homefahrt. Beide rechten Dashboards meldeten
vor dem neuen Review RUNNING/NORMAL/PLAYING `ros.urp` mit nativer Skalierung 1.
Neue Nachweise unter
`setup/tasks/return_home_20261126/commissioning/home-after-play-4FttPjme/`.

Home-Review `d669d28265274d87ad494597d0f85e92` vom Bediener freigegeben.
Um 13:26:40 AWST Home von beiden Controllern bestätigt, Review `done`.
Die separate N100-Endabfrage ergab höchstens 0,000060 rad (0,0035°)
Abweichung vom jeweiligen Homeziel, gemeldete Gelenkgeschwindigkeit 0,
keine aktiven Armziele, beide Greifer ACT=1/STA=3/FLT=0/POS=3 und keinen
aktuellen FCL-Konflikt. Die Greiferfreigabe erfolgte vor Ort und war keine
erfolgreich ausgeführte automatische Ablage. Der Aufgabenrunner bindet
das Szenenfoto an die eingefrorene Revision. Künftige Return-to-Home-
Zeitüberschreitungen versuchen, ausschließlich die eigenen Ziele dieser
Bahngruppe zu stornieren und quittierte Stornos zu protokollieren. Diese
Fehlerbehandlung ist lokal mit 42 Tests geprüft und wird mit dem nächsten
normalen Aufgabenlauf übertragen.

Der Aufgabenrunner liest jetzt vor den Öffnungsbefehlen einmal den Status
aller Mitglieder der Griffgruppe parallel. Wenn ein Greifer seine
Bereitschaft nicht bestätigt, enthält der Phasenbericht den Fehler je Arm
und die Gruppe erhält keinen Öffnungsbefehl. 41 isolierte Return-to-Home-
und Motion-Review-Tests bestanden. Die Korrektur wird beim nächsten Lauf
mit dessen Aufgabenrunner übertragen.

## RTDE-Zeitzuordnung im N100-Minimalbetrieb, 26.11.2026

Nutzer genehmigte die Korrektur samt möglicher zusätzlicher Rechenzeit pro
Paket und meldete, dass es zum gespeicherten Ereignis links vorne keine
tatsächliche Kollision gab. Im aufgezeichneten 18-s-Fenster lag die
Empfangszeit aktuell, während links vorne das alte Quellalter rund 3 s
betrug. Offline-Replay desselben Fensters mit laufbezogenem Zeitabgleich
ergibt links vorne höchstens 70,2 ms. Vier C++-/Mock-Prüfungen auf N100
bestanden, einschließlich dauerhaft verspäteter und zurückspringender
Zeitstempel sowie kleiner Uhrdrift.

Aktiv im dauerhaften `uwa-minimal-protection.service`, Invocation
`6374c97cee93499dbdc466037020fa7f`. Nur Schutzprozess und zugehörige
Quellen ausgetauscht. Gleiche Kollisions- und URCL-Bibliotheken, bestehende
0,2-s-Quell-/Empfangsgrenze. Der neue Abgleich beginnt pro ausgehandeltem
RTDE-Stream, verwirft unplausible Zeitfolgen und korrigiert innerhalb des
Latenzfensters bis 1 ms je Sekunde. Kein zusätzliches Netzpolling.

Beim Wechsel alle vier Controller pausiert und ohne Ziele. Größte Differenz
vorher/nachher 0,00006568 rad. Software-Pause erneut bestätigt, kein Resume
und keine Fahrt. Die unmittelbare Aktivierungsprüfung meldet für alle
Arme verfügbare Kollisionsdaten und keinen aktuellen Konflikt.
Über 30,45 s und 597 Zustandsmeldungen blieb das größte Quellalter links
vorne bei 48,0 ms und über alle Arme bei 50,4 ms. Sämtliche 596
Statusmeldungen bestätigten die Software-Pause, verfügbare Kollisionsdaten
und keine Kollision. Die größte beobachtete Gelenkspanne war 0,000176 rad.
Rücksicherung auf N100 unter `review-candidates/rtde-clock.I818quMn/`.
Nachweise unter `setup/tasks/return_home_20261126/rtde-clock/`.

Erneute 3-mm-Kartonprobe in Motion Review
`6816a825dd72491e84bce1b0cb66a930` nach Bedienerfreigabe und Resume um
12:46:55 AWST erfolgreich. Aus den Encoderständen abgeleiteter Absenkweg
2,968 mm vorne und 3,001 mm hinten. Größter beobachteter relativer
Vertikalversatz in jeweils 14 Stichproben 0,104 mm. Beide Greifer halten
weiter. Das ist ein Nachweis für diesen kurzen Schritt. Daten unter
`setup/tasks/return_home_20261126/commissioning/after-clock/` und
`settled-after-clock/`. Die Fortsetzung nutzt den frischen Endstand.
Eine erste Freigabeanfrage für die Fortsetzung wurde vor jedem Befehl zurückgezogen,
weil Hydrogens direkte Homewege nur seriell bestanden. Der Compiler prüft
seither weitere Wegvarianten auf gemeinsame Fahrt, bevor er seriell plant.
Die neue Fortsetzung hat ca. 16 mm berechneten Restspalt, geprüften
senkrechten Rückzug und eine gemeinsame Homegruppe über die aufrechte
Zwischenstellung. Öffnungsreview `a4ef61404c954c1da568e76aac7fb426`
ab 12:52 AWST bei Aufgabenvertrauen `Unsure`. Artefakte unter
`setup/tasks/return_home_20261126/commissioning/release-parallel-after-clock/`.

## OAK-Rohrhalter und mobile Boardaufnahme, 26.11.2026

- Linke USB-OAK-D Pro in der gemeinsamen Gazebo-/RViz-Darstellung mit
  aus dem Lieferpaket exportiertem Kameraträger und Rohrschuh, Ø19-mm-Mast
  und vorhandenem Tischfuß. Nutzer bestätigt Veranschaulichung ohne
  separate Kalibrierung und vorläufig abgeleitete Lage. Optik, Intrinsics,
  TF und Sensoreinstellungen wie bisher. Im Standardmodell etwa 60,16°
  abwärts, 1.227 mm Anschlagabstand, Achse 7,9 mm innerhalb der
  nominalen Tischkante. Mögliche ca. 12 mm Überkante am Fuß dokumentiert.
  [Daten und Vorschau](hardware/oak_d_pro_left/README.md#visualisierung-des-aufgebauten-halters-2026-11-26)
- Zwei Lyrical-Pakete gebaut, vier Visuals im laufenden Gazebo-Modell
  nachgewiesen. RViz verwendet dieselben Extrakte aus SDF. 16 vorhandene
  Offline-Tests bestanden. Der Test zur vollständigen rechten
  Tischabdeckung scheitert im nominalen Layout auch mit den Dateien
  des Ausgangscommits. Keine neue Laufzeitprüfung.
- [Rechter Halter](hardware/oak_4d_right/README.md) als parametrische CAD-
  Baugruppe und acht geschlossene Druck-STLs einschließlich Tischlehre.
  Überwiegend gedruckte Klemmung über zwei M8-Zugstangen und Stahl-Gegenplatte,
  lange Ø19-mm-Rohrführung, Drei-Punkt-Anlage und lösbarer oberer Slider
  fürs mobile 450 × 360 × 3-mm-Board. M4-Kameraträger am OAK-4-D-
  Hersteller-CAD geprüft. Kandidat bei 60° mit 1.270-mm-Rohr kommt auf
  ca. 2,10 m optische Höhe. Ideale Projektion zeigt beide bestehenden
  festen Muster im Bild. Physische Passung, Steifigkeit, Kabel und
  spätere Kameraregistrierung stehen aus.
- Dritte Kamera ist laut Nutzer angekommen. Ihr Einbau und die
  Einmessung des mobilen Boards zur relativen Tischmessung folgen separat.
  Seitlicher Boardanschlag bleibt separat.

## Object scan und Asset Library, 26.11.2026

- `object-scan-v1` im bestehenden Loopback-Webserver von **UWA Robot Power**.
  Scan-Sitzungen speichern Originale, Gerätemetadaten, Auflagenotizen,
  strukturierte Gemini-Vorschläge, revisionsgebundene Bedienentscheidungen
  und Abdeckung. Die Asset Library unter den Programmen zeigt suchbare
  Entwürfe und ihre Quellen. [Bedienung](docs/object_scan_library.md)
- Erste OAK4-Ansicht als ausgerichtetes RGB-D, weitere als native Fotos.
  OAK Pro nativ und Wrist-Snapshots separat auswählbar. Gemini Hydrogen
  erhält verkleinerte Bilder nur auf ausdrückliche Browseraktion. Metrische
  OBB ist eine vorläufige lokale OAK4-Schätzung im optischen Kameraframe.
  Abdeckung benennt beim Holzbalken sechs Flächen und fehlende Ansichten.
- Quader als GLB/OBJ/STEP aus Bedienermaßen oder vorläufiger RGB-D-Schätzung
  exportierbar. Fotoquellen pro texturierter Fläche an den Originalhash und
  vier bestätigte Bildpunkte gebunden. Andere Formen können als Datensatz
  mit Abdeckungsbericht gespeichert werden.
- 25 gezielte Softwaretests bestanden. Chrome-Ablauf am isolierten
  Library-Server einschließlich Aufnahme, Vorschlagsrevision, Flächenprüfung,
  Texturzuordnung, echtem GLB-Export und mobiler Ansicht bestanden. Kamera und
  Gemini im Browserszenario simuliert. Simulierter Altserver-Katalog bleibt
  ohne Scan-Routen bedienbar. [Browsernachweis](work/object-scan-web-20261126.md)
- Zwei getrennte Aufrufe am konfigurierten Gemini Hydrogen über Antigravity
  mit ausschließlich synthetischem Balkenbild bestanden. Identifikation
  meldete `found`. Die Abdeckungsprüfung lieferte sechs Flächen und `more_views`.
- Erste reale Ansichten am 26.11. um 15:43–15:44 AWST. Nutzer meldet
  Balken auf dem linken Tisch, ungefähr 70 × 30 × 1.100 mm. **Holzbalken –
  linker Tisch**, Sitzung `e6fa878e0efe44d0aefbc0e4186ca121` unter
  `setup/tasks/uwa_program_library/object-scans/`: OAK4 RGB-D (1280 × 960),
  OAK Pro nativ (4056 × 3040) und OAK4 nativ (8000 × 6000). Originale
  und Vorschauen dekodiert und gegen ihre Dateihashes geprüft. Balken
  liegt parallel zur Tischkante. Die Aufsicht der OAK Pro zeigt die
  Oberseite am besten. Arme verdecken je nach Ansicht einen Endbereich.
  Lokale Sichtprüfung, reine Kameraaufnahme während laufender Zellarbeit.
- Vollständiger Scan und ausführbarer Greif-/Präsentationspfad stehen aus.
  Dafür fehlen verifizierte Zellpose, Kontakte und Last sowie offline
  geprüfte Bewegungen und für aufrechtes Umgreifen die Lastübergänge.

## Return to Home, 26.11.2026

Nutzer meldet 19 mm Restspalt und erlaubt für den aktuellen stabilen
Avocado-Karton bis 50 mm Fallhöhe. Profil bindet diese Ablage an den
Grifflauf, verwendet 5 mm Planungsannahme zur Messunsicherheit und
bewertet Öffnen nach bestandener Fallraumprüfung als **low**. Der
senkrechte Rückzug wird ebenfalls **low**, wenn die aufgeweitete
Landehülle geprüft ist. Neue Objekte haben eine Eingabe für die Fallhöhe.

Einmalige 3-mm-Realmessfahrt für beide rechten Arme in **Motion Review**
`f0bd4b31bcd140568e4f0ea858469c87` vom Bediener freigegeben. Der N100
beendete die Phase vor dem ersten Fahr- oder Greiferbefehl wegen einer
bestehenden Softwarepause. Keine Gleichlaufmessung dieses Realschritts.
Aus dem erwarteten Endzustand sind 16 mm Restspalt, Fallraum, offene
Rückfahrt und Home offline geprüft.

Safety Log: Die Kollisionspause stammt von 10:31:52 AWST und betrifft
links vorne (Handgelenk/Greifer) gegen rechte Tischplatte, FCL-Kontaktgrenze
0 mm. Neu eingelesene vier Gelenkstände bestehen sowohl MoveIt als auch
das installierte C++-Replay. Der Live-Kern behält den gespeicherten
Konflikt bei fehlenden gültigen Daten für links vorne. Die sechs
passiven Zustandsmeldungen zeigten 19–29 ms seit Empfang, aber
3,062–3,072 s berechnetes Quellalter bei 0,2 s Grenzwert. Zeitzuordnung
prüfen und die aktive Ursache vor erneuter Ausführung klären.
Kein Resume und keine Änderung am Schutzdienst. Der Aufgabenrunner
meldet den bestehenden Konflikt künftig vor der Review-Anfrage.

**Force-based placement** hat eine langsame Offline-Vorschau, reale
Lastübergabe mit Schaumstoff ist noch nicht qualifiziert. Daten unter
`setup/tasks/return_home_20261126/commissioning/`.

Library-Programm, Hydrogen-Beratung und Motion Review für Griffgruppen
mit einem bis vier Armen ergänzt. Bedienung und Nachweis in
[Return to Home](docs/return_to_home.md).

Aktueller Vierarm-Start passiv auf N100 gelesen und portabel an das
ROSmini-Kollisionsmodell gebunden. Hydrogen priorisierte die aufrechte
Zwischenpose vor der Basisdrehung. Gegenprüfung aus diesen Gelenken:
beide rechten Arme zusammen, 54,74 s modellierte Gesamtfahrt, 83,5 mm
Nachbarabstand-Untergrenze in der Homegruppe. Direkte Homepfade bestehen
seriell, 74,53 s Gesamtfahrt. Erst rund 20 mm gemeinsam absenken und nach
dem Öffnen 150 mm senkrecht zurückziehen. Der Karton steht in der
historischen Ablage über der Lücke auf beiden koplanaren Platten.

Lageunsicherheit am Aufsetzpunkt und gemessener belasteter Gleichlauf
der rechten Gruppe fehlen für die reale Ausführungsfreigabe. Der frühere
Hub bestätigt Endzustand und Lastschätzung. Für diesen Pilot keine
Bewegung und keine Greiferbefehle. Dateien unter
`setup/tasks/return_home_20261126/`.

## Holzrahmen in Browser und Gazebo, 25.11.2026

Zwei rechte URs tragen den Querbalken gemeinsam. Links hinten fährt parallel
zur Vorposition und setzt je zwei axiale Werkzeugzyklen an beiden Pfosten.
Links vorne bleibt geparkt. Die simulierte Vorrichtung verwendet 340 mm
Pfostenabstand, um beide Schraubzugänge mit der 40-mm-Nachbararmmarge zu
erreichen. Bedienung und Rezept in [Holzrahmen-Demo](docs/wood_frame_demo.md).

Browser-Nominalfall und 5°-Variante aus markerlosen synthetischen Bildern
bestanden. OAK Pro lieferte den Fit bei teilweiser Verdeckung der ersten
Ansicht. 26 Phasen, 48,49/49,10 s Modellzeit, jeweils 3,57 s gemeinsame
Aktivbewegung der drei Arme. Nachweise mit Sechs-Paar-FCL, Bild-Overlay und
Chromewiedergabe vorhanden. Bei vollständiger Verdeckung ergab die lokale
Messung keine Pose. Gemini 4 Hydrogen Low bestätigte sie anhand eines
synthetischen Bilds. Der Suchfenster-Nachmesspfad ist zusätzlich mit einer
lokalen Modellantwort geprüft.

Nach Nutzerhinweis die Browser-Verdeckung an beiden Verbindungen korrigiert.
Die Darstellung ordnet überlappende Holzflächen anhand ihrer Ebenen im
gewählten Blickwinkel. Der Querbalken verdeckt beide Pfosten von der
Schraubseite, von hinten gilt die umgekehrte Reihenfolge. Im Chrome-Vergleich
2.910 überlappende Bildpunkte mit unabhängigen Sehstrahlen geprüft, von
670 falschen Zuordnungen auf null. Beide Viewer und die Browserreferenz
aus den bestehenden geprüften Plänen neu exportiert.

Gazebo-Kontaktlauf `gazebo-contact-03` an die erste bestandene Browserbahn
`browser-gazebo-reference` gebunden. Alle vier Pads bestätigten Aufnahme,
26 Phasen vollständig, vier virtuelle Schrauben, ideales Gazebo-Festgelenk
bestätigt. Balkenpose nach Öffnen und Rückzug unverändert, 0,83 mm und
0,39° vom Soll. 68,66 s Simulationszeit. 500 kg/m³ Modelldichte und 1,0
Padreibung sind Simulationsannahmen. Ergebnisse und lokales Gazebo-Overlay
unter `setup/tasks/wood_frame_20261125/`. Quellstand der aktiven N100- und
Simulationsdienste erhalten. Die reale Stufe wartet auf die Werkzeug- und
Montagevermessung samt eigener Inbetriebnahmefreigabe.

## Stiftfreigabe angekommen, Resume-Übergang korrigiert,25.11.2026

Lauf `52befffcfa974f6390b4658d081ae7d4` scheiterte vor der ersten Bewegung
mit `left_rear: trajectory rejected`; keine Einfahrt/Greiferbefehle.
Bediener-Approved16:34:56 korrekt. Resume16:35:38,148; gemeinsame RUNNING-
Antwort16:35:38,180 noch mit alter pausierter left_rear-Quittung/Faktor0.
Alle Quittungen erst16:35:38,315 bestätigt; Reviewfehler unmittelbar danach.
Starker Quell-/Zeitnachweis für Zielversand vor lokaler Resume-Zulassung;
genauer lokaler Sperrwert beim Goalcallback nicht als Einzelprobe vorhanden.
Aktuell RUNNING/NORMAL, keine gemeldete Kollision und alle Controller bestätigt.

Nur Stift-Aufgabenhelfer/Runner korrigiert: vor nächstem Armkommando vorhandene
Resume-Quittung derselben Generation und fertige Rampe links hinten anhand
bereits abonnierter Daten abwarten. Kein zusätzlicher RPC/Wächter, kein
automatisches Resume/Retry, keine Tempo- oder Schutzprogrammänderung. Zustand
wird im Lauftext ausdrücklich angezeigt.29 gezielte Offline-Tests bestanden.
Neuer normaler Library-Lauf mit frischen Eingaben:
`060e937a67c346d2b04263e86998a365`, Start16:42:36AWST. Neue Reviews verfolgen;
keinen zweiten Stiftlauf parallel starten. Details:
[Resume-Zulassung](work/pen-resume-admission-20261125.md).

Review `0d0d013960714d27b08f67239c3be286` wurde freigegeben;
Anfahrt und offene Einfahrt abgeschlossen. Nutzer brach wegen verbleibendem
Versatz nach rechts im Wristbild ab und stellte den Stift um. Alte offene
Kontaktfreigabe zurückgezogen; Arbeitsbereich danach ausdrücklich erneut
freigegeben. Frische OAK-Pro-Auswertung scheitert an Kabelverdeckung von
Marker97; kein erneuter Greifschluss oder Hub des Stiftprogramms.

Nutzer beauftragt getrennt+100mm senkrecht nach oben, um das Kabel zu
entfernen. Vollzellgeprüfte Bahn5,544s, unveränderte Orientierung und Tempo,
Greifer offen. Genau ein Ziel angenommen, dann Client-Zeitüberschreitung:
native UR IDLE/PAUSED ros.urp/Skalierung0, UWA selbst RUNNING ohne Kollision.
Kein Hub gemessen; das Ziel bleibt im Controller aktiv. Keine zweite Bahn,
keine Power-/Brake-/Play-Befehle. Nutzer erlaubt nun ausdrücklich Brake
Release/Play, mit Vorrang für den parallelen Kartonprozess. Fortsetzung
durch bestehende Library-Sperre zurückgestellt: neuer Kartonlauf
`7d124f9a84e54252b3d7e0261e7ad981` benötigt die Roboter. Helfer nicht
gestartet, keine nativen Befehle. Vor späterer Fortsetzung alle Startgelenke
neu vergleichen und bei geänderter Szene erneut offline prüfen.
Details: [100-mm-Hub](work/pen-up100-20261125.md).

## Kamerübergreifende Winkelgrenze3° genehmigt,25.11.2026

Nutzer bestätigt ausdrücklich3° als ausreichend. `carton_multiview.py`
akzeptiert nun bis einschließlich3° (nur numerische Rundung an der Grenze),
bei weiterhin30mm Zentrum, unveränderter OAK4-Pose als alleiniger metrischer
Quelle und gleicher180°-Symmetrie. Einzelbildkriterien unverändert.
Keine Änderung am N100-Schutzprogramm, Controllern oder Geschwindigkeit.
36 gezielte Prüfungen der3°-Grenze bestanden. Neuer Library-Lauf
`1adaf627563c4e259db7f2352923bfb9` bestand den aktuellen Kameravergleich
14,119mm/1,40528° mit unveränderter OAK4-Pose; keine Bewegung. Danach
`NO_CHECKED_PATH_FOUND`, start_valid=false, keine Suchversuche. Exakte
Offline-Diagnose: primäres volles Zellmodell frei; die zusätzliche statische
Kartonhülle überschneidet die volle Öffnungshülle eines RF-Fingertips, obwohl
beide rechten Greifer bestätigt offen sind. Kein Nachweis einer aktuellen
realen Arm-/Tischkollision daraus ableiten.

Aufgabenfix: Nur in diesem Startfall zusätzlich offene rechte Greifergeometrie
gegen den Karton prüfen, UND das unveränderte primäre volle Öffnungsmodell
gegen Zelle/Arme/Tische. Linke Greifer behalten auch im Zusatzmodell volle
Hüllen. Keine Robot-/Kartonkontakt-Ausnahmen ergänzen. Neun Originalmeshes
separat hashen/stagen/präzise auf N100 nachweisen. Review bindet vor der hohen
Anfahrt reguläre Aktivierung/Öffnung an den aktuellen tischgestützten Start;
falls diese Vorbereitung nicht bestätigt ist, keine Armfahrt. Alte Starts
mit vollständig freier Öffnungshülle behalten ihre Vorbereitung nach high.
Keine zusätzlichen Laufzeitwächter, kein Safety-Core-/Controllerupdate.

Vollständige Folge mit den gespeicherten aktuellen Eingaben erfolgreich:
`setup/tasks/carton-weigh-20261125/open-start-plan/`; high7,26076s,
entry7,61427s, Hub1,15206s, beide Arme in jeder Phase gemeinsam. Alle
unveränderten Geschwindigkeits-/Kollisionsgrenzen erhalten.113 gezielte
Offline-Tests bestanden (einschließlich UND-Verknüpfung beider Kollisions-
modelle, Erhalt fremder Körper, Meshbindung und richtiger Open-Befehlsfolge).
Vier Taskdateien versionsgeprüft mit Sicherung auf N100 installiert,
keine Dienste neu gestartet. N100-Dateiprüfung erfolgreich:60 gebundene
Dateien/Ressourcen, offene Startkonfiguration im tatsächlichen Aufgabenlader
frei, high und Hub jeweils eine gemeinsame RF/RR-Gruppe. Beleg
`n100-resume/open-start-n100-check.log`. Keine Arm-/Greiferbefehle aus dieser
Dateiprüfung.

Der anschließende normale Startversuch wurde vom Library-Server ohne neuen
Kartonlauf abgelehnt (`Another library run is already active`). Andere
Aufgabe: `060e937a67c346d2b04263e86998a365`, Pick pen from holder,
seit16:42:36AWST, Phase Motion Review vor der Fahrt. Nicht abgebrochen oder
freigegeben. Nutzer nach Reihenfolge gefragt: Stift beenden und danach Karton,
oder wartenden Stiftreview ausdrücklich ablehnen und Karton vorziehen.
Kartonfortsetzung erst nach freier Library mit frischer Wahrnehmung/Snapshot.

Nutzer entscheidet anschließend ausdrücklich: Karton fortsetzen, Stift soll
im Zweifel warten. Beim aktuellen Lesen war der Stiftlauf bereits vor
Kontakt beendet (`Review already interrupted`, Ende16:54:25AWST); kein
Stiftreview verändert und kein laufender Auftrag abgebrochen. Aktueller
Kernstatus RUNNING/OPERATOR RESUME, vollständige Kollisionsdaten, keine
Kontakte/Warnungen, vier bestätigte Controller Faktor1 ohne aktive Actions.
Die zwischenzeitliche Resume-Freigabe wurde in der Stiftarbeit bereits
umgesetzt; hier kein weiteres Resume gesendet. Neuer normaler Kartonlauf
`fa0bf4688408463487045dba0f6bac42`, Start17:02:03AWST, scheiterte17:02:11
bereits in External-Control-Vorbereitung: right_front `ros.urp PAUSED`.
Keine neue Bildaufnahme, Kartonfahrt oder Wiegehub in diesem Lauf.

Diagnose17:04–17:09AWST: Safety-Report ohne neuen geometrischen Stopp.
GUI-Audit zeigt16:49:42 für alle vier URs `ROBOT_EMERGENCY_STOP`,16:49:47
wieder NORMAL, Programme weiter PAUSED. Wiederholte Start+ROS-Bedienung
16:50/16:52 wurde ohne Befehle wegen PAUSED abgelehnt. Aktuelle native
Lesung bestätigt rechts IDLE/NORMAL/PAUSED, links vorne POWER_OFF, links
hinten IDLE. Quelle des Not-Aus nicht aus dem Audit beweisbar; keine
gemessene Kollisions-/Geschwindigkeitsgrenze als Ursache vorhanden.
Softwarekern RUNNING ist davon getrennt und kein nativer Bereitschaftsnachweis.
Belege `setup/tasks/carton-weigh-20261125/n100-resume/`:
`safety-priority-report.json`, `native-priority-status{,-02}.json`,
`live-status-priority.json`. Kein Stop/Power/Brake/Play aus dieser Diagnose.
Konkrete Freigabe angefragt: Arbeitsbereich nach Not-Aus frei, beide rechten
pausierten Programme regulär stoppen, Start+ROS, danach frische Kartonplanung
und normale Reviews. Nutzer hat anschließend ausdrücklich zugestimmt.
17:15AWST beide rechten Programme korrekt identifiziert, NORMAL/IDLE,
keine rechten Ziele aktiv; je ein reguläres Stop bestätigt, danach über
bestehenden Starthelfer Brake Release/Play erfolgreich. Beide RUNNING,
PLAYING, Reverse verbunden. Keine Treiber-/Schutzdienständerung, keine
Greiferbefehle in dieser Vorbereitung. Links hinten wartet fremder100-mm-
Auftrag UUID9a880049… bei nativ PAUSED; linke Arme daher ausdrücklich nicht
vorbereitet/resumiert. Beleg `n100-resume/restart-right-approved.jsonl`.
Neuer normaler Library-Lauf `7d124f9a84e54252b3d7e0261e7ad981`,
Start17:15:54AWST. Nur diesen verfolgen, keine parallelen Kartonstarts.
Frische Zweikameraprüfung erfolgreich11,776mm/1,3981°, OAK4 weiterhin1/0.
Komplette Folge einschließlich gemeinsamem20-mm-Hub1,15406s offline geprüft.
Motion Review `712adf9b817c407a9a419d6d81eb4d54`, SHA
`08728c03bd892156a37bfb19aecf4e9215ef3005084bbd9e9fb888b79ad5750d`,
wartet auf ausdrückliche Freigabe der neuen hohen Anfahrt/offenen Einfahrt
14,98546s. Neuer Griff20mm höher als bisher, daher high risk trotz Vertrauen100.
Noch keine Kartonbewegung/kein Greifschluss; Kontakt/Hub erst nach frischem
Einfahrbild. Konkrete Chatfreigabe dieser Revision angefragt, nicht erteilt
oder als GUI-Klick dargestellt.
Kamerareferenzen
weiter gültig bis26.11.03:19AWST, sofern Kamera/Board nicht verstellt wurden.

Historischer Zwischenstand vor dem oben belegten Resume: Die Zelle war nach
dem unabhängigen Stift-Fehlgriff wieder OPERATOR PAUSE.
Die frühere Resume-Freigabe wurde bereits vor diesem erneuten Stopp verwendet;
diesen neuen manuellen Stopp nicht eigenmächtig aufheben. Vor tatsächlicher
Fortsetzung aktuelle Arbeitsfläche und ausdrückliches Resume/Review klären.

## Stiftfahrt: seitlicher Fehlgriff und Symmetrie,25.11.2026

Nutzer meldet nach Lauf `a49718ebcac64a849d218afb8c618704` mehrere Zentimeter
seitlichen Fehler bei plausibler Höhe sowie unnötige Handgelenksdrehung.
Anfahrt/Einfahrt wurden nach Bedienerreview ausgeführt. Kontaktreview wurde
ebenfalls angenommen; bei der Diagnose waren Schließen und Hub schon beendet.
Workflow `PEN_LIFT_COMPLETED` bedeutet hier **keinen bestätigten Stiftgriff**:
Schließresultat contact_detected=false, OBJ3/POS227/PRE255/FOR0/SPE16.
Auf ausdrückliche nachträgliche Nutzerfreigabe alle vier Arme pausiert;
PAUSED/OPERATOR PAUSE, vier pausierte/bestätigte Controller ohne aktive Action.
Keine weitere Greifer-/Armfahrt oder ein Resume durch diese Diagnose.

q6-Anfahrt tatsächlich+174,603°. Ursache im Aufgabenplaner: erste gültige
Symmetrie genommen. Jetzt beide Orientierungen vor vollständiger Bahnprüfung
nach Gelenkweg vorreihen. Offline mit gleichem archiviertem Start und altem
Kamerabezug vollständige gültige Alternative−5,397°,17,759s statt73,132s;
unverändert0,1rad/s, keine Tempoerhöhung oder Kollisionsausnahme.

Referenzgegenprobe im Einfahrbild: rechter Boardbezug konsistent (0,740px),
am linken Board83,817px Projektionsfehler. Unabhängiger linker Fit mit17
Markern/0,403px Prüf-RMS ergibt für den Stift ungefähr40mm seitliche
Änderung bei1,4mm Höhe. Ähnlicher Befund bereits im Bild vom24.11.
Modellinterne Ist-Tool0-Abweichung zur angefahrenen Sollpose nur0,048mm;
dies ist keine absolute externe Genauigkeitsmessung. Übernommene Basen
unverändert. Nutzer bestätigt anschließend ausdrücklich: linkes Board weder
bewegt noch verändert; Fortsetzung beauftragt.

Aktuellen linken Boardfit im Stiftcompiler vorbereitet und nach dieser
Bestätigung in der Programmdefinition mit `reference_board=left` aktiviert.
Entwurf mit demselben alten
Start vollständig offline geprüft:20,155s, q6−12,512°, Zieländerung
[−40,118,−4,348,+3,187]mm. Keine Ausführung dieses archivierten Entwurfs.
Neue Eingaben/Planung vom tatsächlichen Zustand und normale Reviews folgen.
Aufgabenlogik
beendet leeres Schließen jetzt vor dem Hub mit `NO_OBJECT_CONTACT`, ohne
zusätzliche Abfragen, Wächter oder gemeinsame Stopps.23 gezielte Tests
bestanden. Keine Änderung am Sicherheitsprogramm. Einzelheiten/Artefakte:
[Stift-Fehlgriff](work/pen-grasp-offset-20261125.md).

Aktueller korrigierter Lauf `52befffcfa974f6390b4658d081ae7d4` gestartet
25.11.,16:23:41AWST nach Ende des belegenden Kartonlaufs. Neue Aufnahme/
Gelenke, linker Boardfit17Marker/0,7198px Prüf-RMS, Penfit1,5929px.
Vollständiger Plan18,3676s, q6-Anfahrt−7,029°, unveränderte0,1rad/s und
0,2rad/s²; aktueller Ausführungshelfer mit leerem-Griff-Abbruch SHA-gebunden.
Review `b0d81aa4580b48b0b8cc4a38e6e1ce1a` wartet auf Bedienung.
Nutzer um Anfahrt-/Einfahrtfreigabe und RESUME gebeten, Kontakt danach erst
anhand des neuen tatsächlichen Einfahrbildes. Kein zweiter Stiftlauf starten.

## N100 wieder erreichbar; Wiegeerweiterung installiert,25.11.,15:05–15:25AWST

Ergänzung15:27–15:38AWST: Nutzer genehmigt den einzelnen Parametervergleich
und danach ausdrücklich generell gezielte SET-Befehle für die Greiferdiagnose.
Der zunächst abgelehnte Vergleich wurde erst danach ausgeführt. Auf derselben
TCP-Verbindung zeigten RF undRR nach genauFOR0/SPE16 jeweils drei stabile
korrekte Rücklesungen; keine ACT/POS/GTO-Befehle in diesem Vergleich.

Transportfix: Ein normaler Greiferauftrag hält nun eine Verbindung für seine
SETs und bestätigenden GETs. Unabhängige Lesethreads behalten eigene
Verbindungen; Verbindung nach Abschluss/Fehler schließen. Keine geänderten
Fristen, Parameterbestätigungen oder automatischen Befehlswiederholungen.
40 gezielte Transport-/API-Tests und81 bestehende Karton-/Reviewprüfungen
bestanden. Direkte Framing-/Lebensdauerprüfung mit fragmentierten Antworten,
falschem ACK und gleichzeitigem separatem Leser. Alte Diagnoseänderungen
im gemeinsamen SDK erhalten. SDK-SHA256 nach Fix:
`a6f9eb336ee3f00ea8d2f3130c8c27d16845958fe2fe880e5ca7adffe6ab1137`.

Vor Installation wurde eine andere laufende Review-Aufgabe erkannt; Abbruch
vor jeder SDK-Änderung. Erst nach deren Ende und bei vier untätigen Greifern
Base- und Kandidatenquellen mit exakten Vorgängerhashes/Sicherung aktualisiert
und nur `uwa-grippers.service` neu geladen; maximale Rohwerte0/16 erhalten.
Schutz-/Armcontroller unverändert. Danach normale ROS-Öffnung beider rechten
Greifer einmal erfolgreich: ACT1/STA3/FLT0/OBJ3/POS3/PRE0/FOR0/SPE16.
Damit aktueller Parametrierungsblocker beseitigt; ein einmaliger Vergleich
allein wäre kein dauerhafter Nachweis gewesen. Hardwarebeleg
`normal-open-with-fixed-transport.json`, Sicherungen `transport-backup/`.

Erster aktueller Library-Lauf wurde noch vor jeder Fahrt am Kameravergleich
abgewiesen:13,304mm Zentrum,2,521° Winkel;30mm erfüllt, striktes<2° nicht.
Begrenzte bestehende OAK4-Nachmessung änderte den Widerspruch nicht; letzte
Hydrogenrunde lief in Timeout. Gesonderte freigegebene USB-/Hydrogen-Nachmessung
ergab weiter2,378°, daher nicht zur Ausführung übernommen. Keine Grenzlockerung.
Anhand des aktuellen USB-Originalbilds engeren Karton-/Wandausschnitt gewählt:
ROI[1400,1350,2800,2600], FaceROI[1500,1400,2700,2050]. Dieselbe native
Standardauswertung besteht damit die bisherigen Einzelbildkriterien und
12,447mm/1,71544° Gegenvergleich. OAK4-Pose exakt unverändert, Gewichte1/0.
Beleg`usb-crop-native/result.json`; Suchfenster in `carton-usb.json` gespeichert,
vorherige Konfiguration gesichert. Kein Genauigkeitsnachweis daraus ableiten.
Neuer normaler Library-Lauf15:49:58AWST mit frischen Aufnahmen/Snapshot:
`26c717534906463d95d90ebe6a75c241`: erneut vor Bewegung am Vergleich
13,348mm/2,311° abgewiesen. Bestehende drei OAK4-/Hydrogen-Runden blieben
bei3,054°; nicht übernommen. Ein zusätzlicher engerer OAK4-Aufdruckcrop
(alle Einzelbildkriterien unverändert) ergab3,010°, ebenfalls verworfen;
primäre Standardfenster deshalb unverändert. Erste erfolgreiche USB-Crop-
Nachmessung ist kein Stabilitätsnachweis für frische Bilder.
Nutzerentscheidung angefragt: explizite alte<2°-Grenze weiter diagnostizieren
oder kamerübergreifend bis3° erlauben; OAK4-Vorrang und30mm unverändert.
Bis zu dieser Antwort keine Winkelgrenze geändert, kein weiterer Live-Lauf,
keine neue Armtrajektorie/kein Wiegehub. Nur diesen weiterverfolgen;
der erste Lauf bleibt als ursprünglicher Ablehnungsnachweis erhalten.

Neuer normaler Library-Lauf gestartet15:37:56AWST:
`f1c17f764e9f4775a32e2ef8f6b426bd`. Verwendet aktuelle Bilder/Gelenkdaten
und aktivierte Wiegevariante; noch keine Greiffahrt/Wiegeauswertung zum
Zeitpunkt dieses Zwischenstands. Weiteren Ablauf anhand dieses Laufs
verfolgen, nicht einen zweiten parallel starten. Frühere Beschreibung des
Parametrierungsblockers im folgenden Abschnitt ist damit überholt.


Nutzer erklärt Routerneustart. Beide eingerichteten SSH-Zugänge wieder
funktionsfähig. Fünf ausschließlich aufgabenbezogene Dateien nach Manifest-
und Vorgängerversionprüfung installiert, einschließlich Paketlink für das
neue Pythonmodul. Sicherung/Beleg auf N100:
`setup/tasks/carton-weigh-install-20261125/receipt.json` in der aktiven
Minimal-Runtime. Kein Safety-/Controllerquellstand oder Grenzwert geändert.

Direktes neues output-only-RTDE-Rezept auf beiden rechten URs erfolgreich:
je41 Pakete/2s, Payload jeweils1kg. `force-recipe-check.json` ist ausdrücklich
**keine unbelastete Referenz**; kein Kartongewicht daraus bestimmen. Erster
N100-Dateiladetest lehnte den Offline-Beispielplan wegen unterschiedlicher
`libur_controllers.so`-Bindung ab. Vorhandenen passenden ROSmini-Prüfstand
`setup/skill_library/n100-checker` verwendet und vollständige Folge neu
geplant, keine bloße Hashänderung. `complete-plan-n100-checker/`,
`staged-n100-checker/`, N100`carton-weigh-qualified-v2/prepared/`:60 Dateien,
alle Ressourcen und tatsächlicher Wiegeplan-Lader erfolgreich überprüft;
keine Ausführung dieser Archiv-Eingaben. Beleg `n100-resume/executor-file-check.log`.

Vorbereitung: Die gemeinsame Quelle veröffentlichte für LF/LR/RR sechs
Nullen und für RF alte Werte. Direktes LF-RTDE zeigte aktuelle Nichtnull-
Winkel; die gemeldeten LF-/Tischkontakte sind daher kein Nachweis einer
aktuellen realen Kollision. Safety-Log zuerst gelesen; Journal zeigt
Netzabbrüche/Wiederverbindungen. Beide hinteren URs waren POWER_OFF.
Nutzer bestätigt aktuelle freie Arbeitsfläche und tischgestützten leeren
Karton sowie Öffnen/Neugreifen; separat Start+ROS, unveränderten Dienst-
neustart im Stillstand und Resume nur nach aktuellen freien Daten genehmigt.
Unser Start+ROS-Aufruf wurde wegen bereits laufender Vorbereitung abgewiesen;
deren anschließender normaler Status bestätigt alle vier ready/PLAYING/NORMAL.
Keinen zweiten Start parallel ausgeführt. Schutzdienst nur bei vier
pausierten bestätigten Controllern ohne Action neu gestartet, Pause sofort
wieder angefordert. Danach vollständige aktuelle Geometrie ohne Kontakte,
explizites Resume. Alle vier quittieren Faktor1, kein Armziel aktiv.
RR meldet weiter die beim Pausezeitpunkt gespeicherte einmalige Inventarwarnung;
seine separate Controllerliste bestätigt den aktiven vorgesehenen Pausable-JTC.
Keine Sicherheitsprogrammänderung zur Warnungsunterdrückung durchgeführt.

Library unter`http://127.0.0.1:8780` taskbezogen gestartet; Browserhost weiterhin
nicht verfügbar, keine GUI-Klicks behaupten. `weigh_after_grasp=true` nach
Installation/Dateiprüfung aktiviert. Neue Kamerakalibrierung über normalen
Library-Endpunkt, Lauf`afe3838f9bd54cbf888fc4756db83926`: OAK4 17Marker/1,42px,
OAK Pro16Marker/1,288px; gültig bis26.11.~03:19AWST. Aktuelles OAK4-Bild zeigt
Karton weiterhin tischgestützt zwischen rechten Greifern. Arbeitsbereich neu
bestätigt, Session`465bb4cc216643a6a8f116b63ad4bf61`; Vertrauen100 und Tempo
33⅓% unverändert.

Aktueller Blocker: normale Öffnung zunächst vor MOVE abgelehnt, weil Greifer
inaktiv waren. Nach regulärer Aktivierung erreichten beide ACT1/STA3/FLT0/
POS3/PRE0, aber die folgende Parameterbestätigung schlug fehl: RF erwartet
SPE16/FOR0, zuletztSPE0/FOR16; RR erwartetFOR0, zuletztSPE255/FOR255.
Kein neuer POS-/GTO-/Armzielbefehl wurde von diesen fehlgeschlagenen MOVE-
Aufrufen gesendet; Aktivierungsbefehle wurden ausgeführt. Originalergebnisse
`release-before-new-grasp.json`, `activate-and-open.json` in den N100-Belegen.
Noch kein neuer Library-Greiflauf oder Wiegehub, kein gemessenes Kartongewicht.

Geplanter eng begrenzter Parametervergleich: einmalFOR0 undSPE16 je rechtem
bereits offenem Greifer auf derselben durchgehend offenen TCP-Verbindung;
keine ACT/POS/GTO-/Armbefehle. Automatische Freigabeprüfung lehnte diesen
zusätzlichen direkten Parametervergleich mangels ausdrücklicher Freigabe ab.
Nicht ausgeführt, keine Umgehung. Konkrete Nutzerfreigabe dafür angefragt.
Weitere Originalnachweise lokal`setup/tasks/carton-weigh-20261125/n100-resume/`
und`n100-artifacts/`. Frühere Installations-/Erreichbarkeitsblocker unten sind
für den Stand ab15:05AWST überholt.


## Erste Tagesinbetriebnahme: verfrühter Pendant-Hinweis,25.11.2026

Heutiges Robot-Power-Log15:17 zeigt bei left_rear und right_rear direkt nach
erfolgreichem `load ros.urp` samt `tobias.installation` kurz
CONFIRM_SAFETY/NORMAL. Bereits15:17:32 wieder POWER_OFF/NORMAL; zweiter Start
ohne erneutes Laden bis15:18:13 erfolgreich. Nutzer meldet keine Änderung oder
Popup am Pendant. Kein Beleg für eine geänderte Sicherheitskonfiguration.
Die Startlogik interpretiert den einzelnen nativen Zwischenzustand zu früh als
manuell erforderliche Sicherheitsbestätigung. Ein täglicher UWA-Prüftimer ist
hier nicht implementiert. Alte Aktionshinweise können als `Last action` bleiben.

Ausdrücklich durch „ja bitte :)“ genehmigte und auf N100 installierte Korrektur:
nur nach eigenem erfolgreichem Laden
CONFIRM_SAFETY/NORMAL im vorhandenen30-s-Startfenster mit bestehendem250-ms-
Abstand auslaufen lassen, danach sofort regulär fortfahren; dauerhafte native
Sperren konkret melden. Zusätzliche Dashboard-Abfragen nur beim Startübergang.
Kein Zusatzsleep im regulären Ladefall.50 gezielte Prüfungen bestanden, inklusive
vollständigem Kaltstart im Double ohne doppelte Befehle und dauerhaftem nativen
Bestätigungszustand ohne Power/Play. Tatsächlich installierte Datei zusätzlich
auf N100 rein im Speicher geprüft; keine echten Roboterbefehle oder Dienstneustarts.
Startskript SHA256 `4cfa159e3a9439851c5d60202f8140727322e220f1d89eac5ecaa38c7e69d0cd`;
Rücksicherung im Kandidaten `validation/first-start-confirm-safety-20261125.t18lm8qd/`.
Backend greift beim nächsten Startaufruf. Neuer sachlicher englischer GUI-Text
liegt lokal bereit; offene Stiftfreigabe erhalten und GUI PID50406 nicht
unterbrochen, Text wird beim nächsten Öffnen geladen. Ein neuer echter Kaltstart
wurde für diese Prüfung nicht ausgelöst.
[Ablauf und Primärquellen](work/ur-first-start-confirm-safety-20261125.md).

## Karton-Kraftreferenz und Wiegehub vorbereitet,25.11.2026

Nutzerauftrag24.11.: Kraftreferenz beider rechten URs vor dem Greifen speichern,
anschließend gemeinsam20mm höher anheben und Lastübernahme/Masse beurteilen.
Nutzer bestätigt leeren Karton, geschätzt500g–1kg, keine präzise Waage. Keine
Referenzmasse oder Genauigkeitsprüfung daraus ableiten. Nach Nutzerpause am
25.11. fortgesetzt. Keine Roboter-/Greiferbefehle für diese Erweiterung gesendet.

Endliche output-only-RTDE-Messung und signierte Kraftdifferenzauswertung in
`carton_weighing.py`, Taskausführung in `carton_weigh_phase.py`. Je Fenster
0,5s Setzzeit und2s bei20Hz, beide Arme parallel. Referenz vor Schließen,
tischgestütztes Fenster nach Schließen, Fenster nach abgeschlossenem Hub.
Payload/COG/TCP-Offset unverändert voraussetzen; Änderungen machen Masse
ungültig. Beide Lastanteile und Streuung ausgeben; keine50/50-Annahme, kein
neuer Wächter, keine globale Pause oder automatische Öffnung/Absenkung aus
Messwerten. Native Sensor-/Payloadkonfiguration, Safety-Kern und Controller
unverändert. Ein abgeschlossener Hub wird bei Messfehler nicht wiederholt.

Offline-Compiler prüft die gesamte Folge vor Anfahrt. Zunächst meldete das
zusätzliche Kartonmodell beim alten Griff Nicht-Pad-Kontakt an inneren
Greifergelenken. Öffnungshüllen als unveränderten primären Zellnachweis und
nominelle Padkontaktgeometrie als getrenntes Aufgabenmodell behandeln.
Auch bei erster nomineller Schließberührung ist der alte Griff nicht frei.
Begrenzte Höhenstudie:10mm höher reicht nicht,20mm höher erlaubt zuerst
modellierten Padkontakt. Separate Entwurfsvariante
`config/carton_programs/carton-supported-weigh-v1.json`: Greifpunkt20mm höher,
übrige Haltungsvorgaben übernommen. Noch kein realer Griffnachweis dieser
Höhe. Anfahrt und Kontakt/Hub verlangen dafür normale explizite hohe Reviews;
kein altes Schrittvertrauen übernehmen.

Vollständige Offline-Folge erfolgreich in
`setup/tasks/carton-weigh-20261125/complete-plan/`, nur Archiv-Eingaben des
24.-November-Laufs. Beide Arme gemeinsam, Wiegehub1,149305077s, unveränderte
0,1rad/s-/83,33mm/s-TCP-Grenzen; bei diesem kurzen Weg bindet0,2rad/s².
Primärer unabhängiger Fortschrittsnachweis mit40-mm-Marge bestanden. Bewegtes
Kartonmodell/Controllerpolynome257-mal geprüft; maximale TCP-Abweichung
<0,42µm im Modell. Nomineller Kontaktwinkel~0,493447rad ist weder gemessene
Öffnung noch Fingerkommando. Anfangs nur sich lösenden Kontakt der5mm nach
unten erweiterten Kartonhülle mit den koplanaren Tischen zulassen; nach Hub
15mm Hüllenfreiheit. Keine Nicht-Pad-Ausnahmen. Reale Padkontakte,
Klemmtragfähigkeit, Schlupffreiheit oder genaue Synchronität nicht behaupten.

Lokal: Zyklusintegration, hashgebundener Transfer, separate Kontaktkomponente
für den Hub, Library-Ausgabe und RViz-Werkstückhub vorbereitet. Option
`weigh_after_grasp: true` wählt die neue Variante. Bisherige Live-Konfiguration
noch unverändert; kein unbemerktes Aktivieren einer nicht installierten Folge.
Lokales Staging `staged/`, `staging.log`; tatsächlicher Dateilader auf ROSmini
in `executor-files-local.log`. Details [Wiegehub](docs/carton_weighing.md).

Offen: Installation und Read-only-RTDE-Formatprüfung auf N100, danach aktueller
neuer realer Griff samt Wiegehub. SSH192.168.8.5 lief in Timeout; separater
vorhandener mDNS-Zugang `miniminiPC.local` nicht auflösbar. Nichts auf N100
geändert. Aktueller physischer Karton-/Zellzustand wurde nicht bestätigt.
Keinen unbelasteten Referenzwert aus dem zuletzt geschlossenen Griff ableiten.
Vor realem Neustart Arbeitsraum/aktuellen Zustand und ggf. reguläres Öffnen
abklären; Kamerareferenzen sind nach12h zu erneuern. Das ist kein neuer
Hardware-Freigabenachweis.81 gezielte Offline-Softwareprüfungen bestanden;
`regression-final.log` im Nachweisordner. Python-Kompilierung und Diffprüfung
bestanden. Lokales Staging umfasst60 gehashte Dateien; der lokale
Dateilader akzeptiert genau eine gemeinsame RF/RR-Wiegegruppe.
UI-/RViz-Änderungen noch ohne neuen Sichtnachweis; ein JavaScript-Parser
stand in dieser Sitzung nicht zur Verfügung. Vor Aktivierung auf N100 den
realen output-only-RTDE-Rezeptaufbau und die Anzeige prüfen.
Geprüfte Kommandospitzen: RF0,074376rad/s und0,199999rad/s²,
RR0,072975rad/s und0,196394rad/s² (`command-extrema.json`).
`deployment-manifest.json` hält genau die noch nicht übertragenen Taskquellen
und ihre Hashes fest.


## Stiftlauf: Greifervorbereitung abgebrochen, Diagnose25.11.2026

Nutzer hat die Diagnose nach einer Pause wieder freigegeben. Der reale Lauf
`7d8b308369e34fd28f14c7b31bca49d7` vom24.11. erreichte mit **left_rear** die
Vorposition erfolgreich, scheiterte danach beim Öffnungsaufruf vor der
vertikalen Einfahrt. Kein Schließen und kein Ausheben. Der Lauf meldete
19:11:19AWST den generischen15-s-Greifer-Timeout; Reviewstore protokollierte
denselben Fehler bereits19:11:12. Beide Zeitquellen getrennt erhalten.

Drei nachgelagerte Registerabfragen vom24.11.: ACT1/STA3/FLT0/POS3/PRE0,
FOR255/SPE255 statt angeforderterFOR0/SPE16. Der Transport bestätigt FOR vor
SPE und vor POS/GTO; Fehler daher wahrscheinlich in der Kraftparametrierung.
Die damaligen Action-Rückmeldungen fehlen, deshalb keine endgültige Ursache
oder genaue fehlgeschlagene SET-Operation behaupten. Minimalstatus danach
RUNNING ohne gemeldete Kollision; die zugänglichen Safety-Quellen enthalten
keinen passenden Kollisionsauslöser, das Minimaljournal war nicht verfügbar.
Tatsächlich gemessene Gelenkgeschwindigkeit beim Abbruch nicht aufgezeichnet;
genehmigte/geplante Grenze bleibt0,1rad/s.

Reine Aufgabendiagnostik ergänzt: getrennte Aktivierungs-/Öffnungs-/
Schließergebnisse, letzte vorhandene Action-Rückmeldung und konkrete
Fehlerphase. Transport-Timeouts nennen Schritt, Soll und letzte Register;
keine zusätzlichen Abfragen, Wiederholungen oder geänderten Befehlsgrenzen.
Sicherheitsprogramm unverändert. Nach Nutzerhinweis auf wieder erreichbaren
N100 am25.11. fortgesetzt;55 gezielte Offline-Tests bestanden.

Hersteller-URCap aus dem N100-Archiv hashgeprüft zurückgeholt. Einmalige
Parameterproben bei ACT0/STA0/FLT0/GTO0: ausschließlich `SET FOR 0`, danach
bei bestätigtemFOR0 `SET SPE 16`. Jeweils drei anschließende Registerabfragen
bestätigen den neuen Wert, ACT/STA/POS/PRE bleiben unverändert. Keine ACT-,
POS-, GTO-, Armfahr-, Power-, Brake- oder Play-Befehle gesendet. Das ist eine
Bestätigung des Serverzustands, kein Nachweis realer Hardwareparametrierung
oder einer Öffnung: native Abfrage meldet POWER_OFF/NORMAL, Programm läuft
nicht, geladen `/programs/<unnamed>.urp`.

Diagnosetransport auf N100 mit Rücksicherung installiert, alle vier Adapter
vorher unbeschäftigt. Nur `uwa-grippers.service` neu geladen, Invocation
`b9a65565d3b64b6782f7eaf663ea9447`. Transport-SHA256
`b4edec5680b891c45e89d710f2510a9885af6c7ebcc79931d3c4a921b74a0534`.
Danach alle neun Register aller vier Greifer unverändert; left_rear weiter
inaktiv, FOR0/SPE16. Stift-Ausführungshelfer lokal für den normalen nächsten
hashgebundenen Library-Transfer aktualisiert, kein Wiederanlauf des alten Runs.

Zellenzustand vor dem Greifertest separat: PAUSED/COLLISION, zwölf FCL-Kontakte links vorne
gegen rechten Tisch gemeldet, Kollisionsdaten rechts vorne fehlen. Kein
Resume oder Eingriff in diese Pause. Dies ist kein nachgewiesener Auslöser
des gestrigen Stiftfehlers.

**Einzelner realer Greifertest25.11.,15:18:51–15:18:54AWST erfolgreich.**
Nutzer bestätigt mit „erledigt“ sowohl Bereitschaft als auch den angefragten
einmaligen Aktivierungs-/Öffnungstest ohne Armfahrt. Vorher nativ RUNNING,
NORMAL, `ros.urp` läuft; Schutzpause bleibt bestehen. Genau ein Aktivierungs-
und ein Öffnungsaufruf über den regulären ROS-Client. Nach Aktivierung
ACT1/STA3/FLT0/POS165, FOR/SPE noch255; anschließender Öffnungsauftrag bestätigt
FOR0 zuerst, dannSPE16 und schließlich OBJ3/POS3/PRE0/COU0.53 vorhandene
Action-Rückmeldungen gespeichert. Keine Wiederholung, keine Arm-, Power-,
Brake-, Play- oder Resume-Befehle. Transportänderung betrifft nur Diagnostik;
der ursprüngliche Fehler wurde nicht reproduziert und ist nicht als dauerhaft
behoben nachgewiesen. Kein Stift geschlossen oder ausgehoben.

Abschließender Schutzstatus PAUSED/OPERATOR PAUSE, vollständige Kollisionsdaten,
keine aktuellen Kontakte. Pausenursache hat sich zwischen den lesenden
Abfragen geändert; kein Pausen-/Resumeaufruf durch diese Diagnose. Der linke
hintere Greifer bleibt aktiviert/offen bei FOR0/SPE16. Nachweise und Fortsetzung:
[Arbeitsnotiz](work/pen-gripper-abort-20261124.md),
`setup/tasks/pen-debug-20261125/`.

## Supported carton grasp mit Minimalbetrieb erfolgreich, 24.11.2026,19:03AWST

Library-Lauf `c0ea7847aa8e49dd99b7ab6aa6b7f144`, gestarteter N100-Aufgabenpfad
`minimal-candidates/minimal.upWhPwQC/setup/tasks/skill-library-carton-2004ca438cc048848d3a93010a8a431c/cycle`.
Hochanfahrt, Greifervorbereitung und gemeinsame Einfahrt beider rechter Arme
erfolgreich über `protection_backend=minimal`. Einfahrabschluss
`BOTH_OPEN_AT_WALL_HELD_NO_CLOSE`; Originaltempo0,1rad/s/83,33mm/s TCP.
Keine Änderung am Safety-Kern, seinen Controllern oder Grenzwerten in diesem
Debugging. Anbindung/Dateizuordnung des Aufgabenprogramms separat korrigiert;
Einzelheiten im folgenden Integrationsabschnitt.

Erster Kontaktaufruf scheiterte vor dem Schließen an der bestehenden
Foto-Zeitprüfung: OAK4-Metadatenende19:00:46,922 lag beim Aufruf vor dem
N100-Jetzt19:00:46,642. Foto nach Einfahrabschluss aufgenommen. Einfahrbild
unabhängig angesehen: Karton tischgestützt, beide offenen Greifer um die
vorgesehenen Seitenwände. Abgeleitete reine Inspektionsansicht
`entry-photo/inspection.jpg` im Library-Lauf, Original/Metadaten erhalten.

Runner wiederholt diese unveränderte Bildvalidierung künftig genau einmal
bei `WAITING_VISUAL_REVIEW`/diesem Bildfehler, bevor er Kontakt freigeben kann;
kein erneutes Anfahren, keine Toleranz-/Metadatenänderung.70 gezielte Offline-
Softwareprüfungen bestanden, einschließlich begrenztem Wiederholungsfall und
dauerhaft ungültigem Bild. Der bestehende N100-Kontaktschritt desselben Laufs
wurde nach Behebung erneut aufgerufen, ausschließlich Kontaktfortsetzung.
Freigabe `f7002ef9761a4751a17933de47a0c604` laut Reviewstore durch Bedienung
angenommen (`actor=operator`); der Agent sendete keine `decide`-Freigabe.

Ergebnis: `success=true`, Workflow `SUPPORTED_CONTACT_HELD`, beide regulären
Schließbefehle erfolgreich (`GRIPPER_CLOSE_COMPLETED`). RF OBJ2/POS202,
RR OBJ2/POS203, jeweils rawFOR0/SPE16. Dies sind Kontaktregister/Programmerfolg,
kein Nachweis vier einzelner Pads, gemessener Klemmkraft oder tragfähigem Hub.
Karton bleibt auf dem Tisch; keine Hub-/Transport-/Öffnungsfahrt angefordert.
Abschließender Kernstatus RUNNING, vollständige Kollisionsdaten, keine
Warnung/Kollision, vier bestätigte Controller ohne laufende Action, Faktor1.

Die ursprüngliche Library-Zeile bleibt als historischer Fotozeit-Fehlversuch
erhalten; die tatsächlich erfolgreiche Kontaktfortsetzung liegt gesondert in
`setup/tasks/uwa_program_library/c0ea7847aa8e49dd99b7ab6aa6b7f144/contact-continuation/result.json`.
N100-Originalworkflow ist erfolgreich. Weitere Nachweise:
`setup/tasks/carton-library-debug-20261124/minimal-final-grasp.json`,
`minimal-final-protection.json`, `minimal-library-regression.log`.

## Stiftgriff in der Program library, 24.11.2026

Nutzer beauftragt nach der Bildprüfung ein eigenes Programm nach Vorbild
Supported carton grasp für **left_rear**: OpenCV/OAK Pro, Gemini-Fallback,
Planung auf aktuelle Pose und Greifen. Nutzer bestätigt beide30mm-Quadrate
mittig, schwarze Außenkante nachgemessen30mm und vollständigen Sitz.
Anfangs war die Kappe aufgesetzt; auf Rückfrage für den CAD-Programmstand
abgenommen und Stift erneut eingesetzt. Die frühe22-mm-PnP-Höhendifferenz
ist kein bewiesener Kappeneffekt. Native Kantenanpassung reduzierte am
frischen Foto den Fitfehler auf1,514px; Druckmaß unverändert30mm verwenden.

Programm **Pick pen from holder** / `pen-left-rear-v1` mit **Inspect pen**,
**Plan pickup only** und **Start program** angelegt. Kamera- und Planmodus
senden keine Arm-/Greiferbefehle. Start verwendet getrennte neue Bewegungs-
und Kontakt-/Liftprüfungen im vorhandenen Reviewstore; Kartonvertrauen wird
nicht auf die neue Aufgabe übertragen. Aktives Schutzbackend übernehmen.
Keine UR-Programm-/Power-/Brake-Aktion beim Anlegen oder Öffnen.

Vollständige Folge wird vor der Anfahrt geprüft:150mm Vorposition, vertikale
Einfahrt, Schließen rawFOR0/SPE16 und150mm vertikales Ausheben. Kontakt nach
frischem Einfahrfoto. Adaptergriffreferenz46mm über CAD-Adapterdatum nahe
dem oberen Ende; nomineller Robotiq-TCP145mm, keine neue reale TCP-Messung.
Eigene taskbezogene Öffnungshüllen enthalten den ganzen Greiferbereich mit
konvexen Mesh-Sweeps und analytischem Zwischenstützstellenzuschlag. Dadurch
wird die grobe Sphärenüberdeckung am kleinen Halter vermieden; aktive
Hardwaregeometrie, Vollzell-FCL und40-mm-Nachbararmmarge bleiben separat.

Anleitung [Stiftgriff](docs/pen_grasp_library.md), Arbeitsstand
[Programmnachweis](work/pen-grasp-library-20261124.md). Aktuelle Fotos,
Gemini-Ausschnittantworten und Offline-Nachweise unter
`setup/tasks/pen_pick_20261124/`. Reale Greif-/Haltekraft und Schreib-TCP
stehen noch aus; keine erfolgte Stiftfahrt aus der Programminstallation ableiten.

Finale aktuelle Plan-only-Prüfung erfolgreich:
`setup/tasks/pen_pick_20261124/library-plan-current-02/`.
OpenCV-Kantenfit1,5335px RMS, Anfahrt27,678s, Einfahrt8,069s, Lift8,069s,
gesamt43,817s. Analytische Prüfung der Controllerinterpolanten bestätigt
≤0,1rad/s und≤0,2rad/s²; TCP-Limit83,3mm/s. Vollzell-/Taskobjektprüfung,
376 zusätzliche nicht auf dem Erzeugungsraster liegende Öffnungszustände
über8Greiferkörper sowie portable RViz-Mesh-/Timeline-Bindung bestanden.
Nachweis `setup/tasks/pen_pick_20261124/final-plan-validation.json`.
Bibliothek im untätigen lokalen Minimal-Bedienfenster neu geladen, alle drei
Aktionen im HTTP-Katalog bestätigt. Direkter GUI-Zugriff nicht verfügbar;
keine GUI-Klicks oder reale Stiftfahrt behauptet.
59 gezielte Tests bestanden. Run-spezifische N100-Import-/Plandateiprüfung
bestätigt approach/entry/lift ohne Arm- oder Greiferbefehle:
`setup/tasks/pen_pick_20261124/n100-import-and-files.json`.

## Kartonprogramm mit neuer Minimal-Runtime fortgesetzt, 24.11.2026

Auf ausdrücklichen Nutzerauftrag erneut über die Program Library fortgesetzt.
Vorher aktiven Kern `uwa-minimal-protection.service`, Invocation
`f440e62ec5724c279e6f029a5deb4231`, und beendeten Altdienst bestätigt.
Kernstatus RUNNING, vollständige Kollisionsdaten, keine Warnung/Kollision,
alle vier Controller bestätigt, keine laufende Action. Taskvertrauen100,
Tempo33⅓% (=0,1rad/s), bestehende Arbeitsbereichssitzung freigegeben.
Die neue GUI und ihr Library-Prozess binden ausdrücklich
`minimal-candidates/minimal.upWhPwQC`; deren Port36919 verwendet.
Die alten Library-Server39823/8780 nicht für reale Starts benutzt.
Browsersteuerung weiterhin nicht verfügbar, daher normaler Button-Endpunkt
`POST /api/runs`. Lauf `189034efca4e48a38525a929d56d3312`, Start18:29:10AWST.
Beide Kamerareferenzen gültig. Keine Safety-Änderung oder neue Wächter.
Erster Lauf vor Kamera/Bewegung gesperrt: Ausgabe-Elternordner `setup/tasks`
fehlte in der neuen Runtime. `run_carton_program.py` legt nun den Elternordner
vor dem weiterhin exklusiv angelegten Laufordner an. Python-Kompilierung und
Diffprüfung bestanden. Erneuter normaler Start18:30:14AWST,
`6e9c53258e95489295b2cbf2408ff2bb`: Kameravergleich12,729mm/1,986° akzeptiert,
OAK4 unverändert übernommen. Vor Versand der Bahn beim Offline-Vorbereiten
gesperrt: installierter ROSmini-Pythonpfad enthält neues Modul
`uwa_cell_motion.protection_backend` noch nicht. Der Offline-Launcher in
`run_carton_program.py` bindet nun das aktuelle Motion-Quellpaket ausdrücklich
ein; bestehender Bibliotheks-/Checkervergleich bleibt erhalten. Acht bestehende
Library-Softwareprüfungen und tatsächlicher Modulimport über diesen Launcher
bestanden. Keine N100- oder Safety-Datei geändert. Erneuter normaler Start
18:32:27AWST, `70922ed93dc64c6a8f78e01c1754863f`: vor Planung wegen
13,385mm/2,172° Kamerawiderspruch abgelehnt;30mm erfüllt, Winkel<2° nicht.
Gezielte bestehende Hydrogen-/Native-Pixel-Nachmessung der gespeicherten
Aufnahme ergab in Runde2 eine weiterhin streng gültige OAK4-Pose und
14,350mm/1,458° Gegenvergleich. Keine Grenzlockerung oder Kamerabewegung.
Nachweis `setup/tasks/carton-library-debug-20261124/minimal-fit-refinement/`.

Der normale Library-Runner verwendet diese begrenzte Nachmessung nun bei zwei
akzeptierten, aber widersprüchlichen Einzelposen: vorhandene Hydrogen-Führung,
native Pixelmessung, maximal bestehende drei Runden. OAK4 bleibt metrische
Quelle; Originale, Feedback und alle Vergleiche werden erhalten. Bei weiterem
Widerspruch/ungültigem Fit bleiben Originalposen und Ablehnung bestehen.
Keine Änderung am Safety-Programm.34 gezielte Softwareprüfungen bestanden,
einschließlich Ablehnung trotz Nachmessung und ungültigem Einzelbildfit.
Vollständiger Offline-Plan mit dem korrigierten Launcher bestanden:
`setup/tasks/carton-library-debug-20261124/minimal-offline-plan/`.

Die neue GUI wurde währenddessen anderweitig neu geöffnet, ihre Library liegt
jetzt auf Port44295. Minimal-Umgebung und Runtimepfad separat bestätigt.
Automatische Freigabeprüfung lehnte zunächst wegen früherer Importfehler ab;
nach erneuter Vorlage der bestandenen34 Prüfungen und des vollständigen
Offline-Plans wurde der normale Start zugelassen. Lauf
`f675efab2f1d4ab1b23b3354334c1e85`, Start18:39:13AWST: Foto und kompletter
Offline-Plan erfolgreich, vor Motion Review wegen eines remappten Meshpfads
gesperrt. Der bisherige Transfer nahm alle Pakete im Kandidateninstall an;
`uwa_cell_description` stammt tatsächlich aus dessen gemeinsamem Underlay.

Transferkorrektur: tatsächlichen Paket-Share-Pfad auf N100 abfragen, nur diese
installierten Description-Assets dorthin zuordnen. Quellen/Aufgaben bleiben im
Kandidaten. N100-Runner akzeptiert genau sein per Ament aufgelöstes Description-
Paket zusätzlich als gehashte Modellquelle; alle bestehenden Hash-/Bahnprüfungen
bleiben aktiv.68 gezielte Softwareprüfungen und vollständiges dateibasiertes
Staging des Originalplans bestanden. Nur Task-Runner auf N100 aktualisiert,
SHA-256 `a014d929dd8712e45cb3d3be0f80ce17d59fb5918d6b7d409ff5f4c4aeedc520`;
Vorversion unter Kandidat `setup/tasks/run_carton_cycle.before-description-share.py`.
Keine Änderung am Schutzkern, Controller oder deren Konfiguration.
Nachweis `setup/tasks/carton-library-debug-20261124/minimal-shared-stage/` und
`minimal-library-regression.log`. Erneuter Start18:43:54AWST,
`d9be7d999c2f45c08491d120d6a96706`: Meshzuordnung erfolgreich, danach vor
Motion Review wegen fehlender `setup/tracking/models/carton_avocado_v1/reference.npz`
gesperrt. Diese feste Aufgabenreferenz aus der bisherigen N100-Runtime in
die neue Kandidatenablage kopiert, ohne vorhandene Datei zu überschreiben;
auf beiden Hosts SHA-256 `db5a70a6120aeafdc249f597e53e410ed74b15d8a4da4faf6eec33fc06fb28a9`.
Keine Safety-Datei geändert. Erneuter Start18:46:05AWST,
`66755f694bcc4d089718fe55cd4fa522`: vor Planung bei12,228mm/2,174° abgelehnt.
Drei gezielte Native-Pixel-Nachmessungen verblieben bei2,45–2,60°; keine
Toleranz geändert und keine Fahrt. Wegen dieses konkreten Kamerawiderspruchs
beide Tischboard-Kamerareferenzen separat über die Library neu aufgenommen,
vorherige JSONs unter `setup/tasks/carton-library-debug-20261124/before-evening-camera-reference/`
gesichert. Kamera-only-Lauf `a19cf54c42914e369cf754eebebd5048` erfolgreich:
OAK4/Fokus107,17Marker,1,208px Prüf-RMS; USB/Fokus112,16Marker,0,978px.
Neue12-h-Fristen ab18:49:11/18:49:17AWST bis25.11.06:49AWST. Keine globale
Intrinsics-/Armbasisänderung. Erneuter normaler Kartonstart18:49:47AWST,
`68e5ec8f882a4e7b9fcf4c0439457c2d`: Kameravergleich und N100-Empfang der
Bewegungsrevision erfolgreich. HIGH vor Zielversand abgelehnt, weil die
Mesh-Hashliste auf kopierte Kandidaten-Quelldateien zeigte, die URDF dagegen
auf Symlink-installierte Dateien des gemeinsamen Underlays. Inhalt unverändert,
aber Schlüssel der aufgelösten Pfade verschieden. Transfer fragt jetzt sowohl
installierten Share als auch aufgelösten Description-Quellpfad auf N100 ab;
alle gehashten Modellreferenzen werden konsistent dorthin gebunden. Kein
Vergleich entfernt.68 bestehende gezielte Softwareprüfungen bestanden.
N100-Taskrunner SHA-256
`ce078ede719e492fe54c9c118937956cce166fc3081705885d6cabb583966d96`,
vorige Datei `setup/tasks/run_carton_cycle.before-canonical-assets.py` im Kandidaten.
Reines Datei-Staging nach `setup/tasks/canonical-model-check/prepared` auf N100;
`checked_problem`-Modellprüfung dort ohne ROS-Goals gestartet. Keine neue
Safety-Logik, kein Kern-/Controllerwechsel und weiterhin keine Armfahrt in
diesen Integrationsversuchen. Lauf `42561b7e82a641ee83543edb697eb538`
passierte Geometrieprüfung und Motion Review, wurde vor Fahrziel wegen
Hardware-Bindung abgelehnt: der Description-Quellpfad wurde auch für
Kalibrierdateien umgebunden. Remapping auf `meshes/` begrenzt; Armkalibrierungen
bleiben im Kandidaten.68 Softwareprüfungen einschließlich dieser Trennung
bestanden. Vollständiges erneutes Datei-Staging unter
`setup/tasks/binding-model-check/prepared` auf N100: `checked_problem` und
`read_bundle` für HIGH und ENTRY bestanden, inklusive Hashes, Checker,
Modell, Originalquellen und Hardwarebindung. Kein Goal für diese Datei-Prüfung.

## Sicherheitsprogramm: ausdrückliche Freigabe vor Erweiterungen, 24.11.2026

Nutzer fordert vor künftigen Änderungen am Sicherheitsprogramm seine ausdrückliche
Genehmigung, wenn sie die Ausführung verlangsamen könnten **oder** allgemein
Performance kosten könnten **oder** Funktionen ohne unmittelbaren Hardwareschutz
ergänzen. Auch unmittelbar schützende Änderungen mit möglichen Performancekosten
fallen darunter. Konkrete Änderung und Auswirkungen vorher darlegen; bereits
konkret erteilte Freigaben bleiben gültig. Verbindliche Regel in den
[Projektregeln](AGENTS.md) und den Workspace-Regeln.
In diesem Arbeitsschritt ausschließlich Dokumentation ergänzt, keine Laufzeitänderung.

## Gazebo-Video mit gelben/roten Werkstückspuren, 24.11.2026

Nutzerauftrag abgeschlossen: native Gazebo/Ogre2-Videofassung der bestehenden
Dreiarm-Kartondemo mit gelben Zeichenlinien, sechs roten virtuellen
Bohrstellen und mitgeführter Werkstücknahansicht.15 Bilder/s Ablaufzeit
werden bei30fps mit2× Tempo abgespielt. Datei:
`setup/tasks/carton_video_20261124/uwa-carton-gazebo-2x.mp4`,
1920×1080,H.264,90,37s,12,8MB,2711 Bilder.

Quelle sind die gespeicherten geprüften Sollbahnen des erfolgreichen Home-
Laufs vom20.11. (`house_drill_home_20261120_01/run05`,54 Phasen ab Hub plus
Anfahrt/Einfahrt). Kinematische Renderwiedergabe mit visueller
Greiferinterpolation, keine neue Kontaktphysik oder reale Ausführung.
17 Standbilder einschließlich Dreh-/Rückfahrübergängen visuell geprüft.
Die Nahkamera wurde nach erster Prüfung oberhalb des Tisches geführt.
Zehn Stichproben aus der lokalen MP4 dekodiert; Bildzahl/FPS/Format bestätigt,
SHA-256 der Videokopie stimmt mit titanpc überein. Renderjob erfolgreich
beendet. Quellen, Reproduktion und weitere Nachweise:
[Videoexport](docs/gazebo_carton_video.md),
[Arbeitsstand](work/carton-video-20261124.md).

Nutzer hat das Video anschließend unter
`https://youtu.be/YHpvsQd1fE8` veröffentlicht. Neuer englischer Eintrag auf
seiner Projektwebsite in`src/tobiasrecker.github.io` erstellt, gerendert
und mit Commit`0b9b6fc` veröffentlicht. Nach Nutzerbestätigung funktioniert
hierfür ein eigener Repository-Deploy-Key. Live-Eintrag mit Videolink und
passendem Vorschaubild geprüft:
`https://tobiasrecker.github.io/projects.html#cooperative-task-programming`.
Zugang und Nachweise im Workspace-HANDOVER.

## ChArUco: professioneller Neudruck und fertige PDFs, 24.11.2026

Nutzer plant professionellen Druck und fragt nach idealer Platten-/Mustergröße
und Pattern; freie Formate einschließlich größer als A3/A4 sind möglich.
Bestand: feste aktive Muster280×200mm (7×5,40/28mm), mobiles266×190mm
(7×5,38/28mm). A3 bezeichnet bisher das Papier, nicht die Musterfläche.

Bevorzugter Entwurf des Agenten für die bestehende Zelle: zwei feste Platten
550×400mm, aktive Muster500×350mm,10×7Felder à50mm/Marker36mm;
mobil450×360mm, Muster405×315mm,9×7Felder à45mm/Marker33mm.
ChArUco mit DICT_5X5_250, getrennten ID-Bereichen und dokumentierter Generation.
Im Folgeauftrag beauftragt der Nutzer die entsprechenden PDFs. Die Druckdaten
zu diesen Maßen sind erstellt; ein physischer Austausch oder eine operative
Profilaktivierung ist damit noch nicht beauftragt.

Drei einseitige Vektor-PDFs unter `output/pdf/`:
`uwa_charuco_table_left_550x400mm_1to1.pdf` (IDs0–34),
`uwa_charuco_table_right_550x400mm_1to1.pdf` (IDs50–84) und
`uwa_charuco_mobile_450x360mm_1to1.pdf` (IDs100–130).
Eingebettete Schriftarten, Endformat als Media-/Crop-/Trim-/BleedBox,
PrintScaling=None, je100mm-Kontrollstrecken in X/Y. Eigene Definition
`config/print_designs/charuco_professional_v1.json`, reproduzierbar mit
`scripts/print_professional_charuco.py`.

Alle finalen Seiten visuell geprüft. Der unabhängige Validator rendert die
fertigen PDFs mit Poppler bei300dpi:101/101Marker und156/156ChArUco-Ecken
korrekt erkannt, alle geplanten IDs vorhanden, Seitenformate/Vektorausgabe und
beide Kontrollstrecken geprüft. Raster-Geometrieabweichungen unter0,2mm;
dies ist kein Fertigungs- oder Genauigkeitsnachweis des späteren Ausdrucks.
Hashes und Bericht: `output/pdf/uwa_charuco_professional_v1_{manifest,validation}.json`.
Druckanleitung: [ChArUco PRO v1](docs/charuco_professional_print.md).

Kurze Projektion mit gespeicherten Kameraposen/K/D ergibt bei der festen
550×400mm-Platte mindestens91px Trägerrandreserve an der nahen USB-OAK-
Ansicht;600×450mm nur etwa9px. Das mobile450×360mm-Board ist im Zentrum
der vier Wrist-Ansichten plausibel, verkleinert aber den Bewegungsbereich;
den bisherigen A4-Quader50×50×25cm nicht übertragen. Schärfe, Verdeckungen,
Tischplatz und reale Erkennung sind damit nicht nachgewiesen.

Steife, plane, matt bedruckte Platte und dokumentierte Maßhaltigkeit in beiden
Achsen empfehlen. Vor Austausch Musterursprung und Oberflächenhöhe auf den
bisherigen Tischbezug übertragen; die übernommenen Armbasisbindungen bleiben
Arbeitsreferenz. Keine aktive Boarddefinition, Kalibrierung, Kamera oder
Runtime geändert. Quellen, Rechnungsannahmen und Druckhinweise:
[Arbeitsnachweis](work/charuco-professional-print-20261124.md).

## Neues minimales Hardware-Schutzkonzept, Auftrag 24.11.2026

Nutzer verwirft das bisherige UWA-Guard-/Supervisor-/Watchdog-Konzept und
beauftragt nach gemeinsam festgelegtem Plan die Implementierung. Schutzumfang:
Hardware-Geometrie und gemeinsamer Software-Pausenknopf; fehlende Kollisionsdaten
warnen nur. Greifer ausschließlich Kollisionsgeometrie, keine weiteren
Greifer-Schutzprüfungen. Native UR-Sicherheit und geplante Geschwindigkeiten
bleiben unverändert. Vierarme-Pause mit ausdrücklicher Fortsetzung; 40-mm-
Nachbararmmarge und sonstige bisherige FCL-Kontaktgrenzen erhalten.

Implementierung und Kandidatenprüfung abgeschlossen. Neues Paket
`uwa_cell_protection`, pausierbarer C++-JTC und gemeinsame Robot-Power-
Stop/Resume-Bedienung mit eigenem N100-Kanal. Kartonprogramm, Kamera-Library,
Parking, Akquisitionsfolgen und paralleler Scan nutzen im Minimalbetrieb den
gemeinsamen Adapter statt der alten Wächter. Bestehende Bahnen und Tempi bleiben.

Seit dem ausdrücklich beauftragten realen Betriebswechsel24.11.2026 aktive N100-Runtime:
`/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
Fünf Pakete erfolgreich gebaut; Quellenmanifest geprüft. Schlussregression:
168 Pythonprüfungen und6/6 C++-/Controller-Mocktests bestanden, darunter zwei
Vierarm-Aufgaben unmittelbar nacheinander und Pause/Fortsetzung derselben Goals.
Bibliotheks-/Modulbindung auf N100 geprüft (JTC6.9.0, Manager6.10.1). Fünf
archivierte Zellzustände liefern auf N100 und ROSmini gleiche Entscheidungen
und exakt gleiche verglichene Abstände; kanonische Geometrie/Meshes und SRDF
stimmen überein. Kleine N100-Dateistichprobe:12,1–27,0ms ungecachet bzw.
0,035–0,057ms wiederholter Zustand; kein Live-Dauerlast- oder Anhaltenachweis.

Nutzerpause wurde durch gezieltes SIGSTOP des eigenen Builds umgesetzt und
nach ausdrücklicher Fortsetzung anhand Prozessidentitäten wieder aufgehoben.
Der Build ist inzwischen beendet. Die damalige reine Implementierung nahm
keine Hardwareänderung vor. Im folgenden ausdrücklichen Nutzerauftrag wurde
der reale Betriebswechsel durchgeführt: alten Schutz zuerst beendet, vier
Treiber auf den Kandidaten umgestellt, C++-Kern gestartet und alle vier
`ros.urp` über **Start + ROS** regulär gestartet. Alte UWA-Wächter sind aus.
Der Kern ist jetzt ein dauerhafter N100-Benutzerdienst
`uwa-minimal-protection.service` mit `Restart=no`, ohne ExecStopPost und mit
aktiviertem Benutzer-Autostart/Linger. Aktuelle Invocation
`f440e62ec5724c279e6f029a5deb4231`; Desktop und Safety-Log-Aktion binden denselben
Kandidaten. Treiber/Programme bleiben separat bediente Starts.

**Reale Funktionsprüfung18:11AWST bestanden:** zwei simultane Vierarm-Aufgaben
q6 je0,1rad hin/zurück, je1,875s nominell, unverändert0,1rad/s und0,2rad/s².
Stop und Resume als automatisierte Qt-Mausereignisse im sichtbaren
Originalfenster; eigener SSH-Kanal bleibt von der laufenden Fahrt unabhängig.
Alle vier ursprünglichen Action-UUIDs und Phasen während Pause erhalten,
anschließend dieselben Ziele erfolgreich fortgesetzt. Zweite Aufgabe direkt
danach erfolgreich, ohne Reset. Größte Positionsspanne über1,036s Pause
0,000288rad; größte Rückkehrabweichung0,000080rad. Native Skalierung1,0;
Programme vorher/nachher PLAYING/ROS-ready, keine beobachtete Programmunterbrechung,
Greiferregister unverändert. Endzustand: alle vier Ziele beendet, Arme in ihren
Ausgangspositionen, Kollisionsdaten vollständig, keine Warnung/Kollision.

Vorab vollständiger unabhängiger Fortschrittsnachweis und110 C++-Geometrieprüfungen
auf beiden Hosts. Keine absichtlichen realen Kollisionen oder Datenfehler;
kein maximaler Bremsweg- oder Dauerstabilitätsnachweis. Frühere Anforderungen,
alle alten UWA-Wächter im Neubau zu erhalten, sind durch den Nutzerauftrag ersetzt.

[Bedienung](docs/minimal_hardware_protection.md) ·
[Arbeitsstand und Nachweise](work/minimal-hardware-protection-20261124.md) ·
[Pythonprüfung](../../setup/tasks/minimal-protection-20261124/python-complete-tests.log) ·
[C++-/Mockprüfung](../../setup/tasks/minimal-protection-20261124/cpp-final-ctest.log) ·
[N100-Build](../../setup/tasks/minimal-protection-20261124/n100-final-build.log) ·
[Rechnervergleich](../../setup/tasks/minimal-protection-20261124/n100-cross-host-parity.json).

[Realer Betriebswechsel und Nachweise](work/minimal-real-cutover-20261124.md).
Safety Log liest jetzt die aktive Minimal-Runtime und deren Kern-Journal;
zwölf gezielte Prüfungen bestanden. Aktueller lokaler Diagnoseexport mit
realem GUI-Audit und Rohmessungen ist über
`setup/logs/uwa-control/latest-export.txt` im Workspace auffindbar.

## Stiftaufnahme: ArUco-Druckbogen, 24.11.2026

**Folgeaufnahme17:41AWST:** Nutzer hat zwei30mm-Marker am Stift angebracht,
oben und auf der Seite senkrecht zu den Greifflächen. Aktuelles natives
OAK-Pro-Foto4056×3040/Fokus112 mit dem bestehenden N100-Fotowerkzeug:
**obenID97, seitlichID96**, beide direkt in Originalpixeln erkannt.
Kanten97 etwa60–74px,96 etwa42–75px; perspektivisch unterschiedlich verkürzt.
Beide Marker gehören zum Stift/Adapter,97 ist trotz seiner ursprünglichen
Druckbogenbeschriftung keine Halterreferenz. Foto, Metadaten, SHA256,
Eckkoordinaten und180°-Anzeigedetail unter
`setup/tasks/pen_pick_20261124/20261124-pen-markers-oakpro-01/`.
USB-Gerät18443010314F3B1300, Factoryhash unverändert, Kamera geschlossen
und Lease freigegeben. Keine Arm-/Greiferaktion. Sichtbarkeit in diesem
Einzelbild bestätigt; metrische Greifpose und weitere Blickrichtungen/
Verdeckungen noch nicht geprüft. Die folgende Empfehlung20mm ist historisch.

Nutzer hat den Stift im gemeinsam entworfenen Halter auf den Tisch gestellt
und möchte dessen Aufnahme künftig als weiteres Teilprogramm der Program
library. Zunächst beauftragt: markerlose Erkennung einschätzen und bei
sinnvoller Markernutzung einen mehrfach belegten A4-Druckbogen erstellen.

Empfehlung des Agenten: ArUco auf einer planen, starren Fläche am Adapter,
bei Bedarf auf einer kleinen Trägerlasche; optional eigener Haltermarker.
Keinen ebenen Quadratmarker um die runde Stifthülse wickeln. Ein Haltermarker
weist die Stiftanwesenheit nicht nach. Ohne aktuelles Kamerabild sind weder
die markerlose Robustheit noch die erforderliche Markerkante im realen
Aufbau belegt. Montage/Markerbezug zur Greifpose und tatsächlicher Stiftsitz
bleiben zu prüfen. Dies ist noch keine bestätigte Nutzerentscheidung zur Montage.

Erstellt: [A4-Druckbogen](output/pdf/uwa_pen_markers_A4_1to1.pdf), eine Seite
mit26Etiketten,20/25/30/40mm schwarzer Außenkante plus4mm Weißrand.
DICT_4X4_100, IDs92–99 ohne Überschneidung mit den bestehenden drei Boards.
Jede ID hat genau eine Größe; doppelte IDs sind Ersatzkopien, nur eine
sichtbare Kopie je ID verwenden. ID92/20mm als erster Adapterversuch
vorgeschlagen, kein nachgewiesenes Kameralimit. Anleitung und ID-Tabelle
in [marker_tool/README.md](hardware/marker_tool/README.md).

PDF visuell geprüft und bei300dpi alle26Marker im gesamten Blatt sowie
einzeln korrekt decodiert. A4-Maß, deaktivierte Druckskalierung und gerenderte
Kantenmaße mit<0,2mm Rasterabweichung geprüft. Dies prüft das digitale PDF,
nicht den Ausdruck oder reale Kamera-/Greifgenauigkeit. Reproduktion mit
`scripts/print_pen_markers.py`, Metadaten und Nachweis neben dem PDF.
Keine Kamera-/Roboteraktion, kein Dienstneustart und noch kein ausführbares
Stiftprogramm in der Library angelegt.

## N100-Entlastungs-Candidate, 24.11.2026

Nach diesem verworfenen 20-Hz-Candidate wurde eine kleinere Vereinfachung
geprüft: Der Hardware-Watchdog betreibt keinen zweiten StopPort-/RPC-Pfad,
sondern behält nur die unabhängige native Stop-Funktion. Der StopPort pollt
Manager-, Hardware- und Parameterdienste nicht mehr im ruhenden unbelasteten
Zustand. Die Abfrage wird bei Blockierung oder expliziter Freigabe erneut
aufgenommen. Der 50-Hz-Supervisor-/Watchdog-Takt und die RTDE-/Geometrie-
Stillstandsprüfung bleiben unverändert. 154 relevante lokale Tests bestanden.

Der finalisierte Candidate `pilot.3avMfmBY` enthält die vollständigen
Entlastungsmodule `hardware_nodes.py`, `hardware_ports.py` und `interlock.py`,
alle Motion-Pythonmodule, Motion-Configs und das Audit-Skript. Die
SHA-256-Prüfung und 22 Candidate-Pilottests bestanden. Isoliert bestanden
79 Guard-/StopPort-/Reserve-/RPC-Tests auf dem N100.

Ein isolierter Mockgraphstart des Candidate konnte den bestehenden
rclpy-/ROS-Laufzeitkontext nicht herstellen und lief weiter gegen die
operative Installation; ohne Streams ist dies kein positiver Mock-Nachweis.
Der Overlay ist nicht aktiviert. Die laufenden echten Guard-, Supervisor-
und Watchdog-Prozesse verwenden weiterhin die operative 50-Hz-Quelle.
Keine Hardwareaktivierung oder reale Fahrfreigabe aus der Candidate-Prüfung
ableiten.

Candidate pilot.3avMfmBY wurde am24.11.2026 tatsächlich kurz auf dem N100
bewaffnet. Der Guard erreichte22,1/21,2%, Supervisor19,5/19,2% und Watchdog
10,1/10,2% in zwei 15-s-Messungen. Beim anschließenden regulären Stopp blieb
die vierarmige Hold-Bestätigung nicht vollständig frisch: vier native Stops
wurden quittiert, links vorne und rechts hinten meldeten keine bestätigten
Holds. Der Candidate wird daher nicht weiter freigegeben.

Der operative Stand wurde danach zurückgesetzt und mit dem absoluten Profil
`hardware_carton_supported_trend.yaml`, RR-Priorität20 und bewaffnetem Dienst
wieder gestartet. Alle vier Arme waren stationär und native STOPPED. Die
Rückroll-Rücknahme nutzt wieder 20-ms-Supervisor-/Watchdog-Takte und den
ursprünglichen periodischen Controller-/Hold-/Hardwareprüfpfad. Messung:
Guard32,6%, Supervisor47,9%, Watchdog21,4% eines Kerns. Der Dienst bleibt
blockiert und führt keine Fahr-/Reset-/Play- und keine Freigabefahrt aus.

## Kartonablauf nach Wartungsabschluss fortgesetzt, 24.11.2026

Nutzer erteilt nach der vorigen Freigabeablehnung ausdrücklich die erneute
Freigabe zum Fortsetzen. Vor Start lesend alle vier stationären Holds,
Verriegelungen, Interlock und Modellbindung bestätigt. Aktuelle rechte
Driver-/Native-Abweichung maximal0,0000372rad, bestehende Grenze0,005rad.
Watchdog nach dem dokumentierten Wartungswechsel verriegelt, keine nativen
STOPs ausstehend; der normale Library-Start enthält den bestehenden Reset
unter unbeladenen Holds. Beide Start-/Ablaufskripte auf ROSmini/N100 identisch.
Normaler Start13:11:53AWST über den Button-Endpunkt der Power-Library
Port39823, Lauf `2cc9ee00bd3040e6bb2d2a18f8ffa48b`. Browsersteuerung weiterhin
nicht verfügbar. Vor Foto/Fahrt gesperrt, weil ein anderer regulärer UR-Start
die vorhandene `apply.lock` hielt. Später kein weiterer Startprozess und freie
Startsperre bestätigt; weder Sperrdatei gelöscht noch Sperre umgangen.
Erneuter normaler Start13:13:24AWST, Lauf
`9dfaf820af0a46339835c7f98a555adc`: Kameravergleich12,979mm/1,630° akzeptiert.
Hochanfahrt erfolgreich und beide rechten Greifer erstmals im normalen
Library-Ablauf vorbereitet: `ACTIVE_OPEN_HELD`, rawFOR0/SPE16. Einfahrt
nach Annahme beider Ziele abgebrochen (`right_front: DEVICE STATE STALE`),
keine native Fahrbewegung oberhalb0,003rad/s aufgezeichnet. Kein Kontakt.
Der Fehler ist nach Zielversand einzuordnen, nicht vor dem ersten Ziel.
Beim späteren Fehler-Snapshot war die letzte RF-Quelle rund0,36s alt bei
0,20s Grenze; das Alter im ersten auslösenden Prüfschritt fehlt. RF/RR-
Actionantworten um440775,576/440775,609s monoton, Guard meldet den Verlust
des Ausführungsbesitzers um440775,758s. Unabhängige RTDE-Mitschnitte laufen
dabei weiter. Nach dem Abbruch alle vier Holds, Interlock, frische Daten und
nicht ausgelösten Watchdog getrennt bestätigt.

Kurze Offline-Kostenmessung mit gespeicherten Originalmodellen auf N100:
primäre Kollisionsprüfung4,2–11,1ms, Kartonmodell0,69–1,09ms, je sechs Aufrufe.
Dies erklärt die Empfangslücke nicht. Keine Grenz-/Tempoänderung. Nachweise
`setup/tasks/carton-library-debug-20261124/entry-freshness-result.json` und
`entry-freshness-safety.json`. Nächster normaler Library-Lauf13:18:47AWST,
`7ecbceef602c4e71864ea0cf9f354067`, mit der vorhandenen passiven180-s-
Statusaufzeichnung auf N100 `setup/tasks/carton-driver-restart-20261124/library-record04.jsonl`.
Ergebnis des aufgezeichneten Laufs: Abbruch HIGH vor Zielversand,
`right_rear: native robot/program is not ready`, nativSTOPPED und keine
Arm-/Greiferbefehle. Der Safety Log ordnet vorangegangene native STOPs der
fehlenden Hardware-/Hold-Bestätigung rechts hinten zu. In der abgeschlossenen
Aufzeichnung04 verliert dieser Port wiederholt kurz Manager-/Hardware-/
Hold-Bestätigung und erhält sie nach Readback zurück; STOP-Anforderungen
folgen teils mit1,66–6,58s altem Hardware-Readback. Kein Geschwindigkeitsfehler.
Guard-Quellintervalle maximal51,3ms, Supervisor/Watchdog weiter nominal20ms.
Der separate Recorder hatte gemeinsame Empfangspausen bis365ms; seine Pause
belegt keinen gleich langen Guard-Ausfall. Daten:
`setup/tasks/carton-library-debug-20261124/library-record04.jsonl.gz` und
`recorded-retry-safety.json`.

Der im folgenden Abschnitt beschriebene, bisher nur vorbereitete
Entlastungsstand wurde erneut mit81 bestehenden Offline-Softwareprüfungen
geprüft. Alle bestanden; lokale Socketprüfungen benötigten Netzwerkfreigabe
außerhalb der Sandbox. Drei Dateien als inaktiver Kandidat auf N100:
`~/uwa-ur-runtime/review-candidates/carton-supervisor-20261124.bumWYrPi/`.
Manifest und vorherige aktive Dateien dort gesichert, noch keine Installation
und kein Schutzdienstneustart. Nutzerfreigabe für den konkreten Betriebswechsel
einschließlich regulärem Stoppen der rechten Programme wird benötigt.

## Greifervorbereitung zwischen Hochanfahrt und Einfahrt ergänzt, 24.11.2026

Nach dem freigegebenen rechten Treiberneustart hat Lauf
`582b5aefb41d44508c8928465e434a15` die Hochanfahrt mit beiden rechten Armen
erfolgreich beendet (`AT_HIGH_PREGRASP_HELD_NO_CONTACT`). Unabhängig
aufgezeichnete Fahrzeit RF27,55s/RR20,35s, davon19,83s gemeinsam. Einfahrt
vor Zielversand gesperrt: `right_front: reviewed unloaded/open state unavailable`.
Beide rechten Greifer ACT0/STA0/POS3/PRE0/FLT0: offen, seit Boot inaktiv.
Hochanfahrt erlaubt dies ausdrücklich; Einfahrt benötigt aktive Greifer.
Der Library-Ablauf übersprang bisher die vorhandene Phase
`carton_gripper_phase.py prepare` zwischen diesen Schritten.

`run_carton_cycle.py` ruft diese Vorbereitung nun nach bestätigter Hochanfahrt
und vor Einfahrt auf. Sie aktiviert bei Bedarf beide rechten Greifer und
öffnet mit rawFOR0/SPE16 unter den bestehenden vier Holds und Frische-/
Positionsprüfungen. Einfahrt erst nach `ACTIVE_OPEN_HELD`; kein Schließen an
der Hochposition. Tätigkeit und Quellenhash stehen in der Bewegungsreview.
22 Offline-Softwareprüfungen bestanden, einschließlich gesperrter Einfahrt
bei unbestätigter Vorbereitung. Keine zusätzliche Hardwareprüfung oder
Grenzlockerung eingeführt. ROSmini/N100-Runner SHA-256
`ae294751cc2d7dc502be7ad0a8917cb1af60fe2bf2917eca6fef97ef91257260`;
N100-Vorversion in `setup/tasks/carton-driver-restart-20261124/run_carton_cycle.previous.py`.
Normaler Library-Neustart13:05:02AWST, Lauf
`a77e4131d72645de9a72f03f9615d132`, vor Hardwarevorbereitung wegen kurzzeitig
abweichender Starthelfer-Version gesperrt. Danach Starthelfer auf ROSmini und
N100 identisch (`05f83c8066f118c9fad0dc0b31eb00b354ea92729d6f19f564ccc1ebd920c2dc`).
Folgelauf `1e63657fa5ba47ffac421af983d9b441`13:06:00AWST vor Foto/Planung
gesperrt: rechts hinten Controller-/Hardware-/Hold-Bestätigung nicht verfügbar.
Keine neue Arm- oder Greiferaktion. Die spätere sechssekündige lesende Aufnahme
bestätigt alle vier Holds, Verriegelungen und Hardwarezuordnungen fehlerfrei,
Watchdog in dieser Aufnahme nicht ausgelöst. Die Zeitstempel des zeitweisen
Nachweisverlusts sind inzwischen zugeordnet. Rechts hinten begann der geplante
Treiberneustart um 13:06:13 AWST. Um 13:06:19 meldete der gleichzeitig gestartete
Library-Lauf die fehlende Manager-/Hold-Bestätigung; um 13:06:39 waren wieder
vier Holds bestätigt. Der abschließende Watchdog-Zustand des gesamten
Wartungsfensters ist im folgenden RTDE-Abschnitt dokumentiert.
Datei `setup/tasks/carton-library-debug-20261124/latest-holds.json`.

Ein weiterer Live-Start wurde durch die automatische Freigabeprüfung vor
Ausführung abgelehnt: ungeklärte Controller-/Hold-Unterbrechung, reale Bewegung
möglich, erneute konkrete Nutzerfreigabe erforderlich. Nutzer darüber informiert
und Freigabe zum normalen Library-Start bei erneut bestätigten Holds angefragt.
Greifervorbereitung damit offline geprüft und installiert, noch nicht real
ausgeführt. Weiterhin Hochposition, keine Einfahrt oder Kontaktfahrt erfolgt.

Nachweise lokal `setup/tasks/carton-library-debug-20261124/`:
`after-driver-restart-high-result.json`, `after-driver-restart-entry-result.json`,
`after-driver-restart-safety.json`. Der Safety Log ordnet den Einfahrblock
korrekt vor dem Fahrziel ein; die STOP-Meldungen um12:58:57AWST gehören zum
vorangegangenen Treiberwechsel, nicht zur erfolgreichen Hochanfahrt.

## RTDE-Wiederverbindung aller vier Treiber repariert, 24.11.2026

Im Journal brachen die beiden rechten Treiber nach je drei fehlgeschlagenen RTDE-Handshakes ab. Im lokalen Nachlauf mit der bisherigen N100-Bibliothek ließ sich dieselbe Meldung reproduzieren. Auch der geprüfte [offizielle UR-Quellstand](https://github.com/UniversalRobots/Universal_Robots_Client_Library/blob/f53cd97f5b18ba3ac86c32dbae895c2f31e3c8f5/src/rtde/rtde_client.cpp#L1136) begrenzt diese Versuche. Die lokale Korrektur wiederholt den Handshake einer bereits aufgebauten Sitzung nach vorübergehendem Ausfall mit Wartezeit. Der Hintergrundleser liefert ein Paket nur bei tatsächlich eingegangenen Daten mit fortschreitendem Gerätezeitstempel. Die ROS-JointState-Header selbst stammen weiter vom Host. Während einer Unterbrechung bleibt der unabhängige native Zustand für den Vergleich erforderlich.

Der Loopback-Server lehnte beide Protokollversionen in fünf aufeinanderfolgenden TCP-Verbindungen ab. Danach nahm der neue Client wieder echte Testserverdaten an. Vier vorhandene RTDE-Serverprüfungen und 30 Library-/Review-Softwareprüfungen bestanden. Beim Start des Kartonprogramms wird der bestehende zeitlich abgeglichene Positionsvergleich für die beiden rechten Arme bereits vor Kartonaufnahme und Bahnplanung ausgeführt. Der Verbindungsaufbau kann frische Daten abwarten. Die Prüfung vor der Bewegung gilt weiterhin. Es gibt keinen zusätzlichen dauerhaften Überwachungsprozess.

Nach Nutzerfreigabe und vier bestätigten Holds beide laufenden rechten Programme regulär gestoppt. Alle vier Treiberdienste bis 13:07:44 AWST einzeln gewechselt, Bibliothek im jeweiligen Manager verifiziert und nach jedem Arm vier Holds bestätigt. SHA-256 der Bibliothek `4b763aac379fc443817d7b408e43a044d0940273133df474fdaa43566b07a604`. Vorversionen der drei installierten Dateien auf dem N100 unter `~/uwa-ur-runtime/review-candidates/rtde-recovery-20261124.BK4Oy0of/previous/`.

Bei der ersten Abnahme ergab eine Abtastlücke während der ROS-Discovery rechts vorne 0,00754 rad einschließlich Unsicherheit bei nur 0,000061 rad gemessener Abweichung. In der anschließenden stationären Messung nach Verbindungsaufbau waren die Maxima einschließlich Unsicherheit rechts vorne 0,000143 rad (13 Werte), rechts hinten 0,000339 rad (12), links vorne 0,000456 rad (20) und links hinten 0,000075 rad (14). Bestehende Grenze 0,005 rad. Endstand vier native STOPPED, max. gemessene Gelenkgeschwindigkeit je Arm 0 rad/s, vier Holds, Interlock bestätigt, Watchdog nach Dienstwechsel verriegelt und keine ausstehenden nativen STOPs. Keine Bewegung im Wartungsfenster. [Messdaten und Protokolle](../../setup/tasks/ur-rtde-recovery-20261124/).

## N100-Entlastung vorbereitet, noch nicht aktiv, 24.11.2026

Korrektur der früheren Aktivmeldung: Der folgende Stand ist im Quellbaum
vorbereitet, aber noch nicht im laufenden N100-Schutzdienst aktiviert.
Direktprüfung nach dem Kartonabbruch bestätigt Dienstbeginn11:18:24AWST,
Invocation `df2859b0d71647288c6ad914312ce72e`, alte Dateien
`hardware_nodes.py` SHA425a2455… und `hardware_ports.py` SHA684497d9… .
Die passive Aufzeichnung bestätigt weiter50Hz für Supervisor/Watchdog.

Die vorbereitete Hardware-Überwachung ist auf ereignisgebundene Managerabfragen umgestellt.
Eine bestätigte ruhende Zelle sendet keine periodische Controller-, Hardware-
oder Hold-Parameterliste. Beim Verbinden, Zustandswechsel, Reset oder Wieder-
anlauf bleiben frische Abfragen und die bestehende Ressourcensperre erhalten.
Supervisor und Watchdog würden mit20Hz statt50Hz publizieren. Die 20Hz-RTDE-
Istwerte, Gelenk-/TCP-Geschwindigkeit, 40-mm-Kollisionsprüfung, Stillstands-
fenster und native Dashboard-Rückfälle wurden nicht gelockert. Der Watchdog
verwendet auf Hardware keine zweite vollständige StopPort-RPC-Kette, sondern
behält den unabhängigen nativen Stopp bei.

## Karton-Hochanfahrt vor Zielversand gesperrt, 24.11.2026, 12:51 AWST

Nach ausdrücklichem Nutzerauftrag beide rechten `ros.urp` regulär gestoppt.
Unabhängige Aufnahme bestätigte alle vier Arme stationär mit nativSTOPPED.
Nur die zwei rechten N100-Treiberdienste neu gestartet und deren vorhandene
Sechs-Gelenk-Holds bereitgestellt. Neue Dienstidentitäten RF
`fa6155d558614f7fbf6d46b011a450c5`, RR
`a3a6757e480d4417a6a2dfae263f66c9`. Anschließend aktuelle Driver-/Native-
Winkeldifferenz RF maximal0,00007153rad, RR0,00002688rad, beide Kanäle
Geschwindigkeit0. Alle vier Holds/Interlock und Modellbindung bestätigt;
Watchdog nach dem Betriebswechsel erwartungsgemäß verriegelt. Keine
Vergleichsgrenze oder Geschwindigkeit geändert. Lesender Nachweis:
`setup/tasks/carton-library-debug-20261124/driver-after-restart.json`.
N100-STOP-/Stillstandsnachweise:
`~/uwa-ur-runtime/setup/tasks/carton-driver-restart-20261124/`.
Normaler Library-Neustart12:59:19AWST, Lauf
`582b5aefb41d44508c8928465e434a15`. Der Hochanfahrtsbericht bestätigt
die abgeschlossene Anfahrt. Der nachfolgende Einfahrschritt meldete rechts
vorne `reviewed unloaded/open state unavailable`; die Greiferregister
zeigten ACT=0 und STA=0. Diese Meldung trat vor dem RTDE-Dienstwechsel auf.
[Hochanfahrt](../../setup/tasks/carton-library-debug-20261124/after-driver-restart-high-result.json) · [Einfahrschritt](../../setup/tasks/carton-library-debug-20261124/after-driver-restart-entry-result.json).

Im Library-Lauf `a03f0f556cc842429f68fa0b4e5143b9` waren Planung und Freigabe abgeschlossen. Der Positionsvergleich rechts vorn scheiterte vor dem ersten Ziel. Größte Abweichung am Handgelenk 3: 0,009839 rad, mit Interpolations- und Uhrenunsicherheit 0,009901 rad gegenüber 0,005 rad Grenze. Handgelenk 1 wich um 0,007676 rad ab. Im Treiberverlauf rechts vorn hatten alle 2.000 Meldungen über 4,406 s exakt dieselben sechs Positionswerte bei fortschreitenden Zeitstempeln. Rechts hinten dasselbe Muster. Der unabhängige native Messkanal lieferte fortlaufend Istwerte; er registrierte für beide Arme keine Fahrbewegung oberhalb der Auswerteschwelle. Keine Arm- oder Greiferziele gesendet.

Beide rechten Treiber hatten laut Journal um 10:18 AWST ihre RTDE-Neuinitialisierung nach drei Versuchen abgebrochen. Bis zum Abbruch der Hochanfahrt erschien für beide keine erfolgreiche RTDE-Wiederverbindung im gefilterten Treiberjournal. Das spricht für die Weiterveröffentlichung eines alten Positionsstands. Der genaue Zeitpunkt des letzten vom Treiber übernommenen Gerätepakets fehlt im Fahrbericht. [Messreihen](../../setup/tasks/carton-library-debug-20261124/oak4-primary-high-result.json) · [RTDE-Journal](../../setup/tasks/carton-library-debug-20261124/right-drivers-rtde-reconnect.log) · [Safety Log](../../setup/tasks/carton-library-debug-20261124/oak4-primary-safety.json)

## OAK4-Vorrang und30-mm-Zentrumsvergleich, Nutzerentscheidung24.11.2026

Der folgende reale Library-Lauf `a03f0f556cc842429f68fa0b4e5143b9`
bestand den Kameravergleich mit14,0195mm und1,9810°. OAK4-Pose unverändert
an beide offline geprüften Parallelpläne übergeben. Der spätere Treiberabbruch
vor Zielversand ist oben gesondert dokumentiert.

Der Nutzer bestätigt den Vergleich der Boxlage aus beiden Blickwinkeln,
bevorzugt die OAK4-Lokalisierung und beauftragt30mm Grenze für den Abstand
der Zentren. Höhere OAK4-Genauigkeit ist seine Einschätzung, kein neuer
Kalibriernachweis. Bei zwei gültigen Fits bleibt nun die OAK4-Pose samt
Armbindungen exakt erhalten; die USB-OAK liefert nur die Gegenprüfung.
Bis einschließlich30mm akzeptiert, oberhalb abgelehnt. Die180°-Zuordnung
und bestehende Winkelgrenze<2° bleiben aktiv. Einzelbildkriterien, Fall
mit nur einer gültigen Kamera, Einfahrbild und N100-Schutz bleiben erhalten.
Diese Regel ersetzt die frühere gleichgewichtete Mittelung/10-mm-Grenze.

31 gezielte Softwareprüfungen bestanden. Der Offline-Nachlauf der letzten
Originale (`1bcfd25ade114d5fb8e0d834b7bcc3a3`) akzeptiert14,392mm/1,304°
im Modus `primary_checked`; Hauptkamera `oak4`, Gewichte1/0. Die resultierenden
`T_camera_object`, `T_world_object_candidate` und beide `world_object_by_arm`
entsprechen exakt den ursprünglichen OAK4-Werten. Nachweis:
`setup/tasks/carton-library-debug-20261124/oak4-primary-30mm-verified/`.
Die englische Library benennt OAK4-Pose und30-mm-Gegenprüfung ausdrücklich.

## Erneuter Library-Start nach Symmetriekorrektur, 24.11.2026

Auf ausdrücklichen Nutzerauftrag erneut über die normale Startaktion der
Power-Library auf Port39823 gestartet. Browserzugriff weiterhin nicht
verfügbar, daher derselbe HTTP-Endpunkt wie der Button. Lauf
`1bcfd25ade114d5fb8e0d834b7bcc3a3`, Start12:42:28AWST. Beide Referenzen
gültig, Programmvorbereitung sowie aktuelle Aufnahmen und beide Einzel-
registrierungen durchlaufen.180°-Umbenennung der zweiten Pose angewendet.
Restabweichung14,392mm zwischen den Grundflächenmittelpunkten und1,304°.
Die Winkelgrenze<2° ist erfüllt, die Positionsgrenze<10mm nicht. Abbruch
vor Bahnplanung, kein Fahrziel und kein Greifbefehl. Keine weitere Toleranz-,
Kamera- oder Schutzänderung für diesen Versuch. Die Symmetriefrage ist
damit vom weiterhin bestehenden metrischen Positionsversatz getrennt.
Nachweis: `setup/tasks/uwa_program_library/1bcfd25ade114d5fb8e0d834b7bcc3a3/multiview/decision.json`.

## Aufgabenbezogene180°-Symmetrie des Kartons, Nutzerkorrektur24.11.2026

Laut Nutzer sind alle vier Wände bedruckt; für den symmetrischen Kartongriff
ist die Unterscheidung zweier180°-Darstellungen unnötig. Die Nachfrage nach
einem eindeutigen Vorderseitenmerkmal ist damit überholt. Der Kameravergleich
berücksichtigt diese Gleichwertigkeit nun vor der Mittelung. Die zweite Pose
wird samt Eckursprung um den Grundflächenmittelpunkt zur Darstellung der
Hauptkamera zugeordnet. Verglichen/gemittelt wird die physische Mittelpunktslage;
die Rotation wird erst nach der Zuordnung gemittelt. Primärer Kartonframe,
Armrollen und bestehendes Greifrezept bleiben in dieser Darstellung erhalten.
Keine zusätzliche90°-Symmetrie und keine Änderung von Bild-, TCP- oder
Geschwindigkeitsgrenzen. Die vollständige Bahn-/Kontaktprüfung bleibt nötig.

28 gezielte Kalibrier-/Multiviewprüfungen bestanden, darunter identische
Kartonlagen mit vertauschten Eckursprüngen, Rotationsmittelung über180°, echte
Translation und der nicht gleichwertige90°-Fall. Offline-Nachlauf der letzten
Originale:12,987mm Mittelpunktsabstand/2,954° Restwinkel. Die alte
518,125mm/177,046°-Rohabweichung war weitgehend ein Framewechsel; der
verbleibende Messwiderspruch liegt weiter außerhalb<10mm/<2°. Daher noch
keine freigegebene Mittelpose oder Roboterfahrt. Nachweis:
`setup/tasks/carton-library-debug-20261124/symmetry-aware-comparison/decision.json`.
Geändert ist nur die ROSmini-Posenauswahl, nicht der laufende N100-Schutz.

Zusätzlicher Offline-Nachlauf mit der vorhandenen, auf drei Messanfragen
begrenzten Hydrogen-Nachmessung: lokal akzeptierte OAK4-Neumessungen
verbleiben symmetriebereinigt bei15,107mm Mittelpunktsabstand und1,621°
zur ursprünglichen USB-Pose. Die Winkelgrenze wird dabei erfüllt, die
Positionsgrenze weiter nicht. Keine Live-Suchfenster übernommen und keine
weitere Kamera-/Roboteraufnahme. Bericht:
`setup/tasks/carton-library-debug-20261124/symmetry-refinement/summary.json`.

## Live-Library und Flächenzuordnung im Zweikameralauf, 24.11.2026

Auf Nutzerauftrag den fertigen Zweikamera-Stand übernommen.22 gezielte
Kalibrier-/Multiviewprüfungen zusätzlich ausgeführt, alle bestanden. Der
gemeinsame `carton_camera_session.py` stimmt nun auch auf dem N100 mit
ROSmini überein (SHA-256 `801ad60c93474c317cf1859afb81db801a4f6080673f5223dbf66dbf1ffe519c`),
vorherige Datei unter `~/uwa-ur-runtime/review-candidates/camera-reference-shared.r7EMw2CJ/previous.py`.
Kein Schutzdienstwechsel;15%-Toleranz bleibt aktiv. Library des Power-Fensters,
Port39823, wird verwendet; Browsersteuerung weiterhin nicht verfügbar.

Lauf `7e14069f070d442e9a2bbd236aab01a2` um11:43:22AWST bestätigte die
Programmvorbereitung und erfasste beide frischen nativen Ansichten. Abbruch
vor Planung:518,125mm/177,046° zwischen den unabhängigen Posen. Die rein
diagnostische180°-Umrechnung verbleibt bei13,423mm/2,954°.
Beide Registrierungen akzeptierten nur Modellfläche4 (`y=0`). Fläche3
gegenüber enthält in ihrer Referenztextur einen gespiegelten Schriftzug.
Ein isolierter Offlineversuch berücksichtigt ihre Außenansicht mit korrekt
rückwärts zugeordneten UV-Punkten. Beide Bilder ergeben dann Hypothesen
für Fläche3 und4, bleiben aber mehrdeutig. Keine der85 kamerübergreifenden
Hypothesenpaarungen erfüllt<10mm/<2°; beste Positionen liegen etwa20,3mm
auseinander. Keine aktive Modell-/Referenzänderung und keine gelockerte
Bildgrenze. Die damalige Nachfrage nach einem eindeutigen Wandmerkmal ist
durch die oben dokumentierte Nutzerkorrektur zur180°-Symmetrie überholt.

Die passive180-s-Aufzeichnung02 endete regulär. Im aufgezeichneten Lauf
größtes natives Zustandsalter am Guard je Arm<55ms. Der separate
Diagnoseempfänger hatte Empfangspausen bis363ms; dies belegt keinen gleich
langen Ausfall der nativen Quelle. Diagnoseablage
`setup/tasks/carton-library-debug-20261124/`: `library-start-record02.jsonl.gz`,
`outward-probe-*`, `panel-hypotheses.json`. Keine Armfahrt oder Greifaktion.

## Frischeabbruch vor dem Zweikamera-Kartonstart, 24.11.2026

Lauf `93f12452b4374e7e97d10e3822e4bf1b` brach um 11:41:36 AWST vor Play, Kartonaufnahmen und Bahnversand ab. Im N100-Lauf `skill-library-carton-487019f1b2214ca38c95baf7e75e8fc7` stehen beide rechten Arme als für Play vorgesehen, die Dashboard-Befehlslisten sind leer. In `browser-play.json` fehlen bereits die ersten Hold-Ergebnisse. Der Fehler kam beim Verbinden oder beim anschließenden Warten auf den Watchdogzustand. Der Client hatte ein frisches Zellpaket mit vier Armzuständen, beim Einzelbefund links hinten war das Empfangs- oder Quellalter größer als 200 ms. Beide Einzelwerte und die Geschwindigkeit beim Abbruch fehlen im Fehlerlog. Der Safety Log verzeichnet im Startfenster keinen neuen nativen STOP. Der nächste Lauf `7e14069f070d442e9a2bbd236aab01a2` bestätigte die vier Holds und nahm beide Kamerabilder auf. Sein späterer Abbruch beim Kameraposenvergleich ist ein eigener Befund. [Fehlstart](../../setup/tasks/uwa_program_library/93f12452b4374e7e97d10e3822e4bf1b/progress.json) · [Safety Log](../../setup/tasks/carton-library-debug-20261124/dual-camera-start-safety.json) · [Folgelauf](../../setup/tasks/uwa_program_library/7e14069f070d442e9a2bbd236aab01a2/progress.json)

Seit dem Folgeauftrag auf dem N100 installiert. Nach der ROS-Erkennung wartet der Library-Start vor Play bis zu fünf Sekunden gemeinsam auf frische native Zustände aller vier Arme und aktuelle Meldungen von Guard, Supervisor und Watchdog. Bei Fristablauf enthält `browser-play.json` unter `startup_timeout` Phase, Grund und je Arm Quell- und Empfangsalter oder einen fehlenden Messwert. Das Profil fordert weiterhin höchstens 200 ms alte Armdaten. Im Offline-Nachlauf mit simulierten Nachrichten traf nach 0,45 s eine gemeinsam gültige Lage ein. Bei dauerhaft 226 ms Quellalter und 20 ms Empfangsalter blieb der Start gesperrt. Auch fehlender Watchdog, Modellfehler und fehlende Erstdaten wurden offline geprüft. 28 bestehende Softwaretests bestanden. ROSmini und N100 haben für den Starthelfer denselben SHA-256 `43eb1739eaa78e3bd27d163c616505e6dd597b9709c3e27db121c6afc5ad1582`. Vorversion auf dem N100 in `~/uwa-ur-runtime/review-candidates/carton-start-freshness.GrzaVHME/previous.py`. Eine reale Fahrt wurde dafür nicht ausgelöst.

## Zweite OAK-Perspektive im Kartonprogramm, 24.11.2026

Nutzerauftrag: OAK Pro gegenüber der OAK4 im **Supported carton grasp**
verwenden. Zwei unabhängig gültige Posen mitteln, bei schwächerer Gegensicht
Anwesenheit am projizierten Ort prüfen und bei Verdeckung weiterhin die
bisher ausreichend sichere Einzelpose zulassen. Der Nutzer hat den Versand
aktueller Karton-Bildausschnitte und Overlays an Gemini Hydrogen über das
vorhandene Antigravity-Konto nach einer automatischen Freigabeablehnung
ausdrücklich erlaubt. Lokale USB-Konfiguration `gemini_enabled: true`.

Implementiert auf ROSmini: eigene USB-Optik-/Sitzungsdatei, vorhandener
N100-USB-Aufnahmepfad, native ungedrehte4056×3040-Pixel, kamerabezogene
Hydrogen-Suchkoordinaten, sphärischer Orientierungsmittelwert bei gleicher
Gewichtung, strikte Einzelbild-Fits und gesonderte kategoriale Zweitbildprüfung.
Gemeinsamer Posevergleich zunächst unter10mm/unter2°, übernommen aus den
vorhandenen Registrierungsgrenzen. Bei Widerspruch keine Pose an die Planung.
Keine Änderung an N100-Ausführungsquellen, Tempo oder Live-Schutz.
[Bedienung und konkrete Rückfallregeln](docs/carton_multiview.md).

Reine Kameraaufnahme24.11.11:31AWST: OAK Pro/Fokus112,
16rechte Boardmarker,1,1907px Prüf-RMS, eigene Referenz gültig bis23:31:11AWST.
Aktuelle Originalfotos beider Kameras wurden anschließend offline ausgewertet.
Beide lokalen Fits bestanden ihre bisherigen Einzelbildkriterien, haben aber
eine annähernde180°-Mehrdeutigkeit des Kartonframes. Unveränderte Rohposen
unterscheiden sich um519,403mm/177,747°. Eine ausschließlich diagnostische
180°-Rechteckumrechnung ergibt10,679mm/2,253° und bleibt ebenfalls außerhalb
der Grenzen. Keine automatische Symmetrieumdeutung und keine Mittelpose
freigegeben. Die richtige Zuordnung der gegenüberliegenden bedruckten Wand
zum gemeinsamen Kartonframe bleibt fachlich offen.

Gemini Hydrogen Low bestätigte in der echten OAK-Pro-Aufnahme den Karton
an der aus der gültigen OAK4-Pose projizierten Stelle (`confirmed`). Das
belegt den Anwesenheitspfad, löst aber den metrischen Widerspruch nicht und
setzt dessen Ablehnung nicht außer Kraft. Kein realer Programmlauf und keine
Roboterbewegung für diese Erweiterungsprüfung gestartet.

35gezielte Offline-Softwareprüfungen bestanden; JavaScript-Syntax mit Node-VM
geprüft. Die beiden lokalen Library-Endpunkte39823 und8780 mit neuer
Konfiguration lesend bestätigt, beide Kamerareferenzen verfügbar. Nur die
Webserver wurden aktualisiert. Browserzugriff des Agenten ist weiterhin
nicht verfügbar; keine GUI-Klicks oder visuelle Browserprüfung behaupten.
Bild-/Messnachweise: `setup/tasks/carton-multiview-20261124/`, insbesondere
`image-check/multiview/decision.json` und `image-check/cross-view-check/result.json`.

## Schnellere Kamerapfade der Programmbibliothek, 24.11.2026

**Supported carton grasp** startet auf ROSmini eine native OAK4-Sitzung
mit dem in der Kamerareferenz hinterlegten Fokus. Sie beginnt parallel
zur Aufnahme des N100-Ausgangszustands und liefert die frischen
Standardfotos für Registrierung und offene Einfahrt. Beide verwenden
einen SDK-Prozess und dieselbe Kamera-Lease. Der Pfad gibt die Kamera
nach dem Einfahrfoto oder beim Abbruch frei. Das zweite Bild und seine
Metadaten gehen zusammen in einer Übertragung an den N100.

Die feste OAK4-Standardaufnahme des Objekt-Scan-Bootstraps und der
direkten Aufnahme ohne GUI verwendet eine Metadaten-gesteuerte Einlaufzeit.
Die separate Library-Kalibrierung probiert ein natives Einzelbild mit
bekanntem Fokus und prüft die zurückgehaltenen Marker. Bei unzureichendem
Fit folgt die bisherige Fokus-/Belichtungssuche. In einem isolierten
Library-Lauf waren 17 Marker und 1,35 px Prüf-RMS nach 9,44 s bestätigt.
Drei frühere Suchläufe brauchten 22,24–25,04 s. Der SHA-256 der gemeinsam
genutzten Kamerareferenz blieb beim Prüflauf gleich.

Zwei native Auslösungen in einer laufenden OAK4-Sitzung lieferten das
Bild nach je 0,66 s an ROSmini und speicherten es nach 2,56 bzw. 2,51 s.
Die früheren Einzeltransaktionen der Library brauchten 10,78–12,47 s
einschließlich Neustart. USB-Einzelaufnahme bei Fokus 112 auf dem N100
14,88 s nach Übernahme des geprüften Workers, gegenüber 15,06 s vorher.
Die frühe USB-Variante mit stärkerem Clipping wurde verworfen.
Die Sechskamera-GUI betreibt beide OAKs und ihre Wrists bereits warm.
Wrist-HD-Kalibrierung verwendet native Bursts und protokollierte
Kameraeinstellungen. HQ, HDR, Tiefen- und RGB-D-Pfade nutzen ihre
jeweiligen Sensor- und Ausgabemodi. Der Nachweis für die neue Pipeline
besteht aus Kameraaufnahmen und Offlineprüfungen.
[Messberichte](../../setup/calibration/oak_pipeline_20261124/)
und [Bedienung](docs/camera_library_program.md).

## Gelenkgeschwindigkeitstoleranz im Kartonpiloten, 24.11.2026

Der Nutzer beauftragt15% Toleranz im Wächter: bei0,1rad/s Sollmaximum
bis0,115rad/s gemessene Armgelenkgeschwindigkeit akzeptieren, darüber stoppen.
Beide Prüfungen sind profilgebunden vorbereitet: `GuardState` und
`PilotGuardChannel`/`MotionEnvelope.check_measured`. Planprüfung, Solltempo
und TCP-Grenze bleiben unverändert. Die Toleranz ist Teil der Guardsignatur;
der Pilotstatus nennt sie und die tatsächliche Gelenkauslöseschwelle.
Andere Profile behalten ihre bisherigen Schwellen. Zusätzliche Fingerkoordinaten
behalten ebenfalls ihren bisherigen Faktor.

35 gezielte Offlineprüfungen für Grenzen einschließlich exakt0,115 und
knapp darüber, TCP-/Planungsgrenzen, Signatur, Parametervalidierung und den
Pilotkanal bestanden auf ROSmini und im inaktiven N100-Kandidaten
`~/uwa-ur-runtime/review-candidates/joint-tolerance15.2BHwmKi7/`.
45 weitere bestehende Kern-/Kartonprüfungen auf ROSmini bestanden.
Die fünf betroffenen aktiven Dateien stimmen mit der lokalen Ausgangsversion
überein und sind unter `setup/tasks/carton-library-debug-20261124/tolerance-active-before.tar`
gesichert. Der Nutzer hat den Schutzdienstwechsel einschließlich regulärem
Beenden und Wiederstarten von `ros.urp` ausdrücklich beauftragt.
Aktiv seit24.11.11:18:24AWST, Invocation `df2859b0d71647288c6ad914312ce72e`.
Die ursprüngliche Stoppfunktion bestätigte mechanischen Stillstand und vier
Ressourcenholds. Im neuen Guardpaket stehen Toleranz0,15, keine aktiven
Fehler, passendes Treibermodell und vier stationäre Arme; der Supervisor
bestätigt vier verriegelte Holds. Watchdog bleibt nach Neustart zunächst
verriegelt. Guardsignatur `91a0e715dcf4156210ba997c68f0214ab7158ffcb69a25fa5907f594ff85392e`.
Die Laufkopie liegt unter `activation.ooqfIa87` im Kandidatenverzeichnis,
die vorherigen fünf Dateien unter dessen `previous/`. Der erste Skriptaufruf
endete vor Robotereingriffen an `set -u` während ROS-Setup; der korrigierte
Aufruf hat den Wechsel abgeschlossen. Der reguläre Vierarm-Neustart via
`power.sh start` bestätigte kein laufendes Programm: der nach Dienstwechsel
verriegelte Watchdog forderte bei jedem Play erneut nativen STOP an.
Safety-Log und enges Guardjournal ordnen diese Stopps ausdrücklich dem
Watchdog zu, nicht der neuen Geschwindigkeitstoleranz. Anschließend wurde
der vorhandene Library-Start über dessen normalen HTTP-Endpunkt ausgeführt,
weil der Browserzugriff weiter ausfiel. Lauf `c720294d06cb49f3950c0a788e177844`
startete24.11.11:22AWST. Dessen vorhandener Start unter unbeladenen Holds
setzt den Software-Watchdog regulär zurück; beide rechten Programme wurden
bestätigt, danach begann die aktuelle OAK4-Aufnahme. Kein neuer Start-Bypass
und keine Änderung des Watchdogs. Der Lauf erreichte Foto, Registrierung,
Offlineplanung und automatische Anfahrfreigabe. Um11:23:06AWST forderte
der Supervisor wegen veralteter Hardware-Verwaltungsbestätigungen nativen
STOP für alle vier Arme an (rechts vorne52,880s, rechts hinten51,942s seit
letztem Verwaltungsbefund). Der Watchdog folgte. Die Hochanfahrt endete vor
dem ersten Fahrziel; beobachtete Bewegung beider rechten Arme0s. Diese
Zeitwerte belegen keine tatsächliche Antwortdauer der Dienste, weil die
Abfragen im bestätigten ruhigen Hold absichtlich pausieren. Der Anlass,
warum die Wiederverwendung endete, ist noch nicht nachgewiesen.

Eine endliche passive Aufzeichnung der vorhandenen Guard-/Supervisor-/
Watchdog-, Manager- und Parameterereignisse wurde vor dem nächsten
Library-Start bereitgestellt; kein neuer Schutzwächter oder Aktionsclient.
Dieser nächste Start `e3ad6d5d2b0946918e656cf30576eb3f` um11:27:48AWST
endete jedoch schon im Versionsvergleich von `carton_camera_session.py`.
Seit11:24 wurden parallel im Workspace Kamerastart/-registrierung und
zugehörige Tests geändert. Diese fremden laufenden Änderungen wurden
erhalten und nicht ungeprüft auf den N100 übertragen. Ihr Fertigstellungs-
und Übernahmestand ist beim Nutzer angefragt. Die bestehende Speed-
Toleranz ist weiterhin aktiv. Passiver Zwischenstand: vier stationäre,
verriegelte Holds, alle Programme nach dem Abbruch gestoppt. Diagnosepfade
`library-resume-safety.json`, `library-resume-stops.log`,
`library-start-record01-summary.json` in der heutigen Diagnoseablage.
Alle vier Arme meldeten vor der Vorbereitung wieder
`RUNNING/NORMAL`, `PLAYING` und bestätigte Reverse-Verbindungen.

## Schrittweise Library-Diagnose, 24.11.2026

Nutzerauftrag: **Supported carton grasp** über den normalen Library-Start
gemeinsam schrittweise diagnostizieren. Der Browserzugriff des Agenten ist
nicht verfügbar; der Nutzer bedient die Library, der Agent liest die Laufdaten.
Die vorhandene Library wurde mit `setup/skill_library/live-carton.json` auf
`http://127.0.0.1:8780` gestartet. Die alte Kamerareferenz war um03:10:30AWST
abgelaufen. Nutzer bestätigte die Anzeige und startete die separate Kalibrierung.
Lauf `f8a787799552491ba0141d2dd148bcc3` erfolgreich:17Marker,1,47px Prüf-RMS,
neue Referenz gültig24.11.10:36:14 bis22:36:14AWST.

Nach bestätigtem freiem Arbeitsbereich startete der Nutzer den Kartonlauf
`a54b414cabb94ecc9a506b978f616098` um10:36:48AWST. Abbruch vor Foto und
Planung um10:36:56: `right_front` benötigt **power on**. Keine Bahn gestartet.
Der Nutzer führte anschließend **UWA Robot Power → Start + ROS** aus.
Dieser Bedienlauf10:37:19–10:39:39AWST endete mit `success:false`.
`left_front` meldet `NO_CONTROLLER`; bei den drei anderen Armen sind die
Antriebe danach `RUNNING`, aber das Programm `STOPPED` (`play_not_confirmed`).
Die GUI-Sitzung `setup/logs/uwa-control/sessions/20261124_103227_7888_52ab14cb/`
belegt die einzelnen Power-/Brake-/Play-Antworten. Nächster Schritt ist die
Pendantmeldung links vorne und die fehlgeschlagene ROS-Programmvorbereitung
zu klären, bevor erneut ein Kartonlauf gestartet wird. Die Startsperre
wegen abgelaufener Referenz und fehlende Antriebsvorbereitung sind getrennte
Befunde; sie erklären noch nicht den Bewegungsabbruch des Vortags.

Der letzte Lauf vom23.11.16:30AWST (`ca53f028852e4b1e8b685f508ce7021e`)
hatte Registrierung, Planung und automatische Anfahrfreigabe erreicht.
Sein N100-Workflow bestätigt14,951s gemeinsame beobachtete Bewegung der
rechten Arme vor `Reviewed arm group interlocked`. Eng eingegrenztes
Guardjournal belegt23.11.16:32:14AWST als Auslöser `right_rear`, gemessene
Gelenkgeschwindigkeit0,100462608rad/s bei geprüfter Grenze0,1rad/s;
TCP0,07630394m/s bei0,08333333m/s Grenze. `REVIEWED EXECUTION OWNER LOST`
folgte erst danach. Keine Tempo-/Grenzwertänderung.

Nachfrage des Nutzers zur Kopplung von Planungs- und Abschaltgrenze:
Der gespeicherte Hochanfahrplan erreicht rechts vorne0,0999999302rad/s
und rechts hinten0,0999999410rad/s (jeweils Handgelenk3), bei0,1rad/s
geprüfter Grenze. `MotionEnvelope.check_measured` vergleicht jeden
ausgewerteten nativen Messwert direkt mit `>` gegen dieselbe Grenze;
keine Toleranz oder Mindestüberschreitungsdauer in diesem Vergleich.
Die protokollierten0,100462608rad/s lagen0,4626% darüber. Damit fehlt
praktisch eine Reserve zwischen geplantem Sollmaximum und Abschaltschwelle.
Diese Analyse ist keine Freigabe einer Tempo- oder Wächteränderung.

Beim heutigen regulären Hochfahren meldete der Guard unter anderem native
Gelenkgeschwindigkeiten links hinten−0,139669rad/s (10:37:22,Index3),
rechts vorne0,237407rad/s (10:38:08,Index3) und rechts hinten0,203426rad/s
(10:38:59,Index4), jeweils gegen0,1rad/s. Diese Werte gehören zur
Antriebsvorbereitung; keine Kartonbahn war aktiv. Beim anschließenden
External-Control-Start wurden native Hardwarebestätigungen als veraltet
gemeldet. Die Reverse-Verbindungen entstanden und brachen kurz darauf ab.
Der zeitliche Befund ist gesichert, die vollständige Ursache noch offen;
keine neue Guard- oder Native-Stop-Änderung daraus ableiten.
Neue Diagnoseablage: `setup/tasks/carton-library-debug-20261124/`, mit
`previous-motion-guard.log`, `startup-runtime.log`, `startup-drivers.log`,
Status-Snapshots und dem Safety-Bericht (Journalabdeckung dort nur teilweise).

Lesender Nachlauf am24.11.: `power-status-recheck.jsonl` meldet links vorne
inzwischen `unreachable`, die anderen drei Antriebe `RUNNING` mit Programm
`STOPPED`. Ein direkt empfangenes Supervisorpaket (`supervisor-status.yaml`)
bestätigt alle vier Ressourcenholds und Verriegelungen bei `state: STATE STALE`.
Die drei erreichbaren Arme verwenden bestätigte stationäre Holds. Links vorne
fehlt weiterhin ein aktuelles natives Stillstandsfenster (`samples:0`);
die Dashboard-STOP-Antwort läuft dort in einen Timeout. Ein bestätigter
ROS-Halteregler ersetzt diesen fehlenden nativen Zustandsnachweis nicht.
Die Pendantmeldung ist beim Nutzer angefragt und steht aus.

Aktive N100-Quellen lesend abgeglichen: `hardware_nodes.py` SHA-256
`425a2455e517ae7c07e89ed3446e762ec365041e8a9e2ba004546a18094dfc36`,
`hardware_ports.py` `684497d91490af406016a72d74fd228be9e228c92a15c2c27ef9b22d03e06cbe`.
Der lokale Stand zur identischen Manager-Nachricht bei Teilhold ist weiterhin
nicht installiert. Keine Guardänderung, kein Reset und kein weiterer Play-
oder Bewegungsversuch im lesenden Nachlauf.

## Hydrogen-Nachmessung für Supported carton grasp, 23.11.2026

Der Library-Bildpfad gibt Hydrogen Low den verworfenen Fit mit Fehlermaßen
und Modelloverlay. Hydrogen kann im selben Dialog bis zu drei Messungen
über Bildregion oder sichtbare Vorderwandecken anfordern. Der lokale
geometrische Fit verwendet die Originalpixel. Auf dem vorher verworfenen
Bild ergaben sich zwei gültige Hypothesen mit 2,535 mm und 0,559°
gegenseitiger Abweichung. Die Offline-Bahnprüfung fand gemeinsame
Hochanfahrt und Einfahrt für rechts vorne und rechts hinten. 19 Tests
bestanden. Registrierungsquelle auf ROSmini und N100 abgeglichen. Ein
neuer realer Griff steht aus.
[Bilddialog, Fit und Bahnprüfung](work/carton-hydrogen-feedback-20261123.md)

## Kraftabhängiger Kontaktsuch-Skill in Gazebo, 23.11.2026

`seek_contact` kombiniert geplante Vorposition, Zustellung bis zur
tarierten axialen Handgelenkskraft und geprüften Rückzug aus gemessenen
Gelenkständen. Zwei vollständige Home-Kartonläufe mit gleichem Rezept,
2 N Schwelle und 20 mm/s Prozessvorschub erreichten DONE. Die lokal
um 2 mm vorstehende Fläche wurde nach 3,355 statt 5,348 mm erkannt.
Beide Kontaktpaare bestätigten den Treffer und beide Kartons wurden
abgesetzt. 10-ms-Auslösewerte 26,0/29,9 N, Physikschrittspitzen
175,5/196,2 N. Kraftgeregeltes Zeichnen ist weiter offen.
[Bedienung](docs/seek_contact.md) · [Kraft-Weg-Vergleich und Rohdaten](../../setup/tasks/seek_contact_20261123/report/report.md)

## Externe Kameras in Gazebo und Zellansichten, 23.11.2026

Die Kalibrierung aus den 15 Sechskamerasätzen ist im Standardlayout für
Simulation und Darstellung übernommen. TF hängt beide optischen Zentren an
`right_charuco`. Das aktuelle Modell ergibt in `world` die Zentren
(1,2870; 0,0372; 2,1160) m und (−0,8509; 0,0132; 2,1249) m.
Gazebo-Modelle, CameraInfo, die beiden RViz-Sichtpyramiden und die statischen
TFs wurden in einer separat gerenderten, ruhenden Zelle ausgelesen. Die
relative Transformation stimmt numerisch mit der Posendatei überein.
[Gerenderte Ansichten](../../setup/calibration/external_pair_20261123/gazebo_kameraansichten.jpg)
und [Bedienung](docs/oak_overview.md). Die USB-OAK hat einen eigenen
RGB-Bildstrom und das Gehäuse aus `depthai_descriptions`. Neue
Greifszenen, Karton- und Zeichnungs-Vorschauen berücksichtigen die Kameras.
Die parallel laufende Greifsimulation behielt ihren gespeicherten Weltstand.
Die zwei älteren Offline-Prüfungen zur vollständigen Tischabdeckung des
nominalen Entwurfs und zur OAK-Pose des historischen Basisprofils vom
12.11. scheitern identisch auf dem unveränderten Quellstand. Die übrigen
17 Prüfungen der beiden bestehenden Kameratestdateien sind erfolgreich.

## Wiederholte Bewegungsfreigabe beim Kartongriff, 23.11.2026

Ausgangsbefund vor der Änderung. Lesender Abgleich mit der N100-Freigabedatenbank. Für `carton_supported_grasp` ist Vertrauen 100 gespeichert. Die Anfragen um 15:11:51 und 15:27:06 AWST hatten beide Risiko `high`, den Standardgrund „Operator review requested for this approach.“ und keinen zusätzlichen Programmstart. Beide Bedienerfreigaben wurden gespeichert. Der Browser übergibt für die Anfahrt keine Risikobewertung. Der Runner setzt dann `high`, während `Confident` höchstens `medium` automatisch übernimmt. Das gilt unabhängig von der Zahl vorheriger Freigaben. Für den Kontakt fordert dieser Browserpfad die Bedienprüfung des aktuellen Einfahrbilds an. [Bedienung](docs/carton_motion_review.md)

Auf Nutzerauftrag ist das schrittbezogene Lernen für kommende Kartonstarts auf dem N100 installiert. Eine frühere Bedienerfreigabe oder ein erfolgreich abgeschlossener gleicher Schritt senkt die Unsicherheit einmal auf Medium. Der Vergleich verwendet Rezeptrevision, Prüfphase, Reihenfolge der Armgruppen und Tempo. Ein später abgebrochener, ausdrücklich genehmigter Lauf zählt als geprüft. Eine spätere Ablehnung oder Neuplanungsanfrage für den passenden Schritt verwirft diese Grundlage. Ein Kontakt mit noch ungeprüftem aktuellem Einfahrbild verlangt weiter eine Bildentscheidung. Im lesenden Nachlauf beider heutigen gespeicherten Pläne lieferte die vorhandene Bedienerfreigabe `5506221212b34d7aa9a6dc3e7c06e02b` Medium, eine geänderte Phasenfolge oder ein anderes Tempo High. Runner auf dem N100 SHA-256 `aafe3af157c870af8ef70f6faa1ebdece5b5b2c087f5deb743db5216a4103098`, Vorversion in `~/uwa-ur-runtime/review-candidates/carton-familiarity.drWJ7ndT/previous.py`. Kein realer Programmlauf zur Prüfung ausgelöst.

Zur früheren Kameraanfahrdiagnose ordnet der Nutzer die gemessenen 0,262 rad/s als über dem Plan ein und hält Gelenkgeschwindigkeiten unter 0,3 rad/s für sich genommen für unbedenklich. Das ist seine Einordnung des Messwerts. Die eingestellten Fahr- und Überwachungsprofile wurden bei dieser GUI-Auskunft beibehalten.

## Haltezustand beim Start von Supported carton grasp, 23.11.2026

Der Browserlauf von 15:12 AWST brach vor dem ersten Ziel der Hochanfahrt
ab. Im letzten nativen Messwert standen alle vier Arme bei 0 rad/s. Eine
spätere Abfrage ergab vier freigegebene Arme ohne Ressourcenhold. Bei
bereits laufendem External Control übersprang der alte Startpfad die
Haltevorbereitung. Der bisherige Phasenbericht enthielt die auslösenden
Supervisorflags nicht. [Laufbericht](../../setup/tasks/carton-holds-20261123/high-result.json)

Auf dem N100 sind Kartonstart und Phasendiagnose aktualisiert. Der Browser
prüft die Holds vor Foto und Planung und fordert bei bestätigtem unbeladenem
Stillstand fehlende Verriegelungen beim Supervisor an. Der Safety Log auf
ROSmini berücksichtigt auch die Workflowverzeichnisse der Program Library.
28 vorhandene Offlineprüfungen bestanden. Beim erneuten realen Start um
15:26 AWST waren alle vier Holds bereits bestätigt. Das Anfordern fehlender
Holds wurde separat im Offline-Nachlauf geprüft. Nach der Bedienfreigabe
endete der Versuch vor dem ersten Ziel. Schon um 15:26:19 AWST unterbrach
sich das native Programm rechts vorne, kurz darauf links vorne. Der neue
Kartonstart wertet die native Programmrückmeldung vor dem Foto aus.
Das per SSH abgerufene Pendantlog bestätigt einen Empfangstimeout auf
`reverse_socket` rechts vorne. Die geladene Konfiguration nennt 40 ms.
Der genaue Ort der Telegrammlücke ist offen. Die Protokolle und der
separate spätere STOP rechts hinten stehen im Arbeitsbericht.

Passive Aufzeichnung am 23.11. beim regulären Wiederanlauf um 16:13 AWST.
Die Reverse-Verbindung rechts vorne blieb über 2 min 35 s offen.
Der größte gemessene Abstand ausgehender Pakete betrug 11,923 ms.
Der Lauf endete schon bei der OAK4-Posebestimmung. Standard- und
Hydrogen-Fenster lieferten für das aktuelle Bild keine gültige Lage
mit Tischauflage. [Messbericht](work/carton-program-holds-20261123.md)
[Arbeitsstand und Nachweise](work/carton-program-holds-20261123.md)

## Sechskamera-Aufbau in der Program Library, 23.11.2026

Nutzerauftrag: den erfolgreichen Aufbau mit vier Beobachtungsposen und der
Sechskamera-GUI dauerhaft als Programm speichern. Eigene Karte **Multi-camera
calibration capture** (`multi-camera-calibration-capture-v1`), zusätzlich zur
kamerareinen **OAK4 camera calibration**. **Start capture setup** exportiert
aktuelle, lesende RTDE-Zustände und die N100-Modellbindung, plant auf ROSmini
neue Wege, führt die SHA-gebundene serielle Folge über den vorhandenen
HardwareClient aus und öffnet danach die normale native GUI. Alle Arme müssen
vorbereitet, unbeladen und der Arbeitsraum freigegeben sein. Kein automatisches
Power/Reset/Standby. **Open capture GUI** funktioniert ohne Robotervorbereitung
oder gültige OAK4-Referenz. Ein bekanntes aktives Fenster wird wiederverwendet;
die PID wird mit ihrer Prozessstartzeit geprüft.

Die auftragsbezogenen0,09rad/s bleiben erhalten, aktive Grenzen unverändert.
Laufkopien der zwei Hilfsskripte werden separat auf den N100 übertragen; keine
Installation der parallel bearbeiteten Guard-Dateien. Bestehende Zielstellungen
innerhalb der bisherigen0,0005rad-Starttoleranz werden ausgelassen.
Keine neue gemeinsame Kalibrierung oder12h-Gültigkeit durch Öffnen der GUI.
[Bedienung und Abgrenzung](docs/multi_camera_library_program.md).

Prüfung23.11.:30 Tests für Library-Routing, Fehlerreihenfolge, Fenster-
Wiederverwendung und bestehende Board-/Sechskamera-/Dauerstream-GUI erfolgreich;
Python-Kompilierung, JavaScript-Syntax und `git diff --check` ebenfalls.
Die untätige ROSmini-Bedienoberfläche samt Library-Server wurde neu geladen.
Am laufenden API sind alle drei Karten vorhanden und beide neuen Aktionen
verfügbar. Keine neue Roboterfahrt oder Kameraaufnahme für diese Einbindung.
Die Browser-Fernansicht war nicht erreichbar; die neue Webseite wurde deshalb
nicht visuell abgenommen. Der reale automatische Library-Gesamtlauf wurde
nicht erneut ausgeführt; die frühere Vierarmfahrt bleibt dessen bisheriger
Hardware-Nachweis.

## Externe Kameras im rechten Tischboardrahmen, 23.11.2026

Sitzung `six_camera_mobile/20261123_143953_b34a17a2`, 15 Sätze. Auf
ROSmini liegen die Auswertung und die beiden titanpc-Messprotokolle unter
`setup/calibration/external_pair_20261123/`. Die Extrinsiken beziehen sich
auf die optischen Zentren der unverändert orientierten nativen Farbbilder.
Ursprung von `right_charuco` ist die obere linke Musterecke. Z weist in
die Platte. Die Messung verwendet beide festen Muster mit 40-mm-Feldern.
Ihre gegenseitige Lage ist frei geschätzt. OAK4 bei Fokus 107 mit vorhandenem
8000×6000-Profil, USB-OAK bei Fokus 112 mit 4056×3040 und neu bestimmter
Brennweitenskala. Die Kamerazentren im rechten Musterrahmen liegen bei
(0,9315; 0,0628; −1,2130) m und (−1,2064; 0,0868; −1,2219) m.
Der Abstand beträgt 2,1380 m. Diese Auswertung ist eine gespeicherte
Offline-Kalibrierung. Betriebsprofil, TF und Kartonreferenz sind separat.

Alle 90 Originale mit tatsächlichem SHA-256, abgeschlossenem Gemini-Hydrogen-
Review (High) und ausgewähltem Detektorbericht abgeglichen. 85 bestätigt,
vier Wrist-Fotos unsicher, eines ohne sichtbares Zielboard. Alle 30 OAK-Fotos
bestätigt. Separater Stereofit allein am mobilen 38-mm-Board ergibt 2,1222 m
Abstand und weicht in der relativen Pose um 19,96 mm und 0,619° ab.
[Ergebnis und Reproduktion](../../setup/calibration/external_pair_20261123/Ergebnis.md).

## ChArUco-Fotoprüfung über Antigravity, 23.11.2026

UWA Camera Capture registriert seine neuen Sitzungen bei der persistenten
Warteschlange auf ROSmini. Die laufende Bedienersitzung
`six_camera_mobile/20261123_143953_b34a17a2` wurde einschließlich ihrer ersten
Fotos übernommen. Der aktivierte Benutzerdienst `uwa-gemini-charuco.service`
bearbeitet fertige Kamerafotos auch nach Fensterschluss. Pro Auftrag werden
Quellbild und OpenCV-Evidenz über SHA-256 zugeordnet. Antigravity bestätigt
`gemini-4-hydrogen` und `high` beim Anlegen der Sitzung. Das Modell sieht das
gesamte Bildfeld in einer verkleinerten Ansicht, Überlagerungen und Details.
OpenCV misst am nativen Original und kann auf Modellanforderung ein Bildfenster
oder eine perspektivisch entzerrte Tafel erneut auswerten. Die geometrisch
geprüfte Kombination zweier Messungen ist ein zusätzlicher Kandidat.
Ergebnisdateien, Fortschritt und Wiederanlauf stehen in der
[Bedienanleitung](docs/three_camera_capture.md#automatic-gemini-marker-review).

**Unabhängige Erstprüfung** am echten Bedienersatz `set_144323_162753` mit
sechs Originalen. Bei beiden OAKs waren 17 Marker und 24 ChArUco-Ecken
bestätigt, mediane Abweichung zur unabhängigen Pixelmessung 0,22 bzw.
0,34 px. Nach echter Hydrogen-Nachprüfung der rechten Wrists hinten 17/24
und vorne 12/14 (Marker/Ecken). Links vorne 5/3. Links hinten am unteren
Bildrand 1/0, unabhängig war ein zweiter Marker lesbar. Rechts vorne
bestätigten Originalpixel alle zwölf behaltenen Marker. Die beiden rechten
Kameras führen die ursprünglichen Modellurteile neben der bestätigten
Revision. Die vier Ansichten mit mindestens zwölf brauchbaren Ecken können
zur Datensammlung beitragen. Es wurde keine Kalibrierung aktiviert.
[Erstprüfung und Pixelvergleiche](../../setup/calibration/charuco_gemini_review_20261123/ERSTPRUEFUNG.md)

## Stopp rechts hinten bei der Kamerapositionierung, 23.11.2026

Um 14:32:18 AWST forderte der unabhängige Watchdog einen nativen STOP für alle vier Arme an. Der Client für rechts vorne befand sich noch im Verbindungsaufbau. Rechts hinten ist für diesen Vorfall keine Geschwindigkeits- oder Abstandsauslösung protokolliert. Die Ursache der ausgebliebenen Supervisor-Rückmeldung ist offen. Bereits um 14:27:48 hatte der Supervisor rechts vorne wegen einer 257,803 s alten Hardwarebestätigung gestoppt. Der Watchdog forderte anschließend auch rechts hinten STOP an.

Beim früheren Programmstart um 14:07:18 ist eine tatsächliche Bewegung am rechten hinteren Handgelenk 3 belegt (0,261919 rad/s bei 0,1 rad/s Profilgrenze). Im späteren erfolgreichen Kameralauf bestanden die ROS-Verbindungen bereits vor Play. Rechts hinten erreichte das Ziel in 59,19 s bei einer gemessenen Spitze von 0,094257 rad/s. Während dieser Fahrt ist kein nativer STOP verzeichnet.

Lokal geprüft und korrigiert ist ein vermeidbarer Verwaltungsstopp bei unveränderter Meldung desselben Controller-Managers, teilweiser Verriegelung und frisch bestätigtem Stillstand der gesamten Zelle. Die drei Kontrollabfragen erhalten in diesem Fall 250 ms. Ein Offline-Nachlauf ergab null statt einer STOP-Anforderung. Auf dem N100 ist diese Änderung noch nicht installiert. [Zeitliche Zuordnung, Messberichte und Offline-Nachlauf](work/right-rear-kamera-stopp-20261123.md)

## Laufzeit der nativen Mehrkameraaufnahme, 23.11.2026

Auf Nutzerwunsch hält **UWA Camera Capture** während der Sechs-Kamera-Sitzung
alle sechs nativen Kameras offen. Vorschau und Einzelbild teilen die laufenden
Streams. Der Klick fordert sechs frische Frames parallel an. **FRAMES ACQUIRED**
gibt das mobile Board zum Umsetzen frei, **DONE** bestätigt die Archivierung
und Boardauswertung. **Release cameras** und das Schließen des Fensters geben
die Geräte frei und stellen die regulären Wrist-Visiondienste wieder her.
Der bestehende lesende Stillstandsnachweis nutzt die kontinuierliche
RTDE-Historie und protokolliert das Aufnahmefenster je Satz.

Echter Test der installierten GUI mit zwei aufeinanderfolgenden Klicks am
23.11. um 14:35 AWST. Klick bis zur Bestätigung des letzten Kamerabildes
**0,927 s** und **0,776 s**, Dauer des vollständigen Satzes laut Manifest
**5,24 s** und **5,13 s**. Beide Male sechs vollständig gespeicherte native
Bilder und bestätigter Stillstand. Alle vier Robotiq-Dienste nach dem
Schließen wiederhergestellt. Die Bildbestätigungen sind Hostmessungen mit
unabhängigen Kamerauhren. Zwei Durchläufe belegen keine garantierte Latenz.
[GUI-Messprotokoll](../../setup/calibration/six_camera_speed_20261123/gui-check/20261123_143454_4fd520e2/gui-check.json)

**Vergleich zum bisherigen Einzelbildpfad.** Dieser gibt beide OAK-Vorschauen frei, erfasst
die vier Wrists parallel und ruft danach OAK4 und USB-OAK nacheinander auf.
Die OAK4 wurde wegen früherer Startfehler bei gleichzeitigen nativen
Wrist-Aufträgen zurückgestellt. Jedes Kamerabild wird vor Abschluss seines
Auftrags gespeichert und auf das Board ausgewertet.

- Am 18.11. dauerten 14 erfolgreich gespeicherte Fünfersätze in
  `five_camera/` und `five_camera_pose/` zwischen 34,31 und 46,20 s
  (Median 36,08 s, je Manifest). In einem Satz entfielen 3,88 s auf den
  Vorlauf, 13,51 s auf die parallelen Wrists, 15,39 s auf die OAK4 und
  2,77 s auf den Abschluss. Die OAK4 belichtete darin 16,7 ms.
  [Fünfersatz mit Zeitstempeln](../../setup/calibration/oak_capture_proposal_20261118/five_camera_pose/20261118_140754_8caebf54/set_141026_915496/manifest.json)
- Beim separaten rechten vorderen Wrist-Test lagen 0,20 s zwischen erstem
  und letztem gespeicherten Bild der Dreierserie. Von 15,27 s am Host
  entfielen 9,36 s auf die Wiederherstellung von Visiondienst und Einstellungen.
  [Wrist-Messung](../../setup/calibration/wrist_speed_led_20261112/fast_led_comparison_2_right_front.json)
- USB-OAK am 23.11. im GUI-Einzeltest auf dem N100 14,03 s, davon 4,00 s
  zwischen erstem Anlaufbild und gewähltem Vollbild bei 30 ms Belichtung.
  Der anschließende Dateitransfer nach ROSmini und die Boardauswertung
  kommen hinzu. Diese Messung betrifft den früheren Einzelbildmodus.
  [USB-Aufnahmebericht](../../setup/calibration/mobile_volume_20261123/usb-gui-check-02/photo/native/metadata.json)

## Vier Handkameras erreicht, Sechskamera-GUI offen,23.11.2026,14:40AWST

- Nutzerauftrag vollständig ausgeführt: LF → LR → RF → RR nacheinander in
  die berechneten Beobachtungsposen gefahren; danach vorhandene Aufnahme-GUI
  um N100-USB-OAK erweitert und sichtbar geöffnet. Größter Gelenkzielfehler
  0,0001326rad, letzter GuardCLEAR/keine aktuellen Fehler. RF-Basis+51,9°
  erhält den vom Nutzer am19.11. entdrillten Umlauf.
- Explizite Nutzerfreigabe nach LF-Stopp bei0,108457rad/s: **nur diese vier
  Anfahrten mit0,09rad/s Sollgrenze**. Aktive nominelle Überwachung0,1rad/s,
  vorhandener Faktor1,05 und sonstige Limits unverändert. Erst nach dieser
  Zustimmung neu geprüft und gefahren. Die LF/LR-Befunde liegen in
  `execution-01/frozen-02/`, RF/RR in`persistent-05/`; zusammen alle vier
  Ziele anhand des letzten frischen Gesamtzustands bestätigt.
- Offline-Endentwurf auftitanpc im festen Profil
  `hardware_20261118_base_fixed_v1`: Kamera-XYZ jeweils(±0,95,±0,85,1,50)m,
  rund1,294m zur Arbeitsmitte. Geschätzter gemeinsamer Boardmitten-Quader
  50×50×25cm, worldX/Y±0,25/Z1,20–1,45m. Raster-/Optikentwurf für vier
  Handkameras, kein Erkennungs-/Präzisionsbeweis; LF-Optikanbindung nominal.
  Kompakte Ziele`config/view_designs/mobile_board_volume_20261123.yaml`
  bleiben eine Endstellungsreferenz, kein direkt ausführbarer Fahrplan.
- Vollständige Anfahrten ab realen eingeschalteten Gelenkständen aufROSmini
  geprüft; verifizierte N100-Geometrie, Meshes, Config und Planerquellen.
  Exakte SHA-gebundene Trajektorien ohne erneute komplette N100-Zeitplanung.
  Bestehende Start-, Quellenfrische-, Modell-, Korridor-, Vollzell- und
  Actionprüfungen erhalten. Endgültiger Dispatcher baut den gemeinsamen
  Client samt Actions/Lesern **vorPlay beiSTOPPED** auf und behält ihn über
  die seriellen Armwechsel. Keine Schutzdienst-/Grenzänderung dafür.
- Unterwegs belegte Betriebsprobleme: separater schon laufenderStart+ROS
  meldete LR−0,1953/RF+0,1584/RR+0,2619rad/s vor den Kamerafahrten.
  Dessen eindeutig identifizierter Prozess wurde unterbrochen und alle Holds
  bei nativSTOPPED an aktuelle Driver-/RTDE-Winkel gebunden. Später gespeicherte
  partielle Freigabe und beim Client-Neuaufbau erneut administrative STOPs/
  Watchdog-Verlust. Reguläre, tatsächlich angewendete Einzel-Resets und
  durchgängig aufgebaute Ausführungsschnittstellen ermöglichten den Abschluss.
  Details und offene Runtimebefunde nicht als behoben verschweigen:
  [Ablauf und Messwerte](work/mobile_board_observation_20261123.md).
- GUI: sechs aktive Livebilder am23.11.ab14:40:10AWST bestätigt,
  Dienst`uwa-camera-capture-six-20261123.service` aufROSmini. Sitzung
  `setup/calibration/six_camera_mobile/20261123_143953_b34a17a2/`.
  **CAPTURE ALL SIX**, bisDONE stillhalten; einseitiges Board zwischen
  Serien zu verschiedenen Blickpaaren drehen. Pair-Metadaten berücksichtigen
  dieselbe Board-ID.28 gezielte Kamerasoftwaretests/Paketbuild bestanden.
- Profil`config/digitization/six_camera_capture.yaml`: LF245/LR406/RF435/
  RR388, OAK4107, USB112. USB1280×960-Vorschau über eigene SSH-Sitzung,
  native4056×3040-Fotos über bestehenden Fotopfad, gemeinsame N100-Lease.
  USB-Anzeige180°, Detektion/Rohbilder ungedreht. Pause/Schließen gibt die
  eigenen Kameras frei. Startmenüeintrag auf sechs Kameras aktualisiert;
  drei/fünf Kameramodi bleiben verfügbar. Neue Intrinsics/Extrinsics und
  zwölfstündige Referenz wurden durch diesen Auftrag **nicht** aktiviert.
- Material unter`setup/calibration/mobile_volume_20261123/`, insbesondere
  `execution-01/final-verification.json`, `gui-live-status.json`,
  `six-camera-live.png`, `README.md`. SDK-Fotoprüfung USB: native4056×3040,
  Factoryhash unverändert, Kamera/Lease nach Test geschlossen. Die aktuelle
  GUI besitzt ihre Vorschau-Lease, solangeLive aktiv ist.

## N100-Treiber und Stoppverwaltung in Betrieb, 23.11.2026, 13:45 AWST

- Links vorne liefert wieder aktuelle RTDE-Daten. Der Nutzer bestätigte
  die Arme unbeladen und die Zelle frei. Vier Treiberdienste nacheinander
  bei aktivem Schutz gewechselt, jeden Hold erneut provisioniert und
  bestätigt. Der reguläre Stopppfad des Schutzdiensts bestätigte den Halt.
  Neue Guard-Invocation `7d44ce47a3374b6587dcdd0d284282c5`,
  unverändertes Kartonprofil und RR-Priorität 20. Alle vier Manager laden
  die geprüfte URCL-Bibliothek `6d862c646678…`. Der Greiferadapter liefert
  vier frische Registerbeobachtungen mit ursprünglichem Lesezeitpunkt.
  Rücksicherung `~/uwa-ur-runtime/review-candidates/vor-ur-driver-guard-20261123.nb5lzt61/`.
- Bei der Abschlussprüfung war der Modell-Publisher links hinten zunächst
  für den Guard unsichtbar. Nach erneutem Start des betroffenen Treiberdiensts
  entsprachen alle sechs veröffentlichten Gelenktransformationen exakt
  dem Zellmodell. In 20 s alle 884 empfangenen Supervisorzustände mit vier Holds
  und ruhenden Verwaltungsabfragen, alle 362 empfangenen Guardzustände mit
  vier mechanisch ruhenden Armen und nativ gestoppten Programmen.
  Keine aktuellen Guardfehler. Watchdog weiterhin verriegelt, kein Reset.
  Links vorne steht auf RUNNING/NORMAL, die drei anderen Arme auf POWER_OFF.
- Zwei 15-s-Messungen vor dem Wechsel und im Endstand ergaben 95,32 und
  66,12 % Hostlast, 164,34 und 100,56 % eines Kerns für den Schutzdienst,
  1.024 und 30 offene Deskriptoren pro Manager, 93 und 0 protokollierte
  native STOP-Anforderungen sowie 9.907 und 0 Treiberjournalzeilen.
  Der reguläre ROSmini-Offline-Compiler stimmt in allen 27 Prüferkomponenten
  mit dem N100 überein. Keine Fahrt oder Greiferbewegung ausgelöst.
  [Betriebsstand, Zeitfenster und Belege](work/n100-ueberwachung-20261123.md).

## Vorbereitung der N100-Treiber- und Stoppkorrektur, 23.11.2026

- N100-Ablage `~/uwa-ur-runtime/review-candidates/ur-driver-guard-20261123.71r24erk/`.
  Übertragene Dateien und operativer Ausgangsstand per SHA-256 geprüft.
  Die Kandidatenbibliothek schließt fehlgeschlagene TCP-Verbindungen und
  behandelt den RTDE-Wiederanlauf samt Meldungen. 24 vorhandene
  Loopback-Tests bestanden. Alle 97 vom echten N100-Hardwareplugin
  benötigten URCL-Symbole sind vorhanden, die Prüfung mit `ldd -r` direkt
  auf dem N100 ergab vollständige Auflösung auf den Kandidaten.
- Supervisor und unabhängiger Watchdog teilen die Stoppzuständigkeit.
  Weitere native STOPs entfallen bei frischem physischem Nachweis von
  Programmstopp und Armruhe. Ungeklärte Arme und Prozessausfälle behalten
  ihren Rückfall. Die drei Verwaltungsabfragen ruhen beim bestätigten,
  exklusiven stationären Hold und wachen bei Änderungen oder Freigabe auf.
  Der vorhandene Vierarm-Mock bestand alle 17 Prüfpunkte, auch die Übernahme
  eines laufenden Fake-Auftrags. Gesonderte Replays decken native Zustände,
  falsche und verspätete Rückmeldungen sowie die Rücklesefrist ab.
- Bei identischer Paarpose entfällt die neue Distanzrechnung. Bei geringen
  Änderungen genügt häufig die exakte Berechnung für 32 Kugelpaare.
  8.480 archivbasiert verglichene Paarbefunde stimmten feldweise überein.
  Die Ruheauswertung wird je Arm und Guard-Takt einmal erstellt. Die
  Greifer-Lesewiederholung und die Zwei-Sekunden-Frist bei der offenen
  Einfahrt sind im Kandidaten enthalten. Die Korrektur für einen verlorenen
  Vorschauexport gehört zur GUI auf ROSmini.
- Bei der Vorbereitung fehlten links vorne frische RTDE-Daten. Die spätere
  Übernahme und der Vorher-/Nachhervergleich stehen im vorstehenden
  Betriebsstand. [Softwareprüfung und Ausgangsmessung](work/n100-ueberwachung-20261123.md).

## Last der realen UR-Überwachung und der vier Treiber, 23.11.2026

- Lesende N100-Stichprobe um 11:50 AWST über 15,02 s im Fehlerzustand.
  Von vier logischen Kernen belegte der Wächterdienst 1,62, die vier
  Treiberdienste zusammen 1,71. Host-Auslastung 94,8 %. Das Journal enthielt
  79 native STOP-Anforderungen des ausgelösten Watchdogs für die vier Arme
  und 19 des Supervisors für links vorne wegen fehlender Stillstandsdaten.
  In denselben 15 s schrieben die vier Treiberdienste 8.390 Journalzeilen.
  Um 11:53 AWST hatten alle vier Manager wieder je 1.024/1.024 offene
  Dateideskriptoren am Softlimit, darunter 1.009 Sockets.
- Operative `hardware_ports.py` per Datei-SHA bestätigt (`35673c4ff3ed…`).
  Die bereitgelegte Variante (`c8f185fa0eea…`) verlängert Fristen bei
  gleicher Anfragerate. Vorschlag aus dem Audit: Verwaltungsabfragen an
  Ressourcenwechsel binden, doppelte Stoppaufträge zusammenführen und
  RTDE-/Socket-Fehler der Treiber gesondert beheben. Eine Übernahme auf
  Hardware oder Änderung von Schutzfrequenzen war nicht Teil des Audits.
  [Einzelprüfung, Messwerte und Belege](work/n100-ueberwachung-20261123.md).

## N100-Wächterwechsel wartet auf RTDE links vorne, 23.11.2026

- Nutzerbeobachtung vom 23.11.: Links vorne bootete mit abgezogenem externem
  Netzwerkkabel normal. Die anschließende lesende N100-Abfrage um 13:16:52 AWST
  erreichte den UR wieder (`RUNNING`, Safety `NORMAL`, `ros.urp STOPPED`).
  Der Wächter-Zustandsstrom lieferte anschließend zwei fortlaufende RTDE-
  Quellzeitstempel, jüngster Messwert rund 46 ms alt. Das bestätigt die
  Wiederherstellung nach dem Boot. Der Auslöser beim verbundenen Start ist offen.

- Pendant-Foto des Nutzers: PolyScope meldete `IncompatibleClassChangeError`
  im `ControllerConnectionThread` bei `RTDEClient.makeConnection`, mit
  `IOUtil.close` am Anfang des Stacktraces. Der Statusbericht wurde laut
  Pendant am 23.11. um 12:13:57,320 erzeugt (Pendant-Uhr). Der SSH-Dienst
  links vorne antwortet vom N100 aus. Nach ausdrücklicher Nutzerfreigabe
  wurde der vorhandene Bericht `recording20261123_12_13_57.zip` per SSH lesend
  abgerufen. ZIP-Prüfung und SHA-256-Abgleich bestanden. `summary.log`
  bestätigt den Stacktrace. Die genaue Fehlerursache ist offen.
  [Statusbericht](../../setup/logs/uwa-control/exports/left-front-20261123/recording20261123_12_13_57.zip)
- Offline-Auswertung des Statusberichts: `URControl.log.0` meldet am 23.11.
  um 12:12:48,404 laut Steuerbox-Uhr erstmals `urEthernetDriver: Lost eth package`,
  danach Timeouts. Der erste protokollierte RTDE-Client verbindet sich erst
  um 12:12:50,096. Ab 12:13:31 folgt ein weiterer URControl-Startabschnitt,
  in dem die Zustände `CONFIRM_SAFETY` und `DISCONNECTED` erscheinen. Die
  PolyScope-Ausnahme folgt um 12:13:57,307. `log_history.txt` enthält dieselbe
  Ausnahmeklasse bereits nach den Startsequenzen um 10:50 und 11:24. Kein
  konkreter Kommunikationsendpunkt lässt sich aus den Paketwarnungen zuordnen.
  Nächster Trennversuch nach Freigabe: kontrollierter Steuerbox-Start mit
  Antrieben aus und getrenntem externem Roboternetz, danach Logs vergleichen.

- Zum erneut beauftragten Wechsel stimmt die vorbereitete `hardware_ports.py`
  auf dem N100 weiterhin per SHA-256 mit der lokalen Datei überein. Dienst
  `uwa-hardware-motion.service` läuft weiter mit bisheriger Datei und PID 2254092.
- Dashboard meldete alle Programme `STOPPED`, drei Arme `POWER_OFF` und
  `left_front` `NO_CONTROLLER`. Der Wächter bestätigte Stillstand der drei
  anderen Arme. Links vorne war der letzte RTDE-Messwert rund 65 Stunden alt.
  Der Treiber meldete Wiederverbindungsversuche. Der Supervisor meldete vier
  Holds, jedoch fehlt der frische Stillstandsnachweis links vorne. Daher wurde
  der Dienstwechsel bei dieser Prüfung nicht eingeleitet.

## N100-Wächterwechsel vorbereitet, 20.11.2026, 18:03 AWST

- Der Nutzer beauftragte die Übernahme seiner Änderungen in `hardware_ports.py`
  und den Wächterneustart. Alle Arme waren laut Nutzer unbeladen, niemand war
  in der Zelle. Die Datei (SHA-256 beginnt mit `c8f185fa0eea`) und die bisherige
  Version liegen auf dem N100 unter `~/uwa-ur-runtime/review-candidates/hardware-ports.JexhTUgr/`.
  SHA-256 und Syntax bestätigt, zwölf bestehende isolierte Regressionen bestanden.
- Der Stop-Client bestätigte Stillstand und erhielt für alle Arme das native
  `Stopped`. Die Controllerlisten wurden im Stop-Client zu alt für den separaten
  Hold-Nachweis, auch mit aktivem Kartonprofil und passendem DDS-Transport.
  `profile-stop.json` und `matched-stop.json` im Kandidatenverzeichnis enthalten
  die Befunde. Die operative Datei und der aktive Dienst (PID 2254092) wurden
  nicht gewechselt. Passiver Abschlussstand: vier gemessene Stillstände und
  vier Holds am bestehenden Supervisor, Interlock bestätigt, Watchdog ausgelöst.

## Eigenes Kamerakalibrierprogramm in der Library,20.11.2026

- Nutzer beauftragt, den ChArUco-Suchdienst als eigenes Library-Programm
  aufzunehmen und die ermittelte Kamerapose zwölf Stunden für andere Programme
  gültig zu markieren. Der bestehende Karton-Zusatzknopf wurde zu einer
  eigenständigen Karte **OAK4 camera calibration** mit eigener Programm-ID
  `oak4-camera-calibration-v1`, Detailseite und **Start calibration** ergänzt.
- Der vorhandene Kamera-only-Ablauf bleibt: neue ChArUco-Aufnahme, rechte
  Boardpose mit passender Optik und eingefrorenen Basisbindungen prüfen,
  Ergebnisvorschau erzeugen und gemeinsame Sitzung atomar veröffentlichen.
  Keine N100-Vorprüfung/Play-/Arm-/Greiferbefehle aus dem Kameraprogramm.
  Veröffentlichung erst nach vollständiger Vorschau/Ergebnisablage.
- Sitzung weiterhin zentral `setup/skill_library/carton-camera-session.json`;
  bestehender Name für alle bisherigen Verbraucher erhalten. Kartonprogramm
  verwendet dieselbe12h-Referenz ohne erneute Boardprüfung im Kartonbild.
  API-Katalog nennt den Referenzstatus und Zeitraum, UI zeigt explizit
  REFERENCE VALID/CALIBRATION REQUIRED und AWST-Ablaufdatum. Nutzung verlängert
  die Frist nicht; bei Kamera-/Boardverstellung ausdrücklich neu kalibrieren.
- Softwareprüfung:6gezielte Offline-Tests für getrennten Katalogeintrag,
  ausschließlich Kalibriermodus, Startdispatch, exakte12h-Grenze und atomare
  Veröffentlichung inklusive Vorschaufehler. JavaScript-Syntax und native/
  ältere Katalogzuordnung im Node-VM geprüft. Bestehende lokale Änderungen
  zur N100-Threadbegrenzung in run_carton_program.py erhalten.
- Laufenden untätigen Webprozess auf8780 gezielt unter identischer Adresse/
  Konfiguration neu geladen, jetzt `uwa-program-library.service` mit
  `KillMode=process`. Power-GUI und ihr eigener Server wurden nicht beendet;
  neue Frontend-Dateien zeigen den Programmeintrag auch für deren ältere
  laufende Server über den bestehenden Kalibriermodus. Keine UR-Runtimeänderung.
- Browserzugriff über CUA war nicht verfügbar; API-/Programmprüfung läuft
  unabhängig davon. Nachweise `setup/tasks/camera_library_program_20261120/`.
- Abschließender realer API-Lauf `043a0df2880b41a69d08370275014118` mit der
  neuen Programm-ID erfolgreich:17rechte Marker/1,53px Prüf-RMS. Aufnahme-
  referenz20.11.17:50:42,834520 bis21.11.05:50:42,834520 AWST, exakt43200s.
  Beide Katalogprogramme und die gemeinsame Sitzung melden denselben Zeitraum.
  Gemeinsame Datei und Laufkopie sind SHA256-identisch, Vorschau-Endpunkt
  liefert JPEG, Kamerasperre nach Abschluss unabhängig frei geprüft.
  Laufphasen ausschließlich setup/oak_calibration/camera_reference/
  camera_publish/done. Keine Roboter gestartet oder bewegt. Bedienung
  [camera_library_program.md](docs/camera_library_program.md).

## Laufende UR-Wächter auf dem N100, 20.11.2026, 17:45 AWST

- Lesende SSH-Inventur bestätigte einen aktiven systemd-Benutzerdienst
  `uwa-hardware-motion.service` mit drei Schutzprozessen im Hardwaremodus
  (`--armed`): `hardware_guard`, `hardware_supervisor`, `hardware_watchdog`.
- Alle drei verwenden relativ zu `~/uwa-ur-runtime/src/multi_arm_manipulation_UWA/`
  das Profil `uwa_cell_motion/config/hardware_carton_supported_trend.yaml` und
  `config/hardware_inventory.yaml`. Die transiente Unit liegt unter
  `/run/user/1000/systemd/transient/uwa-hardware-motion.service` und hatte
  keine Drop-ins. Die Inventur belegt den Prozessstand.
- `hardware_supervisor` überwacht je Arm `list_controllers` über
  [`StopPort.tick()`](uwa_cell_motion/uwa_cell_motion/hardware_ports.py#L113).
  Auf dem N100 im installierten Quellpfad lesend bestätigt: Eine bestätigte
  Liste gilt unter 250 ms als frisch, eine noch offene Anfrage wird nach
  über 300 ms verworfen, der Mindestabstand zwischen Anfragen ist 50 ms.
  Diese Werte stehen im Code. `heartbeat_timeout_s: 0.25` und
  `hold_config_max_age_s: 1.0` im aktiven YAML betreffen separate Prüfungen.

## Native STOP bei verspäteter Controllerliste, 20.11.2026, 17:36 AWST

- Weblauf `b10edbd8a8764868b1be6d9018eef802`: beide Kartonarme spielten
  beim Eingang der Motion review. Während der Einrichtung der genehmigten
  Hochanfahrt veranlasste der N100-Supervisor um 17:36:17,316 für
  `right_front` einen STOP. Die letzte Controllerliste war 261,721 ms alt
  bei einer Grenze von 250 ms. Die Hold-Konfiguration war 21,934 ms alt
  und gültig. Um 17:36:17,347 fiel die ROS-Reverse-Verbindung ab. Beide
  rechten Arme hatten 0 s Bewegung über 0,003 rad/s. Im Ergebnis stehen
  keine Arm- oder Fingerbefehle. Der spätere Status meldete `right_front`
  STOPPED und `right_rear` weiterhin PLAYING.
- Armweiser Archivabgleich am 23.11.: Der Safety-Report enthält für beide
  rechten Arme veraltete Controllerlisten vor Play. Um 17:27:41 meldete
  `right_rear` 520,762 ms bei 250 ms Grenze. Beim früheren manuellen
  Start um 17:20:12 folgte auf die Reverse-Verbindung von `right_rear`
  ein Watchdog-STOP und der Verbindungsabbruch. Der konkrete Programmabbruch
  um 17:36:17 betraf `right_front`.
  [Safety-Report](../../setup/tasks/uwa_program_library/b10edbd8a8764868b1be6d9018eef802/n100-safety-report.json)
- Der Browser startet N100-Ausführungsprozesse für Fahrt- und Kontaktreview
  jetzt mit je einem OpenBLAS-/OpenMP-Thread. Ein kleiner Vergleich auf
  dem N100 bestätigte für NumPy/SciPy vier Threads ohne und einen mit
  Begrenzung. Die Browser-Übergabe wurde offline geprüft. Konkurrenz um
  CPU-Zeit ist plausibel, die Ursache der verspäteten Controllerliste
  ist offen und die Wirkung auf einen neuen Live-Lauf steht aus.
- Regulärer Dashboard-STOP läuft weiter über die explizite Bedienaktion
  **Standby**. Der protokollierte STOP stammt aus der Schutzfunktion.
  Die Schutzkette wurde bei dieser Diagnose nicht geändert.
  [N100-Journal](../../setup/tasks/uwa_program_library/b10edbd8a8764868b1be6d9018eef802/n100-high-guard-exact.log) ·
  [Ausführungsbeleg](../../setup/tasks/uwa_program_library/b10edbd8a8764868b1be6d9018eef802/n100-high-result.json)

## Browser-Play für beide Kartonarme bestätigt, 20.11.2026, 17:28 AWST

- Bedienperson startete den Weblauf `b10edbd8a8764868b1be6d9018eef802`
  um 17:27:30. Vier offene Greifer und vier Holds bestätigt. Nach
  erfolgreichem Software-Watchdog-Reset meldeten die Treiber die
  Reverse-Verbindung für `right_front` um 17:28:07,477 und für
  `right_rear` um 17:28:08,618. Beide standen im anschließenden
  Dashboard-Readback auf `RUNNING/NORMAL/PLAYING`, Reverse verbunden.
  Die beiden linken Programme bleiben beim Karton-Weblauf selektiv auf
  STOPPED.
- Das bestätigt den Browserstart einschließlich realem Play nach der
  Wiederherstellung des Greiferadapters. Bei Eingang der Bewegungsfreigabe
  in UWA Robot Power meldeten beide rechten URs erneut PLAYING und ready.
  [Startbeleg](../../setup/tasks/uwa_program_library/b10edbd8a8764868b1be6d9018eef802/n100-browser-play-result.json) ·
  [Dashboard-Readback](../../setup/tasks/uwa_program_library/b10edbd8a8764868b1be6d9018eef802/n100-dashboard-after-browser-play.json)

## UWA Robot Power meldet NOT READY, 20.11.2026, 17:26 AWST

- Der manuelle **Start + ROS** ab 17:18:39 AWST erhielt für alle vier
  Arme die Dashboard-Antwort `Starting program`. Alle vier waren
  bei der nachfolgenden Bestätigung wieder `STOPPED`. Der nach dem
  Guard-Neustart ausgelöste N100-Watchdog sendete in diesem Zeitraum
  native STOPs. Beispielsweise bei `right_rear` am 17:20:12 AWST:
  Reverse-Verbindung um .642, Watchdog-STOP um .693 und Verbindungsabbruch
  um .722. Die lesende Statusabfrage um 17:26 zeigte weiterhin alle
  `RUNNING/NORMAL/STOPPED`, Reverse getrennt. Bei dieser Diagnose keine
  Sollwerte oder Bedienbefehle gesendet.
- Der manuelle Desktop-Pfad sendet Play ohne den unter bestätigten Holds
  ausgeführten Watchdog-Startschritt des Karton-Webpfads. Der zweite
  Browser-Versuch von 17:21 endete ebenfalls in der Greiferabfrage und
  lag vor der Wiederherstellung des Greiferdienstes um 17:24. Die lesende
  Vorprüfung des korrigierten Webpfades bestand anschließend bis vor
  dem Watchdog-Aufruf.
  [N100-Journal](../../setup/tasks/uwa_program_library/79a52f8964b043e3b0198bf8a528656f/n100-manual-start-journal.log) ·
  [Status](../../setup/tasks/uwa_program_library/79a52f8964b043e3b0198bf8a528656f/n100-power-status.json)

## ROS-Lesedienst des rechten vorderen Greifers, 20.11.2026, 17:17 AWST

- Der Browserlauf `79a52f8964b043e3b0198bf8a528656f` brach vor Play
  und OAK-Aufnahme in der Greiferabfrage ab. Beide rechten Arme meldeten
  `RUNNING/NORMAL/STOPPED` und hatten einen erreichbaren Script-Listener.
  Ein frischer ROS-Client sah alle vier Greiferdienste im ROS-Graphen,
  konnte aber innerhalb von 15 s ausschließlich
  `/uwa_hardware/right_front/gripper/read` nicht verbinden. Ein separater
  Client empfing vom selben Adapter weder Statusmeldungen noch Antworten.
  Der Adapterprozess lebte mit 26 Dateideskriptoren. Der native
  Robotiq-GET für diesen Greifer war erreichbar.
- N100 meldete Stillstand und vier Holds, die vier nativen Greifer-GETs
  meldeten inaktive offene Greifer. Nur `uwa-grippers.service` wurde um
  17:24:04 AWST neu gestartet. Die korrigierte Browserprüfung meldete
  vier erfolgreiche Greiferabfragen in 1,15 s, darunter 52 ms für
  `right_front`. Die Ursache der verlorenen ROS-Verbindung ist offen.
- Der Browser erstellt jetzt die vier Leseclients gemeinsam und nennt
  den konkreten Dienst bei fehlender Discovery. Eine zweite lesende
  Vorprüfung bestätigte vier offene Greifer, frische Guard-Pakete,
  vier Holds und die Erreichbarkeit des Watchdog-Diensts. Der lesende
  Versionsvergleich bestand. Bei dieser Diagnose wurden weder Play
  noch Greiferbefehle gesendet. 33 bestehende Offline-Tests bestanden.
  [ROS-Discovery](../../setup/tasks/uwa_program_library/79a52f8964b043e3b0198bf8a528656f/n100-gripper-discovery.log) ·
  [Wiederherstellung](../../setup/tasks/uwa_program_library/79a52f8964b043e3b0198bf8a528656f/n100-gripper-recovery.log)

## Browser-Play und Hold-Konfigurationsalter, 20.11.2026

- Nutzer beauftragte 1.000 ms für die Bestätigung der Hold-Konfiguration
  und Play bei Bedarf über **Start program**. `hold_config_max_age_s: 1.0`
  gilt für das aktive N100-Kartonprofil. RPC-Fristen, Nachweise von
  Controllerliste und realer Hardware sowie native Zustands- und
  Heartbeat-Frische behalten ihre jeweiligen Grenzen.
- Der Webrunner fragt die beiden rechten Arme vor Foto und Planung ab.
  Für vorbereitete, gestoppte Programme sendet der N100 unter den
  vorhandenen unbeladenen Haltebedingungen ausschließlich Play. Er prüft
  vor dem Befehl erneut die Arbeitsbereichssitzung und offene Freigaben.
  Sind beide Programme bereits verbunden, bleibt es beim lesenden Check.
  Die Fahr- und Kontaktfreigaben laufen wie bisher über UWA Robot Power.
- Erster Guard-Wechsel um 17:13:02 AWST zurückgerollt. Die beiden
  rechten Controller bestätigten ihre Zustände innerhalb des ersten
  18-s-Prüffensters noch nicht. Zweiter Wechsel um 17:14:42 AWST mit
  längerem Prüfzeitfenster bestätigt. Vier Arme stationär und auf STOPPED,
  vier Holds und Interlock bestätigt. Der Watchdog war nach dem Neustart
  ausgelöst. Keine Bewegung und kein Live-Play während der Umstellung.
- 57 bestehende Offline-Tests bestanden. Gezielte Offline-Prüfung für
  Altersgrenze, Armwahl und Play-only. Der lesende Live-Versionsvergleich
  von ROSmini und N100 bestand. Erster tatsächlicher Play-Befehl über den
  Browser steht aus.
  [Aktivierungsbeleg](../../setup/tasks/carton_browser_play_20261120/n100-activation-retry.log) ·
  [Bedienung](docs/carton_motion_review.md)

## Kartonstart bei gestopptem ROS-Programm, 20.11.2026, 17:03 AWST

- Der Startsnapshot um 17:00 meldete alle vier Arme mit
  `robot_mode=7` (Antriebe eingeschaltet), `safety_mode=1` (NORMAL) und
  `runtime_state=1` (`ros.urp` STOPPED). Bildfit und Offline-Planung
  bestanden, weil der Planungssnapshot gültige Gelenkpositionen auch bei
  STOPPED zulässt. Die Hochanfahrt braucht `runtime_state=2` (PLAYING).
  `right_front` war der erste abgewiesene Fahrarm. Beide rechten Arme
  zeigten 0 s Bewegung über der Messschwelle von 0,003 rad/s. Der
  Ausführungsbericht enthält keine Arm- oder Fingerbefehle.
- Der letzte belegte PLAYING-Zustand für `right_front` und `right_rear`
  ist im Snapshot von 15:56. Die beiden N100-Treiber protokollierten
  um 15:58:51 den Verlust ihrer Reverse-Verbindungen, zeitgleich mit
  dem protokollierten Schutz-STOP des Supervisors für `right_front`.
  In den geprüften Treiber- und GUI-Logs ist danach bis zum Fehlerlauf
  kein erneuter erfolgreicher Play belegt. Der Safety-Log zeigt um
  17:03 den Workflowfehler ohne neuen Supervisor-STOP. Der bestätigte
  Guard ist seit 19.11. 17:14:28 AWST aktiv (PID 505211).
- Der lesende N100-Dashboardstatus danach bestätigte an allen vier Armen
  `ros.urp` geladen und STOPPED, Treiber-Listener erreichbar und Reverse
  getrennt. Keine Betriebsbefehle bei dieser Diagnose.
  [Ablaufbeleg](../../setup/tasks/uwa_program_library/6d35f87793fd47dcb1d7380f6367e044/n100-motion-workflow.json) ·
  [Treiberjournal](../../setup/tasks/uwa_program_library/6d35f87793fd47dcb1d7380f6367e044/n100-driver-state.log)

## Hydrogen Low als Karton-Bildreserve, 20.11.2026

- Nutzerentscheidung: den getesteten Gemini 4 Hydrogen Low als Reserve
  übernehmen und Vorbereitung zwischen Läufen wiederverwenden. Aktiv auf
  ROSmini über `setup/skill_library/carton-hydrogen.enabled`.
- Der lokale Ablauf verwendet die feste Markdown-Bildanweisung, den auf
  1.120 px verkleinerten Tischbildausschnitt und ein validiertes
  Bildrechteck-JSON. Hydrogen wird nach Ablehnung des Standard-Bildfits
  aufgerufen. Haben Fenster bereits zu einem gültigen Fit geführt, probiert
  ROSmini sie bei ähnlicher aktueller Aufnahme mit derselben ChArUco-Sitzung
  zuerst. Die Pose entsteht jedes Mal aus den nativen Pixeln der aktuellen
  Aufnahme mit dem bestehenden Auflage- und Mehrhypothesenfit.
- Archiv-Replay des 16:05-Fehlerfotos: 34,74 s für die gesamte Bildphase
  mit Standardablehnung und Hydrogen, davon 2,36 s ACP-Start und 7,21 s
  Modellanfrage. Wiederverwendung auf der separaten 15:56-Aufnahme und
  erneut auf dem 16:05-Foto dauerte 10,63 bzw. 11,00 s. Beide Fits gültig
  ohne Modellanfrage. Die weiter links stehende Archivlage und eine
  andere Kamera-Sitzungskennung verwarfen den Cache.
- Mit der neu berechneten Pose und dem archivierten N100-Snapshot bestanden
  der Offline-Bahnplan und die lokale Erstellung der N100-Übergabedateien.
  Die Prüfung endete vor dem Upload und vor einer realen Bewegung.
  [Messwerte](../../setup/tasks/carton_hydrogen_fallback_20261120/measurements.json) ·
  [Bedienung](docs/carton_motion_review.md#hydrogen-low-als-reserve-für-den-bildfit)

## Antigravity als Bildlokalisierung im Kartonversuch, 20.11.2026

- Nutzerauftrag: zuerst schnelles verfügbares Bildmodell bei niedrigster
  Reasoning-Stufe, Vergleich von Antwortzeit und nutzbarem Ergebnis. Kleine
  Markdown-Anweisung und 0–1000-JSON-Boxen für ganzen Karton und bedruckte
  Front. Eingaben drei gespeicherte Kartonbilder und ein kartonfreier
  Ausschnitt. ACP übermittelte Bild und Prompt ohne Werkzeugaufrufe.
  [Prompt](docs/agent_trials/PROMPT_CARTON_VISION.md)
- Die Modellboxen zentrierten die vorhandenen 2.600/2.550 px breiten
  Suchfenster. Der gleiche Bild-, Tischauflage- und Mehrhypothesenfit rechnete
  die Pose. Der damalige Weblauf verwendete ausschließlich den SIFT-Pfad
  mit erweitertem festem Detailfenster. Dies war ein Archivversuch.
- Feste Fenster lieferten aus drei positiven Bildern eine gültige Pose.
  Gemini 3.8 Flash Low beantwortete alle vier Bildfälle korrekt, Median
  4,43 s bis Antwort, 0,980 Median-IoU zur Bildannotation, zwei gültige
  Posen. Flash Medium lieferte zwei korrekte Antworten in 8,37 und 21,78 s,
  zweimal fiel die Anfrage ins 32-s-Zeitlimit. Eine gültige Pose.
  Gemini 4 Hydrogen Low beantwortete vier von vier, Median 5,89 s,
  IoU 0,990 und drei gültige Posen. Anfragezeit erfasst ACP und Netzwerk,
  separater lokaler Fit im Bericht. JSON erschien teils in einem Markdown-
  Codeblock, den der Benchmark strikt entpackt und danach validiert.
- Das Fehlerfoto um 16:05 bestand drei getrennte Hydrogen-Low-Anfragen
  mit jeweils anschließendem Fit. Modellursprung maximal 3,20 mm und
  0,75° auseinander. Einer der bestandenen Fits lag nur 0,00095 px unter
  der bisherigen Grenze. Der LLM-Vorschlag ist ein Kandidat für die
  Ausschnittwahl, metrische Genauigkeit und Live-Stabilität sind offen.
  [Vergleich](../../setup/tasks/carton_antigravity_20261120/comparison.json) ·
  [Weiter links stehender Karton](../../setup/tasks/carton_antigravity_20261120/hydrogen-low/low-C-overlay.jpg)

## Kantengeometrie, FoundationPose und Bildmerkmale am Karton, 20.11.2026

- Nutzerauftrag: Kartonpose direkt aus den Kanten schätzen, FoundationPose
  mit automatischer Startmaske testen und SIFT gegenüber ORB einordnen.
- Offline auf ROSmini: vier Archivbilder, STL-Randprofile plus sichtbare
  untere Frontkante, kalibrierte Tischauflage, x/y/Drehung aus einem gemeinsamen
  Suchbereich, keine Texturpose als Startwert. Bei den drei praktisch gleichen
  Aufnahmen driftete der reine Kantenfit in einer Aufnahme auf eine innere
  Naht, größte Mittelpunktstreuung 33,10 mm. Vier automatisch detektierte
  gelbe Randlaschen lieferten einen zusätzlichen Silhouettenhinweis. Damit
  1,236 mm Mittelpunktstreuung und 0,624° Drehstreuung, ohne Nachweis der
  absoluten Genauigkeit. Abstand zur Texturpose um 15:56 blieb 13,21 mm
  am Modellursprung. Auch die versetzte Archivlage vom Vortag wurde gefunden.
- FoundationPose auf titanpc mit den acht gespeicherten 640×480-RGB-D-Paaren
  vom auf der Seite stehenden Karton. Tisch-Ebene aus Tiefe, gelber Aufdruck
  als Startregion, daraus zusammenhängende RGB-Silhouette per GrabCut. Maske
  automatisch und ohne Szenenpose erzeugt. IoU 0,781 zur Handmaske, beide
  Poseläufe unterscheiden sich im ersten Frame um 0,441 mm und 0,134°,
  acht gültige Frames im automatischen Lauf. Vergleich auf identischen Daten,
  keine absolute Genauigkeit oder roboterseitige Greifqualifikation.
- SIFT/ORB auf den Bildern 15:49, 15:56 und 16:05 mit derselben Poseprüfung
  und denselben ROI. ORB verwendet neu erzeugte Binärreferenzen, Hamming und
  denselben 0,73-Verhältnistest wie SIFT. Beide akzeptierten zwei Bilder.
  SIFT hatte drei, drei und einen gültigen Auflagefit, ORB zwei, zwei und
  keinen. Laufzeiten SIFT 5,46–10,56 s, ORB 1,99–2,61 s. Ergebnis gilt für
  diesen kleinen Vergleich und die benutzte Konfiguration.
  [Messbericht](../../setup/tasks/carton_perception_comparison_20261120/comparison-summary.json) ·
  [Kantenvergleich](../../setup/tasks/carton_perception_comparison_20261120/kantenvergleich-1605.jpg) ·
  [FoundationPose-Projektion](../../setup/tasks/carton_perception_comparison_20261120/foundationpose-auto-result/overlay_000.png)

## OAK4-Wiederholaufnahme bei gleicher Kartonlage, 20.11.2026

- Nutzer meldet unveränderten Karton und unveränderte Kamera. Vergleich der
  akzeptierten Aufnahme 15:56 und der abgelehnten Aufnahme 16:05 bestätigt
  eine Verschiebung der Bildmerkmale deutlich unter einem nativen Pixel.
  In beiden Aufnahmen liegt die bedruckte Front im korrigierten Ausschnitt.
  Fokus 107, Belichtungszeit 25 ms und Kamerareferenz identisch. Gemeldete
  ISO-Werte 265 bzw. 290. ISO allein ist als Ursache unbewiesen.
- Die Rohbilder lieferten drei bzw. einen gültigen Auflagefit. Reproduzierter
  Übersichtsfit für dieselbe Kartonfläche: 50 bzw. 65 Textur-Inlier, bei
  Tischauflage 5,773 bzw. 7,556 px RMS (Grenze 6,5 px). Der Detailfit mit
  1.200 px und Streckung 1,5 stieg von 7,825 auf 10,231 px bei 8,5 px Grenze.
  Der Detailfit mit Streckung 1,6 blieb gültig (8,107 und 8,090 px). Damit
  war der Karton im Bild auffindbar und dem Ablauf fehlte ein zweiter
  belastbarer, zur Tischauflage passender Fit.
- Der Bildvergleich nutzt die echten Punktzuordnungen und zeigt ausgewählte
  Reprojektionsfehler sechsfach vergrößert. Beide Ursprungsberichte wurden
  aus den unveränderten Eingaben exakt wiederholt. Im Wiederholungsnachweis
  wurden Bildarchiv und bestehende Erkennung verwendet.
  [Bildmessung](../../setup/tasks/carton_oak_repeat_20261120.nmF6Bhre/frame-comparison.json) ·
  [Fehlgeschlagener Bericht](../../setup/tasks/uwa_program_library/59fe6864007d413c905c3131f39c1cca/registration/registration.json)

## Nativer STOP vor der Hochanfahrt, 20.11.2026, 15:58 AWST

- Nutzerentscheidung: `ros.urp` im regulären Betrieb nur durch den Nutzer
  oder auf ausdrückliche Aufforderung beenden. Bestehende Schutzstopps
  bleiben die gesonderte Schutzfunktion. In beiden AGENTS-Dateien dokumentiert.
- Karton-Weblauf `e7b50828b789419ba029347a3aeb8893` bereitete Bildpose und
  beide parallelen Bahnphasen erfolgreich vor. Der native Snapshot um 15:56
  zeigte `ros.urp` bei beiden rechten Armen und `left_rear` als `PLAYING`.
  `left_front` war bereits `STOPPED`. Die Bedienperson gab die Bahn um 15:58
  frei. Die GUI-Sitzung protokollierte keinen regulären Stop/Standby zu diesem
  Zeitpunkt. Die Hochanfahrt brach vor Haltereset und Zielversand ab, mit
  `arm_commands=[]` und `finger_commands=[]`. Native Bewegungsmessung für
  beide rechte Arme jeweils 0 s über 0,003 rad/s.
- Der aktive N100-Supervisor (PID 505211) protokollierte um 15:58:51,369
  einen nativen STOP für `right_front`, weil die letzte Bestätigung der
  Haltekonfiguration 300,212 ms alt war (Grenze 300 ms, Controllerliste
  199,748 ms und frisch). Beim Folge-STOP um 15:58:51,627 war der Nachweis
  der realen Hardware 540,081 ms alt (Grenze 300 ms). Die GUI meldete
  darauf `ros.urp` `STOPPED`, während Antrieb und Safety `RUNNING/NORMAL`
  blieben. Für weitere gleichzeitig als gestoppt gemeldete Arme enthält das
  enge Journalfenster keinen eigenen Auslöser. Warum die Statusantworten
  verspätet eintrafen, ist offen. Der Runner war währenddessen in der
  Initialisierung des Ausführungskontexts. Freigabe-/Schutzlogik unverändert.
  Lesender Status um 16:02 zeigte alle vier Antriebe `RUNNING/NORMAL`, alle
  Programme `STOPPED` und alle vier Treiber bei je 30 Dateideskriptoren.
  [N100-Schutzjournal](../../setup/tasks/uwa_program_library/e7b50828b789419ba029347a3aeb8893/n100-high-guard-exact.log) ·
  [Ergebnis Hochanfahrt](../../setup/tasks/uwa_program_library/e7b50828b789419ba029347a3aeb8893/n100-high-result.json)

## Detailausschnitt für die OAK4-Kartonpose, 20.11.2026

- Der Lauf um 15:49 AWST endete bei der Bildregistrierung. Das aktuelle
  Foto enthielt die bedruckte Vorderseite etwa bei y=3250–3900 im 8K-Bild.
  Der bisherige Detailausschnitt begann mit y=3980 darunter und enthielt
  das ChArUco-Board. In der Übersicht bestand ein Auflagefit mit 53 Inliern
  und 6,212 px RMS bei 6,5 px Grenze. Zwei weitere Fits derselben Fläche
  lagen bei 7,869 und 9,383 px. Für die Registrierung sind zwei gültige,
  übereinstimmende Fits erforderlich.
- Die lokale Optikdatei erweitert den Detailausschnitt nach oben auf
  `[2450,3200,5000,5000]`. Derselbe Bildsatz um 15:49 liefert drei gültige
  Fits mit maximal 1,792 mm und 0,524° Abweichung. Das Fehlerfoto um 12:47
  liefert zwei, der am 19.11. um 13:24 bereits akzeptierte Bildsatz fünf.
  Suchbreiten, Kalibrierung und bestehende Fit-Grenzen sind identisch.
  [Bildvergleich](../../setup/tasks/carton_web_roi_20261120/latest-roi-overview.jpg) ·
  [Registrierung 15:49](../../setup/tasks/carton_web_roi_20261120/upward/registration.json) ·
  [Registrierung 12:47](../../setup/tasks/carton_oa4_crops_20261120.l1cMEo9Z/12-47-face-y3200/registration.json)

## Start + ROS am Dateideskriptorlimit der N100-Treiber, 20.11.2026

- Nach Meldung des Nutzers, dass die Zelle frei und unbeladen ist, bestätigte
  ein frischer RTDE-Snapshot alle vier Arme stationär. Die vier betroffenen
  N100-UR-Treiberdienste wurden gezielt neu gestartet. Um 13:59:57 waren
  alle vier neuen Controllerprozesse auf ihren vorgesehenen Ports erreichbar
  und belegten je 30 statt 1.024 Deskriptoren. Live-Schutz und Greiferdienst
  liefen mit denselben Dienstidentitäten weiter. Die anschließenden
  Dashboard-/RTDE-Readbacks zeigten `RUNNING/NORMAL/STOPPED` und Stillstand.
  Die vorhandenen Sechs-Gelenk-Haltecontroller wurden auf den vier neuen
  Managern mit dem bestehenden `provision`-Befehl inaktiv bereitgestellt.
  Die Bedienperson startet anschließend `ros.urp` über **Start + ROS**.
  [Neustartnachweis](../../setup/tasks/ur-driver-restart-20261120/restart-verified.log) ·
  [Haltecontroller](../../setup/tasks/ur-driver-restart-20261120/holds-verified.log)
- Der auf ROSmini und N100 identische URCL-Quellstand in `tcp_socket.cpp`
  überschreibt beim erneuten `socket()`-Aufruf unter bestimmten Fehlerpfaden
  den alten Deskriptor, ohne ihn freizugeben. Das erklärt einen plausiblen
  Mechanismus für die Ansammlung. Die Zuordnung aller historischen Sockets zu
  diesem Pfad ist offen. Der TCP-Server verwendet `select()` und verwirft
  Deskriptoren ab `FD_SETSIZE`. Ein höheres Prozesslimit ersetzt die Korrektur
  der Socket-Verwaltung daher nicht.

- Der Karton-Weblauf um 13:23:35 AWST endete um 13:23:47 bei der lesenden
  RTDE-Zustandsprüfung. `left_rear`, `right_front` und `right_rear` meldeten
  `POWER_OFF` (3), Safety `NORMAL` (1), Runtime `STOPPED` (1). Der Weblauf
  erreichte weder Aufnahme noch Bewegungsanforderung.
- Im N100-GUI-Protokoll forderte der Nutzer um 13:46:21 **Start + ROS** an.
  Der Start endete um 13:48:16 als unvollständig. Dashboard-Readback um
  13:48:19: vier Antriebe `RUNNING/NORMAL`. Beide vorderen Arme
  `ros.urp` `STOPPED` nach Play-Timeout. Beide hinteren Arme `PLAYING`,
  aber ohne bestätigte ROS-Reverse-Verbindung. Die vorherigen `CONFIRM_SAFETY`-
  Meldungen beim Laden um 11:43 beschreiben einen früheren Startversuch.
- Alle vier N100-Controllerprozesse belegten um 13:48:52 exakt je 1.024
  Dateideskriptoren am Softlimit 1.024, darunter je 1.009 Sockets. An den
  Ports 51002, 52002, 53002 und 54002 scheiterte `accept` mit `Too many open
  files`. TCP-Verbindungen der Roboter erreichten die vorgesehenen Ports.
  Je 997 Sockets waren in den abgefragten `/proc/net`-Tabellen keinem
  Endpunkt zugeordnet. Ein ähnlicher Fehler wurde historisch auf ROSmini
  gemessen. Der Mechanismus des Zuwachses ist offen. Ein gezielter Neustart
  der vier Treiber ist der bisher erprobte Weg zur Betriebsbereitschaft
  und bedarf einer Freigabe für den aktuellen physischen Zustand.
- Safety Log während des Startens, 13:47:20: native STOP-Anforderung für
  `right_front` wegen verweigertem Stillstandsnachweis. Gelenk 6 zeigte
  0,00250 rad/s Positionstrend bei 0,001 rad/s Limit und 0,00153 rad Spanne
  bei 0,0005 rad Limit im 0,49994-s-Fenster. Das zeigt eine gemessene
  Positionsänderung beim Hochfahren. Ein Zusammenhang mit dem Play-Timeout
  ist unbelegt. [N100-Status und Treiberlog](../../setup/tasks/uwa_program_library/00d1bc2458704638a95927b1a3f7100e/n100-start-current.log) · [FD-Messung](../../setup/tasks/uwa_program_library/00d1bc2458704638a95927b1a3f7100e/driver-fd-current.txt) · [Safety Log](../../setup/tasks/uwa_program_library/00d1bc2458704638a95927b1a3f7100e/safety-report-current.json)
- Eine weitere rein lesende RTDE-Messung nach dem Start bestätigt für alle
  vier Arme `RUNNING/NORMAL` und Stillstand in Fenstern von 0,528–0,550 s.
  Programmzustände blieben vorne `STOPPED` und hinten `PLAYING`.
  [RTDE-Nachweis](../../setup/tasks/uwa_program_library/00d1bc2458704638a95927b1a3f7100e/observations-after-start.json)

## Rechneraufteilung für den Kartonpilot, 20.11.2026

- Nutzerentscheidung: ROSmini übernimmt Bildauswertung, Bahnplanung und
  Offline-Prüfung. Größere Rechenaufträge bei Bedarf auf titanpc. Der N100
  liefert den gemessenen Startzustand und betreibt Regelung, Ausführung und
  Live-Schutz. Das versionsgebundene statische Modell darf wiederverwendet
  werden. Die Rechneraufteilung ersetzt die frühere Zuordnung der Planung
  zum N100.
- Der bisherige Snapshot ist eine native RTDE-Messreihe. Vier parallele
  Leser holen je 20 Samples, während zwei weitere Abfragen die Greifer lesen.
  Der Messabschnitt je Arm dauerte 0,912–0,950 s, der Aufruf auf dem N100
  insgesamt 3,05 s. Das bestehende Ruhefenster beträgt 0,5 s.
- ROSmini wiederholte die Bildauswertung des unveränderten Fehlerfotos um
  12:47 AWST in 6,738 s. Auf dem N100 waren es 44,804 s. Alle 19
  Hypothesenprotokolle stimmten überein. Die erweiterte Diagnose mit größerem
  Ausschnitt bleibt ein eigenes Ergebnis. Cache-Messung auf ROSmini:
  2,124 s für den Erstaufbau des statischen Rezepts und 0,465 s beim
  Wiederaufruf. [Messnachweis](../../setup/tasks/carton_web_timing_20261120/rosmini-feature-replay/summary.json)
- Die Webbibliothek meldet Zustand, Aufnahme, Kartonregistrierung und
  Bahnplanung einzeln. Ein ungeeigneter Zustand beendet den Vorlauf vor
  Fotoaufnahme und Modellrechnung. Ein neuer lesender Web-Snapshot meldete
  `POWER_OFF` bei `left_rear`, `right_front` und `right_rear`. Messung und
  Auswertung dieses Aufrufs dauerten 6,55 s einschließlich SSH und Start
  der Werkzeuge. [Snapshot-Auswertung](../../setup/tasks/carton_desktop_handoff_proof_20261120/observed-start/check-snapshot.log)
- ROSmini prüft die Bahn bei dem aktuell gemeldeten gemeinsamen Tempo.
  Der Transport bindet die Eingaben an die Zielpfade vor der Motion review.
  Prüferidentität, Bahnzeitstempel, Sollwerte und Parallelitätsnachweis bleiben
  erhalten. Die tatsächliche UR-Controllerbibliothek des N100 ist als lokaler
  Offline-Nachweis in `setup/skill_library/n100-checker/` hinterlegt, da sich
  dieser Binärhash von ROSmini unterscheidet. Die übrigen Prüferkomponenten
  stimmen überein. Der Web-Vorlauf vergleicht alle Komponenten je Lauf.
- Auf dem N100 akzeptierten die vorhandenen Modell- und Bündelprüfungen
  in einer isolierten Archivprüfung beide Pakete, aus frischem und aus
  wiederverwendetem Rezept. Beide Phasen blieben parallel mit nominell
  35,22 s und 8,78 s bei 33⅓ %. Die Offline-Planung auf ROSmini dauerte für
  die archivierte Bahn mit vorhandener Pose und Rezept 18,09 s. Die lokale
  Übergabeprüfung wies geänderte Freigabesitzung und geändertes Tempo ab.
  Der vollständige lokale Archiv-Webworker inklusive kaltem Cache,
  Bildfit, Bahnprüfung und Bereitstellung der Übergabe brauchte 27,95 s.
  [N100-Nachweis](../../setup/tasks/carton_desktop_handoff_proof_20261120/live-checker.wEmXfM8p/n100-verify-cached.log)
- Der neue Empfänger ist auf dem N100 installiert. Vorgänger
  `~/uwa-ur-runtime/review-candidates/rosmini-handoff.A9eOvUVr/run_carton_cycle.py.before`.
  Der inaktive Standalone-Webserver auf Port 8780 wurde aktualisiert und
  sein Katalog geprüft. Der aktuelle Rezeptcache auf ROSmini ist aufgebaut.
  Der reale Armstart und die Kontaktentscheidung wurden in diesem Auftrag
  nicht ausgeführt. Treiber und Schutzdienste liefen weiter.

## Historischer N100-Weblauf vor der Umstellung, 20.11.2026

- Nutzer fragt, warum der Weblauf bei einer ungültigen Eingabe so lange unter
  „Planen“ steht. Beim Lauf `68173c28fafe44dcb9ac19155683be6a` um 12:47 AWST
  dauerte Klick bis Fehler etwa 86,6 s. Foto und Transferphase 15,51 s
  (Aufnahme 11,40 s), statische Rezeperzeugung 17,13 s, lesender Gelenksnapshot
  3,05 s, Bildregistrierung 44,80 s. Der übrige Vorlauf und Rücktransport
  dauerte rund 6,1 s. Die Bahnplanung wurde nicht aufgerufen.
- Gültige Kamerasitzung mit 1,606 px Prüf-RMS. Die bedruckte Kartonseite
  lag im Foto oberhalb des konfigurierten Detailausschnitts. Genau ein
  Auflagefit bestand im größeren Ausschnitt (56 Inlier, 5,886 px RMS bei
  6,5 px). Rohbildsuche und Kontrastvariante ergaben zusammen 19 protokollierte
  Versuchsresultate. Die Ablehnung erfolgte vor Planung, Review und Zielen.
- Die Weboberfläche ordnete den gesamten damaligen N100-Vorlauf „Plan both
  arms“ zu. Die Statusmessung erkannte `POWER_OFF` an beiden rechten Armen
  und `left_rear`. Der Ablauf hätte die Eignung des Startzustands erst
  nach der Kartonregistrierung im Planer ausgewertet.
- Originalbericht und Bildausschnitte in `setup/tasks/carton_web_timing_20261120/`.
  Der frühere Lauf um 12:44 hatte fast gleiche Wartezeit und denselben
  Registrierungsfehler. Die Auswertung hat weder einen Lauf noch eine
  Laufzeitänderung ausgelöst.

## Separate OAK4-Kamerareferenz im Kartonprogramm, 20.11.2026

- **Calibrate OAK4** nutzt `oak4_photo.sh capture --mode charuco`. Das
  Kartonprogramm übernimmt den vollständigen rechten Boardbezug zwölf
  Stunden ab Aufnahme. Passende ID, Fokus, Optik, Boarddefinition und
  Basisbindungen sind in der Sitzung gebunden. Nach Kameraverstellung
  oder Verschieben des Boards neu kalibrieren.
- Bei gültiger Sitzung entsteht die Kartonpose weiter aus dem aktuellen
  Bild. `stored_charuco_session` überspringt die Boardprüfung im Kartonbild.
  Offenes Einfahrbild bleibt Grundlage der Kontaktentscheidung.
- Erste Sitzung 20.11.2026 12:35:55 bis 21.11.2026 00:35:55 AWST.
  17 Marker, 1,606 px Prüf-RMS, Fokus 107. N100-Quellpaket aktiv, Vorgänger
  in `review-candidates/carton-camera-session.DYOAUmW7/previous/`. Der
  Web-Preflight und 29 bestehende Offline-Tests bestanden.
- Die Kartonregistrierung mit gespeichertem Boardbezug gelang auf ROSmini
  und N100 im Diagnoseausschnitt. Der Karton stand 12:41 weiter links
  außerhalb des normalen Greif-Suchbereichs. Reale Greifausführung steht
  aus. [Laufbericht](../../setup/tasks/carton_camera_session_20261120/report.md)

## Kamerareferenz-Abbruch im Karton-Weblauf, 20.11.2026

- Weblauf `f7badf0f257b4e95aecc7b5bdbab06ce` stoppte um 11:44:25 AWST
  nach Rezept und rein lesendem Snapshot bei `registration`. Der N100-Log
  meldet 3,988 px RMS und 5,377 px maximal bei Grenzen <2 und <4 px. Der
  Lauf erreichte keine Karton-Textursuche, Bahnplanung, Review oder Ziele.
- Das OAK-Foto `20261120-114332-standard-5eaef2a5` hat Fokus 107 und sieht
  16 Ecken der rechten IDs 52, 56, 59 und 63. Gegen die Aufnahme vom 19.11.
  18:31:18 verschieben sich die wiedererkannten Eckpunkte beider Boards
  gemeinsam nach rechts (mittlere Verschiebung rechts 3,54 px, links 3,78 px).
  Die physische Ursache ist offen. Der bestehende Weg für einen vollständigen
  aktuellen Kamerabezug braucht mindestens 48 gut sichtbare rechte Ecken.
- Im Snapshot des Laufs meldeten beide rechten Arme und `left_rear` nativ
  `POWER_OFF`. `left_front` war im Messfenster von 0,528 s stationär
  (größte Gelenkspanne 0,000072 rad bei 0,0005 rad Grenze). Diese Zustände
  sind ein zeitgebundener Befund und kein Grund für den Bildabbruch.
- Rohlog und Snapshot `setup/tasks/carton_board_reference_20261120/`. Der
  lokale allgemeine Safety-log-Export stammt vom Vortag. Zum Vorfall gehören
  die aktuellen Web- und N100-Laufberichte.
- Nutzer fragt nach thermischer Drift und möchte den Ablauf robuster machen.
  Fokus-107-Optik mit fx 5832 px und mittlerer Tiefe der 16 sichtbaren rechten
  Markerecken 1,334 m. Der horizontale Versatz von 3,536 px entspricht
  näherungsweise 0,035 Grad Sichtwinkel oder 0,81 mm quer zur Blickrichtung
  unter den jeweiligen Einzelannahmen. Beide Foto-Metadaten enthalten keine
  Material- oder Umgebungstemperatur. Ein reiner modellierter Höhenverlust
  der Kamera um 0,47 mm ergibt im Mittel −0,023 px horizontal und −1,080 px
  vertikal. Kippen oder differenzielle Dehnung bleiben offene Hypothesen.
- Die Offline-Auswertung vorhandener Bilder prüfte das linke Board als
  zusätzlichen Weltbezug. Selbst der beste separat am rechten Board
  geprüfte Fit landete bei 2,84 px RMS und 5,52 px Maximum. Eine brauchbare
  gemeinsame Pose braucht einen besser belegten Anker. Der vorhandene Weg
  mit ausreichend sichtbaren, fest angebundenen Markern am rechten Tisch
  erlaubt eine neue Kamerapose direkt aus der laufenden Aufnahme. Die
  automatische Zweiboard-Korrektur wurde nicht übernommen.
  Nachweis `setup/tasks/carton_board_reference_20261120/two-board-diagnostic.json`.

## Aktuell nach Klarstellung: kein Reserveblocker, UR-Startup offen

- Beide aktuellen Parallelphasen sind mit `geometric_only` und0,0m zusätzlichem
  dynamischem Stoppaufschlag geprüft. Der Prüfer ist bereits verwendet und
  entsprechend AGENTS.md dokumentiert; kein weiterer ungenutzter Prüfer,
  der zugleich Kommunikations-/Startupfehler beheben würde.
- attempt16 wurde vom Operator tatsächlich freigegeben. Regulärer ROS-Start
  unter vier bestätigten unbeladenen Holds war Bestandteil dieser Revision.
  Vor jedem Arm-/Fingerziel Abbruch nach30s Startup-Zeitüberschreitung des
  bestehenden `ur_bringup.py --apply --review-id ...`. Eligibility und
  Software-Witness-Reset unter Holds waren bestätigt; Startup-Abschluss nicht.
  Kein Fahrziel, kein Griff/Kontakt, keine automatische Wiederholung.
- Program-start.json blieb leer; deshalb nicht behaupten, ein bestimmter Arm
  sei in diesem Versuch erfolgreich gestartet oder dies sei ein Bremsreserve-
  Abbruch. Vorangegangener Verbindungsverlust RF/LR ist separat im Treiberjournal
  belegt. Native Zustände nach Timeout rein lesend neu erfasst unter
  `setup/tasks/carton_motion_review_20261119/after-attempt16/`.
- Offener Punkt ist die verlässliche reale Programmanbindung auf N100, kein
  fehlender geometrischer Parallelplan. Native Programm-/Frische-/Stoppgates
  nicht durch Entfernen räumlicher Reserven umgehen. Aktuell keine aktive
  Freigabe oder nächste Fahrwiederholung zugesagt.

## OAK-Texturabbruch im Weblauf behoben, 19.11.2026

- Weblauf `a266d02976094ab09d965be515332c22` brach um 18:20:57 AWST bei
  der Registrierung ab. Rezept und lesender Gelenksnapshot bestanden.
  16 rechte Board-Ecken bestätigten die Kamerareferenz mit 1,970 px RMS
  bei einer Grenze von 2 px. Alle 36 Texturnachweise scheiterten am planaren
  Konsens. Der Karton lag im Ausschnitt. Keine Planung, keine Zielsendung.
- Wenn `--planar-texture` zu wenige gültige Fits liefert, prüft der
  Registrierer den Ausschnitt der bedruckten Seite nach lokaler Kontrastanpassung
  (CLAHE). Die bisherigen Geometrie-, Reprojektions-, Auflage- und
  Übereinstimmungsgrenzen gelten. Bei zwei Fotos muss jedes einen eigenen
  gültigen Fit beitragen. Erfolgreiche Rohbild-Fits gehen in den Vergleich ein.
- Dasselbe Originalbild bestand lokal und auf dem N100 mit 25 und 24
  übereinstimmenden Texturpunkten. Auflagefehler 2,97 und 3,11 px bei jeweils
  6,375 px Grenze. Streuung zwischen den Posen 0,227 mm und 0,058°. Der alte
  erfolgreiche Fotofall vom 13:24-Lauf war numerisch identisch ohne CLAHE.
  Die lokale Offline-Planung aus dem Snapshot des abgebrochenen Weblaufs
  ergab zwei gemeinsame rechte Gruppen mit nominell 32,21 s und 8,78 s.
- Registrierer auf den N100 übernommen. Vorgänger gesichert in
  `~/uwa-ur-runtime/review-candidates/carton-vision.G23jmlMj/previous.py`.
  Sechs Web-Prüfsummen stimmen, Katalog meldet Live verfügbar. Kein neuer
  Echtlauf ausgelöst. Nachweise `setup/tasks/carton_web_registration_20261119/`.

## Live-Starttaste am Arbeitsplatz wieder verfügbar, 19.11.2026

- Nutzer meldete den deaktivierten Webstart und fragte nach Play. Gemeint war
  der Status des laufenden UR-Programms `ros.urp` mit External Control in der
  vorherigen Messung. Die Webtaste folgt der Konfiguration der Serverinstanz.
- Die auf Port 8780 tatsächlich benutzte Standalone-Instanz war ohne
  `--live-config` gestartet. `GET /api/catalog` meldete `live_available:
  false`, obwohl die Optikdatei vorhanden war. Eine abgeschlossene Demo war
  der letzte Lauf.
- Umgestellt auf dieselbe Loopback-Adresse mit `--live-config` und der
  transienten Benutzereinheit `uwa-program-library.service`. Verifiziertes
  `GET /api/catalog` meldet `live_available: true`. Vorhandene Browserseite
  neu laden. Kein Kartonlauf ausgelöst. Nachweis
  `setup/tasks/uwa_program_library_live_button_20261119/verified.json`.

## N100 für den benannten Webstart eingerichtet, 19.11.2026

- Nutzer beauftragte nach dem Versionsabbruch die Übernahme. Installiert
  wurden `tools/run_carton_cycle.py`, `tools/prepare_carton_recipe.py` und
  `config/carton_programs/carton-supported-v1.json` aus Stand `9c21fcf`.
  Vorherige Skripte auf dem N100 in
  `~/uwa-ur-runtime/review-candidates/carton-program.xm6X1qFA/previous/`.
  Der Wächter lief durch (PID 505211, `NRestarts=0`).
- Der lesende Web-Preflight bestätigte alle sechs Dateihashes, einen
  freigegebenen Arbeitsbereich und keine offene Review. Der N100 erstellte
  aus archivierter Pose und Gelenkmessung zur hohen Anfahrt und offenen
  Einfahrt jeweils eine gemeinsame Bahn der beiden rechten Arme. Nominell
  35,22 s und 8,78 s bei 33⅓ %. Rechenzeit in diesem Einzelfall 149,98 s.
- `setup/skill_library/live-carton.json` ist auf ROSmini für den bekannten
  rechten Aufbau aktiv, Fokus 107. `GET /api/catalog` meldete den Live-Start
  verfügbar. Die unabhängige OAK-CLI und SDK sind vorhanden. Es wurde kein
  Foto angefordert, kein Lauf zur Freigabe gestellt und kein Programm gestartet.
- Die rein lesende UR-Abfrage meldete `right_rear` bereit. Bei `right_front`,
  `left_front` und `left_rear` ist `Play` der nächste Vorbereitungsschritt.
  Die Programmbibliothek setzt betriebsbereite Programme voraus. Nachweise
  `setup/tasks/carton_agent_free_n100_setup_20261119/`.

## Agentenfreier Webstart bis zum ersten Blocker, 19.11.2026

- Nutzerauftrag: den vorhandenen Ablauf bis zum ersten Hilfepunkt testen und
  dort gemeinsam weitersehen. Um 18:01 AWST nahm die Bibliothek einen Live-Start
  für `carton-supported-v1` an. Der Testserver nutzte die dokumentierte
  Optikkonfiguration in einem separaten Laufordner.
- Der Ablauf stoppte in `live_preflight` am SHA-256-Abgleich von
  `tools/run_carton_cycle.py`. Der N100 hat eine andere Runner- und
  Rezepterzeugerversion. `config/carton_programs/carton-supported-v1.json`
  fehlt dort. Registrierer, Fahrprofil und Texturmodell stimmten bytegleich
  überein. Vorab war der Arbeitsbereich laut N100 freigegeben, offene Reviews
  gab es keine.
- Der erste Blocker liegt vor der OAK-Aufnahme. Kein neuer Review-Eintrag,
  Programmstart, Arm- oder Fingerziel. Testserver beendet. Der Test hat die
  Wrist-Bildentscheidung und die reale Programmstartphase nicht erreicht.
  Nachweis `setup/tasks/carton_agent_free_live_20261119/result.json`.

## Bedarfsabhängiger UR-Programmstart, 19.11.2026

Die bedarfsabhängige Play-Freigabe ist im aktiven N100-Kartonrunner installiert (Sicherung und Hashlisten unter `~/uwa-ur-runtime/review-candidates/program-readiness.2oUsF55y`). Lokale Prüfungen: 27 Review-/GUI- und 30 Dashboard-/Power-Tests bestanden. Lesender N100-Test meldete rechts hinten bereit, die anderen drei Arme mit nächstem Schritt Play. Alle Befehlslisten waren leer. Keine Fahrt und kein Dienstneustart. Der N100 behält seine vorhandene Rezeptvariante.


## Aktuell: Parallelprüfer reservefrei, Programmstart getrennt,19.11.2026

- Nutzerklarstellung beantwortet: Der korrigierte Motion-review-Parallelprüfer
  ist bereits im Einsatz. In beiden attempt15-Gruppen (hoch und Einfahrt)
  `geometric_only`, für jedes geprüfte Paar zusätzlicher Stoppaufschlag0,0m.
 40mm Modellabstand und bestehende Laufzeitstopps bleiben wie vereinbart.
- Reiner Bereitschaftsschritt14 war tatsächlich PASS, danach verlor jedoch
  RF/LR um17:31:40 die UR-Reverse-Verbindung. Driverjournal belegt zeitgleiche
  Disconnects; keine Brems-/Latenzreserve als Ursache behaupten. attempt15
  wurde operatorbewilligt, stoppte vor jedem Armziel an nicht laufendem
  RF-Programm. Empfänger lebte, kein Receiverfehler. Rechte Greifer offen,
  keine weitere Bewegung/kein Griff. Tatsächliche Parallelfahrt noch offen.
- Fremder Diagnose-Guardwechsel laut seinem Arbeitsstand bereits17:14:28;
  aktueller Dienst NRestarts0. Dies nicht als Neustart um17:31 oder belegte
  Ursache der späteren Reverse-Abbrüche darstellen. Bestehenden Guard erhalten.
- attempt16 verwendet denselben geprüften Parallelweg nach erneutem frischem
  Startvergleich und vollständigem Sweep-/Timingcheck. Regulärer ROS-Start
  nach komplettem Graphaufbau vor jeder unbeladenen Fahrphase explizit Teil
  der neuen Reviewrevision. Nur falls nötig und unter frisch bestätigten
  vier offenen/unbeladenen/stationären Holds; keine Power-/Brake-/native
  Sicherheitsquittierung und keine Wiederholung nach Kontakt/Fehler.
- Das ist eine getrennte Betriebsanbindung, keine Rückkehr dynamischer
  räumlicher Reserven. Neue GUI-Revision erforderlich, keine alte Freigabe
  verwenden. Nachweise und Arbeitsstand weiterhin im Karton-Taskordner.

## Klarstellung zur Parallelprüfung,19.11.2026

- Nutzer fragt nach, ob mit „neuem Prüfer“ ein weiterer noch nicht verwendeter
  Baustein gemeint war und ob entfernte Brems-/Latenzreserven wieder greifen.
  Gemeint ist der inzwischen korrigierte Motion-review-Prüfer, bereits auf
  N100 eingesetzt. Keine erneute Einführung dieser Zusatzreserven beauftragt.
- Aktuell `geometric_only`: zusätzliche Brems-, Datenalter-/Abtast-, Reaktions-
  und Latenzaufschläge wirksam null, auch für gleichzeitig bewegte Paare.
  attempt15/high zeigt für alle fünf geprüften Paare ausdrücklich
  `stop_allowance_in_clearance_bound_m: 0.0`.40mm Modellpuffer, vollständige
  Geometrie-/Fortschrittsprüfung und bestehende Laufzeitstopps bleiben.
  Die Parameter für `enforce` dürfen bestehen, greifen hier aber nicht.
- Empfangsrückstau und Reihenfolge der Zielbestätigungen waren separate
  Ausführungsfehler. Ein geometrischer Parallelprüfer löst sie nicht mit;
  Korrekturen und Nachweise getrennt dokumentieren. Vollständige tatsächliche
  Parallelfahrt nicht mit bestandenem Modellnachweis gleichsetzen.
- Reiner Bereitschaftsschritt14 tatsächlich operatorbewilligt und PASS:
  alle vier Programme RUNNING/Normal, Ressourcenholds/Latches bestätigt,
  keine Arm-/Fingerziele,8s Livevergleich maximal0,001919rad konservativ.
  Nun attempt15: vorhandene Geometrie nur nach frischem Startvergleich
  weiterverwendet (maximale Abweichung0,000081rad bei0,0005rad Starttoleranz),
  Quellen und vollständige zeitparametrierte Sweeps neu geprüft. Kein
  automatisches Play in dieser Fahrrevision, Programme bereits bereit.

## Gazebo-Kartonreibung, 19.11.2026

- Nutzerhypothese: Die reale Verformung der Kartonwand durch die Greifbacken
  könnte zum Kraftschluss etwas Formschluss beitragen. In der starren
  Gazebo-Hülle wurde auf seinen Vorschlag zunächst der Reibwert erhöht.
- Das schnelle Zeichnungsprofil setzt 1,0 nur für die vier rechten
  Greifpad–Karton-Paare. Das virtuelle Motordrehmoment blieb 0,7 Nm.
  Die Boden-/Tischkontakte folgen dem bisherigen Materialansatz. Die
  Änderung gehört zur Kontaktphysik und erfasst keine Laufzeitmessreihe.
- Wiedergabe bei bis zu 1 rad/s durch alle 44 Planphasen bis zum Öffnen.
  163,1 mm Hub und 22,9° Endneigung am Tischspalt. Der höhere Reibwert
  allein beseitigte die Schräglage in diesem Lauf nicht. Bericht und Bild
  unter setup/tasks/house_drill_gazebo_friction_20261119_01/report.md.
- Am 20.11.2026 meldete der Nutzer aus der laufenden Gazebo-Ansicht, dass
  der Karton schon während der Drehung im Griff verrutscht. Das seitliche
  Moment am Greifer ist seine Erklärung. Die Endpose am Tisch dokumentiert
  nur den Endzustand. Schlupf und Moment wurden während der Drehung nicht
  gemessen.
- Auf Nutzerwunsch vom 20.11.2026 wurde dieselbe Haus-/Bohrdemo live in
  Gazebo mit einem effektiven Greifpad–Karton-Reibwert von 1000 abgespielt.
  Der Nutzer beobachtete während der Drehung kein Verrutschen im Griff.
  Das separate Versuchsprofil behält die schnelle Zeitparametrierung und
  den bisherigen Greiferantrieb. [Laufbericht](../../setup/tasks/house_drill_gazebo_high_friction_20261120_01/report.md)
- Der anschließende Gazebo-Lauf vom 20.11.2026 mit Reibwert 50 absolvierte
  alle 44 Phasen und setzte den Karton aufrecht ab. Hin- und Rückdrehung
  zeigen im Mitschnitt kein sichtbares Verrutschen. Die Offline-Bahnen
  stimmen mit dem Lauf bei 1000 numerisch überein. 50 ist der niedrigste
  bisher erfolgreiche Vergleichswert nach Sicht, der Mindestwert bleibt
  offen. [Laufbericht](../../setup/tasks/house_drill_gazebo_friction50_20261120_01/report.md)
- Am 20.11.2026 lief das erweiterte Programm mit Reibwert 20 und bis zu
  1 rad/s in Gazebo. Drei Kreise, Haus, sechs virtuelle Bohrzustellungen,
  zweite Drehung und vollständiger Rückweg. Die rechten Arme lassen die
  Box beim letzten Kreis am festen Stift kreisen. 54 Phasen, 52.070
  Modellzustände und 162,5 mm Gazebo-Hub, danach beide Greifer geöffnet.
  In der nativen Aufnahme kein deutliches Verrutschen erkennbar. Die alte
  Gegenwandpose scheiterte am rechten Hinterarm, die Endpose wurde rund
  31 mm verschoben. [Rezept- und Laufnachweis](../../setup/tasks/house_drill_box_circle_friction20_20261120_01/report.md)
- Der anschließende Gazebo-Gesamtlauf vom 20.11.2026 begann mit vier
  Armen in Home und dem Karton vollständig auf der rechten Tischplatte.
  Beide rechten Arme fuhren gemeinsam an und griffen über vier Padkontakte.
  Der vorhandene Compiler prüfte ab dem so gebildeten Griff 54 Phasen mit
  53.040 Modellzuständen bei bis zu 1 rad/s. Gazebo meldete 162,9 mm Hub,
  54 erfolgreiche Folgeaktionen und danach beide Greifer offen. Reibwert 20.
  Die Box erzeugt den Gegenwandkreis am feststehenden virtuellen Stift.
  Halter und dort sichtbarer Stift bleiben Ansichtsmodelle. Der lokale
  Simulationsbildfit nutzt für den stehenden Karton die Tischhöhe; ein
  vorheriger freier Bildfit hatte den Hub in der Offline-Prüfung blockiert.
  [Laufbericht und Mitschnitt](../../setup/tasks/house_drill_home_20261120_01/report.md)

## Gazebo-Tempo und Freigabe neuer Wächter oder Tests, 19.11.2026

- Nutzerentscheidung für alle Agenten. Das höchste derzeit zulässige und
  für die Aufgabe genehmigte Bewegungstempo verwenden. Gazebo bis 1 rad/s
  je Armgelenk. Weitere Wächter oder Tests nur mit ausdrücklicher
  Einwilligung des Nutzers. Bestehende Offline-Planprüfung weiterverwenden.
- Haus-/Bohr-Demo: `cell_task prepare --drawing-recipe RECIPE` wählt das
  schnellere Gazebo-Profil. Das Zeitgesetz des Compilers nutzt dessen
  Grenzen, die räumliche Auflösung der bestehenden Planprüfung bleibt
  erhalten. Physiktakt 1 ms, Echtzeitfaktor 1 als Ziel. Nachweise und
  Vergleich mit 0,1 rad/s unter `setup/tasks/house_drill_gazebo_fast_20261119_01/`.
- Am 20.11.2026 bestätigte der Nutzer dieses schnelle Tempo als Standard
  für künftige vergleichbare Gazebo-Demos.
- Offline auf dem archivierten Griff kompiliert. 44 Phasen, 23.464
  Zustände, 80,36 s Simulationszeit ab Hub statt 390,11 s. Rückdrehung
  15,55 s statt 107,53 s. Planstützstellen bis 0,999992 rad/s.

- Schnelle Gazebo-Wiedergabe run02 abgeschlossen: 44 Phasen,
  162,68 mm Hub, vollständige Haus-/Werkzeugfolge und Öffnen.
  Wandzeit ab Hub bis Öffnen 2:38 min statt 26:35 min.
  Schräglage an der Tischkante im nativen Endbild weiter sichtbar.

## Gazebo-Wiedergabe und Offline-Planprüfung, 19.11.2026

- Nutzerentscheidung für Gazebo. Bewegungsbahnen offline prüfen, die
  Simulation für die Wiedergabe und physische Kontakte verwenden.
  Laufzeitwächter für Kollision, Frische, Schlupf, Stillstand und Gelenke
  einschließlich passiver Finger samt Gazebo-Störfalltests entfernt.
- Der normale Zellstart, die Kontaktwelt und die Kalibrierung verwenden
  reguläre Controlleraktionen. Die Greifpads schalten die simulierte
  Greifvorspannung. Die Schutzkette für echte URs bleibt getrennt.
- Haus-/Bohr-Demo mit 0,1 rad/s im Ordner `setup/tasks/house_drill_gazebo_playback_20261119_01/`.
  Alte Versuchswelt beendet und ursprüngliche Artefakte erhalten.
  Neue Kontaktwelt mit nativer Gazebo-Ansicht. 44 Phasen mit 19.594
  Modellzuständen und 390,11 s geplanter Simulationszeit ab Hub offline
  geprüft. Die Bewegungsphasen stehen in `run01/state.json`.
- Der Gazebo-Lauf hat alle 44 Phasen ab Hub und das Öffnen beendet.
  162,97 mm Hub aus Gazebo, Kreis, acht Hauskanten und sechs virtuelle
  Zustellungen. Der Karton steht nach dem Öffnen schräg an der Tischkante.
  Die geplante Auflage überbrückt den 191-mm-Spalt. Native Bilder und Ergebnis
  in `report.md` im Laufordner. Gazebo-Fenster offen belassen.
- Lyrical-Build für fünf Pakete erfolgreich. 135 gezielte Offline-Tests
  bestanden. Zwei Alt-Fixtures mit abweichendem Basisursprung bzw. Modellhash
  zeigen denselben Fehler in der Ausgangsversion. Details im Laufordner.

## Aktuell: Empfangs-FIFO korrigiert, 19.11.2026

- attempt13 wurde in der echten GUI vom Operator freigegeben, noch bevor eine
  zusätzliche Chatfrage nötig war. Abbruch im Preflight vor jedem Arm-/Finger-
  ziel: `right_front: driver JointStates unavailable/stale`. Native Messung:
  für beide Arme keine Bewegung über0,003rad/s. Kein Kontakt, Karton frei.
- Neue Daten zeigen den zu großen neuen Empfangspuffer als konkretes Problem:
  Driverpakete wurden zuletzt bereits196,7/198,8ms alt verarbeitet, danach
  an der unveränderten200ms-Grenze verworfen; nativeRTDE-Daten blieben frisch.
  Queue128 kann bei500Hz bereits256ms Rückstau enthalten. Keine Frischegrenze
  erhöhen, keine alten Pakete als aktuell deklarieren.
- Eigenen Empfänger beibehalten, Queue auf ursprüngliche Sensor-Tiefe5
  korrigiert. Die große FIFO war hier eine Fehlentscheidung. Quellzeit,
  Epochen-, Lücken-,5mrad-,200ms-, Geschwindigkeits- und Geometriestopps bleiben
  unverändert. Empfängerfehler/Threadleben jetzt im Fehlerbericht enthalten.
-12 gezielte Empfänger-/Ausführungsprüfungen PASS. Neuer rein passiver N100-
  Nachweis verlangt bereits laufende, gehaltene UR-Programme; er startet
  keine Programme und sendet keine Ziele. Noch keine weitere Reviewversion
  zur Fahrt bereitgestellt, bis dieser Empfangsnachweis ausgewertet ist.
- attempt13-Ticket0d108c72db544069b597e6bff47df419 ist failed; vorherige
  Freigaben nicht wiederverwenden. Physischer Start zuletzt wie nachattempt11,
  vor weiterer Fahrt wieder frisch prüfen. Tasknachweise unverändert unter
  `setup/tasks/carton_motion_review_20261119/`.

## UWA-Programmbibliothek und Bildauswertung, 19.11.2026

- Nutzer wünscht eine lokale Webbibliothek mit Übersicht, Detailansicht und
  Programmstart neben UWA Robot Power. Der eingerichtete Kartonlauf soll die
  Pose- und Vorgrifferkennung selbst aufrufen können. Desktop-Fenster startet
  den Loopback-Server auf ROSmini, **Program library** öffnet dessen Adresse.
- HTTP-Test aus dem Qt-Mock startete den Archivlauf, prüfte Phasenstatus,
  Laufabschluss und alle drei JPEG-Vorschauen. Der neu registrierte
  Kartonursprung lag bei x=0,614 m, y=−0,166 m und z=0,900 m. 16 im Bild
  sichtbare Board-Ecken bestätigten die Kamerareferenz.
  Beide Phasen parallel, 44,0 s nominelle Armfahrt. 38,4 s Testwandzeit.
  Ein gleichzeitiger zweiter Start und Anfragen von anderer Herkunft wurden
  abgewiesen. 53 gezielte Tests bestanden. Der Browserzugriff für eine
  visuelle Prüfung war nicht verfügbar.
  Nachweis `setup/tasks/uwa_program_library_check_20261119/verified.json`.
- In den separaten echten Vorgriffaufnahmen lag der vordere Prüfpunkt bei
  y=2236 px und 1944 px Bildhöhe außerhalb des Bilds. RR gelbe Randlinie gemessen,
  Line-Fit-RMS 4,84 px und 50,16 px Bildabstand zum angenommenen Prüfpunkt.
  Beide Backen und Griffmitte waren damit nicht belegt. Aggregatstatus
  `REVIEW_REQUIRED`. Die im Modell aus der real gemessenen offenen Einfahrt
  projizierten Prüfstellen liegen an beiden Wrists außerhalb der Bildfelder.
  Nachweis `setup/tasks/uwa_program_library_check_20261119/wrist-entry-fov.json`.
- Live-Brücke lokal vorbereitet und mit simulierten Erfolgs- und Abbruchfällen
  geprüft. Sie verwendet die vorhandene OAK-Registrierung auf N100, fordert
  Motion review an und reicht nach offener Einfahrt ein aktuelles OAK-Foto
  zur Kontaktfreigabe ein. Keine reale Übernahme, Aufnahme oder Fahrt in
  dieser Arbeit. FoundationPose bleibt der dokumentierte RGB-D-Archivpfad.
  [Bedienung und Konfiguration](docs/carton_motion_review.md#programmbibliothek-im-browser)

## Aktuell: gemeinsamer Start korrigiert, 19.11.2026

- Operator hat attempt12 tatsächlich freigegeben. Die vorbereiteten Phasen
  waren beide parallel (RF/RR, nominell40,972s). Beide Armtargets wurden mit
  gemeinsamer Startzeit versandt; Versandabstand33,46ms. Abbruch noch in der
  Zielannahme: `Missing timely group acceptance before the common trajectory
  start`. Native Aufzeichnungen zeigen für beide Arme keine Bewegung über
  0,003rad/s. Kein Griff, keine Fingerziele, Karton weiter frei.
- Abschluss des Abbruchs bestätigte Ressourcenholds und Latches aller vier;
  kein nativer Fallback nötig. Frischer attempt13-Start: alle vier stationär,
  RUNNING/Normal, Programme laufen/runtime2. RF etwa [0,13699;−1,53424;
  −0,81925;−1,48620;0,68677;−0,65051]rad. Neue Freigabe war nur für attempt12;
  nicht auf eine veränderte Ausführung übertragen.
- Konkreter Reihenfolgefehler korrigiert: Der Ausführer wertete vor den
  Zielantworten bereits volle FCL-Geometrie aus und prüfte den Timeout vor
  den Antwortfutures. Antworten jetzt vor blockierender Geometrie auswerten.
  Fehlende oder erst verspätet beobachtete Antwort stoppt weiterhin bei100ms,
  gemeinsame Startvorlaufzeit bleibt200ms. Während Annahme Startpose,
  Quellfrische, Korridor, ruhende Arme, Greifer/Kraft und unabhängigen Guard
  weiter prüfen; volle Geometrie vorab und nach gemeinsamer Annahme.
-10 gezielte Ausführungsprüfungen PASS, darunter130ms langsame Geometrie erst
  nach beiden rechtzeitigen Annahmen, fehlende/zu späte Antwort, Widerruf,
  Greifer- und Wrenchfehler. Kein Zeitfenster, Tempo oder Stopp gelockert.
  Die vorher fehlenden Antwortzeitstempel werden künftig mitprotokolliert;
  tatsächlich rechtzeitige Controllerantworten für attempt12 sind dadurch
  rückwirkend nicht nachgewiesen.
- attempt13 wird als neue vollständige Parallelrevision vorbereitet; noch
  keine Freigabeanfrage und keine weitere Fahrt. Nachweise im Taskordner
  `setup/tasks/carton_motion_review_20261119/` auf N100/ROSmini.

## Aktuell: Parallelkorrektur vorbereitet, 19.11.2026

- Nutzer hat die besprochene Korrektur mit „approved“ bestätigt. Seine vorherige
  echte GUI-Freigabe bezog sich noch auf attempt11/seriell: nur RF fuhr ein
  weiteres Stück, dann Stopp am RR-Zeitvergleich, kein Griff/Kontakt. Danach
  frischer Snapshot `after-attempt11`: alle vier RUNNING/Normal/STOPPED,
  Trendruhe bestätigt, rechte Greifer OBJ3/POS3/PRE0/FOR0/SPE16 offen.
- Tatsächlicher RF-Start jetzt etwa [0,13697; −1,53424; −0,81926; −1,48625;
  0,68666; −0,65050]rad. Alte Home-/Teilstarts nicht wiederverwenden.
- Konkreter Abbruchnachweis: ruhender RR Rohabweichung höchstens0,0000474rad,
  aber konservative Interpolationsunsicherheit0,006293rad durch124ms-Lücke
  der Driverhistorie. Daher stoppt unveränderte0,005rad-Grenze. Keine reale
  Positionsabweichung dieser Größenordnung aus dem Fehlertext ableiten.
- Neuer eigener Driver-Empfänger hält die Historie unabhängig von FCL/RPC-
  Arbeit aktuell. Profilkorrektur entfernt nur das interne Erzwingen
  dynamischer Hüllen unter `geometric_only`; volle Geometrie/40mm und alle
  unabhängigen Fortschrittskombinationen bleiben geprüft. Geschwindigkeit,
  Frische, Vergleichsgrenzen und native Stopps unverändert. Bei `enforce`
  bleiben die zusätzlichen unabhängigen Stoppreserven bestehen.
-35 gezielte Prüfungen PASS; Motionpaket lokal/N100 gebaut, kein Guard- oder
  Treiberneustart. Passiver N100-Nachweis: tatsächlich150,8ms Hauptthreadpause,
  RF63/RR79 neue Samples, danach5,6/7,6ms Sourcealter. Maximal konservativ
  0,001002rad, maximale Zeitklammer29,97ms, keine Clock-/Empfängerfehler.
- attempt12 vollständig vorbereitet: hohe Anfahrt und offene Einfahrt jeweils
  eine gemeinsame RF/RR-Gruppe, keine seriellen Rückfälle. Nominell32,187s+
  8,785s=40,972s bei unverändert33⅓%. WAITING_FOR_MOTION_REVIEW,
  Ticketc2dfde11df75406a9f66f104a65f4d4e,
  Versionb4f798dfcc68ce0069e5aef5fa87f8946006a6401924e5cd397494d724fd3a03.
  Tatsächlicher N100-Store bestätigt pending, neue GUI-Entscheidung angefragt.
  Noch keine weitere Fahrt. Nutzer meldete zuvor fehlende Aufforderung;
  erst jetzt wird das tatsächliche Vorliegen der neuen Anfrage bestätigt.
- Nachweise `setup/tasks/carton_motion_review_20261119/`; Arbeitsstand
  `work/carton-motion-review-real-20261119.md` im Zellrepo.

## Gespeicherter Kartongriff mit Pose als Eingabe, 19.11.2026

- Nutzerziel: denselben Aufgabencode für unterschiedliche Posen des bekannten
  Kartons aufrufen. Der Vorgänger konnte bereits die objektbezogenen Griffpunkte
  aus einer neuen OAK-Pose transformieren. Die Bedienschritte für Bildausschnitt,
  Rezepterzeugung und die separate Offline-Vorbereitung waren manuell verteilt.
- `carton-supported-v1` speichert das Griffdesign und die IK-Referenzen unter
  `config/carton_programs/`. `run_carton_cycle.py --program` erzeugt das Rezept
  und protokolliert die verwendete Definition mit SHA-256. `--plan-only` nimmt
  gespeicherte Pose und Gelenkmessung und verwendet dieselben Planungsphasen.
- Auf ROSmini zweimal aus demselben Vierarm-Snapshot bei 33⅓ % geplant. Die
  Archivpose aus `registration-v4` und eine synthetische Verschiebung von 50 mm
  in Welt-X ergaben jeweils gemeinsame Hochanfahrt und offene Einfahrt von RF
  und RR. Beide Weltgriffpunkte verschoben sich um genau diesen Betrag.
  Planungswandzeit 22,07 s / 21,68 s, nominelle Armfahrt 44,00 s / 44,10 s.
  48 gezielte Lyrical-Tests bestanden. Beide Paare von Bahnbündeln wurden als
  isolierte Mock-Replays geladen.
- Nachweise `setup/tasks/carton_program_reuse_20261119/comparison.json` und
  jeweilige `workflow.json`. Der Versuch deckt zwei Posen im Modell ab.
  Die zweite Pose stammt aus einer rechnerischen Verschiebung. Ein belegter
  Erkennungs- oder Greifbereich und der reale Einsatz des neuen Aufrufs stehen
  aus. Der neue Stand wurde lokal geprüft und liegt noch nicht auf dem N100.
  Anleitung in [Kartonfahrt mit Aufgabenfreigabe](docs/carton_motion_review.md).

## Parallelfahrt: konkreter Planungsblocker, 19.11.2026

- Nutzer fragt ausdrücklich nach weiterhin fehlender Gleichzeitigkeit und
  bekräftigt deren frühere Freigabe/Anforderung. Aktueller Plan attempt11
  wartet unverändert auf Motion review und enthält weiterhin serielle Gruppen.
  Diese Analyse verändert keine Freigabe, Betriebsgrenze oder Hardwareaktion.
- `reviewed_carton.py:prove_group` erzwingt bei zwei bewegten Armen über
  `stopping_reserve_policy='enforce'` zusätzliche unabhängige Brems-/Latenz-
  hüllen, obwohl das aktive Profil `geometric_only` verwendet. Auch die
  gerichteten Stoppboxen werden für bewegte Paare zusätzlich berechnet.
  Das ist eine Inkonsistenz zwischen Betriebsprofil und neuem Parallelprüfer.
- Konkrete attempt11-Untergrenzen im Modell für RF/RR: hohe Anfahrt rein
  geometrisch 41,36 mm, mit zusätzlicher Stopphülle −144,79 mm; Einfahrt
  geometrisch 160,21 mm, mit Stopphülle −122,58 mm. Gefordert 40 mm.
  Negative Nachweisschranke ist kein beobachteter Kontakt. Gemeinsame Gruppen
  scheitern hier an dieser Zusatzprüfung; `compile_groups` wählt daraufhin
  RF und RR nacheinander. Keine fehlende Nutzerfreigabe für Gleichzeitigkeit.
- Der Prüfer kombiniert Armfortschritte unabhängig, statt die durch einen
  gemeinsamen Zeitplan tatsächlich erreichbaren Abweichungen zu begrenzen.
  Das verstärkt die Konservativität; ein gemeinsamer Start wird vom Executor
  bereits unterstützt. Tatsächliche zeitgleiche Hardwareausführung ist durch
  diese Analyse nicht nachgewiesen. Clock-/Istwertabbrüche separat behandeln.
- Erkenntnis dokumentiert, noch keine Schutzberechnung geändert. Vor einem
  Parallelplan Profilkonsistenz und gemeinsamen Zeitablauf konkret prüfen;
  keinen bloßen Grenzabbau als bestandenen Modellnachweis ausgeben.

## Aktuell19.11.2026: Uhrmessung korrigiert, neue Reviewvorbereitung

- Operatorfreigegebeneattempt10 brach vor jedem Arm-/Greiferziel am Clockflag
  ab. Keine neueBewegung/keinKontakt. FrischerStartsnapshotattempt11 bestätigt
  alle4 nativRUNNING/Normal, ProgrammeSTOPPED/runtime1 undTrendruhe; rechte
  Greifer weiteroffen. RF-Teilpose seitattempt09 bleibt aktuellerStart.
- KonkreterSoftwarefehler imHost-Uhrvergleich korrigiert: ungeklammerte
  Wall-/Monotonic-Abfragen können Schedulingpause alsZeitsprung deuten.
  NeueAbfrage mit≤200µsPaarspanne/max3unmittelbarenVersuchen; unsichererRead
  liefertkeinenfrischenDriverSample. Messunsicherheit verbraucht zusätzlich
  vorhandene0,005radVergleichstoleranz.20msClockjump-/Header-/NativeEpoch-
  Stopps,200msFrische,0,1rad/s/40mm unverändert. KeineSchwellenlockerung.
-12Clock-/Alignment- und30Hardware-/ReviewmockprüfungenPASS. N100Passivlauf
  ohneClockFault; nachersten100Discoveryvergleichen maximal0,000101radraw,
 0,000963radkonservativ/25,99msDriverabstand/110,93msQuellalter. Anfangs alte
  Discoverydaten bis380mswurden nichtalsgültigerFahrstartverwendet; normale
  Connect-/Frischebedingungen bleiben erforderlich. Softwarebug belegt,
  vollständigeErklärung beiderRealabbrüche weiterunbewiesen.
- attempt11 vollständig vorbereitet, WAITING_FOR_MOTION_REVIEW,
  Ticket3240fa2e55a34fcbb8916764a00c7b53, neueOperatorentscheidung angefragt.
  GleicheSHA-geprüfteaktuelleZwei-Bild-Registrierung. KeinePower-/Play-/Reset-/
  Arm-/Greiferaktion bisneuer tatsächlicherGUI-Entscheidung. Kontext/Restunsicherheit
  imReviewgrundtext; keinealteFreigabewiederverwenden.
- Daten setup/tasks/carton_motion_review_20261119/; Arbeitsstand imZellrepo
  work/carton-motion-review-real-20261119.md.

## Historisch19.11.2026: zweites Review vor Fahrziel abgebrochen

- OperatorApprove für neueMotionrevision8f5bf4ac92c04c9995302bcb6452857a
  tatsächlich aufN100 angekommen. attempt10 startete reguläreROS-Programme
  unter unbeladenenHolds, aber **kein Arm-/Greiferziel**: noch im Preflight
  Abbruch `Device epoch changed; regenerate the hardware plan`. Keine weitere
  Bewegung seit RF-Teilanfahrt ausattempt09, kein Kontakt/Karton weiterhinfrei.
- NeueFehlerdaten zeigen alle4 nativenEpochen0 undnativeRuhe. Sammelfehler
  kann auch Host-Wall/Monotonic-Abgleich oder Driver-Zeitstempel bedeuten;
  keinen echtenUR-Neustart daraus ableiten. Je rechterJointState genau1Publisher
  reinlesendgeprüft, keinNachweis doppelterPublisher. WeitereZeitdiagnose nur
  passiv, keine neueReview-/Fahrwiederholung bis Ursache eingegrenzt.
- AlleGrenzen/Stopps/Tempo unverändert. BestehendeClock-Faults jetzt mitgenauer
  Ursache und Zeitpaar-Dauer protokolliert; kein automatisches Reset/Play.
  Endzustand nachdiesemAbbruch vorweitererFahrt erneutfrischbestätigen.
- Nachweise setup/tasks/carton_motion_review_20261119/attempt10/high/result.json
  und alignment-with-model-clock-events.log aufN100; Arbeitsstand imZellrepo
  work/carton-motion-review-real-20261119.md.

## Historisch19.11.2026: freigegebene Hochanfahrt gestoppt, kein Griff

- Operator hat Motionrevisionf252b03840344e83a5dea047c5f1cade tatsächlich in
  echter GUI bewilligt; Herkunftoperator, inzwischen Vertrauen50/Familiar,
  Tempo unverändert33⅓%. Die mittlere Risikostufe bleibt bedienpflichtig.
- attempt09 hat reguläre ROS-Programme unter unbeladenen Holds gestartet und
  nur RF ein tatsächliches Armziel gesendet. Nach3,75s beobachteter Bewegung
  Abbruch: `right_front: time-aligned driver cache differs from independent
  actual joints`. RR nicht gefahren, keine Fingerziele, keine Einfahrt/kein
  Kontakt/kein Hub. Reviewstatusfailed; kein automatisches Replay/Reset/Play.
- Frischer rein lesender Abschluss nach Stopp: alle4 nativRUNNING/Normal,
  ProgrammeSTOPPED/runtime1, genehmigte Trendruhe für alle4 bestätigt.
  RechteGreiferOBJ3/POS3/PRE0/FOR0/SPE16offen. RF nun leicht von Home versetzt:
  q≈[-0,04531,-1,57698,-0,05210,-1,57729,0,04580,-0,04859]rad.
  Alter Planstart ist überholt; kein automatisches Zurückfahren.
- Runner bestätigt Ressourcenholds/Latches, sein `standstill_confirmed:false`
  ist kein späterer Stillstandsnachweis; der neue Read-only-Snapshot bestätigt
  Stillstand separat. Ursache des Zeitabgleichabbruchs noch offen; Werte im
  neuen Reviewed-Fehlerbericht fehlen. Read-only-Zeitdiagnose in Arbeit,
  keine Grenze gelockert. NativeStopps des Schutzdiensts ebenfalls erhalten.
- Passive Diagnose mit und ohne FCL reproduziert den Vergleichsabbruch nicht:
  maximale Rohabweichung0,0001115rad, konservativ0,002538rad bei unveränderter
 0,005rad-Schwelle. Ursache weiterhin ungeklärt. Reviewed-Fehlerbericht um
  tatsächliche Vergleichs-/Zeitreihendaten ergänzt;8Mock-AusführungenPASS.
  attempt10 aus frischem Stoppstart vollständig vorbereitet, aktuell
  WAITING_FOR_MOTION_REVIEW. NeuesTicket8f5bf4ac92c04c9995302bcb6452857a,
  Version99488b56d809d74cdc10edde73d08c17f6a48b9bc62c8878af6cca88bf0c8820,
  nominell83,397s seriell. NeueBedienentscheidung angefragt; frühere Freigabe
  gilt nicht für dieseRevision. Noch keine weitere Fahrt.
- Daten setup/tasks/carton_motion_review_20261119/attempt09/high/ sowie
  after-reviewed-stop/ auf N100; Arbeitsstand im Zellrepo
  work/carton-motion-review-real-20261119.md. Vor weiterer Bewegung neuen
  tatsächlichen Start prüfen und neue genaue Reviewrevision vorlegen.

## Historisch19.11.2026: Motion-review-Planung wieder aufgenommen

- Nutzer erlaubt nach der POWER_OFF-Rückfrage ausdrücklich weiterzumachen.
  Vorhandener echter GUI-Start lief bereits; eigener Drives-only-Versuch wurde
  vor jeder Aktion von dessen Startsperre abgewiesen. Kein paralleler Start.
- Danach alle vier nativ RUNNING/Normal/STOPPED. Alle vier unbeladenen
  CollisionHolds unter frischer nativer/Driver-Ruhe an aktuelle Gelenke
  gebunden, jeweils PASS, keine Armbewegung/kein Play. RF-Basis bleibt nahe0°.
- Bestehende echte Bereichssitzung73300e040a5d407db9916ab38ee1d877 weiterhin
  freigegeben, Vertrauen0/Tempo33⅓% unverändert. Zwei neue native OAK-Fotos
  15:53:26 und15:53:52/Fokus107 auf N100 übertragen; Übersicht visuell geprüft.
- attempt08 direkte Zwei-Bild-RegistrierungPASS (26/24/24/24Inlier,
  interne1,450mm/0,368°; keine Absolutgenauigkeitsbehauptung). attempt09
  verwendet diese10 SHA-geprüften Eingaben weiter und nimmt frischen Iststart.
  Hohe Gesamtanfahrt UND offene Einfahrt vollständig vorbereitet.
  Aktuell WAITING_FOR_MOTION_REVIEW, Ticketf252b03840344e83a5dea047c5f1cade,
  echte GUI-Entscheidung ausstehend,84,294s nominell, beide Phasen seriell.
  Beide Ellbogen oberhalb Tisch, RF-Basisziel+0,389rad statt altem Umlauf.
  Reale Ziele erst nach echtem GUI-Approve; noch keine Arm-/Greiferziele.
  Wegsuchbudget60s ist nur Rechenzeit. Guard/Tempo/40mm unverändert.
  Letzte Snapshot-Moduskorrektur jetzt auf N100 übertragen.
- Nachweise setup/tasks/carton_motion_review_20261119/ auf ROSmini/N100.

## Motion review real übernommen,19.11.2026: Antriebe ausgeschaltet

- Nutzer hat nach manueller Kabelabwicklung den Arbeitsbereich erneut in der
  echten GUI freigegeben; Sitzung `73300e040a5d407db9916ab38ee1d877`.
  RF-Basis steht nun nahe0° (letzter eingeschalteter Messwert etwa−0,0572rad),
  der alte Start nahe−360° ist überholt. RF-CollisionHold wurde vor erneutem
  Play unter nativ STOPPED/Normal an die echte Pose gebunden; Nachweis PASS,
  keine Gelenkbewegung. Den alten Winkelumlauf nicht wieder anfahren.
- Aktueller zuletzt bestätigter Zustand: **alle vier URs POWER_OFF / NORMAL /
  STOPPED**, rechte Greifer offen, kein neuer Kontakt. In dieser Motion-review-
  Serie wurden **keine Arm- oder Greiferziele** gesendet. Nutzerklärung, ob
  bewusst ausgeschaltet oder wieder startbereit zu machen, steht aus.
  Bis zur Antwort keine Power-/Bremsen-/Programmaktionen. Konstante Positionen
  im ausgeschalteten Zustand sind kein gültiger gemessener Planungsstart.
- Neuer Motion-review-Softwarestand auf N100 übernommen: Quellbackup,
  18Pakete/24,2s Build PASS, vier Treiber, Greiferschnittstellen FOR0/SPE16
  und bewaffneter Guard mit bestehendem Trendprofil/RR20. Echte GUI läuft;
  Vertrauen0 und Tempo33⅓% bleiben Nutzerwerte. Noch kein ausführbarer
  Reviewauftrag zur Entscheidung, keine Freigabe durch den Agenten.
- Zwei aktuelle OAK-Bilder nach Bereichsfreigabe ergeben drei akzeptierte
  Textur-/Auflagefits mit24/25/24Inlier und4,045/4,283/4,151px Unterstützung.
  Interne Streuung0,107mm/0,0394° beschreibt Konsistenz, keine absolute
  Genauigkeit. Historische Foto-/Kamerareferenzen sind SHA-gebunden;
  die Objektpose stammt aus aktuellen Bildern, globale Profile unverändert.
- attempt01–03 scheiterten vor Bewegung an Bild-/Referenzbedingungen;
  attempt04/05 vor Planung an Startbereitschaft. Snapshot verwendet jetzt
  dasselbe genehmigte Trendruhekriterium wie der Guard und verlangt zusätzlich
  native Betriebsbereitschaft.17 gezielte Tests PASS; letzte native Modusprüfung
  bisher nur lokal, noch nicht auf N100 übertragen. Keine Geschwindigkeits-,
  Frische- oder Kollisionsgrenzen gelockert.
- Nach Wiederherstellung frische tatsächliche Startwerte und bestehende
  Haltesollwerte prüfen; komplette hohe Anfahrt/offene Einfahrt als eine
  Revision zur echten GUI-Entscheidung. Vor Kontakt aktuelles Einfahrbild und
  eigenes Kontaktreview. Kein Hub oder Transport beauftragt.
- Nachweise `setup/tasks/carton_motion_review_20261119/`; ausführlicher Stand
  im Zellrepo `work/carton-motion-review-real-20261119.md`.

## Neuer Kartonort: bis Start vorbereitet, Hardwarepause19.11.2026

- Nutzer meldet umgestellten Karton; während Erkennung stoppt er Hardware und
  erlaubt ausdrücklich nur Vorbereitung bis zum Start. **Keine Programmstarts,
  Arm-/Greiferziele oder Ausführung bis zu neuer Nutzerrückmeldung.** Letzter
  bestätigter Armzustand Home/offen; aktuelle native Bereitschaft nach Pause
  erst vor Ausführung neu prüfen. In dieser Sequenz kein Armziel gesendet.
- Neues OAK-Standardbild13:24:16/Fokus107: Kartonzentrum gegenüber vorheriger
  Pose etwa434,5mm versetzt und15,73° gedreht. Rechtes Referenzboard durch Karton
  teilweise verdeckt. Explizite bisherige vollständige Kameraregistrierung gegen
  aktuelle16Ecken validiert: RMS1,771px/max2,933px. Keine neue Extrinsic aus
  wenigen Ecken, keine alte Objektpose verwendet; globale Kameraprofile gleich.
- `register_carton_from_oak.py --camera-reference-pose ... --planar-texture`
  mit aktuellem Bildausschnitt erfolgreich (`registration-v4/`). Drei akzeptierte
  aktuelle Textur-/Tischauflagefits mit25/25/26Inlier, Unterstützung4,27/5,00/
  4,52px; interne Streuung2,866mm/0,682°. Vorschau visuell geprüft. Keine
  Behauptung absoluter Genauigkeit oder qualifizierter realer Kontakte.
- Konkrete Visionkorrektur: planare Modellfeatures über Homographie-Konsens
  auf entzerrten Pixeln vor IPPE bewerten, statt vorab allein EPNP zu verlangen;
  bestehende Positivtiefe-/Mehrdeutigkeits-/RMS-/Inliergrenzen erhalten. Opt-in
  affine Merkmalsansichten und panelweise Zuordnung, Ergebnisse im Originalbild
  prüfen.8gezielteTracking-/ReferenztestsPASS. Alte Fehlversuchev1–v3 erhalten.
- Vollständige hohe Anfahrt UND nachfolgende offene Einfahrt geometrisch gültig.
  Auch tatsächliche serielle RF/RR-Vorpositionsbahnen mit Zeitparametrierung
  offlinePASS (`high-offline`: OFFLINE_CHECKED_NOT_EXECUTED); Einfahrt-Ausführer
  offlinePASS (`entry-offline`: OFFLINE_ENTRY_RECHECKED). Beide Ellbogen im
  Ziel etwa1,486m über Welt0, Tisch0,9m; gewünschte negative Ellbogenzweige.
  Reine nominale hohe Motorbahnen35,22+32,18s, keine gemessene Ausführungszeit.
- Auf zuletzt tatsächlich gemessenen Homezustand vor Nutzerstop gebunden;
  vor echtem Start weiter frische Start-/Halt-/Offenprüfung ohne Grenzlockerung.
 0,1rad/s/0,2rad/s²/40mm/Trendruhe unverändert. Aktueller N100-Stand genutzt;
  paralleler lokaler Motion-Review-Pilot nicht ungeprüft deployt oder aktiviert.
- Daten `setup/tasks/carton_new_pose_20261119/`, `prepared.json`, `pose-preview.jpg`;
  N100 gleichnamig unter `~/uwa-ur-runtime/`. `execute-prepared.sh` nur als
  Datei vorbereitet, NICHT gestartet. Es endet nach offener Einfahrt; tatsächliche
  neue Einfahrtaufnahme muss vor FOR0/SPE16-Schluss geprüft werden. Danach nur
  gemeinsame Objektgruppe/HOLD. Keine geladene unabhängige Armfahrt.
- Dieser Vorbereitungsabschnitt enthält Visionentwicklung und Hardwarepause,
  ist kein repräsentativer vollständiger Griffzeitlauf. Details im Arbeitsstand
  `work/carton-new-pose-20261119.md` im Zellrepo.


## Aktuell: Karton frei, rechte Arme Home,19.11.2026

- Nutzer bestätigt letzten Griff, verlangt Loslassen und Home, um Karton
  anschließend anders hinzustellen. Ausgeführt: beide rechten Greifer offen,
  OBJ3/POS3/PRE0/FOR0/SPE16, keine Kontaktmitglieder. Beide150mm nach oben
  freigefahren; anschließend beide tatsächlich Home mit Endholds bestätigt.
  Schlussnachweis `setup/tasks/carton_reposition_20261119/home-replanned/`
  `result.json`: PASS/BOTH_OPEN_AT_HOME_HELD, beide executed=true.
- **Jetzt keine neue Greifsequenz. Auf Nutzerumstellung warten.** Danach neues
  Foto und neue Kartonpose; alte Registrierungen sind historische Referenzen,
  keine aktuelle Zielpose des versetzten Kartons. Virtuelle Kontaktgruppe
  hat keine aktiven Mitglieder mehr; frühere Kontakt-HOLD-Aussagen historisch.
- N100 bleibt alleiniger UR-Steuerhost.0,1rad/s/0,2rad/s²/40mm/Trendruhe und
  bestehende Frische-/native Stopps unverändert. Linke Arme nicht verfahren.
- Release hatte kurzen Halte-Transienten trotz bestätigtem Öffnen; kein zweites
  Fingerziel. Erster Homeversuch durch generische Epochen-/Zeitprüfung gestoppt,
  alle4 Resourceholds/Latches bestätigt. Neuer Snapshot und komplett neue
  Homebahn anschließend tatsächlich PASS. Keine Überwachungsgrenze gelockert.
  Ursache der Zeitdiagnose noch nicht genauer belegt; Fehlerbelege erhalten.
- Lokale Nachweise unter `setup/tasks/carton_reposition_20261119/n100-evidence/`,
  N100-Originale unter `~/uwa-ur-runtime/setup/tasks/carton_reposition_20261119/`.
  Arbeitsstand `work/carton-reposition-20261119.md` im Zellrepo abgeschlossen.


## Sicherheitsprotokoll in UWA Robot Power, 19.11.2026

- Seit 19.11.2026, 17:14:28 AWST ist der geprüfte Guard auf miniminiPC aktiv. Für weitere Arbeiten diesen Stand verwenden. Die installierten Python-Module verweisen per Symlink auf die aktualisierten Quellen. SHA-256 für hardware_nodes.py beginnt mit 43bb1c691f01, für guard_core.py mit 5343b37f04fe. Alle 40 Kandidatentests bestanden. Dienstaufruf fe6d7a01decf464d93fe41843fd4c636. Sicherung unter `~/uwa-ur-runtime/review-candidates/guard-log-backup.sgiKZeF4`.
- Guard, Supervisor und Watchdog sendeten nach dem Neustart jeweils mehrere bewaffnete Statuspakete. Alle vier Arme meldeten Stillstand. Um 17:15 AWST bestätigte der Supervisor alle vier Holds und den Interlock. Der Watchdog war ausgelöst, die Fahrt gesperrt. Kein Reset und keine Fahrfreigabe im Rahmen des Wechsels.
- Über **Safety log → Save logs** oder die gleichnamige Desktop-Aktion kann die Bedienperson den N100-Bericht auch während einer offenen Freigabesitzung lesen und auf ROSmini sichern. Alte abgeschlossene Fehler lösen beim Öffnen des aktualisierten Power-Fensters keine erneute Entscheidungsaufforderung aus. [Bedienung](docs/ur_power_gui.md#investigating-a-stop)
- Erster geprüfter Export um 16:36 Uhr Perth. Von den letzten 600 nativen STOP-Anforderungen entfielen 578 innerhalb desselben rund 38-sekündigen Fensters auf den fehlenden oder ausgelösten Supervisor-Heartbeat, je eine Wiederholungsfolge pro Arm. Die Ausgabe kennzeichnet die Begrenzung der Journalquelle. Versuch 09 endete nach 3,75 s gemessener Bewegung von rechts vorne. Versuch 10 scheiterte vor dem ersten Armziel der Hochanfahrt. [Lesbarer Bericht](../../setup/logs/uwa-control/sessions/20261119_163625_617287_e599ab6a/safety-report.txt)
- Protokolländerung am Wächter lokal getestet. Künftige Einträge enthalten neue Ursachen im bestehenden Halt sowie bei DISTANCE den verfügbaren Abstand und Grenzwert. Der N100-Bericht funktioniert auch mit dem bisherigen Journalformat. 81 gemeinsame Regressionen für GUI, Export und Schutzlogik bestanden. In diesem Diagnoseauftrag keine Hardwareaktion und kein Neustart eines Schutzdienstes.

## Freigabe-Pilot für Kartonfahrten, 19.11.2026

- **UWA Robot Power → Motion review** auf ROSmini enthält Tray, Bereichsfreigabe,
  aufgabenspezifisches Vertrauen, Temporegler, Kontaktfoto und RViz für dieselben
  Sollbahnen wie der Executor. Der N100-Freigabeendpunkt ist installiert und
  per GUI-Statusprotokoll gelesen. Zustand beim Test: 33⅓ %, Vertrauen 0, kein
  freigegebener Arbeitsraum und keine Aufträge. Näheres in
  [der Bedienanleitung](docs/carton_motion_review.md).
- Eigentlicher Bewegungs-/Wächterstand separat auf dem N100 geprüft und
  **inaktiv** unter `~/uwa-ur-runtime/review-candidates/pilot.9wp9dKqF`.
  Hashprüfung, Python-Kompilierung und 10 isolierte Freigabetests auf dem N100
  bestanden. Der parallele reale Kartonauftrag verwendet seinen bisherigen
  Stand. Keinen laufenden Guard aus diesem Piloten ersetzt oder neugestartet.
- Lyrical-Build für beide geänderten ROS-Pakete bestanden. 107 gemeinsame
  lokale Regressionen bestanden, darunter Teilannahme vor gemeinsamem Start,
  Verlust der Freigabe während der Fahrt, Greiferkontakt und Wrench-Sprung.
  GNOME-Tray und ein echter isolierter Domain-74-RViz-Empfänger geprüft.
  Laufzeiten, Nachweise und fertig befüllte GUI-Mocks unter
  [setup/tasks/carton_motion_review_20261119](../../setup/tasks/carton_motion_review_20261119/).
- Archivfall RF/RR bei 33⅓ % fährt modellseitig seriell. Bei 10 % passt
  die offene Einfahrt im Modell parallel, nominell 23,28 s vs. 46,53 s für
  dieselben Bahnen nacheinander. N100-Betriebswert unverändert. Kein gemessener
  Hardware-Zeitgewinn dieses Piloten. Direkte ROS-/Pendantquellen bestehen,
  deshalb bleibt die reale Zelle auch ohne laufenden Pilotauftrag bewaffnet.
  Die Umschaltung auf den geprüften Softwarestand und die erste beauftragte Realfahrt stehen aus.

## Karton für Umstellen freigeben,19.11.2026

- Nutzer bestätigt Griff, möchte repräsentativen neuen Versuch mit umgestelltem
  Karton. Aktueller Auftrag ausschließlich: lösen, hochfahren, Home, danach warten.
- Beide rechten Greifer tatsächlich geöffnet: OBJ3/POS3/PRE0/FOR0/SPE16,
  remaining_contact_members[]. Releasebericht bewahrt kurzen Halte-Transienten
  (`HELD_OPEN_UNCONFIRMED`); keine Wiederholung des Fingerziels. Frischer
  Offen-/Armzustand aufgenommen; Rückzug/Home mit vorhandenen vollständigen
  Vorfahrprüfungen in Arbeit. Keine geladene unabhängige Bewegung.
- Reale Betriebsdienste weiter ausschließlich N100. Laufende Ergebnisse
  `setup/tasks/carton_reposition_20261119/`, Arbeitsstand
  `src/multi_arm_manipulation_UWA/work/carton-reposition-20261119.md`.
- Vorherige Kontakt-HOLD-Aussagen unten historisch. Nach Home keine erneute
  Greifsequenz; erst Nutzerumstellung abwarten und neue Kartonpose bestimmen.


## Kartonzyklus N100 abgeschlossen,19.11.2026,13:01

- **Aktuell beide rechten Greifer am aufliegenden Karton geschlossen. Nur HOLD.**
  RF/RR melden ACT1/STA3/FLT0/OBJ2/PRE255/FOR0/SPE16, POS204/202.
  Abschlussprüfung `continuation/grasp-started/result.json` tatsächlich PASS,
  `SUPPORTED_TWO_ARM_CONTACT_HELD`, beide Kontaktmitglieder und statischer
  Endhalt bestätigt. Gemeinsamer virtueller Objektframe/TCP-Offsets eingefroren.
  Keine unabhängigen Armziele, kein Reset/Play/Öffnen, kein Hub als automatische
  Erholung nach Kontakt. Geladene Hardwarebewegung bleibt nicht implementiert.
- Abschließender unabhängiger Lesesnapshot `final-held/observations.json`:
  alle4 Programme RUNNING/runtime2, safety1, stationär; Positionsspannen im
  kurzen Snapshot maximal0,000125rad. Aktuelles OAK-Abschlussbild unter
  `setup/tasks/carton_cycle_n100_20261119/final-{preview,jaws}.jpg` (ROSmini).
- Betriebsanbindung nun N100 `~/uwa-ur-runtime`, Domain66/LOCALHOST, GUI ROSmini
  `--n100`. Alle4 External-Control-Hosts192.168.8.5, Ports unverändert.
  Keine parallelen ROSmini-Hardwaredienste starten. Geschwindigkeitsgrenze
  unverändert0,1rad/s, Beschleunigung0,2rad/s², Modellpuffer40mm.
- Ruheprofil `hardware_carton_supported_trend.yaml` aktiv und auf neue
  ausdrückliche Nutzerfreigabe auch künftig Karton-Toolstandard. Armruhe über
  Positionstrend, weiterhin0,0005radSpanne/0,5s. Weitere fachlich begründete
  Ruhelockerung erlaubt, aktuell nicht nötig vorgenommen. Keine Freigabe zur
  Lockerung von Frische-/Kollisions-/Geschwindigkeits-/nativenUR-Stopps.
- RF-Ellenbogenkonfiguration wie vom Nutzer gewünscht korrigiert. Tatsächliche
  hohe Anfahrt und offene Einfahrt in `continuation/` beide PASS. Vor Schließen
  aktuelle OAK-Fotos12:56:19/12:59:51 visuell geprüft: Backenpaare straddeln
  kurze Wände, Tischauflage. Keine neue Wrist-Zentriermetrologie behauptet.
- **Zeit:** seit letztem Home-Start12:42:12 bis beobachtetem Griffabschluss
  13:01:16 rund19min05s, einschließlich Softwareabbruch/Korrektur/Fortsetzung.
  Ab initialem Logger11:18:30 insgesamt1h42min46s inklusive Hostwechsel,
  Nutzerwartezeiten, Konfigurationskorrektur und Fehlversuchen; erste
  Dokumentlesung vor Logger ausgeschlossen. **Kein störungsfreier Zykluswert.**
  Lokale Zeitbasis/Einzelphasen: `setup/tasks/carton_cycle_n100_20261119/`
  `timing.json` und `completion.json`; keine Host-Monotonzeiten subtrahiert.
- Beobachteter Blocker war nach Ruhekorrektur wiederholt eine Hardware-/Manager-
  RPC-Antwort >0,3s beim ROS-Schnittstellenwechsel. Keine Frischegrenze gelockert.
  Bekannte Cancel-Clients jetzt vor Timern, Arm-/Read-Schnittstellen für beide
  seriellen Arme vor Programmstart, bis Serienende erhalten; Gripper-Read-RPCs
  persistent mit jeweils neuen Geräteanfragen. Hohe Anfahrt und Einfahrt danach
  bestanden. Zeitlicher Zusammenhang belegt, keine allgemeine Middleware-
  Ursachen- oder Dauerstabilitätsgarantie. Gezielte Offlineprüfungen bestanden.
- Erster Schlussversuch vor Fingerziel wegen STOPPED-Programm verweigert.
  Nach gezielter Korrektur **expliziter** regulärer Start erst nach vollständigem
  Graphaufbau unter allen4 offenen stationären Holds; danach nurRF/RRgeschlossen.
  Neuer Opt-in `carton_gripper_phase.py close --start-ros-programs` ist nur bei
  `--execute --visual-confirmed` zulässig. Kein Sicherheitsstopp quittiert,
  keine automatische Wiederanlaufserie. Frühere Fehlerdateien bleiben erhalten.


## Aktueller Kartonzyklus auf N100,19.11.2026 (12:42)

- Nach zuvor bestätigtem Griff vom Nutzer beauftragt: lösen, hoch, Home und
  erneut greifen, Gesamtdauer messen. Lösen, Rückzug und Home auf N100 erfolgt.
  Beide rechten Arme zuletzt offen in Home, kein aktueller Kartonkontakt.
- RF-Konfiguration nach Nutzerkorrektur tatsächlich mit negativem physischen
  Ellbogen korrigiert (`rf-trend-correction/` PASS), danach für neuen Zeitlauf
  beide offen Home (`clean-home/` PASS). Ältere Kontakt-/Wartestände unten sind
  historische Nachweise und keine aktuelle Bedienanweisung.
- cycle01 scheiterte vor Einfahrt an ungeeigneter RF-Konfiguration; cycle02 vor
  Armzielen an Manager-/Herzschlagfrische. Keine vollständigen Griffzeiten.
- Dauerhafte Nutzung des Ruheprofils und fachlich begründete großzügigere
  Ruhebewertung nun ausdrücklich genehmigt. Vier Karton-Prepare/Cycle-Werkzeuge
  verwenden `hardware_carton_supported_trend.yaml` als Standard; N100 aktiv.
  Keine zusätzliche Toleranzweitung notwendig vorgenommen. Frühere Auto-Review-
  Ablehnung der dauerhaften Nutzung wurde durch diese neue Freigabe aufgelöst.
- Konkrete Laufzeitkorrektur: bekannte ROS-Cancel-Clients vor den bewaffneten
  Timern provisionieren, Aktionsclients nur für gewählte Arme. Gezielte5Tests
  bestanden. Guarddienst RR20 unter UR-Regelpriorität50, tatsächlich geprüft;
  kein Nachweis einer maximalen Reaktions-/Bremszeit. Frische-/Kollisions-/
  Geschwindigkeitsgrenzen unverändert. Start-Latch bei frischen ruhigen Holds
  über vorhandenen ausdrücklichen unbeladenen Startpfad behandeln.
- Frisches Foto12:42:12, neuer Versuch `cycle03/` mit korrigierten Referenzseeds,
  vollständiger Einfahrtplanung vor Realanfahrt und visueller Prüfung vor
  Schließen. Laufstatus vor weiteren Befehlen lesen; Erfolg noch nicht behauptet.


## CPU-/GPU-Container für Offlinearbeit, 2026-11-19

- Nutzer bevorzugt titanpc für rechenintensive GPU- und längere CPU-Läufe,
  standardmäßig in Containern. Gilt unter anderem für IK/FCL-Sweeps,
  Datensatzgenerierung, Training und Vision-Replays. Regeln in AGENTS.md,
  Bedienung über `setup/titanpc/compute.py` aus dem Workspace.
- Rootloses Apptainer im eigenen Datenordner installiert. Lyrical-CPU-Job
  mit isolierten Arbeitsordnern, Abbruch, Zeitlimit und Ergebnisabruf geprüft.
  Fertige Images für ROS Lyrical, MoveIt/OMPL/SciPy und PyTorch/CUDA 12.6.
  Synthetischer FCL-Kollisions-/Freifall sowie Matrixprodukt auf der TITAN RTX
  bestanden. Nachweise unter `setup/titanpc/results/` im Workspace.
  CPU/GPU-Jobs gehören zur Offline-Verarbeitung. Live-UR-Ausführung und
  Schutzdienste nutzen ihre eigene reale Betriebsanbindung.

## Konfigurationslehre aus dem Wiederholungszyklus,19.11.2026

- Nutzerkorrektur: RF fährt Ellenbogen-unten-Vorpose an, RR gut. Bestätigt durch
  IK/Plan: RF physischer Ellbogen positiv1,143rad statt zuvor negativ; hohe Pose
  allein gültig, Absenkbahn bei59,8% am bestehenden Nachbarpuffer verworfen.
  Keine offene Einfahrt/Fingerziele in diesem Wiederholungsversuch ausgeführt.
  Zusätzlicher nativerAll4STOP bestätigt, Arme offen/gehalten. Nicht als
  erfolgreichen oder ungestörten vollständigen Zeitlauf ausgeben.
- Übertragbare Nutzerregel: erst logische Eignung für ganze Aufgabe, danach
  Zahlen. Ellenbogen unten bei Tischgriff häufig ungünstig; Handgelenk innen
  nachteilig, falls näher am Nachbararm. Kontextbezogen, keine Universalverbote.
  Danach Gelenkreserven, Manipulierbarkeit, Nachbarabstand, Weg/Kontinuität.
  In Root-/Zell-AGENTS dauerhaft festgehalten.
- Konkrete Rezeptur verlangt für RF den zuvor erfolgreichen physischen negativen
  Ellbogenzweig, erkannt mit sin(q_elbow), invariant zu2piWinding. Kandidaten
  nach Geometriefilter mit ausgewiesenen Kennzahlen/Paretorang: relative
  Gelenkreserven, kleinster Singularwert eines mit0,5m skalierten Jacobis,
  Wrist-Nachbarabstand, Weg. Rangheuristiken sind keine Sicherheitsgrenzen.
- Gesamte Einfahrt wird künftig vor hoher Realfahrt an ausdrücklich geplantem
  zukünftigen Hochzustand geprüft; Live-Startbindung bleibt erhalten. Aktuelle
  Korrektur nurRF, RR bleibt fest. ReineZufalls-IK hatte zunächst anderen
  Schulter-/Wristzweig trotz negativemEllbogen geliefert. FrischeIK aus real
  bewährtemReferenzseed findetdirektenvollenRF-Pfad; kompletteFolgeeinfahrt
  PASS (`rf-vetted-plan/`, `corrected-entry-plan/`). Seed ist keinReplay.
- RealerRF-Korrekturstart `rf-correction/` vorControlleraktivierung abgebrochen:
  RR-Ruhewächter registriert0,0010157rad/s beiPositionsspannen<0,000089rad,
  nativeRRSTOP/neueLatch. Alle4Ressourcenholds bestätigt. RF-Zweig daher real
  noch NICHT korrigiert, keine erneuteEinfahrt/Schließung. Nichtblindresetten.
- Konkreter Kandidat `uwa_cell_motion/config/hardware_carton_supported_trend_candidate.yaml`
  bewertetArmruhe überPositionstrend und identische0,0005radPositionsspanne/0,5s
  stattjederqdSpitze. Raw0,1rad/s-/Kollisions-/Frische-/UR-Stopps unverändert;
  DefaultprofilweiterPeak.39gezielteOfflineprüfungenPASS. LokaleUnterstützung
  vorbereitet; NutzerhatAktivierungexplizitfreigegeben („Ja, Ruheprofil aktivieren“).
  AktiveFassung `hardware_carton_supported_trend.yaml` aufN100nachbestätigten
  HoldsübergezieltenGuard-Neustartübernommen. Treiber/Greiferunverändert.
  FrischgebundenerRF-Planistgültig, ganzeEinfahrtvorRealstarterneutprüfen;
  Korrekturfahrt/Griffabschlussnochzuverifizieren. DefaultprofilebleibenPeak.

## N100-Liveübergabe und gemessener Wiederholungszyklus,19.11.2026

- Expliziter Auftrag: Loslassen, hochfahren, Home, erneut greifen mit Gesamtzeit.
  Nutzer bestätigt den vorherigen realen Griff als korrekt. Karton tatsächlich
  losgelassen (beideOBJ3/POS3/PRE0/FOR0/SPE16), danach alle6eigenen ROSmini-
  Hardwaredienste kontrolliert geschlossen. N10018Pakete aktuell gebaut.
- Nutzer bestätigt Hostumstellung aller4External-Control-URCaps auf192.168.8.5,
  bisherige armweisen Ports. N100-Bringup alle4ready/Reverse verbunden, Holds
  provisioniert und gemeinsamer Guard/Greiferservice aktiv. Reale150mm-Rückzüge
  beiderRechten aufN100 bestanden; alleEndholds/Stillstände bestätigt.
- Home benötigt RF-Zwischenroute zuerst aufrichten, dann Basis drehen wegen
  bestehendem40mm-Nachbarpuffer. Erster Home-Grenzfall: Encoder1,26µrad unter
  nominaler-360°-Modellgrenze; sichereHolds, kein belegterKartonkontakt. Ziel an
  Winkelgrenze1mrad nachinnen gesetzt; gemesseneGrenzprüfung unverändert.
  Danach beide rechtenHomepositionen tatsächlich bestanden (`home-interior/`).
- GUI bleibtROSmini; Startmenüinstaller mit`--n100` durchgeführt. Nie gleichzeitig
  lokaleROSmini-Hardwaretreiber starten. NativeUR-Adressen/Basisprofile unverändert.
- **Gemessener Zyklus ab tatsächlichemHome läuft jetzt aufN100**: neueAufnahme,
  Bildregistrierung/Planung, hoheAnfahrt, offeneEinfahrt, Agent-Bildprüfung,
  Schließen. NochkeinneuerKontaktabschluss behauptet.0,1rad/s/0,2rad/s²,
  40mmMargin und bestehendeFrische-/Stoppschwellen unverändert.
- N100-Daten `~/uwa-ur-runtime/setup/tasks/carton_cycle_n100_20261119/`,
  lokaleZeitbasis `setup/tasks/carton_cycle_n100_20261119/timing.json`.
  EinmaligeVorbereitung/Hostwechsel/Home von Zykluszeit trennen; unterschiedliche
  Host-Monotonzeiten nicht voneinander subtrahieren. Details im Arbeitsstand.

## N100 als möglicher UR-Steuerrechner, 2026-11-19

- Anschlussauftrag19.11.: N100 vorbereiten und für RT-Kernel neu starten.
  Ubuntu `7.0.0-43-realtime` gebootet, `PREEMPT_RT=y`, N100 per Ethernet
  erreichbar, SSH-/Benutzermanagergrenzen 99/unlimited geprüft. Isolierter
  Lyrical-Overlay `~/uwa-ur-runtime`, GUI-Option `--n100` auf ROSmini.
  Der Desktop-Eintrag steht bis zur späteren Betriebsübergabe auf lokal.
- N100-Lasttest mit USB-OAK und Archivleselast abgeschlossen. Vier
  Mock-JointState-Quellen, passende Kinematiken sowie Guard, Supervisor und
  Watchdog im Monitorbetrieb bestätigt. Gelenk-, kartesische und
  CollisionHold-Controller auf allen vier Mock-Managern inaktiv konfiguriert.
  FIFO-Priorität 50 im Managerlog. Kurzstichprobe 30 s mit 179 µs maximaler
  Scheduler-Aufwecklatenz, ca. 1,64 GiB Cgroup-RAM und 2,20 logischen
  CPU-Kernen. Mockzyklus 100 Hz. N100-Runtime und Prüfnachweise in
  `setup/n100/ur-runtime/`. Realer Wechsel des External-Control-Hosts und
  Leistungs-/Stoppnachweis mit realen Regelkreisen stehen aus.
- Abschluss der Vorbereitung: 18 Pakete inklusive `mur_control` für den
  bestehenden kartesischen Controller und `match_cooperative_handling`
  für Aufgabenmathematik. Drei aktuelle Karton-/Greifer-CLI-Imports und
  16 vorhandene Softwaretests auf dem N100 bestanden. Lokale 29
  Power-/Bringup-Tests und simulierter N100-GUI-Ablauf bestanden. Der
  gebaute Quellstand ist vor dem echten Umschalten mit paralleler
  Zellarbeit abzugleichen.
- Nutzer ergänzt, dass die Roboter bei weiterlaufenden Treibern aus waren.
  Das ist der beobachtete Kontext für die FD-Diagnose. Die genaue Ursache
  des Socket-Wachstums und die Dauerstabilität bei ausgeschalteten URs
  bleiben offen.
- Nutzer erwägt, die Echtzeitausführung hinter **UWA Robot Power** vom
  simulations- und planungsbelasteten ROSmini auf den N100 zu verlagern.
  Präzisierung19.11.: GUI auf ROSmini, betriebsbezogene Berechnung und
  Überwachung auf dem N100.
  SSH-Bestandsaufnahme bestätigt vier Kerne, 5.954 MiB verfügbaren RAM im
  Leerlauf, Lyrical und kabelgebundenes Zellnetz. Die Bestandsaufnahme wurde
  vor der oben dokumentierten Echtzeitinstallation durchgeführt.
- Auf ROSmini erreichten alle vier alten `ros2_control_node` jeweils 1.024
  offene Dateideskriptoren am Softlimit, davon je 997 Sockets. Die Journale
  meldeten fortlaufend `Too many open files` an den Script-Sender-Ports.
  Die vier laufenden Dienste beanspruchten in Fehlerstichproben etwa
  6,2–7,2 logische CPU-Kerne und 5,6 GiB Prozessspeicher (PSS), vieles im
  Launch-Prozess. Ursache der Socket-Ansammlung offen. Nach unabhängigem
  Neustart durch den parallel bearbeiteten Karton-Bringup zeigten alle
  vier Manager je 52 FDs. Die Dienste lagen bei zusammen 1,8 GiB PSS und
  0,82 logischen CPU-Kernen in einer kurzen Vergleichsmessung. Der
  Wächterdienst war inaktiv. Dauerbetrieb und Last auf dem N100 offen.
- Empfehlung zur Prüfung: GUI, Simulation und Offlineplanung auf ROSmini.
  UR-Treiber, Live-Guard, Supervisor, Watchdog und Ausführung auf einem
  Host (N100), weil die heutige Frischeprüfung gemeinsame monotone
  Zeitstempel voraussetzt. Eine getrennte Runtime braucht kontrollierte
  Auftrags-/Statuswege und pro UR genau einen aktiven Treiberhost. Die
  Anwenderpräferenz für die GUI ist bestätigt. Der Umschaltablauf steht
  in der [N100-Anleitung](../../setup/n100/ur-runtime/README.md).
  [Messwerte, Quellen und Prüfplan](work/n100-ur-runtime-20261119.md).

## Neuer Kartonzyklus mit N100 beauftragt,19.11.2026

- Nutzer bestätigt ausdrücklich: Karton korrekt gegriffen. Beauftragt Loslassen auf Tisch, Hochfahren, Home und vollständige Wiederholung mit Gesamtzeitmessung; UR-Steuerung diesmal auf N100. Dies erlaubt gezieltes Lösen und anschließende unbeladene Betriebsübergabe, keine geladene unabhängige Armfahrt.
- Karton inzwischen tatsächlich losgelassen: beide OBJ3/POS3/PRE0/FOR0/SPE16. Nach kurzzeitigem Ruhefehler bei Öffnung aktuelle frische Holds/Stillstände bestätigt. Alle6eigenen Hardwaredienste auf ROSmini kontrolliert beendet. N100-RT-Runtime aktuell gebaut (18Pakete/21,1s), echte Dienste dort noch inaktiv. External-Control-Hostwechsel aller4am Pendant auf192.168.8.5 ist beimNutzer angefragt und abzuwarten. Aktiver Stand `work/carton-cycle-n100-20261119.md`, Zeit-/Ausführungsdaten `setup/tasks/carton_cycle_n100_20261119/`.

## Aktueller realer Kartongriff,19.11.2026: Kontakt gehalten, RR-Programm gestoppt

- **Beide rechten Greifer geschlossen am aufliegenden Karton. Keine unabhängigen
  Armfahrten, kein Reset/Play/Öffnen oder Dienstwechsel als automatische Erholung.**
  Nur HOLD; kein Hub/Transport. Direkter Nutzerauftrag zur Fortsetzung erledigte
  hohe Anfahrt, Aktivierung/Öffnen, offene Einfahrt und tatsächlichen Greifschluss.
- Aktuelle OAK-Registrierung über sichtbares festes rechtes Board; Basisbindungen
  unverändert. Hohe Anfahrt `setup/tasks/carton_grasp_20261119/high-20hz/` und
  offene Einfahrt `entry/` tatsächlich PASS, beide Endholds/Stillstände bestätigt,
  keine Guardstopps in diesen Fahrten. Unverändert0,1rad/s/0,2rad/s²/40mmMargin.
- OAK-Einfahrbild10:50:29 visuell geprüft, beide Backenpaare straddeln die kurzen
  Wände. Minimales Schließen FOR0/SPE16: beide ACT1/STA3/FLT0/OBJ2/PRE255,
  RF-POS204/RR-POS202. Beide ROS-Greiferaktionen erfolgreich, keine Öffnung danach.
- **Abschlussprüfung des Gesamtablaufs abgebrochen**, nicht als vollständigen
  qualifizierten Grifflauf ausgeben: während Schließen meldet RR Ruhewächter
  länger als1s keine Ruhe. Spitzen bis0,005016rad/s bei Positionsspannen nur
  etwa0,00031rad überschreiten bestehende0,001rad/s-Ruheschwelle. Supervisor
  stoppt RR-Programm10:51:24; anschließend Guard-Latch PROGRAM INTERRUPTED.
  Ursache ist hier Reaktionsbewegung/Stillstandskriterium, kein nachgewiesener
  Kollisions-/Kraftüberschreitungsfall. Grenzen nicht verändert, kein Neustart.
- Nachfolgend rein lesend bestätigt: frische alle4Pakete, alle4Ressourcenholds
  und native Ruhe. Native Safety NORMAL an allen4; RR STOPPED, übrige PLAYING.
  `grasp/result.json` bleibt negativer Originalnachweis. Kontaktmitglieder und
  gemeinsamer virtueller Objektframe/feste Objekt→TCP-Offsets separat unter
  `grasp/final-held-state.json`; allowed_next_action HOLD, loaded_motion_enabled
  false. Kein Tragfähigkeits-/Backenkraftnachweis. Foto10:52:24 und Nahbild
  `setup/tasks/carton_grasp_20261119/grasp-jaws.jpg` zeigen beide Wandgriffe,
  Karton auf Tisch, keine offensichtliche Beschädigung.
- Startprobleme gezielt behandelt: vier alte Treiber bei1024FD erschöpft,
  nach nativenSTOPs ersetzt; übersehener globaler Hochrunner-Reset auf armweisen
  Endpoint korrigiert. Bestehende Zustandsweitergabe passend zur nativen20Hz-Rate
  auf20Hz gestellt, Frische-/Stopplimits unverändert. FOR vor SPE einzeln
  rückbestätigt; aktive Bootstellung nur für Öffnen hoch zugelassen. ALIGN/ENTRY
  proArm in einer Action, identische Einzelzeitgesetze. Kontaktmitglieder auch
  bei abschließendem Native-Readinessfehler vorab erhalten. Eng begrenzte lokale
  Prüfungen bestanden, Details `work/carton-contact-grasp-20261118.md`.
- Vor weiterer echter Bewegung zuerst den gehaltenen Kontaktzustand behandeln;
  der tragende gekoppelte Hardwareexecutor bleibt separate offene Arbeit.


## Historischer Sitzungsabschluss18.11.: Software für19.11. vorbereitet

- Expliziter Nutzerstopp18.11.: heute keine weiteren Fahr-/Greifziele, Software
  offline fertigstellen, realer Versuch morgen. Eigene Hardware-Schutz-/Greifer-
  Dienste kontrolliert geschlossen; abschließender nativer STOP über vorhandene
  Dienst-Nachbehandlung. Keine automatische Wiederaufnahme am nächsten Tag.
- Zuletzt tatsächlich erreichte Armstellungen: beide hohen Vorpositionen aus
  `carton_grasp_20261118_go_real01`. Die spätere direkte Board-Korrektur wurde
  NICHT ausgeführt. Keine Fingeraktivierung/Schließung, kein Kontakt/Hub heute.
  Das ist der aktuelle Stand; ältere Inspektionsposenbeschreibungen sind historisch.
- Software jetzt mit armweisem Supervisor-Reset: nur gewähltes Mitglied freigeben,
  andere Haltezustände behalten, keine globale Freigabe plus erneutes Stoppen.
  Guard-Geometrie/Frische/UR-Sicherheit unverändert. Parallel-Resets werden
  serialisiert, neue STOPs gewinnen. RPC-Clients bleiben über den Ablauf erhalten.
  Diese Umstellung ist offline geprüft, real noch zu bestätigen.
- Wiederverwendbare Schritte: kanonisches Geometrierezept, aktuelle Board-/Bild-
  Registrierung, hohe Anfahrt, offene Einfahrt, minimale statische Greiferphase.
  Details [kurzer normaler Ablauf](docs/carton_supported_grasp.md). Keine separate
  Diagnose-/Simulationskampagne als normaler Start. Schließen endet bei HOLD,
  mit eingefrorenem gemeinsamem virtuellen Objektframe; kein tragender Hubmaster.
- Historischer Simulationspfad `carton_preload_home_20261116_02/case00` inzwischen
  nicht mehr vorhanden. Neue Rezeptdaten werden aus dem versionierten Asset
  erzeugt; alte Hashbindungen nicht fälschen/reparieren. Vollständiger neuer
  Offline-Stand unter `setup/tasks/carton_grasp_20261118_offline_finish/`.
  Dessen `READY.json` trennt Softwarebereitschaft von noch ausstehender realer
  Bestätigung; Aufnahme/Hochstart sind historische bzw. geplante Daten.
- Um17:56 breite ROS-Signalbeendigung einschließlich Treibern/Simulation/Schutz-
  und Greiferknoten beobachtet; Benutzer erläutert Beenden von UWA Robot Power.
  Reines Fensterschließen soll laut Code Treiber nicht beenden, deshalb keine
  abschließende kausale Zuordnung. Normale Anbindung wurde zwischendurch wieder
  hergestellt, danach auf jüngsten Nutzerstopp beendet. VorlagekeineFahrfreigabe.


> Ergebnisarchiv18.11.: ältere abgeschlossene Workspace-Versuche und Logs
> liegen jetzt auf dem N100, Originalpfade im Archiv erhalten. Einstieg
> **UWA Archiv (N100)** / http://127.0.0.1:8767; gezielt zurückholen mit
> `python3 ~/UWA_ws/setup/archive_n100/archive.py restore GRUPPEN-ID`.
> Heutige Versuche, Kalibrierung, Forschung und Quellprojekte bleiben lokal.
> Ältere Ergebnisordner enthalten ARCHIV_AUF_N100.txt mit dem konkreten Befehl.
> Prüfstand und Ablage im Workspace-HANDOVER; keine Hardwaredienste verändert.

## Kartongriff: Wrist-Abgleich und aktuelle Neuberechnung, 2026-11-18

- Nutzer beauftragt Greifen und fragt nach Wrist-Zentrierung. Vorherige
  Vor-Greifpose war OAK/FK-geprüft, nicht bereits durch Wristkameras zentriert.
  Jetzt native Bilder beider rechten Kameras und zusätzliche RF-Blickfahrten
  bei unverändert0,1rad/s ausgeführt; keine Fingerbefehle/kein Kontakt/kein Hub.
- Wrist-Abgleich verworfen: Bilder und berechnete Kamerabewegung passen nicht
  ausreichend zusammen. Die erste Zuordnung zu einer Kartonbewegung war zu
  voreilig. Nutzer bestätigt anschließend: zwischen den Wristaufnahmen blieb
  der Karton stehen. Die109mm/7,71° sind eine Differenz zweier Objektschätzungen,
  kein nachgewiesener physischer Versatz. Ursache des früheren Paars offen.
  Basisbindungen bleiben unverändert fest übernommen; alte Greifziele nicht
  ohne erneuten Abgleich weiterverwenden.
- Aktuell RF außerhalb in gedrehter Inspektionspose, RR am alten Vorgriff;
  beide nicht als aktuell mittig bestätigt ausgeben. Alle4 Arme gehalten
  und stationär bestätigt, Guard CLEAR/keine Faults, Watchdog nicht getrippt;
  rechte Finger inaktiv/offen ACT0/POS3/PRE0. RR-Programm STOPPED nach bestehendem
  Stillstandswächter16:28; keine automatische Wiederaufnahme am Ende.
- Kein mittiger Griff bestätigt, Greifen nicht versucht. Aktueller Index
  `setup/tasks/carton_grasp_20261118_scene03/result.json`, neue reine
  Objektbeobachtung ebenfalls in scene03. Details und
  Callback-/Fehlerhold-Korrekturen: [Arbeitsstand](work/carton-contact-grasp-20261118.md).
  Fortsetzung braucht einen unveränderten Szenenstand, neue Zielbindung und
  offenen Einfahrkorridor; nach Kontakt keine unabhängigen Armbewegungen.
- Neuberechnung nach Nutzerkorrektur: OAK16:50:12/Fokus107,27Inlier/3,051px;
  gegenüber16:40-Schätzung0,506mm/0,438° Differenz. Wrist bei identischer Pose
  wiederholt:1277Bildmatches,95%-Bildverschiebung0,985px. Interne Wiederholbarkeit,
  keine absolute Genauigkeitsfreigabe. Neue Kontur visuell zum Wrist passend.
- Beide150mm-Vor-Greifziele neu berechnet, aktuelle Istpose gültig, vollständige
  Geometrieprüfung und Offline-Replay PASS bei unverändert0,1rad/s. Vor jedem
  neuen Fahrziel jedoch Abbruch: vorhandener Schutzdienst stoppt16:57:12 wegen
  Hardware-/Manager-Statusalter0,26–0,32s. Keine Arm-/Fingerziele und kein Reset
  gesendet. Reguläres RR-Play unmittelbar zuvor erfolgte unter geprüften Holds;
  danach keine erneuten Startschleifen. Frische-/Stoppgrenzen unverändert.
  `carton_grasp_20261118_recalc_plan01`, `recalc_checked01`, `recalc_real01`.

## Marker und Tischaufnahme in Gazebo/RViz, 2026-11-19

- Nutzer bestätigt den CAD-Entwurf und möchte Stift, Adapter und
  Aufnahme in der aktuellen Szene. Zwei visuelle DAE-Assets aus
  dem akzeptierten STEP plus angenähertem Markerprofil. Anker
  `left_table_top` bei (−0,270; −0,400) m, vorläufig. TF-Ursprung
  `asset/cos_marker_docked` an der nominellen Stiftspitze.
- Standardzelle lädt beide Assets über `scene_objects`. Die getrennte
  Haus-/Bohrwelt `uwa_grasp_lab` lädt nur die beiden Marker-Props
  zusätzlich. In der bereits laufenden Welt sind sie seit 17:44 AWST
  sichtbar. RViz für `/uwa_grasp_house` läuft als eigene View-Sitzung
  `uwa-grasp-house-marker-view.service`; originale Gazebo-PID blieb.
- Drei Lyrical-Pakete gebaut. Live-Szenenabfrage bestätigt beide
  Meshes und gleiche Posen in Gazebo und RViz, einen RViz-Abonnenten
  und vorhandenen physischen Karton. Fünf Asset-Tests bestanden.
  Der ältere Test zur Position des Kartons scheitert auch mit dem
  Ausgangslayout (32,55 statt maximal 30 mm X-Abweichung).
- Visual-only. Stiftaufnahme und Rückgabe als Kontakte, physische
  Kollisionsmodelle und Marker-TCP bleiben spätere Arbeit. Details und
  Startbefehl in [der Marker-Anleitung](hardware/marker_tool/README.md).

## COS-Marker und Robotiq-Tischaufnahme, 2026-11-19

- Nutzermaße näherungsweise Ø20 mm bei 10 mm und Ø19 mm bei 35 mm
  vom hinteren Ende, 125 mm Länge offen. Konstruktion in
  [hardware/marker_tool](hardware/marker_tool/README.md).
- Zweiteiliger, mit vier M3-Schrauben geklemmter Stiftadapter mit
  34 mm Greifweite und Führungsleisten für die angenommenen
  22-mm-Standardpads. Asymmetrischer Zapfen mit Trichterablage,
  vertikale Entnahme, nominal 5 mm Luft unter der Spitze.
- Baugruppe als STEP, drei druckorientierte und geschlossen geprüfte
  STLs, Schnittbild und parametrischer Export abgelegt. Nominelle
  Einsteckgeometrie und Sperre gegen 180° verdrehte Ablage im CAD
  geprüft. Reale Passung, Drehfestigkeit, Greifhöhe und Spitze/TCP
  stehen aus. Keine Roboteraktion ausgeführt.

## Linke USB-Übersichtskamera und Rohrhalter, 2026-11-19

- USB-OAK gegenüber der Ethernet-OAK4. N100-SDK-Artefakt bestätigt
  OAK-D Pro AF (RVC2), Geräte-ID 18443010314F3B1300 mit Autofokus.
- Nutzer nutzt das vorhandene 1.200-mm-Edelstahlrohr Ø19 mm und vier
  vorhandene Tischlöcher. Tischfuß zuerst konstruieren, mit langer
  Führung und sparsamem Materialeinsatz. Ersetzt den Vorentwurf vom
  18.11. mit 40-mm-Vierkantmast und Schraubklemmen am Tisch.
- STEP-Referenz `Rohrhalter.step` gelesen. 98 × 98 mm Raster, vier
  Ø9-mm-Löcher und Rohrachse 67,45 mm vor der nahen Schraubenreihe
  in Konstruktion übernommen. Neuer Fuß mit 145 mm Führungsbauhöhe,
  141 mm Einstecktiefe, zwei M5-Klemmzonen im Schraubenabstand 113 mm
  und drei Rippen. CAD-Volumen 203,5 statt 289,8 cm³ (30 % weniger).
- [CAD, STL, Passprobe und Vorschau](hardware/oak_d_pro_left/README.md).
  STEP wieder eingelesen, Solid gültig. Beide STLs geschlossen,
  konsistent orientiert, jeweils ein Volumenkörper. Kantendistanz
  der nahen Bohrungsreihe für vollständige Auflage mindestens 87 mm.
  Tischmaße, Passung, Druck und Steifigkeit am realen Tisch stehen
  aus. Kamerakopf und Raumprüfung folgen nach dem Fuß.

## Schritt 4: variierte Lehrerbahnen für die hinteren Arme, 2026-11-18

- Fünf modellgeprüfte Starts auf zwei archivierten Startankern, 40 Referenzen.
  12 freie Kontrollen und sieben FCL-Kollisionsfälle mit gültigen Enden im
  Screening. Rest: sieben IK-Abbrüche, zehn ungültige Enden und vier reine
  Prüfgrenzenverletzungen im Mittelteil ohne FCL-Kollision.
- Sieben ausgewählte Fälle durch den Lehrer und die Modellprüfung geführt.
  Sechs bestehen: drei korrigierte Referenzen (Unterarm/Unterarm, Karton gegen
  je einen linken und rechten Oberarm) und drei freie Kontrollen. Bei den
  korrigierten Fällen verbleiben 4,0–5,2 cm Nettozielversatz hinter dem letzten
  Referenzkontakt. Vier verschiedene Starts und sechs unterschiedliche Ziele.
- 47.648 Zustände im zeitlichen Raster bis 5 ms geprüft, 0,1 rad/s Obergrenze.
  Maximal 0,09838 rad/s bei dichter Auswertung, mindestens 20,89 mm Armhüllabstand
  und 27,63 mm bewegte Armhülle/Tisch. Zeitspanne 8,53–68,76 s im Modell.
  Die bekannte statische Frontarm/Tisch-Hüllenüberschneidung ist in jedem
  Bericht gesondert erhalten. Vollständige FCL-Prüfung aller vier Arme.
- Ein Selbstkollisionsfall zwischen rechtem hinterem Handgelenk und eigenem
  Unterarm wird vom Ersatzmodell des Optimierers verfehlt und von der finalen
  FCL-Prüfung verworfen. Ergebnis und Kontaktzeugen erhalten, kein Export.
- Sechs NPZ-Dateien, 600 Übergänge im bestehenden 52/6-Schema. Exportaudit
  prüft Verkettung, Endzustand und Rekonstruktion der Aktionen. Splitstatus
  unassigned und Gruppierung nach Startanker. Kleiner Pilot mit festem
  Modell, zwei Ankern und gezielter Auswahl, keine Generalisierungsstatistik.
- Artefakte `setup/research/rear-pair-screen-20261117/step4-pilot/`, Galerie
  `run01/viewer.html`, Prüfberichte `run01/export-audit.json` und Einzelberichte.
  28 gezielte Tests und sechs Browserprüfungen bestanden. Reproduktion
  `tools/generate_rear_pair_pilot.py` mit `screening.json` und `selection.json`.

## Gemeinsame Zeitplanung der hinteren Arme geprüft, 2026-11-18

- Schritt 3 abgeschlossen für die Seitenvariante mit festem Endziel. Die
  Archivkorrektur aus Schritt 2 wurde mit 201 IK-Stützstellen als gemeinsame
  12-Gelenk-Trajektorie mit C3-Zeitgesetz und 0,1 rad/s geplante Obergrenze
  zeitparametriert. Modellzeit 76,734 s. Analytische Schranke 0,093639 rad/s,
  dicht gesampelte Spitze 0,090910 rad/s. Beschleunigungs-/Ruckgrenzen
  0,4 rad/s² und 2 rad/s³ geprüft, alle Ableitungen an den Endpunkten null.
- 15.348 Modellzustände am zeitparametrierten Interpolanten in Abständen
  von höchstens 5 ms geprüft. Null FCL-Kollisionen, alle sechs Armpaare,
  geparkte Arme, Gelenkgrenzen und feste Greiftransformationen. Minimum
  20,92 mm zwischen Armhüllen, 27,64 mm zwischen bewegter Armhülle und Tisch,
  3,53 mm Karton/Umgebung im Boxmodell. Endpose stimmt mit Schritt 2 überein,
  maximale numerische Griffabweichung rund 0,021 µm und 0,127 µrad.
- `goal-continuation/timed/` bewahrt den ersten Hüllenbefund. Der geparkte
  vordere linke Oberarm überschneidet sich im Kugelhüllenmodell bereits am
  Start um 38,84 mm mit der Tischplatte. Originale Kollisionsnetze vorhanden,
  komplette FCL-Szene meldet keinen Kontakt. Zusatzschranke für Arm/Tisch
  analog Episodenlehrer für beide fahrenden Arme. Frontarmwert dauerhaft
  als statischer Befund im Bericht. FCL und Arm/Arm-Prüfung für alle vier.
- Ergebnis und zeitgesteuerter Viewer unter `setup/research/`
  `rear-pair-screen-20261117/goal-continuation/timed-02/`. Reproduktion
  `tools/time_rear_pair_teacher.py SCREENING_ORDNER GEOMETRY_RESULT_JSON
  --output-dir NEUER_ORDNER`. 22 gezielte Tests bestanden. Modellnachweis
  mit zeitlichem Prüfraster, ohne Kontaktphysik oder gemessene Stoppgrenzen.

## Reale Karton-Vor-Greifpose mit beiden rechten URs erreicht,2026-11-18

- Neuer expliziter Auftrag: Karton erkennen und RF/RR in Vor-Greifpose fahren.
  Aktuelles OAK-Foto/Fokus107, neuer Kamerafit und fest übernommene Basis-
  anbindungen genutzt. Texturregistrierung im agentgewählten Kartonausschnitt
 25Inlier/2,729px; Gesamtbildversuche ohne belastbare Pose bleiben erhalten.
- Beide realen Ziele mit offenen, inaktiven Greifern erreicht,150mm über dem
  geplanten Kontakt; kein Absenken/Greifen/Hub. Unverändertes Profil0,1rad/s,
  amax0,2/geometric_only. NominalRF33,0/RR103,9s. Native Spitzen0,103282/
 0,103748rad/s innerhalb bestehender5%-Monitortoleranz. Bahnrestfehler höchstens
 0,000104rad. BeideEndholds/Latches/Guardruhe und unabhängigeRuhefensterPASS,
  keineWächterstopps während der ausgeführtenArmwege, keinNativeSTOP-Fallback.
- Endcheckalle4RUNNING/NORMAL/runtime2/stationär,alle4Ressourcenholds/Software-
  latches, GuardCLEAR/keineFaults, Watchdognichtgetrippt. GreiferAPIMONITOR ONLY;
  keineAktivierung/Greiferziele, Backenweiteroffen. Abschlussfoto visuell geprüft.
- IndexmitQuellen/Foto `setup/tasks/carton_pregrasp_20261118_completed/`.
  RF-Teil aus real03 und separater RR-Lauf zusammengeführt; ursprüngliche
  Vorprüf-/Übergangsfehlerberichte erhalten. TechnischeDetails undKorrekturen
  work/carton-pregrasp-20261118.md. AktuellePose ist neuerStart, altePläne nicht
  blindwiederholen. TragendergekoppelterHardwareexecutor bleibtseparatoffen.

## Hinteres Armpaar mit Ziel hinter der Konfliktregion, 2026-11-18

- Nutzer fragt nach der scheinbar anderen Endpose. Archivierter Viewer öffnete
  bei 50 %, während der Korrektur. Bei 100 % stimmen beide Kartonposen exakt
  überein. Der ursprüngliche Fall hat dieselbe Start- und Zielpose.
- Neuer Offlinefall mit 8 cm Versatz in Welt-X, 1 cm Hub und +10° um Welt-Z
  als eigenem Endziel. Start und Ziel im Modell geprüft. Drei vorwärts
  versetzte Vorschläge hatten ungültige Enden und sind in `screening.json`
  erhalten. Die Seitenvariante kollidiert nominal an 20 von 61 Wegpunkten
  zwischen 35 und 66,7 %. Danach verbleiben rund 6,5 cm Kartonweg der Korrektur.
- Bestehender Lehrer mit vorheriger Korrektur als Startwert. 1.201 korrigierte
  Wegpunkte ohne FCL-Kollision, minimal 20,92 mm Armhüllabstand und 3,58 mm
  Karton/Umgebung-Trennung nach Boxmodell. Identische Zielpose und gleicher
  Endzweig der Gelenke im Vergleich zur Referenz (max. 4,16e-10 rad Differenz).
- `setup/research/rear-pair-screen-20261117/goal-continuation/checked/` enthält
  Resultat, Vergleichsviewer, Zielbild und neun erfolgreiche Browserprüfungen.
  Öffnet bei 0 %, `Show goal` zeigt 100 %, `Jump to contact` den Referenzkonflikt.
  `tools/plan_rear_pair_teacher.py --task` lädt Ziele im bestehenden Aufgabenformat.
  Die zeitparametrierte Prüfung steht im Abschnitt zu Schritt 3 oben.

## Hinteres Armpaar mit korrigierter Kartonbahn, 2026-11-18

- Schritt 2 abgeschlossen. Der bestehende `TwoArmTeacher` optimierte dieselbe
  +60°-Referenz aus `rear_y0.55` mit festen Griffen und Endposen. Lokale 6D-Suche
  mit 121 Stützstellen, 13 Iterationen und 41,5 s Rechenzeit. Modell und
  Startkonfiguration sind an den Archivfall gebunden.
- Korrigierte Geometrie an 1.201 gleichmäßig verteilten Wegpunkten geprüft.
  Null FCL-Kollisionen, kleinster Armhüllabstand 20,92 mm bei 20 mm Vorgabe,
  kleinste Karton/Umgebung-Trennung nach Boxmodell 4,00 mm. Gelenkgrenzen,
  Griffschluss und beide Endzustände bestanden. Fremdarme stehen in der Szene.
- Maximale Abweichung von der Referenz 45,0 mm Translation und 33,44°
  Orientierung. Der Karton kippt zusätzlich, während die Z-Drehung in der
  verwendeten Eulerzerlegung bis 61,2° erreicht. Start und Ziel identisch.
- `setup/research/rear-pair-screen-20261117/teacher-step2/checked/` enthält
  `result.json`, `viewer.html`, `correction.png` und elf Browserprüfungen.
  Beide Varianten bei gleichem Wegfortschritt umschaltbar. Geometrische
  Modellbahn. Gemeinsames Zeitgesetz und dessen Prüfung folgen in Schritt 3.

## Hinteres Armpaar im 3D-Viewer, 2026-11-18

- Schritt 1 abgeschlossen. `tools/preview_rear_pair_collision.py` erzeugt die
  Ansicht aus dem archivierten Griffstart `rear_y0.55` und der +60°-Referenz
  um Welt-Z mit 5 cm Zwischenhub. Das gebundene historische Modell sowie Pose
  und Gelenkzustand des gespeicherten Kontaktzeugen wurden erneut geprüft.
- `setup/research/rear-pair-screen-20261117/contact-preview/viewer.html` öffnet
  bei 50 % Wegfortschritt. Wiedergabe, Schieber, Zoom und Rotation funktionieren.
  Die rote Spur umfasst 17 von 61 Prüfpunkten bei 36,7 bis 63,3 % Fortschritt.
  In allen 17 meldet FCL die beiden hinteren Unterarme. Rot hebt diese Körper
  hervor. Das weiße Kreuz zeigt die aus Kugelhüllen geschätzte Kontaktregion.
- Nachweise im selben Ordner. `preview-check.json`, 17 native Kontaktlogs,
  `contact.png` und zehn erfolgreiche Browserprüfungen einschließlich der
  bestehenden Lehreransicht. Die Anzeige läuft als Offline-Referenz über
  Wegfortschritt und liefert den archivierten Ausgangspunkt für Schritt 2 oben.

## Basisanbindungen fest übernommen, 2026-11-18

- Ausdrückliche Nutzerentscheidung: bisher keine Probleme beobachtet;
  vorhandene Basisanbindungen aller vier URs einschließlich left_front als
  fest übernehmen. Kalibrierproblem-/Diagnosehinweise dazu aus aktiven
  Berichten/Anzeigen/Übergaben entfernen; erst bei konkret auftretenden
  Problemen erneut untersuchen. Dauerhaft in beiden AGENTS.md festgehalten.
- Neues Standardprofil hardware_20261118_base_fixed_v1: vier SHA-gebundene
  gemessene T_base_board, Statusfixed_user_accepted und Originalfreigabe.
  LF aus vorhandenem HD-Boardfit gleichberechtigt übernommen. Aktuelles
  OAK-Export enthält alle vier Basistransformationen unter transforms, keine
  separate diagnostic_transforms-Gruppe mehr. Ursprungsberichte erhalten.
- Gemeinsame Beschreibung und RViz-Overlay laden feste Boardframes unabhängig
  von optischer Hand-Auge-Anwendung. Basisanbindungen sind keine Aufgabe der
  laufenden OAK-Optik-/Posenprüfung mehr. Details applied_calibrations.md.
- Zwei betroffene Pakete gebaut;16gezielte Profil-/Consumer-/Overlaytests
  bestanden. Ein vorhandener Overlaytest erwartete noch90cmTischbreite;
  auf bereits verwendete99,1cm korrigiert, Modellwerte unverändert. Aktives
  installiertes Profil und alle vier OAK-Exporttransformationen geprüft,
  bestehende Kinematik-/Optikartefakte identisch. Zusätzlich11Foto-Kontext-Tests
  bestanden (gesamt27). Nachweis
  setup/calibration/oak_capture_proposal_20261118/base-bindings-adoption-check.json.

## Übergabe und protokollierter Agententest vorbereitet, 2026-11-18

- Nutzer bestätigt Boxzeichnungsvarianten und wünscht einen anderen Agenten
  zur Reproduktion/Erweiterung testen. Ziel: weitere Rotation und dritter
  Kreis auf der abgewandten Längswand. Für den Test ausdrücklich als
  Objektfläche y_min konkretisiert, y_max/z_min und25mmRadius erhalten.
- Kurze Einstiegskarte docs/agent_trials/BOX_DRAWING_HANDOFF.md, kopierfertiger
  PROMPT_AWAY_FACE.md und TRACE_PROTOCOL.md. Dateien/Artefakte/Umgebung,
  zweiflächenfeste Erweiterungsstellen, Modellgrenzen und Abnahme benannt.
  Aktuelle0,1rad/s vonhistorischem0,35rad/s-Modellprofil unterschieden;
  keine eigenmächtige zusätzliche Temposenkung oder alte Ausnahme erfunden.
- Neuer Standardlib-Logger tools/agent_trial.py: init/start/end/run/note/
  finish/summary, Git-Ausgangsstand, monotone Schritt-/Befehlszeiten,
  argv/CWD/Exitcode und vollständige stdout/stderr. Fehlversuche bleiben
  auch nach Reparatur im Bericht. Parallele Befehlsintervalle nur einmal
  zählen; Restzeit explizit Lesen/Bearbeiten/Chat/Warten, keine Denkzeit.
- Shelllogging erfasst keine fremden API-/Browser-/Editor-/Chatausgaben
  automatisch; Protokoll verlangt dafür Notizen/Artefakte bzw. sichtbaren
  Client-Export. Tokenwerte/Modellname nur bei belegten Angaben. Entwicklung
  und robotische Episoden bleiben getrennt, kein nachträglich erfundener
  vollständiger Trace des bisherigen Entwicklungsagenten.
- Logger mit sieben gezielten Tests einschließlich Timeout/Startfehler, Parallelität,
  Rohtext, Literalargv und Unterbrechung geprüft; CLI-Smoke mit achtAufrufen
  und absichtlich erhaltenem Exit3 erfolgreich. Artefakte
  setup/agent_trials/logger_smoke_20261118/, ausdrücklich kein Fremdagentenlauf.
- DritteZeichenfläche nicht selbst implementiert oder neuerAgent gestartet;
  das bleibt der vorbereitete Testauftrag. Keine Robot-/Kamera-/Dienstaktion.
  Eigener Arbeitsstandwork/box-drawing-agent-handoff.md.
## OAK-Kalibrierung fortgesetzt, 2026-11-18

- Neuer Berechnungsstand nach Nutzeraufnahmen:14vollständigeFünfkamera-Sätze,
 70nativeFotos;1vorAufnahmeabgebrochenenVersuchausgeschlossen. Offline neu alle
  dreiBoards getrennt erkannt; alle14OAK-Mobileansichten verwendbar. Vorabfolge
  ergibt10Fit-/4Prüfstellungen. AlleBild-SHAs/Format/Fokusbestätigt, keineFahrt.
  Vorläufiger gemeinsamer OAK-Posekandidat gespeichert unter
  setup/calibration/oak_capture_proposal_20261118/calibration_candidate_v1/:
  oak_pose_candidate.json/.yaml, Ergebnis.txt und calibration_quality.png.
- Fokus107: Factory-D/Hauptpunkt/Aspekt plus neu gefittete Brennweitenskalierung
  0,978326, fx5832,357/fy5831,934px. DisjunktePrüfeckenMedian1,242/Max1,375px.
  FesterTischboardfitalleinPrüfunglinks~0,3/rechts~0,9px. Gemeinsamer robuster
  Fit aller fünf Kameras/Boards konvergiert; Wristvorhersage auf4zurückgehaltenen
  mobilenAnsichten2,32–9,22nativeOAK-Pixel. Keine Millimetergenauigkeit bestätigt.
  Nach erster Prüfdatensichtung explorativ verfeinert; neuer unabhängiger
  Abschlusstest weiterhin offen. Kein stilles Auswechseln des globalen Profils.
- Alle vier bestehenden Basisanker sind seit Nutzerentscheidung18.11. fest
  übernommen und im OAK-Kandidat gleichberechtigt enthalten.
  Mobile Bildabdeckung nurx25–58%/y27–79%; weitere schräge seitliche Randansichten
  bei107 würden die Optikprüfung ergänzen. GUI undFokus107 bleiben bestehen.
  Weitere Details/Nachweise work/oak-recalibration-20261117.md.

- Neuester Fokusauftrag: beide festen Boards vorne/hinten gemeinsam scharf.
  Vier native Vergleichsfotos mit unveränderter Montage:100/107/112/116.
  Fokus107 bei beiden Referenzen visuell und per kontrastnormalisierter
  Schärfemetrik bester getesteter Wert, beide24/24Ecken. Andere Werte
  links/rechts100=9/18,112=19/24,116=0/21. Readbacks korrekt. Nachweise
  setup/calibration/oak_capture_proposal_20261118/focus_both_static/.
  Eigene GUI geordnet geschlossen und als Fünfkameraansicht wieder gestartet;
  acquisition_active.yaml hält107 für Vorschau/Fotos, Wristwerte unverändert.
  Keine Intrinsics/Extrinsics angewandt; alte Bilder/Importzähler erhalten.

- Neueste Präzisierung: Ziel ist OAK-Pose gegenüber Robotern/Welt. Die zuvor
  geöffnete OAK-only-GUI ist ein Intrinsics-Hilfsschritt bei Fokus107, keine
  Extrinsicsmessung eines frei bewegten Bretts. Zur Fünfkamera-Aufnahme zurück:
  mobile gemeinsame Sicht OAK+mindestens eine Wristkamera, feste unveränderte
  Tischboards als zusätzliche Basisanker; kein Zwang zur gemeinsamen Sicht
  aller fünf. Absoluter Weltanker bleibt bisher provisorisch. Eigene
  Einzelkamera-GUI geordnet beendet; Fünfkamera-GUI uwa-oak-pose-view-20261118
  gestartet und visuell geprüft: alle fünf Feeds frisch, OAK/RF mobiles Brett
  je24/24. Tischboards ebenfalls erkannt, Referenzidentität unter jedem Bild.
  Knopf CAPTURE ALL FIVE. Sitzung five_camera_pose/20261118_140254_3e66161f
  unter setup/calibration/oak_capture_proposal_20261118; vier bisherige Sätze
  mit20Fotos in Zählern übernommen. Keine neue Aufnahme automatisch gestartet,
  keine Roboterkommandos oder neue Kalibrierung angewandt.

- Vorheriger Stand: Nutzer möchte weitere Aufnahmen über passendeGUI starten.
  EigenesOAK-Intrinsicsfenster geöffnet: Mobile38mm/IDs75–91, Fokus107,
  native8000×6000, nurOAK-Aufnahme. Dienstuwa-oak-intrinsics-20261118,
  Sitzungszeiger setup/calibration/oak_capture_proposal_20261118/intrinsics-session.txt.
  VierOriginalbilderübernommen:2mobilebrauchbar24/24,2Reviewmit2/9Ecken.
  Ziel12unterschiedlicheBoardstellungen;8Fit/4Validierungvorabzugeordnet,
  naheDublettenzusammenhalten. GUILive24/24/fehlerfreiundScreenshotgeprüft.
  Capture-All-1istderaktuelleKnopf, speichertnurOAK. KeineArmfahrt oder
  Geschwindigkeitsänderung; keineKalibrierungangewandt.

- Nutzer meldet wieder aktivierte Antriebe und beauftragt Fortsetzung.
  Lesend nach Hochlauf alle4RUNNING/NORMAL, keine erneuten Armfahrten oder
  Programmaktionen.0,1rad/s und keine eigenmächtige Reduktion gelten weiter.
- Beide festen Tischboards laut Nutzer unverändert relativ zu den Basen.
  Kamera-GUI auf `both` statt Mobile-Muster gestellt, linke Referenzen jetzt
  erkannt. Erster nativer Fünfkamera-Satzgespeichert/all_usable/StillstandPASS:
  LF20/LR19/RF24/RR24/OAK24Ecken. GUI1kompletter/1verwendbarerSatz/5Fotos.
  Sitzung20261118_133517_0068a219/set_133728_183314 im Aufnahmeordner.
- NativeOAKbeideTischboards24/24. FactoryK/DvonFokus116nurinitialverwendet:
  disjunkteEckenlinks0,283px/rechts1,402px(Kriterium1px). Fokus107weiter
  intrinsischunvalidiert; T_base_oak-KandidatenbeiderRearankerundrelative
  Basenmatrixnichtangewandt. first-oak-reference-check.json.
- NächsterSchrittmobilegeneigteBoardansichtenfürIntrinsics107;12Startansichten
  mit8Fit/4vorabdefinierterValidierunggeplant. ErsteBrettplatzierungamrechten
  Tisch30–45°angelehntvomBedienerangefordert. KeineweiterenArmfahrtenoder
  Geschwindigkeitsreduktion. work/oak-recalibration-20261117.md.

## Dauerhafte Geschwindigkeitsvorgabe, 2026-11-18

- Nach der erfolgreichen Umstellung auf0,1rad/s verlangt der Nutzer ausdrücklich,
  diese Entscheidung dauerhaft festzuhalten: **keine weiteren Reduktionen der
  Geschwindigkeit ohne seine ausdrückliche Aufforderung**.
- Vorgabe in Workspace- und Projekt-AGENTS.md hinterlegt. Keine stillen
  Rückfälle auf alte Langsamprofile, niedrigere Kommandogrenzen oder gezielte
  Zeitstreckung. Bei einem Konflikt mit bestehenden Bedingungen konkret melden,
  statt eigenmächtig langsamer zu fahren. Sicherheitsstopps bleiben bestehen;
  keine höhere Geschwindigkeitsfreigabe erfunden.
- In diesem Arbeitsgang ausschließlich Dokumentation geändert; aktuelles
  Aufnahmeprofil mit0,1rad/s unverändert.

## Bedienerwunsch: dynamische Reserve aus, 0,1rad/s, 2026-11-18

- WährendOAK-AnfahrtfordertNutzerausdrücklichEntfernungdeszusätzlichen
  Stoppschutzesund0,1rad/s. AlterLR-Laufgezieltangehalten, Holds/Stillstand
  bestätigtundalterExecbeendet; LFistbereitsamAufnahmeziel, LRteilweise.
- Opt-in`stopping_reserve_policy: geometric_only`implementiert: zusätzliche
  dynamischeDistanzbudgets0, PaarleasebestehendeHeartbeatfrist. Modell/FCL/
 40mmgeometrischerPuffer, Daten-/Heartbeat-/Speedprüfung,Holds,nativeUR-
  Sicherheitbleiben. Policy/hashgebunden; DefaultandererProfileenforce.
 33gezielteTestsPASS. Nativensicherheitsstoppsnichtquittiert.
- Aufnahmeprofilalle24GelenkeKommando/Monitor0,1rad/s,amax0,2; vorhandene5%-
  Monitortoleranzbleibt. KeinequalifizierteBremswegabsicherungindiesemModus.
  NeuenModusnachbestätigtemHaltaktiviert; StatusOFF(GEOMETRICONLY)/CLEAR.
  LR/RR/RF damit erfolgreich, kein Wächterstopp. Zusammen mit LF sind alle4
  Aufnahmeziele erreicht; gemeinsame native Endabweichung maximal0,000295rad
  (0,0169°) beim letzten Fahrtende. Nominelle Restdauern25,55/56,80/29,53s.
  Fünfkamera-GUI geöffnet, alle5Livefeeds frisch/fehlerfrei; keine Fotos/Fit/
  Profilübernahme. Spätere Abfrage alle4POWER_OFF/STOPPED/NORMAL, Ursache/
  Akteur unbekannt. Eigene Folge enthält kein Power-off, kein automatisches
  Wiedereinschalten. PowerOff-qd teils stale und kleine Posenänderungen;
  nicht als aktuellen ROSReady-/Ruhebeleg ausgeben. Quelle
  setup/calibration/oak_capture_proposal_20261118/geometric-only/.

## OAK-Anfahrt: schneller Vorschlag zur Bedienerbewertung, 2026-11-18

- Nutzer möchte wenige Prüfungen und zuerst einen plausiblen Pfad inRViz/
  Animationbewerten. EinmaligengeometrischenVorschlagumgesetzt, keineganze
  Test-/BenchmarkfolgevorerneuterVorschau. RealeAusführungweiterseparat.
- Aktuelllesendalle4POWER_OFF/NORMAL/STOPPED mitq=0. Daherletztenvaliden
  Messstart17.11.verwendet, imFensterexplizithistorischmarkiert. Keine
  aktuelleArmstellungausNulltelemetrieabgeleitet, keineAntriebsaktion.
- VorschlagLF→LR→RR→RF, direkteGelenksegmentezuAufnahmestellungenmitkürzester
  erlaubter2π-Entsprechung. EineFCL-/statischeHüllenprüfung266Stützstellen
  ≤0,035rad/alle6Paare/40mm, vollständigeÖffnungshüllen. Berechnung2,122s.
  NominaleVorschlagszeit170,09sbei0,1rad/s/0,2rad/s², keineRealprofilfreigabe.
- EigenesRVizundenglischesPlay/Pause/Zeitschieber/Endposenfenster,
  Domain74/LOCALHOST, nurVorschau-JointStates/TF/Marker.
  Dienstuwa-capture-proposal-20261118, Quelletools/preview_capture_approach.py,
  Daten setup/calibration/oak_capture_proposal_20261118/.
  Boardressourcenuntereigenemmodel/-Verzeichnispersistentgehalten.
  NutzerbeauftragtanschließendAusführung. Alle4nochPOWER_OFF/NORMAL,
  Treiber/Schutzinaktiv; gebündeltePower/Brake/ROS-/Profilfreigabeinkl
  LFq6=.1am18.11.ausdrücklicherhalten, Bereichfrei bestätigt.
  PendantbestätigunganLR/RF/RRvomBedienererhalten; danachalle4ROSReady.
  FrischerStartmax0,358°vomVorschlagentfernt. LF-Direktwegfrischgeprüft,
  q6=.1-Profilaktiviert, aktuellerStillstands-/HoldnachweisundResetPASS.
  LFfährttatsächlichmitWächterCLEAR/keinenFaults; andere3stationär.
  EigenesExecuwa-capture-motion-20261118-01; nachAbschlussweiterLR→RR→RF,
  keineerneuteidentischeallgemeineFreigabeabfrage.

## Gazebo-Dreiarm-Kontaktlauf, 2026-11-18

- Nutzer hat Ausführung des neu geplanten Ablaufs in Gazebo bestätigt.
  Opt-in `drawing_recipe` koppelt RF/RR/LF über einen gemeinsamen
  18-Gelenk-Controller und Stopp. Frisch bestätigter Kontaktgriff bindet
  beide festen Offsets. RF im alternativen IK-Zweig und LR in geprüfter Parkpose.
- Run04: vier Kontakte bestätigt, 17 Phasen aus dem frischen Griff vor
  dem Hub geprüft. Gazebo hob den Karton bis zu 132,38 mm an. Der Stopp
  erfolgte vor Zeichnung wegen passiver RF-Finger bis 0,500 rad/s bei
  0,2 rad/s Grenze. Drei Arm-Holds bestätigt, vier Kontakte erhalten,
  Box ohne Tischauflage. Kein Lösen oder automatischer Reset. Eigene Welt
  bleibt im Halt, Hauptwelt läuft. 40 fokussierte Quelltests bestanden.
- Run04 enthält nun auch OAK-Kamerabilder vor dem Abheben und bei
  132,38 mm Hub im bestätigten Halt. Nachträglich in Gazebo/Ogre2 aus
  der aufgezeichneten Telemetrie gerendert. Oben in `run04/review.html`
  verlinkt und als nachträgliche Renderings gekennzeichnet.
- Hubwiedergabe aus 432 aufgezeichneten Gazebo-Gelenk-/Kartonzuständen
  in `run04/lift-replay.html`, auch in `run04/review.html` verlinkt.
  Zeitachse in Simulationssekunden, 132,38 mm Spitze und bestätigter Halt
  sichtbar. Wiedergabe der Telemetrie als 3D-Ansicht ohne Kameravideo.
- Protokolle und Review im Workspace unter
  `setup/tasks/box_drawing_gazebo_live_20261118_01/`.

## Greifhöhe im HTML-Piloten und in der Kontaktgeometrie, 2026-11-19

- Nutzer weist auf den unterschiedlichen Abstand zwischen Greifern und
  Karton in HTML, Gazebo und realer Zelle hin. Im ursprünglichen
  Boxzeichnungs-Viewer sieht man Kollisionshüllen und einen angenommenen
  starren Griff mit nominell offenen Fingern. Die Kontakt-Neuplanung
  verwendet die profilgebundene Gazebo-Geometrie und die beim Vier-Pad-Griff
  aus Werkzeug-FK und Bildpose bestimmten Objekt→Tool0-Transforms.
- Abgleich im kartonfesten Zentrumframe mit gleicher nominaler Oberkante.
  `present_surface_20261118/reference02/result.json` nutzt einen virtuellen
  TCP 158,5 mm entlang Tool0+Z. Nach Rückrechnung auf Tool0 beträgt die
  Höhe über der nominalen Oberkante rechts vorne/hinten je 143,5 mm.
  In `box_drawing_gazebo_replan_20261118_01/result.json` sind es 91,4/88,5 mm.
  Das entspricht 52,1/55,0 mm tieferer Werkzeugpose. Die Zahlen beschreiben
  die gespeicherten Modellreferenzen, keinen gemessenen Padspalt.
- Das nominale Rezept für den gestützten Realgriff
  (`carton_grasp_20261118_offline_finish/recipe-v2/contacts.json`) zielt
  auf 95,8/93,0 mm über dem Kartonboden. Die nominellen TCP-Ziele des
  HTML-Piloten liegen bei 148,3 mm. Die Wristaufnahmen zeigen den
  verstärkten mehrlagigen Rand; realer Padabstand und Mittigkeit sind durch
  diese Zahlen und Bilder nicht bestätigt. Siehe
  [Kontaktaufnahme und Bildabgleich](work/carton-contact-grasp-20261118.md).
- Auf Nutzerwunsch als dauerhafte Übergaberegel in AGENTS.md und
  docs/box_drawing_pilot.md verankert. Gemeinsamer Kartonframe, Werkzeug-
  und Padbezug, Fingerstellung und Wandgeometrie vor dem Übertragen prüfen.
  Die fallbezogene Werkzeughöhendifferenz bleibt ein Vergleichsbefund.

## Zweiter Agententest mit Gemini vorbereitet, 2026-11-19

- Nutzer möchte die Toolchain mit einem frischen Agenten eines anderen
  Anbieters testen. Aufgabe: derselbe Drei-Flächen-Ablauf im Dateimodell
  mit 22 mm Radius und Prüfung der Einordnung von HTML-Greifgeometrie.
  Die vorhandene Flächen-CLI ist Bestandteil des Tests. Der erste
  Agententest erforderte dagegen eine Erweiterung des Modellcodes.
- Antigravity CLI 1.5.12 lokal unter `setup/agent_tools/antigravity/agy`
  aus Googles Linux-Release abgelegt, Manifest-SHA512 und Versionsaufruf
  geprüft. Anmeldung über das Nutzerkonto steht aus. Die Bedienanleitung
  unterscheidet Konto-Kontingent und API-Projekt sowie CLI/VS-Code.
- [Start und Auswertung](docs/agent_trials/GEMINI_TRIAL_02.md),
  [Testprompt](docs/agent_trials/PROMPT_GEMINI_TRIAL_02.md) und
  [Agentenübergabe](docs/agent_trials/GEMINI_HANDOFF.md).
  Starter `tools/start_gemini_trial.py` legt Prompt, Eingangssnapshots und
  sichtbaren Terminalmitschnitt mit Zeitmarken neben dem Aufgaben-Trace ab.
- Vorabprüfung ohne Gemini: eigener Offline-Drei-Flächen-Lauf mit 22 mm
  bestand den separaten FK-/Zeitaudit, Modellzeit 395,080 s,
  Spitzengeschwindigkeit 0,096583 rad/s. Starter in lokalem Terminaltest
  mit simuliertem Client geprüft, einschließlich Exitcode-Erhalt,
  sichtbarer Ausgabe, Timing und IDE-Vorbereitung. Der anschließende
  Gemini-Lauf ist im folgenden Abschnitt ausgewertet.

## Gemini-Lauf geprüft und Nikolaushaus vorbereitet, 2026-11-19

- Auf Nutzerwunsch bleibt der Starter erhalten und akzeptiert
  `--mode=auto` für den direkten Start im Antigravity-Automatikmodus.
  Der gewünschte Modus wird pro Lauf in `observer.json` gespeichert.
  Ohne Option entscheidet der Client wie bisher. Der aktive Modus ist
  in der CLI-Statuszeile sichtbar.

- `box_gemini_20261119/session-50t0fawy` enthält einen neuen Offline-Lauf
  mit Gemini 4 Neon (High). Drei Kreise à 22 mm, gemeinsamer Rückweg und
  Spitzengeschwindigkeit 0,096583 rad/s bestätigt. Erneuter Audit auf
  temporärer Kopie bytegleich. Phasen und Programm entsprechen exakt der
  lokalen Vorabprüfung derselben Eingabe. Modellausgabe und Rohprotokoll
  zeigen eine Neuberechnung mit dem vorhandenen Planer. Kein Hinweis auf
  Kopieren alter Laufartefakte im sichtbaren Trace. Der bekannte
  Gegenwand-Umweg ist als Suchstart im Toolkit enthalten.
- 82,086 s ausgeführter Planungsbefehl, 344,544 s Entwicklungszeit ab
  Logger-Init und 395,080 s Modellzeit. Nicht direkt mit dem ersten
  Agententest zu vergleichen, der neuen Modellcode verlangte.
  [Auswertung und Quellen](docs/agent_trials/REVIEW_GEMINI_02.md).
- Nutzer möchte das Haus vom Nikolaus statt des Unterseitenkreises.
  Der dritte Test lässt beide 22-mm-Seitenkreise stehen und verlangt einen
  durchgängigen Acht-Kanten-Zug auf `z_min`. `start_gemini_trial.py --case
  nikolaus` bereitet einen separaten Checkout ohne Git-Remote und
  einen frischen Prompt vor. Historische Resultate sind kein
  Testkontext. Modellquelle und Offline-Umgebung bleiben geteilt.
- Der Hauptrepo-Prüfer `tools/check_nikolaus_trial.py` prüft die Form
  unabhängig anhand der Gelenkinterpolanten und FK. Synthetischer
  Referenzzug bestanden, Testabweichungen und früheren Drei-Kreis-Lauf
  abgelehnt. Normale Offline-CLI in der Quellkopie mit Seitenkreis und
  Audit geprüft. Der neue Agent implementiert das Haus.
  [Einstieg für den Bediener](docs/agent_trials/NIKOLAUS_TRIAL_03.md).

## Nikolaushaus-Agententest ausgewertet, 2026-11-19

- Nutzer bittet um Analyse der Gemini-Bearbeitung und meldet auffällige
  Endbewegung des Zeichenarms. Hauptrepo-Audit der acht Hauskanten und
  beider Seitenkreise PASS; Gemini-Audit bytegleich wiederholt,
  archivierter Drei-Kreis-Lauf besteht den erweiterten Prüfer.
- `return_from_y_min` und `return_box` spielen die gemeinsamen Hinwege
  rückwärts. Letzte Phase 374,52–406,41 s Modellzeit, LF-Handgelenke
  1/3 drehen −172,83°/+130,64°. Nach dem Haus führt ein separater
  40-mm-Standoff-Weg von B nach A zurück. Sieben direkte Parkvarianten
  mit unverändertem Halterpfad im Offline-Screen am virtuellen
  Stift/Karton-Konflikt gescheitert. Kein alternativer Rückweg freigegeben.
- Entwicklungszeit 19:25 min, Hauptplanung als Befehl 71,52 s,
  Anpassung und Prüfung zusammen rund 12:44 min Stufenwandzeit.
  Vorschlag: Datenvertrag für Zeichenpfade, freier Zeichenarm-Rückweg
  ab tatsächlicher Ausstiegspose und wiederverwendbare Audit-/Timingschritte.
  [Auswertung und Messbelege](docs/agent_trials/REVIEW_NIKOLAUS_03.md).

## Werkstückbezogene Werkzeugbahnen und freier Arbeitsarm-Rückweg, 2026-11-19

- Nutzer definiert Zeichnen als reversiblen Stellvertreter. Planer soll
  Kleben/Farbauftrag, Sägen/spanende Bearbeitung und Fensterschaum entlang
  werkstückbezogener Bahnen unterstützen. Axialer Vorschub für Bohren
  und Schrauben vorgesehen. Bestätigt einen neu geplanten Rückweg.
- `workpiece_paths.py` liefert Flächenframes, freie Punktfolgen und
  `AxialFeed` mit Vorpose, Oberfläche, Zieltiefe und Rückzug, auch auf
  geneigten Flächen. Axial ist ein geometrischer Referenzbaustein.
  Reale Prozesskopplung, erlaubter Eingriffsbereich, Werkzeugsensorik
  und Eingriffsfreigabe sind getrennt zu integrieren.
- Boxpilot akzeptiert `--tool-paths DATEI` mit Linienzügen je Fläche.
  Daten und Programmhash sind an die Episode gebunden. FK-Audit prüft
  tatsächliche Kanten, Richtung und feste Haltung. Test: 8 Hauskanten
  auf `z_min`, beide 22-mm-Kreise und unabhängiger Nikolaus-Audit PASS.
  Unabhängiger Test einer offenen Dreikantenbahn auf `y_max` und
  archivierter Drei-Kreis-Audit ebenfalls PASS.
- `--replan-return` behält beide Halterpfade und wechselt den freien
  Arbeitsarm innerhalb der ersten Rückbewegung gleitend zur Parkpose.
  Beim Haus sind die Halter-Stützstellen bitgleich zur Gemini-Referenz.
  Die letzte Phase verkürzt sich 31,89→22,15 s, Armspanne dort null
  (früher 172,83°/130,64° an Handgelenken 1/3). Modellgesamtzeit
  406,41→396,67 s, 19.864 Prüfpunkte bei höchstens 20 ms, minimale
  Hüllenlücke 50,20 mm, Geschwindigkeit 0,09767 rad/s. Ursprüngliche
  Rückfahrt als vollständig geprüfter Fallback am Zweiflächenlauf PASS.
- 15 gezielte Tests und sieben Browserchecks bestanden. Bedienung
  [Werkstückbahnen](docs/workpiece_paths.md). Dateimodell, Viewer,
  Vergleiche und Referenzdaten in `setup/tasks/workpiece_paths_20261119/`.
  Keine Hardwareaktionen. Der offene Linienzug hält vorerst den
  Standoff-Wiederanschluss ein, den der bestehende Fallback voraussetzt.

## Gemini-Test für doppeltes Haus, Lochkreis und festen Stift, 2026-11-19

- Nutzer meldet ausbleibendes Auto-Approve. CLI-Log vom Start 12:43:58
  bestätigt `--mode=auto` erkannt, dann Rückfall auf Standardmodus,
  da Antigravity 1.5.12 bei
  `kernel.apparmor_restrict_unprivileged_userns=1` seine Sandbox
  deaktiviert. Im laufenden Terminal später `accept-edits`; Shellbefehle
  fragen weiter. Separater Bubblewrap-Nur-Lese-Test direkt auf dem Host
  besteht. Ursache ist die Antigravity-Erkennung bei aktiver AppArmor-
  Richtlinie. Starter warnt jetzt in diesem bekannten Fall und protokolliert
  die Warnung. Praktischer Weg im laufenden Test: `accept-edits` und
  gezielte Freigaben für diese Unterhaltung. In diesem ersten Lauf blieb
  die Host-Richtlinie bei `1`.

- Nutzer wünscht geometrisch doppeltes Nikolaushaus auf der Unterseite,
  sechs gleichmäßig verteilte Bohrstellen auf Ø150 mm und möglichst den
  letzten Kreis durch Kartonbewegung an festem Stift. Testinterpretation:
  vollständiger Kreis mit 60° Abstand um die Mitte der Hausabmessungen,
  Modell-Zustellung 3 mm und Vorabstand 15 mm. Alle Punkte passen auf
  den Karton; Lochmittelpunkte mindestens 15 mm von der Hausspur entfernt.
- `tools/start_gemini_trial.py --case house-drill --mode=auto` nutzt
  die separate Quellkopie. Starter und Kontext-Hashes im CLI-Probelauf
  geprüft. Prompt, Übergabe und Geometrie stehen unter docs/agent_trials/.
  Der vierte Versuch testet Axialintegration und Rollenwechsel beim
  Kreis im Werkstückframe. Gemini soll die Lösung selbst erstellen.
- Doppeltes Haus im isolierten Checkout mit dem vorhandenen Bahnplaner
  einzeln geprüft: acht Kanten und Rückkehr PASS, 0,097281 rad/s Peak.
  129 Punkte der Gegenwand-Kreisreferenz mit festem Werkzeug und
  bewegtem Karton bestanden den punktweisen Modellcheck; Anfahrt,
  Rückzug und zeitparametrierter Gesamtweg dort noch nicht belegt.
- Gemini-Lauf `setup/agent_trials/house_drill_gemini_20261119/session-bodzvnj2`
  abgeschlossen. Der Prüfer `check_house_drill_trial.py` aus dem Hauptrepo
  besteht mit den abgegebenen Gelenkinterpolanten. Alle acht Hauskanten,
  sechs Zustellzyklen, beide Kreise, feste Haltergriffe, Rückkehr und
  unveränderter Stiftarm beim Kreis auf der Gegenwand sind im Modell belegt.
  503,81 s Modellzeit in 46 Phasen, Spitzenwert 0,098483 rad/s. Abgabe und
  Quelldiff liegen im Trial. Der erste Python-Probeaufruf überschrieb
  `PYTHONPATH`; korrigierter Aufruf hängt den bestehenden Wert an.
- Terminalstart bis `trial_end`: 35:30 min. 16 Bash-Freigaben belegen im
  CLI-Log 16:31 min Wartezeit. Die verbleibenden 18:59 min enthalten
  Lesen, Editieren, Chat und Rechenbefehle. Der Modelllauf brauchte 98,19 s.
  Beim einfacheren Nikolaushaus waren es 20:01 min, davon 7:42 min
  Freigabewartezeit. Aufgaben und Umfang unterscheiden sich.
- Nutzer wünscht vorab freigegebene Routine. `house-drill` im CLI-Starter
  bereitet Logger und `trial/artifacts` vor. Sitzungsregeln und lokaler
  Antigravity-Hook decken wörtliche Logbefehle, eine Dateiliste und
  `mkdir` in `trial/artifacts` ab. Ask-/Deny-Einträge übernommen,
  globale Allow-Einträge durch die Sitzungsregeln ersetzt. Tests gegen
  den Starter, 15 Positiv-/Negativfälle und Laden in CLI 1.5.12 bestanden.
  `antigravity.log` liegt direkt in der Sitzung.
- Nutzer-Wiederholung `setup/agent_trials/house_drill_gemini_20261119/session-x6z3i06d`
  mit gleicher JSON-Spezifikation, aktualisiertem Checkout und Host-Wert `0`.
  Kurzzeitiger CLI-Fallback beim Initialisieren, ab 14:23:59 tatsächlich
  `auto`. Einmalige Workspace-Vertrauensabfrage, kein manuell bestätigter
  Toolaufruf im Log. Der Hook wurde geladen. Das Transkript enthält
  23 von 29 Shell-Aufrufen mit angefordertem `BypassSandbox`. Das belegt
  weder eine komplett in der Sandbox ausgeführte Sitzung noch den isolierten
  Effekt des Hooks. Den Host-Wert `0` nach der Wiederholung beobachtet.
- Wiederholung bis erste vollständige Modellsequenz 16:28 min (vorher
  25:25 min), bis Abgabe 28:21 min (vorher 35:30 min). Gegenüber den
  18:59 min des ersten Laufs ohne Freigabewartezeit bleiben 9:22 min mehr
  Wandzeit. Zweite Implementierungsrunde plus zweiter Planlauf rund 4:32 min
  in ihren benannten Stufen, Modellrechenzeiten 93,72 und 92,83 s; alter Lauf
  einmal 98,19 s. Unterschiedliche Abläufe und zwei gleichzeitig geänderte
  Freigabebedingungen verhindern eine isolierte Effizienzschätzung.
- Hauptrepo-Prüfer besteht für `run01` und finale Abgabe `run02`. `run02`
  hat 45 Phasen, 498,13 s Modellzeit, 0,097973 rad/s Peak, acht Hauskanten,
  sechs axiale Zustellungen, zwei Kreise und unveränderten Stiftarm beim
  Gegenwandkreis. `run01` kommt ohne geplanten früheren Rückweg auf 519,87 s.
  [Testanleitung](docs/agent_trials/HOUSE_DRILL_TRIAL_04.md).

- Nutzer beauftragt einen Vergleich mit dem schnellen eigenständigen
  Modell. `agy models` bestätigt `gemini-4-hydrogen-high` für das Konto.
  Vergleich `session-4eu3n4pm`, `--case house-drill --mode=auto --model
  gemini-4-hydrogen-high`, gleiche Aufgaben-JSON und unveränderte relevante
  Planer-/Prüferquellen gegenüber dem Neon-Wiederholungslauf bei neuerem
  Startcommit (`0d45594`). Hydrogen-`High` und Modus `auto` im Log
  bestätigt. Beide Läufe ohne manuelle Befehlsfreigabe.
- Hydrogen bis erste vollständige Modellbahn 13:12,4 min und bis `trial_end`
  22:13,5 min. Neon-Vergleich 16:28,0 min und 28:21,1 min. Einzelbeobachtung
  mit einem Modellplanlauf bei Hydrogen (101,79 s) und zwei bei Neon
  (93,72 s und 92,83 s). Hauptrepo-Audit besteht für Hydrogen `run01`,
  503,81 s Modellzeit bei 46 Phasen und 0,098483 rad/s Peak. Ergebnis liegt
  unter `setup/agent_trials/house_drill_gemini_20261119/session-4eu3n4pm`.
- Hydrogen exportierte per `git diff` nur den ungestagten Test. Vollständiger
  Patch nach dem Lauf unter `review/changes-full.patch` ergänzt, sechs
  Dateien gegen den festgehaltenen Startcommit in frischer Kopie eingespielt
  und bytegleich verglichen. Originalabgabe und ihre Zeitmessung erhalten.
  Vollständiger Export gegen Startcommit im Trace-Protokoll dokumentiert.
- Auf Nutzerfrage den Hydrogen-Trace und die sichtbaren Antigravity-Aktionen
  ausgewertet. Stufenwandzeiten in Sekunden: Orientierung 207,06, Anpassung
  356,97, Planung 170,10, Prüfung 304,60, Abgabe 145,66, außerhalb benannter
  Stufen 149,21 inklusive Start und Stufenwechseln. Gewrappte Befehle
  zusammen 131,03 s, davon Planer 101,79 s. Vom Ende des Planers bis zur
  Abgabe vergingen 541,15 s. Nachweis: `trial/events.jsonl`,
  `trial/summary.md`, `antigravity.log` und sichtbare Tool-Trace-Aktionen.
- Die Vereinigung der vom CLI gemeldeten Intervalle automatischer
  Toolprüfungen umfasst 167,54 s, bereits in den Wandzeiten enthalten.
  Keine manuelle Befehlsfreigabe. Zeit zwischen Logereignissen enthält
  Modellantworten, Dateiwerkzeuge, Toolprüfung und Protokollübergänge.
  Einen exakten Anteil interner Modellrechnung weisen die Daten nicht aus.
- Für einen späteren Beschleunigungsvergleich vorgeschlagen: Prüfungen,
  Viewer-JSON, Hashes und Patch in einen deterministischen Abgabeschritt
  bündeln. Dem Agenten kurze Einstiegsliste mit Aufrufen und API geben.
  Für wiederkehrende Aufgaben geprüfte, allgemeine Pfadbausteine für
  Oberfläche, axiale Zustellung und festes Werkzeug wiederverwenden.
  Erstmals neue Funktionen zu erstellen bleibt eine eigene Messaufgabe.
- Auf Nutzerfrage den Umfang der 213 Tests abgeglichen. Hydrogen rief
  das gesamte Python-Testpaket `uwa_cell_tasks` auf, 15,57 s Befehlswandzeit.
  Darin sind unter anderem Greifer-/Karton-Hardwarelogik, Registrierung,
  Freigabelogik und Logger enthalten. Die konkreten Bahnnachweise stammen
  aus den separaten Audits. Nachträgliche Stichprobe im finalen Hydrogen-
  Checkout: 16 Tests für Pfadbausteine, Box-CLI und Episoden bestanden
  in 1,66 s Prozesswandzeit. Vorschlag für isolierte Entwicklung: Audits
  für jede Bahn und gezielte Regression bei Bausteinänderung; ganze Suite
  bei gemeinsamer Integration. Der Ein-Aufruf-Abschluss folgt unten.
- Detailmessung auf Nutzerfrage für die 304,60 s der Hydrogen-Phase `verify`:
  28,58 s aktive geloggte Befehle, 43,27 s vom CLI protokollierte automatische
  Toolprüfungen ohne Überlappung mit diesen Befehlsintervallen, 232,75 s
  übrige Wandzeit. Beide Audits waren nach 76,29 s fertig (10,07 s Befehlszeit).
  Danach folgten Archivieren und Lesen der Ergebnisse, Viewer-Inspektion
  samt Retry, Suite und ergänzter Unit-Test, Hashprüfung und Stufenende.
  Auch zwischen dem 66-ms-Hashbefehl und dem Stufenende vergingen 28,29 s.
- Nutzerauftrag19.11. umgesetzt: `finish_house_drill_trial.py SITZUNG RUN`
  führt beide im Hauptrepo bereitgestellten Audits aus, prüft Viewer-JSON,
  Phasen, kanonischen Ergebnis-Hash und Arbeitsstand, führt bei Python-
  Änderungen fokussierte vorhandene Tests aus und exportiert Bericht,
  Logs und vollständigen Patch gegen den Startcommit. Der Starter setzt
  den Aufruf in den Prompt ein. Eigene oder geänderte Tests und Audits
  sind für Gemini ausgeschlossen und werden in der gebündelten Abgabe
  gemeldet. Bei PASS schließt der Aufruf den Trial im Logger ab.
- Viewer-Fehler war ein verlorenes `$`-Escape in Geminis Inline-Regex. Der
  Prüfbefehl liest das eingebettete JSON mit dem JSON-Decoder, ohne JavaScript
  auszuführen. Drei frühere Viewer bestanden, falsch gebundener Viewer wurde
  abgelehnt. Vollständiger Offline-Probelauf in separater Kopie: 13,70 s für
  Prüfung und Abgabe, 15 vorhandene Tests bestanden, `trial_end=complete`.
  Export in frischer Kopie angewandt und fünf Dateien einschließlich
  gestagter, ungestagter und neuer Datei bytegleich geprüft.
- Nutzer-Folgetest mit gebündelter Prüfung und Abgabe: Antigravity CLI
  1.5.12, Hydrogen High, Modus `auto`, Sitzung `session-04xvx0m0` unter
  `setup/agent_trials/house_drill_gemini_20261119/`. Separater Checkout auf
  `0d45594` wie bei `session-4eu3n4pm`, gleicher Hash der Aufgaben-JSON,
  Modellquelle und Modell-Signatur. Die gemeinsam genutzte Datei
  `configuration.py` hatte einen neueren Quellhash.
- Terminalstart bis erste Modellbahn 799,37 s (alt 792,39 s), bis Abgabe
  899,95 s (alt 1333,54 s). Erste Bahn bis dokumentierter Abschluss
  100,58 s (alt 541,15 s). Beide Läufe enthalten je eine vollständige
  Modellplanung. Neuer Einzelaufruf für Prüfung und Abgabe 14,97 s,
  vollständiger alter `verify`- und `deliver`-Stufenaufwand 450,26 s.
  Einmalige manuelle Bestätigung für Logger-Stufenende in `orient`,
  50,00 s Freigabewartezeit im neuen Lauf, 0 s im alten. Die Gesamtzeit
  enthält diese Wartezeit. Unterschiedliche Agentenaktionen bleiben
  Teil des Einzelvergleichs.
- Zwei Audits, Viewer-Abgleich und 15 vorhandene Regressionstests PASS.
  Beide Bahnen haben 46 Phasen und rund 503,81 s Modellzeit. Keine
  Test-/Audit-Änderungen in der neuen Agentenabgabe. Patch umfasst exakt
  die vier geänderten Dateien gegen den Startcommit. Report unter
  `trial/verification/run01-0b91c207/report.md` der neuen Sitzung.
- Nutzerentscheidung19.11.: diesen Ablauf als Standard für neue Aufgaben
  hinterlegt. `start_gemini_trial.py` startet alle unterstützten Fälle in
  isolierten Quellkopien und wählt Hydrogen High. `--model` überschreibt
  die Vorgabe. Der Prompt enthält `finish_gemini_trial.py`, das zu Fall und
  Spezifikation passende Audits nutzt, Viewer, Git-Patch und Bericht prüft
  bzw. erstellt und vorhandene gezielte Tests bei Python-Änderungen ausführt.
  Kreisfall prüft drei 22-mm-Kreise mit festem Karton und vorgegebenen Rollen,
  Nikolausfall die Hausgeometrie, Haus-und-Lochkreis deren eigene Bedingungen.
  Neue Fälle brauchen eigene Prüfkriterien; siehe Trace-Protokoll.
- Starter mit CLI-Ersatz über PTY für alle drei Fälle geprüft, einschließlich
  Modell-Override. Frische Offline-Läufe für `circles` und `nikolaus` im
  temporären Checkout bestanden und im Logger abgeschlossen; Prüfaufrufe
  2,48 s und 7,09 s. Haus-und-Lochkreis über den bestehenden Namen in einer
  neuen Ausgabekopie erneut PASS, 15 vorhandene Tests. Keine neue Gemini-
  Sitzung für die Umstellung gestartet.

## Haus- und Lochkreis in Gazebo, 2026-11-19

- Nutzer wünscht Umsetzung und Ansicht im nativen Gazebo-Fenster.
  Der Kontaktadapter bindet den Seitenkreis, acht Hauskanten, sechs
  axiale Zyklen und den Rückweg an den frisch gemessenen Griff.
  Sichtbare virtuelle Spitze, axial maximal 3 mm am passenden Lochmittelpunkt.
  Gegenwandkreis separat. 20 gezielte Tests bestanden.
- Run03 bestätigt vier Padkontakte. Alle 44 Phasen vor dem Hub dicht
  geprüft. Die Kontaktphysik erreichte 61,35 mm Hub. Fingergeschwindigkeit
  rechts hinten (passive Spitze 0,500 rad/s und Knuckle 0,222 rad/s)
  überschritt 0,2 rad/s. Halt bestätigt, vier Padkontakte erhalten,
  Box ohne Tischauflage. Haus und Zustellungen in Gazebo offen.
- Frühere Testwelt vor dem Hub durch GUI-Start pausiert; Frischewächter
  ausgelöst, Halt nach Wiederaufnahme des Takts bestätigt. Run03 lief
  ohne GUI. Danach mit reiner Ansicht (ohne WorldControl) geöffnet.
  Live-Halt, vier Kontakte und nativer Viewport-Screenshot geprüft.
- Bericht und Nachweise: `setup/tasks/house_drill_gazebo_live_20261119_01/`.
  Ansicht im Halt belassen; kein Öffnen oder Zurücksetzen.

## Gazebo-Vorprüfung der Haus- und Bohrdemo, 2026-11-19

- Nutzer möchte die jüngste Demo zuerst in Gazebo sehen, bevor er
  der Übertragung auf die reale Zelle vertraut. Maßgeblich ist
  `house_drill_gemini_20261119/session-x6z3i06d/trial/artifacts/run02`.
  Hauptrepo-Audit erneut bestanden: acht Hauskanten, sechs axiale
  3-mm-Zustellzyklen auf Ø150 mm, zwei 22-mm-Kreise einschließlich
  Gegenwandkreis mit festem Stift und Rückkehr. 498,13 s Modellzeit
  und 0,097973 rad/s gemessener Modellspitzenwert.
- Kurzer Offline-Transfercheck mit geschlossenen Gazebo-Greifern,
  FCL und allen sechs Armpaaren. Griff aus dem bisherigen Kontaktlauf
  als Offline-Annahme übernommen, originale Arbeitsarmbahn beibehalten.
  Alle drei getesteten Zweige bestehen 39 Phasen bis durch Haus, sechs
  Zustellungen und Rückzug zur freien Vorpose. Der ursprüngliche
  Greifzweig kollidiert beim Weiterdrehen von `right_front`
  (Wrist3/Unterarm). In beiden Alternativfällen besteht der Übergang
  mit 641 Stützstellen. Die IK-Fortsetzung von `right_rear` bricht
  beim Gegenwandkreis mit festem Stift bei Bahnparameter 0,04297 ab
  (257 Stützstellen). Das ist ein lokaler Suchbefund.
- Der aktuelle Gazebo-Adapter akzeptiert drei Kreise mit 25 mm fest
  hinterlegtem Radius. Für diese Demo braucht er pro Phase die
  jeweilige Bahnreferenz: 22-mm-Kreis, Liniensegment, axialer
  Zustell-/Rückzugskorridor und festes Werkzeug bei Kartonbewegung.
  Nächster geeigneter Kontaktlauf: Hub und Unterseite mit virtuellem
  Werkzeug. Greifstabilität, Bahnfehler, sechs Zustellungen und
  Rückweg aus Gazebo-Telemetrie auswerten. Kraft, Drehmoment und
  Materialeingriff beim Bohren sind zusätzliche Prozessgrößen.
- Daten und Fehlerzustände:
  `setup/tasks/house_drill_gazebo_preflight_20261119_01/`.
  Der Transfercheck lief ausschließlich offline. Der frühere
  Gazebo-Hubstopp wegen passiver Fingergeschwindigkeit bleibt ein
  offener Kontaktphysikbefund für die neue Sequenz.

## Neuplanung des Gazebo-Drei-Kreis-Ablaufs, 2026-11-18

- Folgeauftrag: alternative Trajektorie für die Gazebo-Kontaktgeometrie
  berechnen. Boxbewegung und Kreisziele beibehalten. Rechts vorne vor
  Greifschluss anderer IK-Zweig, rechts hinten ursprünglicher Zweig.
- Offline bestanden: Anfahrt und Greifeinfahrt separat, 17 gemeinsame
  Phasen ab Hub bis Absetzen, 39.303 Zustände ≤20 ms, alle sechs
  Armpaare, FCL, Griffzwang und virtueller Stift. Kleinster
  Hüllenabstand 47,35 mm, 785,56 s Modellzeit Hub bis Absetzen.
- Vorschau und Bahn unter
  `setup/tasks/box_drawing_gazebo_replan_20261118_01/`. Kontakttransform
  aus Bild vor Kontakt und Werkzeugposen am Vier-Pad-Stopp abgeleitet.
  Ausführung in Gazebo offen. Frischen Griff binden und Zeichenarm mit
  gemeinsamer Sollzeit, Stoppbindung und 0,1 rad/s einbinden. Der aktuelle
  Kontakt-Runner behandelt ihn als unselektierten Arm (0,05 rad/s).

## Gazebo-Übertragung des Drei-Kreis-Piloten, 2026-11-18

- Folgeauftrag: drei Kreise nach kontaktbasiertem Greifen und Anheben in
  Gazebo ausführen. Basen, Tischanker und nominelle Kartonlage stimmen mit
  dem Modell überein. Hauptwelt lief weiter; Versuche in eigener Kontaktwelt.
- Kollisionswächter akzeptiert im skalaren Kontaktprofil jetzt auch sechs
  Armgelenke plus sechs einzeln gemessene Fingerkanäle. 54 gezielte Tests bestanden.
  0,1 rad/s Armgrenze. Erzwungene dynamische Reserve blockierte schon den
  Reset. Fortsetzung im vorhandenen Kraftmessmodus mit beobachteter Reserve,
  weiter aktivem Geometrie-, Kontakt- und Geschwindigkeitswächter.
- Aus normalem Start Vor-Greifpose erreicht. Frischer Wiederholungslauf
  ab dieser Pose bestätigt vier Pad-Kontakte über 0,310 s Simulationszeit.
  Zustandslücke von 156 ms beim Kameracheck löste vor dem Hub einen
  bestätigten Halt beider Arme aus. Box gestützt, kein Lösen kommandiert.
- Direkte Übertragung mit Kontaktgriffen kollidiert in FCL beim Präsentieren
  von y_min an RF-Wrist3/Unterarm. Getestete Translations- und Yaw-Umwege
  ohne freien Nachweis. Drei Kreise in Gazebo bleiben offen.
  Rohdaten, Bericht und Vorschau im Workspace
  `setup/tasks/box_drawing_gazebo_20261118_01/`.

## Flächenpräsentation im Code-as-Policy-Piloten, 2026-11-18

- Nutzer bestätigt den Ausbau von `present_surface` nach der Trial-Auswertung.
  `box_drawing_pilot.py run --faces y_max z_min y_min` erzeugt das
  Aufgabenprogramm aus der Flächenfolge. Kreisradius, Anzahl der
  Halteposenversuche und Obergrenze für die Transferdauer sind optional.
  Bedienung in docs/box_drawing_pilot.md.
- Der Baustein sucht deterministisch mit bestehenden IK-, FCL-, Hüllen-,
  Werkzeug- und Griffprüfungen. Er prüft den interpolierten Transfer sowie
  Annäherung, Kreis und Rückzug, bevor er einen Kandidaten übernimmt.
  Erster vollständig geprüfter Treffer pro Fläche. Rückwege werden am
  Ende separat geprüft. Vorschauen tragen den Status **CHECKS PENDING**.
  Suchprotokoll enthält Kandidaten, Zeiten und Ablehnungsursachen.
- Lauf reference02 mit 25 mm Radius reproduziert 397,286 s Modellzeit,
  19.882 Prüfpunkte, 50,201 mm minimale Hüllenlücke und 0,096576 rad/s
  Auditspitze bei 0,1 rad/s Grenze. Direkte 180°-Variante an RF-IK-Sprung
  bei 10 % Wegfortschritt abgelehnt. Vorhandener 160°/55°-Umweg als
  Kandidat neu berechnet und angenommen. Transfer-Vorschauen nach 8,85 s
  und 33,38 s ab Schreibzeit von program.json. Gesamtberechnung 115,84 s.
- Alternativfolge `z_min y_max` mit 20 mm, Einzelfläche in passender
  Startpose und neuer Overlap-Regressionslauf bestehen eigene Audits.
  Versuchslimit 1 und Transferlimit 1 s erzeugen erwarteten Fehler
  mit Diagnose. 23 Softwaretests und 18 Chrome-Prüfungen bestanden.
- Artefakte und Hashnachweise unter
  `setup/tasks/present_surface_20261118/verification.json`.
  Modellfixture und Rollen sind pilotenbezogen. Kontaktphysik, neue
  Griffstrategien und eigenständiger LLM-Zeitvergleich bleiben offen.
  Die separate Gazebo-Kontaktuntersuchung steht im Abschnitt darüber.

## Gegenwand im Code-as-Policy-Pilot, 2026-11-18

- `--variant away_face` ergänzt den 25-mm-Kreis auf `y_min` nach `y_max`
  und `z_min`. Rechte Grifftransforms fest, left_front zeichnet, left_rear
  parkt. Versetzte/angehobene Haltepose mit 160° Roll und 55° Welt-Yaw.
  Beide Präsentationswege nach dem Zeichnen rückwärts geprüft.
- Run06 bestanden: 13 Phasen, 397,286 s Modellzeit bei 0,1 rad/s Grenze,
  19.882 Modellprüfzustände (≤20 ms), kleinste Armhüllenlücke 50,201 mm.
  Unabhängiger FK-/Zeitaudit und 20 fokussierte Tests bestanden.
  Kinematikmodell mit angenommener In-air-Fixture, Kontaktmessgrößen unbekannt.
- Trial, Bericht, Viewer und Negativbefunde unter
  `setup/agent_trials/box_away_face_20261118/trial01/`, Vorschau unter
  `artifacts/run06/viewer.html` relativ zum Trial. Bedienung:
  `docs/box_drawing_pilot.md`.

## Gegenwand-Agententest ausgewertet, 2026-11-18

- Nutzer meldet Abschluss des unabhängigen Agenten. Original-Trial01 unter
  setup/agent_trials/box_away_face_20261118/ ausgewertet; Review mit Ursachen
  und Prioritäten: docs/agent_trials/REVIEW_AWAY_FACE_2026-11-18.md.
- Gemessene Entwicklung18:54,88min, 80Befehle, elfNonzero-Exits:
  drei geometrische Kandidatenablehnungen, drei Suchläufe ohne Treffer,
  drei Aufruf-/Pfadfehler, eine Sandboxblockade und eine verfrühte
  Statusabfrage. Rund85,2%Wandzeit in Planungsstufen inklusive Bearbeitung.
  Befehlsintervalle9:41,64min; übrigeWandzeit keine gemessene Denkzeit.
  Vorlauf, vollständigerClientexport, Modellname/Token/Kosten unbekannt.
- Run06-FK-/Zeit-/Episodenaudit erneutPASS mit identischem Ergebnishash;
  397,286sModellzeit, dreiKreise, vollständigerRückweg, Peak0,096576rad/s.
  Original-FCL-Prüfung nicht unabhängig neu implementiert/wiederholt.
  EchterChrome-Test mit zwölfPrüfungen und ScreenshotPASS; Feedbackpayload
  nur abgefangen, keine Rückmeldung in dieEpisode importiert.
- Logginglücke an acht `python3 -`-Bearbeitungsbefehlen nachgewiesen.
  Logger jetzt mit optionalem `--stdin-file DATEI|-`: exakteInputkopie,
  Größe/Hash und Weitergabe dieserKopie; ohneOption explizit unerfasst.
  Zehn gezielteLoggertestsPASS. Protokoll/Git-Diff-Abschlussregeln ergänzt.
- Empfohlener nächsterAusbau: wiederverwendbarer `present_surface`-Skill
  mit Halteposen-/Routensuche und strukturiertenDiagnosen, dann einheitlicher
  Aufgabenvertrag und früheVorschau. Ein erfolgreicherKinematiktrial belegt
  noch keine Fast-LLM-Benchmark, Teleop-/Demolernen oder Langzeitverbesserung.
  Evidenz und Browserdaten: setup/agent_trials/box_away_face_review_20261118/.
  KeineHardware-/Kamera-/Dienstaktion. FremdeÄnderungen erhalten.

## Erster Feedbackzyklus: Boxzeichnung koordinieren, 2026-11-17

- Nutzer hinterfragt Umkonfiguration des Arbeitsarms vor Unterseitenkreis;
  schlägt höher/näher gehaltene Box oder gleichzeitiges Umstellen vor.
  Rückmeldung in run08/episode an transfer_to_z_min gespeichert; neue
  Modellvarianten binden diese Episode und Feedbackhashes als Herkunft.
- Ursache im ersten Programm: Boxdrehen und Workerwechsel seriell, nähere
  LF-IK scheitert bei Anfahrt an forearm/wrist2-Selbstkollision. Gewählter
  anderer Zweig verlangt165,40°wrist1/129,74°wrist3. Keine Aussage, dass ein
  solcher Wechsel für jede Boxpose nötig wäre. Mehrere Offlineprobes erhalten.
- Neue CLI-Varianten --variant overlap und closer_coordinated, optional
  --feedback-from RUN. Ursprung/Ende aller24Armgelenke und Zeichenaufgabe
  unverändert. Baseline --variant baseline weiterhin reproduzierbar.
- overlap01: gleiche Boxposition, vollständige Umkonfiguration gleichzeitig
  mit80°Boxdrehung, gemeinsame Rückbewegung;49,837s statt66,858s Modellzeit
  (17,022s/25,46%weniger). AchtPhasen/2504Prüfzustände≤20ms,
  minArmhülle230,818mm. GroßeWristbewegung bleibt, separateWartephase entfällt.
- closer01: 8cmWelt−XnäherzumLF, Verschieben undZurückversetzen tatsächlich
  enthalten. DurchgängigerLF-Zweig und koordinierter Übergang, größter
  Gelenkhub dabei33,66°statt165,40°. ZehnPhasen/3421Prüfzustände≤20ms,
  minArmhülle213,628mm. Gesamtdauer68,073s; geringerer Gelenkhub ist hier
  kein schnellerer Gesamtablauf unter gleichem v/a/Ruck-Profil.
- Beide vollständigen Interpolanten/FCL/Markergeometrie/alle6Armpaare/
  GriffzwängePASS, separateFK-/ZeitauditsPASS. Prüfungen unverändert;
  gleiche Anfangs-/Endzustände im gespeicherten Vergleich nachgeprüft.
  Modellbewegungsüberlappung aus tatsächlichenSplineableitungen geschätzt,
  nicht allein aus gleichzeitigem Versand abgeleitet. KeineKontaktphysik.
- Vergleich setup/tasks/box_drawing_pilot_20261117/feedback-comparison01/
  viewer.html undcomparison.json; Baseline/overlap01/closer01 auswählbar.
  13SoftwaretestsPASS,35/39Variantenbrowserchecks+7VergleichschecksPASS,
  Screenshotsvisuellgeprüft. HöhereBoxen undalternativeStartzweige zunächst
  nurStichproben, nichtvollständigqualifizierteWeitereVarianten.
- Arbeitsstandwork/box-drawing-pilot.md, Anleitungdocs/box_drawing_pilot.md.
  Beispiel für Nutzerfeedback→konkreteCodeänderung→geprüftenVergleich;
  keine autonomeGewichtsaktualisierung, Realfahrt oderDienstaktion.

## Hierarchischer Vorfilter auch mit neuen Stoppreserven, 2026-11-17

- Nutzer wünscht die entwickelte Kollisionsmethode künftig bei Wegprüfungen
  und eine Angabe der Berechnungsdauer. Als Arm-AABB-Methode16.11.interpretiert,
  RückfragezurBestätigungoffen. NeuerkörperbezogenerReservezweigumgingbisher
  derenPython-Vorfilter; jetztautomatischintegriert. JedeKugelumeigenes
  Stoppbudgetaufweiten, sichereElternhüllentrennungnutzen, sonstunveränderte
  Feinprüfung. GeometriecachemitAbhängigkeitsbindung, Budgetneuberechnung.
- AktuellerLF-Weg01eoffline:20,182→10,074sfürgesamtePlanunginklEndprüfung/
  Metriken; Modellaufbauzusätzlich1,471s. GeometrischeWegfindung2,567→1,144s.
 895Trajektorienpunkteexaktgleich;150Zustände×3Wiederholungen5,316→2,294ms
  proZustand. NurdiesesBeispiel, keineallgemeineLaufzeitgarantie.
- 50gezielteTestsund316gesamteMotion-PytestsPASS. ExakteWächter-/Leasewerte,
  Grenzwerte/Geometrie/Profilbindungenunverändert. KeineRoboterbefehleoder
  Dienstneustarts. q6-Profilfreigabebleibtseparatausstehend.
  Details docs/collision_prefilter.md / work/body-reserve-prefilter.md;
  Messung setup/calibration/oak_recalibration_20261117/body-prefilter-benchmark-01/result.json.

## Hinteres Armpaar: erste Kollisionsstichprobe, 2026-11-17

- Nutzer schlägt die näheren hinteren Arme für schwierigere Kartonfälle vor.
  Offlineprobe mit vorhandenen ObjectTransport/TwoArmTeacher/discover_start,
  individuellen TCPs, festen kurzen Seitengriffen, unveränderter FCL/20mm-Prüfung.
  Basen hinten0,991m statt rechts1,35m; Karton quer gedreht und zwischen
  hintereArme gesetzt. Frontarme bleiben modellierte aufrechte Hindernisse.
- Drei Startlagen x0/y0,25/0,40/0,55m bei bisheriger angehobener Höhe geprüft:
 2/2/6gültigeIK-Kombinationen; ausgewählte Anfangsabstände der tragenden Arme
 230,8/221,1/84,8mm. Je±60°umWeltXYZ mit5cmZwischenhub, Start=Ende,
 61Stützstellen proReferenz. FCL-kollidierende Referenzen0/6,1/6,5/6;
  IK-Abbrüche2/6,1/6,0/6. Andere Hüllenfehler getrennt erhalten.
- Konkreter nativer Kontaktzeuge beim hintersten Start/+60°WeltZ:
  left_rear_forearm_link gegen right_rear_forearm_link. Somit tatsächlich
  Arm/Arm-Fall, nicht nur aufgeblähter Mindestabstand. Geprüfte freie Enden.
- Diese kleine gezielte Stichprobe belegt geeignete schwierige Referenzen,
  keine statistische Kollisionsrate, keine erfolgreiche Optimierung/Anfahrt,
  Kontaktphysik oder Trainingsfreigabe. Rechter Kontrollstart bei denselben
  Weltachsenproben1/6frei und5/6IK-Abbrüche; kein fairer allgemeiner Rankingbeweis.
- Artefakte setup/research/rear-pair-screen-20261117/{result,summary}.json,
  probe.py/check.py, nativer Kontaktlog. Zwei Fehler der Zeugenextraktion
  (Zeilenschema) korrigiert; ursprüngliches Screening unverändert erhalten.
  Keine produktiven Kernquellen/Geräte/Dienste verändert; Arbeitsstand
  work/rear-pair-screen.md. Nächste fachliche Stufe: diese Fälle optimieren
  und vollständig zeitparametriert prüfen, bevor BC-Beispiele exportiert werden.

## Code-as-Policy-Pilot: erste Dreiarmszene und Episoden, 2026-11-17

- Nutzer bestätigt Pilotstart und grenzt Auswertung ein: zunächst Dauer,
  beobachteteKraftmaxima, Fehlgriff/Neuansatz, Objektverlust, Agenteneingriffe
  und subjektives Endfeedback; detaillierteStrichbild-/Produktoptimierung
  ist optional. FehlendeMessungen nicht alsNull, Nutzermeldungen getrennt.
- Implementiert neue isolierte Module box_drawing.py/pilot_episode.py und
  tools/box_drawing_pilot.py. Gespeichertes Pythonprogramm läuft gegen
  file-only Kinematikadapter: beide rechtenArme halten, LF führt virtuellen
  Marker, LR geparkt. Zwei benannte Flächen y_max/z_min, nichtalleBoxseiten.
  In-airFixture16cm, offeneGreifer/festeGrifftransforms alsAnnahmen.
- Erster Referenzlauf setup/tasks/box_drawing_pilot_20261117/run08/:
  MODEL_SEQUENCE_COMPLETE, zehnPhasen/66,858sModellzeit,3358Prüfzustände≤20ms.
  80°Präsentation derUnterseite, beideKreise, Arbeitsarmräumen undRückdrehung.
  FCL/bewegterKarton/alle6Armpaare/virtuellerMarkerkörper geprüft;
  minArmhüllabstand230,818mm. KeineKontaktphysik oder Last-/Stoppqualifikation.
- Separater Audit PASS:1510FK-Zustände/2001AbleitungsprobenjePhase,
  Phasenanschlusssprung0, gemeinsameHalteframes undKreisreferenz numerisch
  erfüllt. v/a/Ruck-Spitzen0,35/0,40/1,463rad-Einheiten. WinzigeFK-Fehler
  sind numerischeKonsistenz, keinephysischeGenauigkeit. result.json,
  independent-audit.json undImplementierungs-/Modellhashes imLauf.
- Episoden: manifest/hashgebundeneEreignisfolge, Modell-/Rechen-/Ausführungszeit
  getrennt, deklarierteBeobachter, Kraftmaxima proSensor/Frame/Bezugspunkt,
  Originalfeedback mitPhase. CLI summary/history/feedback; ImportfremderEpisode
  oderPhaseabgewiesen. NochkeineangeschlossenenKraft-/Griff-/Verlustdetektoren,
  entsprechendeFelderUNKNOWN; keinNutzerfeedbackstellvertretendangelegt.
- viewer.html mitPlay/Pause/Zeitschieber/Orbit/Phasen/Code undFeedbackexport.
 13Softwaretests und39BrowserchecksPASS, Screenshotpreview.pngvisuellgeprüft.
  Browser-QA-Beispieltext nichtinEpisodenimportiert. HTMListOriginalsnapshot;
  CLIzeigt spätereFeedbackeinträge. Browser-Sandboxsocketblock, isolierte
  Hostprüfungerfolgreich; keineÄnderungbestehenderBrowserprofile.
- NegativeEntwicklungsversuche1–5erhalten: virtuelleSpitzengeometrie,
  Transit/Selbstkollision undabschließendeBoxdrehungbeiMarkerimSchwenkraum.
  KorrigiertdurchpassendePräsentation, vollständigeBranch-Vorprüfung und
  explizitesArbeitsarmräumen. VerworfenesPlanningnichtalsRuntimeeingriffzählen.
- Bedienung docs/box_drawing_pilot.md, Arbeitsstandwork/box-drawing-pilot.md.
  Quellbaum-CLIohneNeuinstallationgeteilterKontaktplugins; keineROS-Nodes,
  Hardware-/Kamera-/Dienstaktion oderTraining. NächsteStufe: Nutzerfeedback,
  Kontakt-/Ausführungsadapter, Teleop undgetesteteProgrammverbesserung.

## OAK-Aufnahmeanfahrt: LF-Handgelenkdiagnose, 2026-11-17

- Hauptauftrag weiterhin vier Aufnahmestellungen plusFünfkameraGUI. ErsteLF-
  Anfahrt automatisch gehalten, Zielnicht erreicht. Vergleich zeitversetzter
  ROS-/RTDE-Werte korrigiert, unveränderte5mrad-Grenze einschließlich
  Interpolationsunsicherheit; 40Tests/Build/separaterMockPASS, real lesend
 1.616Vergleiche max0,520mrad. Keine allgemeine0,3rad/s-Stoppqualifikation.
- Nachfolgend LF-q6 imNativezustand Geschwindigkeitbis0,04446rad/s und
 0,001079radPositionsspanne/10s. Nutzer bestätigt kleine realeRucke; Ursache
  ungeklärt, keinbloßerRauschennachweis. LFStillstandnichtbestätigt, Wächter
  wiederholtSTOP; andere3ruhig. KeineFilter-/Stillstandslockerung.
- Nutzerfreigabe ausschließlichLFStandbyundPower/Brake/ROS-NeustartzurDiagnose
  erhalten. Standby tatsächlichPOWER_OFF/NORMAL/STOPPED bestätigt, keinFahrziel.
  Power/Brake-NeustartbestätigtRUNNING/NORMAL/STOPPED; danachursprüngliche
  StillstandsprüfungwiederPASS, LF2,016s/vmax0/Positionsspanne83,9µrad.
  SoftwareReset/ROS-Wiederanlaufbestätigt. NeuerRealversuch01dbeiLFq6−0,03811
  gegen0,00755rad/sgehalten; wiederstationär, Aufnahmestellungnicht erreicht.
  Kandidat01emitq6-Monitor0,1inklneuerReserve/FCLPASS47,89snochNICHTaktiviert.
  AutomatischePrüfunglehntkonkretenProfilwechselmangelseindeutigerFreigabeab;
  expliziteBedienerzustimmungangefragt, keineUmgehung/keineTeilaktivierung.
  KameraGUIläuftpausiert. Details work/oak-recalibration-20261117.md,
  Daten setup/calibration/oak_recalibration_20261117/hardware-views-01/.

## BC-Zielketten und Arm/Tisch-Bedingung, 2026-11-17

- Nutzer möchte längere Abläufe ohne Rücksetzen zur Mitte, freie Kontrollen
  plus viele enge/kollidierende Referenzen und Tischvermeidung.
- Neue Offline-Tools generate_teacher_episodes.py, teacher_episode_core.py,
  review_teacher_episodes.py. Tatsächlicher validierter Endzustand wird exakt
  weitergereicht; feste Griffe, gemeinsamer Stillstand an jedem Ziel. Neue
  Arm/Tisch-Kugelhüllenbedingung samt analytischem Gradienten, unveränderte
  native FCL-Prüfung. Frühere gebundene Teacher-/Hardwarequellen erhalten.
- Pilot setup/research/teacher-episodes-20261117/run01: zwei vollständige
  Sechs-Ziel-Ketten, 56,88/47,99s Modellzeit, 1,648/1,023m Objektweg,
  bis46cm vom ursprünglichen Anker, XYZ-Spannweite bis50,3/44,0/23,7cm.
  Zustandsübergabesprung0, 20.991Prüfzustände bei≤5ms bestanden,
  1.200geometrischeBC-Übergänge; `goal_terminal` gilt proZiel, keinRegeltakt.
  ZwölfAbschnitte aus200Vorschlägen, Workerzeiten107,47/92,51s mit2CPUs/BLAS1.
- MinArmpaar115,5/58,9mm, MinArm/Tischje27,6mm. KeineReferenzkollision,
  keine20mm-Armpufferverletzung und keineTeacher-Korrektur. Sechs `near`
  sind nur die breite<80mm-Suchklasse; hoherSchwierigkeitsanteil bleibt offen.
  LängereZielkettenverbessernZustandsabdeckung, garantierenkeineGrenzfälle.
- AlterFCL-Tischfallweiternegativ: neueHülle−55,1mm aufReferenz undbereits
  −30,8mmamfestenZiel. LokalerUmwegkannungültigenfestenEndpunktnichtreparieren.
  NeuerScreenerweistdasZielab. ViergesamteArm/Tisch-GradientprobenFehler≤4,9e−10.
  KonservativeHülle≠nativerKontakt; keineglobaleUnlösbarkeitbehaupten.
- 23gezielteTestsinklusivevierneuerTests, Export-/Übergabeaudit undzehnBrowserchecksPASS;
  viewer.html/viewer.pnggeprüft. Detailsdocs/teacher_episodes.md.
  Gruppenpoolweiterunassigned, verwandteFamilienauchüberfrühereRunsbinden.
  KeinNetztraining, keineGeräte-/ROS-/Dienstaktion. SchwierigeReferenzenmit
  gültigenEndenundTeacher-LösungbleibennächsteDatenfrage.

## BC-Daten: echte Kollisionsfälle zuerst auswählen, 2026-11-17

- Nutzer kritisiert geringe Schwierigkeit und langsame Datenerzeugung. Ziel:
  Referenzen, die ohne Planung kollidieren; positive Abstandsverletzungen
  nicht als nachgewiesene Kontakte darstellen. Die letzten13+4gültigen Bahnen
  hatten keine FCL-Kollision der Referenz, im älteren21-Bahnen-Satz neun.
- Neue CLI tools/mine_teacher_collisions.py: eingefrorene Startbank/Modelle,
  bisdreiIK-Kombinationen jeStart, einfache direkteSE(3)-Verbindungen,
  optionalbreiteZielorientierungen. Erst61-Punkte-Screening, gültigesEnde
  aufdemfortgesetztenIK-Zweig, dannnurFCL-KandidatenzumteurenLehrer.
  FCL-Kontakt/Hüllenüberlappung/positiveAbstandsverletzunggetrennt;
  nativeKontaktzeugenmitLinknamen undPose/Gelenkzustandgespeichert.
- Ergebnis setup/research/teacher-collision-mining-20261117/:run01
 184Kandidaten/29,61s,89ohneTreffer/54IK-Fehler/41ungültigeEnden.
  run02enthältdiese184plus736Zufallsziele:920/80,74s,107ohneTreffer,
 723IK-Fehler/89ungültigeEnden/einFCL-Fall. Raten6,2/11,4Kandidaten/s,
  keineRatenpositiverLehrerbahnen. ZufallsausbeutefürschwierigeFälleunzureichend.
- EchterFall north-ik3-random-011: gültigerStartundZiel, RF-Ober-/Unterarm
  trifftTischplatte. LehrerREFERENCE_CONSTRAINTS_CLEAR, weilArm/Umgebung
  keineeigeneOptimierungsbedingungist. DichterRecheckverwirftBahn:
 2.108Zeitpunkte/266FCL-Fehlpunkte. KeinpositivesTrainingsbeispielexportiert.
  recheck01/viewer.html zeigt ausdrückliche negativeReferenz, keineLehrerlösung.
- ZusätzlichelokaleZwischenrotationsprobenlocal02:vierHüllenüberlappungen
  bis−16,7mm,keineFCL-Kontakte. NichtalsblockiertedirekteStart-Ziel-Aufgaben
  ausgeben. FrühereEinordnungMARGIN_ONLYinlocal01historischerhalten.
- NumericalAdapterimMiningbegrenztFortschrittsrundung≤1e−12auf[0,1];
  ersterRecheckrun02an1+ulpgescheitert, recheck01danachgeometrischverworfene
  Bahnkorrektvollständiggeprüft. AltegebundeneKernquellenunverändert.
- Build/viergezielteTests/achtBrowserchecksPASS,Screenshotgeprüft.
  Dokumentationdocs/teacher_collision_mining.md, Arbeitwork/teacher-collision-mining.md.
  NächsterfachlicherSchritt: fehlendeLehrerbedingungen/gegebenenfallsglobale
  Initialisierung, dannSamplingumechteKontaktgrenzen undAusbeutemessen.
  KeinTraining, keineGeräte-/Dienstaktionen; Mining-PoolnochkeinemSplitzugeordnet.

## RF-Stopptest real ausgeführt / q6-Grenze 0,1 rad/s, 2026-11-17

- **Abschließender Versuch05 PASS** nach Recorderkorrektur/29gezieltenTests.
  StoppACK, gemessenerStillstand, RF-Hold und Verriegelung bestätigt; keine
  Guardfaults. Bei0,001728rad/sMedianvorStopp:20%-Geschwindigkeitsabfall in
  empfangenenDaten nach14,79ms, erstes20msFenster≤0,0002rad/s ab30,86ms,
  strengerStillstands-/Holdnachweis nach939,23ms. KeineallgemeinenBremsgrenzen.
 8.078Samples/2msGeräteraster, maxEmpfangslücke22,41ms; q6Nettonachlauf4,77µrad
  unterEncoderstreuung, daherkeinegenaueBremsstrecke behaupten. Gesamtq6-Versatz
  imLauf0,003225rad. Alle4abschließendRUNNING/NORMAL/PLAYING/Reverseverbunden,
  RFweitergehalten/verriegelt, keinReset/Rückweg nach05. AktivesProfilunten.
  VollständigeDaten `setup/realtime/right-front-stop-20261117-05/`, analysis.json.
 03/04 bleiben historische Fehlversuche;05ist separater Erfolgsnachweis.
  ErsteNiedrigphasebei31msnichtdauerhaft: kurzegemeldeteq6-/q5Überschreitungen
  bis175,7/384,8ms; durchgehendniedrigbisMessendeab386,84ms. Bestätigtes
  QuietWindow390,78–936,90ms. PhysischerBremswegunterEncoderstreuungunaufgelöst.

- Nutzer bestätigt Durchführung, freie/unbeladene Übergabe und Not-Halt-Zugriff;
  danach ausdrücklich nötigen Start der vier ROS-Programme. Beim Scharfschalten
  zunächst native Stopps durch fehlende Verifikation/Watchdog während Discovery.
  Nach stabilen Nachweisen kontrollierter Startupreset, jeUR PLAY über Bringup.
  Keine Power-/Brake-/Greiferaktion; vorhandene Treiber/Kameraansicht erhalten.
- Versuch03 mit altem langsamen Profil: realer RF-q6-Weg durch SPEED LIMIT
  gestoppt (Guard0,004729rad/s >0,003; roher500HzPeak0,021313). Absichtlicher
  Trigger nie erreicht, daher kein Reaktionszeitmesspunkt. RF-Endversatz zum
  Start ca0,332mrad/0,0190°, alleArme danach unabhängig stationär.
- Nutzer fordert anschließend Grenze0,1rad/s. Neues separates Profil
  `uwa_cell_motion/config/hardware_right_front_stop_test.yaml` aktiviert:
  nur RF-q6 überwacht0,1, übrige23Achsen0,003, Kommando0,003/a0,006.
  Vorhandene5%-Toleranz erhalten und in Reserve berücksichtigt; neuer Modus
  per_body_joint_caps_v2, vollständige frische Bahn-/FCL-/Reserveprüfung PASS.
  Frische,10Hz,40mmPuffer,1sStopplatenz und0,2rad/s²Bremsannahme unverändert.
- Versuch04: absichtlicher Supervisor-Stopp tatsächlich ausgelöst/ACKtrue,
  keine Guardfaults während der Probe. Nativeq6Peak0,012449rad/s; gesamte
  Nettoauslenkung bis späterem Stillstand0,002872rad/0,16455°. Kein Bremsweg.
  Recorder behandelt erwartete Action-Cancellation als Fehler und endet49,9ms
  nach Stoppanforderung. analysis.json lässt Bremszeit/-strecke deshalb null.
  Empfang des Holdstatus nach49,3ms, Stillstandsfensterstatus nach618,7ms;
  diese Nachweisverzögerungen nicht als physische Bremszeit ausgeben.
- Unabhängige1,2sEndkontrolle alle4stationär/RUNNING/NORMAL, ProgrammePLAYING,
  Reverse verbunden. Schutzdienst aktiv mit neuemProfil, **RFimSupervisor
  verriegelt/gehalten**, andereArme ohne Fahrziel. Kein Reset/Rückweg nach04.
- Artefakte `setup/realtime/right-front-stop-20261117-{03,04}/`, Originalrecords,
  Pläne, angewendeteTrajektorien, Interlockspur, Quellenhashes, Native-Endkontrolle
  und Diagnose-PNG/JSON. OriginaleFAILbleibenerhalten; Recorderfix separat.
  Anleitung docs/right_front_realtime_stop_test.md, Arbeitsstand
  work/right-front-realtime-stop.md. Reale Bremsparameter weiter unqualifiziert.

## Anfahrtempo0,1rad/s vorgeschlagen, 2026-11-17

- Nutzer hält auch9,24min für die vier Kameraposen für zu lang; schlägt eine
  Obergrenze0,1rad/s vor und gibt Nothaltzugriff an. Keine gemessene Stoppgrenze
  oder Freigabe zum Abschalten von Schutzfunktionen daraus ableiten.
- Reiner Zeitvergleich derselben glatten seriellen Wege, unveränderte
  Beschleunigung0,02rad/s²:173,27s/2,89min bei0,1rad/s; LF47,87/LR39,02/
  RR56,85/RF29,53s. Quelle setup/calibration/oak_recalibration_20261117/
  speed-0p1-time-only.json. Keine bestandene Stoppreserveprüfung oder Realfahrt.
- v2 bleibt trotz Körper-/Achsgrenzen zu pauschal über den ganzen Weg: kurze
  Engstelle links hinten begrenzt die gesamte Fahrt auf0,01364rad/s. Lokales
  Tempo und passende gebundene Betriebsverträge sind noch nicht umgesetzt.
  Die1sStoppannahme ist weiterhin ungemessen und nicht unveränderliche UR-Grenze.
- Separater RF-RT-Stopptest laut work/right-front-realtime-stop.md in Durchführung;
  in dieser Diagnose weder dessen Controller noch gemeinsamen Schutzdienst
  ändern.0,1-Sensitivitäten ausschließlich offline und ausdrücklich hypothetisch.
- Sensitivität abgeschlossen unter speed-0p1-diagnosis/summary.json: Bei1s
  besteht die Reserveprüfung für LF/RR, scheitert für LR/RF. Selbst mit rein
  hypothetischen50ms scheitert LR noch; Datenalter/Takt, angenommene Bremsung
  und achsweise Trackingzulage wirken ebenfalls. Keine Latenzänderung aktiviert.
  Zeitwert2,89min ist deshalb weiterhin keine bestandene Bewegungsfreigabe.

## Kooperative Code-Policies und langfristiges Lernen, 2026-11-17

- Nutzerkorrektur:32Aufgaben/21Bahnen sind separate Kollisionsvermeidung.
  Hier geht es um Gesamtaufgaben: zweiArme halten/drehen Avocado-Karton,
  dritter stapelt Teil2 oder zeichnet Kreise auf jede Boxseite. CodeasPolicy
  ausdrücklich bestätigt. Frühere Transport-Pilotempfehlung damit überholt.
- Nutzer bevorzugt Agentenvorführung zunächst inSimulation mit sprachlichem
  Feedback oder direkterTeleopkorrektur; gezielteHandführung bleibt interessant,
  automatischeErkennungdesBedarfs ist ausdrücklich fraglich. Langfristiges
  Lernen aus eigenenAusführungen plus manuellemFeedback fürIndustrie/Bau gewünscht.
- Recherchefortsetzung: DAgger/HG-DAgger für Korrektur an selbst erreichten
  Zuständen; Reflexion/Voyager für sprachliches/prozeduralesGedächtnis ohne
  Gewichtsupdate. HG-DAgger untersuchtFahren, VoyagerMinecraft; keine automatische
  Übertragbarkeit ihrerErgebnisse oderDAgger-Garantien aufLLM-Code behaupten.
- Entwurf docs/interactive_code_policy_learning.md: versionierteCodeprogramme,
  Halte-/Arbeitsrollen, Simvorführung/Übernahme, zustandsgebundeneKorrekturen,
  Episoden-/Regel-/Skill-/Parameterwissen, Lernen ausgemessenenErgebnissen.
  EigenständigeErgebnisprüfer, Kandidatenvergleich undRegressionen erforderlich;
  erfolgreicheBewegung istwedergezeichneterKreisnochstabileStapelung.
- Empfehlung: Kreisaufgabe alsSimulationspilot, zunächstexplizitkleinererUmfang
  möglich; jedegeforderteSeite späterinklusiveGreif-/Stützverdeckung behandeln.
  Reihenfolge/Pilotumfang nochkeineNutzerentscheidung. NeueWerkzeug-/Kontakt-/
  Prüffunktionen, MehrrollenrunnerundTeleopintegration weiteroffen.
- BestehendenReviewkorrigiert, AGENTS/README/Arbeitsstand ergänzt. NurDokumentation;
  keineSimulation, Geräte-/Dienstaktionen, Trainingsläufe oderImplementierung.

## Stoppreserve allgemein überarbeitet und im Mock geprüft, 2026-11-17

- Nutzer wählt die allgemeine Überarbeitung statt extrem langsamer Fahrten.
  Ursache der72,19min war die provisorische globale Kommandogrenze0,004rad/s
  als Behelf gegen pauschale Arm-Maximalreserven, keine physische UR-Grenze.
- Neuer opt-in-Modus `per_body_joint_caps_v2`: Kommandotempo getrennt von sechs
  einzeln überwachten Achsgrenzen je Arm; Reserve pro Körper, vollständige
  Kugelpaarprüfung und kürzeste Ausfall-Lease über alle Paare. Vollständig
  eingeschlossene virtuelle Greiferöffnung nicht doppelt aufblähen. Timing
  und Überwachung verwenden denselben signaturgebundenen Achsvertrag.
- Vier unveränderte Sichtwege offline:72,19min →9,24min; LF1,60/LR4,77/RR1,89/
  RF0,98min. Modellpuffer40mm, angenommene1sReaktion/0,2rad/s²Bremsung,10Hz
  und Frische unverändert. Neue Zeiten sind Vorschläge unter diesen Annahmen.
- Build/CTest PASS,268Motion-Regressionen PASS und31abschließende gezielte
  Tests PASS. Getrennte Mock-Prozesse in Domain67 PASS: Achsgrenzenfahrt,
  Datenverlust stoppt Nachbarn, keine automatische Wiederaufnahme und Ausfall
  jeweils von Guard/Supervisor/Watchdog hält alle. Fehler früherer Testläufe
  erhalten; produktive Frische-/Resetgrenzen nicht für Tests gelockert.
- Anleitung docs/stopping_reserve.md, Arbeitsnachweis work/stopping-reserve-revision.md.
  Artefakte setup/calibration/oak_recalibration_20261117/reserve-v2-audit-02/,
  reserve-v2-process-mock-02/ und reserve-v2-benchmark.json. Geometrie allein:
 100Aufrufe Median3,78ms/Maximum4,02ms, keine Ende-zu-Ende-Fristgarantie.
- Neue reale Profile nicht aktiviert und Arme nicht gefahren. Ursprüngliche
  Aufnahmestellungen/Neukalibrierung weiterhin offen; vor realer Verwendung
  frischen Start und passenden aktiven Phasenvertrag prüfen. Die physische
  Stoppkette ist durch diese Software-/Mockprüfung nicht qualifiziert.

## BC-Teacher mit verschiedenen Ausgangszuständen, 2026-11-17

- Nutzer bestätigt weitere schwierige Fälle und bemängelt praktisch gleichen
  Start aller bisherigen Abläufe. Startvielfalt ist ausdrücklich Teil des
  nächsten Datensatzes, nicht nur Ziel-/Zwischenbahnvariation.
- Neue Module/CLI teacher_starts.py, generate_diverse_teacher_dataset.py und
  review_diverse_teacher_dataset.py. Zwölf vorab festgelegte Startfamilien,
  je zwei Ziele; getrennte Multistart-IK je Arm, anschließend gemeinsame
  Prüfung aller Kombinationen. Volle Gelenkumdrehungen dedupliziert.
- Startbank geprüft: neun von zwölf Posen gültig, je2–12gültige Armkombinationen.
  Auswahl einer gültigen Kombination mit kleinstem Armhüllabstand je Pose.
  Startausdehnung32×32×14cm, Orientierungsunterschiedbis125°, kleinster
  Start-Armhüllabstand58,91mm. Noch keine Aussage über alle folgenden Bahnen.
- Quellen eingefroren im Forschungsordner frozen-source/ wegen paralleler
  Änderungen am Planungsunterbau. Ursprüngliche Pilotquellen unverändert.
  Offline-Trajektorienlauf unter setup/research/two-arm-diverse-starts-20261117/
  run01/ abgeschlossen:13/24gültige Bahnen ausachtStarts,1.300Übergänge.
  AkzeptierteStartabdeckung32×32×10cm,max34,76cm/125°zwischenStarts;
  mindestens13,4cmvomaltenAnker. SechsAufgabenohnegültigenStart,fünfReferenz-
  IK-Fehler. HauptlaufminArmabstand32,22mm, eineReferenzkorrektur.
- Zusatzdiagnoseencounters01: sechsvorabfixierteZwischenrotationsverstärkungen
  anzweiStarts, Start-/Endposeunverändert, Eltern-Hashes/Splitsübernommen.
 4/6gültig,400Übergänge. ZweiRF/RR-Armabstandsverletzungenkorrigiert:
 15,82→21,00mm(max2,05mm/1,17°) und5,64→21,00mm(max4,74mm/3,48°).
  ReferenzenkeineFCL-Kontaktkollision,20mmHüllabstandsbedingungverletzt.
  EinKonditionsfehlerundeinIK-Fortsetzungsfehlererhalten. GezielteDiagnose
  nachSichtung,keinunabhängigerBlindtest. Insgesamt17neueBahnen/1.700Übergänge.
- Buildund18TestsPASS, beideExportauditsPASS, WiederaufnahmebeiderLäufePASS,
 199/73BrowserchecksPASSundScreenshotsgeprüft. Galerienjeweilsviewer.html.
  StartorientierungzumaltenAnkerundlaufendeÄnderungzumneuenStartgetrennt.
  NochkeinausgewogenerTrainingskorpus: positiverMisch-Trainanteilimhiesigen
  Hauptlaufleer, ArmkorrekturdiagnosenerbenTestsplit. WeitereFamiliennötig.
- Gleiche feste Griffe/Objekt/Basen/parkendeArme. Unabhängige Anfangszustände,
  kein Nachweis einer Anfahrt oder eines IK-Zweigwechsels bei starrem Griff.
  Kein Netztraining, keineGeräte-/Dienstaktionen. Anleitung
  docs/teacher_start_diversity.md, Arbeitsstandwork/teacher-start-diversity.md.

## Programmierpipeline: wenige Demonstrationen plus Sprache, 2026-11-17

- Nutzer möchte bestehende Pipeline für ein schnelles einfaches LLM verfeinern
  und optional Vormachen per Teleoperation/Handführung mit Bildern, UR-Posen,
  Kräften und sprachlicher Erklärung nutzen. Keine vollständige Gesamtpolicy.
- Code-/Dokumentationsreview und Primärliteraturrecherche abgeschlossen:
  docs/programming_pipeline_lbd_review_2026-11-17.md; Arbeitsnachweis
  work/programming-pipeline-lbd-review.md. Bestehende parallele Änderungen erhalten.
- Empfehlung: gemeinsame typisierte Aufgabenbeschreibung für Sprache und Demo,
  objektrelative Phasen/Bedingungen, danach vorhandene Skills und numerische
  Prüfung. Bestehender Skillkatalog ist noch kein generischer Interpreter;
  Kartonfolge derzeit in runtime._run_task. Planner-BC bleibt getrennte Ebene.
- Vorhandenes pilot02-summary/export-audit gelesen:21/32Bahnen,2100Übergänge,
  Auditpassed:true; kein neues Training/Prüflauf. Rotations-Testabdeckung fehlt,
  Bild-/Sprach-/Kraftkonditionierung nicht Teil dieser52D-Planereingabe.
- Besonders passend ShowTell, Demo2Code, DROC; ergänzend Code as Policies,
  DINOBot, task-parametrisierte Few-Demo-Skills, Forceful Manipulation und
  MimicGen. ACE-CaP-0(12.11.2026) als neuer Preprint separat eingeordnet;
  kein Beleg schneller kleiner Modelle oder genereller Zwei-Demo-Garantie.
- Offener Bedarf: gemeinsame Aufnahme/Zeitqualität, Quellen-/Framebindung,
  Phasensegmentierung und harte/weiche Bedingungen, MRS-Rollen/Greifgruppen,
  beobachtbare Erfolgsbedingungen, reale Kraft-/Kontaktintegration. HQ-Standbilder
  ersetzen keinen dynamischen Demostream; aktuelle OAK-Neuregistrierung beachten.
- Erste Pilotempfehlung (durch spätere Nutzerpräzisierung überholt): vorhandenen Simtrace importieren, dann erklärtes Zweiarm-
  Versetzen und Übertragung auf zurückgehaltene Objektlagen. Sprache/1Demo/2Demos
  und kleines/stärkeres Modell bei gleicher Bibliothek vergleichen; Zeit bis
  validiertem Programm einschließlich Bedienaufwand messen. Empfehlungen noch
  nicht vom Nutzer als Implementierung beschlossen. Nur Dokumentation ergänzt,
  keine Geräte-, Dienst-, Fahr- oder Trainingsaktion.

## Zusätzliche 3D-/6D-Teacher-Beispiele für BC, 2026-11-17

- Neuer Nutzerauftrag: mehr Teacherbewegungen mit gleichzeitiger Translation
  und Rotation um mehrere Achsen. Frage nach getrennten Translations-/Rotations-
  und Mischnetzen bleibt eine Abwägung, keine festgelegte Netzarchitektur.
- Empfehlung: gemeinsame6D-Policy; reine3D-Translation, reine3D-Rotation und
  gemischte6D-Referenzen als getrennte Aufgaben-/Auswertungsklassen. Auch eine
  reine Drehreferenz kann Positionskorrekturen benötigen. Kein Netz trainiert.
- Implementiert reproduzierbarer32Aufgaben-Pilot aus16Familien×2Varianten,
 8Translations-/8Rotations-/16Mischaufgaben; vorab festgelegte16/8/8Aufgaben
  inTrain/Validierung/Test, naheVariantenbleibenzusammen. KleineStartposevariation,
  nichtparalleleZiel-/Auslenkungsrotationsvektoren, alleaktivenAchsenvariiert.
- Neue CLI `tools/generate_teacher_dataset.py`, Reviewer/Galerie
  `tools/review_teacher_dataset.py`; Anleitung docs/teacher_dataset_6d.md.
  NurzeitlichundamExportrastergeprüfteBahnenliefernje100geometrischeBC-Übergänge
  (Δs=0,01),52D-BeobachtungmitReferenzausblick und6D-Weltposeaktion. Keine
  LehrerkorrekturimReferenzeingang, keine100Hz-/Geschwindigkeitsaktion.
- VollständigerOfflinebatch `pilot02` unter
  `setup/research/two-arm-teacher-dataset-20261117/` abgeschlossen:
 21/32gültig (Translation8/8,Rotation5/8,Mischung8/16), zehnReferenzenkorrigiert
  (neunFCL-Kollisionen,eineAbstandsverletzung),elfReferenz-IK-Fehlererhalten.
 2.100BC-Übergänge; akzeptiertTrain12/Validierung5/Test4ganzeBahnen.
  ReineDrehaufgabenbenötigen9,5–21,1mmTranslationskorrektur, größteMischkorrektur
 46,4mm/11,3°. Endposenfest, Zwischenreferenzenweich.
- Abdeckungnochlückenhaft: reineRotationimpositivenTestsatzleer, gültige
  Mischtestbahnenbereitsfrei. NeueKorrekturenbetreffenKarton/Umgebung;
  Referenz-Armhüllabstandmindestens196,4mm, keineengenArm/Arm-Begegnungenim
  neuenPilot. Früherer−100°Fallbleibtseparat. NochkeinbelastbarerTrainings-
  oderGeneraliserungsnachweisfürArm/Arm-Kollisionsvermeidung.
- 48.859Zeitprüfpunkte≤5msund2.121ExportzuständePASS,201,48mmminimaler
  Armabstand/3,611mmKartonumwelt/107,87mmKartonarm. Exportauditmitunabhängiger
  Aktions-/Beobachtungsrekonstruktionund20.001AbleitungsprobenjeBahnPASS.
  Buildund15TestsPASS, Wiederaufnahme32/32erkannt,309BrowserchecksPASS,
  Screenshotvisuellgeprüft. viewer.html/summary.json/export-audit.json.
  Höchstens2CPU-Worker/niceness10/BLAS1; keinNetztrainiert.
- FrüherLauf `pilot01` wegenzuweiterVersionsbindungabgebrochen: parallele
  Änderungvonunbenutztemhardware_state.py. ZehnpositiveEinzelfällehistorisch
  erhalten, nichtinpilot02übernommen. NeueBindungauf19tatsächlichrelevante
  Planungs-/Modellquellen, Quellen-/Szenen-/Meshbindungweiteraktiv.
- Arbeitsstand work/teacher-dataset-6d.md. KeineGeräte-/ROS-/Dienstaktion;
  festeBasen/Griffe, hypothetischstarreoffeneGreifer, linkerArmzustandgeparkt.
  KleinePilotmengekeinGeneraliserungsnachweis; vollständigePolicy-Rollouts,
  weitereAufgabenfamilienundvariableSzenenbleibenspäter.

## right_front-RT-Stopptest vorbereitet,2026-11-17

- NutzerbeauftragtVorbereitungamvorderenrechtenArm192.168.8.103. KeineBewegung,
  keinReset/Play/Power/Brake/Greifer-/StopkommandoindieserArbeit.
- Bestehenderhardware_stop_probe: nurq6max+0,03rad,0,003rad/s/0,006rad/s²,
  Stoppnach80msbestätigterBewegung/0,5mradVersatz. KeineRückfahrt/Auto-Reset.
  OptionalerRTDEOutputfrequencyparameter1–500Hz(Default20weiterfürGuard),
  Probezeitfenstertriggertauchbei500Hz. OfflineauswertungtrenntGeschwindigkeits-
  abfall/Niedriggeschwindigkeit/nachAnforderungzurückgelegtenWeg/Holdbestätigung.
- LesendeVorprüfungall4RUNNING/NORMAL/stationär; RFtatsächlich500Hz,
  Geräteschritt2ms, Empfangslückemax2,788msüberca1s. ModellplanPASS(q6+0,03,
 18,75snominal),FCL/Greiferöffnungshüllen/Paarreservevorhanden. Momentaufnahme,
  vorAusführungIststart/Arbeitsbereich/Übergabefrischprüfen.
- Artefakte setup/realtime/right-front-stop-20261117-02/{plan.json,preview.html,
  native-state.json,preparation.json,manifest.json}. ErsterFall01vorNativezugriff
  amrelativenModellpfadgescheitert,korrigiert. Toolprepare_right_front_stop_test.py
  ausschließlichlesend; keinService/Action/Controllerwechsel.
- VorhandenerSchutzdienstbeiPrüfungmonitor-only. Nichtumgestellt; spätere
  tatsächlicheSchutzfreigabeseparatabstimmen. ParalleleHardware-/OAK-Arbeit
  erhalten.235MotiontestsHostPASS/BuildPASS; initialSocket-Fakeservertestdurch
  Sandboxblockiert(234PASS1FAIL),danachkompletterLoopbackfähigerLaufPASS.
- Bedienung/nochkeineAusführungsfreigabe:docs/right_front_realtime_stop_test.md,
  work/right-front-realtime-stop.md. KeineRT-Bremsgrenzequalifiziert.

## Kalibrier-Aufnahmestellungen: Reserve geklärt, noch keine Fahrt, 2026-11-17

- Nutzer bestätigt feste OAK und freien Vierarmbereich. Alle4URs danach
  RUNNING/NORMAL, ros.urpPLAYING/Reverse verbunden; vorhandene Treiber erhalten.
  Vier CollisionHold-Regler inaktiv provisioniert; Schutzdienst MONITOR ONLY.
- Frischer kompletter FCL-Start kollisionsfrei, aber freie hintere
  Hüllenoberflächen nur133,50mm auseinander. Standardprofil verlangt172,90mm:
 40mm Modellreserve +30,09mm Takt/Datenalter +100,31mm angenommene1sReaktion
  +2,51mm angenommene Bremsung. Radien bereits abgezogen, Wert nicht gemessen.
- Nutzer widerspricht zusätzlicher17,3cmReserve bei großen Hüllen. Herkunft
  erläutert; keine Hüllengröße als neue Stoppmessung ausgegeben. Zusätzlichen
  langsamen Trennweg zunächst zurückgestellt, keinerlei Fahrziel gesendet.
- Offlinealternative mit Kommando0,004/überwacht0,006rad/s erfordert bei sonst
  gleichen Annahmen119,14mm. Erste Sichtstellung links vorne vollständig geprüft,
  aber1196,75s; übrige serielle Pläne noch in Berechnung. Nutzer zu sehr langsamer
  Fahrt versus zuerst konkreterer Reserveberechnung gefragt. Keine solche neue
  Reserveberechnung oder geänderte physische Stoppqualifikation behaupten.
- Belege setup/calibration/oak_recalibration_20261117/motion/ und
  motion-planning-slow.log. Bestehende Kamera-GUI weiter offen/Fokus107.

## OAK nach bestätigter Neumontage geprüft, 2026-11-17

- Nutzer bestätigt neue Montage. Letzter Bildausschnitt passt für weitere
  Kalibrieraufnahmen: beide Tische/Zentrum sichtbar, unten mehr Rand. Diese
  Montage vorerst beibehalten; Höhe nicht gemessen. Frühere Empfehlung einer
  zusätzlichen Abwärtsneigung bezog sich auf den ersten15:10-Ausschnitt.
- Neue native8K-Prüfungen: Fokus116 im ersten Ausschnitt rechts13/links0Ecken;
  Autofokus107 im späteren Ausschnitt rechts24/links15; fester100 im ähnlichen
  späteren Ausschnitt rechts19/links8. Montage und Fokus änderten sich zwischen
 116/107, deshalb keinen isolierten Fokusvergleich daraus behaupten.
- GUI wieder offen mit vorläufig festem107 und datensatzlokalem Aufnahmeprofil.
  Factory-Intrinsics bei116 sind für107 noch nicht validiert; neue Sitzung
  kennzeichnet bisherige Registrierung nach Stativbewegung als historisch.
  Kein globales Profil geändert und keine Kalibrierung aktiviert.
- Quellen setup/oak4/photos/{20261117-151025-standard-6bc0b63c,
  20261117-151245-standard-15690ce1,20261117-151413-standard-f8e7dbe9}/;
  Messübersicht setup/calibration/oak_recalibration_20261117/remounted/.
- Ursprünglich gewünschte vier Aufnahmestellungen noch ausstehend. Vorher
  Rückmeldung über feste Montage/freien Bewegungsbereich erfragt, weil Personen
  im Prüfbild direkt hinter den Tischen stehen; danach frische Hardware-/Wegprüfung.
  In dieser Sicht-/Fokusprüfung keine UR-Schreibbefehle.

## UR-Echtzeitthreads nach Nutzerstart bestätigt,2026-11-17

- Nutzer hat Treiber gestartet. Alle4UR-Treiberdiensteactive; actual
  ros2_control_nodePIDs26053(LF)/26312(LR)/26571(RF)/26824(RR).
- ProTreiberje2ThreadsmitSCHED_FIFO(policy1)/Priorität50 direkt amHost
  nachgewiesen; tatsächlicheProzesslimitsrtprio99/99,memlockunlimited.
  Kernelweiter7.0.0-43-realtime,/sys/kernel/realtime=1.99istRechtobergrenze,
  keineVorgabealleThreadsauf99zusetzen. Reverse-VerbindungenimStartjournalalle4.
- Ausschließlichlesend,0Robot-/Dienstkommandos. KeineLatenz-/Bremsqualifikation
  oderÄnderungderWächtergrenzen. VorigerBefund„Treiberinaktiv“istüberholt.
- Nachweise setup/realtime/postboot-20261117/ur-driver-threads.json und
  ur-realtime-startup.json; docs/realtime_preparation.mdaktualisiert.

## Zweiarm-Lehrer für Behavioral Cloning: erster Beispielsatz geprüft, 2026-11-17

- Nutzer bestätigt BC und Reihenfolge: zuerst Lehrer und gute Beispiele,
  anschließend Training. Bewegungen voraussichtlich ähnlich (Nutzerannahme).
  Neuer Einstieg zwei Arme an kurzen Kartonseiten; insbesondere Orientierung
  variieren. Montageziel: zwei Arme Teil1, dritter Teil2, vierter Werkzeug.
- Offlinearbeit: work/two-arm-object-teacher.md. Beide rechten Arme
  erreichen x_min/x_max des404×342×163mm-Kartons. Andere Arme bleiben im
  Modell aufrecht/stationär. Korrekturen inXYZ und3DRotation, feste Griffe,
  gemeinsames12Gelenk-Zeitgesetz; keine Hardware-/Kontaktphysikaktionen.
- Erste Referenzproben und verworfene Korrekturen zeigen zusätzlich zu
  Armabständen Objekt/Tisch- und Objekt/Unterarmkollisionen. Diese Abstände
  sind als eigene Optimierungsbedingungen ergänzt, FCL bleibt Endprüfung.
- Implementiert `two_arm_teacher.py`, CLI `tools/plan_two_arm_teacher.py`,
  unabhängiger Verifier und englischer Vorher/Nachher-Viewer. Bestehender
  ObjectTransport jetzt selektierbare Greifgruppe, DefaultvierArme erhalten.
  Sechs6D-Splinekontrollen, feste Endpose, Trust-Region/SQP mit deterministischen
  Hub-/Rotationsinitialisierungen; analytische Paar-/Objektarmgradienten,
  numerische Objekt/Umgebung-Quadergradienten. Lokaler begrenzter Lehrer.
- Ergebnis `setup/research/two-arm-object-teacher-20261117/run02/`: drei gültige
  Beispiele ausvierAufgaben, zwei ursprünglich kollidierende Referenzen korrigiert.
  FreierZielversatz(10,3,1)cm+35°Yaw unverändert4,863s.−100°Welt-Y-Zwischen-
  drehung: Armabstand5,17→109,78mm, maxKorrektur50,40mm/26,06°,20,353s;
  erreicht ungefähr−74°, Zwischenreferenz istweich. +70°Fall: max30,58mm/0,98°,
 18,482s. BeideDrehfällekehrenzurStartposezurück, Endposeimmerfest.
  +100°Yaw ohneTranslation scheitert anRR-IK, keinUnlösbarkeitsbeweis.
- AkzeptierteInterpolanten974/4072/3698Samples≤5msPASS; Objekt-/Umwelt-/Selbst-
  FCL, alle6Paare,3mmObjekthüllabstand,20mmArmabstand, starreGriffe und
  v/a/j0,45/0,4/2geprüft. NumerischerGriffschluss≤1,45e−9m/1,35e−9rad,
  keinephysischeGenauigkeit. GeparkteArmeunverändert. Referenzfehlererhalten.
- Build/28Pythonprüfungen, alterVierarm-Verifier,80Browserchecks undvisueller
  ScreenshotPASS. UnabhängigeFDmaxK/Paar/Objektarmfehler5,51e−11/5,36e−10/
 4,01e−10; sechsNächstfeaturewechsel separatprotokolliert, festeFeature-
  Ableitunggeprüft, keineeindeutigeMinableitungbeiBindungbehauptet.
 20.001AbleitungsprobenjeakzeptiertemFall undnegativeObjekt/TischprüfungPASS.
- Grenzen: hypothetischstarre/offeneGriffe,8cmhöhererInitialzustandkein
  Pickupnachweis, festeBasen, teilweisenurvisuelleModelldetails, konservative
  Hüllquader, diskretePrüfung, keineStopp-/Kraft-/Hardwarequalifikation.
  OptimierungEinzellauf86,4/80,1s, keineLaufzeitstatistik/globaleOptimalität.
  Noch kein trainiertes Netz und keine allgemeine Lehrerqualifikation.
  Nächster Schritt: ganzeStart-/Ziel-/Drehfamilien fürDatengeneration definieren
  undTrain/Test nachFamilientrennen. Anleitung docs/two_arm_object_teacher.md.

## OAK-Pose erneut beurteilt / Fünfkamera-Feedback,2026-11-17

- Nutzer vermutet fremde Stativbewegung und beauftragt zuerst Posebeurteilung,
  danach4UR-Aufnahmeposen und5Kamera-GUI; deutlichere Aufnahmezustände/Zähler.
  VorherigeChatvolltexte nicht direkt verfügbar; lokale Übergaben ausgewertet.
- FrischesStandardfoto14:04,Fokus116,native8000×6000:
  setup/oak4/photos/20261117-140400-standard-f9d95b9e/. Rechts24/24Ecken,
  links0/24. Gute zentrale Übersicht, fernesBoard klein/unscharf. Keine aktuelle
  gemeinsameKalibrieransicht. Empfehlung höher(max2m), steilerzurMittebeiderTische;
  Fokus zusätzlich prüfen. Alte v3-OAK-Pose bleibt historischevorläufigeReferenz,
  nichtalsnachBewegunggültigbestätigt; keinProfilüberschrieben/aktiviert.
- NeueGUI: großer dauerhafter RECEIVED/RUNNING/DONE/FAILED-Banner, HOLD STILL
  bisBackendabschluss, laufendeFotozahl, getrennteZähler fürvollständige/
  verwendbareSätze/Einzelbilder/Review, letztesErgebnisbleibtnachLive/Pause.
  GleichbleibendeBildfeldgrößen verhindernWachstum/VerdrängunguntererFeeds.
  12gezielteTestsPASS inklusiveLivebild-Layoutregression; diff--checkPASS.
- EigeneKamera-GUI sichtbar: uwa-oak-recalibration-view-20261117.service,
  mobile38mmReferenz, alle4Wrists+OAK, keep-camera-settings, RTDE nurlesend.
  Diagnose/UI-Belege setup/calibration/oak_recalibration_20261117/.
  EswurdenkeineKalibrierfotosetsoderArmfahrtenausgelöst.
- ErsteAbfragealle4URsRUNNING/NORMAL, Abschlussabfragelesendalle4POWER_OFF/
  NORMAL, ros.urpSTOPPED, lokaleTreiber/ReverseLinksfehlen; eigenecommands[]leer.
  Kameramontage/Rückmeldungnochabzustimmen; danachfrischeZustände,Wegprüfung
  undbeauftragteAufnahmeposen. KeinealtenAusführungspläneungeprüftwiederverwenden.

## Echtzeitkernel nach Nutzerneustart bestätigt,2026-11-17

- Nutzer meldet Neustart; ausschließlich lesend geprüft, keine Dienst-/Roboter-
  Aktion. Aktiv7.0.0-43-realtime, /sys/kernel/realtime=1, CONFIG_PREEMPT_RT=y.
- Tatsächliche aktuelleSitzung undBenutzermanagerPID6118: rtprio99/99,
  memlockunlimited/unlimited. NeueSystemrechtealsoaktiv,nichtnurzurInstallation
  vorgemerkt. Boot-IDundNachweise setup/realtime/postboot-20261117/verification.json.
- Alle4UR-Treiberdiensteinactive/MainPID0, keineControllerthreads. Daher
  tatsächlicheUR-FIFO-Prioritätennochungeprüft. KeinautomatischerStart allein
  ausStatusfrage. Echtzeitlatenz-/Bremsmessungweiteroffen.
- VorigerAbschnitt„NeustartwartetaufNutzer“isthistorischerInstallationsstand;
  NeustartinzwischenvomNutzerdurchgeführt. Fallkernelweitererhalten.

## Lernbasierter Objektplaner als Vergleich: Einschätzung, 2026-11-17

- Nutzer nimmt Lernverfahren als Vergleich wieder auf: gewünschter Objektversatz
  bzw. kurzer Zielhorizont und MRS-Zustand sollen gemeinsame nächste Schritte
  bestimmen; Optimierungslösungen als Lehrer. Festes Objekt/feste Griffe als
  Einstieg, Architektur und RL ausdrücklich noch offen. Nur Konzept/Literatur.
- Originalgespräch im lokalen Rollout vom16.11.,14:10:45 gelesen (Offlineumfang,
  Starrverbund, minimale Profilabweichung, Jacobimatrix/Gradienten), außerdem
  aktuellen Offline-Transportstand. Keine vollständige externe Chathistorie behauptet.
- Technische Empfehlung, noch keine Nutzerentscheidung: zentralisierte Policy
  im Objektraum, zunächst Behavioral Cloning und DAgger-artige Datenkorrektur;
  kleine MLP-Baseline, später multimodale kurze Bahnsegmente. Gemeinsame IK,
  Kettenbedingungen, geometrische Endprüfung und gemeinsames Retiming erhalten.
  Greifmatrix reicht nicht; q, Objektpose/Ziel, bei Variation Basis-/Umweltzustand
  und gegebenenfalls Geschwindigkeiten/Referenzphase berücksichtigen.
- Aktueller Lehrer optimiert nur Yaw entlang fester Translation. Für allgemeine
  XYZ-/Rotationsausweichbewegungen zunächst Lehrer erweitern und schwierigere
  Aufgaben generieren. Bestehendes Idealprofil war bereits frei; Zusatzabstand
  ist kein Nachweis geretteter Kollisionsfälle. Kein Netz trainiert/getestet.
- Literatur: Neural MP, Motion Policy Networks, Ha et al. Multiarm-SAC+BiRRT,
  MPD und IROS2025 Hierarchical Framework for Constrained Dual-Arm Cooperative
  Manipulation (letzteres hier nur Abstract/Einleitung zugänglich). Abgrenzung
  freie Mehrarmziele vs. starre geschlossene Ketten beachten. Details/Quellen im
  letzten Abschnitt von docs/mobile_multiarm_planning_survey_2026-11-16.md.
- Vorgeschlagener Benchmark: Optimierer, Netz+Prüfung, Netz+Korrektur+Prüfung;
  rohe Fehlerrate und Korrekturaufwand sowie gesamte Plan-/IK-/Prüfzeit messen,
  Train/Test nach ganzen Aufgabenfamilien trennen. Kein Leistungsnachweis bisher.

## OAK-Neuregistrierung vorbereitet / Kameraeinstellungen behalten,2026-11-17

- Nutzer hält OAK-/Stativbewegung seit12.11.fürmöglich, Tischboards/Tische eher
  unverändert; neueKalibrierung gewünscht/angeboten. Mobiles38mm-Brett verfügbar.
  GuteFokus-/Belichtungseinstellungen dürfen laut neuer Präferenz bestehen bleiben.
- DreiOAK-Aufträge ergeben statischeBoard-Wiederholbarkeit0,599mm/0,0271°, aber
  Prüf-RMSbis2,098pxgegen1px weiterhinFAIL. NeueOfflinewerkzeuge speichern explizit
  Diagnosekandidat, keinekalibrierteWeltpose/Profilaktivierung/Hardwarefreigabe.
- SichtbareZweikamera-App OAK+RF, `--keep-camera-settings`, eigeneAufnahme unter
  setup/calibration/carton_oak_reregistration_20261117/. NutzerstelltmobilesBoard
  für unabhängige gemeinsame Fotos bereit; Armegehalten, Greiferoffen. Anleitung
  docs/three_camera_capture.md, Details work/carton-hardware-commissioning.md.
 26gezielteKamera-/RegistrierungstestsPASS. Keine weitereArmfahrt/keinKontakt.
- Letzter13:42Nativecheck: alle4stationär/RUNNING/NORMAL, ProgrammeSTOPPED;
  beideGreiferoffen. Schutzdienst13:27aufHardware-/Managerfrischeausgelöst,
  alle4Holdsbestätigt/Watchdoggelatcht; GuardentscheidungenimkurzenTracefehlend.
  KeinReset/PLAY. VorneuerArmfahrtFrischeursacheklären; FotoreihebrauchtkeineFahrt.

## Realer Kartontest: RF-Anfahrt bestanden, Bildabgleich fehlgeschlagen,2026-11-17

- Nach ausdrücklicher Freigabe unbeladener Schutzprofilwechsel RF allein mit
  Kommando0,015rad/s/Monitor0,03 in geprüfte150mm-Vorposition gefahren. Andere3
  gehalten; abschließend RF-Hold/Latch und unabhängige Ruhe bestätigt.4250native
  Samples/212,448s, Istmaximum0,0169364rad/s, Bahnabweichung0,000133567rad.
- Frisches OAK-Foto zeigt deutlichen seitlichen Kartonversatz. Kein Absenken,
  RR-Ziel, Greifen oder Hub; Greifer offen/MONITOR ONLY, alleArmegehalten.
  Tischboarddiagnose erklärt plausibel etwa6,29° Fehler der vorläufigen alten
  Kameraregistrierung. Heldout2,087px besteht1px-Kriterium nicht; keine neue
  Kalibrierung aktiviert. Beide historischen rechten Boardfits widersprechen
  nominalen Front/Rear-Basen um etwa54mm. Unabhängige Wrist-Prüfung aktiv.
- Reale Quelle: setup/tasks/carton_hardware_rf_approach_20261117_01/, Details
  work/carton-hardware-commissioning.md. Alte Anfahrtstartzustände überholt;
  nächste Planung muss von tatsächlicher angefahrener RF-Stellung ausgehen.
  Transportfreier Objektmaster ist weiterhin kein gekoppelter Hardwareexecutor.


## Vierarm-Objekttransport mit Yaw-Gradienten, 2026-11-17

- Nutzer beauftragt Umsetzung und wählt Richtung anhand Erreichbarkeit.
  Aus letzter Seitenmitten-Endstellung hypothetisch feste FK-Grifftransformationen;
 10cm Hub,20cm Versatz, waagerecht,±15°Yaw als erster Versuchsrahmen.
  Welt−X besteht kontinuierliche IK und Geometrieprüfung;±Y/+X scheitern an
  dieser IK-Fortsetzung. Keine globale Nichterreichbarkeit anderer Richtungen.
- Neue Offlinewerkzeuge `tools/plan_object_transport.py`,
  `tools/verify_object_transport.py`, Modul `object_transport.py`; Anleitung
  `docs/offline_object_transport.md`. Gemeinsam24Gelenke,3C3-Phasen mit Halt
  an den Profilknicken. `smooth_paths.curve_bounds` auf beliebige Gelenkzahl
  erweitert; Regression prüft ausdrücklich limitierenden24.Gelenkkanal.
- Endartefakt `setup/research/offline-object-transport-20261117/final/`:
  Idealprofil17,532s, minArmabstand32,676mm, Yaw0°, minskalierteArm-σ0,08878.
  Bereits gültig, deshalb unverändert. Getrennter Zusatzversuch fordert
 20+40sin²(πs)mm:19SLSQP-Iterationen mit analytischen Paargradienten,
  maxYaw6,017°,15,332s, minAbstand31,321mm, minArm-σ0,13015;
  verbleibender Abstand über variabler Forderung mindestens0,499mm.
  Mittelpunktbahn/Endpose unverändert; der global kleinste Abstand ist kein
  geeignetes Maß für diese entlang des Weges unterschiedliche Zusatzforderung.
- Beide tatsächlichen Interpolanten geprüft in≤5ms/3510bzw3070Samples:
  bewegtes Kartonmesh gegen vorhandene FCL-Geometrie, Selbst-/Umweltkollision,
  alle6Arm-Hüllpaare, Gelenkgrenzen und starreTCP-Offsets PASS.
  Numerischer Griffschlussfehler≤2,47e−9m/1,50e−11rad; keine physische Genauigkeit.
  Analytischev/a/j-Grenzen Ideal≤0,275/0,400/1,210 undYaw≤0,294/0,400/1,556
  (rad/s,rad/s²,rad/s³), zusätzlich dichte Ableitungsauswertung.
- Unabhängige finiteDifferenzen an Start/Mitte/Ende beider Fälle: maxK-Fehler
 2,63e−9, maxAbstandsgradientfehler1,97e−9. Absichtlich20mm abgesenkter
  Karton wird als Tischkollision erkannt; Rücksetzen wieder frei. Unveränderte
  Bahn verletzt Zusatzforderung an97/241Samples. Frühere61-Punkt-Optimierung
  ohnePuffer scheitert feinerPrüfung; negatives `optimization-0.04.json` bleibt.
  Final121Optimierungspunkte und0,5mmPuffer, danach unabhängiges Zeitraster.
- Lyrical-Paketbuild und35Tests in5gezielten CTest-Suiten PASS. HTML-Browserprüfung28Checks
  PASS, kontrollierterScreenshot; Viewer beider Varianten mitPlay/Pause/Slider,
  Echtzeit, Orbit/Zoom, Abstands-/Yaw-Kurven. Logs `setup/logs/uwa-object-transport-*`.
- Grenzen: offeneFinger/hypothetischeGriffe, festeBasen, nominal3mmTischspalt,
  kein tatsächliches Absetzen/Tragen/Last-/Kraftnachweis, keineROS-/Hardwareaktion.
  AlteStoppreservediagnostik bei allenSamples überschritten; getrennt sichtbar,
  nichtgeometrischeKollision. DiskretePrüfung, keine kontinuierlicheGarantie.
  Skalierte Einzelarm-σ sind heuristischeKinematikindikatoren, keine umfassende
  Parallelroboter-/Lastsingularitätsqualifikation. Translation/IK-Zweigwechsel
  nochkeineOptimierungsvariablen; Umwelt/Objekt/Singularität nurAbnahmekriterien,
  derzeit nurArm-Paarabstände differenzierbareOptimierungsconstraints.

## Objekt-Jacobimatrix und Abstandsgradienten, 2026-11-17

- Nutzer bestätigt Objektbahnplan/erste5Schritte, stellt lernende Verfahren
  zurück und fragt nach gezielten Gradienten/Singularitätsüberwachung. Konzept
  präzisiert: J_i qdot_i=A_i V_O, bei regulären6R-Armen K=stack(solve(J_i,A_i))
  als24×6Objekt→Gelenk-Abbildung. Für Armkörperabstand grad_X d=K^T grad_q d.
  Singularität über skalierte Einzelarm-Jacobians, Richtungsverstärkung und
  vollständige Kettenbedingungen betrachten; beliebige24D-Nullraumbewegung unzulässig.
- Geometriecode SphereModel.jacobians liefert bereits analytische Punkt-Jacobians.
  Kleiner Offlineprobe an letzter Vierarm-Seitenendstellung: hypothetisch feste
  TCP-Offsets aus FK, Weltrotation um Kartonmittelpunkt, alle6Paargradienten.
  Analytische Kettenregel gegen zentraleIK-Differenzen bei1e−4/1e−5 geprüft:
  maxGradientfehler1,60e−9/3,11e−11, maxK-Fehler2,17e−7/2,23e−9;
  keine wechselnden nächstgelegenen Kugelpaare in diesen Stencils. PASS.
- +1°Welt-Z-Rotation: rechtesPaar Abstand etwa66,0→62,6mm, prognostizierte
  Änderung−3,388mm, erneutberechnet−3,380mm. Lokale Sensitivität, keine
  kollisionsgeprüfte Objekt-/Tischbewegung. Fest amObjekt gekoppelte Greifer-
  Teilkörperabstände sind invariant (Gradient≈0); das ist kein Solverfehler.
- CharakteristischeLänge0,5m nur zurEinheiten-Normierung: skalierte minSingulär-
  werteLF/LR/RF/RR0,300/0,284/0,297/0,351; keine physische Schwellenqualifikation.
  DifferenzielleConstraintmatrix24×30 hat Rang24 in dieserProbe.
- Artefakte setup/research/offline-object-gradients-20261117/{probe.py,result.json},
  Log setup/logs/uwa-object-gradients-20261117.txt. KeineROS-/Hardwareaktion,
  zu diesem Zeitpunkt nochkeinVierarmtransport (nunobenimplementiert). Survey umGradienten, SQP/Trust-Region,
  TSR-Abgrenzung undTrajOpt-Primärquelle ergänzt.

## RT-Kernel installiert / Neustart wartet auf Nutzer,2026-11-17

- ExpliziterFolgeauftrag:KernelinstallierenundUR-Echtzeitrechteeinrichten;
  NutzerkündigtNeustartbereitschaftspäteran. InstallationerfolgreichohneReboot,
  ohneTreiberneustart/Robotkommandos. LaufenderKernelweiter7.0.0-43-generic.
- Ubuntu-Realtime1.1.3/linux-realtime7.0.0-43.43.1/rt-tests2.9-1ubuntu1
  installiert. PREEMPT_RT=y,Initrd/GRUB-PrüfungPASS, normalesUbuntu-Bootziel
  jetzt7.0.0-43-realtime durchPaket-Flavourorder; Generic43/42erhalten.
  SecureBootaktiv, RTundGenericgleicheCanonicalSigning2022v1-Kette;
  tatsächlicherBootnachweisweiterausstehend. dpkgAuditohneBeanstandung.
- PAMDatei99-uwa-realtime.confbenutzerspezifischrosmatchrtprio99/memlockunlimited.
  Systemmanagerdropinuser@1000.serviceundvierUR-TreiberdropinsmitgleichenLimits
  persistentinstalliert, DaemonreloadohneRestarts. FrischePAM-Sitzung99/unlimited
  geprüft. LaufendevierUR-ProzessePIDs13780/14185/14464/14787unverändertmitalten
  Limits0/8MiB; volleWirksamkeitnachNeustart/erneutemTreiberstartprüfen.
- KeineFIFO-PolicyfürkomplettePython-/GUI-Prozesse, keineFrische-/Brems-/Rate-
  ÄnderungandenrealenWächtern. ParalleleHardwarequelländerungenerhalten.
- Logs/Backup/Manifest/Verification:setup/realtime/installation-20261117/;
  vollständigeBedienung/Rückfall/Nachstartprüfungdocs/realtime_preparation.md.
  **KeinNeustartbisNutzerbereit.**

## Konzept für vierarmigen starren Transport, 2026-11-17

- Neuer Nutzerwunsch: nach Griff ohne Loslassen20cm seitlich umsetzen; minimale
  Abweichung vom Pick-and-Place-Profil, Orientierung als erster Ausweichhebel,
  bei Bedarf räumlicher Umweg. Konzept-/Literaturfrage, noch kein Transportlauf.
- Modell: vier geschlossene6R-Ketten mit starren Objekt→TCP-Transformationen;
  bei festen Basen und regulärer Kinematik lokal6 Bewegungs-DOF des Objekts,
 24Antriebe bedeuten keine18 freien Gelenkbewegungen. IK-Zweige kontinuierlich
  verfolgen, neue Zweige vor Griff wählen; bewegte Tische ergänzen Basis-DOF.
- Architekturvorschlag (noch nicht implementiert/qualifiziert): Referenzbahn
  anheben/versetzen/absetzen; zuerst feste Translation mit Orientierungsfreiheit,
  dann erweiterter Positionskorridor, zuletzt globaler constrained Samplingplaner
  +lokale Optimierung. Harte Griff-/Kollisions-/Gelenkconstraints, danach ein
  geglättetes gemeinsames Zeitgesetz über alle24Gelenke. Endorientierung fest.
- Vorab gemeinsamen Zielarbeitsraum und kontinuierlichen Transport aus der
  Greifkonfiguration prüfen; bisherige kürzeste Anfahrt allein reicht nicht.
  Aktuelle Vierarmvorschau endet offen und begründet keinen realen starren Griff.
  Objektgeometrie muss mitbewegt, nur beabsichtigte Padkontakte ausgenommen werden.
- Lokaler Code gelesen: GraspGroup in uwa_cell_tasks/core.py und Compiler
  object_trajectory in planning.py haben bereits Objektbezug/gemeinsame Zeit,
  sind auf rechtesPaar zugeschnitten und interpolieren vorgegebene Objektwege;
  automatische Vierarm-Umwegoptimierung fehlt. Transportfreier Hardwarekern
  hardware_object_reference.py ist kein ausführbarer Hardwareplan.
- Primärquellen ergänzt im bestehenden Survey: CBiRRT/TSR2011, AtlasRRT2013,
  driftfreie constrained Collocation2023, payload-aware mobile Manipulation2024,
  Kraft-/Zeitoptimierung2024, VAE-MPPI2026 (nur Dual-Panda-Simulation).
  DG-MAP2025 löst freie Armkonflikte, kein fertiger Starrverbundplaner.
  Vorschlag: deterministische Objektbahnoptimierung als Hauptweg, constrained
  Sampling als Vergleich/Fallback, gelerntes Sampling+Projektion später optional.

## Seitenmitten-Anflug und Glättung als Standard, 2026-11-17

- Nutzer übernimmt Glättung als Standard für Offline-Anfahrbeispiele und
  beauftragt vier eindeutige Seitenmitten statt Ecken. Neue Pipeline
  tools/plan_carton_grasp_paths.py liefert standardmäßig geglättete, erneut
  geprüfte Trajektorien; Primitive/10×-Fall bleiben als Vergleich erhalten.
- Gemeinsame Zuordnung unter je zwei nächsten Seiten nach horizontaler
  Basisdistanz: LF→A/x_min (Rang1), LR→D/y_max (Rang2), RF→C/y_min (Rang2),
  RR→B/x_max (Rang1). Minimale Distanzsumme, keine Zeitoptimalitätsaussage.
  120 mm Anflug von oben, TCP15 mm unter Oberkante, Backen quer zur Wand.
- Negative Vorversuche erhalten: greedy verdrängte LF auf Rang3/keine IK
  (`primitive/`); ursprüngliche Bremsreserve verwarf sämtliche 20.736
  Endkombinationen (`case02/`). Aktuelle Offline-Auswahl explizit static_margin:
  volle FCL-Szene und 20 mm für alle sechs Paare. Reservediagnose unverändert
  separat; kein Verändern aktiver Hardware-/Simulationsgrenzen.
- 12 IK jeArm, 315 gültige Endkombinationen, 10 Einzelwege, 36 kompatible
  Wegkombinationen; gewählt goal-0-2-3-0. Begrenzte IK-Menge, keine Vollständigkeit.
  Neue Dauer12,746 s; analytische v/a/Ruck-Obergrenzen0,450/0,400/1,105.
  Max. gemessene TCP-Bahnänderung durch Glättung0,000640 mm nur im Modell.
- 32.008 isolierte Prüfstellungen +1.276 gemeinsame Zeitpunkte≤10 ms ohne
  Kollision/20-mm-Unterschreitung. Dichtere Nachprüfung2.551 Punkte≤5 ms,
  min. Armhüllabstand53,697 mm, max. Gelenkschritt0,002250 rad ebenfallsPASS.
  Unabhängige Zeitgesetzrekonstruktion800.008 PunktePASS (Ruckspitze0,791).
  Reserve weiterhin1.145/1.276 verletzt, auch am ruhenden Ziel wegen alter
  Betriebscap-Untergrenze. Kein Nachweis unter dieser Bremsreserve.
- Build,31 gezielte Tests und20 BrowserfällePASS; Draufsicht/Endstellung visuell
  geprüft. Vollständiger Standardlauf einschließlich NachprüfungPASS, identische
  Trajektorien zur ersten erfolgreichen Auswertung. Daten/Viewer unter
  setup/research/offline-carton-sides-20261117/standard/, Anleitung
  docs/offline_carton_sides.md; Logs setup/logs/uwa-carton-sides-*.
  Nur Offlinekinematik, Basen fest, Greifer offen; keine Kontakt-/Hardwareaktion.
  Diskrete Modellprüfung, kein kontinuierlicher oder physischer Kollisionsbeweis.

## Geglättete Eckanflüge aller vier URs, 2026-11-17

- Nutzer bestätigt alle vier Arme; bisheriges Tempo grundsätzlich okay,
  Geometrie möglichst erhalten, Beschleunigung/Ruck reduzieren. Rein offline.
- Neue quintische Geschwindigkeitsrampen mit Konstantfahrt und C3-Zeitgesetz;
  Gelenkgeraden exakt erhalten. Cartesian-Anflug jetzt quintischer C4-Spline
  durch dieselben IK-Knoten. Maximal gemessene TCP-Bahnänderung 0,000508 mm,
  Gelenkabweichung 1,5911e−6 rad im Modell; keine reale Genauigkeitsangabe.
- Gesamtdauer 22,067→15,995 s (−27,5 %). Analytische Obergrenzen:
  v 0,454584→0,450000 rad/s; a 1,223044→0,400000 rad/s²;
  Ruck 10,085925→1,084747 rad/s³. Gewählte Entwurfsgrenzen 0,45/0,4/2,0,
  keine Hardwarelimits/zeitoptimale Lösung. Zwischenstopp vor Vertikalanflug bleibt.
- Individuelle Zeiten verändern Begegnungen: 32.008 isolierte Prüfstellungen
  sowie 1.601 gemeinsame Zeitpunkte (max. 10 ms) ohne FCL-Kollision oder
  Verletzung der statischen 20-mm-Paarreserve; min. Armhüllabstand 155,147 mm.
  Alle sechs Paare geprüft. Diskrete Prüfung, kein kontinuierlicher Beweis.
  Dynamische Reservediagnose weiterhin 1.297/1.601 verletzt; unveränderte
  Annahmen aus dem 10×-Vergleich, keine physisch qualifizierte Stopphülle.
- Build und 25 gezielte Tests PASS. Unabhängig 800.008 Ableitungssamples PASS,
  Spitzen 0,450000/0,400000/0,835104 unter den Obergrenzen. 15 Browserfälle
  PASS; Darstellung und aufklappbare v/a/Ruck-Kurven visuell geprüft.
- Neue Dateien smooth_paths.py, test_smooth_paths.py, smooth_carton_paths.py,
  preview_carton_smoothing.html; Ergebnis/Verifier/Viewer unter
  setup/research/offline-carton-smoothing-20261117/. Anleitung
  docs/offline_carton_smoothing.md, Logs setup/logs/uwa-carton-smoothing-*.
  Alte Ergebnisse erhalten. Keine Hardware-/Kontakt-/ROS-Knoten-/Dienstaktion.
  Basen fest, Greifer offen, executable:false. Native MoveJ/MoveL-Reproduktion
  des Zeitgesetzes und physische Ausführung bleiben unqualifiziert.

## Echtzeit-/Reaktionskettenvorbereitung,2026-11-17

- NutzerbeauftragtVorbereitungderzuletztgenanntenSchritte. Hostaudit:
  Ubuntu26.04.1/7.0.0-43-generic, PREEMPT_RTaus, Sitzungrtprio0/memlock8MiB.
  APT-Dry-runubuntu-realtime+rt-testsPASS, keinInstall/Neustart/Systemeingriff.
  BenutzerspezifischerLimitsentwurf undRückfallplanin
  docs/realtime_preparation.md; Artefakte setup/realtime/preparation-20261117/.
- SimTaskparameter`simulation_guard_rate_hz`10–100(abweichendnurExploration),
  gleicherWertfürTimerundPlanungsbudget, Default10Hz. Zeit-/Intervall-/Overrun-
  Diagnoseergänzt,25/50/100HzKandidatenvorbereitetnichtlivequalifiziert.
 300Offline-Geometriefällemedian3,552/p994,495/max4,813ms; keinRuntimebeweis.
- Reinlesenderprepare_realtime.py: audit/jitter/record/analyze. RecorderMock67
  PASS(198Guardpakete),0Robotkommandos. KettenanalyseprüftkorrelierteStage-/
  Boot-/Uhrdaten; echteDispatch-/Bremsmessungweiteroffen. VorhandenenHardware-
  InterlocktracederparallelenArbeitwiederverwenden,nichtverändern.
- 20sPythonNormal-Schedulerprobe2ms: p99437µs/max2836µs/5verpassteTermine;
  keineEchtzeitgarantie/keinCyclictest.121TasktestsundTaskbuildPASS. Initiale
  CollectionwegenparallelemneuemuninstalliertemModulfehlgeschlagen,nachBuildPASS.
- Wichtig:350ms/2rad/s²geltenfürKontakt-Sim; realeCommissioningannahmen
 1300ms/0,2rad/s²nichtautomatischändern. KeineHardware-/Kernelaktion.

## Vier Eckanflüge mit zehnfacher Zeitkompression, 2026-11-17

- Nutzer findet Bewegung natürlich und fragt nach10×Trajektorientempo, nicht
  Planungsdauer. Offlineauftrag ausgeführt; keine Physik-/Hardwarefahrt.
  Alte Vorschau hatte20×Wiedergabe (220,7s in11s); neue Vergleichsansicht
  startet ausdrücklich mit10×Trajektorie und1×Wiedergabe, Dauer22,067s.
- Quelle case03 unverändert. Neue gemeinsame Zeitkompression aller vier
  empfohlenen Wege, einschließlich Abschnittszeiten/Ankunft/Warten. Stützstellen
  und Splineknoten identisch; v×10,a×100,Ruck×1000. Neue isolierte Dateien
  path_speed.py, compare_carton_path_speed.py und preview_carton_speed.html.
- Analytische lokale Intervallobergrenzen10×:0,454584rad/s,1,223044rad/s²,
 10,085925rad/s³. Unabhängige dichte Spitzen0,454556/1,153333/10,085924 darunter.
  Alle24URDF-Geschwindigkeitslimits eingehalten; langsames0,05rad/s-/0,1rad/s²-
  Planungsprofil überschritten. Dieses Profil ist kein physisches UR-Maximum;
  keine qualifizierten Hardware-a-/Ruck-/Torque-/Trackinggrenzen daraus ableiten.
-2.208gleich normierte Zeitpunkte jeVariante:0FCL-Kollisionen, gleicher
  minArmhüllabstand155,755mm; Gelenkabweichung bei t/10 nur1,87e−14rad.
  Fast-Diagnose höchstens0,010sRaster, also nicht gröber als vorher0,100s.
- Geschwindigkeitsabhängige Reserve mit ursprünglicher0,05Untergrenze,
 350mszusammengesetzterVerzögerung/0,5rad/s²angenommenerBremsung ausgewertet.
  Nachbarreserveverletzungen423→1.606/2.208; maxPaaranforderung199→1.357mm.
  Momentane Sollgeschwindigkeitsdiagnose, keine realeStopphülle/Qualifikation
  eines erhöhten Betriebscaps oder Beschleunigung während Reaktionslatenz.
  Bestehende Reserve-/Cap-/Hardwarekonfiguration unverändert.
- BuildPASS,16gezielteTests(9neu+7Bahntests)PASS. Unabhängige100.001Punkte pro
  Abschnitt bestätigen Ableitungen/Zeiten/Geometrie.15BrowserfällePASS,
 241paarweise Vorschauzustände identisch,1sWiedergabe=1sModellzeit geprüft.
  Enddarstellung visuell geprüft. Keine Roboter-/Kamera-/Dienstaktionen.
- Ergebnisse setup/research/offline-carton-speed10-20261117/:
  comparison.json,trajectory-10x.json,verification.json,viewer.html.
  Weiterhin executable:false; kein Greifschluss/Hub/Lastnachweis.
  Anleitung docs/offline_carton_speed10.md, Logs setup/logs/uwa-carton-speed10-*.

## Kontakt-Simulation: Reserve-Observe-Modus,2026-11-17

- Nutzerbeauftragt ausdrücklichSimulationsmodusohneerzwungene dynamische
  Reaktions-/Bremsreserve. Implementiert`simulation_stop_reserve_mode: observe`,
  nurmitExploration+Kraftmessung; Default`enforce`. PlanerundGuardgleich;
  modellierteReserve/VerletzungenweiterimTrace, ModusimReview/Status/RViz.
- Geometrie/20mmPuffer, Geschwindigkeit/Kontakt/Schlupf/Frische/Gruppenstopp
  bleibenaktiv; Hardwarepfadeunverändert. AktiveGreifweltenvorÄnderungHost-
  geprüft:keine. KeineHardware-/KernelaktionundkeinneuerDrehphysiklauf.
- BisherigeAnnahmen:10Hz+150msPlan-Zustandsalter+100msStopplatenz=350ms,
  letztesProfil2rad/s². KeinUR-Messnachweis; NutzerwünschtPerspektiveauf
  schnelleresInterface/PREEMPT_RT. Quellen/Formeln/Beispielin
  docs/simulation_stop_reserve_mode.md. RealzeitbudgetsbenötigenEnd-to-end-Messung.
- 103TasktestsPASS/BuildPASS; gespeicherteDrehbahn600Zustände:enforce600
  Reserveverletzungen(min−37,188mm),observe0(min176,277mmüber20mmPuffer).
  AbgetasteterPolicytest,keinPhysiknachweis. Artefakte
  setup/tasks/carton_stop_reserve_mode_20261117/, Logsuwa-sim-reserve-*.

## Karton: rechte UR-Übergabe, ROS-Leerfahrt und Anfahrkandidat,2026-11-17

- Nutzer bestätigt „Jetzt frei“ nach fremdem UR-Test. Frisch lesend: rechteURs
  RUNNING/NORMAL/Remote, ros.urpPLAYING/Reverseverbunden, beidePositionHoldsaktiv.
  Default-FastDDS passt zu aktuellen Managern; erzwungenesUDPv4 lief inTimeout,
  ohne Transportoverride beideControllerlisten erfolgreich. KeinTreiberneustart.
- OAK-Erlaubnis genutzt: native8K/Fokus116 um10:31:25 und11:14:57, Karton amPlatz;
  Kamera nachjeweiligemFoto geschlossen. ErsteEinzelbildpose69Inlier/2,458px,
  vorläufigerWelttransform1,43degNeigung. KeineabsoluteGreifgenauigkeit belegt.
- Neuer transportfreierObjektreferenzkern: eineObjektuhr mit min(nativeScaling×
  targetSpeedFraction), festeGriffoffsets, Quellfrische/Relativprüfung und
  verriegelterGruppenstopp alsAnforderung.14TestsPASS; keineechteIK-/Aktuator-
  Zustellung/Stillstandsbestätigung daraus ableiten. GemeinsamesTaskpaketnichtgebaut.
- OfflineHardware-Anfahrtstool verwendet aktuelleFactorykinematiken/99,1cmLayout,
  Kartonmeshes, vollständigeGreiferöffnungshüllen/FCL undaltePaarreserven.
  DritterFall findetRF-dannRR-Weg in80mmVorposition, beideSegmente≤0,005rad
  nachgeprüft. VorigezweiSuchfehlversucheerhalten; zusätzlichelimitkonforme
  äquivalenteGelenkumdrehungen naheIststellung vermeidenunnötige360°-Wege,
  kartesischeZiele perFKnachgeprüft. KeineZeitplanung/Absenkung/Realtrajektorie.
- GemeinsameGreifer-API einesanderenChats inzwischenverfügbar. Eigenerzweiter
  Adapter anGeräteLeasekorrektabgewiesen,0Goals; Umstellung aufvorhandeneROS-
  Endpunkte. NeuerEmpty-Stroke-Harness standardmäßiglesend; keineSocketwriter.
- **EchteFingerbewegung in diesemChat:** RF undRRjeweils raw0→128→0 überROS,
  einzeln, SPE16/FOR0; alle4Goalsbestätigt, keinKontakt/Fehler. Vorherfrische
  stationäreunbeladeneArmstellunggeprüft. KeinACTIVATE/Armziel/Controllerwechsel/
  Power/Brake/Play/Reset. GemeinsamenDienstfürTestaktiviert, danachzurückMONITOR
  ONLY/caps0und16. KeinFullstroke-/N-/mm-/Fingerstop-/beladenerGriffnachweis.
- Danachalle4nativenArmstreamsstationär, letzteqd0; beideRechtsgreiferoffen
  POS3/PRE0/OBJ3/ACT1/STA3/FLT0/SPE16/FOR0. VorhandeneArmholds/-wächtererhalten.
- Prüfung24FällePASS (14Referenz/10Pregrasp), ROS-Mock67PASS mitkorrigierter
  separaterFOR/SPE-Schreibfolge. RealeTeilfahrt undLeseschnittstellenPASS.
  Hauptdaten setup/tasks/carton_hardware_pregrasp_20261117_03/,
  carton_gripper_ros_empty_stroke_20261117_01/ und
  carton_hardware_post_gripper_20261117_01/; Details docs/carton_hardware_commissioning.md.
- **VollständigerRealgriffweiterhinoffen:** gekoppelterHardware-Kommandopfad samt
  gemeinsamerZeit/IK/Kollisions-/Gruppenstopport, physischerObjekt-/Toolabgleich,
  Kraft-/Öffnungsabgleich/Beladungsprüfung. Historische0,005rad/s-Planidee liegt
  überaktuellem0,003-Wächter; nichtsoausführen oderWächterzumBestehenanheben.
  VorArmanfahrt KommandoboundgegenbeobachteteNativePeaksabgleichen undreplanen.

## Schritt 3: feste Kartoneckziele und glatte Einzelbahnen, 2026-11-17

- Nutzer fand gleichzeitig wechselnde Aufgabenposen/IKs verwirrend; neuer
  Fall: jeder UR von oben an seine nächste Ecke des Avocado-Kartons. Genau
  eine unveränderte Greifpose je Arm, verschiedene Gelenklösungen/Wege dazu.
- Nullstart [0,0,0,0,0,0] modelliert kollidierend: LF-Wrist/Greifer schneidet
  rechten Tisch,12FCL-Kontakte. Nutzer wählt nach konkreter Rückfrage ausdrücklich
  aufrecht [0,-90,0,-90,0,0]Grad für alle4. FCL/Planungsreserven dort PASS.
- Bestehender Karton an bildbasierter Pose/99,1cm-Basislayout lokal als statisches
  Mesh-Hindernis ergänzt. Gemeinsame Szene/unabhängige Arbeiten unverändert.
  Ecke jeweils eindeutig nächster Basis zugeordnet. Nominaler TCP145mm entlang
  GreiferbasisZ,15mm unter oberer Ecke, Z senkrecht abwärts/Schließachse diagonal.
  Annahmen für Geometrieprüfung, kein kalibrierter/tragfähiger Eckgriffnachweis.
- Neuer Modul carton_paths.py und tools/plan_carton_corner_paths.py:96IK-Seeds,
 12behaltene Kandidaten/Arm für feste Ziele,20.736Kombinationen/18gültige Endpunkte.
  Rückwärts-IK120mm nach oben, glatte Gelenktransit-/senkrechte Anflugprimitive,
  C2 mit Stillstand an Übergängen. Bei Fehler optionale Pan-/Faltzwischenpunkte.
- Acht geprüfte Einzelbahnen(2LF/2LR/3RF/1RR),12kompatible Bahnsätze. LR-Kandidat8
  scheitert an allen3versuchten Gelenkrouten; keine Vollständigkeitsbehauptung.
  Einzelprüfszene enthält Selbst/Tische/Kiste/alle festen Basen, andere bewegliche
  Armteile separat in gemeinsamer Zeitdiagnose. Gelenksampling≤0,005rad.
- Empfohlener Bahnsatz goal-8-1-3-0: gemeinsame Starts, nominal220,7s;423von2.208
  Diagnosepunkten verletzen Paarreserven, keine FCL-Kollision an Prüfpunkten,
  min Hüllabstand155,8mm. Orange Timeline macht offene Zeitkoordination sichtbar.
  Nicht als gemeinsame kollisionsfreie/executable Trajektorie ausgeben.
- Unabhängiger dichter Check tools/verify_carton_paths.py:32.784Zustände aller8
  Einzelbahnen PASS, max Geradenabweichung0,000508mm im Modell/max Gelenkschritt
 0,002312rad. Solver-/Modellgenauigkeit, keine physische Messgenauigkeit.
- Build PASS;88gezielte Pythonfälle(7neu) und nativer Vorfilter PASS. Eigenständiger
  Viewer tools/preview_carton_paths.py/.html mit Play/Pause/Zeitschieber/Orbit/
  Zoom/3Gelenklösungen/festen Zielen und verworfener Nullpose.20Browserfälle,
  identische End-TCPs aller Vorschauvarianten PASS, Start/Ende visuell geprüft.
- Reproduzierbarer Endstand setup/research/offline-carton-paths-20261117/case03/,
  Anleitung docs/offline_carton_paths.md, Logs setup/logs/uwa-carton-*.
  Erstversuch case01 im nativen Meshaufbau abgestürzt; Logs/unfertigen Fall erhalten.
  Erfolgreich mit expliziter file-URI und beibehaltenem nativen Modellbesitz;
  case02 Entwicklungsnachweis, case03 reproduzierbarer CLI. Keine Fehlerretusche.
- MoveJ-/MoveL-artige Offlineprimitive, keine Ausführung/Identitätsgarantie
  nativer UR-Interpolation. Offene Greifer, kein Schließen/Hub/Physiktest, keine
  Hardware-/ROS-Knoten-/Kameraaktion. Feste Basen. Nächster Schritt4:
  Startversätze/Warten und Alternativen zur Zeitkoordination mit Endprüfung.

## Karton: 1×-/5×-Kontaktkraftvergleich, 2026-11-17

- Nutzer möchte bestehenden Ablauf schrittweise beschleunigen; ersteStufe5×.
  Implementiert: gemeinsameZeitkompression aller12Tragegelenke t/5,v×5,a×25,
  Ruck×125; optionaleExplorationsparameter, perGelenk-Grenzen/Bremsreserveerhalten.
- Vollständige5×-Drehung imkonservativenReservevorfilter abgewiesen (bis37mm
  Fehlreserve). StattGrenzlockerung identischen147,812mmHubmitRücksetzen separat
  getestet. DieserneueKontaktzyklus DONE/PASS; tatsächlicherCOM-Hub147,738mm,
  Relativfehlermax0,373mm, VierpadkontaktbeimTragen, unterstütztesLösen/Holds.
- Vergleichmithistorischem1×-Hub:56,538→11,308sSollzeit; alle2263Gelenkstützpunkte
  stimmenbis1,70e−13radüberein, nativeCapsnichterreicht. GemesseneArmgipfel
 0,011477→0,057567rad/s. Material/Physikschritt/Engine/Kontaktbackendgleich;
  RTF0,4→0,2gibtmehrRechenzeit, keineandereSimulationsgeschwindigkeitderRoboter.
- Max10ms-Backenmittel1×→5×: RFlinks4,887→4,965N(+1,6%), RFrechts4,506→4,699N
 (+4,3%); hinten−0,17/+0,10%. GrößtePhysikschritt-Peakobergrenze5,162→5,401N.
  Lückenlose5653/1130Hubkraftfenster; gemeinsamerMessbereich99,947%desSollhubs.
  Einzelhistorienvergleich, Betragsobergrenzen; keineMaterial-/Hardwarefreigabe.
- Erstversuchebleibenerhalten:01/03Runnerstatuslücke,04ZustandslückevorHub;
 02wegenfalschverdrahtetem0,04rad/sNativeCapausdrücklichinvalidiert. FixnativeCap
  folgtmaximalerproDOFGrenze; exaktePolynomprüfungin128Segmentblöckenohne
  Fristlockerung. Erst05gültig. AlleeigenenExperimentprozessebeendet.
- MaßgeblicherIndex setup/tasks/carton_speed5_20261117/comparison-final/result.json,
  gültigerLauf fast-attempt05/, Quellen frozen02/. Bericht
  [Kraftvergleich](docs/carton_speed_comparison_2026-11-17.md), Arbeit
  work/carton-speed5-force.md. 95TasktestsundLyricalTaskbuildPASS.

## Gemeinsame ROS-Greiferfunktionen für Agenten, 2026-11-17

- Neueste Präzisierung: nominelle Sollwerte aus dem Datenblatt reichen dem
  Nutzer; eigene N/mm-Kalibrierung nicht voraussetzen. Ergänzte reine Python-/
  CLI-Umrechnung:50mm→58,82%/Positionsraw105; nominal50N→Kraftraw36 aus linearer
 20–235N-Näherung. Hersteller nennt85mmHub/20–235N, weist aber auf nichtlineare
  tatsächliche Kraft hin. Keine exakte Kraftkennlinie oder Istkraft behaupten.
  NeueFunktionen `set_width_mm`, `close_gripper(force_n=...)`, CLI`set-width`
  und`--force-n`; bestehen dieselben Servercaps, keine Hardwarebewegung.

- Nutzerauftrag umgesetzt: Öffnen, Schließen mit vorgegebener Krafteinstellung
  und relative Öffnung über neue `GripperCommand`-Action; Read/Capabilities als
  Services, Python-Client und CLI. Eigenes Paket `uwa_cell_gripper_control` für
  LF/LR/RF/RR; vorhandener rücklesegeprüfter Robotiq-Transport wiederverwendet.
  Alte rohe Action `/command` kompatibel, neue Komfort-Action `/operate`.
- Einheiten ausdrücklich Rohkraft0–255 und prozentualer Registerhub; echte
  N-/mm-Kennlinien fehlen. Nutzer bestätigt anschließend ausdrücklich, dass
  Rohkraft und relative Öffnung zunächst reichen; damit erster API-Umfang
  bestätigt, keine ungeprüfte Umrechnung nötig. Ergebnisse nennen Istregister und native Kontakterkennung,
  keine behauptete Klemmkraft oder tragfähige Vierpunktauflage.
- Eigener Dienst `uwa-grippers.service` auf66/LOCALHOST läuft MONITOR ONLY;
  alle vier Read-/Capabilities-Services real geprüft, keine SET-Kommandos oder
  erneuten Finger-/Armbewegungen. Befehlsfreigabe über `scripts/grippers.sh enable`
  mit expliziten Rohwertgrenzen. Default Kraftgrenze0/Geschwindigkeitsgrenze32.
  Start/Exit aktivieren/öffnen nichts, letzter Greifauftrag bleibt am Gerät.
- Höchstens ein Schreibauftrag je Arm über beide Actions. Bestehende Prozess-
  Lease mit altem Adapter gemeinsam; kein fremder Besitzer verdrängt. Cancel
  bleibt abgelehnt, da noch kein qualifizierter generischer Fingerstopp besteht.
- Nur Interfacepaket und eigenes neues Paket gebaut.13API-Tests und echteROS-
  Loopbackintegration67 bestanden: explizites Aktivieren, Öffnen/Weite/Kontakt-
  schließen, Kraftgrenzen, konkurrierende alte/neue Action, doppelte Prozesse,
  Monitor ohne Writes und Zielerhalt beim Exit. Keine Task-/Motionbibliotheken
  oder fremden Simulationen neu gebaut/gestartet.
- Anleitung docs/gripper_ros_api.md, Arbeit work/gripper-ros-api.md, Nachweise
  setup/research/gripper-ros-api-20261117/{mock/result.json,hardware-readonly.json},
  Logs setup/logs/uwa-gripper-api-*. Reale Kraft-/Weitenkalibrierung und
  belasteter Griff sind weiterhin separate, nicht erbrachte Nachweise.

## Reale Greifer-/Stopp-/Vierarmprüfung, 2026-11-17

- Nutzer bestätigt heutige freieArm-/Fingerbereiche/Not-Halt-Präsenz und
  quittiert nötigePolyScope-Sicherheitsmeldungen selbst. RegulärerBringup;
  keineSafetyquittierung ausderFerne. NeuesOAKFoto weiterohnelinkenBoardfit;
  ausdrücklich akzeptierten99,1cm-Fallback zentralübernommen (x±0,4955m),
  übrigeMontageparameter vorläufig. Alte90cmPläne/Benchmarknichtübertragen.
- Alle4Greifer real einzeln aktiviert/vollgeöffnet. AbschließendACT1/STA3/
  FLT0/POS3/PRE0/OBJ3/SPE16/FOR0jeGerät. ACKaufSammelschreiben belegte
  Parameternicht; jetztFOR/SPEeinzeln und zweimalzurücklesen vorPOS/GTO.
  Aufallen4real bestätigt; keineN-/mm-Zuordnung, keinbeladenerGriff.
- LangsameresProfil hardware_commissioning.yaml:0,003rad/s/0,006rad/s²;
 40mmReserve/Frische/10Hz/angenommeneStoppparameterunverändert. Hüllspalt
 133,7mmgegen79,3mmAnforderung. Vollszene/FingerhüllenfürTestwegePASS.
- Einzelq6-StoppRF real beobachtet: Anforderung/physischerAbfall/ResourceHold/
  Verriegelung bestätigt. Bestätigungsfenster nach0,699s, keineBremszeit.
  OriginaleFehlversucheerhalten: initialveralteteClientzustellung; nebenläufige
  falscheWatchdoganzeige(korrigiert/testbarreproduziert); zuletzt50µrad-
  PrüfkriteriumunterstationäremEncoderrauschen. SeparateAnalysebestätigtHalt
  bei0,2mradPositionsspanne/0,2mrad/sGeschwindigkeitundDrift; Laufzeitwächter-
  Grenzenunverändert. KeineOriginalfehlresultate überschrieben.
- Vierarmweg real versucht: tatsächlichegemeinsameBewegung≥1,45snachgewiesen.
  KeinvollständigerZielweg: erstLFbei0,004554rad/sgegen0,003Grenze, danach
  übrigeArmejeweilswegen eigenerGeschwindigkeitverriegelt. KeineFilter-/
  Grenzlockerung.64GuardSamples: Callbackmedian4,692/p9927,003/max37,236ms
  bei100msBudget; Intervallmax101,355ms, Quell-Empfangsaltermax48,17ms.
- Endzustandfrischbestätigt: alle4Holdsaktiv/alle4stationär, qdmax0imSample;
  Wächterweiterarmed, Greiferoffen. KeinReset/keineRückfahrt/keinResume.
  RechenreservefürdiesenKurzversuchbelegt, nächsterSchrittIstgeschwindigkeits-
  /Trackingabgleich vorerneutemvollständigemWeg. RealeStoppparameterunqualifiziert.
  Bericht docs/hardware_commissioning_2026-11-17.md und
  setup/research/hardware-commissioning-20261117/report.html, Rohdatendort.
- Abschlussregression153Motiontests+24Greifer/Read-only-TestsPASS. Kombinierte
  ErstcollectionscheiterteangleichnamigenTestmodulen; getrenntePaketimporte/
  importliblösenohneTeständerung. Messkurven gerendert/visuellgeprüft.

## Gemeinsame Offline-Zielauswahl, Schritt 2, 2026-11-17

- Nutzer bestätigt anschaulichen Viewer und beauftragt Schritt2. Implementiert
  und installiert: `cell_goal_selection`, neues isoliertes selection-Modul;
  bestehende Planer/Controller und parallele Karton-/Hardwarearbeit erhalten.
- Gespeicherte Kandidaten auf Modell/Mesh/Config, Gelenkgrenzen und ursprüngliche
  Zielalternativen rückgeprüft. Suchraum ist Produkt der behaltenen Kandidaten,
  unabhängig von bisherigem16-Endstellungen-Ausgabelimit. Alle6Paarabstände
  gecacht; vorhandene4Nachbarreserven und statische Mindestreserve allerPaare.
  Jeder gültige Endpunkt zusätzlich mit voller FCL-Szene/Planungsprüfung.
- Drei Kriterien: Summe Gelenkverschiebungen minimieren, kleinsten Armabstand
  und kleinste normierte Gelenkgrenzenreserve maximieren. Paretovergleich und
  deterministische Politik mit6Dezimalstellen; ungerundete Metriken gespeichert.
  Keine gewichtete Summe. Default kleinste Verschiebung, Alternativen für
  Abstand/Gelenkgrenzen; vollständige gültige Ergebnisse bleiben für Fallbacks.
- Neues synthetisches Vierarmbeispiel mit4gleichwertigen Flanschzielposen/Arm,
 8behaltenenIKs/Arm, eingefrorenem99,1cm-Modell:4.096Kombinationen vollständig
  ausgewertet,2.192gültig,1.456Paarreserve-/448Vollszene-Ablehnungen,28Pareto,
 3Vorauswahlziele. Suche1,72s, mitRanking1,87s in einemLauf; ohne Modellladen/
  Eingabeprüfung, keine allgemeine Laufzeitgarantie. Voriges90cm-Beispiel:
 4.096gültig, alle3Politiken wählen denselbenEndpunkt. Historische Daten erhalten.
- Hauptdaten setup/research/offline-goal-selection-20261117/task-alternatives/:
  request/candidates/selection.json, layout.yaml, model.urdf, viewer.html.
  Unabhängiger Vollzustands-Bruteforce verify.py bestätigt alle4.096Entscheidungen,
  Metriken und28Paretopunkte ohne Paarcache; verification.json PASS.
- BuildPASS.81gezielte PythonfällePASS(18Auswahl,13Kandidaten,29Core,21Planung)
  und nativerVorfilterPASS. Letzter zusätzlicher Cartesian-Provenienztest direkt
  mitpytest; übrige übercolcon. Gesamtes altes test-result-Verzeichnis enthält
  weiterhin den historischen Sandbox-Loopbackfehler, kein neuer Vollpaketlauf.
  CLI zunächst wegen fehlendemExecutablebit nichtgefunden; Bit korrigiert,
  installierterros2run-NachweisPASS. Initialfehler und Wiederholung erhalten.
- Viewer um Vergleichstabelle, drei auswählbare Ziele und aufklappbaresDiagramm
  ergänzt; synthetische Aufgabe/festesModell/keineBahn sichtbar.38neue und48alte
  UI-Auswahlen imChromePASS, endgültigesLayout visuellgeprüft.
  Logs setup/logs/uwa-goal-selection-*; Anleitung docs/offline_goal_selection.md.
- Ergebnisse weiterhin executable:false. Keine Bahn-/Zeit-/MoveJ-Ausführung,
  bewegte Basen oder Singularitätsbewertung implementiert. Nur Endstellungen;
  IK unvollständig, Pareto/Empfehlung auf ausgewertete Kandidaten begrenzt.
  NächsterSchritt3: glatte primitiveEinzelwege zu Vorauswahlzielen/Alternativen;
  danach zeitliche Konfliktauflösung und vollständige Trajektorienprüfung.

## Zielkandidaten anschaulich anzeigen, 2026-11-17

- Nutzer möchte Ergebnis sehen und Markdown korrekt lesen. Eigenständiger
  HTML-Viewer setup/research/offline-goal-candidates-20261117/viewer.html erstellt
  und per xdg-open im vorhandenen Browser geöffnet. Vierarm-Endstellungen und
  einzelne kinematische Kandidaten mit unterschiedlicher Textkennzeichnung.
- Orbit/Zoom,6Paarabstände und Gelenkwinkel; keine Zwischenanimation als
  vermeintlich geprüfte Bahn. Historisches90cm-Modell und Full-Turn-Mehrdeutigkeit
  ausdrücklich erklärt. Gespeicherte URDF-/Meshbindung vor Export geprüft.
- Generator tools/preview_goal_candidates.py plus HTML-Vorlage. Chrome-Render
  visuell geprüft,48Zustandswechsel und Status/Tabellen/Auswahlanzeigen im
  Headless-Browser PASS. setup/logs/uwa-goal-candidates-viewer-check.txt.
- Anleitung docs/offline_goal_candidates.md um Browseransicht und VS-Code-
  Markdownvorschau ergänzt. Keine Modelle/Planer/Roboteraktionen geändert.

## Offline-Zielkandidaten und Plan-PDF, 2026-11-17

- Nutzer beauftragt PDF des vorgeschlagenen Plans und Beginn von Schritt1.
  Dreiseitige A4-PDF output/pdf/uwa_offline_multiarm_plan_2026-11-17.pdf,
  alle Seiten gerendert und visuell geprüft. Reproduzierbarer Generator
  tools/build_offline_planning_pdf.py, ReportLab aus .venvs/charuco-print.
- Implementiert/installiert: `cell_goal_candidates`, separates Modul candidates.py.
  Explizite Weltposen/Gelenkziele und mehrere Alternativen jeArm, Multistart-IK,
  getrennte Positions-/Rotationsresiduen, Duplikatfusion und begrenzte gemeinsame
  Endstellungsprüfung. Bestehende Planer unverändert. Anleitung
  docs/offline_goal_candidates.md; keine frei formulierte Aufgaben-/Greifsynthese.
- Kinematische Einzelkandidaten nicht gegen Startstellungen anderer ausgewählter
  Arme verwerfen. Gemeinsame Ziele: volle FCL-Szene, bestehende Nachbarreserven,
  statische Mindestreserve über alle6Armpaare. Kein Pfad/Timing/MoveJ-Execute;
  Ergebnisse `executable:false`. Budgetgrenzen und fehlende Vollständigkeit sichtbar.
- Installierte CLI in zwei Vierarmbeispielen: je8Kandidaten/Arm und16gültige
  Kombinationen innerhalb gesetzter Ausgabegrenze, ca0,81/1,58s reine Suche.
  64Kandidatenposen/32Endstellungen unabhängig nachgerechnet. Daten unter
  setup/research/offline-goal-candidates-20261117/, verification.json.
- Parallel änderte anderer Auftrag Standard-Basisabstand90→99,1cm. Signaturcheck
  erkannte Änderung; historische Beispiele mit zugehöriger alter Layoutfassung
  und generierter URDF separat gesichert, keine gemeinsame Änderung zurückgesetzt.
  Erste gescheiterte Verifikation erhalten; spätere passende Verifikation PASS.
- Lyrical-Build PASS.13neueTests PASS; Paketlauf126Pythonfälle:125PASS,
  ein bestehender Loopbacktest durch Sandbox-Socketverbot blockiert, derselbe
  Test separat außerhalb Sandbox PASS(127.0.0.1). Nativer Vorfiltertest PASS.
  Initiale Build/Testaufrufe erkannten doppeltes Paket im eingefrorenen Task-
  Snapshot; Wiederholung mit `--base-paths src` erfolgreich. Originalfehlerlogs
  erhalten unter setup/logs/uwa-goal-candidates-*. Kein Hardware-/ROS-Knotenstart.
-13Kandidatentests auch nach gemeinsamem Layoutwechsel erneutPASS. Installierte
  CLI mit eingefrorenem Beispiellayout reproduziert Kandidaten und Kombinationen
  exakt; Zeitmessung separat. PDF-Zwischenbilder nach Sichtprüfung entfernt.
- Nächster Schritt: Kandidatenauswahl mit alternativen primitiven Einzelwegen
  verbinden, dann Bahnfortschritts-/Zeitkoordination. Bewegte Basisbahnen sind
  weiterhin spätere Erweiterung, keine reaktive Steuerung hinzugefügt.

## Langsamer realer Kartontest vorbereitet, Live-Inbetriebnahme offen, 2026-11-16

- Nutzer beauftragt Vorbereitung eines deutlich langsameren Realtests; startet
  URs erst selbst auf Bereitschaft. Greifer bisher laut Nutzer unbenutzt; ROS-
  Steuerung ausdrücklich erkunden. Keine Power-/Brake-/Play-, Arm-, Greifer-
  oder Controllerschaltbefehle in dieser Vorbereitung. Vorhandene Dienste erhalten.
- Beide rechten URs gelesen: POWER_OFF/NORMAL, ros.urpSTOPPED, commands[].
  Alle4RTDE-Ausgaben aufgenommen (q/qd,TCP/Wrench/Offset,nativeSpeedScaling).
  Beide rechtenTCPoffsets0. IndividuelleFK/nativesTCP stimmen innerhalb1µm
  überein; nur interner Modell-/Frameabgleich, keine physische Genauigkeit oder
  validierte Welt-/Tisch-/Basenextrinsik. Auch aktuelle Stillstandwerte sind
  ungeprüfte native Schätzausgaben; POWER_OFF ist kein Geschwindigkeitsabgleich.
- Neue ROS-Greiferanbindung: `uwa_cell_gripper_interfaces/RobotiqCommand` und
  tools/carton_gripper_ros.py. StandardMONITOR ONLY, Domain66 real/67loopbackMock;
  GET-Status/Read-Service, ausdrückliche ACTIVATE-/MOVE-Actions erst mit--actuate.
  Keine automatische Aktivierung beim Start/MOVE, Kraft/SPE/POS klar als Rohwerte,
  StartcapsFOR0/SPE32 ohneN-Zuordnung. Keine automatische Öffnung/Reset/Force0
  nach Fehler oder Nodeexit. Cancel wird abgelehnt, physischer Greiferstopp
  noch zu prüfen. Keine Greiferkommandos bei Armstopp; letztes Greifziel bleibt.
- Vorhandenes lokales Robotiq-URCap1.8.6 als Protokollprimärquelle geprüft.
  Beide echten63352-Server GET-erreichbar, ACT0/STA0/FLT0. Zwei echte ROS-Read-
  Services erfolgreich getestet, ausschließlichGET; eigene Nodes Exit0/beendet.
  Keine physische Greiferaktivierung oder Kraft-/Öffnungsprüfung behaupten.
- Neues Interfacepaket gebaut;23gezielte Softwaretests PASS. ROS-Mockintegration
  auf67gegenLoopbackserver PASS: readonly ohneSET, explizitActivate+Move, höhere
  FORabgewiesen, ShutdownohneFreigabe. Belege setup/tasks/carton_gripper_ros_*_20261116_01/.
- Readonly-Vorbereitung: tools/prepare_carton_hardware.py, langsames Datenprofil
  carton_hardware_first_test.yaml (0,5mm/s,5mmHub,0,005rad/s,0,005rad/s²).
  Paket erzeugt ausdrücklich keinen ausführbaren Hardwareplan/motion_ready.
  Daten setup/tasks/carton_hardware_preparation_20261116_01/. Initiale Import-/
  Offline-FK-Pfad-/Frameentwicklungsfehler in Logs erhalten, erfolgreiche
  Nachfolger geprüft. Kein Neubau laufender Simulations-/Motionpakete.
- Nächste Stufe nach Nutzerstart: frische Status-/Controller-/Sensorprüfung,
  sichere einzelne Greiferleerfahrt, realer Geometrie-/Objektabgleich. Tragender
  Hardware-Objektmaster noch integrieren/qualifizieren; unabhängigenPTPRunner
  nicht für starren Griff benutzen. Keine Simulation-only-Sperre entfernt.
  **Bereit für Live-Inbetriebnahme, nicht sofort für automatischen Kartonhub.**
  Anleitung docs/carton_hardware_commissioning.md, Arbeit work/carton-hardware-commissioning.md.

## Planungsforschung auf Offlinekoordination präzisiert, 2026-11-16

- Nutzer kennt alle geplanten Arm-/Basiswege; zunächst keine externe Störung,
  Menschenreaktion oder reaktive Online-Regelung. Frühere MPC-Priorisierung
  ist für den aktuellen Umfang durch Offline-Zeitkoordination ersetzt.
- Gemeinsame Samplingplanung als Vergleich ausdrücklich gewünscht; Schwerpunkt
  mehrere Ziel-/IK-Kandidaten, glatte MoveJ/MoveL-nahe Wege und priorisierte
  beziehungsweise zeitliche Konfliktlösung. Moderner Lernvergleich gewünscht.
- Vergleichsdokument um Bahnfortschritts-Konfliktkarten, Raum-Zeit-Voxel,
  Primitive-/Blendinggrenzen und Sample→Abstand/Klasse ergänzt. Vorschlag:
  paarweise Abstandsregression mit relativer Basispose statt dichtem24D-Raster;
  geometrische Endprüfung erhalten. DiffCo von generativer Diffusionsplanung
  und metrische Clearance von Gelenkraum-CDF unterscheiden.
- cuRoboV1 laut Nutzer enttäuschend, genaue Ursache unbekannt. V2-Änderungen
  anhand Technical Report recherchiert, keine lokale V2-Erprobung behauptet.
- Nur Konzept/Dokumentation in diesem Schritt, keine neue Implementierung,
  Dienste oder Bewegung. Details docs/mobile_multiarm_planning_survey_2026-11-16.md.

## Echter Vierarm-Timingtest vorbereitet, Bewegung durch Startreserve blockiert, 2026-11-16

- Neueste Nutzerkorrektur: **offene Greifer, etwa20cm Spalt; hintere Basen
  mit Zollstock recht genau100cm**. Ersetzt die unten historisch genannten
 30cm und die bloße100cm-Schätzung. Originale offene Meshgeometrie erwartet
  bei100cm statt90cm Basisabstand ungefähr21cm Spalt, also plausibel passend.
  Nutzer regt OAK-/Tischboard-Abgleich an. Beide validierten hinteren
  T_base_board liegen vor; gemeinsame Bildsicht erlaubt relative Basenlage
  ohne OAK-Weltpose. Kamera-only-Prüfung abgeschlossen:12.11.-Boardposen ergeben
  mit den akzeptiertenRear-Fits99,115cm, konsistent zurZollstockmessung, aber
  historisch/alterFokusunbekannt. FrischeStandard-/HQ-Fotos: linkesBoard stark
  unscharf/nur1Marker/0Ecken; rechts24Ecken, unabhängigePrüf-RMS1,835/1,924px
  überschreiten1px. Keine neue vermesseneBasispose/Profilaktivierung/Fahrt.
  Kamera-Lease freigegeben.100zufälligeTransformationsketten PASS, geometrische
  Genauigkeit dadurch nicht bewiesen. Bericht docs/rear_base_spacing_review_2026-11-16.md,
  Rohdaten setup/research/four-arm-model-distance-review/board-base-review.json.

- Nutzer widerspricht dem implizierten realen Engstand: Arme seien recht weit
  getrennt. Physische Startvorbereitung vorerst zurückgestellt; zuerst Modell-
  Realabgleich.42,3mm ist Abstand modellierter Fingerhüllkugeln, kein Messwert
  der Zelle. Modell setzt90cm Basisabstand/43,7cm Flanschabstand und nachinnen
  gerichtete Greifer aufca1,98m an. Basis-/Tischanker/Montagewinkel weiterhin
  nominal, Werks-FK/optischeKalibrierung ersetzt keinen Basisextrinsikabgleich.
  Ansicht setup/research/four-arm-model-distance-review/rear-envelope-gap.png.
  Keine Aufforderung, reale Arme passend zu diesen Modellannahmen umzustellen.
  Präzisierung: Ausrichtung passt, realer Greiferabstand laut Nutzer eher30cm
  (Schätzung, keine Kalibrierung). Montagezentren-Abstand angefragt; angenommene
 90cm und konservative Greiferhülle getrennt prüfen, keine globale Pose aus
  dieser einzelnen groben Distanz fitten. Bewegungstest weiter ausstehend.
  Nutzer nennt anschließend etwa100cm Basis-Mittelpunktabstand und hält Gazebo
  optisch für passend. Laufendes /uwa_cell/robot_description in Domain64 geprüft:
  Basenx±0,45m, also90cm wie Hardwaremodell. Kein unterschiedliches Live-Gazebo-
  Layout als Ursache gefunden. Bei90cm ergibt ursprüngliche Greifergeometrie
  entlangVerbindung8–11cm statt4,23cm Hüllabstand; Hüllen allein erklären30cm
  nicht. Diese Schätzungen noch nicht als globale Kalibrierung übernehmen.

- Nutzer beauftragt kleine gemeinsame Realbewegung mit Wächter und bestätigt
  freie Bereiche/Not-Halt-Bereitschaft. Alte Bewegungscontroller alle inaktiv
  nachgelesen,6Joint-Holds inaktiv geladen. Bringup meldete alle4bereitsbereit,
  commands[]/keine eigenenPower-/Brake-/Play-/Treiberstartbefehle. Kein Fahrziel.
- Vorhandener reinlesender Hardwaremonitor neu gestartet mit Zeitdiagnostik.
  RR5.10braucht556ms für RTDE-Protokollanmeldung; separate2s-Verhandlung,
  unveränderte200ms-Datenfrische/Streamtimeout.121RegressionenPASS.
- Reale15s-Messung mit4URs/141Samples: Callbackmedian5,385ms/max54,486ms
  unter100msBudget; Zyklusmax102,888ms. Quell-Empfangsalter beimGuardmax48,25ms,
  GuardalterbeimSupervisormax146,43ms. Observer-Zustellalterbis272,64ms,
  also Rechenzeitbeleg im Stillstand, keine allgemeine End-to-End-Garantie.
- +0,03rad letztesHandgelenk jeArm vorgeplant, aber INVALID_START: Mesh/FCL
  undGelenkgrenzenklar, hintereGreiferhüllen nur42,3mm Abstandgegen172,9mm
  Planungsreserve/zuletzt155,8mm LiveSchwelle. KeinArming/keineFahrt, Grenzwerte
  unverändert. Vierarme meldenROSREADY, MonitorUWA_MOTION_ARMED=0.
- Startvorbereitung ausstehend: Nutzer nach separaterPlanung(nochkeineFahrt)
  oder manuellerAusrichtung gefragt. KeineBewegungs-/Bremsabnahme behaupten.
  Bericht setup/research/four-arm-live-timing-20261116/report.html, Rohdaten/
  Status/Planfehler unter setup/logs/uwa-four-arm-live-*. Arbeit
  work/four-arm-live-timing.md. Nach Umstellen neueActuals/Prüfung verwenden.

## Karton90°: Geometrie bestanden, Kontaktzyklus offen, 2026-11-16

- Nutzerauftrag: bestehende Zweiarm-Pipeline für Längsachsendrehung90° und
  Absetzen mit Öffnung zur Kamera wiederverwenden. Kamera als feste OAK
  interpretiert. Keine Hardwareaktion. Arbeitsnachweis work/carton-roll-90.md.
- Implementiert: optionales `carton_roll_90.yaml`, geometrisch berechneter
  Hub/Drehzentrum am Modell-COM, kameraseitig bestimmtes Vorzeichen und ganze
  Endfläche auf einem Tisch. Aktueller nominaler Weg146mmHub/+90°/linkerTisch;
  direkte rechte Absenkung kollidiert RF-Unterarm/Wrist3. Alter Standardlauf
  bleibt reineTranslation; Greifstrategie/GraspGroup/12Gelenk-Zeitgesetz und
  Kollisions-/Kontakt-/Schlupf-/Stopppfade weiterverwendet.
- Ganze Rezeptgeometrie vor Einfahrt und nach Kontakt mit gemessenen festen
  Offsets vor Abheben prüfen. Kein künstliches Anheften/Offsetnachführen.
  Intervallweise konservative gemeinsame Zeitgrenzen:55,76sHub/250,94sDrehung/
  61,88sAbsenken im Nominalbeleg04; alte1588,61sDrehzeit separat erhalten.
- Dichte nominelle Planprüfung und Anfahrt/Einfahrt bestanden.44Pythonfälle,
 8CTest-Suites und JS-VM-Play/Reset/Timeline/COMPLETE-Anzeige PASS. Browserrender
  nicht geprüft. Modellvorschau: setup/tasks/carton_roll_20261116_04/animation.html.
- Vier Kontaktversuche, **kein vollständiger90°-Kontaktzyklus**:01Home vor
  Bewegung verworfen;02Fixture vor Abheben170msSTATE STALE;03RTF0,4 hebt
 147,734mm frei und dreht8,927°, dann RR-Relativfehler2,0303mm>2mm;
 04stärkerer virtueller Motor(100Nm/rad/2Nm) vor Abheben169msSTATE STALE.
  Alle Stops bestätigt, keine automatische Öffnung/Rückfahrt. VierPads bei
 02–04 am Stopp erhalten;03 frei getragen,02/04 unterstützt. Eigene Welten beendet.
- Alle vier Krafttraces vollständig; größte Backen-Peakobergrenze8,105N.
  Kein Kraft-/Material-/Hardwarefreigabenachweis. Beim Drehen zusätzliche
  Schwerkraftmomente durch hohen Griff plausibel; Schlupf vs elastische
  Getriebebewegung nicht isoliert. Niedriger COM-Griff kollidiert mit beiden
  Greiferpalmen und wurde nur offline verworfen. Prototypquellen erhalten,
  nicht in aktiven Code übernommen. Schutzgrenzen unverändert.
- Versiegelte Zusammenfassung: setup/tasks/carton_roll_summary_20261116/result.json.
  Offen: Zustandslücken stabilisieren, Drehsteifigkeit qualifizieren, vollständige
  Vierteldrehung/unterstützte Freigabe/Wiederholung mit Kraftaudit nachweisen.
- Koordinationsfehler zu Beginn: Quelländerungen invalidierten fremde Reihe02,
  case01 vor Griff mit bestätigten Holds. Dokumentiert, keine fremden Prozesse
  beendet. Später fremde Welt vollständig abgewartet. Ein aus sandboxed `ps`
  unsichtbarer Prozess ist kein freier Weltnachweis; Host-Prozesssicht verwenden.

## Literaturvergleich für vier URs mit gleichzeitig bewegten Basen, 2026-11-16

- Nutzerziel präzisiert: auch gleichzeitige Basis- und Armbewegungen, zuerst
  zwei Tische mit je zwei starr montierten Armen als Fallbeispiel. Langfristig
  vier mobile Manipulatoren. Aktueller Auftrag: Ansätze zusammentragen und
  einordnen; Anwendung ist der nächste Schritt, noch keine Implementierungswahl.
- Relevante lokale Originalgespräche und Projektnachweise geprüft. Sammlung
  [docs/mobile_multiarm_planning_survey_2026-11-16.md](docs/mobile_multiarm_planning_survey_2026-11-16.md)
  enthält klassische Verfahren, aktuelle Primärquellen bis November2026,
  Publikations-/Versuchsgrenzen, CDF-Einordnung und vorgeschlagenen Vergleich.
- Forschungsableitung: gemeinsame Sampling-/Raum-Zeit-Planung als Referenz,
  priorisierte/CBS-artige Konfliktauflösung als Alternative, gekoppelte
  Trajektorienoptimierung/NMPC für simultane Basis-/Armbewegung. GCDF2026 als
  Abstandsmodell besonders relevant; MR-STORM2026 zeigt vier UR5e mit festen
  Basen. Keine allgemeine Überlegenheit oder neue Hardwarefreigabe abgeleitet.
- Bestand bleibt enger: feste Tisch-Welt-Gelenke, CDF mit einem bewegten Arm
  und szenengebundener Kontaktbank. Punktkonditionierte Original-CDF-Modelle
  können Hindernisse im aktuellen Basisframe abfragen; Tischverschiebung
  verlangt daher nicht grundsätzlich Neutraining. Gekoppelte Ableitungen,
  Basisgeometrie und Zeitkoordination sind zusätzliche Arbeit.
- Offen: tatsächliche Basisfreiheitsgrade, vorgegebene/steuerbare/extern bewegte
  Tische, Pose-/Geschwindigkeitsmessung und Basis-Stoppmöglichkeit. Feste
  Vier-Nachbarpaarliste nicht auf variable Aufstellungen übertragen. Volle
  Modellprüfung ist kein Nachweis kalibrierter Realgeometrie oder CCD.
- Prüfung: lokale Ergebniszahlen mit Originalnachweisen abgeglichen,
  Primärquellen und lokale Links geprüft, unabhängige fachliche Reviews von
  Bestand/CDF/Mehrarmmethoden. Ausschließlich Recherche und Dokumentation;
  keine ROS-/Hardware-/Kameraaktion oder Dienstneustart.

## Arm-Hüllquader-Vorfilter implementiert und geprüft, 2026-11-16

- Nutzeridee: ganzerArm→Glieder→feineKugeln, entfernte Paare früh aussortieren.
  Entspricht Broadphase/BVH; MoveIt/FCL nutzt dies bereits, eigene zusätzlichen
  Kugelreserveabfragen waren bislang dicht. Nutzer beauftragt anschließend
  ausdrücklich den ersten Vorfilter. Implementiert im gemeinsamen Python-
  Planungscheck und nativen RRT-Worker, Details work/collision-hierarchy-review.md.
-150Zustände bestehender RR-CDF-Bahn mit3festen Armen: Basis-Hüllkugeln
  verwerfen0/600Paarabfragen, engere vollständige Arm-AABBs587/600. Diese erste
  reine Potenzialanalyse ist getrennt vom folgenden Laufzeitvergleich erhalten.
  Mikroprofil FK/Kugeln0,524ms, FCL0,115ms,4Kugelabfragen0,333ms proZustand.
  Daten setup/logs/uwa-collision-hierarchy-profile.json. Einarm-Beispiel nicht
  auf beliebige Vierarmaufgaben verallgemeinern.
- Vorfilter umfasst ganze Kugelvolumina/Tools, nach außen gerundet, gleiche
  Schwellen. Nahe Grenze/Überlappung führt zur alten Feinprüfung. Cache proArm
  berücksichtigt bewegliche Vorfahren/Mimic-Quellen/Greifer; ungültige Zustände
  werden vor Cachezugriff abgelehnt. Ganze FCL-Prüfung und genaue Wächter-/CDF-
  Abstände/Gradienten unverändert, keine Trajektorienabschnitte pauschal freigegeben.
- Lyrical-Build und120Paketchecks PASS,270identische Suite-Zustandsentscheidungen,
  3000native Zufallsfälle plus Grenzen/Volumen, Hardware-Öffnungshüllen und
  Greifer-Cacheinvalidierung. setup/logs/uwa-prefilter-{build,tests}.log.
- Offline-Laufzeit mit5rotierten Wiederholungen: gleicherTrajektoriencheck
  1,051→0,734ms/Zustand,30Aufgaben1,035→0,771ms. GanzerCDF-Plan inklusive
  Endprüfung3,112→2,304s, exakt identische zeitparametrierte Bahn; Bankvorbereitung
  ausgenommen. Ein nativerRRT-Lauf6,913→1,194s, beide Wege vollständig validiert;
  kein allgemeiner5,8×-Faktor und keine identischenRRT-Bahnen behauptet.
- Bericht setup/research/aabb-prefilter-v1/report.html/result.json, Anleitung
  docs/collision_prefilter.md, wiederholbares benchmark_prefilter.py im Motion-
  Testordner. Keine Dienste neu gestartet, keine reale Bewegung/Physikreplay.

## Einzel-UR-CDF mit eingefrorener Restzelle implementiert, 2026-11-16

- Nutzer lobt HTML-Animation und wünscht solche Übersichten häufiger; Präferenz
  in AGENTS festgehalten. Erklärung der Darstellung: Kugeln stammen aus dem
  vorhandenen konservativen Geometriemodell und sind keine CDF-Vorschrift.
  Heatmap zeigt unsigned Kontaktkonfigurationsabstand in Gelenkradian für den
  ganzen Arm gegen feste Hindernisse; keine Innen-/Außen-Kollisionsmaske.
  Oben rechts q1/q2-Schnitt bei Start-q3…q6, weiße Linie lediglich Projektion
  der tatsächlichen6D-Bahn mit veränderlichen q3…q6; Farben entlang dieser
  Linie entsprechen deshalb nicht allgemein den tatsächlichen Bahn-CDF-Werten.

- Nutzer nimmt CDF wieder auf: zunächst ein UR bewegt, drei andere starre
  Hindernisse. Originalprojekt/Code gelesen, MIT/Commit
 08a725718e748366c5b4da5cbc4c67e991961f0f dokumentiert. Neue CLI `cell_cdf`,
  Anleitung docs/single_ur_cdf.md; keine reale Geräte-/Fahraktion, kein
  gemeinsamer Gazebo-Neustart. Andere Agentenarbeiten erhalten.
- Nichtparametrischer szenenbezogener Paperansatz: analytische Batch-UR-FK,
  konservatives Ganzkörper-Sphere/Box-SDF, L-BFGS-B-Kontaktzustände, CDF als
  Gelenkradiannorm über Kontaktpräfixe/Minfusion, reaktiver logarithmischer QP.
  Eigenes UR-/Tool-/Modell-/Fremdarm-Binding, geänderte eingefrorene Gelenke
  invalidieren Bank. Keine Franka-Gewichte, kein neuronales Training, keine
  RRT-Führung/Rückfallstrategie. Selbstkollisionen in voller MoveIt-Endprüfung.
- Vorlage von0-Level-Kontakten bleibt endlich/approximiert; CDF-Wert/Projektion
  ist kein Freiraumnachweis. Jeder Schritt und fertig zeitparametrierte Bahn
  bestehen gleiche FCL-/Werkzeug-/Tisch-/Kamera-/Wächterprüfung wie Referenzen.
  Hardware-Problem/mehrere ausgewählte Arme abgelehnt; bestehender Sim-Execute
  kann erfolgreiche Ausgabe mit seinem aktuellen Start/Wächter übernehmen.
- Erster RR-Nachweis: setup/research/cdf-ur-comparison-v2/report.html und
  animation.html.27Offlineversuche(3Aufgabentypen×3Seeds×3Verfahren). Jeweils
  freier und wirklich blockierter gültiger Weg3/3PASS bei allen Verfahren;
  unzulässiges Ziel jeweils3/3INVALID_GOAL. Nur zwei gültige Aufgaben,
  keine repräsentative Erfolgsstatistik oder Paper-Benchmarkreproduktion.
-63/50/57Kontaktzustände aus1024Seeds, Vorbereiten17,65/13,15/12,14s.
  Blockierte CDF-Planung0,546–0,554s, inklusiveEndprüfung3,13–3,21s;
  QP-Abstandsbedingung verändert5–6Schritte. RRT7,28–9,01s, Circular1,21–1,28s
  ohne jeweiligeEndprüfung. CDF-Vorbereitung zusätzlich/reusabel je Szene;
  keinen pauschalen Geschwindigkeitsgewinner daraus ableiten.
- Zwei ursprüngliche SLSQP-Abbrüche waren numerische falsche Unlösbarkeit.
  Alte v1-Ergebnisse erhalten. Exakter skalarer Dual-Löser für denselben
  konvexen QP, mit unabhängigem SciPy-Optimum und konkretem UR-Regressionstest
  geprüft; v2 verwendet identische unveränderte Kontaktbanken, keine
  gelockerten Bedingungen. Alle drei blockierten Seeds danach PASS.
- Lyrical-Build/Paketregression107PASS(101pytest+6CTest),
  setup/logs/uwa-cdf-all-tests.log. Batch-FK aller4URs und SDF/CDF-Gradienten
  gegen numerische Gegenprüfung. Offlineplot visuell geprüft, interaktive
  Viewerlogik in JS-VM bestanden; Browserhost für echten GUI-Check nicht
  verfügbar. Viewer ist Modellanimation, kein Gazebo-/Bewegungsnachweis.
  Installierte Query/Plan/Preview-Kette am blockierten Fall ebenfalls PASS,
  setup/research/cdf-cli-smoke/ und setup/logs/uwa-cdf-cli-smoke.log.
- Keine Physikausführung/Hardware-CDF-Freigabe aus diesem Arbeitsschritt.
  Nächste Forschung: größere feste Suite, Projektionsgenauigkeit/Abdeckung,
  Physikreplay, danach ggf. szenenunabhängige Punkt-/neuronale UR-Repräsentation.
  Eigene HTTP-Vorschauserver beendet; keine neuen Dauerdienste.

## UWA Robot Power installiert, 2026-11-16

- Kleines Startmenüfenster mit eigenem Symbol und zwei Vierarmaktionen:
  Standby (ros.urp stoppen, dann Antriebe abschalten) und Start + ROS
  (vorhandener Bringup). Je Arm bestätigter Status oder Bedienhinweis.
  Exklusiver Bringup-Lock, laufende andere Programme werden nicht gestoppt.
- Installierter Desktop-Eintrag erfolgreich geöffnet; doppelter Aufruf
  zeigt dieselbe Instanz. Status las alle vier als ROS READY. 29
  Dashboard-Tests im Simulator und Qt-Klicktest mit simuliertem Backend
  bestanden. Im echten Test wurden keine Schaltbefehle gesendet.
  [Bedienung und Neuinstallation](docs/ur_power_gui.md).

## Alle vier URs in aufrechter Parkpose, 2026-11-16

- Nutzerauftrag: seitlich ausladende Arme kompakt parken. Vier aufrechte
  Parkziele und serielle MoveIt-Wege aus frischen 24 RTDE-Gelenkwinkeln
  geplant und live abgeglichen. Nach Vor-Ort-Bestätigung der freien
  Fahrbereiche und Not-Halt-Bereitschaft LF, LR, RF, RR gefahren.
- Alle vier Ziele bestätigt, unabhängiger RTDE-Endabgleich <0,004°,
  Arme stehen. Eigene Bewegungscontroller danach inaktiv. Keine Änderung
  von Sicherheitskonfiguration, PolyScope-Programmen oder Treiberdiensten.
  Ziele sind Parkreferenzen; vor Wiederverwendung neuen Weg aus Livezustand
  prüfen. [Arbeitsnotiz](work/four-ur-home-20261116.md).

## Studentischer Roboter: erster 3D-Kandidat und präzise LF-Diagnose, 2026-11-16

- Nutzer beauftragt 3D-Modellarbeit und separate Kameradokumentation zur parallelen
  Bearbeitung. Ausschließlich gespeicherte Daten verwendet, keine Hardware-/GPU-
  Aktion, kein Profil-/Simulationsassetwechsel. Anleitung docs/student_robot_visual_hull.md.
- Neuer CPU-Visual-Hull-Prototyp silhouette_mesh.py: manuelle hashgebundene
  Außenkonturen,7Fit-/6reserviertePrüfansichten, LF ausgeschlossen. Feste direkte
  Boardposen/nativeK/D, keine FK/Hand-Auge-/Objekt-Ground-Truth.4mm Gitter/2px
  Maskentoleranz; Nutzer-Auflagehöhe als ausdrückliche koplanare Board-/Tisch-
  Annahme. Freier erster Suchraum unten abgeschnitten: Fehlversuch erhalten.
- Geschlossener Nachfolger mit Tetra-Isosurface,258220Dreiecke, Hülle452×320×316mm.
  Länge gegenüber grober Nutzerangabe330mm offen prüfen; keine erzwungenen Maße.
  Prüfsilhouetten-IoU0,846–0,938/Mittel0,905 als reine Eingabekonsistenz.
  Hüllenrechenzeit5,41s ohne Annotation/Textur/Export/Agent, kein Reasoningvergleich.
- GLB/STL/Quellen/Preview unter
  setup/digitization/student_robot_20261113/reconstruction_v1/asset_candidate/.
  Fototexturen nur ausFitbildern,66,8% der Dreiecke; Restgrau. Gitterlöcher und
  Innenräume nicht gemessen, geschlossene Kappe ist nurHülle. Foto enthält am
  Gitter sichtbaren Hintergrund, keine gemessene Albedo. DRAFT_REVIEW_REQUIRED,
  keine Geometrie-/Tracking-/Manipulationsfreigabe oder Fertigungs-CAD.
-11gezielteTests PASS; GLB nach Wiederexport identisch, STL wasserdicht,
  positive Orientierung und metrische Ausdehnung nach Einlesen bestätigt.
  Originaljob bleibt NEEDS_INPUT: Prototyp noch kein validierter Standardbackend.
- LF: docs/left_front_camera_diagnosis_2026-11-16.md und Offlinewerkzeug
  diagnose_digitization_camera.py. Kamera028E1F350009061C/2592×1944/Fokus245,
  zentrale Intrinsicsprüfung damalsPASS, Hand-AugeFAIL getrennt. Aktuelle direkte
  Board-RMS1,987–55,683px am linken Bildrand; gespeicherter radialer Modellanteil
  abnormiertemRadius0,485246 nichtmonoton. Extrapolationsproblem mathematisch
  belegt, Hardwaredefekt/einzige Ursache nichtbewiesen. Quellen/Readbacks,
  Tabellen und getrennte Prüfschritte für parallele Arbeit dokumentiert;
  Originalprofile nicht verändern. Arbeit work/digitization-fast-workflow.md.

## Hardware-Kollisionswächter/PTP implementiert, physische Abnahme offen, 2026-11-16

- Nutzer beauftragt Übertragung aus Simulation. Neuer expliziter Backendpfad
  `cell_hardware_motion`, Domain66hardware/67mock; Simulation64 bleibt gesperrt
  gegen Hardware. In dieser Arbeit keine reale Geräteabfrage, kein Treiber-
  neustart, STOP, Power/Brake/Play oder Fahrziel. Fremde Zellarbeiten erhalten.
- Output-onlyRTDE20Hz mit Gerätezeit, Puffersignalalter, Epoch-/Freezeprüfung;
  Geometrie10Hz monotone Zeit. Individuelle Werkskinematik und zentrale
  Kalibriergeometrie; reale Treiberursprünge vor Freigabe vergleichen. Genau
  vier Nachbarpaare, latching, scoped partialreset, kein automatischer Wiederanlauf.
- Je Manager6echte Positionsschnittstellen des C++CollisionHold; Actionabbruch,
  Topic-/Positionsaktivierungskonflikte und polled Entfernung anderer
  Armcontroller. Supervisor+separater Watchdog mit Lease, Hardwareplugin- und
  laufendem Parameterreadback. Native Dashboard-Rückfall ausschließlichSTOP;
  schlanker Exit-Helfer ohne ROS-/MoveIt-/Kinematikinitialisierung. ACK und
  Ressourcenbesitz ausdrücklich kein gemessener Stillstand; je Arm prüfen.
- MONITOR ONLY ohne Stellaktionen als Standard; Provision(inaktiv), Arm,
  Reset, Plan, HTML-Vorschau und Execute getrennt. Arming verriegelt anfangs
  alle Arme. Managerfremdaktivierung bleibt polled, kein hardwareseitig
  unüberwindbarer Inhibit gegen privilegierte Clients/Pendantprogramme.
- Unbekannte Greiferöffnung: komplette volumetrische Öffnungshülle mit
  analytischer Zwischenwinkelreserve,166Kugeln/Arm. Interne gekoppelte
  Robotiq-Hüllpaare explizit in beiden ACMs erlaubt; externe Tool/Kamera/Arm/
  Tischprüfungen erhalten. Keine innere Mechanikabnahme. Bewegliche unbekannte
  Fingervisuals entfernt; echte24JointStates und Modell28 getrennte Themen.
- Beide Planer verwenden dieselbe volle Szene/Timingprüfung, keine versteckten
  Rückfälle oder Startrepositionierung; Hardware-/Mock-Modellbindung, tatsächlicher
  Start und gemessener Fortschritt. Skalierter echter UR-JTC; Restwege gegen
  gestoppte Arme/Bremsreserve prüfen. Bestehende manuelle GUI-Gates unverändert.
- Echte ros2_control-/C++-Pluginprüfung in privatem GenericSystem bestanden:
  setup/logs/uwa-hardware-hold-plugin-check.json.6Positionclaims, Positions-
  konflikt abgelehnt, Topic ohne Wirkung, Velocityfremdbesitz entfernt. Eigene
  Testunit danach beendet. Aktueller Viermanager-Fake-Lauf vollständig PASS:
  setup/logs/uwa-hardware-mock-integration-current.json, beide Planerpfade,
  unabhängiger Arm fährt bei Paarstopp weiter, sämtliche Ausfallinjektionen.
  Fehlversuche mit historischer ACK-Testannahme/zu früher Resetbeobachtung
  erhalten; Produktiv-Frischegrenzen nicht gelockert. Lyrical-Build und89
  Paketprüfungen PASS(84pytest+5CTest), setup/logs/uwa-hardware-motion-tests.log.
  Installierter Viernode-Monitorlaunch mit getrennten Prozessen in Mock67 PASS,
  fehlende Quellen bleiben STALE: uwa-hardware-monitor-launch-check.json.
  Eigene Mock-/Launchprozesse anschließend beendet; kein Hardwaredienst aktiv.
- Hardwareprofil0,01rad/s/0,02rad/s²,1s Latenz/0,2rad/s² Bremsen/40mm Reserve
  **unvermessene technische Annahmen**. Reale Latenz/Bremsen/Netz-/Prozessausfall,
  Paarstopp mit unabhängigem Arm und Welt-/Tischanker physisch prüfen, bevor
  Sim-/Mock-Nachweise als Realbetriebsergebnis ausgegeben werden. Kein aktiver
  Hardwarewächterdienst aus dieser Arbeit. Anleitung docs/four_arm_hardware_motion.md,
  laufender Eintrag work/four-arm-hardware-motion.md.

## Reale Kartonpose auf FoundationPose-GPU erstmals geprüft, 2026-11-16

- Nutzer stellt bekannten Avocado-Karton neben studentischen Roboter, bestätigt
  ruhende Aufnahme. Neue aufrechte Seitenlage;8RGB-D-Paare unter
  setup/oak4/rgbd/20261116-111619-rgbd-5a8d0ae9/.
- Manuelle sichtbare Startkontur, gehashte Eingangsdaten,292Dreieck-Meter-Mesh
  mit Texturatlas im unveränderten Assetframe. Kein gespeicherter Szenen-/
  Board-/Weltposeprior, keine globale Kalibrier- oder ROS-Backendänderung.
-1280×960 scheitert am unveränderten45%-GPU-Limit. Wiederholung640×480 mit
  korrektem Pixelzentrum-K und nearest-Tiefen-/Maskensampling bestanden:
 1,623s Registrierung/18,806ms mediane Trackingkernzeit,8statische Frames.
- Box und Textur-Rückrender visuell plausibel. Masken-IoU0,913, Tiefenrest
 7,08mm reine Eingabekonsistenz, keine unabhängige Genauigkeit. Reale Bewegung/
  Verdeckung/LOST und WLAN-Livepfad offen. PyTorchmax5068MiB reserviert.
- Eigene Kamera-/GPU-Prozesse beendet, Kamera-Lease frei, GPU175MiB/0%.
  Heutiger Workstation-Metadatenvergleich unverändert.38OAK-Tests/9Subtests
  und3Exportprüfungen PASS. Keine Arm-/Programmaktion oder Dienstneustarts.
- Nachweise setup/tracking/foundationpose_carton_20261116/, Anleitung
  docs/foundationpose_titanpc.md; Arbeit work/foundationpose-carton-real.md.

## Studentischer Roboter: reale Mehransichtsbilder aufgenommen, 2026-11-16

- Nutzer bestätigt unveränderten Aufbau. Offener Fokus-/HTTP-Restore verifiziert;
  neuer vollständiger stationärer Satz4×2592×1944+OAK8000×6000 akzeptiert,
  allebrauchbar/Stillstandtrue, Boards teilweise sichtbar. Alte Fehlschläge erhalten.
  Daten setup/digitization/student_robot_20261113/job/captures/20261116_103720_9f6d61d9/.
- Explizit genehmigter lokaler Vierarm-Treiberneustart mit UDPv4 und Stop/Play
  ausschließlich ros.urp ausgeführt; keine Power-/Brake-/Fahrbefehle. Neuer
  Benutzerdienst uwa-ur-drivers-udp-20261116.service. Alle vier RUNNING/NORMAL,
  Reverse verbunden, je5Broadcaster aktiv/4Motioncontroller inaktiv; frische
  JointStates aller Arme, gemessener Peak0,000137rad/s im8s-Fenster.
- Enger MATCH-Fix: Runtime-Spawner braucht eigenen Armnamespace für YAML-Auswahl;
  zuvor RF-GPIO-Präfix leer.16Tests PASS. Vorherige zusätzliche Discovery-Ausfälle
  im neuen UDP-Lauf nicht beobachtet, genaue Ursache noch unbewiesen. Clients
  für diesen Lauf mit FASTDDS_BUILTIN_TRANSPORTS=UDPv4 verwenden.
- Zwölf neue Sicht-/Kollisionswege ab gemessenen Starts geprüft.
  Parallele Abstandsprüfung für alle4 initial/extra/all PASS:
 50mm Anforderung/5mrad Korridor, minimale untere Abstandsschranke349,7mm.
  Live-Preflight CHECKED/motion_sentfalse/3Runden; reine gemeinsame Fahrzeit59,1s.
  Nutzer danach am Nothalt/freie Fahrbereiche bestätigt; alle3gemeinsamen
  Fahrten ausgeführt, keine automatische Rückfahrt.
- Runde1/2 vollständig/stationär bestätigt. GUI/Runner während letzter Aufnahme
  unerwartet Exit143 (Ursacheoffen); Bewegungscontroller zuvor deaktiviert,
  Kamera-Worker beendet Transaktion/Restore. Dritter Originalsatz vollständig,
  aber LF-Geschwindigkeitssignal0,020229rad/s verletzt Stillstandsprüfung;
  Positionsspanne0,276mrad. Nicht importiert/Flags nicht verändert.
- Nachprüfung alle4Motioncontroller inaktiv und Geschwindigkeitennull. Reiner
  Kamerawiederholsatz am erreichten Standpunkt erfolgreich, keine weitere Fahrt.
  Mit Referenzsatz jetzt4akzeptierteSätze/20nativeBilder,4Standpunkte jeWrist,
 1OAK. Prepare10,307s; LF metrisch ausgeschlossen/diagnostisch, RFFailed-Flags
  erhalten. Fokus-Restores und LED0 aller4bestätigt. Aufnahmeziel erfüllt,
  ursprünglichen Scanprozess ausdrücklich NICHT als COMPLETE ausgeben.
- Kontaktbogen accepted_views.jpg und scan_recovery_summary.json unter
  resume_20261116/. Vor neuer Fahrt persistente Prozessführung/Abbruchpfad klären.
  Geometrie/Tracking weiter NOT_TESTED; geprüfte Objektmasken und validierter
  dichter Mesh-Backend fehlen. Anleitung docs/student_robot_digitization.md,
  sämtliche Neustart-/Plan-/Preflightnachweise unter
  setup/digitization/student_robot_20261113/resume_20261116/.

## OAK-RGB-D-Boardprüfung und weitere Referenz benötigt, 2026-11-16

- Fortsetzung mit vorhandenen8Paaren: vorderes rechtes40mm-Board24Ecken,
 16Fit-/8Prüfecken, maximales Prüf-RMS0,3222px. K/D unverändert, kein Weltprior.
- Tiefe gegenüber RGB-Boardebene median+11,05mm; keine Millimetergenauigkeit
  oder sichere Ursache. Nutzer misst5Felder200mm mit Lineal, ohne kalibrierte
  Unsicherheit. Keine globale Kalibrierung/Offsetkorrektur daraus vorgenommen.
- Daten: setup/oak4/rgbd/20261116-102913-rgbd-fa320e7a/board-check-v1/;
  Offlinewerkzeug und36Tests/9Subtests bestanden, Anleitung OAK-Repo OAK4_RGBD.md.
- Mobiles38mm-A4-Board für verschiedene Abstände/Neigungen vorgeschlagen;
  Nutzer nach Verfügbarkeit gefragt. Karton kann später funktionalen Poseversuch
  ermöglichen, ersetzt diese metrische Referenz nicht. Keine neue Kamera-/UR-
  oder GPU-Aktion; Status work/foundationpose-rgbd-validation.md.

## Erster realer OAK-RGB-D-Datensatz für FoundationPose, 2026-11-16

- Nutzer beauftragt Schritt1; aktuell steht studentischer Roboter an früherer
  Kartonstelle. Für Aufnahmetest kein Mesh nötig, keine automatische Poseerkennung.
- Neuer OAK-CLI-Modus `capture --mode rgbd`, vorhandene Kamerasperre/SDK-Isolation.
  Acht entzerrte RGB-/ausgerichtete Tiefenpaare1280×960, Fokus116, maxZeitabstand
  1,727ms; tatsächliche Ausgabe-K beider Frames identisch. Paarrate10,00Hz.
- Datensatz setup/oak4/rgbd/20261116-102913-rgbd-fa320e7a/, preview.png und
  initial-check.json geprüft; Roboter/Board sichtbar, Tiefe mit Lücken. Lease
  danach frei.31Offlineprüfungen/9Subtests PASS; keine UR-/GPU-/Dienstaktion.
- Anleitung OAK-Repo OAK4_RGBD.md. Nächste Stufe: Board/K-/Tiefengeometrie prüfen,
  danach Mesh/Initialmaske. Noch keine Genauigkeits- oder Manipulationsfreigabe.

## Gemeinsamer UR-Start für ROS (2026-11-16)

- Neuer Befehl `scripts/ur_bringup.py`: Standard/--status rein lesend,
  --apply bereitet die ausgewählten realen Arme vor; Standardauswahl alle vier.
  Bedienung, JSON-Status und Hinweise am Pendant: [UR Bringup](docs/ur_bringup.md).
- `/programs/ros.urp` pro Arm im Inventar nach dem Backup verifiziert;
  Seriennummer und PolyScope-Generation live abgleichen. Bereits laufende
  Programme erhalten, bei Safety/Local/ungespeichert Bedienerhinweis. Keine
  Sicherheitsquittierung und keine Bewegungsziele.
- Live am 16.11.: alle vier per Ethernet erreichbar, `ros.urp` bereits
  geladen und gestoppt. Fehlende lokale Treiber über den realen Launch
  gestartet (`uwa-ur-bringup-drivers.service`). `--apply`: beide hinteren
  Arme eingeschaltet und Bremsen gelöst, Programm auf allen vier gestartet.
  Alle vier danach RUNNING/NORMAL/PLAYING und mit ROS verbunden.
- `--apply` startet fehlende Treiber jetzt selbst, ohne aktive Instanzen zu
  ersetzen. 22 Simulationstests bestanden, darunter der Treiberstart vor
  Dashboard-Schreibbefehlen und der Abbruch bei fehlendem Treiber. Der
  erneute reale Aufruf meldete alle vier bereit und sendete keine Befehle.

## Beschaffung realer FoundationPose-Eingaben eingeordnet, 2026-11-16

- Nutzer fragt nach dem besten Weg zu den fehlenden Informationen. Bestands-
  und Quellenprüfung, keine neue Aufnahme, Installation oder Hardwareaktion.
- Vorhanden: Meter-Assets, OAK-Werkskalibrierung/Ausgabe-K, separate RGB-/
  Mono-Tiefenpfade und vorläufige OAK-Weltregistrierung. Hauptlücke ist ein
  zusammengehöriger entzerrter und RGB-ausgerichteter RGB-D-Datensatz.
- Empfehlung, noch keine Nutzerentscheidung zur Umsetzung: feste OAK zuerst,
  RVC4 ImageAlign+Sync mit gemessener Zeitdifferenz, tatsächliche Ausgabe-K,
  erster Objektumriss manuell. Statischer Karton-Replay auf GPU, dann PTFE/
  Bewegung/Verdeckung und erst anschließend WLAN-Livepfad. Keine Neuaufnahme
  sämtlicher Wrist-/Hand-Auge-Kalibrierungen für reine Kameraposen nötig.
- Werksdaten/Alignment am Board und an unabhängigen Kontrollmaßen prüfen;
  OAK→Roboterbasis separat vor Manipulation validieren. Existierende HQ-Bursts
  nicht als zeitgleiche RGB-D-Paare oder bewegungstauglich deklarieren.
- Vorgehen/Quellen in docs/foundationpose_titanpc.md, Abschnitt16.11.; eigene
  Statusdatei work/foundationpose-input-plan.md. Aktive UR-Vorbereitung erhalten.

## Wiederaufnehmbare Digitalisierung implementiert; Robotertest offline vorbereitet, 2026-11-13

- Nutzer beauftragt Umsetzung des schnellen Workflows und Test an komplexem
  studentischem Roboter, grob330×300×330mm. Objekt ausgeschaltet/unbeweglich und
  Unterseite auf Tischplattenhöhe bestätigt. Danach URs wegen Meeting aus;
  ausdrücklich offline weiterarbeiten. Seit dieser Mitteilung keine UR-Anfrage.
- scripts/digitize.sh und digitization_job/geometry/optics/views: eigene Jobs,
  Hash-/Identitäts-/Fokusbindung, Stillstandsimport, wiederverwendbare Stufen,
  Rollen für Fit/Prüfung, zwei feste Formrezepte, explizite Texturflächendaten,
  CAD/ROS-Kandidaten und unabhängiger Einzelbild-Trackingcheck. Kurze Skill
  .agents/skills/uwa-digitize/SKILL.md validiert. Keine Hardwarefahrfunktion.
-61gezielteTests und Lyrical-Build bestanden. Reale gespeicherte PTFE-/Karton-
  Datensätze offline verarbeitet und Kandidaten exportiert; technische STEP/
  STL/GLB/DAE-Prüfungen bestanden, beide Geometrien bleiben REVIEW_REQUIRED.
  PTFE-Prüfansicht weiterhin ohne sichere Erkennung. Keine Originalassets ersetzt.
- CPU-Vorschau ersetzt für neue Runner-Kandidaten anfällige Qt/OpenGL-Abhängigkeit.
  Alter VTK-Versuch ist als Entwicklungsmisserfolg erhalten. Mess-/Cacheberichte
  unter setup/digitization/pipeline_offline_20261113/, kein Reasoning-Vergleich
  oder universeller Scanner nachgewiesen. Noch kein dichter Mesh-Backend.
- Ein Offlineaufruf `run` bündelt die Stufen ohne neue Aufnahme. Am gespeicherten
  PTFE-Satz mit fertigen Annotationen7,18s einschließlich Shell-/Pythonstart,
  Wiederholung1,33s; gemessene Qualität dabei unverändert prüfbedürftig.
  one_call_cli_timing_final.json. Relative/absolute Jobpfade kanonisiert, damit
  identische Inputs nicht unnötig neue Kandidaten/Cachemisses erzeugen.
- Neuer Roboterdatensatz setup/digitization/student_robot_20261113/: OAK-Übersicht,
  erster Fünfersatz vor Bildern abgebrochen, zweiter dreiWrist-HD+OAK, LF-SSH
  nicht erreichbar und abschließender Stillstand/Restore unbestätigt. Nichts
  nachträglich als gültige Aufnahme oder erfolgreicher Restore markieren.
- Planungshülleca546×546×403mm aus OAK-Referenz/Nutzermaß/Entwurfszuschlägen.
  Erstere Suche kein gemeinsamer Blick; zweite mit größeren Kameraabständen
  bei unveränderten Grenzen:12modellgeprüfte Abschnitte, dreiWristansichten je
  Arm plus OAK. Domain74/offline, gespeicherte ältere RTDE-Werte; Bericht
  offline_view_plan_wide/report.json und Vorschau. Noch nicht ausführbar oder
  unabhängig parallel freigegeben. Keine Arm-/Treiber-/Power-/Brake-/Playaktion.
- Vor Fortsetzung nach Nutzer-Einschalten: Kamera-Restore/LF-HD-Zugriff klären,
  frische Zustände und Wege prüfen, aktuelle Bedienerbereitschaft vor Fahrzielen.
  Bedienung docs/digitization_workflow.md, Test docs/student_robot_digitization.md.

## Zusätzliche NVIDIA-Workstation für FoundationPose, 2026-11-13

- Nutzer stellt titanpc/192.168.2.137 über WLAN für Compute bereit. Gemeinsame
  Workstation anderer Nutzer: vorhandene Umgebungen/System/Dienste erhalten.
- TITAN RTX24GiB, Ubuntu22.04.5, Treiber570.211.01, Toolkit12.3 real gelesen.
  Docker ohne Benutzerzugriff; Systempartition nur5,5GiB frei. Deshalb eigener
  Ordner und eigene Conda-Umgebung auf Datenlaufwerk RAID1_L, keine Adminänderung.
- FoundationPose installiert: eigenePython3.11/PyTorch2.5.1+cu121-Umgebung,
  PyTorch3D0.7.8/nvdiffrast0.3.3/mycpp gebaut, pipcheck PASS. Offizielle Gewichte
  und RGB-D-Daten geladen. Zwölf-Frame-Test und100-Frame-Bewegungsabschnitt
  PASS, zuletzt1,699s Initialisierung/24,61ms mediane Trackingkernzeit,
  PyTorch5058MiB maximal reserviert. Overlays bei Bewegung/Verdeckung geprüft.
- Keine Live-/WLAN-Ende-zu-Ende-FPS oder UWA-Asseterkennung daraus ableiten.
  Systempaket-/Shell-/Conda-Metadaten vorher/nachher identisch; eigene Jobs
  beendet, GPU wieder175MiB/0%. Eigener Ordner9,3GiB auf Datenlaufwerk.
  CPU-Tracker und lokale Roboter-/Simdienste erhalten. Stand/Bedienung:
  docs/foundationpose_titanpc.md; Nachweise lokal unter
  setup/tracking/foundationpose_titanpc_20261113/ einschließlich motion/.
- Fachlicher Anschluss: bekannte Karton-/PTFE-Assets, statische Lokalisierung
  und dynamische Verfolgung. Reale OAK-Anbindung benötigt noch passende
  RGB-ausgerichtete Tiefe, Intrinsics und Initialmaske; keine direkte Nutzung
  der Mono-HQ-Tiefe mit RGB oder neue Manipulationsfreigabe.

## Schnellere Digitalisierung: ursprüngliche Bestandsprüfung und Konzept, 2026-11-13

- Nutzer möchte weniger Wartezeit und niedrigeren Reasoning-Aufwand bei
  möglichst gleicher Qualität/Sicherheit. Noch keine Modelleinstellung geändert.
- Bestandsprüfung: Aufnahme/Optik/Fit/Export/Prüfung teilweise wiederverwendbar;
  Formbeschreibung, Bildzuordnung und Texturflächen noch objektspezifisch.
  Erfolgreiches PTFE-Fünferset laut Manifest44,34s, ohne Vorbereitung/Restore,
  Fehlversuch und nachfolgende Entwicklungszeit; vollständiges Timing fehlt.
- Geplant: Runner mit festen Daten-/Qualitätsverträgen, konfigurierbare Kasten-
  und Plattenvorlagen, Wiederaufnahme, kompakte Statusausgabe, kurze Skill für
  schnellen Agenten; gezielte Fachbearbeitung bei unbekannter Form/Fehlern.
  Geometrie/Darstellung/Tracking/Manipulation getrennt bewerten.
- Abnahme zuerst auf gespeicherten Karton-/PTFE-Daten plus Fehlerfällen,
  anschließend Vergleich der Reasoning-Stufen und neues Objekt ohne neue
  Objektskripte. Keine Laufzeit-/Genauigkeitsgarantie vor dieser Messung.
- Dieser ursprüngliche Eintrag dokumentiert die Konzeptphase; die spätere
  Implementierung und der Robotertest stehen im neueren Abschnitt oben.
  Plan docs/digitization_pipeline_plan.md.

## PTFE-L-Konstruktion aufgenommen und als Asset exportiert, 2026-11-13

- Separater Nutzerauftrag: neues Objekt mit vier Wristkameras und OAK aufnehmen,
  Asset für anschließendesTracking anlegen. Nutzer bestätigt20×20mm-Profile und
  10mm-Platten; Außenmaße bildbasiertca300×177×181mm. Keine Armbewegung.
- Set setup/digitization/ptfe_l_20261113/acquisition/20261113_153425_f9234640/
  set_153436_409595/ vollständig aufgenommen/brauchbar und kontinuierlich
  stationär bestätigt; nicht alle Boards vollständig sichtbar. Erster Versuch
  ohne ROS-Joints bleibt gescheitert. Zweiter Versuch explizit mit neuem rein
  lesendem RTDE-Ausgabebeobachter; keine Treiber-/Programm-/Poweraktionen.
- Asset description/assets/ptfe_l_assembly_v1 mit STEPmm, STL/GLB/DAEm,
  fünf Fototexturen, Manifesthashes. Ein geschlossener Körper/116Dreiecke,
  STEP-/Mesh-Rückimport geprüft,21gezielteTests bestanden. Platten/Profilnuten/
  Schraubdetails teilweise vereinfacht; keine absolute Genauigkeit validiert.
- Geometriefit OAK/LR/RR, RF ausschließlich geometrische Prüfansicht mit25,20px
  Restfehler bei1600px-Breite. LF wegen nativer Optik-/Boardinkonsistenz metrisch
  ausgeschlossen. Schätzgrenzen in docs/ptfe_l_assembly.md, keine PASS-Umdeutung.
- Trackingreferenz1494Merkmale vorbereitet. Offline-OAK/LR/RR/RF jeweilsLOST;
  regelmäßige Lochstruktur/glatte Flächen erschweren SIFT. Keine Online-
  Tracking- oder Manipulationsfreigabe für dieses Objekt. Mehrskaliger Versuch
  ebenfalls erfolglos, Diagnosen erhalten, bisherigen Trackerstandard beibehalten.
- Laufende Karton-Simulations-/Greifarbeit unverändert; neues Asset installiert,
  noch keine aktive Szeneinstanz. Anleitung und Vorschau docs/ptfe_l_assembly.md.

## Schnellere Simulationsprofile in Prüfung, 2026-11-16

- Explizites Explorationsprofil mit separaten Arm-/Fingergrenzen implementiert;
  gleiche per-DOF-Stoppreserve in Planung und Wächter. C2-Einfahrt mit gemeinsamer
  Zeitparametrierung ersetzt feste30s-Untergrenze nur bei explizitem Profil.
  Kontaktservo-/Holdgrenzen szenengebunden, keine shared Motionmodule verändert.
- Build PASS, colcon meldet37Tests ohne Fehler (8CTest-Suites einschließlich Treiber-Cleanup/Klassifikation). Geplante
  Ruckgrenze ergänzt: exakte Extrema der JTC-Quintik, gleichmäßige Retimierung
  aller beteiligten Gelenke. Keine Aussage zum gemessenen Servo-/Stoppruck.
  Spätere erfolgreiche500g-/10mm/s-Durchläufe und Stoppprüfungen stehen unten;
  die folgenden ursprünglichen Fehlschläge bleiben erhalten.
- Run78/explore01:0,1rad/s Arm,0,5rad/s Finger,1rad/s² Bremsen vor Fahrt
  abgewiesen. Home-Abstand rechts0,221m, erforderliche Reserve0,334m. Kein
  Kartonlastfehler; Arme bestätigt gehalten. Rohdaten/Fehler erhalten. Nächster
  Kandidat0,06rad/s Arm,0,2Finger,0,15grobes Schließen,0,02fein,5mm/s Objekt.
- Run79/explore02:0,06Arm/0,2Finger ebenfalls vor Anfahrt gestoppt; mit
  Datenalter steigt Reserve auf0,227m über0,222m Abstand. Run80/explore03
  (0,05Arm/0,15Finger,0,1grobes Schließen,5mm/s Objekt,1rad/s³ Planruck)
  stoppt beim unbelasteten Öffnen: Runner-Empfangslücke0,203s. Unabhängiger
  Kraftrecorder ohne Fensterlücke, maximaler Wall-Empfangsabstand0,0744s.
  Alle drei Episoden bestätigt stillgelegt und eigene Welt beendet, Rohdaten
  inklusive Kraftauswertung erhalten. Keine Kraft-/Materialgrenze erreicht.
- Diagnoseversuch81/explore04 mit5s stabiler Telemetrie vor Reset/Arming
  und Threadstack-Dump bei Runner-Frischefehler erreichte echten Kontaktgriff
  und16,495mm500g-Hub. Anfahrt50,582s, Einfahrt7,042s, geplanter30mm-Hub11,475s.
  Abbruch wegen passivem RR-Tip0,153791rad/s über Profilgrenze0,15. VierPads
  und tragender Griff beim bestätigten Stopp erhalten; maximaler Relativfehler
  im aufgezeichneten geladenen Abschnitt1,091mm/0,003697rad. Kein fertiger Zyklus.
  Last je Backe bis3,289N/10ms, Peakobergrenze6,051N, unter50N-Nutzerreferenz.
  Kräfte gültig, aber eine Empfangslücke vor Arming:14fehlende10ms-Fenster in
  observe. Altes Lastreportfeld zählt1Lückenintervall; neuer Analyzer zählt
  fehlende Fenster und listet Intervalle explizit. Kein vollständiger Datensatz.
  Eigene Welt nach bestätigtem Stopp ohne Öffnung beendet. Keine Frist gelockert.
- Recorder erhält jetzt50BestEffort-Pufferplätze für Kräfte statt5; Messlücken
  bleiben sichtbar. Neuer Kandidat0,05Arm/0,2Finger, gleiche Mechanik und
  eingehaltene Stoppreserven. `carton_exploration_20261116_ladder01` läuft als
  echte endliche Versuchsfolge5/10mm/s, je eine Wiederholung, noch kein PASS.
- Ladder01/case00 (5mm/s) tatsächlich bis29,371mm getragen und gehalten,
  maxRelativfehler1,041mm/0,003387rad. Beim Absenken passive RR-Gelenke bis
  0,477701rad/s über0,2-Profilgrenze: **FAIL**, kein vollständiger Zyklus.
  VierPads/Grip beim bestätigten Stopp erhalten.20082Kraftfenster ohne Lücke,
  Backenmittel max4,801N/10ms, Peakobergrenze6,419N. Eigenes Welt-Cleanup und
  nächste Fallvorbereitung automatisch erfolgt. Case01/10mm/s ebenfalls29,371mm erreicht; Stopp beim Absenken wegen RR
  0,447932rad/s. MaxRelativfehler1,104mm/0,003388rad, Backenmittel max3,281N,
  Peakobergrenze5,946N, lückenlose Kräfte. Beide Gesamtabläufe **FAIL** wegen
  konfigurierter Fingergrenze, keine gemessene Kartonlastgrenze. Folge komplett.
  Ergebnis `setup/tasks/carton_exploration_20261116_ladder01/result.json`.
- Cleanup-Audit Ladder01: beide Verbundstopps bestätigt, keine eigenen
  Testprozesse mehr vorhanden. Case00 sauber beendet; Case01 Supervisor erst
  beim SIGINT-Cleanup mit−11 beendet. Äußere Exec-Sitzung meldet143 trotz
  vollständig geschriebenem Zwei-Fälle-Ergebnis; nicht als sauberer Exit ausgeben.
  Eigener Supervisor-CLI jetzt Python-Signalhandler wie Runner: ROS-Kontext erst
  nach Executor-Join schließen, gemeinsamen Motioncode nicht verändert.
  Halbschrittfolge endet danach mit Exit0 und allen Launchkindern sauber;
  einmaliger positiver Cleanup-Nachweis, alte−11/143-Protokolle erhalten.
- Physikschritt explizit0,1–1ms konfigurierbar;0,5ms-Welt-Export geprüft,
  Build/8CTest-Suites und41Tests PASS. Gleicher500g-/5mm/s-Versuch mit0,5ms
  unter `carton_exploration_20261116_halfstep01` abgeschlossen: **FAIL** schon
  beim Lastübergang wegen RR-Tip0,210320rad/s über0,2. Nur0,970mm Hub,
  maxRelativfehler1,425mm/0,002857rad; Kräfte lückenlos, 10ms-Mittel bis3,035N,
  Peakobergrenze6,576N. Halbierung allein behebt die passive Geschwindigkeits-
  grenze nicht; Konvergenz/physische Belastungsgrenze ausdrücklich unbewiesen.
- Wiederverwendbare Vorpositions-Fixture: tools/prepare_manipulation_fixture.py
  aus geprüftem Plan, nur Anfangszustand einer neuen Welt, kein Reset/Anheften.
  Kollisions-/Kinematiksignatur gegenüber Quellszene gleich nachgeprüft.
  `carton_pregrasp_fixture_20261116_01/layout.yaml`; Runner unterstützt--layout
  konsistent in Prepare/Launch/Task. Kein Home-Anfahrtsnachweis daraus ableiten.
- Isolierter Kontaktversuch `carton_contact_dynamics_20261116_01` läuft:
  0,5ms, gleiche Masse/Reibung/Getriebe/0,1grobe+0,02feine Schließrate und2rad/s²
  Bremsgrenze. Beobachtungsgrenze Finger0,6 statt0,2; Armgrenze dafür0,025 statt
  0,05, damit volle worst-age-Stoppreserven erhalten bleiben (Vorprüfung14,6mm
  minimale Restreserve). **FAIL** beim Lastübergang wegen Relativfehler/Schlupf:
  2,023mm-Schwellenauslösung, insgesamt2,029mm/0,003740rad; nur1,135mm Hub.
  VierPads/Verbund beim Stopp gehalten; lückenlose Backenlasten bis3,062N im
  10ms-Mittel bzw5,413N-Peakobergrenze. Relative Verschiebung kann auch
  Greifercompliance enthalten, nicht allein als Reibschlupf interpretieren.
  Exakte22Quell-/Binärbindungen unter implementation_snapshot archiviert.
- Virtuelle Motorvorspannung getrennt vom Getriebe parametriert. Default weiter
  0,35Nm; höhere Motorgrenze nur explizit im Explorationsmodus, maximal2Nm.
  Native Getriebegrenze unverändert0,35Nm, gleiche100Nm/rad Getriebesteifigkeit.
  Neue Probe `carton_contact_preload_20261116_01`: Motorsteifigkeit30 statt10Nm/rad,
  Motorgrenze0,7 statt0,35Nm; restliche Dynamik-Fixture gleich. **PASS** des
  vollständigen5mm/s-Kontaktzyklus ab Vorposition:29,925mm Hub, maxRelativfehler
  0,252mm/0,001648rad, vierPads bis unterstützter Freigabe, finale Holds bestätigt.
  Armpeak0,024526rad/s, Fingerpeak0,099781rad/s. Kräfte lückenlos; Backenmittel
  maximal5,141N (10ms), Peakobergrenze5,356N. Beide deutlich unter50N-Nutzerreferenz.
  Exakte Quell-/Binärbindungen archiviert; World-Cleanup und äußerer Exit0 sauber.
  Keine kalibrierte Zuordnung zu echten Robotiq-Force-Settings. Build/42Tests PASS.
- Vollständiges Home-Profil mit gleicher Motorvorspannung,0,05Arm/0,15Finger,
  0,5ms und10mm/s unter `carton_preload_home_20261116_01`: beide Fälle **PASS**,
  lückenlose Kräfte. Hub29,9244/29,9243mm, maxRelativfehler0,274/0,244mm und
  0,001692/0,001637rad. Backenmittel bis5,380N (10ms), Peakobergrenze5,556N.
  Unterstützte Freigaben/finale Holds bestätigt, gleiche gebundene Taskquellen
  und vier Binärversionen archiviert. Keine maximale physische Geschwindigkeit.
  Nachfolgende Stoppmatrix01 mit getrennt dokumentierten Positiv-/Negativfällen unten.
- Fault-Runner unterstützt jetzt die drei alten scoped Fehlerarten unter neuem
  Profil, Injektion ab gewählter Hubhöhe (hier12mm nahe Tempopeak). Recorder
  kann nach Terminalzustand2s weiter rein lesend erfassen. Testcode vorhanden;
  neue geladene Stopps erst nach tatsächlichem Matrixlauf als bestanden melden.
- Stoppmatrix01/case00 member_stop **PASS**: absichtlicher Armstopp bei
  getragenem500g-Karton/10mm/s, vierPads erhalten, maxRelativfehler0,233mm,
  beide Holds mit Stillstandsfenster bestätigt (0,796s inklusive Messfenster,
  keine reine Bremszeit). Lückenlose Kräfte, Root-Fall accepted=true.
  Case01 runner_pause wurde **vor Injektion** durch verpasstes Agentenreview
  nach300s beendet; bestätigte Holds, kein geladener Ausfallnachweis. Eigenen
  Bedienfehler/Negativdaten erhalten, gezielter neuer Fall ist erforderlich.
  Case02 guard_pause hat beide Holds/Kontakte bestätigt, maxRelativfehler0,238mm,
  aber **FAIL**: passiver Fingerpeak0,167661rad/s über0,15-Profilgrenze.
  Frische/Stationarität/Griff gut, kein Lastproblem; Grenze nicht nachträglich
  gelockert. Originalmatrix mit beiden Fehlschlägen und äußerem Exit143 erhalten.
  Neue Matrix `carton_preload_faults_20261116_02` testet0,2Finger statt0,15 mit
  größerer vollständiger Geometrie-/Stoppreserve, sonst gleichem Profil.
  Matrix02 wurde durch parallele Taskquellenänderungen vor Injektion ungültig
  (case00/01); case02 konnte deshalb Guard/Supervisor nicht starten. Kein
  Fault-PASS, keine eigenen Prozesse verbleibend. Daten unverändert erhalten.
  Neue isolierte Matrix03 nutzt Snapshot `carton_frozen_baseline_20261116_01`
  mit erfolgreichen Home-Taskmodulen und erweiterter Abhängigkeitsbindung.
  Gemeinsamer Checkout/90°-Drehauftrag wird nicht zurückgesetzt.
  Matrix03 **3/3 PASS**: member_stop/runner_pause/guard_pause bei getragenem
  500g-Karton und10mm/s-Profil, vierPads erhalten, maxRelativfehler
  0,240/0,238/0,237mm. Beide Holds einschließlich Stillstandsfenster nach
  1,285/1,600/1,370s bestätigt (keine reine Bremszeit). Passive Spitze maximal
  0,173818rad/s innerhalb neuer0,2-Grenze; lückenlose Kräfte, Backenmittel
  <=5,146N/10ms, Peakobergrenze<=5,394N, Implementierungsbindung überall gültig.
  Alle eigenen Launchkinder sauber beendet/äußerer Exit0, cleanup-audit.json.
  Home02-Start zunächst wegen aktiver fremder Kartondrehwelt abgewiesen;
  begrenzte Warteschlange startet erst nach deren Ende. Anschließend
  `carton_preload_home_20261116_02` **2/2 komplette Home-Zyklen PASS** mit
  exakt demselben0,2Finger-Profil/gebundenen Code wie Stoppmatrix03:
  COM29,92485/29,92425mm, maxRelativfehler0,252/0,274mm und0,001797/0,001780rad.
  Lückenlose Kräfte, je Backe höchstens5,379N/10ms und5,504N Peakobergrenze;
  vierPads bis unterstützter Öffnung, finale Holds, Cleanup/äußerer Exit0.
  Gemeinsamer versiegelter5-Fälle-Index und exaktes Profil:
  `setup/tasks/manipulation_qualification_20261116/result.json`.
  Keine Maximum-/Hardware-/Drehfreigabe; alte Home-PASS behalten0,15Finger.
  Kompakter Prüfbericht docs/carton_dynamic_validation_2026-11-16.md;
  Skill wählt für neue schnelle Translationen explizit Profil+Frozen-Umgebung,
  historischer langsamer Default bleibt separat. Aktueller Experimenttreiber
  verlangt auch bei Fault-PASS zusätzlich gültige Implementierungsbindung;
  zwei gezielte Treibertests PASS (uwa-exploration-driver-test09.log).
- Aktionskatalog auf16Verträge erweitert: Kraftreferenzprüfung, Lastbeobachtung,
  rein virtuelle Fixturevorbereitung, endlicher Experimentfall und geladener
  Fehler-/Stoppversuch. Lokale Planungs-/Wächterabhängigkeiten inklusive
  gemeinsamer Motionkonfiguration, Holdbibliothek und RRT-Binärdatei werden in
  neuen Szenen zusätzlich gehasht (binding_scope v2). Vorherige Messberichte
  bleiben mit ihrer engeren ursprünglichen Bindung historisch erhalten; die
  aktuellen gemeinsamen Motiondateien anderer Arbeiten werden nicht verändert.
- Kräftevergleich muss tatsächliche Padlasten verwenden. Hersteller nennt für
  2F-85 eine Grasp-Force-Spanne20–235N; diese Geräteangabe nicht ungeprüft mit
  einzelnen Wandkontakten gleichsetzen. Primärquelle in docs/manipulation_pipeline.md.
- Validator liest bei Fehlversuchen Peaks aus gebundenem Stop-Diagnosebericht,
  getrennte Arm-/Fingermaxima und Dateihash. Vorhandene Reports werden nicht
  überschrieben, neuer Berichtname nötig. Historische Negativdaten nicht neu
  für geänderte Implementierung qualifizieren.
- Endlicher automatischer Geschwindigkeitsleiter-Runner implementiert unter
  tools/explore_manipulation.py; Agentenreviews bleiben Pflicht. Eigene Szenen,
  Recorder vor Arming, scoped Cleanup nur nach bestätigtem Stopp, gemeinsame
  Bewegungs-/Kraftauswertung. Erste zwei Fälle negativ; spätere stärkere
  Motorvorspannung besteht die oben dokumentierten500g-Gesamtzyklen.
- Recorder schreibt jedes empfangene100Hz-Kraftfenster zusätzlich zur20Hz-
  Bewegungsaufzeichnung. Neue Lastauswertung summiert je Backe/Wandfläche,
  vergleicht50N-Nutzerreferenz und meldet Lücken. Historische Nachweise nicht
  nachträglich mit neuen Profilen oder geänderten Validatoren umqualifizieren.

## Aktive Umsetzung der Kraftvalidierung, 2026-11-16

- Neue Nutzerwerte: leerer Karton500g; laut Nutzer hält eine einzelne Backe/
  Wandkontaktfläche50N locker aus. Masse als Nutzerangabe übernommen,50N als
  vorläufige Lastreferenz pro Kontaktfläche, ausdrücklich keine vermessene
  Bruchgrenze. Defaultmasse jetzt0,5kg, Reibung bleibt Annahme. Alte0,3kg-
  und0,2kg-Prüfnachweise unverändert/historisch, nicht auf0,5kg übertragen.
- Referenzmatrix `setup/tasks/force_reference_20261116_matrix01/` besteht alle
  zwölf Fälle (0,3/0,6kg ×1/0,5/0,25ms ×2Wiederholungen). Statische Kontakte,
  dynamische Kräftebilanz, freie bekannte Beschleunigung, Gelenkreaktion und
  90°-Messframe sowie Fallimpuls geprüft. Impulsstreuung0,1574%, harter
  Aufprallpeak vervierfacht sich bei Viertelung des Zeitschritts. Keine
  Material-/UR-Dynamikfreigabe daraus ableiten; Rohdaten und Fehlanalyse erhalten.
- Zusätzliche Datenwegfehler: Link-WorldVelocity/-Acceleration können nach
  Stillstand auf alten Werten bleiben. Impuls unabhängig aus Positionsänderungen
  prüfen. Ganze Kontaktmanifolds pro ungeordnetem Kollisionspaar auswählen;
  punktweise Rundungs-Dedup scheitert an separat bis1µm gecachten Geometrien
  und zählte Impulse doppelt. Fehlanalyse vor Korrektur archiviert.
- Neuer separater `force_telemetry`-Plugin: unsigned Kontaktlasten/Impulse,
  physikschrittweise Peaks und10ms-Mittel, Gelenkreaktionen im jeweiligen
  Gelenkframe. Eigener privater Topic `tasks/forces`; Szene bindet Observer-
  Binärhash. Vorhandener Clock-/Kontaktwächterpfad nicht ersetzt. Gerichtete
  Kraftzuordnung über Collision1→body1 weiterhin ausdrücklich nicht vertrauen.
- Build/alle5CTest-Suites PASS,28Pythonfälle+nativer Getriebetest. Neuer
  Beobachter/Recorder liest ohne Fahraktionen. Zellintegration force01 mit
  500g **PASS**:421Nachrichten, davon315stabile; Tisch-Normalkraft4,904986N
  statt erwartet4,905N. Alle4beobachteten Gelenkreaktionen vorhanden, keine
  fehlenden/invaliden Wrenches, physics-step-Peaks vorhanden. Kein Griff-/Hub-
  Nachweis. Daten `setup/tasks/carton_force_observation_20261116_01/`.
- Nutzer hat Beginn der Umsetzung beauftragt; bei fehlenden Angaben gezielt
  nachfragen. Aktives Ziel umfasst instrumentierte Simulation und darauf
  aufbauende dynamische Grenzsuche, nicht nur langsamere Wiederholung.
- Neuer separater Native-Logger `force_probe.cpp` und Runner
  `tools/validate_simulation_forces.py`: eigene endliche Gazebo-Welt ohne ROS,
  Controller oder Hardware. Bekannte0,3kg Last, Zusatzkraft1N, horizontale2N,
  Hebelarm0,15m, gedrehter Gelenkframe und Fallkontakt. Originalgreifwelt nicht
  gestartet; vorhandene Nachweise nicht überschrieben.
- Erster tatsächlicher Befund smoke01/02: Gelenkreaktion2,943N und−0,44145Nm,
  nach1N Zusatzlast3,943N/−0,59145Nm, gedrehter Frame plausibel. Spätere
  vollständige Zeitschritt-/Wiederholungsabnahme steht oben.
- Kritischer Datenwegfehler tatsächlich reproduziert: ContactSensorData liegt
  pro Kollision vor; dasselbe Paar wird doppelt und mit vertauschten Collision1/2
  gemeldet, rohe body1/2-Kräfte behalten dabei ihre Reihenfolge. Daher keine
  allgemeine gerichtete Körperkraft aus Collision1→body1 ableiten. Native
  GazeboPhysics-Quelle bestätigt diese Umordnung ohne Kraftumordnung/BodyIDs.
- Neue `force_metrics.py` dedupliziert Manifolds und liefert vorzeichenunabhängige
  Normal-/Tangentiallasten; fehlende/widersprüchliche Kräfte nicht als0 behandeln.
  Vier Regressionstests bestanden. Analytische Richtungszuordnung nur im
  bekannten horizontalen Referenzfall, nicht als generische Korrektur nutzen.
- Rohdaten unter setup/tasks/force_reference_20261116_smoke01 und_smoke02.
  Aktuell Pipeline-Auswertung und anschließende Temposuche in Arbeit;
  keine Kraftgrenze oder schnellere Roboter-/Hardwareausführung freigegeben.

## Neue Zielrichtung: dynamische Simulationsgrenzen ausloten, 2026-11-16

- Nutzer ergänzt bedingte Alternative: falls direkte Gazebo-Kraftmessung nicht
  robust/realistisch genug ist, UR auf passive federnd-gedämpfte Linearachse
  setzen und deren Auslenkung messen. Gewünscht hohe Steifigkeit/Dämpfung und
  Rückstellung; Erweiterung entfällt, wenn direkte Kraftmessung ausreicht.
- Lokaler API-/Binärbefund, noch kein Messnachweis: GazeboSim10.5.0 enthält
  ForceTorque-Systemplugin und JointTransmittedWrench-Komponente (N/Nm im
  Gelenkframe). gz-physics/DART9.5.2-Bibliothek führt GetContactsFromLastStep,
  GetJointTransmittedWrench, SetJointSpringReference und SetJointSpringStiffness.
  Contact-Protobuf enthält Wrenchfelder; bisheriger Taskexport verwirft diese.
  Vorhandensein dieser Schnittstellen beweist keine brauchbaren Messwerte.
- Direkter Pfad zuerst: Kontaktkräfte plus Gelenkwrench an geeigneter starrer
  Messstelle vergleichen. Bekannte statische Last (SummeKräfte≈mg) und Hebelarm,
  bekannte dynamische Last/Kräftebilanz, reproduzierbare Zeitschrittvariation
  prüfen. Frame/Vorzeichen und doppelte Kontaktmeldungen berücksichtigen. Bei
  Stößen zusätzlich Impuls und definierte Zeitfenstermittel statt nur Solverpeak.
- Rückstellfeder braucht konzeptionell keinen aktiven Antrieb: SDFormat kennt
  Federsteifigkeit, Ruhelage und viskose Dämpfung auch für prismatische Gelenke;
  Engine-Unterstützung lokal wie oben gefunden, praktische Umsetzung offen.
  Quasistatisch Kraftkomponente≈k·Auslenkung; dynamisch Dämpfung, Trägheit und
  Eigenbewegung/Eigenlast des Roboters berücksichtigen. Eine Achse misst nur
  eine Richtung. Sehr hohe Steifigkeit kann Numerik verschlechtern; Lagerung
  verändert die Roboterdynamik und muss in den tatsächlichen Welt-TCP-Frames
  auftauchen. Kein Nachführen starrer Greifoffsets zur Fehlerverdeckung.
- Beide Messwege verwenden denselben Solver; Lagerung kann Beobachtbarkeit
  verbessern, heilt aber keine falsche Kontaktphysik. Erst einfache bekannte
  Referenzfälle, dann Greifversuche/Temposweeps. Bislang nur Bestand/Quellen
  geprüft, keine Achse eingebaut und keine Kraftkalibrierung als PASS behaupten.
  Quellen: GazeboSensors9 ForceTorqueSensor, gz-physics9 GetContacts.hh,
  gazebosim/sdformat sdf16 sdf/1.12/joint.sdf und gz-physics9 DARTJointFeatures.
- Nutzer präzisiert: In Simulation schnelle Abläufe und ihre Grenzen erkunden,
  dabei hohe Kräfte/Kollisionen prüfen; reale Ausführung anschließend mit
  Reserve für unmodellierte Effekte. Das bisher sehr langsame Profil dient als
  historischer Inbetriebnahmebeleg, nicht als künftiges Optimierungsziel oder
  nachgewiesene Leistungsgrenze. Keine neue Hardwarefahrfreigabe.
- Künftige Auswertung: Zykluszeit gegen phasenabhängige Geschwindigkeit,
  Beschleunigung/Ruck, Kontakte/Kollisionen, Kontaktkräfte und Impulse,
  Greifer-/Armbelastungen, Schlupf/Objekt-TCP-Fehler und innere Verspannung.
  Beim starren Verbund weiterhin eine gemeinsame Zeitparametrierung; nur die
  jeweils greifenden Arme gehören dazu. Mehrere Masse-/Reibungs-/Lagevarianten
  prüfen, um günstige Einzelbedingungen nicht als robuste Grenze auszugeben.
- Bestand geprüft: `task_telemetry.cpp` exportiert Kontaktpaare, Positionen,
  Normalen, Eindringtiefen, Pads/Unterstützung, aber keine Kontaktwrenches.
  `contact_gripper.cpp` meldet angelegte Greifer-Aktuatormomente, ausdrücklich
  keine daraus gemessene Kontaktkraft. Arme nutzen idealisierten begrenzten
  Geschwindigkeitsantrieb; reale Drehmoment-/Dynamikfähigkeit nicht nachgewiesen.
  Starrer Karton bildet Quetschung nicht ab. Diese Modell-/Messlücken zuerst
  für belastbare Kraftgrenzen schließen; Geschwindigkeit allein ist kein Maß.
- Technische Konsequenz: getrennte Explorationsprofile und aussagekräftige
  Belastungsauswertung, dann automatischer Parametersweep mit erhaltenen
  Negativfällen und Wiederholungen. Reale Reserve aus Unsicherheit/Realabgleich
  ableiten; ein pauschaler Abschlag vom Simulationsmaximum reicht als Beleg nicht.
  Bewegungsgrenzen, Stoppreserve und Messfähigkeit gemeinsam betrachten.
- In diesem Gespräch Konzept/Bestand dokumentiert; noch kein schneller
  Physiklauf, keine bewegungswirksame Code-/Parameteränderung und kein neuer
  Kraft- oder Hardware-Prüfnachweis. Bestehende14Versuchs-Nachweise unverändert.

## Sichtbare Karton-Demonstration, 2026-11-16

- Laufzeitdiagnose auf Nachfrage: Die Ausführung nutzt ein konservatives
  Inbetriebnahmeprofil, keine ausgereizte Roboterleistung. Armgrenze0,05rad/s,
  gemeinsame8cm-Einfahrt mindestens30sim-s; Finger0,02rad/s frei/öffnend und
  0,004rad/s im Kontaktbereich; Objekt0,5mm/s. Quintische30mm-Hubtrajektorie
  benötigt114,75sim-s, mitRTF0,6 ca191Wand-s je Richtung (~24s im8×-Replay).
  Gemessene Phasen71: Anfahrt84s, Griff inkl. Einfahrt/Beobachtung185s,
  Hub inkl. Kompilierung/Halten224s, Absetzen inkl. Kompilierung228s, Öffnen68s.
  Achtfach bezieht sich auf aufgezeichnete Wandzeit, daher ca4,8×Simutempo.
  Native Armantriebe begrenzen zusätzlich fest auf0,05rad/s; YAML allein zu
  erhöhen reicht nicht. Diagnose ändert keine Grenzwerte/Quellen der Bewegung.
- Nutzer möchte einen Ablauf sehen. Erfolgreichen Kontaktlauf71 vom14.11. als
  ausdrücklich gekennzeichnete8×-Wiedergabe gemessener Gelenke/Kartonpose in
  eigenem RViz und kontrastreichem englischem Bedienfenster geöffnet.
- Neuer rein visueller Player `tools/replay_manipulation.py`, Anleitung
  `docs/manipulation_pipeline.md`. Prüft Originaltrace/Robotermodell/Ergebnis
  gegen gespeicherte Qualifikationshashes. Keine neue Kontaktphysik, keine
  Änderung des Originalnachweises, keine Controller/Actions/Fahrbefehle.
- Eigene Displaytopics `/uwa_grasp_replay/{joint_states,robot_description,tf,
  tf_static,markers}` auf64/LOCALHOST. Tatsächliche passive Gelenkwerte im
  visuellen Modell statt neu berechneter Mimicwerte. Keine Originalmodelle ändern.
- Aktuelle Ansicht `setup/tasks/carton_replay_20261116_03/`; Wiedergabe mit
  Play/Pause/Restart, Zeitleiste und Tempoauswahl.8× etwa2min, Ende bleibt
  sichtbar; Restart setzt zurück und pausiert, danach Play replay. Schließen
  beendet nur eigene RViz-/State-Publisher-Kinder. Hardware unberührt.
- Zwei GUI-Startfehler erhalten:01erbte Snap-GTK-Laufzeit,02Qt5-Enum unter
  Qt6. Behebung prozesslokale GTK-Pfadbereinigung/Qt6-Enum; exakt eigene
  verwaiste02-Anzeigekinder beendet, keine anderen Dienste.03läuft.
- Externe Bildschirmaufnahme auf diesem Wayland-Desktop nicht verfügbar;
  keine daraus behauptete Screenshotprüfung. RViz-Start/GL-Log, Playerzustände
  und vollständige Ablaufphasen direkt geprüft; kein neuer Griff-PASS.

## Modulare Karton-Greifpipeline: aktuelle Qualifikation, 2026-11-14

- Nutzerauftrag: modulare agentbedienbare Skills; zwei rechte URs greifen den
  leeren Karton, heben30mm, halten mindestens2s, setzen ab und öffnen. Agent
  prüft Strategie, Plan und Vorposition selbst. Ausschließlich Simulation.
- Implementiert: `uwa_cell_tasks`,11Skill-Verträge, CLI/Review/HTML-Vorschau,
  Ressourcenlease, SHA-gebundene Szene/eigene Quellen/Binärdateien/Physik,
  bildbasierte Beobachtung, unabhängiger FCL-/Kugel-/Kontakt-/Schlupfwächter
  und Ressourcen-Supervisor. Einstieg `.agents/skills/uwa-manipulate/SKILL.md`,
  Anleitung `docs/manipulation_pipeline.md`, Nachweismatrix unter
  `setup/tasks/manipulation_qualification_20261114/result.json` (Testmatrix mit
  Einschränkungen; nominale Wiederholsicherheit ausdrücklich nicht nachgewiesen).
- Ab bestätigtem Kontakt ein Objektframe, eingefrorene Objekt→TCP-Offsets,
  ein12Gelenkcontroller/eine gemeinsame Zeitparametrierung; Geometriekern in
  `match_cooperative_handling.rigid_object`. Andere Arme gemessene Hindernisse.
  Verbundstopp erhält Griff; kein automatisches Öffnen/Home/Resume oder
  Loaded-Reset. Freigabe nur unterstützt/stationär mit Guard-Ack, gemessenem
  Öffnen aller12FingerDOFs und finalen Holds. Kein künstliches Anheften.
- Isolierte Welt `uwa_grasp_lab`, `/uwa_grasp_validation`, Domain64/LOCALHOST,
  private Uhr/TF. Hauptsimulation und Hardware unangetastet.100Hz native ECM-
  Telemetrie,1ms DART9.5.2/RTF0,6; bildsensorfreie Physik plus statischer
  Snapshot-Renderer. Bildpose ohne Wahrheit als Prior; OAK VALID, Wrist LOST
  ausgeschlossen. Wahrheit nur Rendererdefinition/Audit/Auswertung/Guard.
- Physikannahmen: starrer2,5mm-Karton, elastische energieausgeglichene Kopplung
  100Nm/rad, Motor10Nm/rad/Cap0,35Nm, Fingerdämpfung0,08Nm·s/rad. Masse0,3kg,
  Reibung0,6 unvermessen. Experimenteller Default0,5mm/s mit positivem Home-
  Einzelbeleg71, aber fehlgeschlagener Wiederholung74. Frühere positive
  Fixtures/leichte Variante sowie Memberstop72 bei expliziten1mm/s. Grenzen:
  rechte Gelenke inkl. passiver Finger0,05rad/s+1e-8, Relativlage2mm/1°.
- Aufrechter Karton/horizontale Unterstützung; Neigung>2° abweisen. Greifer
  gravitationsparallel mit Bild-Yaw. Gegenüberliegende untere Wandbereiche,
  ganze nominale Padbox3mm unter Ausschnitten.40konvexe Teile/7native Boxen
  erhalten offene Geometrie. Vier interne Gelenknachbarschaftsausnahmen wie
  Bestandsmodell, im Python-ACM und nativen RRT identisch.
- COM-Hub explizit30±2mm: Scene bindet `lift_reference_point_object_m`
  [0,201215;0,170013;0,048267]m aus demselben uniformen Materialmodell wie
  Physikinertia. Asset-/Objektkommandoframe bleibt unverändert; Eckursprung-Hub
  separat diagnostisch. Erlaubtes Kippen kann dort deutlich weniger Hub ergeben.
- Fünf aktuelle vollständige **DONE + unabhängige Trace-PASS**:

  | Run / Szene | Profil / Start | COM-Hub mm | maxRelativfehler mm / rad |
  | --- | --- | --- | --- |
  |64 / V88|0,3kg/0,6,1mm/s, Vorpositions-Fixture|29,921|0,315 /0,002299|
  |65 / V88|dasselbe, Wiederholung ohne Reset|29,821|1,284 /0,009797|
  |67 / V89|0,2kg/0,4,1mm/s, Home|29,809|1,424 /0,010912|
  |68 / V89|leicht, Wiederholung ohne Reset|29,813|1,581 /0,012105|
  |71 / V95|0,3kg/0,6,0,5mm/s, Home|29,893|0,511 /0,003783|

  Alle Pads/Offsets unter Last erhalten, unterstützt gemessen geöffnet, Gruppe
  aufgelöst und finale Holds bestätigt. Nur diese Paare/Startbedingungen sind
  belegt; kein allgemeiner Masse-/Reibungsbereich oder Hardwarebeleg.
- Abgewiesene aktuelle Versuche bleiben erhalten:66/V89 vor Kontakt wegen
  eigener Joint-Empfangslücke0,200368s;69/V90 schwer0,4kg/0,8 bei1mm/s wegen
  passivem Fingertip0,078645rad/s;70/V94 nominal Home bei1mm/s wegen0,059102.
  Jeweils unterstützt, beide Holds bestätigt;69/70 alle Pads erhalten. Keine
  Grenzlockerung, kein positiver Hubnachweis und kein Resume dieser Läufe.
- Run72/V91 Memberstop unter frei getragener Last **PASS**: alle Pads erhalten,
  maxRelativfehler0,27095mm/0,002014rad, stationäre beidseitige Holds nach
  0,394s einschließlich Bestätigungsfenster. Rezept erwartungsgemäß FAILED
  mit bestätigtem Stopp. Virtuelle Episode danach ohne Öffnen/Resume beendet.
- Run73/V92 scheitert **vor Runnerpause-Injektion**: passives Rear-Right-
  Fingertip0,070306rad/s, beide Holds bestätigt, Objekt unterstützt/all4Pads.
  Kein bestandener Runner-Ausfalltest; zeigt weitere Start-/Kontaktstreuung
  des1mm/s-Fixtureprofils. Der langsame nominale Wiederholungsversuch
  Run74/V96 nominal0,3kg/0,6/0,5mm/s aus Home ebenfalls vor Injektion
  abgewiesen, passives Rear-Left-Fingertip0,052335rad/s, unterstützt/all4Pads,
  beide Holds bestätigt. Nominales0,5mm/s-Profil hat positiven Einzelbeleg71,
  aber **keine Wiederholsicherheit**. Bestandene Ausfalltests75/V98 Runnerpause
  und77/V100 Guardpause nutzen leichte0,2kg/0,4-Variante bei0,5mm/s aus Home.
- Run76/V99 Wächtertest schon vor Fahrt/Griff im Reset abgewiesen: linker
  passiver Finger nicht ruhig (Diagnose-InnerKnuckle−0,08869rad/s), LF-
  Geschwindigkeitsursache gelatcht. Unterstützt, rechte Pads frei, beide rechten
  Holds bestätigt; keine Injektion. Eigene Welt beendet;77/V100 frischer Versuch.
- Störfallvertrag: `tools/test_manipulation_fault.py` friert Auswertebaseline schon bei unterstützter
  Gruppenbildung ein, injiziert erst bei≥5mm freiem Hub/all4Pads. Stoppbeleg:
  ≥0,3s Positionsfenster Arme≤10µrad/Objektachsen≤0,1mm/Rotationselement≤1e-4,
  beide Holds anschließend0,6s behalten, Kontakte/Relativgrenzen/frische Daten,
  erwartetes FAILED mit bestätigtem Stopp. Nur vorhandene bestandene Reports zählen.
- Run75/V98 Runnerpause unter frei getragener leichter0,2kg/0,4-Last bei
  0,5mm/s aus Home **PASS**: frischer CLEAR-Zustand vor Injektion, all4Pads
  erhalten, maxRelativfehler1,42098mm/0,010883rad, beidseitige stationäre Holds
  nach0,920s einschließlich Bestätigungsfenster, erwartetes FAILED mit Stopp
  bestätigt. SIGCONT nur zur Fehlerbehandlung, kein Bewegungs-Resume.
- Run77/V100 Guardpause unter frei getragener leichter0,2kg/0,4-Last bei
  0,5mm/s aus Home **PASS**: all4Pads erhalten, maxRelativfehler1,41896mm/
  0,010866rad, stationäre beidseitige Holds nach0,617s einschließlich Fenster,
  erwartetes FAILED mit Stopp bestätigt. Alle drei Last-Störfälle72/75/77
  bestanden. Eigene Welt/Nachfahren danach ohne Öffnen/Resume beendet;
  Hauptsimulation und Hardware erhalten. Keine pauschale Griffqualifikation.
- Startverfahren: Recorder `tools/trace_manipulation.py RUN --prepare` und ggf.
  Fault-Probe vor Runner, Trace-Datei prüfen/Discovery abwarten. CPU-Profil nur
  eigene Launch-Nachfahren Physik0–3/Guard4/Supervisor5, Runner6–11; keine CPU-
  Reservierung/Echtzeitgarantie. Keine neuen ROS-Teilnehmer während armiertem
  Lauf; beobachtete DDS-Pausen nicht abschließend erklärt. Frischegrenzen
  unverändert. Zwei12fach-Beobachtungsstresstests PASS, maxAbstand131,44ms<150ms.
- Peaks jeder empfangenen100Hz-Rechts-JointState bis unbeladenem Reset gelatcht;
  keine5%-Basisknoten-Toleranz übernehmen. Open braucht tatsächliche Finger
  |q|<0,02 und|v|<0,003 für0,3sim-s plus Actionerfolg. Nur ListControllers
  lesend einmal wiederholen. Stopp sendet beide Anfragen vor dem Warten;
  Bestätigung benötigt frische Zustände und aktive unabhängige Holdcontroller.
- Software:24PythonTests plus nativer Energie-/Reaktions-/Dämpfungstest, voller
  finaler Lyrical-Build einschließlich Manifestabhängigkeiten und CTest4Suites
  PASS,24Pythonfälle+nativer Test. colcon zählt28inkl. CTest-Wrappern, keine
  28unabhängigen Unitfälle. Skill quick_validate und separater Traceaudit aller
  Injektionsvorzustände PASS. Alle11genutzten Szenen-/Quellen-/Binärbindungen
  nach Build unverändert geprüft. Eigene Greiflaunches0, Hauptlaunch52643 läuft.
  Sealed `software-verification.json`/`fault-baseline-audit.json` im Nachweisordner.
  Historische Entwicklungsversuche/Quellstände in `work/carton-grasp-pipeline.md`;
  alte PASS nicht als Nachweis der aktuellen Byteversion ausgeben.

## CPU-Objektpose mit statischem und dynamischem Modus, 2026-11-13

- Neuer Nutzerauftrag: bekannte digitalisierte Assets wiederfinden, statisch vor
  Manipulation Genauigkeit priorisieren, dynamisch Onlinegeschwindigkeit.
  Ursprünglich zunächst Intel-Mini-PC; zusätzlicher NVIDIA-Rechner seit13.11.
  ausdrücklich für isolierte FoundationPose-Versuche verfügbar (siehe oben).
- Neues Paket uwa_cell_tracking: assetgebundeneSIFT-/3D-Merkmale ohne bekannte
  Objekt-/Boardpose, globale/panelweisePnP-Hypothesen,3-Frame-Static mit robustem
  Fit, dynamischesLK/PnP und Wiederinitialisierung. ROS-Pose/Status/Overlay,
  expliziteLocalize/Start/Stop-Services; Worker unabhängig vom ROS-Spin.
- Echte OAK opt-in auf65/LOCALHOST mit bestehender Fotolease. VorhandenerSDK-
  Previewworker unterstützt zusätzlich1600×1200/10fps und tatsächlichesK/D/
  SDK-Bildalter; alte2fps-GUI-Vorschau unverändert. Keine Roboteraktionen.
-6Kernel-/Referenztests und isolierterROS-Replay71 bestanden. Begrenzterrealer
  OAK-Lauf:188Frames/10,012fps, statischVALID0,42pxRMS/Ergebnisalter1,39s;
  116OnlineVALID-Ausgaben inca12s, Kernmedian7,53ms, maxSDK-Bildalter128ms.
  24Boardecken/0,256pxRMS prüfenAusgabeoptik separat, nicht alsTrackerprior.
  OAK danach geschlossen/Fotosperrefrei. Keine Dienste/Roboter neu gestartet.
- Grenzen: Objekt stand still; echte Bewegung/Verdeckung/Wiederfinden und
  absolute Kontrollmaße offen. OAK/RR im finalenBildtest brauchbar; LR/RFLOST.
  Frühere falsche Entwicklungshypothesen erhalten, keine universelle Freigabe.
  VALIDbedeutetBildkonsens; manipulation_approved/absolute_accuracy bleibenfalse.
- AusgabeT_camera_object, keine ungeprüfte Welt-/Basisübernahme. Näherungsmodell
  und vorläufige Weltkalibrierung begrenzen Genauigkeit. M3T und FoundationPose
  als späterevergleichbare Backends geprüft, noch nicht angebunden.
- Bedienung docs/object_tracking.md; Einstieg scripts/object_tracking.sh
  oak/localize/track/stop/view. Rohdaten setup/tracking/carton_cpu_20261113/.

## Texturierter Karton als Zell-Asset eingefügt, 2026-11-13

- Nutzer wünscht das fertige Modell als wiederverwendbares Asset und in der
  virtuellen Zelle an der real beobachteten Position. Paketiert unter
  uwa_cell_description/assets/carton_avocado_v1/: COLLADA+vierJPEGs für beide
  Renderer, GLB/STL/STEP und Manifest mit Herkunft/Hash/Qualitätsgrenzen.
- Zentrale Instanz scene_objects/avocado_carton in cell_layout.yaml; Ursprung
  aus Bildfit relativ zum rechtenChArUco-Board, dessen bestehende Zellpose
  wird weiterverwendet. Unterer Mittelpunkt etwa(-0,013;0,007;0,903)m zwischen
  denTischen. Keine neue absolute Weltkalibrierung oder höhere Genauigkeit.
- Separater statischer Visualspawn, ROS-TF asset/avocado_carton und texturierter
  RViz-Marker teilen eine Pose. Normaler Zellstart lädt automatisch; laufende
  Zelle ergänzt durch cell.sh assets, Reloadservice/uwa_cell/scene_assets/reload.
  Eigener Benutzerdienst uwa-cell-assets; bestehendeZelle nicht neu gestartet.
-17Offlineprüfungen bestanden; liveGazebo-Modellpose/TF/Marker abgeglichen,
  Zell-PID274663 unverändert. RViz geöffnet; keine Texturladefehler imLog.
  Direkter RViz-Renderexport visuell geprüft; Fototextur und Position sichtbar.
  Vorschau output/images/carton_in_virtual_cell.png.
  Sim-OAK vom parallelenReplay entfernt, daher dessen Einstellungen bewahrt
  und kein Kamerabildnachweis behauptet. Bericht unter Kartonordner/scene-live/.
- Visual-only ohne neue Gazebo-/MoveIt-Kollision oder Hardwareaktionen;
  laufenden Planungsvergleich erhalten. Keine vollständigen Rohfotos/Sitzungen
  ins Asset kopiert. Bedienung/Grenzen docs/carton_scene_asset.md.

## Großer Karton aus gespeicherten Farbfotos rekonstruiert, 2026-11-13

- Nutzerauftrag nach Scan:3D-Modell des neuen offenen Avocado-Kartons.
  Erster assistierter CAD-Entwurf ca.404×342×163mm, Boden/vierWände mit
  nachgezeichneten Griff-/Oberkantenausschnitten und optionalen Fototexturen.
  Dateien setup/digitization/carton_multiview_20261113/cad/: STEP/mm, STL/m,
  GLB/m, editierbare SCAD/mm; carton_preview.png im übergeordneten Ordner.
- Alle25Originalfotos geprüft,20metrisch verwendet. LF wegen widersprüchlicher
  nativer Bildgeometrie ausgeschlossen; seine Kalibrierflags unverändert.
  LR/RF/RR eigene passende HD-K/D, OAKWerksoptik; keine VGA-Substitution.
  Direkt sichtbares rechtesBoard und aus Trainingsbildern geschätzte Relation
  beiderBoards, keine nominellen Tischabstände/FK/Hand-Auge-Weltanker.
- ZehnFit-/zehnPrüffotos, davon vierOAK-Prüfungen nur zeitliche Wiederholungen.
  Prüfkameraposen nur ausBoardpunkten. MedianPunkt-RMS bei1600px Breite:
  Training14,05px/Prüfung13,68px. Daher ausdrücklich keine metrische Freigabe
  oder Millimetergenauigkeit. Reale Kontrollmaße und Ursache der systematischen
  Kameradifferenzen offen. Dicke2,5mm angenommen; verdeckte Details vereinfacht.
- STEP-Rückimport/Einheiten, geschlossenes zusammenhängendes STL292Dreiecke,
  GLB-Rückimport, Transformationsrichtung und Kontur-Rückprojektion geprüft.
  Gezielte100/70px-Störung sämtlicher Prüf-Objektpixel verändert Fitparameter
  nicht. Ergebnis/Hashes/Prüfungen lokal erhalten; Vorschau visuell geprüft.
- Neue Offlinewerkzeuge tools/reconstruct_carton_scan.py,
  export_scanned_carton.py, preview_scanned_carton.py. Keine Kamera-/Arm-
  oder Dienstaktionen, keine Profil-/TF-/Gazebo-Änderung, keine Installation.
  Anleitung und Grenzen: docs/carton_multiview_2026-11-13.md.

## Kamerabeleuchtung im Leerlauf geprüft, 2026-11-13

- Nutzer erinnert nach Scanabschluss an Abschalten der Kamerabeleuchtung bei
  Nichtbenutzung. Bestehende Regel gilt weiter: erster Foto-/Videonutzer an,
  letzter Nutzer aus; aktive parallele Nutzer erhalten.
- Keine laufende Kameranutzung und alle vier Nutzungssperren frei. LED0 bei
  LF/LR/RF/RR bereits beim ersten Readback, nochmals explizit gesetzt und erneut
  an der Kamera bestätigt. Automatischer LED-Wächter aktiv/aktiviert; aktive
  Nutzungsintensitäten der Profile beibehalten. Kein aktueller Abschaltdefekt
  nachgewiesen, keine Arm-/Treiber-/Programmaktion.
- Historischen Rolloutstand bereinigt: LR-Job ist seit12.11. COMPLETE; alle vier
  Kameras verwaltet. Nachweis setup/wrist_lighting/idle_check_20261113/verified_off.json.


## Vierarm-Kollisionswächter/PTP: Simulationsvergleich abgeschlossen, 2026-11-13

- Implementiert in `uwa_cell_motion`, ROS 2 Lyrical, ausschließlich Domain64 /
  Partition `uwa_cell_sim` / LOCALHOST. Keine Hardwarekommandos. Anleitung
  `docs/four_arm_motion.md`, Arbeitseintrag `work/four-arm-collision-planning.md`.
- Unabhängiger 10-Hz-Wanduhrwächter für LF/RF, LF/LR, RF/RR, LR/RR; keine
  Diagonalen. Konservative Volumenabdeckung mit216Kugeln für68modellierte
  Körper einschließlich offener Finger, Wrist und Kameras. Abstände zwischen
  Kugeloberflächen; Relativbewegung aller Glieder, Datenalter und Bremsreserve.
- Separater Supervisor mit Paarleases/Heartbeat und Ressourcen-Haltecontroller
  je Arm. Paarverletzung verriegelt beide Arme, Mehrfachfehler deren Vereinigung;
  Zustandsverlust betrifft Nachbarschaften. Teilreset unabhängiger Arme möglich.
  Topic-Kommandos/Aktivierungsversuche erfasst, keine automatische Wiederaufnahme.
- Gemeinsame vollständige Start-/Zielschnittstelle, kartesisch explizit `world`,
  gleiche IK, native OMPL-RRTConnect-Gesamtplanung und unabhängiger CF-inspirierter
  Rollout ohne RRT-Fallback. Gemeinsame MoveIt/FCL-Endprüfung nach Quintik-Timing,
  alle Selbst-/statischen Kollisionen; diskrete Prüfung≤5mrad, kein CCD-Nachweis.
  Planen/Vorschau/Ausführen getrennt. Gemessene Mehrarm-Fortschrittsbarrieren und
  Restwegprüfung nach Paarstopp; nicht nur gleiche Startzeitstempel.
- Offline **300/300** Versuche:30Aufgaben×5Seeds×2Methoden,10s Budget.
  RRT102/125 gültige Zielversuche erfolgreich, CF115/125; je25absichtlich ungültige
  Ziele abgewiesen. Kreuzungen3/25gegen15/25.250unveränderte Ergebnisse mit
  Provenienz zu v2,50korrigierte Kreuzungsversuche. Aussage nur für diese Suite.
- Agentenempfehlung anhand dieser Messung: für freie PTPs vorläufig Feldansatz
  wegen höherer Erfolgsquote bevorzugen, RRT als Referenz behalten. Einzelne
  RRT-Wege kürzer; keine allgemeine Überlegenheit oder Nutzerfestlegung behaupten.
- Alle217erfolgreichen Pläne in Gazebo durch55verschiedene vollständige Start-/
  zeitparametrierte Bahnen repräsentiert; exakte Wiederholungen ausdrücklich
  verlinkt. **Alle55Zielbahnen begonnen,53erfolgreich,2gestoppt**: RRT-Kreuzung03
  Seed0 wegen Greifer0,05835rad/s über Betriebsgrenze0,05; Seed1 wegen152ms
  Zustandslücke. Verlinkte Versuche: RRT100/102Fahrerfolge, CF115/115.
  Keine Fehler weggefiltert: Bericht zählt zusätzlich sämtliche historischen
  Entwicklungs-/Anfahr-/Abbruchdaten, insgesamt118Versuche/18Fehlschläge über
  unterschiedliche Entwicklungsstände. Diese sind keine homogene neue Testserie.
- Endbericht `setup/logs/uwa-motion-comparison-v4/report.html` samt PNG/JSON,
  Fehlversuchsliste `report.attempts.json`, Quellrevisionen `runtime-manifest.json`.
  Audit `validation-audit.json`: eine Kollisionssignatur cdeff888…461504/ein
  Mesh-Satz, geplantes vmax0,05rad/s/amax0,09976rad/s²; größter aufgezeichneter
  Endfehler erfolgreicher Fahrten0,461mrad bei1mrad Zieltoleranz.
- **66Motion-Pytests PASS**,70mit4CTest-Wrappern; zusätzlich36gezielte Gazebo-
  Modell-/Overview-Tests PASS. Finale vollständige Liveabnahme
  `setup/logs/uwa-motion-live-guard-check-executor-acceptance.json`: Paarumfang,
  unabhängige Weiterfahrt, Mehrfachfehler, Datenverlust/Teilreset, Pause/STATE STALE,
  Topic-/Aktivierungssperre, Wächterverlust und verriegelte Wiederkehr PASS.
  Gemessen85ms bis erste Armspeed≤3mrad/s bei0,04756rad/s vor Fault,129ms knappe
  Paarlease,400ms bis Watchdog-Ressourcenhalt. STOPPED verlangt zusätzlich300ms
  geprüfte Historie. Einzelbeobachtungen, keine garantierten Worst-Case-Werte.
- Gegenseitige Ausfalldiagnose/RViz: GUARD LOST löscht alte Kugeln und zeigt
  Holds/Standstill UNCONFIRMED unabhängig. STOP ADAPTER LOST verriegelt Diagnose;
  Adapterverlustprüfung bei bereits gehaltenen Armen, kein Nachweis aktiver
  Stoppwirkung eines vollständig ausgefallenen Backends. RViz-Prüfbilder unter
  setup/logs/uwa-motion-rviz-{held-final,guard-lost}.png. Verlust-Snapshothelfer
  schrieb Bild, stürzte danach beim Beenden ab; Geometrieprozess wieder fortgesetzt.
- Unbeanspruchte Greifertriebe werden an gemessener Pose gehalten, aktive Besitzer
  nicht verdrängt. Ruhende Anschläge zeigen bis5,1µrad Zittern: Werkzeugruhe über
  ≤10µrad Span/300ms und Betriebsgeschwindigkeitsgrenze, Arme weiterhin3mrad/s.
  Echte langsame Bewegung besteht Gegenprobe nicht. Keine Lockerung von Frische,
  Kollisionsabständen oder Betriebsgrenzen wegen Ausführungsfehlern.
- Profilgestützte Executor-Optimierung: unbenutzte Standard-QoS-Warncallbacks
  ausgelassen, explizite Callbacks/Transport-QoS/Clock/Frische bleiben.9,66→4,16Mio
  Profilaufrufe/6s; reale Wächter-CPU nur46→42Prozent eines Kerns. Kein Nachweis,
  dass sämtliche nichtdeterministischen Zustandslücken beseitigt sind. Kaltstart,
  dauerhafter Client-Executor und gemeinsame native/Python-Grenztoleranz1e-8rad
  ebenfalls geprüft. Reguläre Wächterstopps speichern jetzt Diagnose-Snapshots.
- Vergleich ohne Bildrendering (`image_sensors:=false`), Kollisionskörper,
  Inertien, Kalibrierung/TF und OAK-CAD identisch; normale Zellvorgabe bleibt Bilder
  an. Welt-/Tischanker vorläufig, OAK-Stativ/Karton weiterhin visual-only. Hardware,
  reale Stoppreserve und produktive Greiferregelung bleiben eigene Ausbaustufen.
- Abschluss: alle vier Ressourcen gehalten, stabile Antriebe gemessen;
  `setup/logs/uwa-motion-final-checkpoint.json`. Eigene Dienste `uwa-cell-sim` und
  `uwa-cell-motion` laufen, Vergleich beendet; keine automatische Weiterfahrt.
  Fremde Arbeiten/Dienste erhalten. Nutzer-Neustartpause erledigt; späteres
  unbeabsichtigtes SIGTERM in Historie erhalten, Ursache ungeklärt.

## Vierarm-Scan und OAK-Update abgeschlossen, 2026-11-13

- Alle vier Arme haben ihre fünf geplanten Stellungen erreicht. Gültiger Index:
  `setup/digitization/four_arm_scan_20261113/scan_dataset.json` mit **25/25 Fotos**,
  20 Wrist-Ansichten und fünf OAK-Aufnahmen, 21 verschiedenen Kamerastandpunkten.
  Native 2592×1944 bzw. 8000×6000, feste Foki, Bildhashes, Sollpose und tatsächlicher
  Stillstand geprüft. Mindestens12Boardecken je Wrist-Bild,24in jedem OAK-Foto.
  Bildübersicht `scan_all_rounds.jpg`; metrische Rekonstruktionsgenauigkeit noch
  nicht ausgewertet. Keine Qualitätsflags früherer Fehlversuche umgeschrieben.
- OAK nach zunächst erfolgreichem Nutzerneustart erneut Pipeline-Startfehler.
  Nutzer hat darauf das angebotene OS-Update ausdrücklich mit „ja bitte“ erlaubt.
  Herstellerpaket erneut SHA256-/Identitäts-geprüft, exklusiver Kamerazugriff,
  OTA **1.32.1→1.47.0**, Agent **0.28.0**, gleicher OAK4-D R9/1479883285.
- Werkskalibrierung vor/nach Update exakt gleich: SHA256 a07141cce771738c713df4ef62f3719ed2ede411c556bc920089270cc4689eae.
  Produktiver SDK bleibt3.12.0; keine Kalibrierprofile/TFs oder Gazebo-Montagen
  verändert. Quellen/Paket/Updaterlog unter setup/oak4/stability_20261113/ota/.
- Nach OTA15direkt aufeinanderfolgende native8K-Start-/Fotozyklen bestanden:
  Fokus116, gleiche Geräte-ID, durchgehend steigende Gerätezeit, verschiedene
  vollständig dekodierte Bilder. Danach kompletter Fünfkamera-Bildsatz an den
  bereits erreichten Endstellungen mit unabhängigem Stillstandsaudit PASS.
  Insgesamt16nativeOAK-Aufnahmen nach Update erfolgreich. Das ist ein begrenzter
  Wiederholungsnachweis, keine Zusicherung dauerhafter Fehlerfreiheit.
- Letzte Gruppe ersetzt nur die zuvor fehlgeschlagene letzte Aufnahme. Initiale
  gültige Gruppe nach Nutzerneustart, Runde2–4 aus run03_rest, Runde5 aus
  last_round_post_os147. OAK-OS1.32.1 in Gruppen1–4,1.47.0 in Gruppe5 ist im Index
  ausdrücklich festgehalten. Statisches Board vor/nach OTA:24gemeinsame Ecken,
 0,52nativePixelRMS Bildverschiebung; enthält Detektions-/Licht-/Montageeinflüsse,
  keine neue Genauigkeitskalibrierung.
- Bewegungswächter, Kameraarbeit und read-only Stillstandsaufzeichnung sind
  getrennte Prozesse; Frische-/Driftgrenzen unverändert. Bildprozess verwendet
  zwei OpenCV-Threads, temporäres Planungsobjekt wird vor Fotos nicht gehalten.
 87gezielte Softwaretests vor OTA PASS; Firmware zusätzlich real wie oben geprüft.
- Während des letzten ursprünglichen Fotoversuchs wurden Telemetrielücken und
  ein2,18-s-PC-Treiberzyklus protokolliert; Stopp/Stillstand bestätigt. Diese
  Fehlversuche bleiben als Diagnose erhalten. Hostressourcen für spätere
  automatische Hardwarefahrten weiter beachten; Ursache nicht abschließend belegt.
- Während OTA und Nachprüfung **keine Arm-, Power-, Brake- oder Programmaktion**.
  Letzte reale Prüfung: alle vier RUNNING/NORMAL, Stillstand bestätigt,
  Fahrcontroller inaktiv. Linke External-Control-Programme bleiben STOPPED,
  rechte PLAYING; kein automatisches Rückfahrziel. Keine weitere Fahrt offen.
- Abschlussnachweis: setup/oak4/stability_20261113/ota/update_validation.json.
  Bedienung: docs/parallel_object_scan.md und OAK-Repo OAK4_STABILITY_2026-11-13.md.

## Schnellere HD-Fotos und nutzungsabhängige LEDs,2026-11-12

- Nutzerauftrag: HD-Aufnahme beschleunigen ohne wesentliche Qualitätseinbußen,
  Wrist-LEDs aller vier Arme nur während Foto-/Videonutzung. Andere Agenten
  parallel erhalten; keine Armfahrt oder Profiländerung aus dieser Arbeit.
- Doppelte nativeVGA-Rückschaltung entfernt, tatsächliches Originalformat/
  Pixelformat/Bildintervall nach Visionneustart unabhängig geprüft. Strenger
  expliziter Rückfall; vollständige Settings-/Sensor-/Watchdog-Prüfungen erhalten.
  Originalworker/-helfer für fremde eingefrorene Reihen unverändert.
- Bei identischem LED30%-Ablauf RF18,221→15,271s(−16,19%), CB3LF16,522→13,714s
  (−17,00%). RF je24Ecken, praktisch gleiche Schärfe/Clipping, mittlere Ecken
  RMS0,064px auseinander; Nutzer bestätigt statische Szene. Kein Genauigkeits-
  nachweis. RR-TestPASS,24,36s wegen vorhandener strenger Legacy-ROI-Korrektur.
- LED-Nutzung über gemeinsame Prozesssperren. Erster Nutzer an, letzter aus;
  Guardian `uwa-wrist-led-policy.service` installiert/aktiviert, Absturzbereinigung
  mit zwei echten Viewern geprüft: erster Crash bleibt an, letzter Crash aus,
  alle übrigen Settings identisch. CLI/GUI/HD/Kalibrierung/Drei-/Fünfkamera erfasst.
- Aktive Intensität standard30%, im Wrist-Fenster manuell änderbar, Leerlauf0.
  Manueller Setter2/Gettermode1 auf getestetenFirmwares: Bestätigung+Intensität
  statt falschem Enumvergleich. Gesonderter Managed-Restore-Shim. Keine Fokus- /
  Belichtungsänderung durch LED-Befehl. Fremde Pendant-/HTTP-Viewer melden keine
  Nutzung; für eigene Streams activity()-Kontext verwenden.
- AktivRF/RR/LF nach Abschluss ihrer Messreihen; nur ihre Kameradienste neu geladen.
  LR-Rollout bewusst nach eigener laufender Reihe: Job
  setup/wrist_lighting/pending/left_rear.json. Guardian wartet Abschlussstatus
  und freien Kameralock, ersetzt dann ausschließlich altenLR-Kameradienst durch
  uwa-wrist-hd-left-rear-managed.service und bestätigt LED0. Keine UR-/Motionaktion.
- Bau und45gezielte RegressionenPASS; reale Qt-Vorschau/LED-Knopf/Schließen
  sowie ROS-HD-Aufrufe LF13,57s/RR24,39s mit abschließendem LED0 bestanden.
  Wrist-Fenster --arm wählt alle vier IDs bei unverändertem StandardRR.
- [Bedienung/Prüfgrenzen](docs/wrist_speed_led_2026-11-12.md), Rohdaten
  setup/calibration/wrist_speed_led_20261112/, Test-/Buildlogs
  setup/logs/uwa-wrist-speed-led-*.log. Frühe verworfene LED-/Restoreversuche erhalten.

Stand der Zusammenfassung: **2026-11-12**, Zeitzone Australia/Perth.
Diese Datei fasst die bisherigen Gespräche und die überprüfte Implementierung
zusammen. Sie soll bei weiterer Arbeit mitgepflegt werden, nicht als unveränderlicher
Abschlussbericht dienen. Arbeitsregeln: [AGENTS.md](AGENTS.md); Bedienung: [README.md](README.md).

## Native HD-Intrinsics hinten links abgeschlossen,2026-11-12

- Nutzer beauftragt eigeneHD-Reihe nachLF-Ende und bestätigt konkreteVorschau:
  "Vorschau passt, Fahrbereich und Kabel frei – nach vorne links starten".
  NachLF41/41/Controllerinaktiv18:24:46 die gleichen40LR-Ziele mit echten
  Endstellungen erneut vollständig geprüft,Start18:29:18/Ende18:49:53AWST.
- **41/41 Bilder,PASS**,33Fit/8vorabPrüfung,20–24Ecken. Kamera06561F1400090106,
  native2592×1944/Fokus406Manual/33333/Gain16. AlleSensor-/Restoreprüfungen
  bestanden,123Burst-JPEGs gegenOriginal-SHA verifiziert. KeineBilderentfernt.
- **Empfohlen result_v2:Brown5/k3=0**,Fit0,3036px/Prüfmedian0,3177px/
  Prüfmaximum0,3925px. FreierOriginalfitv1 ebenfallsPASS,aber außerhalbder
  beobachtetenEcken nichtmonotoneRandextrapolation. Deshalb geringereModell-
  Ordnung aus denselbenFitbildern,unveränderteGrenzen/Prüfrollen;Originalv1
  erhalten. PositiverJacobi-GittercheckistkeinegemesseneRandgenauigkeit.
  Eckenhülle32,1%Bildfläche,keineabsolute3D-/Weltgenauigkeitbehaupten.
- Sitzung setup/calibration/hardware_handeye/left_rear_hd_20261112/,
  selected_result.json verweistaufv2/CameraInfo/Manifest/Kontaktbogen.
  NativeSafetyNORMAL,Remote/RUNNING,ros.urpPLAYING;LRControllerinaktiv
  direktnachgewiesen,JSBaktiv,KameraNormal/LED0,Endfehler0,0000099rad.
  Exec69707 beendet/Code0/Cleanup0,keineRückfahrt/keinSafetyreset.
- NativeKameraServiceuwa-left-rear-wrist-hd bleibtkamera-only/idle verfügbar,
  eigeneDomain73-Vorschaugeschlossen. AndereArme/Dienste/Treibererhalten.
- AnfänglicherSpawner-Namespace-/Parameterfehler vorAktivierung behoben;
  ersterStartvorFahrziel wegenfehlenderfrischerRR-Datenabgebrochen.
  Initialwartephase16s begrenzt,keineUnionalterSnapshots/keineGuardlockerung.
  13Sequenztests+9ExporttestsPASS. EingefroreneC-/Workerressourcen erhalten.
- Kein Hand-Auge-Fit oder globaleAktivierung;VGA406-/Hand-Auge-Profilbleibt.
  [Bericht](docs/left_rear_hd_intrinsics_2026-11-12.md),Arbeitsstand abgeschlossen.

## Native HD-Intrinsics hinten rechts abgeschlossen, 2026-11-12

- Nutzerfreigabe für genau die Domain72-Vorschau umgesetzt. Alle **41/41**
  Aufnahmen gespeichert, 33 Fit / 8 vorab ausgeschlossene Prüfung. Physische
  Kamera01D1111A00090912, native2592×1944, Fokus388 manuell,
  Belichtung63410/Gain19. Festes rechtes40mm-A3-Board unverändert laut Nutzer.
- **Intrinsics PASS**, unveränderte Qualitätsgrenzen: Fit0,7605px,
  Prüfmedian0,6742px, Prüfmaximum0,9219px. Fokale Fitunsicherheit0,496/0,396%.
  18–24Ecken jeBild; alle Sensorreadbacks,3unterschiedlichenBurstframes und
  vollständigeKamera-Restores bestätigt. Originale/Prüfrollen/Hashes auditiert.
- Sitzung setup/calibration/hardware_handeye/right_rear_hd_20261112/;
  unverändertesErgebnis/ROS-CameraInfo/Manifest/Bildübersicht in result_v1/.
  Boardeckenhülle34,9% derBildfläche, äußersteRänder nichtgleichvalidiert;
  Reprojektionsfehler keine absolute3D-/Welt-/Hand-Auge-Genauigkeit.
- Abgeschlossen18:01AWST. LetzterGelenkfehler0,000044rad, RR-Fahrcontroller
  nachweislichinaktiv (direkteListControllers),UR RUNNING/NORMAL/Remote.
  ros.urp bleibtPLAYING, keineRückfahrt/keinSafetyreset, fremdeDiensteerhalten.
  EigenerExec1925 beendet; Domain72-Vorschau bereitsgeschlossen. DiagonaleLF-
  Aufgabe darf ihren eigenenRestweg jetzt anhandrealerRR-Endpose neuprüfen.
- Kein Hand-Auge-Fit oder globaleAktivierung beauftragt; bestehendesRear-
  VGA404-/Hand-Auge-Profilunverändert. NeueHD388-K/D separatverwendbar.
- NativeAufnahmepfad mitSensorreadback,gebundenerVision-PID-Freigabe,
  begrenzterIO-/JPEG-Recovery und gemeinsamerRestore-Kamerasperre geprüft.
  FrüherActionClient vorMoveIt,proBatchwiederverwendet; nativeSafety/Guard/
  Cancel/Deaktivierungerhalten. 34Vorbereitungstests+7Offline-ExporttestsPASS.
- Freigabe/Fingerprint19d68cdeb45acc0a0f8278c494156bb780da0385309902e8d555f54d7770e651
  in operator_approval.json. VerworfeneVorbereitungsbilder/Fehllogs separat
  erhalten. SchnellerStatushelper hattefalschnegativeROSDiscovery;
  direkteControllerlistebestätigtTreiber/Inaktivität. Nachweise/Bedienung:
  [Bericht](docs/right_rear_hd_intrinsics_2026-11-12.md).

## Links vorne: native HD-Reihe abgeschlossen, 2026-11-12

- CB3 i686, Kamera `028E1F350009061C`, 41 native JPEGs mit 2592 × 1944;
  33 Fit / 8 unabhängige Prüfung, feste V4L2-Werte Fokus 245, 60.590 µs,
  Gain 19, Originalkameraeinstellungen nach jedem Burst verifiziert.
- Intrinsics **PASS**: medianer Prüf-RMS 0,336 px; Hand-Auge **FAIL**: 1,593 px
  bei Grenze 1,00 px. Boardstreuung 0,899 mm / 0,173°. HD-Basislage nur
  diagnostisch, 1,86 mm / 0,172° Abweichung von VGA, kein Profil aktiviert.
- Erster Abbruch: ROS-Stillstandsprüfung reagiert auf gestartete RR-Reihe.
  Nach RR-Ende dieselbe Reststrecke mit allen vier realen Zuständen geprüft.
  Zweiter Abbruch: External Control nach 56-ms-Überlauf getrennt, Safety
  NORMAL und geladenes `ros.urp` STOPPED; ROS-Play, neuer Live-Check, weiter.
  Nach lokalem Prozessende in erreichter Pose 037 dort stationär aufgenommen.
  Am Ende LF-Fahrcontroller inaktiv, External Control verbunden, keine Rückfahrt.
- [Bericht](docs/left_front_hd_calibration_2026-11-12.md), Sitzung unter
  `setup/calibration/hardware_handeye/left_front_hd_20261112/`.
  Kamera-Dienst: [wrist_hd_service.md](docs/wrist_hd_service.md).

## Links vorne: Kamera und relative Basislage kalibriert,2026-11-12

- Nutzer hat die vollständige Serie freigegeben. 40 weitere Bilder erfolgreich
  aufgenommen, insgesamt **41/41** unterschiedliche VGA-Ansichten mit jeweils
  24 Boardecken, 33 Fit / 8 Prüfung. Fokus 245 manuell, 60.590µs, Gain 19.
- Nach OAK-Profilwechsel v3 wurden die 3607 Punkte der unveränderten Nutzerwege
  erneut gegen alle vier Arme geprüft. Kinematik-Inhalte identisch, `sample_000`
  Flanschpose exakt gleich; neue Sitzung und Originalplan separat erhalten.
  Frühe Discovery-Abbrüche vor jedem Fahrziel. Erfolgreicher Lauf mit lokalem
  UDP-Messclient und gemeinsamer Einrichtung von Action und Telemetrie.
- **Intrinsics und Hand-Auge PASS:** mediane Prüf-Reprojektion 0,092px / 0,359px;
  Board-Translations-/Rotationsstreuung 0,543mm / 0,114°. Keine ausgeschlossenen
  Bilder, keine angenommene absolute Messgenauigkeit.
- Relative LF-Basis im LR-`base_link`: [13,92; 1414,32; 0,62]mm, XYZ-Winkel
  [−0,049; +0,124; +179,143]°, Abstand 1414,39mm. Linkes Board nach Nutzerangabe
  seit LR-Kalibrierung unverändert. Kein Weltanker/Profil aktiviert.
- Abschluss NORMAL, External Control verbunden, eigener Controller inaktiv,
  letzte Pose erreicht (0,000091rad), keine Rückfahrt. Nur eigene Vorschau beendet.
- [Bericht](docs/left_front_calibration_2026-11-12.md), Daten unter
  `setup/calibration/hardware_handeye/left_front_20261112/series_current_model_checked/`.


## Vorläufige OAK-Schätzung global übernommen,2026-11-12

- Nutzer akzeptiert nach erklärter5,85/7,40mm- und0,361/0,576°-Prüfkonsistenz
  die erste OAK↔Front-Wrist-Schätzung für erste Versuche und beauftragt Anwendung
  überall einschließlich digitaler Zelle/Gazebo/RViz. Neues Standardprofil
  **hardware_20261112_v3**, vorherigev1/v2 und alle Originalresultate erhalten.
- Profilkopie enthält relative Schätzung/Protokoll, gemessenen Front-q-Snapshot
  vor15:59:05, originale Factory-K/D, SHA-Referenzen und explizite pro-Artefakt-
  Nutzerannahme. passed:false/diagnostic_only:true des Ursprungs unverändert.
  Alte Roboterartefakte und Gelenkstartwerte bytegleich; keine Rear-HD-K erfinden.
- Ableitung: T_world_frontBase(nominal) @ FK_factory(q_measured) @ übernommenes
  T_tool0_frontOptical @ inverse(T_oak_front). Pose ca.[1,2203;0,0522;1,8578]m.
  Weltanker ausdrücklich weiterhin vorläufig, keine neue Tisch-/Basisvermessung.
  OAK raumfest eingefroren, folgt später verschobenen Tischen nicht automatisch.
- Gemeinsamer Description-Loader validiert Starrheit, komplette Ableitung,
  Kamera-/Referenzidentität, Hashes und konkrete Annahme. Sim-/View-Planung nutzt
  dieses Profil, vorhandene Planfingerprints müssen regulär neu geprüft werden.
  Nominalmodus weiterhin ausdrücklichladbar, keine alten Fingerprints ändern.
- Gazebo-Sensorpose/ROS-optical gleich; zusätzlich Referenzframe
  real_oak4_rgb_optical_frame inDomain64, kein echter LIVE-Streamnachweis.
  RViz-Gehäuse/Stativ/Frustum mit PRELIMINARY/USER ACCEPTED/Weltankerhinweis.
  overview.sh nutzt kalibriertes Standardlayout; neue Fotosessions speichern
  calibration_context.json. BestehendeFotos/Manifeste unverändert.
- Physische8K-K/D Rational14 bei116 vollständig archiviert/exportiert als
  oak4_camera_info.yaml. Jetty/Ogre2 meldet BrownDistortionModel unsupported.
  Deshalb simulierteOAK ehrlichPinhole mit skaliertenK/D=0; keine nichtgerenderte
  Verzeichnung als Bildgeometrie ausgeben. Brown5-Näherung nur archiviert für
  spätereRenderer, maxca6,32px/8K auf unabhängigem Prüfgitter. Reale Auswertung
  behält Rational14. Stativ wie bisher visual-only, kein neues Kollisionshindernis.
- Drei Pakete gebaut;40gezielte TestsPASS, einschließlichFK-/SDF-/Optikgleichheit,
  Weltfestigkeit beiTischbewegung, alteRoboterbytes, SHA-/Akzeptanz-/Matrixfehler,
  MoveIt/Overlay undFoto-/Auswertungsregressionen.
- DigitaleZelle über normalenApp-Launcher inDomain64/Partitionuwa_cell_sim
  geöffnet,Gazebo+RViz+Scan+rqt. Erster Kamerasensor beim frühen Szenenaufbau
  verloren, nurKamera neu geladen: Bildempfang wiederhergestellt, keineZell-
  oderRoboterzustände zurückgesetzt. KünftigerLaunch startet Overview erstnach
  Zellmodell-Spawn. Für ehrliche Pinhole-Metadaten nur verifiziertenOverview-PID
  22847 sauber mitSIGINT beendet und als eigener uwa-cell-overview gestartet.
- FinaleLiveprüfungPASS:4000×3000,2verschiedeneBildzeitstempel,D=[0,0,0,0,0],
  K passtFactoryskalierung, beideTFs exaktProfil, GazeboSceneSensorlinkpose
  stimmt, RVizMarkerabonnent nachgewiesen, Simuhr26,406sweiter, Gelenkeendlich,
  alle9Simulationscontrolleraktiv. KeineHardwaredienste/Power/Play/Armfahrt.
- Nachweise setup/calibration/three_camera_evaluation_20261112/adoption-live/
  {report.json,simulated-overview.jpg}, Logs setup/logs/uwa-oak-profile-adoption-*
  (frühereFehlversuchebehalten). Beschreibung docs/oak_preliminary_adoption_2026-11-12.md.

## Links vorne: erste Boardaufnahme erfolgreich,2026-11-12

- Nutzer hat den nach Absturz neu geprüften 53-Sekunden-Weg freigegeben. Der
  UR5 vorne links hat ihn erfolgreich ausgeführt (Result 0, Endfehler 0,0000623 rad).
  Andere Arme wurden nur beobachtet; keine Rückfahrt. Der eigene Trajektorien-
  controller wurde nach der Aufnahme wieder deaktiviert.
- Zwei frühere Versuche endeten vor einem Fahrziel: fehlender Controller und
  zu kurze Action-Discovery. Korrekte LF-Parameter im passenden Namensraum
  gesetzt; Laden und Konfigurieren über getrennte ROS-Dienste, anschließend
  Action-Discovery vor der Aktivierung. Keine Treiber oder Sicherheitsfunktionen
  geändert. Die Ausführung nutzte weiterhin native Safety, External Control
  und frische Zustände aller vier Arme.
- `sample_000` akzeptiert: 640×480, 24 ChArUco-Ecken, drei unterschiedliche
  HTTP-Frames im überwachten Stillstand. Eigener Fokus 245 manuell, Belichtung
  60.590 µs manuell, Gain 19. Originaleinstellungen und Diagnosebilder erhalten.
- 40 zusätzliche Ansichten mit allen vier Armen als Hindernisse und ohne
  diagonale Ausnahme geplant. Zusammen mit sample_000: 33 Fit- und
  8 unabhängige Prüfansichten. Reine Bewegung 354.6s,
  zusätzlich Stillstand und Aufnahme. Vollständiger Check-only bestanden;
  keine Serienfahrt ausgelöst. Fingerprint `a23608cb8cccf2c7ddf1c806451eb8de6f364df601a9368d3886fbdc74915d3b`.
- Messung, Diagnosen und Pläne unter
  `setup/calibration/hardware_handeye/left_front_20261112/`. RViz-Vorschau der
  Serie getrennt von Hardware. Nächster Schritt: Freigabe des neuen Wegs.
  Die relative LF-Basislage wird erst nach bestandenem Fit über das gemeinsame
  feste linke Board und die validierte LR-Referenz bestimmt. Keine globale Pose
  und kein Kalibrierprofil aktiviert.


## Sechs mobile Drei-Kamera-Fotosets offline ausgewertet,2026-11-12

- Nutzer bittet um Einschätzung seiner bisherigen Fotos, nach PC-Absturz
  fortgesetzt. Nur lokale Dateien verwendet, keine Kamera-/ROS-Dienststarts,
  keine Roboterkommandos und kein aktives Kalibrierprofil geändert. Parallel
  laufende LinksFront-Vorbereitung unverändert erhalten.
- Benutzer-Session three_camera_mobile/20261112_155233_897f400a enthält6Sets/
  18nativeOriginale. Alle Bild-SHA256 stimmen mit den Manifesten überein.
  5Sets haben >=12Ecken in allen3Kameras,3Sets alle72Ecken. ErsteTeilansicht
  15:57:44 separatdiagnostisch; kein nachträgliches Entfernen nach Fitfehler.
- Feste Rollen vor Posenfit gespeichert:15:59:05/16:03:42/16:11:47 Training,
  16:12:46/16:14:34 unabhängige Prüfung. Front-HD435 mit ausdrücklich bereits
  akzeptiertem Untergrenzenprofil und OAK-Factory8K/Fokus116 festgehalten.
  Keine hochskalierte Rear-VGA-Matrix: Rear-HD388 weiter ungeprüft, kein Fit.
- Neuer reinlokaler Python-Modul board_photo_evaluation: PnP-Initialisierung
  jeBild ohneNominal-/GT-Posen, gemeinsamer robuster relativer OAK↔Front-Fit
  mit brennweitennormierten Bildresiduen. Resultat ausdrücklich diagnostisch,
  passed:false,calibration_applied:false; keinTF/keineWelt-/Tischkalibrierung.
- Zwei Prüfansichten: Unterschiede unabhängiger relativer PnP-Pose zum Fit
  5,85/7,40mm und0,361/0,576°. OAK-Kreuzprojektions-RMS10,29/6,53px,
  Front8,00/1,28px. Interne Konsistenz, keine vermessene Hardwaregenauigkeit.
- Zusätzlich erste/letzte native Burstbilder neu detektiert: mediane
  Eckenverschiebung0,056–0,157px, Maximum0,456px über ca.0,13s. Kein auffälliger
  Kurzzeitbewegungshinweis, kein Synchronitäts-/Dauerstillstandsnachweis.
  Gelenk-Endpunkte proSetmax0,000105rad auseinander. Optik-Readbacks sind
  kein zusätzlicher Sensor-Fokusnachweis während nativem Burst.
- Fünf gute Boardnormalen ca.26,2° gespreizt, Boardmittenbereich22×16×12cm
  im vorläufigen OAK-Frame. Sichtfeldabdeckung weiterhin begrenzt, vor allem
  OAK. Mehr verschieden geneigte/verschobene/entfernte Ansichten sinnvoll,
  etwa15–20zusätzliche als praktischer Zielwert; keine Garantie durch Anzahl.
- Ergebnisse setup/calibration/three_camera_evaluation_20261112/diagnostic_v1/
  (protocol/result/image-audit.json,coverage.png),all_sets.jpg im Elternordner.
  Bericht docs/three_camera_photo_evaluation_2026-11-12.md; 5synthetischeTests
  PASS für Transformationsrichtung, unabhängige Prüfung, Geometrie-/Hashfehler.

## Links vorne: Kamera-/Basis-Kalibrierung vorbereitet,2026-11-12

- Nach PC-Absturz und Neustart16:17: alle vier URs RUNNING/NORMAL, ros.urp STOPPED.
  Vier flüchtige ROS-Hardwaretreiber mit inaktiven Bewegungscontrollern neu gestartet.
  Nach längerem DDS-Einlesen echte Gelenkstellungen aller vier Arme verfügbar.
  Aktueller Plan `preparation/first_view_rechecked/plan.json`: 53.0s,
  532 Kollisionssamples, voller Check-only bestanden.
  Fingerprint `9ad63ff3dd6c4da5fc9cf8666ec77fa6457b8d399179b7da5e1002a4379ecff0`; alte Vor-Absturz-Pläne nicht ausführen.
  Eigene Vorschau auf Domain68 wieder geöffnet. Vor realer erster Fahrt fehlen
  erneutes External Control links vorne und konkrete Freigabe des gezeigten Wegs.
  Keine Fahr-/Power-/Brake-/Play-Befehle gesendet.

- NeuerNutzerauftrag: Position undKamera des jetztROS-erreichbarenUR5links vorne
  kalibrieren. Nutzerbestätigt linkes40mm-A3-Board seitLeftRear-Kalibrierung
  unverändertbefestigt. DamitspäterLF-Basis relativLR aus gemeinsamemT_base_board
  bestimmbar; keineabsoluteWelt-/Tischanker-Vermessung darausbehaupten.
- KameraHTTP640×480funktioniert,StatusNormal. Erstbildstarküberbelichtet,kein
  Board/keineBewegung. Kamera-only-AE-Trigger liefertbrauchbaresaktuellesBild
  vomBoden/Pendant. Triggerstellt exposureAuto vontrueauffalse; Originalsettings
  gesichertundvorFahrtfreigabewiederzurückgeschrieben,Readbackprotokolliert.
- NativeHD-Probe vorModuswechselgestoppt: alterCB3 i686/32bit hat kein gcc/cc,
  vorhandenerNativeCapture.bootstrap kannC-Helfernichtbauen. KeinKamera-/UR-
  Dienst/OSupdate,keinKalibrierfit;VGA-Pfadfunktioniert. KompatiblerHD-Helfer
  bleibtbeiBedarfvorzubereiten,kein2592×1944-Erfolg fürLF behauptet.
- KonkretererstergerechneterWeg53,0s/531Kollisionssamples,max0,005radSampling,
 0,05rad/s/0,10rad/s². Alle4Armefrischliveerfasst,volleMoveIt-ZellemitLF-
  Werkskinematik,keineDiagonal-Ausnahme. Zielkamera nominell[-.45,-.28,1.453]m.
  park_arm execute --check-only PASS,keinFahrzielgesendet.
- Artefakte setup/calibration/hardware_handeye/left_front_20261112/preparation/,
  first_view/plan.json Fingerprint4c734fab2a835ba373d04acb71a1af748a66c8ac4dc14d4f0bae5fbe9ee7f456.
  EigeneDomain68-RViz-Animationuwa-left-front-calibration-preview geöffnet.
  ErsteFahrt wartetzurSichtprüfung aufkonkreteFreigabe. AndereArme/KameraGUI
  undbestehendeKalibrierprofileerhalten;keineAufnahmefolge/Fit/Aktivierung.


## Links vorne: External-Control-Verbindung bestätigt,2026-11-12

- Nutzer startetros.urp amUR5. JetztDashboardPLAYING/running:true,RobotmodeRUNNING,
  SafetymodeNORMAL. ROSrobot_program_running=true,Hardwareactive,frische6Gelenke
  rund123Hz im10s-Prüffenster(1230Samples,max331msHostlücke).
- KonkreteReverse-Verbindung192.168.8.209:51001↔192.168.8.2 aufgebaut;Trajectory-
  undCommandkanal51003/51004ebenfallsESTAB. NativeTreibermeldung15:54:46:
  Robot connected to reverse interface. Ready to receive control commands.
- ImProgrammstartfenster15:54:37ersteVerbindung/15:54:43Drop/15:54:46Neuaufbau;
  Benutzerstartphase,nichtalsbewiesenerunerklärterDauerausfallausgeben. Bei
  nachfolgendenChecks keinneuerAbbruchgesehen,keinLangzeitnachweis.
- Alle9ControllerunabhängigperROSListControllersnachgewiesen:5Broadcasteractive,
 4Motioncontrollerinactive. ErsterasynchronerListencheckliefertebinnen10skeine
  Antwort;separaterCLI-Serviceaufruferfolgreich. FollowJointTrajectory-Schnitt-
  stellenbeiderTrajektoriencontroller vorhanden. KeineControlleraktivierung,
  keinFahrziel/Power/Brake/Play/SafetyresetdurchdiesenCheck.
- Ergebnis: **ROS-Steuerverbindung bereit**,tatsächlicheTrajektorienausführung
  nochnichtgetestet. FrühereRTDE-BlockadedurchEtherNet/IP-Deaktivierungbehoben.
  Quelle `setup/logs/left-front-ros-readiness-20261112/external-control-155746/`.


## Links vorne: RTDE-Blockade nach EtherNet/IP-Aus behoben,2026-11-12

- Nutzer meldet EtherNet/IP deaktiviert/Installation gespeichert. Nur eigenen
  uwa-left-front-hardware-driver neu gestartet. Laufzeit-KillSignal konnte per
  systemctlset-propertynichtgeändertwerden;normalerNeustart dennochsoforterfolgreich,
  keineSource-/Servicekonfiguration dafür verändert.
- UR5/Serial2017356443/PolyScope3.15.8.106339: Hardware **active**,RTDE125Hz,
  Werkskinematikcheck erfolgreich; speed_slider_mask-Konflikt nichtmehrvorhanden.
  Alle5Broadcaster aktiv,4Motioncontroller ordnungsgemäß geladen/inactive.
  Reverse/Script/Trajectory/Command-Listener51001–51004 offen.
- ROS-Stabilitätsprobe20s:2320gültige6-Gelenk-Samples,124,95Hz innerhalbempfangener
  Zeitspanne,max334,5msLücke,Streuungmax0,000144rad. Keinefehlenden/nichtendlichen
  Gelenkwerte;keinenBewegungs-/Langzeitrobustheitsnachweis darausableiten.
- Historisch vor manuellem Programmstart: NativeRUNNING/NORMAL,ros.urp geladen,
  aber **STOPPED**;nochkeineReverse-
  Verbindung undkeinBewegungstest. Nutzergebeten,ExternalControl ros.urp am
  Pendant laufenlassen(Host192.168.8.209/Port51002),danachSteuerverbindungprüfen.
  KeinePower/Brake/Play/Fahrziele/Safetyquittierung durchdiesenCheck.
- Nachweise `setup/logs/left-front-ros-readiness-20261112/ethernetip-off-155447/`.
  Andere3Roboter-,Kamera-/RVizdiensteerhalten;paralleleDrei-Kamera-Arbeitunverändert.


## Historisch: Links vorne vor EtherNet/IP-Deaktivierung,2026-11-12

- Nachtrag vom Nutzer: **EtherNet/IP am linken vorderen UR5 ist aktiviert**.
  Damit konkrete, zur RTDE-IN_USE-Meldung passende Feldbuskonfiguration bestätigt;
  tatsächlicher Registerbesitz noch nicht separat ausgelesen. Nutzer gebeten,
  EtherNet/IP bei fehlender SPS-Nutzung zu deaktivieren und Installation zu
  speichern. Später vom Nutzer deaktiviert; positiver neuer ROS-Check im aktuellen Abschnitt oben.

- Nutzer bittet zuprüfen,obUR5links vorne inzwischen perROS steuerbar ist.
  Identität192.168.8.2/Serial2017356443 bestätigt; PolyScope3.15.8.106339 im
  Inventar aktualisiert. NativeRUNNING/NORMAL,ros.urp geladen,aberSTOPPED.
- AlteFehlinitialisierung des eigenen uwa-left-front-hardware-driver bestätigt;
  gezielterNeustart. AlterDienst brauchte90sSystemd-Stopp,letzterRSP perTimeout
  beendet; fremdeDiensteunverändert. NeuerStart erneutdreimal RTDE-IN_USE:
  speed_slider_mask vonanderemClient/Feldbusbelegt. Hardwareunconfigured,
  keinJointState/Broadcaster,keineMotioncontroller/Reverse-/Scriptlistener.
- Lokalkein konkurrierenderTCP-Client nach192.168.8.2:30004 gesehen. Tatsächlicher
  Besitzer nichtbewiesen; Nutzer perFrage umEtherNet/IP-/PROFINET-Status gebeten.
  KeineFeldbus-/Safety-/Inputrecipeänderung,keinePower/Brake/Play/Fahrziele.
- Output-only-Gegentest mit vorhandenemReadOnlyStream ohneInputrecipe/Writer:
 71Samples/7s,6echteWinkel,qd0,Robotmode7/Safetymode1. SomitlesbareNetzwerk-
  telemetrie; ROS-Steuerfähigkeit aktuellweiterverneint,keinBewegungstest.
- Diagnose/JSONs/neuerStartlog/ReadOnlyNachweis unter
  `setup/logs/left-front-ros-readiness-20261112/153340/`.
  NachBeseitigungInputbesitz Treibererneutinitialisieren,danachExternalControl
  prüfen. EinSTOPPEDProgramm allein erklärtkeinenRTDE-IN_USE-Konflikt.


## Drei-Kamera-GUI für mobiles A4-Board,2026-11-12

- Nutzer bestätigt mobilesA4-Board IDs75–91 für beide rechtenWristkameras und
  OAK. NeueenglischeApp **UWA Camera Capture**, StartmenüeintragundLauncher
  `scripts/camera_capture.sh`; Bedienung `docs/three_camera_capture.md`.
- Readinesslesend: beideRechtsarme aktuelleJointStates, SafetyNORMAL,
  External-Control verbunden, Bewegungscontrollerinaktiv. KeineArmfahrt,
  Power-/Bremsen-/Programmaktion. ParallelaufgabeLinksFront unverändertlassen.
- DreiVorschauen mitMarker-/Eckenzahl,Empfangsalter,STALE/PAUSED/SNAPSHOT.
  Sichtbarkeitsbanner >=4Previewecken jeKamera; dasistkeineKalibriergüte.
  Capture-All-Button mitRECEIVED/RUNNING/DONE/FAILED undLaufzeit. Native
  Wrist2592×1944 + OAK8000×6000 Einzelbild übervorhandeneFotopfade; Quick
  optionalWristVGA. Originale,Annotationen,metrischeBoardkorrespondenzen,
  physischeKameraID/Fokus,Readback,Hash undZeitfenster jeunveränderlichemSet.
- Fokusprofil config/three_camera_capture.yaml: RF435,RR388,OAK116manual.
  Wristoriginale vorhergesichert,beiFensterschließen strengwiederhergestellt.
  RR-HD388 hatnochkeinevalidiertenIntrinsics; VGA-/HD-/Fokusprofilenichtmischen.
  KeineFits/Kalibrieraktivierung. Hostzeiten sindkeineBelichtungszeiten;
  BoardbisDONEstillhalten,keineHardware-Synchronisierungbehaupten.
- OAKVorschau2000×1500/2fps,voller4:3-Bildausschnitt,5sAE-Einlauf. VorFoto
  nurdieseSDK-Pipelinebeenden,Dateisperrfreigabeabwarten: oakctl-Wrapper kann
  vorherenden. PausegibtOAKfürTiefentoolfrei,keinefremdenDiensteabgeschossen.
- LegacyUCC1.11.1-Restore imvorhandenenWristworkerrepariert: ROI-Korrektur
  nachgemessenerAbweichung,begrenzteIterationen/Koordinaten,temporärerAFbei
  manuellemROI nötig,LegacyLEDmapping; amEndealleOriginalkonfigfelder exakt
  (automatischeAusgabefelder nurbeiaktivemAutomatikmodusausgenommen).
  RealAF-/ManualnativePASS; frühereFehlberichtebleibenunverändert. Erste
  überbelichteteRear-HTTP-Aufnahme durchneuenBelichtungstriggerkorrigiert.
- ErstesnativeDreierset
  `setup/calibration/three_camera_20261112/first_sets/20261112_154033_06fc8276/set_154037_784566/`:
  OAK24/RR24/RF8von24Ecken. VorneBoardobenabgeschnitten; Bildergesichert,
  Setabsichtlichall_usable=false. MobilesBoardinFrontbildmitteausrichten;
  keinezusätzlicheArmbewegung beauftragtoder ausgeführt.
- EchterGUI-AbnahmelaufPASS:
  `setup/calibration/three_camera_20261112/gui_check/20261112_154921_20ecc2ad/gui-check.json`.
  DreiaktuelleVorschauen,Buttonklick+nativesDreierset,Live-Rückkehr,
  PausemitnachgewiesenerDateisperrfreigabe,Originalfokus-RestorePASS.
  Screenshotslive-before/after.png; erneutRF8/RR24/OAK24nativeEcken.
  FrüherefehlgeschlageneAbnahmeläufenichtgelöscht (Freigaberaceaufgedeckt).
- ZusätzlichlesendeDomain66-Telemetrie vor/nachneuenFotosets gespeichert,
  fehlendeSamplesexplizitmarkiert; EndpointdifferenzistkeinDurchgehend-
  Stillstandsnachweis. LiveProbe beiderRechtsarmePASS unter
  setup/calibration/three_camera_20261112/telemetry-check/. KeineROS-Writer.
- Build uwa_cell_control PASS,30gezielteTestsPASS (Detektionsidentität,
  Teilansicht,Datenfehler,Setfehler,SDK-Sperrrace,QtKlick/STALE/Snapshot,
  vollständigerLegacyRestore undbestehendeOAK-Transaktionsgrenzen).
- InstallierterStartmenüeintrag tatsächlichpergioinpersistenterBenutzersitzung
  geöffnet: temporärerDienst uwa-camera-capture (ExitType=cgroup), Session
  setup/calibration/three_camera_mobile/20261112_155233_897f400a/.
  GUI-/SDK-Prozesse aktiv,frische2000×1500-Frames,Fokus116readbackbestätigt.
  BeimnormalenFensterschließenwirdOriginalfokuswiederhergestellt. Laufende
  PreviewbelegtOAKexklusiv; fürTiefen-/andereFotoaufträge **Pause live view**.

## HQ-Tiefenaufnahme als RViz-Punktwolke,2026-11-12

- Nutzer bittet nach HQ-Tiefenmodus um sichtbare RViz-Anzeige. Vorhandene
  Domain70-Designvorschau erhalten; eigene Domain65-Snapshotansicht geöffnet.
- CLI `bash src/oak_camera_calibration/tools/oak4_photo.sh view-depth`, optional
  --capture DIR. OAK-Tools oak4_depth_rviz.py/geometry.py, keine ROS-Neubaupflicht.
  HQ standardmäßig aktiv, Standardwolke optional, klarer STATIC-/Datumshinweis.
- Frische nativeHQ-Aufnahme: setup/oak4/depth/20261112-145646-depth_hq-437c09ec/.
  Worker speichert jetzt tatsächliche rektifizierte Frame-K/Größe und Referenz-
  extrinsics in Metern. K fx=fy800.60913,cx637.89282,cy398.7670 für1280×800.
  Keine unrektifizierteFactory-K als Ausgabe-K verwendet; alte Aufnahmen ohne
  projection für3D abgewiesen. SDK-Metadatenquelle im JSON protokolliert.
- Kamera-lokale PointCloud2,273323HQ-/429717Standardpunkte, EinheitenMeter;
  TF nur oak4_snapshot_view→oak4_snapshot_rectified_right_optical. Kein world-
  TF/kein global aktiviertes Kalibrierprofil, keine angenommene Weltregistrierung.
- Geöffnet per temporäremBenutzerdienst uwa-oak4-depth-rviz; Config/Quelle/Counts
  unter setup/oak4/rviz/. ROS-Empfang mit endlichen Punkten/korrektemPayload/TF,
  RViz-Abonnent und GUI GlobalStatusOk nachgewiesen.17TestsPASS, neue bekannte
  Pixelprojektion/mm→m/Nullwert-/Kalibrierfehlerprüfungen enthalten.
- Rendererbilder perDesktop-/RViz-Qt-Grab unterWayland nicht zuverlässig prüfbar
  (schwarz); deshalb kein visueller Screenshot-Nachweis behauptet. Punkte-
  empfang/GUIstatus sind unabhängig geprüft. Keine fremdenDienste/Roboter geändert.


## Statischer HQ-Tiefendienst ergänzt,2026-11-12

- Nutzer fragt nach ähnlichem HQ-Verfahren für Tiefe. Bestehenden Fotodienst
  erweitert, keine separate permanente Kamera-Pipeline. Neue Trigger-Services
  `/oak4/depth/capture_{hq,standard,compare}` und `/oak4/depth/status`, Domain65.
  CLI über oak4_photo.sh capture --mode depth_hq (Standard16Frames).
- Native1280×800-Stereo/FAST_ACCURACY/SoftwareLR,10fps; Mono-AE nach Einlauf
  sperren. Keine räumlichen/historischen Softwarefilter, stattdessen zeitlicher
  Median gültiger Werte, mindestens75% Support/Inlier und MAD-Grenze
  max10mm/1%Tiefe. Instabile Werte0, keine Lochfüllung. Keine ISO100-Behauptung.
- Worker/Fusion im OAK-Repo tools/oak4_depth_{capture,fusion}.py, Anleitung
  OAK4_DEPTH.md. Rohframes/Count-/Inlier-/MAD-/Maskenkarten,16bit-mm-PNGs und
  Factorybackup unter setup/oak4/depth/. Gleiche Thread-/Dateisperre wie RGB.
- Installierten Vergleichsservice real PASS geprüft, native1280×800,uint16,
 16Frames57–72/1,500s: setup/oak4/depth/20261112-144815-depth_compare-97e070f4/.
  Standard41,67% gültig, HQ26,87% nach konservativer Aussonderung. Akzeptierter
  medianer zeitlicherMAD3mm; kein absoluterGenauigkeitsnachweis. AndereArm-
  arbeit parallel; kein garantierterStillstand/Kamera-Roboter-Zeitsync.
- Regulärer HQ-Endpunkt ebenfalls real PASS: setup/oak4/depth/20261112-145220-depth_hq-29c6117c/.
  Status CAPTURING währendAufnahme, parallelesRGB abgewiesen,danachREADY.
  14automatisierteTestsPASS; intakte16bit-PNGs/NPZ und Supportmasken geprüft.
- Mono links3000µs/ISO188,rechts3135µs/ISO200 währendBurst konstant. Kein
  Firmware-/Flash-/Kalibrierprofil-/Roboterkommando. Foto-/Tiefenaufträge exklusiv.
  Neue Tests für Fusion/ungültigeDaten/Bewegungskanten; bestehende Foto-Sperr-
  Fehler-/Timeouttests erhalten. Agentenhinweise/README in beiden Repos ergänzt.


## Gemeinsame Sichtstellungen real abgeschlossen,2026-11-12

- Nutzer stellt LinksFront vorerst zurück. **NurLR→RR→RF** nacheinander in
  unveränderte vorgeschlagene Ziele gefahren, danachnative2592×1944-Fotos.
  LinksFront bekommtkeinZiel; echteWinkelalsHindernisfortlaufendoutput-onlyRTDE
  überwacht(keineInputs/Writer/URScript),keineerfundeneNull-/Home-Stellung.
- Alle3Ziele erreicht; Abschluss größteGelenkfehler LR2,78e-5/RR4,56e-5/
  RF2,82e-5rad. SafetyNORMAL,alleMotioncontrollerinaktiv,keineRückfahrt.
  NativeIstwinkel/Werkskinematik/volleMoveIt-Zelle,keineDiagonal-Ausnahmen.
- ErsteRR-Fahrt wegenLF-Datenlücke gecancelt/deaktiviert. 25s/258Pakete danach
  stabil(max101msLücke),Restwege frischgeprüft,LRalsalreadyAtTargetübersprungen.
  ReaderverkraftetNichtdaten-/Reconnectpakete,0,5s-Frischeguardunverändert.
  KeinSchutzreset;UrsacheerstemAussetzernichtabschließendbelegt.
- Alle3Wrist-Fotos je24Ecken,NativeJPEGsundÜbersicht unter
  setup/calibration/shared_views_20261112/photos/. LR/RF-DienstaufnahmenPASS
  nachfrischemTelemetrieeinlesennachblockierendemHTTP. RRNativeBildvorhanden,
  DienstRestorefehlgeschlagen(ROI): ausdrücklichdiagnostisch/keineFitbeobachtung.
- RR-Konfiguration anschließendaufursprünglicheWertezurückgeführt: gemessenen
 16pxY-Schreiboffset undLegacyLED-Codierung kompensiert; tatsächlicherReadback
  allerKonfigurationsfelderidentisch,Normal. AlteFehlberichteunverändert,
  automatischerLegacyDienstdamitnichtallgemeinalsrepariertausgeben.
- NeuesOAK-HQ-FotoalsGegensicht:alle3Boards gleichzeitigje17Marker/24Ecken.
  Original setup/oak4/photos/20261112-150024-hq-6a5b0dea/,Annotation/Detektion
  .../shared_views_20261112/oak_post_motion/. KeineOAK-Extrinsicsneuaktiviert.
- Schlüsselzugangaufallen4URsfrischverifiziert: drei e-SerieEd25519,CB3LF
  eigenerRSA3072wegenOpenSSH6.0,LegacySignaturnurfürdiesenHost. FremdeKeys
  erhalten;ZugriffnurPC209,keineWeiterleitungen/PTY. PrivateKeys/Hostvertrauen
  unter~/.ssh,keinePasswörtergespeichert;Backendreconnectautomatisch.12TestsPASS.
- LF192.168.8.2/UR5/Serial2017356443,WerkskinematikimInventar. Benutzerhat
  inzwischenPolyScope3.15.8/ros.urp eingerichtet; nativeSteueranbindungnoch
  prüfen. EigenerFehlstartDienstuwa-left-front-hardware-driver:Inputbesitz
  speed_slider_maskwarblockiert,keineLF-Motioncontrolleraktivierung. Ursprünglich
  Power-on fürIstwinkelohneBrake/Play;späteresRUNNINGvomNutzer,keineeigeneLF-Fahrt.
- Bericht [reale Sichtstellungen](docs/shared_view_hardware_2026-11-12.md),
  Arbeitsstatus work/shared-view-hardware-captures.md abgeschlossen; Ergebnis
  summary.json/manifest.json. Profile/Weltankerunverändert,keinAuto-Rückweg.

## Wiederverwendbarer OAK4-Fotodienst,2026-11-12

- Nutzer beauftragt nach erfolgreichem Standard/HQ-Vergleich dauerhafte Ablage
  als Service und sichtbare Dokumentation für spätere Agenten.
- Implementierung im OAK-Repo `tools/oak4_photo{.sh,_service.py,_capture.py}`,
  Anleitung `OAK4_PHOTOS.md`. CLI ohne ROS, Trigger-Services unter `/oak4/photo/`
  (capture_hq/capture_standard/capture_compare/status), Domain65/LOCALHOST.
- Installiert/aktiviert: systemd-user `uwa-oak4-photo.service`; idle ohne Kamera.
  Bestehende isolierte Laufzeit `.venvs/oak4` (DepthAI3.12) und oakctl verwendet;
  Inventar-IP/Geräte-ID zentral aus Zellrepo, keine temporären Chatabhängigkeiten.
- HQ ISO100, max90ms, acht echte48MP-Frames mit konstantemFokus/WB, nativePNG.
  Sensor10fps, nur angeforderte Vollbilder übertragen. Keine Rohsensor-/HDR-
  Aufnahme, keine Bewegungskompensation oder automatische Roboterfahrt.
  Exklusiver SDK-Zugriff, kein automatisches Stoppen fremder Kameradienste.
- Reale Serviceprobe PASS: setup/oak4/photos/20261112-135950-compare-cf3a4ee9/,
  drei intakte8000×6000-PNGs, StandardISO309/16,666ms, HQISO100/51,498ms,
  Fokus107/WB4138K, achtverschiedeneFrames. Status währenddessen erreichbar,
  zweiteAufnahme abgewiesen, danachREADY. Sechs Fehler-/Sperr-/TimeouttestsPASS.
- Finale reguläre HQ-Serviceprobe nach dem letzten Dienstupdate ebenfalls PASS:
  setup/oak4/photos/20261112-140403-hq-f3cec77a/, ISO100, acht unterschiedliche
  native48MP-Frames, exposure_limited=false. Benutzerdienst aktiv und enabled.
- Agentenhinweise/README in beiden Repos und Workspace-Einstieg ergänzt.
  Ergebnisse dauerhaft in setup/oak4/photos/; keine Bilddateien im Git.


## Grobe OAK-Pose und Beobachtungsstellungen,2026-11-12

- Nutzer bittet um grobe OAK-Pose relativ rechtemTisch sowie UR-Stellungen mit
  freier Tisch-/gemeinsamerOAK-Wrist-Sicht. Keine neue realeFahrt ausgeführt.
- EEPROM-K/D derOAK238 reinlesend,8K-Bildecken beiderTischboards perIPPE/LM
  ausgewertet. Relativ angenommenerrechterTischplattenmitte **[+0,806;+0,025;
  +0,958]m**,33,54°nachunten; bei0,90m Tischhöhe etwa1,858mBodenhöhe.
  LinkesBoard unabhängig0,960m/33,58°. Boardabstand0,959m statt0,90mNominal:
  Tischbewegung/Boardlage noch nicht trennbar, keine Welt-/Basisanker verschieben.
- Einbild-/Factory-Intrinsics-Schätzung mit unbekanntemFoto-AF-Wert, keine endgültige
  OAK-Kalibrierung. Eigenes experimentellesDesignprofil ohne globaleAktivierung:
  config/view_designs/oak_shared_views_20261112.yaml. Aktuellesparallelübernommenes
  hardware_20261112_v2 unverändert benutzt, Front-Qualitätskennzeichnung erhalten.
- Vierarm-Zielkonfiguration kollisionsfrei, jeWrist24Board-Ecken, OAK48Ecken.
  KonservativeMesh-Box-Sichtschätzung freieGesamttischfläche54%→78%; keine
  echtePixel-Messung. GemeinsamfreieTischflächen ungefähr0,59/0,70/0,97/0,77m².
  HorizontalesmobilesA4-Muster passt vollständig in beideKameras bei
 11/28/39/28 der54geprüftenPlatzierungen jeArm(LF/LR/RF/RR).
- Serielle reineModellwege LF→LR→RR→RF mit368s/3685Samples vollständig geprüft;
  echteAusführung bleibt false(linksFront nurNutzer-Home,provisorischeMontagen).
  Keine zusätzlichenWrist2-Umdrehungen, Wrist3-Änderungmax90° alsSuchpräferenz.
- StatischeRViz-Vorschau aufDomain70 geöffnet(28Gelenke/9Marker gelesen), ohne
  Hardwareclients oderTF-/Joint-Kommandobrücke. FünfGeometrietestsPASS.
  Vergleichsbild undlokaleYAML/Posen/Hashnachweise unter
  setup/calibration/oak_pose_20261112/design_wrist/; Geometrie-/Wegprüfung und
  Grenzen in [Bericht](docs/oak_pose_and_shared_views_2026-11-12.md).

## Aktuell: Front-HD übernommen und weitere HD-Kameras geprüft, 2026-11-12

- Nach Erklärung der Qualitätsabweichungen ausdrücklicher Nutzerauftrag:
  Front-HD-Daten übernehmen. Neues Standardprofil **hardware_20261112_v2**,
  baut aufv1 auf; beide validiertenRear-Optiken und Werkskinematiken unverändert.
  Front-Intrinsics2592×1944/Fokus435Manual und Hand-Auge übernommen mit
  `operator_accepted_below_threshold`; ursprüngliche `passed:false` bleiben.
  Nutzerentscheidung pro Artefakt anSHA256/Qualitätsbericht gebunden; keine
  Grenzwerte geändert. Ohne diese konkrete Ausnahme weiterhin strenge Ablehnung.
- Standardloader und generierteFront-Optikmatrix geprüft; keine Welt-/Basen-
  verlegung, keine Arm-/Dashboardbefehle, keine Hardware-/Gazebo-Neustarts.
  Neue Modell-/Planaufrufe nutzenv2; bereits geladene Modelle erst nachNeuladen.
  HD-K/D nicht auf640×480-HTTP-Bilder oder andere Kameras anwenden.
- **left_rear HD-Service PASS:** drei2592×1944-Bilder,je24Ecken,16,12s,
  Restore/Normal und sämtlicheOriginalsettings identisch. UCC3.44.0.149696,
  Kamera06561F1400090106. NativeDaten service/left_rear/c1990d41963846b78e3346ee5b3a8b5d.
- **right_rear nativeHD erhalten**,3×2592×1944,UCC1.11.1.10337,
  Kamera01D1111A00090912. Decke/Leuchte stattBoard,keineArmfahrt fürsMotiv.
  VollständigerService-Restore imAutofokusmodus FAIL: FokusfensterX1/Y1 von
  165/134 über158/118 auf158/102 verschoben; ursprünglicheROI nicht exakt
  wiederhergestellt. Autofokus/Autoexposure-Modi,LED und übrigeFelder erhalten,
  KameraNormal. Dies wird nicht als vollständigerErfolg verschwiegen.
- Weitere UCC1.11.1-Autofokus-Aufrufe vorKamera-/Modusänderung abweisen;
  echter Guardtest2,88s, state_changed:false, vollständigeVorher-/Nachhergleichheit.
  VerifiziertesManualprofil oderUpdate+Restoretest vorweitererSerie nötig.
- LegacyLED-Schreibwerte0/1 bei tatsächlich getestetenZweigen1.11.1/3.44.0
  invertiert; jetztgezieltberücksichtigt, tatsächlicherReadbackmaßgeblich.
  BegrenztesWarten aufSettings;automatischbestimmteFokus-/Exposureausgaben
  dynamisch,Konfigurations-/manuelleWerte weiterhinstrenggeprüft.
- **45Tests PASS**,3LyricalPaketegebaut;Logs uwa-front-hd-adoption-{tests,build}.
  Berichte [Profile](docs/applied_calibrations.md),
  [Rear-HD-Bildtests](docs/wrist_hd_other_arms_2026-11-12.md).
  Daten setup/calibration/wrist_hd/other_arms_20261112/;Sitzungen/RohbildernichtimGit.

## OAK-CAD und eigenes Stativ eingebettet,2026-11-12

- Nutzer beauftragt Modell ausDownloads und optional Stativdarstellung.
  Archiv oak4-pro-3d-model.zip enthält117MB-STEP-Baugruppe. InMeter konvertiert,
  Gehäuse/Frontglas getrennt und auf52169Dreiecke/2,61MB reduziert; Quell-/Mesh-
  Hashes undKoordinatenzuordnung in meshes/visual/oak4_pro/provenance.json.
- Generisches Fotostativ selbst erstellt: Teleskopbeine/Klemmen/Gummifüße,
  Spreizstreben/Mittelsäule/Schwenkkopf/Platte. Höhe aus tatsächlicher OAK-Pose,
  Füße bodenfest. VisuelleNäherung, keine vermesseneStativ-/CAD-Optikmontage.
- GemeinsameGeometrie fürGazebo undRViz; Mesh-/Zylinder-/Boxmarker. Optische
  Transformation/K-D/aktivesProfilv3 erhalten, keine Roboter-/Tischparameter
  geändert. Stativ bleibt wievorher visuell, keine neueMoveIt-Kollision.
- **21TestsPASS**,2Paketegebaut. Live:2CAD-Meshes+27Stativvisuals inGazebo,
  32Marker undRViz-Abonnent, frische4000×3000Bilder/K-D/TFs/9Controllerpositiv.
  Nur uwa-cell-overview.service neu gestartet, keine Zelle/Hardwareprozesse.
  MaxSim-Gelenkänderung0,00001064rad. KeineHardwarekamera/Armkommandos.
- Vorschau visuell geprüft, nativeFensteraufnahmen schwarz und nichtals
  sichtbarerRenderbeleggewertet. Bericht [OAK-CAD](docs/oak_camera_cad.md),
  Vorschau output/images/oak4_cad_tripod_preview.png; Nachweise
  setup/models/oak4-pro/live/ unduwa-oak-cad-{build,tests,live}.log.

## Karton nur aus Farbbildern alsCAD rekonstruiert,2026-11-12

- Nutzer beauftragt erste Pipeline zumDigitalisieren einfacherObjekte; Beispiel
  realerKarton aufTisch aus dreiFarbbildern. NativeDreieraufnahme17:09Perth,
  OAK8000×6000/beideWrist2592×1944, all_captured:true, Restore bestätigt.
  KeineTiefe, Armfahrt oderProfiländerung.
- OffenerKarton mit3Fächern rekonstruiert: ca.524×102×100mm Außenmaße,
  Trennwände ca172/347mm abLängsanfang. Wand/Boden/Trennwand2,5mmangenommen.
  Labels/Klammern/Faltungen/Verformungen nichtrekonstruiert; keineabsolute
  Genauigkeitbestätigt. Gegenmessung stehtaus.
- Maßstab aus rechtem40mm-Tischboard; neu geschätzteBild-Boardposen aus20
  OAK-/28Front-ArUco-Markerecken. OAKFactory14K/D116 undFront-HD-K/D435;
  Rear-HD388 mangelsMatchingK/D nurSichtprüfung. KeineHand-Auge-/FK-/Welt-
  Extrinsics imGeometriefit, keineLive-Gelenke erfunden (CaptureTelemetriefehlte).
- AssistiertesWerkzeug `ros2 run uwa_cell_control digitize_box`: Aufnahme
  vorbereiten/Intrinsics einfrieren, expliziteEckpunktdatei, robuster6Parameter-
  Fit+Trennwände, Overlays undAnnotationssensitivität. Keineallgemeineautomatische
  Segmentierung oderarbiträreOberflächenrekonstruktion behaupten.
- STEPmm/STLm/SCADmm unter setup/digitization/carton_20261112/result_v1/cad/,
  gültigerSolid/STEP-Rückimportmaße/geschlossenesSTL undrechtshändigerPoseexport
  geprüft.6SyntheticTestsPASS,Control-Paketgebaut,CLIinstalliert,Vorschaugeprüft.
- FinaleFit-RMSbei1800px:OAK5,41px/Front6,60px; keineunabhängigeValidierung.
  Zufalls-Annotationssensitivität umfasstnichtKalibrier-/Druck-/Modellfehler.
- Bericht [Objektdigitalisierung](docs/object_digitization.md), Vorschau
  output/images/carton_digitization_preview.png. Rohdaten/Hashmanifest/Overlays
  undKameraprofile untersetup/digitization/carton_20261112/, Logs uwa-carton-*.

## Echter Vierarm-Scan beauftragt, Start wegen Netzverlust offen, 2026-11-12

- Nutzer will Durchführung mit allen4parallel und bleibt amNothalt. Neue Ziele
  mit60mmTrennwandreserve/Reserveansichten gefunden:4Extras jeArm/21Blickpunkte,
  allePhasen unabhängiggetrennt mit50mmRestabstand nach±0,005radBahntoleranz.
  KleinsteModelluntergrenze339,0mm,2400MoveIt-Prüfpunkte. NochkeineArmfahrt.
- NeuerparallelerRunner+separateStop-GUI, GUI-Verlust/NativeSafety/Korridor/
  Datenverlust führenzugemeinsamemCancel/Deaktivieren/Stillstandsprüfung.
  BekannteZielevorWartenaufspäteBestätigungen canceln. ErsteFoto-Runde pausiert
  zurBildkontrolle,STOPbleibtverriegelt,keineHeimfahrt. KeinPower/Brake/Play imRunner.
- Build/34TestsPASS. IsolierteDomain75 mitviernativenMock-Controllern: gemeinsam
  Zielerreichung,STOPwährendFahrtundHeartbeatverlust/Resume-SperrePASS.
  EigeneMock-Prozessegezieltbeendet. RealeTreiber/Programmeunverändert.
- Gegen19:35Roboternetz enp87s0DOWN/CarrierOFF/keine8.209-Adresse,alleDashboards
  timeout. ROSlieferteweiterJoints/RobotMode3,RearSafety9;keineverifizierten
  aktuellenGerätezustände.BeideFrontwarenvorherbereitsPOWER_OFF. KeinStart/
  Safetyresetgesendet;NutzerumKabel/Switch/Steuerungengebeten.
- DeshalbLiveDashboard-HeartbeatzusätzlichzuROSFrischeimplementiert. Reader-
  Latest-SnapshotwurdebeiStatusabfrageersetzt;StartwerteimPlanerhalten,aber
  alteSnapshotbindungnunbewusstabgewiesen,vorFahrtneueimmutableLive-Planung.
- Anleitungdocs/parallel_object_scan.md;Datum/Sitzung
  setup/digitization/four_arm_scan_20261112/. StopfensterzeigtBLOCKEDNetworkDown,
  keineBewegungsschnittstellegestartet.KeineechtenScanbilderaufgenommen.

## Bewegungsraum-/Parallelprüfung der Scanwege, 2026-11-12

- Nutzer will maximale Vorstöße über mittige virtuelle Wände und daraus mehr
  parallele Bewegung. Implementiert Offline-CLI scan_separation, keine Motion-
  Clients/Dienst-/Kameraaktionen. Ganze68Kollisionskörper einschließlich Greifer
  und Kameras, Originalquintiken und konservative Zwischenpunktpolster geprüft.
- Quelle new_carton_plan_current, Modellhardware_20261112_v3. Über gesamte Wege
  LF/RF keine Mittellinienüberschreitung; LR≤34,1mm und RR≤60,4mm gegeneinander,
  tatsächliche Stichproben32,5/58,9mm. Greiferfinger begrenzen diese Vorstöße.
- Anfangswege aller4Arme zeitunabhängig getrennt, trotz hinterer Ebenenübertritte:
  gedrehte3D-Ebene liefert28,6mm Abstanduntergrenze. Technische Prüfschwelle20mm,
  keine gemessene Reserve realer Montagefehler. Alle übrigen Paarabstände größer.
- Zusatzansichten hinteres Paar nicht vollständig mit20mm nachgewiesen, auch
  bei289Einzelkörperpaaren: linke Finger gegenüber rechtemwrist_2 bleiben offen.
  Kein tatsächlicher Kollisionsfund behauptet. Andere5Armpaare getrennt.
- Prüfablauf: alle4Anfangswege parallel; Zusatzketten LF/LR/RF parallel inRunden,
  dannRR. Nicht nachgewiesene Paarreihenfolge LR→RR unverändert; Gelenkpunkte/
  Zeitparameter unverändert, Stillstands-/Fotobarriere nachjederRunde.
  Reine Fahrzeit193,5→80,9s(−58,2%), ohne Aufnahme/Stillstand. Nur Prüfartefakt,
  keine Integration/Aktivierung paralleler Hardwarebewegungen.
- Quell-/URDF-/Mesh-SHA gebunden; Greiferwerte explizite Modellannahme, Weltanker
  vorläufig, Kabel/Personen/Stativ nicht modelliert. Neue Wege neu prüfen.
- Build und12neueTests/Planungs-/Parkregressionen geprüft. Anleitung
  docs/scan_separation.md, Daten setup/digitization/five_camera_design_20261112/
  separation_review/, separater installierterCLI-Lauf separation_installed/.

## OAK zuerst und Fünfkamera-Softwarestufe, 2026-11-12

- Nutzer beauftragt Umsetzung; korrigierter Aufbau: neuer größerer Karton in der
  Mitte zwischen beiden Tischen, Unterseite auf Tischhöhe. Grobe Nutzerangabe
  40×30×20cm. Gewünschter Ablauf zuerst OAK-Foto/Größenschätzung, dann UR-Planung.
- Ein natives OAK-Standardfoto18:20AWST beiFokus116, keine Arm-/Wrist-Aufnahme.
  Automatische rechte Board-PnP24Ecken/1,33px. Assistierter Sechspunktfit schätzt
  43,9×34,6×15,8cm; kein finales CAD/Genauigkeitsnachweis. Overlay durchgesehen.
  Planungsreserve max(Bild,Nutzer)×1,15+4cm ergibt54,5×43,7×27cm.
- Neue CLI object_scan_bootstrap (Foto/assistierte Schätzung), object_scan_plan
  (nur Lesen/Modellprüfung/RViz-Vorschau Domain74) und scripts/object_capture.sh
  (vier Wrist+OAK, Kamera-only). Dreikamera-Standard erhalten. Keine Bewegungs-
  Clients im neuen Planer; alle Ergebniswege bleiben executable:false.
- Neue gemeinsame Modellansichten mit beiden Referenzboards; enger Suchbereich
  wegen Bildausschnitten verworfen, weiter Bereich fand5Grund-/15Zusatzansichten.
  Volle MoveIt-Wege mit gepolstertem Objekt, andere Arme nicht ausgenommen;
  reine Planung, keine reale Ausführung. Alte rechte-Tisch-Kartonpläne überholt.
- Fünfkamera-Telemetrieaudit vor/während Fotos, Roh-JointStates mit Stempeln und
  Geschwindigkeiten. Bewegung/Stale verweigern statische Bestätigung. Echte reine
  Leseprobe alle4frisch/ruhig, maximale beobachtete Gelenkänderung0,000071rad.
  Keine Bilder während dieses Audits. Fotos bei Fehler bleiben diagnostisch.
- Gespeicherte fünf Kameras in digitize_box vorbereitet; fehlende native K/D
  explizit ausgeschlossen. Linkes/rechtes Board nur mittels beider PnP-Posen aus
  demselben OAK-Foto verbinden, Transformationsrichtung synthetisch geprüft.
- Build PASS,35gezielte Tests inklusive Parkregressionen PASS, englische Fünfkamera-GUI mit synthetischen
  Snapshots offline geprüft. Keine laufenden Messreihen/Dienste unterbrochen;
  neue Pfade/Szenen nur offline. Noch kein realer Fünfersatz, kein neuronales Mesh.
- Frische reine Zustandslesung18:35:48AWST und neue Planung bestätigt:20Ansichten,
  19Wege/1963Punkte,139sGrundpositionierung+55sZusatzwege. Aktuellster Entwurf
  new_carton_plan_current/, frühere Entwürfe separat. Statische Vorschau geprüft;
  alle Artefakte weiterhin nicht ausführbar, kein echter Fünfkamera-Scan.
- Anleitung docs/object_scan.md, Daten setup/digitization/five_camera_design_20261112/.
  Welt-/Montageanker teils vorläufig; reale Wege brauchen frische Prüfung und
  konkrete Durchsicht, passende Kalibrierprofile sind teilweise noch separat.

## Vier Wrist-Kameras plus OAK: Scan-Konzept, 2026-11-12

- Nutzerziel: gemeinsames Objekt in Tischmitte, fünf Fotos je Aufnahmeschritt,
  optional kleine Zusatzbewegungen und Nutzung von Literaturverfahren.
  Gemeinsamer Scanbereich und Wege sind noch nicht nachgewiesen; bisherige
  Designposen zielen jeweils auf das eigene Tischboard.
- Empfehlung: fünf feste Ansichten, danach 3–5 Stellungen je Wrist plus feste
  OAK, also 13–21 verschiedene Blickpunkte. Kleine TCP-Bewegungen erfordern
  weiterhin vollständige Wegprüfung. Zunächst seriell positionieren und vor
  nicht belichtungssynchronen Fotos gemessenen Stillstand bestätigen.
- Designprofil config/digitization/five_camera_scan_design.yaml: nicht ausführbar,
  keine Bewegungsschnittstelle; Syntax und Ansichtszähler geprüft. Keine laufenden
  RR-/LF-HD-Kalibrierungen unterbrochen, keine Hardwareaufnahme oder Armfahrt.
- Primärquellen: COLMAP/OpenMVS als geometrische Vergleichsbasis, MASt3R oder
  VGGT als gelernte Initialisierung, anschließend Mesh und parametrischer CAD-Fit.
  Intrinsics je Sensor, Pose je Aufnahme; Maßstab, Objektmasken und zurückgehaltene
  Prüfansichten erhalten. NeRF/Splats benötigen zusätzliche Geometrie-/CAD-Schritte.
- Host mit Intel-Grafik, kein erkanntes CUDA-Gerät. COLMAP Sparse auf CPU möglich,
  dessen eigene dichte Rekonstruktion benötigt CUDA. Keine Modelle installiert
  oder ausgeführt. Stand und Quellen: docs/five_camera_reconstruction.md.

## Nutzerziele und Vorlieben

- Neue Roboter-Codebasis auf **ROS 2 Lyrical** unter **Ubuntu 26.04** aufbauen.
  Die bestehenden Jazzy-Repositories wurden dafür lokal angepasst.
- Einen digitalen Zwilling der echten Roboterzelle in Gazebo erstellen, im Repository
  `multi_arm_manipulation_UWA` unter `~/UWA_ws/src/`.
- Zunächst Geometrie und steuerbare Kinematik. Seit 2026-11-09 zusätzlich automatische
  Hand-Auge-Kalibrierung mit MoveIt-Kollisionsprüfung; allgemeine kooperative Planung
  und Synchronisation mit echter Hardware bleiben Folgearbeit.
- rqt für manuelle Gelenksteuerung erhalten. Neuer ausdrücklicher Auftrag vom
  2026-11-09: eine eigene Qt-GUI für Vorbereitung, Aufnahme, Überwachung, Stopp und
  Übernahme der automatischen Kalibrierung (ersetzt die frühere Einschränkung dafür).
- Bequemer Start wie eine Desktop-App mit eigenem Icon und RViz-Konfiguration.
- **Neuester Bedienwunsch, 2026-11-09:** Der normale App-Klick soll die Punktewolke
  mitladen. Keine zusätzliche Rechtsklick-Aktion zum erstmaligen Anzeigen verlangen.
- Das Vier-Roboter-Icon gefällt dem Nutzer; nur der weiße Außenrahmen sollte
  transparent werden. Das ist umgesetzt, der dunkelblaue Hintergrund bleibt erhalten.
- Deutsch als bisherige Gesprächssprache; praktische, nachvollziehbare Bedienhinweise.
- **Explizit seit 2026-11-09:** Wichtige Ziele, Anforderungen, Entscheidungen und
  Vorlieben parallel in AGENTS-/Handover-Dateien festhalten.

## Globales Profil aktiviert und drei Boards mit OAK erkannt,2026-11-12

- Nutzer beauftragt explizit globale Aktivierung. Neues versioniertes
  `hardware_20261112_v1` ergänzt linkeRear-VGA-Intrinsics/Hand-Auge aus bestandenem
 41er-result_v1. Alte rechte gültige Werte/kinematics/namedposes bytegleich;
  vorherigesBündel unverändert erhalten. FehlgeschlageneFront-HD-/VGA-Extrinsics
  ausgeschlossen. Keine neuen Welt-/Basis-/Tischanker oder OAK-Extrinsics.
- Gemeinsame Standardreferenz umgestellt,description gebaut, installiertes
  Standardprofil bestätigt. Sieben Modell-/K-D-/Sensor-/MoveIt-Consumerprüfungen
  bestanden, einschließlich linker optischerPose und unveränderter Gehäuse/Weltanker.
  Neue Modellloads/Planungen verwendenProfil; keine aktiveSimulation neu gestartet,
  keine UR-Kommandos/Treiberneustarts. Aktivierungsaudit untersetup/calibration/.
- Ethernet-OAK238 exklusiv geöffnet (Live-Dienst vorher inaktiv), natives
  **8000×6000**-NV12-Foto vomIMX586 aufgenommen; kein Upscaling, danach geschlossen.
  OriginalPNG und annotiertes8K-JPEG/Übersicht sowieID-/Eckbericht lokal unter
  `setup/oak4/captures/boards_20261112/`. Keine privaten Fotos imGit.
- Alle drei gleichzeitig vollständig erkannt: linkes/hinteresTischboard IDs0–16,
  rechtes/vorderesTischboard50–66,mobilesA4-Board75–91. Je **17/17Marker und
 24/24ChArUco-Ecken**. Detektion aufOriginal8K ohne GroundTruth/Robotermodell.
- ReineErkennungsprüfung, noch keine OAK-Extrinsics oder metrischeRegistrierung.
  MobilesBoard liegt imFoto untenlinks; Werkzeug-zu-Board-Montage bleibt unbekannt.
  NächsterKalibrierschritt getrennt planen, keine neueRoboterfahrt hieraus ableiten.

## Front-HD-Reihe vollständig aufgenommen, Qualität abgelehnt, 2026-11-12

- **40/40 native HD-Ansichten** von right_front,2592×1944;32Fit/8vorab
  reservierte Prüfungen. Alle angenommen,20–24Ecken,40 verschiedene Pixel-Hashes.
  Eigener Frontlauf ohne Unterbrechung. Rohdaten und getrennte Diagnoseversion
  unter `setup/calibration/hardware_handeye/right_front_hd_20261112/` erhalten.
- **Zum ursprünglichen Abschluss keine automatische Qualitätsfreigabe:** Intrinsics-Fit1,1984px überschreitet1px;
  regulärer Ablauf daher Exit1 nach vollständiger Aufnahme. Zusätzliche reine
  Offline-Diagnose: Intrinsics-Prüfung1,0031px, Hand-Auge-Prüfung1,9248px,
  Boardstreuung1,2669mm/0,5884°. Keine Bilder entfernt/Prüfbilder zumFit benutzt,
  keine Grenzwerte geändert. Diagnosewerte ausdrücklich nicht aktiviert.
- Neueste Nutzerkorrektur ersetzt vorheriges „erst links fertig“: diagonale
  reale Arme erreichen einander laut Nutzer nicht. Bedienerangabe, kein eigener
  Messnachweis. Fingerprinted `independent_diagonal_arm=left_rear` für Front;
  nur dieses Paar von gegenseitiger Kollision/Stillstandsabhängigkeit befreit.
  Selbst-/Tisch-/Werkzeug-/übrige Armkollisionen und native UR-Safety erhalten.
 26 gezielte Tests und Lyrical-Build bestanden.
- Fokus435Manual/60000µs/Gain16 während der gesamten Reihe. HD-Transaktionen
  jeweils mit bestätigtem Restore. Abschlusslesetest12:37Perth: KameraNormal,
  Originalsettings vollständig identisch; FrontRUNNING/NORMAL/PLAYING,Velocity0,
  hält letzte Aufnahmestellung mit aktivem skaliertem Trajektoriencontroller.
  Keine Rückfahrt/Schutzquittierung/Profilaktivierung. Andere Arme nicht gesteuert.
- Vollständige Werte und Nachweise: [Front-HD-Bericht](docs/front_hd_calibration_2026-11-12.md).
  Arbeitsstatus `work/front-hd-calibration-40.md`. Weitere Auswertung der Bilder
  ist offline möglich, ohne neue reale Bewegung. Ältere VGA-Profile erhalten.

## Front-HD: Grund des Intrinsics-Abbruchs eingegrenzt,2026-11-12

- Nutzer fragt nach gleicherFrontkamera/Board mit bestandenerVGA-Kalibrierung.
  WichtigePräzisierung: Front-VGA-Intrinsics bestanden; Front-Hand-Auge bereits
  wegen0,652°>0,5°abgelehnt. HD hat0,588°,nochimmernichtfreigegeben.
- Absolute1Pixel-Grenze berücksichtigt4,05fachhöhereHD-Auflösung nicht:
  1,198HDpx entsprechen0,296VGApx,alt0,289px. KontrollierteOffline-Auswertung
  derselben40HD-Bilder(32/8fest):Verkleinernauf640×480+Eckenneuerkennung ergibt
  Fit0,315px/Prüfmedian0,276px. KeinBelegfürgenerellschlechtereHD-Geometrie.
- ArUco-Subpixelablation bringt praktischkeineÄnderung(1,19834vs1,19841px).
  Rotationsursache nochungeklärt:Optik-/Bildpose,Boardplanheit,Montagestabilität,
  Restbewegung/Zeitzuordnung möglicheBeiträge,keinernachgewiesen.
  NativeHD-KontrollwertewährendStreamwerdennochnichtzurückgelesen;
  Vorher-/Nachher-HTTP-SettingsbelegenkeinevollständigeIn-Stream-Konstanz.
- Diagnosev1 unterHD-Sitzung/resolution_diagnosis_v1/,80Originalhashesbestätigt.
  KeineRealbefehle,Produktions-/GrenzwertänderungenoderProfilaktivierung.
  Bericht docs/front_hd_calibration_2026-11-12.md ergänzt. Auflösungsbewusste
  Bildfehler/robusteGewichtungkünftiggemeinsamdefinieren;mm/Gradseparatprüfen.

## Links hinten: reale Kalibrierung abgeschlossen, 2026-11-12

- Vollständige **41 Ansichten** mit eigenen HTTP-VGA-Bildern (640×480):
  **33 Fit / 8 vorher reservierte Prüfbilder**, alle akzeptiert, jeweils24 Ecken,
  41 verschiedene decodierte Bilder. Kein Bild ausgeschlossen oder überschrieben.
  Fester Fokus406Manual,33333µsManual/Gain16; kein fremdes Kamera-/HD-Profil.
- **Intrinsics PASS:** Fit-RMS0,1143px, medianer Prüf-RMS **0,1481px**.
  **Hand-Auge PASS:** Prüf-Reprojektion **0,2496px**, Board-Translationsstreuung
  **0,7402mm**, Rotationsstreuung **0,1671°**. Interne zurückgehaltene Prüfung,
  keine absolute Genauigkeitsgarantie. HTTP-Empfang ist kein Belichtungszeitstempel.
- Ergebnis und Rohdaten versioniert unter
  `setup/calibration/hardware_handeye/left_rear_20261112/result_v1/`:
  `summary.json`, `intrinsics.json`, `handeye_result.json`, vollständige41er-
  Roh-/Annotationsdaten und SHA256-Manifest. Quelle/Originalrollen erhalten.
  Ergebnis zunächst nicht automatisch aktiviert. Auf späteren ausdrücklichen
  Nutzerauftrag am selben Tag global in **hardware_20261112_v1** übernommen;
  archiviertes ursprüngliches `activated:false` bleibt als Historie erhalten.
- Abschluss: SafetyNORMAL, alle linken Motioncontroller inaktiv, Endfehler
  **0,0000338rad**, Positionsänderung über das letzte0,5s-Prüffenster0,0000424rad.
  Keine Rückfahrt; Arm bleibt an letzter Aufnahmeansicht. Kein fremder Arm gestoppt.

### Unterbrechungen und Wiederaufnahme

- Bei sample029 nativer **C159A5/Wrist3**;29 Bilder gesichert, eigene Action
  gecancelt und linke Motioncontroller inaktiv. RTDE bestätigte0kg/CoG[0,0,0].
  Nutzer meldet Ursache behoben; anschließend1kg/CoG[0,0,0],NORMAL/PLAYING/Link
  geprüft. Kein Nutzlastwert vom Agenten geraten/gesetzt, keine Autoquittierung.
  Separater29er-Diagnosefit bleibt historisch/inaktiv (Mindestzahl30).
- Zwölf Originalrestziele neu aus tatsächlichem Start verbunden; zuerst vor jeder
  Bewegung wegen fehlender rechter Rear-Telemetrie abgebrochen. Alter Manager18298
  stürzte nach PrimaryClient-Pipeline-Überlauf mitExit−11 ab. Nur diesen Treiber
  als `uwa-right-rear-calibration-observer` wieder gestartet, Motion inaktiv,
  kein Power/Play/Armziel. Linker Dienst und Frontmanager erhalten.
- Nach32 Aufnahmen Abbruch wegen Frontbewegung unter alter Stillstandsregel.
  Nutzer bestätigt hier ausdrücklich: **„Ja, diagonale Arme erreichen sich nicht;
  Restreihe ausführen“**. Das ist eine Nutzerangabe zur Reichweite, keine Messung.
  Neue neunRestziele `resume_diagonal/batch.json` (d913d5c2…) samt unveränderten
  Originalzielen/Prüfrollen geprüft; nur gegenseitigeLR/RF-Kollisionen und deren
  Stillstandsabhängigkeit ausgenommen. Übrige Kollisionsprüfung/nativeUR-Sicherheit
  erhalten. Vorherige pauschale Warte-/Einarmangaben sind für dieses Paar überholt.
- AutoReview hatte die neue Ausnahme zunächst mangels konkreter Freigabe im
  aktuellen Gespräch abgelehnt; dabei keine Fahrt. Erst nach obiger ausdrücklicher
  Bestätigung und erneutem Gesamtcheck gestartet. Diagonaltests2/2 bestanden.
- Fortsetzung bis sample040 und Auswertung Exit0; Originaldaten/Haltebilder
  erhalten. Logs `preparation/{series-run,resume-run-after-observer,
  resume-diagonal-run}.log`, Abschluss `completion-state.json` und Freigaben dort.
  Weitere Front-HD-Arbeit läuft separat und wird hier nicht gesteuert.

### Abgeschlossene Erstpose und Bildprüfung

- Aktueller Abschluss nach Nutzerfreigabe „Vorschau passt, Fahrbereich frei –
  erste Pose anfahren“: genau `approach_ready/plan.json`(f6296105…) ausgeführt,
 34,173s, native Action erfolgreich/Result0, unmittelbarer größter Zielwinkel-
  Fehler0,0000158rad; späterer Stillstandssnapshot0,0000513rad. NativeSafetyNORMAL,
  ExternalControltrue, velocities0; skalierter JTC hält die erreichte linke Pose,
  andere linke Bewegungscontroller inaktiv. Keine Rückfahrt oder anderen Armziele.
- Front-Endvergleich0rad, Rear-Endvergleich0,0000246rad zum Wegstart, keine
  kontinuierlichen Maximalwerte behaupten. Erledigte eigene Domain68-Animation
  geschlossen, Hardware-GUIs/drei Treiber erhalten.
- Wirkliches640×480-Bild: erstes AF-Übergangsbild unscharf, danach viermal
  alle17 Marker/24 Ecken links(IDs0–16), Muster vollständig/unverdeckt im
  geprüften Bild. Fünf unterschiedliche Payloads, Fokus406Auto/33333µsAuto/Gain16
  nur gelesen, keine Kameraparameter geschrieben. Inspektionsbilder sind keine
  Fit-/Prüfaufnahmen; noch kein sample000/Kalibrierfit/aktives linkes Profil.
- Zusätzlich nur geplant:40 Zusatzansichten in `left_rear_20261112/batch_plan/`,
 8 unabhängige Prüfrollen, später41 Gesamtansichten/33Fit/8Prüfung. Reine
  Bewegungsdauer709,57s plus Stillstand/Aufnahme. Damals noch keine ganze Folge freigegeben
  oder gestartet; diese Vorbereitung ist durch die oben dokumentierte Serienfreigabe
  und tatsächliche Aufnahme überholt. `first_view_inspection/inspection.json` und
  `preparation/first-view-completion.json` halten aktuellen Stand fest.

### Vorherige Vorbereitung und Verbindungsdiagnose

- Nutzer beauftragt Vorbereitung left_rear192.168.8.169 und ausdrücklich
  Remote-Einschalten/Bremsenlösen/Programmstart über vorhandenen MATCH-Ablauf.
  Linkes40mm-A3-Tischboard(IDs0–16) und links vorne aufrechtes Home unverändert
  bestätigt. Mobile38mm-A4-Vorlage ist hierfür nicht das Ziel.
- Native Verbindung/Wrist-HTTP640×480 nachgewiesen; drei unterschiedliche Bilder,
  Fokus439Auto/Belichtung33333µsAuto/Gain16 nur gelesen. Aktuell noch kein Board
  im Bild; passende feste Optik nach erster tatsächlich erreichter Sicht prüfen.
- Hardware-CLI für alle vier Arm-IDs erweitert,25 gezielte Tests inkl. linker
  MoveIt-/IK-Sweeps und zwei Startup-Warnpfade. MATCH-Startup `.warn`→`.warning`
  für Lyrical korrigiert. Individuelle gespeicherte UR7e-Werkskinematik genutzt.
- Wiederholte Startfehler schließlich lokalisiert: alter linker Manager8998FDs,
  davon8967Sockets. Scriptserver verwarf tatsächlich eingehende Verbindungen
  mit FD8997/8998 wegen FD_SETSIZE1024. Kein URCap-Konfigurationsfehler als
  Ursache behaupten; ursprüngliche PLAYING/Link-false-Diagnose ist überholt.
- Nur geprüften linken Launcher nach bestätigter Inaktivität sauber ersetzt,
  neuer Benutzerdienst `uwa-left-rear-calibration-driver`, neuer Manager48FDs.
  MATCH-Start jetzt Exit0 und tatsächlicher `robot_program_running=true`,
  Safety NORMAL, vier Motioncontroller inaktiv. Rechte Manageridentitäten
  unverändert, parallele Front-Kameraarbeit erhalten. FD-Wachstumsursache noch
  ungeklärt; Neustart beseitigt konkreten Zustand, kein Langzeitfix nachgewiesen.
- Hinten rechts jetzt RUNNING mit plausiblen Livewinkeln. Front bleibtPOWER_OFF/
  Local, nicht-null gemeldete Winkel unabhängig per reinem RTDE gegengeprüft
  (max4,5e−16rad Unterschied). Keine Power-/Programm-/Kameraänderung vorne rechts.
  Linke Home-Hindernispose weiterhin Nutzerangabe, keine Encodermessung.
- Damals frische erste Sicht `setup/calibration/hardware_handeye/left_rear_20261112/
  approach_ready/plan.json`:34,173s, vollständiger MoveIt-Sweep, `--check-only`
  bestanden; RViz-Vorschau Domain68 offen. Nominelle Kamera[-0,45;0,28;1,453]m,
  etwa55cm über linkem Board. Diese erste Fahrt ist inzwischen wie oben
  dokumentiert ausdrücklich freigegeben und erfolgreich abgeschlossen.
- Erst konkrete Vorschau/Fahrbereich freigeben, erste Pose ausführen und echtes
  Board-/Fokusbild prüfen. Vorgesehen41 Ansichten(33Fit/8vorabPrüfung), wide;
  ganze Reihe erst danach planen/freigeben. Keine Rückfahrt oder Profilaktivierung
  aus dieser Vorbereitung ableiten. Frühere reine Entwurfsvorschau bleibt
  nicht ausführbar und wurde nicht ausgeführt.
- Diagnose/Snapshots/aktueller Ablauf unter .../preparation/;
  [Wiedereinstieg](docs/left_rear_calibration_preparation_2026-11-12.md),
  Arbeitsstatus work/left-rear-calibration-preparation.md. Bisherige Messprofile
  und rechte Hardwaretreiber erhalten, neuer linker Dienst bleibt bereit.

## HD-Bilddienst für neue Hardwarekalibrierung,2026-11-12

- Nutzer möchte nativen5MP-Aufnahmeweg als Dienst für erneute Kalibrierung und
  fragt nach Grünstich. Auf echtem Foto24 ChArUco-Ecken; Farbbild/Graubild
  identische IDs/Pixelkoordinaten. Farbstich allein somit hier kein Erkennungs-
  hindernis, neue Geometrie-/Genauigkeitsaussage erst nach unabhängiger Prüfung.
- Neuer ROS-Dienst `wrist_hd_service`,HardwareDomain66,
  `/uwa_hardware/right_front/wrist_camera_hd/{capture,status}`(std_srvs/Trigger),
  dazu `image/compressed`. Drei native2592×1944-JPEGs pro Trigger mit Settings,
  Gerätezeiten/Sequenz im Capturelog,Schärfe-/Clippingwerten,Prüfsummen.
  Kamera-/ROS-Empfangszeit nicht als synchronen Belichtungszeitpunkt ausgeben.
- Nur real ermittelten Kamera-Vision-runit-Dienst kurz freigeben, temporäres
  V4L2-C-Werkzeug,Normal abwarten und alle ursprünglichen Parameter forceRefresh
  vergleichen. Unabhängiger Remote-Watchdog bei Verbindungs-/Prozessverlust.
  Keine Kennwörter im Code/Parametern/Dateien; private SSH-ControlMaster-Sitzung.
- Hardwareaufnahme `--camera-source wrist_hd_service` integriert. Client spinnt
  Telemetrie während RPC, behält Stillstands-/Guardfehler und wartet vor Fehler-
  weitergabe auf erfolgten Restore. Eckenzahl/Schärfe wählen bestes Burstbild.
  Eigene neue HD-Sitzung, kein HD/VGA-/Kamera-ID-Wechsel. Neuer Intrinsicsfit
  ausschließlich aus HD-Trainingsdaten; reservierte Prüfbilder bleiben getrennt.
- **Reale Service-/Clientprobe bestanden:**3×2592×1944,je24 Ecken,16,04s,
  502 Monitorhook-Aufrufe,max32,8ms Abstand; Status weiter CAPTURING erreichbar,
  zweite Aufnahme abgewiesen. Kein echter Bewegungs-/Stopptest daraus ableiten.
  Alle Originalsettings wieder identisch, normaler Kameradienst wieder aktiv.
  Vorangehendes reines Discoveryproblem vor Kameraänderung behoben; Log erhalten.
- Paket gebaut,29 gezielte Offline-Tests bestanden (u.a.Nativegröße,Framewechsel,
  Restorefehler/Erholung,Mode-/Identitätsmix,runit-Zuordnung und transienter
  Bewegungsfehler bis Restore abwarten). Nachweise setup/logs/uwa-wrist-hd-*.log,
  uwa-wrist-hd-live-adapter.json; Rohbilder in dessen Burstverzeichnis.
- Dienst/SSH-Sitzung fürright_front aktuell offen,keine neue Kalibrierfahrt
  gestartet. Noch keine40–50-Posen-HD-Reihe/HD-Genauigkeit nachgewiesen.
  Andere Kameras über diesen Dienst ungetestet. Pro Stellung rund16s Zusatzzeit,
  reguläre URCap-Vorschau dabei kurz unterbrochen,Grünstich weiter sichtbar.
  [Start/Bedienung/HD-Sitzung](docs/wrist_hd_service.md),work/wrist-hd-service.md.

## Natives5MP-Foto Front-Wrist erfolgreich,2026-11-12

- Nutzer beauftragt erneuten Vollauflösungstest right_front192.168.8.103 und
  stellt legitimen temporären SSH-Zugang bereit. Zugangsdaten nicht speichern.
  Nach Aktivierung des SSH-Diensts Anmeldung erfolgreich, Sitzung danach beendet.
- Tatsächlich UCC4.1.0.164735/CQ0-1.4.0,uniqueCamId01D10E1900090912.
  HTTP-Vorschau640×480; direktes V4L2-Gerät bietet MJPEG2592×1944 an.
- **Native Datei2592×1944/5038848Pixel/332800Bytes** per V4L2-MMAP-Aufnahme
  auf Controller erzeugt und perSCP heruntergeladen, lokal decodiert/Größe und
  SHA256 bestätigt. Kein Upsampling, kein Barcode-/SaveImage-/FTP-Programm.
  Datei setup/calibration/wrist_hd/right_front_20261112/controller-artifacts/
  native-2592x1944.jpg; [Prüfbericht](docs/wrist_native_photo_2026-11-12.md).
- Nur Kamera-Vision-Dienst über seinen vorhandenen runit-Supervisor kurz
  gestoppt/gestartet. Erster Versuch Gerätnochbusy, zweiter mit begrenztem
  Freigabe-Retry erfolgreich. Keine Roboterprogramme, Motion, UR-/ROS-Treiber
  oder Simulationen angefasst. Kamera-Konfigurationsdateien unverändert.
- Früher automatischer Restore zu früh während Initialisierung fehlgeschlagen;
  anschließend im tatsächlichen Normal vom PC vollständig wiederhergestellt.
  Alle Originalfelder forceRefresh-identisch(Fokus435Manual/60000µsManual/
  Gain16/AutoLED0). final-restoration.json ist abschließender Nachweis; frühe
  fehlgeschlagene Rohberichte separat erhalten. AutoLED-Setter meldet teilweise
  Fehler15 trotz angewandtem Wert, Rücklesen entscheidend. Normaldienst und
  reguläre640×480-Vorschau wiederhergestellt.
- **Grünstich im direkten JPEG**, Farbwiedergabe/Weißabgleich noch zu qualifizieren.
  Bestehendes640×480-Intrinsicsprofil nicht als5MP-Kalibrierung verwenden.
  Native Aufnahme bewiesen, kein fertiges allgemeines GUI-Aufnahmewerkzeug und
  kein isolierter Nachweis, dass erst das4.1-Update5MP ermöglicht hätte.
- Eigene Aufgabe work/front-wrist-hd-ssh.md abgeschlossen; parallele aktive
  left-rear-Kalibrierungsvorbereitung erhalten. Bild-/Herstellerdaten bleiben
  außerhalb Git unter setup/calibration/wrist_hd/right_front_20261112/.

## Gemessene Kalibrierungen gemeinsam übernommen,2026-11-11

- Expliziter Nutzerauftrag: ermittelte Posen/Kalibrierungen dauerhaft speichern
  und in Simulation, Visualisierung, Kollisionsprüfung und weiteren Verbrauchern
  verwenden. Kein Bewegungsauftrag. [Bedienung/Umfang](docs/applied_calibrations.md).
- Installiertes versioniertes Bündel unter
  `uwa_cell_description/config/calibration/hardware_20261111_v1/`: unveränderte
  Ergebniskopien, drei Werkskinematiken, CameraInfo-YAMLs, benannte Posen und
  SHA256-Manifest `profile.json`. Rohbilder/ursprüngliche Ergebnisse erhalten;
  deren damaliges `activated:false` ist historisch, nicht aktueller Profilstatus.
- Aktiv: individuelle Kinematik left_rear/right_front/right_rear, Intrinsics
  beider rechten Kameras(640×480, Rear404/Front435Manual), Rear-Hand-Auge
  tool0→optical sowie Rear-Basis→Board als Referenzframe. Front-Hand-Auge
  weiterhin abgelehnt(0,652°>0,5°), keine relative rechte Basispose aktiviert.
- `cell_layout_calibrated.yaml` ist jetzt Standard, verweist auf die unveränderte
  zentrale Nominalgeometrie und das Profil. `cell_layout.yaml` bleibt expliziter
  Nominal-Rückfall. Gemeinsamer Python-Loader im Beschreibungs-Paket wird von
  Gazebo und Overlay verwendet; MoveIt/Hardwareplanung verwenden denselben
  Renderpfad. Kein Visualisierungsimport aus Gazebo erforderlich.
- Neue Aufnahmeplanung verwendet gespeicherte K/D inklusive Verzeichnung und
  kennzeichnet erforderlichen Fokus; nomineller Rückfall nur ohne passendes
  Intrinsicsprofil. Keine Übernahme dieser Planungswerte als neue Fit-Beobachtung.
- Inventar verweist auf archivierte Werksdateien, bytegleich zu den zuvor
  verwendeten Dateien. Treiber/GUI nicht neu gestartet. Optische TFs/Sensorpose
  werden geändert, angenäherte Gehäuse-/Greifer-Kollisionskörper nicht aus einem
  Optikfit versetzt. Welt-/Tisch-/Basisanker, OAK-Pose, Scan und Startgelenke
  bleiben vorläufig/unverändert. Intrinsics erfordern passenden Fokus/Bildmodus.
- `named_poses.json`: tatsächliche Park-Snapshots und erste Aufnahme-Snapshots
  beider rechter Arme, rad/Gelenkidentitäten/Quellenhashes; ursprüngliche
  Parkzielwinkel zusätzlich erhalten. Keine Live-Hinderniszustände, keine
  automatischen Fahrten und keine Wiederverwendung alter geprüfter Wege.
- Zusätzliche Simulationsfits je Messprofil getrennt unter
  `setup/calibration/profiles/measured_<Profilhash>/`; bisherige ideale
  `profiles/active.json` bleiben für das Nominalmodell erhalten. Kein alter
  Simulatorfit überschreibt ungeprüft reale Messwerte.
- Fünf Pakete gebaut;99 gezielte Offline-/MoveIt-Prüfungen bestanden, einschließlich
  identischer FK in Simulation/Planung/Overlay. Gespeicherte reale FK-Matrizen
  sample000 beider rechter Kamerareihen mit neuem Modell exakt reproduziert.
  Live-Gazebo: neun aktive Controller, fortschreitende Uhr, endliche Gelenke,
  zwei rechte640×480-Streams, K/D und Rear-Optik-TF passend zum Profil.
  Simulationsbackend IDLE ohne Aktivierung früherer Idealprofile, alle vier
  Kameras24 Ecken erkannt. Eigene Headless-Testsimulation und eigener Backend
  wieder sauber beendet; ursprünglicher inaktiver Simulationszustand erhalten.
- Nachweise `setup/logs/uwa-calibration-integration-{build,tests}.log`,
  `uwa-calibration-integration-{live,backend}.json`; kompakter
  [Prüfbericht](docs/calibration_integration_validation_2026-11-11.json).
  Keine Hardware-Fahrten/Power/Brake/Play. Die vorhandene J-PARSE-Online-
  Kollisionsoption bleibt deaktiviert; MoveIt-Modellverbesserung ist kein
  vollständiger aktiver Online-Zellenschutz und keine absolute Vermessung.

## Mobiles A4-ChArUco-Board für externe OAK,2026-11-11

- Nutzer besitzt einen am UR montierbaren A4-Holzträger und möchte Papier flach
  aufkleben; Muster soll die nutzbare A4-Fläche weitgehend ausfüllen.
- Eigene einseitige Vektorvorlage `output/pdf/uwa_mobile_charuco_A4_1to1.pdf`:
  A4 quer297×210mm, Muster266×190mm,7×5 Felder38mm, Marker28mm,
  DICT_4X4_100 IDs75–91, weiße Ränder15,5mm seitlich/10mm oben und unten.
  Kontrollstrecke100mm. Tischboards40mm/IDs0–16 und50–66 bleiben unverändert.
- Definition `uwa_cell_description/config/mobile_charuco_a4.yaml`, Generator
  `scripts/print_mobile_charuco.py`, Bedienung `docs/mobile_charuco_a4.md`.
  Isolierte Druckumgebung `.venvs/charuco-print`, keine ROS-/Hardwareänderung.
- Prüfung am tatsächlichen300-dpi-PDF-Render:17/17 Marker,24/24 Ecken,
  maximale metrische Eckabweichung0,082mm. PDF-Geometrie38mm-Felder,
  100mm-Strecke, A4/1Seite und Vektorinhalt geprüft, abschließende Sichtprüfung
  bestanden. Report `docs/mobile_charuco_a4_print_validation_2026-11-11.json`.
- Physischer Ausdruck noch nicht nachgemessen.100%/Tatsächliche Größe drucken,
  Seitenanpassung aus;100mm-Strecke und38mm-Feld nachmessen. Mattes Papier
  vollflächig faltenfrei kleben, weißen Rand erhalten, Halter außerhalb Muster.
  Bewegliches Board noch nicht in Detektoren aktiviert; eigene Definition
  explizit verwenden. Werkzeug-Board-Transformation unbekannt/nicht kalibriert.

## Left rear: GUI-/ROS-Treiberstart geprüft,2026-11-11

- Nutzer beauftragt Aufnahme in GUI und echten Treiber-/Starttest. Individuelle
  Werkskinematik erfolgreich rein lesend aus192.168.8.169 extrahiert, im Inventar
  hinterlegt. Datei setup/calibration/hardware_first_view/ur_kinematics/left_rear.yaml,
  Hashcalib_12205487632174246172; konfigurierter Typur7e, Modellressourcen vorhanden.
- Zusätzliches echtes Qt-UWA-Fenster **UWA · Direct UR Test · Left rear** offen,
  eigener Treiber ausschließlich left_rear/Domain66/Ports52001–52004. Bestehendes
  rechtes Besitzerfenster18120 und dessen Treiber18238/18239 erhalten. Nicht als
  allgemeine zukünftige PID-Konfiguration verwenden; laufender Stand neu prüfen.
- GUI Start drivers, Read joint angles undPrepare UR erfolgreich. Sechs reale
  präfixierte Gelenke/2592Samples/493,94Hz, gemeldete Geschwindigkeiten0rad/s,
  maximale Positionsstreuung0,000102rad. Fünf Broadcaster aktiv, vier Motion-
  Controller inaktiv, keine Fahrziele. Prepare bei bereits RUNNING/NORMAL ist
  kein Nachweis eines Kaltstarts ausPOWER_OFF oder echten Bremsenlösens.
- Nach Nutzerbestätigung Host192.168.8.209/Port52002 undRemote: UR bereits
  PLAYING ros.urp/Remote=true vor PC-Prüfung. Kein Programmneustart gesendet.
  Treiberlog bestätigt Programmanfrage/-übertragung und Reverse-Verbindung.
  External-Control-Link18:23AWST per reliable/transient_local gelatchtem
  robot_program_running=true bestätigt, nativer SafetyMode1/NORMAL.2430
  Gelenksamples bei492,55Hz, alle gemeldeten Geschwindigkeiten0rad/s,
  Positionsstreuung0,000104rad. Alle vier Bewegungscontroller weiter inaktiv.
  Programm-/ROS-Verbindung damit geprüft, keine Bewegungserprobung behauptet.
  Erster Diagnoseempfang mit volatile-Sensor-QoS lieferte keinen gelatchten
  Linkwert; korrigierter Empfänger mit passender QoS liefert den Status.
- Gelegentliche500Hz-Overrun-Warnungen beobachtet; kein Echtzeit-/Fahrnachweis
  aus bloßem Gelenkempfang. Report/Screenshots unter setup/logs/uwa-left-rear-driver/,
  Sitzung20261111_181624_259914_22b7a96c; Werkskinematiklog
  setup/logs/uwa-left-rear-factory-kinematics.log. [Bedienung](docs/ur_control_gui.md).
- Arbeitsstatus work/left-rear-driver.md abgeschlossen: GUI/Treiber-/Prepare-/
  External-Control-Verbindungstest erfolgreich. Nachweise external-control-result.json
  undgui-status-confirmed.json unter setup/logs/uwa-left-rear-driver/.
  Neues linkes Besitzerfenster/Treiber offen lassen; rechte Treiber unverändert.
  Keine Trajektorien-/Jog-/Kalibrierfahrt ausgeführt. Andere Front-Ergebnisse erhalten.

## Hinterer linker UR erreichbar,2026-11-11

- Nutzer meldet hinteren linken Roboter unter8.169. Zugeordnet als
  **left_rear=192.168.8.169**,Inventar und Arbeitsregeln ergänzt; kein neuer
  Hardwaretreiber gestartet. Nur lesende Netzwerk-/Dashboard-/Kameraabfragen.
- Ethernet enp87s0/PC192.168.8.209;3/3 Pings,0% Verlust,0,278ms im Mittel.
  Ports29999,30001,30002,30003,30004 und4242 erreichbar.
- Dashboard18:07AWST: RUNNING,NORMAL,STOPPED ros.urp,Remote=false;
  PolyScope5.25.0.130258,Seriennummer20265701623,ModellantwortUR5. Vorhandenen
  konfigurierten Typur7e erhalten: Dashboardfamilienname allein ist kein
  unabhängiger Nachweis der tatsächlichen UR5e-/UR7e-Variante.
- Kamerahello: UCC3.44.0.149696,FirmwareCQ0-1.4.0,Normal,
  uniqueCamId06561F1400090106. Kein Bild-/Fokus-/Beleuchtungswechsel vorgenommen.
  Nachweis setup/logs/uwa-left-rear-reachability-20261111.json.
- Eintrag work/left-rear-reachability.md abgeschlossen; keine Power-/Brake-/
  Play-/Reset-/Bewegungsbefehle, Front-Kalibrierarbeit erhalten.

## Kamera-USB nach Nutzerupdate sichern,2026-11-11

- Nutzer aktualisiert Kamera-URCap selbst, meldet anschließend „Vision system
  down … files extracted correctly“ und stellt den Robotiq-Stick am PC bereit.
  Neues Ziel: vollständiges Image plus Dateisicherung, danach passendes Paket
  direkt ins USB-Wurzelverzeichnis. Nutzer bestätigt Zielversion **4.1.0**.
- Kingston16GB,Seriennummer E0D55EA574E5F3A1E91F0FDB,FAT32/KINGSTON/289C-1ADC:
  alter Stand UCC1.11.1.10337/VSL1.0.23. Vollständiger Gerätelesevorgang erfolgreich,
 15472047104Bytes; unabhängige SHA256-Gegenprüfung **identisch**, Hash6319d351…83ab746.
  Zusätzlich310 Dateien/1263252963Bytes unter files/ gesichert und manifestiert.
  USB-Dateiaustausch nach Zielversionsbestätigung4.1.0 erfolgreich: neuer
  vision_system-Ordner/VSL2.0.0 und Camera-URCap4.1.0.164735 direkt im Root.
  Alle303 Dateien nach Aushängen/RO-Neumount SHA256-identisch zum Paket, keine
  alten Zusatzdateien im vision_system. Sieben übrige Originaldateien unverändert.
  Um16:42AWST ausgehängt, bereit zum Abziehen. usb-update-report.json als Nachweis.
  Nutzer bestätigt anschließend: Wiederherstellung hat funktioniert.
  Dies ist eine Nutzerbestätigung, kein zusätzlicher eigener Pendanttest. Sicherung setup/backups/robotiq-usb/20261111-before-ucc-update/.
- Separat geprüftes ZIP UCC4.1.0 enthält303 Dateien undVSL2.0.0; Startskript
  verlangt diesen VSL-Stand. Versionsmischung ist plausible Fehlerursache,
  aktuelle Controllerinstallation nicht selbst geprüft. Dateien nicht aus
  verschiedenen Versionen mischen. Alte eingebettete SHA1-Tabelle passt schon
  nicht vollständig zum neuen Originalpaket; maßgeblich ist der ZIP-Abgleich.
- Arbeitsstatus work/wrist-usb-recovery.md; [Anleitung/Prüfbefund](docs/wrist_usb_recovery_2026-11-11.md).
  Andere Front-/Bahnplanungsarbeiten erhalten; keine Roboterfahrt, ROS-/
  Controllerneustarts, SSH-Anmeldung oder Hersteller-Installer am PC.

## Front-Versuch mit62 Bildern abgeschlossen; Hand-Auge nicht freigegeben,2026-11-11

- Nutzer hat neue Rear-Parkvorschau und anschließend die gesamte Front-
  Erstansicht/62-Bilder-Folge bei freiem Fahrraum konkret freigegeben.
  Ursprüngliche Ziele und Fit-/Prüfrollen in allen Wiederaufnahmen erhalten,
  nur Verbindungen aus jeweils neu gelesenen Winkeln neu geprüft. Genau ein
  Arm gleichzeitig, komplette MoveIt-Zelle; linke Nutzer-Home-Stellungen
  weiterhin nominell. Keine Power-/Brake-/Play-/Reset-Aktionen durch Agenten.
- Rear-Parken erfolgreich:56,5068s, native skalierte JTC SUCCEEDED/0,
  Zielabweichung0,0000296rad. Plan/Freigabe/Ergebnis unter
  setup/calibration/parking/right_rear_20261111/; Fingerprint
 49e218e0b86a4910826d23c5d1250a82366e32c5d0ef3892f4dc0944259869f3.
  Front-Erstansicht78,903s ebenfalls erfolgreich,0,0000318rad Endfehler;
  approach/ unter Front-Datensatz. Reales Board24 Ecken.
- Front-Kameradienst nach Nutzer-URCap-/USB-Recovery wieder erreichbar640×480.
  Ein Autofokustrigger verursachte HTTP-Reset; danach keinen weiteren Trigger
  verwendet. Tatsächlich scharfen Fokus435 manuell fixiert, mehrere frische
  Bilder/ForceRefresh bestätigen435Manual/60000µsManual/Gain16. LED-Readback1/53,
  keine physische LED-Leistungsbehauptung. Original-/Diagnosezustände erhalten.
- **Datensatz vollständig:** setup/calibration/hardware_handeye/right_front_20261111/.
 62 akzeptierte, unterschiedliche Bilder=50 Fit/12 vorab reservierte Prüfbilder,
 14…24 Ecken, fester435-Fokus. Observierte Bildpunkte x117…586/y76…402, breiter
  als Rear-Reihe; keine Behauptung vollständiger Randabdeckung. HTTP-Bilder
  stationär über wechselnde Payloads zugeordnet, ohne Sensorbelichtungszeit.
- **Intrinsics PASS:** Fit-RMS0,28901px, Median Prüf-RMS0,29924px.
  fx660,868/fy665,589px, cx328,433/cy176,219px; vollständige K/D/Unsicherheiten
  in intrinsics.json. Nicht als gleiche Optik wie Rear404-Fokus behandeln.
- **Hand-Auge FAIL:** unabhängige12 Prüfbilder Median-Reprojektion0,74780px,
  Boardpositions-RMS2,34399mm (beides innerhalb Grenze), Rotations-RMS0,65195°
  über0,5°. Keine Ausreißer ausgeschlossen. Profil **activated:false**,
  keine TF-/Hardware-/Gazebo-Montage geändert. Keine Gütegrenzen gesenkt und
  kein günstigeres Subset als Ersatzprofil gewählt.60er-Zwischenstand mit49
  Fit/11 Prüfung bereits bei0,670° gescheitert, separat in analysis_60_views/.
- **Bildzahlvergleich innerhalb Front-Kamera:** dieselben12 Prüfbilder,
  vier deterministische verschachtelte Teilmengen bei20/33 Fit-Bildern und
  einmal alle50. Rotations-RMS20:0,623…0,775°,33:0,607…0,745°,50:0,652°.
  Bildfehler ebenfalls ähnlich (etwa0,72…0,80px). Kein klarer großer Gewinn
  allein durch höhere Bildzahl; alle Varianten verfehlen Rotationsgrenze.
  Kein formaler Signifikanztest/kein absoluter Genauigkeitsnachweis.
- Versionierte Bewertung unter evaluation_v1/: intrinsics.json,
  handeye_result.json, manifest.json mit SHA256, count_summary.json,
  validation.png/count_comparison.png. Vergleichsdetails count_comparison/.
  [Befund/Bedienung](docs/front_calibration_2026-11-11.md).
- Unterbrechung043: Kabel verdeckt Board,9 Ecken -> automatischer Bildabbruch/
  Front inaktiv. Nutzer sichert Kabel ohne Kamera-/Boardbewegung; neun gemeinsame
  Ecken vor/nach Sicherung Median0,025px/Maximum0,063px Verschiebung. Abgelehnter
  Versuch mit SHA256 unter rejected/sample_043_attempt_01/ erhalten, gleiche
  Pose neu mit24 Ecken aufgenommen, Originalziele44…61 fortgesetzt.
- Unterbrechung060: nativer C153A5/Wrist3 am17:50:33Perth, vom Nutzer als
  gespannter/aufgewickelter Kabelstrang bestätigt und gelöst. Pending-Action
  per SIGINT gecancelt/Front inaktiv, kein automatisches Quittieren. Native
  Zustände danach NORMAL/PLAYING, tatsächliche neue Stellung eingelesen;
  letzte zwei Originalziele neu geprüft/erfolgreich ausgeführt. Kamera beim
  Wiederanlauf auf424Auto zurückgesetzt, vor Weiterfahrt435Manual identisch
  wiederhergestellt und dreifach per Hardware-Readback geprüft.
- Behobene Ablauf-Lücke: ProtectiveStop kann Programmlinktrue beibehalten.
  JointObserver liest jetzt tatsächliches natives SafetyMode und cancelt die
  eigene Action bei Stop-Modi sofort; NORMAL/REDUCED zulässig. Keine neuen
  Dashboard-/Remote-/Armzahl-/GUI-Besitz-Gates.22 abschließende gezielte Tests
  bestanden, zusätzlich3 Standard-Vierarm-/Fit-/Holdout-Regressionen.
- Endzustand18:03Perth: beide URs NORMAL/PLAYING/Linktrue. Rear hält Parkpose,
  Front hält letzte Aufnahmepose mit aktivem skalierten JTC; übrige Bewegungs-
  controller inaktiv. Frontzielabweichung0,0000460rad, Rear-Endvergleich zum
  letzten Wiederaufnahmestart0,0000858rad (kein Maximum über gesamte Reihe).
  completion_state.json. Eigene Vorschauen beendet, Hardware-GUI/Treiber offen.
- Front-Dashboardversion nach Nutzerupdate5.26.3.140631 gemessen und erst nach
  allen Fahrten im Inventar nachgeführt; Rear unverändert5.10.1.106310.
  Alte gespeicherte Planfingerprints dadurch zusätzlich veraltet, für neue
  Fahrten neu planen. Keine bestehende geprüfte Trajektorie nachträglich geändert.
- Nächster fachlicher Schritt: Ursache der Rotationsinkonsistenz gezielt prüfen
  (Bild-Pose-Schätzung/Intrinsics/Board und mechanische Stabilität), statt nur
  mehr gleichartige Bilder aufzunehmen. Hypothesen nicht als nachgewiesene
  Ursache ausgeben. Kabelführung muss den ganzen vorgesehenen Wrist-Bereich
  erlauben; Sichtblockade und Wrist3-Kabelspannung wurden real beobachtet,
  der lose Kabelverlauf ist nicht Teil der Kollisionsgeometrie. Kein validiertes
  Front-Hand-Auge-/relatives-Basisprofil
  übernehmen, bevor unabhängige Prüfgrenze bestanden ist.

## Erfolgreich abgeschlossen: reale Hand-Auge-Reihe, 2026-11-11

- **Qualitätsnachfrage, gleicher Tag:** Nutzer erwägt Rear-Parken und Front-
  Kalibrierung mit50% mehr Bildern. Offline-Test mit20/26/33 Fit-Bildern gegen
  dieselben8 Prüfaufnahmen zeigt keinen klaren monotonen Bildzahlgewinn;
  Intrinsics etwa0,22px, Hand-Auge etwa0,40–0,50px. Kein Beweis, dass mehr oder
  räumlich vielfältigere Bilder nichts bringen. Post-hoc-Diagnose, keine
  Änderung/Neuauswahl des gespeicherten Profils. Details und Vergleichsdesign
  [Qualitätsbewertung](docs/calibration_quality_review_2026-11-11.md).
  Empfehlung: Front separat ca62 Ansichten mit50 Fit/12 reservierter Prüfung,
  bessere Bildabdeckung und Teilmengenvergleich innerhalb derselben Kamera.
  Gleicher Kameratyp nicht als identische individuelle Intrinsics behandeln;
  gemeinsames Board dient später relativer Basispose. Noch kein neuer realer
  Park-/Frontweg aus diesem Vorschlag freigegeben oder ausgeführt. Dafür
  bisherige Code-Anzahlgrenzen gezielt anpassen, keine Gütegrenzen absenken.

- **Ergebnis15:43Perth:** alle32 Restaufnahmen ohne erneuten Schutzstopp
  abgeschlossen. Insgesamt41 akzeptierte Ansichten mit je24 Ecken,33 Fit/8
  vorab reservierte Prüfbilder, keine Ausreißer ausgeschlossen. Manuell404,
 640×480,60000µs/Gain16; alle41 decodierten Bildhashes unterschiedlich.
- Intrinsics **PASS**: Fit-RMS0,24368px, Median der Prüf-RMS0,22200px;
  fx659,800/fy664,507px, cx317,123/cy180,567px. Reale Daten, kein nominelles K.
- Hand-Auge **PASS** samt vorhandener Profilvalidierung: unabhängige8
  Prüfbilder Median-Reprojektion0,46553px, Boardpositions-RMS2,65977mm,
  Rotations-RMS0,24623°. Bootstrap der Kameramontage ungefähr1mm je Achse und
 0,137°; Wiederholbarkeit/interne Konsistenz, **keine absolute Genauigkeitszusage**.
  Geschätztes T_tool0_camera XYZ[0,808;50,141;22,583]mm; vollständige Matrix
  und Verzeichnung in den Ergebnisdateien. Kein Layout-/Ground-Truth-Fit.
- Ergebnis aktiviert **false**: keine TF-/Hardware-/Simulationsprofile geändert.
  Versionierte Kopie unter setup/calibration/hardware_handeye/
  right_rear_20261111/result_v1/{intrinsics.json,handeye_result.json,manifest.json,
  validation.png}. Manifest enthält SHA256 der Ursprungsdateien; ursprüngliche
 9 Aufnahmen unverändert erhalten. Rohdatensatz bleibt right_rear_20261110/.
- Abschlussprüfung: Rear-Zielabweichung0,0000343rad; Front-Abweichung gegenüber
  neuem Start0,0000472rad (Endvergleich, kein Maximum über die gesamte Reihe).
  Rear-scaled-JTC hält letzte Aufnahmepose aktiv, alle Front-Bewegungscontroller
  inaktiv. Beide URs NORMAL/PLAYING, Front Local und Rear Remote. Keine Befehle
  an andere Arme, keine Rückfahrt. Nur eigene Domain68-Vorschau sauber beendet;
  UWA-Arms-GUI und rechte Treiber bleiben offen. completion_state.json gesichert.
- Grenzen: stationäre HTTP-Bilder ohne Belichtungszeitstempel; Bildrand nicht
  validiert (beobachtete Ecken etwa x140…431/y123…341). Ergebnis gilt für
  den verwendeten Modus, Fokus und unveränderte Kameramontage. Noch keine
  Einmessung der Frontkamera, Tisch-/Basisrelation oder statischen OAK.
- Nächster fachlicher Schritt: Profil ausdrücklich/gezielt in ein separates
  kalibriertes Anzeigemodell übernehmen und an zusätzlichen, unabhängigen
  Prüfposen bzw. Messreferenzen prüfen; danach zweiter Arm gegen dasselbe
  feste Board. Keine weiteren realen Ziele aus diesem Abschluss ableiten.

### Historische Anlaufdiagnose der Wiederaufnahme

- **Aktueller Stand15:35Perth:** Front unter derselben IP wieder erreichbar,
  beide rechten echten Gelenkstände gelesen; Front-Parkpose annähernd erhalten.
  Rear PLAYING/native External Control true, beide NORMAL, Bewegungscontroller
  vor Aufnahme inaktiv. Alle32 ausstehenden Ziele unverändert zur freigegebenen
  Originalfolge, Wege aus aktuellen Winkeln neu berechnet und vollständig
  geprüft (`--check-only` erfolgreich). Nur erster Verbindungsweg geändert,
  Dauer2,54s; Gesamtbewegungszeit256,8s. Neue Vorschau Domain68 geöffnet.
  Resume-Fingerprint627571fd735af233510cdbc364a8d990fa46fdee6c874a3f5996af5889429f2b,
  Artefakte right_rear_20261111/resume_plan/, Nutzerkontext operator_context.json.
  Freigegebene Fortsetzung läuft ausschließlich Rear, Log
  setup/logs/uwa-handeye-resume-run.log. Noch keine Ergebnisse behaupten;
  ursprüngliche9 Bilder und Fit-/Prüfrollen erhalten. Keine anderen Armkommandos.

- Nutzer hat die Sicherheitsebenen nach eigener Aussage angepasst und die
  Fortsetzung beauftragt. Die gestrige Pause ist aufgehoben; die neue
  Ebenenposition ist noch nicht unabhängig vermessen/importiert.
- Aktuelle Erstprüfung: right_rear erreichbar, NORMAL/Remote, aber POWER_OFF
  und ros.urp STOPPED. right_front Dashboard nicht erreichbar. Nach Neustart
  keine bisherigen UWA-Prozesse vorhanden; UWA Arms gezielt mit beiden rechten
  Treibern geöffnet, sämtliche gestarteten Rear-Bewegungscontroller inaktiv.
  Rear liefert bei POWER_OFF sechs Nullwerte; diese ausdrücklich **nicht** als
  gültige reale Startstellung verwenden. Front bisher ohne Live-Zustände.
- Nutzer bestätigt Vorbereitung, unveränderte Board-/Kameramontage/linke
  Home-Stellungen und freien Fahrraum. Reale Nachprüfung: GUI-Prepare hinten
  rechts erfolgreich, echte plausible Encoderstände wieder verfügbar,
  RUNNING/NORMAL/Remote; Programm zunächst weiterhin STOPPED/kein natives
  Linkflag. Front-Prepare fehlgeschlagen: kein Ethernet-Nachbar, kein Ping/
  Dashboard/RTDE unter192.168.8.103. Nutzer um Front-Einschalten/IP-Prüfung
  (alternativ aktuelle Pendantwinkel) und Rear-Play gebeten. Keine eigenen
  Power-/Brake-/Play-Aktionen oder Bewegung; kein neuer ausführbarer Restplan
  ohne aktuelle Frontstellung. Diagnose uwa-handeye-resume-after-prepare.json.
- Spätere Prüfung13:33Perth: Rear RUNNING/NORMAL/Remote, ros.urp PLAYING,
  natives robot_program_running=true und54001/54003/54004 tatsächlich verbunden.
  Stationäre Diagnoseaufnahme unter right_rear_20261111/readiness/:
 24 Ecken, drei unterschiedliche Bildpayloads, Fokus404/Manual erhalten.
  Diese Aufnahme ist separat und zählt nicht als neue Haupt-Messansicht.
  Front laut Nutzer eingeschaltet, meldet am Pendant wiederholt kein Netzwerk.
  Rein lesende Dashboard-Suche im192.168.8.0/24 fand nur Rear; keine geänderte
  Front-IP nachgewiesen. Nutzer um sechs aktuelle Front-Pendantwinkel in Grad
  oder die aktuelle Pendant-IP gebeten. Danach Front als manuell gemessenes
  festes Hindernis möglich; keine Bewegung/Power-/Programmaktion für Front nötig.
  Diagnose uwa-handeye-network-dashboard-discovery.json, Aufnahmeprüfung
  uwa-handeye-resume-readiness-capture.log.
- Kamera wieder erreichbar640×480; nach Neustart zunächst Autofokus/Autoexposure.
  Vorherige Einstellungen gesichert und Fokus404/Manual,60000µs/Manual,Gain16,
  LED53 wieder gesetzt. ForceRefresh meldete zunächst LED-Modus1 statt
  angefragtem2. Nach Rear-Vorbereitung Modus2/53 erneut gesetzt und über drei
  HTTP-Bilder stabil zurückgelesen, Fokus404 unverändert; noch kein Nachweis
  physischer LED-Leistung. Livebild24/24 Ecken. Daten unter
  setup/calibration/hardware_handeye/right_rear_20261111/; Diagnose
  setup/logs/uwa-handeye-resume-{status,live}.json.
- `handeye_hardware resume-series` ergänzt: vorhandene akzeptierte Aufnahmen
  als zusammenhängendes Präfix verifizieren, IDs und Fit-/Prüfrollen erhalten,
  verbleibende Ziele mit neuen MoveIt-geprüften Wegen ab aktuellem Zustand
  planen. Originalbatch/Rohbilder unverändert, Hashbindung vorhandener Bilder/
  Records und Prüfung identischer Werkskinematik. Keine blinde Wiederholung
  des unterbrochenen Segments. Noch kein realer Fortsetzungsplan erzeugt.
-13 gezielte Offline-/MoveIt-/Aufnahme-/Intrinsics-Tests bestanden; Log
  setup/logs/uwa-handeye-resume-tests.log. Fit prüft zusätzlich die vorhandenen
  Profil-Gütegrenzen einschließlich Transformationsplausibilität;
  keine automatische Aktivierung. Bisher9 Aufnahmen,32 fehlen (25 Fit/7 Prüfung),
  kein fertiges Intrinsics-/Hand-Auge-Ergebnis.

## Historischer Pausenstand: reale Hand-Auge-Reihe, 2026-11-10

- **Damals auf Nutzerwunsch pausiert; am2026-11-11 aufgehoben.** Bestätigte Ursache des Stopps:
  eine konfigurierte Sicherheitsebene in der UR-Steuerung. Nutzer kann sie
  aktuell nicht deaktivieren und möchte sie morgen,2026-11-11, verschieben.
  Heute keine weiteren Hardwarefahrten/automatischen Wiederanläufe. Keine
  Sicherheitsparameter durch den Agenten geändert oder Stopps quittiert.
- Reale erste Aufnahmesicht hinten rechts erreicht und anhand echter Bilder
  bestätigt: nach freiem Sichtfeld24/24 ChArUco-Ecken. Nicht als exakt angefahrene
  Nominalpose ausgeben: erste Annäherung wurde bei0,0331rad Restabweichung beendet.
  Aufnahmen verwenden die tatsächliche gemessene Stellung und Werkskinematik.
- Nutzer bestätigt rechtes A3-Board1:1 und100mm Kontrollstreifen, Position etwa
  wie Modell. Keine bekannte Wrist-Intrinsics-Kalibrierung. Eigene ChArUco-
  Intrinsics vor Hand-Auge vorbereitet; URCap-Full-Calibration erklärt, nicht
  gestartet. Nominelles K/optische Montage nur für Planung, nicht für den Fit.
- Individuelle Werkskinematiken beider rechter URs rein lesend extrahiert und
  im Hardwareinventar referenziert: setup/calibration/hardware_first_view/
  ur_kinematics/{right_front,right_rear}.yaml. Kein Treiberneustart dafür.
- Nach gesonderter RViz-/Fahrraumfreigabe40 weitere Ansichten geplant und
  begonnen (native skalierte JTC,0,05rad/s,0,10rad/s²). Bei Bewegung zum Bild
  **sample_009** nativer PROTECTIVE_STOP/C400A0; Verbindungsverlust sofort
  erkannt, Action gecancelt, Rear-Bewegungscontroller deaktiviert. UR ordnet
  [C400 der Ellbogennähe zu Sicherheitsebenen zu](https://www.universal-robots.com/manuals/EN/HTML/SW10_8/Content/prod-err-codes/topics/CODE_400.html).
  Die konfigurierte Ebene war nicht Teil der bisherigen FCL-Kollisionsszene.
- **Datensatz:** setup/calibration/hardware_handeye/right_rear_20261110/.
  records/sample_000.json bis sample_008.json samt Roh-/annotiertenJPEGs:
  **9 akzeptierte Aufnahmen**, alle24 Ecken;8 Fit,1 Validierung. Kamerafokus404
  manuell,640×480, Belichtung60000µs manuell, Gain16, LED53Manual. Wechselnde
  Payloads bei Stillstand belegt, kein Sensor-Belichtungszeitstempel vorhanden.
  Keine ausreichende Datenzahl für validierte Intrinsics/Hand-Auge; nichts
  als kalibriertes Hardware-/TF-Profil aktiviert.
- Batch samt Betreiberfreigabe unter batch_plan/, Fingerprint
  80efa418b687052cf63d3010c608c3b4a91b16cdf5f07e630b30d60b8b3f8773.
  Aktueller Pausenzustand in paused_state.json; Diagnose
  setup/logs/uwa-handeye-hardware-{run.log,interruption-status.json}.
  Im zuletzt gelesenen Zustand UR NORMAL, ProgrammSTOPPED, Local stattRemote;
  nicht selbst wieder auf Remote/Play setzen. Front-Parkpose erhalten, linke
  Arme weiterhin nur nominell Nutzer-Home, keine Befehle an andere Arme.
- Software: handeye_hardware plan-view/capture/plan-series/run-series/fit;
  getrennt vom unveränderten Simulationsbackend.31 gezielte Tests bestanden,
  tatsächlicher ros2-run-Prozessgruppen-SIGINT im Mock prüft Cancel/Deaktivieren
  mit0rad Nachdrift. Erststart-Shell- und rclpy-Signalfehler wurden korrigiert.
  [Bedienung/Prüfpfade](docs/hardware_handeye.md).

**Historische Vorbereitung vor der inzwischen abgeschlossenen Fortsetzung:** aktuelle echte rechte
Stellungen und Kamera-/Boardzustand lesen, native Sicherheitsebene mit neuer
Position berücksichtigen, verbleibende Wege neu prüfen/visualisieren. Keine
alten Startstellungen oder alte Freigabe als blind gültig übernehmen. Bestehende
Bilder nicht überschreiben. Der aktuelle Batch-Runner verweigert absichtlich
einen Neustart bei bestehenden sample_001…-Dateien; für Fortsetzung neue Sitzung
oder eine explizit geprüfte Wiederaufnahme ergänzen. Alte Bilder lassen sich
für Hand-Auge nur bei unveränderter Board-/Tisch- und Kameramontage zusammenführen;
für Intrinsics muss zumindest das Optik-/Bildmodusprofil identisch bleiben.
Danach genügend Fit-/Validierungsansichten aufnehmen, Intrinsics und erst dann
Hand-Auge auswerten. Kein automatischer Profilwechsel oder Rückweg.

## Hardware-Wartepose vor Kamerakalibrierung, 2026-11-10

- Nutzer bestätigt erfolgreiches reales Jogging hinten rechts. Neuer Auftrag:
  allgemeines Parkskript, zunächst vorne rechts real testen. Linke Arme laut
  Nutzer bereits aufrecht in Default Home; nominell [0,-90,0,-90,0,0]° als
  user_nominal_home dokumentiert, keine gemessenen Encoderstände behaupten.
- Neues park_arm plan/preview/execute in uwa_cell_control. Zentraler Zelllayout-
  und Hardwareinventarbezug, bestehende vollständige MoveIt-Kollisionsszene,
  lokale quintische Wege mit maximal0,005rad Sampleabstand; keine OMPL-Umweg-
  Planung. Fehlende Zustände machen einen Plan zur nicht ausführbaren Vorschau.
  Vorschau getrennt in Domain68, echte Hardware66/Mock67/Gazebo64 unverändert.
  [Bedienung](docs/hardware_parking.md).
- Ausführung als generische MATCH-Funktion trajectory.execute_trajectory über
  nativen skalierten Hardware-JTC bzw. Mock-JTC. Genau ein Arm, keine Power/
  Brake/Play-/SSH-Kommandos oder automatische Rückfahrt. Aktuelle Startstände,
  Modell/Inventar und vollständigen Pfad vor Fahrt erneut prüfen. Andere rechte
  Live-Arme auf Poseänderung überwachen; Telemetrieverlust cancelt/deaktiviert.
- Vorne rechts alte ROS-Instanz41381 zeigte sechs Nullwinkel trotz RUNNING und
  aufgebauter Reverse-Verbindung. Unabhängiger Ausgabe-only-RTDE-Client lieferte
  plausible actual_q. Nur alten Front-Launch41338 nach Prüfung inaktiver Bewegung
  ersetzt; beide rechten Treiber in neuer GUI inaktiv gestartet. ROS-Winkel
  danach mit RTDE konsistent;53002/54002 lauschen, Programme zuletzt PLAYING.
  Keine Power-/Brake-/Play-Befehle durch den Agenten. Diagnose im Workspace
  setup/logs/uwa-parking-{front,rear}-rtde.json und uwa-parking-ready-*.json.
- Zwei Pakete gebaut und23 gezielte Offline-/MoveIt-/GUI-/Adaptertests bestanden.
  Vollständiger Mock-Parkweg etwa38,35s, Endfehler1,1e−16rad, andere simulierte
  Zustände unverändert. Ausfall einer stationären Mock-Zustandsquelle während
  tatsächlicher Fahrt cancelt/deaktiviert; Nachdrift0rad. Logs
  setup/logs/uwa-parking-{build,tests,live}.*. Bestehende Kalibrierung unverändert
  Simulation-only; keine zusätzliche automatische Hardwarekalibrierung aktiviert.
- Konkreter echter Front-Plan: setup/calibration/parking/right_front_hardware/
  plan.json; Fingerprint7044e86ce9029d3805047324fc87fceefd4d06e13ecd180e318e6b437d323bc6.
  tool0 Ziel ungefähr [0,8504,-0,6741,1,5500]m,620 geprüfte Zwischenstände,
  Dauer61,81s, Limits0,05rad/s und0,10rad/s². Rechte Startwerte live gemessen,
  linke nominell Home. Abschließender --check-only erfolgreich. PNG geprüft;
  eigene RViz-Animation auf Domain68 geöffnet. Fremdes Fenster-Screenshot ergab
  schwarz; deshalb keine erfolgreiche vollständige Screenshot-Sichtprüfung
  behaupten. Nutzer hat die konkrete Vorschau selbst geprüft und **„Vorschau
  passt, Fahrbereich frei – Parkversuch starten“** freigegeben; Freigabe mit
  Fingerprint lokal in operator_approval.json. Erster Realversuch nach16,5s mit
  nativer Pfadtoleranzverletzung0,200rad abgebrochen, Controller wieder inaktiv.
  Beobachtete Frontänderung nur0,000125rad, hinten0,000101rad (Messrauschen).
  Diagnose: DashboardPLAYING ist kein Nachweis einer Reverse-Verbindung;
  aktuell kein53001/53003/53004-Socket und kein robot_program_running-Sample.
  GPIO publiziert nur Zustandsänderungen; fehlendes Sample ist kein gemessener
  false-Wert. Nutzer um Stop→Play vorne rechts gebeten, Freigabe für denselben
  gespeicherten Weg gilt fort. Keine Toleranzgrenzen gelockert. Logs
  uwa-parking-hardware-execute.log, uwa-parking-hardware-motion.json und
  uwa-parking-front-external-control.json.
- **Folgeversuch erfolgreich:** Nutzer Stop→Play ausgeführt, alle drei53001/
  53003/53004-Verbindungen bestätigt und natives Programmflagtrue. Gemeldeter
  Displayfehler „Trajectory socket53003 connected:false“ war bei Prüfung nicht
  mehr aktuell;53003 war verbunden. Genau derselbe freigegebene Plan ausgeführt,
  native skalierte JTC-Action SUCCEEDED/0. Maximaler Endfehler0,0000356rad,
  unabhängige spätere Lesung0,0000291rad. Hinterer rechter Arm maximal0,000101rad
  Änderung im Beobachtungsfenster, linke nicht kommandiert/ohne Live-Telemetrie.
  Ergebnis in setup/calibration/parking/right_front_hardware/execution_result.json;
  Logs uwa-parking-hardware-attempt2.log und uwa-parking-hardware-motion2.json.
  Abschließend Front-JTC hält Ziel, Rear-Bewegungscontroller inaktiv, Hardware-
  GUI/Treiber erhalten; eigene RViz-Vorschau sauber beendet. Kein Rückweg oder
  automatischer Hardware-Kalibrierlauf. Gelegentliche500Hz-Overruns und nicht
  fatale Typesupport-/MoveIt-Loggingwarnungen bleiben als technische Folgefrage.

## Ethernet und manuelles Jogging, 2026-11-10

- Nutzer hat Kabel ersetzt; Roboterrouten geprüft über enp87s0, PC192.168.8.209.
  Aktive Hinweise/Inventar zur temporären Funkverbindung entfernt. Historische
  Messungen und deren Transportbezug bleiben als überholt gekennzeichnet.
- Gewünscht: zuerst right_rear manuell mit dem MuR-Jogging und demselben
  dezentralen IntegratedCartesianAdmittanceController/J-PARSE bewegen; zunächst
  Nachgiebigkeit AUS. Keine automatischen Testfahrten durch Öffnen des Dialogs.
- Gemeinsame Qt-unabhängige MuR-Richtungsberechnung, UWA-Dialog ohne Lift/SSH,
  Base-Frame, Translation/Rotation, 20Hz while held, Loslassen/Space/Fokusverlust
  stoppt. Idle-Fenster senden keinen dauernden Nullstrom an andere Befehlgeber.
- Standard admittance/wrench_twist_gain sechs Nullen, use_ft_sensor=false und
  require_wrench=false. Controller liest Gains in on_init: ausdrückliches
  Aktivieren erstellt ihn zunächst inaktiv neu und lädt danach denselben Plugin-
  Typ. Ein dynamischer Parameterwert allein wäre dafür nicht ausreichend.
- Kollisionsalgorithmen und MuR-Standardprofil erhalten; UWA-Kollisionsoption
  weiterhin nicht als vollständiger Zellenschutz konfiguriert.
- Hardware bleibt Domain66, Mock jetzt strikt Domain67 in GUI, Kindprozessen,
  Launch und Jog-Transport; dadurch keine echte Managerentdeckung im Mockmodus
  und keine Fake-JointStates im lesenden RViz-Twin. Testnamespaces zusätzlich
  separat. Bedienung: [Jogging](docs/ur_jogging.md).
- Drei Pakete gebaut,19 gezielte Adapter-/UWA-Tests und acht MuR-Kartesiktests
  bestanden. Live-Mock in Domain67: Öffnen ohne Twist; beim Halt maximal0,028rad
  Gelenkänderung, nach Loslassen0,0rad weitere Drift im Messfenster. Rotation,
  Fokusverlust-Stopp und effektive Null-Gains/FT aus bestätigt.
  Logs setup/logs/uwa-jog-{build,unit,live,mur-cartesian}.*; Screenshot
  uwa-jog-dialog.png. Breiterer MuR-Test enthält eine bereits im HEAD vorhandene
  MiR-Fixture-Störung (QMainWindow ohne modules), kein Kartesik-Regressionsbefund.
- Hinten rechts alten nicht antwortenden Manager gezielt ersetzt, nach
  Dashboard STOPPED und fehlender Reverse-Verbindung; vorne rechts unverändert.
  Reales Preset lesend bestätigt: sechs Null-Gains für beide Parameter,
  use_ft_sensor/require_wrench=false. Broadcaster aktiv, Bewegung inaktiv,
  UR RUNNING/NORMAL/Remote, geladenes ros.urp STOPPED. Belege
  setup/logs/uwa-jog-hardware-{preset,after-restart}.json.
- Nutzer meldet URCap-Port50002 bei korrekter PC-IP; benötigt wird54002 für
  right_rear. Aktuelle native Prüfung: Route enp87s0/src192.168.8.209,
  drei Pings ohne Verlust0,317–0,344ms, Dashboard erreichbar; Treiber lauscht
  auf54002, kein Server auf50002. Ursache der genauen UR-Meldung nach
  Portkorrektur erneut prüfen. Keine realen Power-/Brake-/Play-/Fahrbefehle
  durch den Agenten; erster physischer Hold-to-jog-Versuch noch offen.
- Abschließender realer JointState-Lesetest liefert alle sechs endlichen
  right_rear-Gelenkwinkel, trotz STOPPED-Programm:
  setup/logs/uwa-jog-hardware-joints.json. Die früheren fehlgeschlagenen
  Empfangstests sind damit für diesen Arm überholt.
- Vollständiger Vierarm-Mock-GUI-Regressionslauf in Domain67 bestanden:
  24 eindeutige Gelenke, Ein-/Zwei-/Vierarm-Wechsel, Kartesik-Neuladen,
  Save logs, STOP, gezielter Managerexit/Neustart und eigener Abbau.
  setup/logs/uwa-jog-full-gui.log und uwa-control/mock-gui-validation.json.
  Installierte Desktop-Aktion RightRearJog via Gio geöffnet und sichtbares
  Haupt-/Jog-Fenster per X11-Fensterinventar bestätigt. Bestehende
  Hardware-Besitzerfenster erhalten; keine reale Controlleraktivierung.

## Englische UR-GUI und Sitzungsdiagnose, 2026-11-10

- Neuer Nutzerhinweis: schwacher Monitorkontrast; Klickannahme deutlich
  rückmelden. GUI mit kontrastreichem Button-Highlight (1,2s), großer dauerhafter
  RECEIVED/RUNNING/DONE/FAILED-Anzeige, Aktionsname/Detail und Laufzeit umgesetzt.
  Hintergrund-Statuspolls überschreiben manuelle Fehler nicht; Klicks/Ergebnisse
  zusätzlich im Sitzungslog und aktueller Feedbackzustand im Exportmanifest.
- Nutzerexport14:35:45 ausgewertet: Dashboard erreichbar/NORMAL/Remote, aber
  Manager hinten rechts seit13:59:00 mit−11 abgestürzt; State-Helper ebenfalls−11.
  Verwaister Launch41339 blockierte neue Starts. Nur diesen Rest beendet;
  künftige Manager-Exits räumen zugehörigen Launch samt Sperre automatisch auf.
  Nativer Segfault selbst noch ungeklärt, keine bewiesene WLAN-Ursache.
  [Diagnose](docs/ur_log_diagnosis_2026-11-10.md).
- Abschluss:17 Offline-Tests, Zwei-Paket-Build und isolierter Live-Mock-Test
  inklusive gezieltem Manager-Exit, Bereinigung nur dieser Instanz und anschließendem
  erfolgreichem Armneustart bestanden. Fehlerhafter alter GUI-Status nach
  Treiberexit wird verworfen. Logs setup/logs/uwa-feedback-{tests,build,live}.log.
  Kontrastreiche Darstellung anhand zweier Screenshots geprüft; aktuelle GUI
  über Desktop-Aktion geöffnet, ohne lebende Hardwaretreiber zu unterbrechen.
- Nutzerauftrag: aktuelle UR-GUI ins Englische übersetzen und Save logs für
  die aktuelle Sitzung ergänzen. Eigene Beschriftungen/Tooltips/Meldungen,
  eigene MATCH-Adapterantworten und Startmenü UWA Arms übersetzt. Native oder
  alte gespeicherte Logs werden unverändert erhalten.
- Eindeutige Sitzungsverzeichnisse unter setup/logs/uwa-control/sessions/.
  Vollständiges GUI-Log und gesonderte Prozessdateien inklusive Statusausgaben,
  Exitcodes; sichtbarer Logpuffer darf weiterhin gekürzt sein.
- Save logs als dauerhaft erreichbarer Button; Export im Hintergrund als
  tar.gz nach setup/logs/uwa-control/exports/. Neuester erfolgreicher Pfad in
  latest-export.txt daneben. Manifest: Zeitpunkte, Modus, Auswahl, letzte
  Statusdaten, PIDs, whitelisted Profilwerte, Dateiliste/Warnungen und Screenshot.
  Kein automatischer Roboterbefehl/Upload, kein vollständiger Environment-Dump.
- Passende seit Sitzungsbeginn geschriebene ROS-Dateien und ältere, noch von
  angehängten Treiberprozessen verwendete ROS-Logs erfassen. Altes gemeinsames
  gui.log explizit als inherited_context, damit Diagnose früherer Treiberstarts
  möglich bleibt. Wiederholte Exporte überschreiben keine vorherigen Archive.
- Offline-Prüfung:16 Tests bestanden, darunter archivierte Fehlerausgaben,
  getrennte Sitzungen, ROS-Auswahl, keine externen Symlink-Dateien und echter
  GUI-Button-Export während einer als laufend markierten Operation.
  Logs setup/logs/uwa-english-log-{tests,build,live}.log; Details Bedienungsdatei.
- Beide Pakete gebaut, isolierter Live-Mock-Test inklusive Save logs bei vier
  aktiven Mock-Controllern bestanden. Archiv enthält Prozessdateien, ROS-Dateien,
  Status-Snapshot und vier Treiber-PIDs; anschließend Controllerstopp und
  sauberer Abbau bestätigt. Beispielarchiv im JSON-Bericht
  setup/logs/uwa-control/mock-gui-validation.json verzeichnet.
- Englischen Desktop-Eintrag installiert/validiert und dessen Hardware-Aktion
  geöffnet. Nur treiberloses Vorgängerfenster ersetzt; Besitzerfenster und beide
  Hardware-Launch-Prozesse41338/41339 erhalten. Neue GUI UWA · Direct UR Test,
  Hardwaremodus/rear right; keine realen Power-/Brake-/Play-/Bewegungsbefehle.

## Aufbau der realen Zelle und Modellannahmen

### Parallele Simulation und gemessene Modelle in RViz, 2026-11-10

- Nutzerziel: beide echten rechten URs zusätzlich zu vier simulierten Armen
  gleichzeitig darstellen. Paket `uwa_cell_visualization`, bestehende cell.rviz
  erweitert: Simulation teilweise transparent, right_front gold, right_rear cyan.
- Ausschließlich zwei JointState-Abos auf Domain66, separate real_-Gelenke/TFs
  und RobotDescriptions auf Domain64. Keine Steuer-Topics/Services/Actions
  überbrückt und keine simulierten Zustände verändert. Eigenständige ROS-Contexts,
  Anzeigezeit an Simulationsuhr angepasst; Originalhardwaredaten unverändert.
- Modelle erst bei sechs vollständigen endlichen Positionen zeigen; WAITING/
  LIVE/STALE-Marker, nach2s ohne Daten Modell ausblenden. Walltime-Timeout gilt
  auch bei pausierter Simulation. LIVE bezeichnet ROS-Empfang, keinen unabhängig
  nachgewiesenen frischen RTDE-Sensorzeitpunkt.
- Montage aus zentralem Zelllayout (base_link relativ Tisch) bleibt vorläufig.
  Individuelle Werkskinematik aus Hardwareinventar optional, aktuell nominell.
  Reale Anzeige hat sechs UR-Gelenke ohne erfundene Greifer-/Kamerazustände.
  Offizielle STL-Schalen farbig dargestellt, keine neue Kollisionsprüfung.
- `cell.sh rviz`/Desktop-App starten `uwa-cell-hardware-overlay` idempotent mit.
  `cell.sh twin` separat; direktes cell.launch rviz:=true enthält optionales
  Overlay. Zell-Stopp beendet nur Visualisierung/Simulation, keine Hardwaretreiber.
- **Beide echten Datenströme LIVE** nachgewiesen. Vorne rechts war Controllerliste
  leer; ausschließlich joint_state_broadcaster geladen/aktiviert. Keine Power-/
  Brake-/Play-/Bewegungscontroller-/Zielbefehle. Hardwaretreiber weiterverwendet.
- Tatsächliche Abnahme: je6 endliche echte Gelenkwinkel, parallel48 simulierte
  Gelenke inkl. Tools, beide real_base_link-/tool0-TFs zur Welt vorhanden.
  `setup/logs/uwa-twin-real-acceptance.json`, Status `uwa-twin-live-status.json`.
- Vier Offline-Tests und isolierte Domain174/175-Prüfung: Modelle/TFs/Werte,
  keine künstliche Initialpose, keine Kommandopublisher, TF-Änderung bei pausierter
  Sim-Uhr, Stale-Ausblendung und unabhängige Wiederkehr beider Arme bestanden.
  Logs `setup/logs/uwa-twin-*`, visueller Screenshot `uwa-twin-rviz.png`.
  Anleitung [RViz-Vergleichsansicht](docs/rviz_digital_twin.md).
- Gemeinsame Visualisierungs-/Gazebo-Suite:61 Tests bestanden. Abschließender
  Dienststatus aktiv für Simulation/RViz/Scan/Overlay, beide Datenströme LIVE;
  `setup/logs/uwa-twin-live-status-final.txt`. RViz-Fenster vergrößert und Marker
  ohne überbreite Ogre-Leerzeichen für bessere Lesbarkeit gesetzt.

### Lokale UR-Vorbereitung und direkte UWA-GUI, 2026-11-10

- Nutzerwunsch: gemeinsame Start-/Bereitstellungs-/Admittanz-/Kollisionsbausteine
  in MATCH belassen; einfache UWA-Oberfläche mit vier Armauswahlen oben links,
  ohne SSH/rsync/mobile Infrastruktur. Adapter `match_ur_hardware`, Client
  `uwa_cell_control`; bestehende MuR-Algorithmen und Launch-Defaults erhalten.
- **Neueste Nutzerkorrektur:** zusätzliche UWA-Sicherheitsgates entfernen, um
  Bremsenlösen, Gelenkwinkel und Controllerwechsel auch per WLAN direkt zu testen.
  Damit sind frühere pauschale bzw. Ein-/Zweiarm-Sperren ausdrücklich überholt.
  Entfernt: Armzahl-/Aktivarmzählung/-lock, Dashboard-NORMAL/Remote/RUNNING/
  PLAYING-Vorprüfungen, exakter Programmpfadvergleich, Inaktivpflicht vor
  Bereitstellung, GUI-Treiberbesitzpflicht und rqt-Statusfreigabe.
- Native UR-Sicherheitsfunktionen, Treiber-Controller-Stopper, bestehende
  Kollisionsalgorithmen/Reglergrenzen nicht verändert. Technische Profil-/Port-
  Validierung und doppelte-Treiber-Schutz bleiben. Keine transportspezifischen Sperren.
  Dashboard-/Treiberablehnungen werden angezeigt; keine automatischen
  Schutzstoppquittierungen, kein automatisches Power/Brake/Play beim Launch.
- Standard nur `right_rear`; App UWA Arme, neues Fenster **UWA · Direkter UR-Test**.
  Domain66/localhost; Gazebo64/OAK65 unverändert. Hardwareinventar separat,
  links weiterhin keine IPs. Eigene Werkskinematik noch nicht hinterlegt.
- Prepare verwendet vorhandenen UR-SetMode-Helfer, ohne Programmstart. Separates
  Play startet aktuell geladenes UR-Programm; `external_control_program` nur
  noch informativ. Native reale Trajektorien mit skaliertem UR-Controller.
- **Gelenkwinkel lesen** empfängt JointState ohne Programm-/Dashboardprüfung,
  Anzeige rad/Grad. **Broadcaster / Controller laden** holt fehlgeschlagene
  Spawner nach, Broadcaster aktiv/Motion inaktiv. Beim Schließen kein zusätzlicher
  Dashboard-Stopp mehr; eigene Prozesse werden beendet. Neues Fenster kann
  fremd gestartete Treiber bedienen, beendet deren Prozesse aber nicht.
- Hardwarediagnose: Log zeigt beide Spawner13:48/13:49 fehlgeschlagen, später
  Verbindungsabbrüche/Reconnects30001/30004. Lesender8-s-Test ohne JointState;
  echte Winkelübertragung noch nicht nachgewiesen. Native UR-read()-Logik liest
  RTDE actual_q unabhängig vom laufenden External-Control-Programm.
- 14 Offline-Tests und Zwei-Paket-Build bestanden, Live-Mock-Test getrennt unter
  /uwa_mock_validation: direkte Ein-/Zwei-/Vierarm-Aktivierung ohne Dashboard,
  JointState-Leser, vier Admittanzcontroller und GUI-Stopp/Prozessabbau bestanden.
  Logs setup/logs/uwa-direct-{tests,build,live}.log und finaler JSON-Bericht unter
  setup/logs/uwa-control/. Frühere gate-spezifische Tests sind historisch.
- Neues direktes Hardware-GUI-Fenster neben altem Besitzerfenster geöffnet,
  dessen laufende reale Treiber nicht gestoppt/neugestartet. Agent hat keine
  realen Power-/Brake-/Play-/Bewegungsbefehle gesendet. Softwarestopp ist kein
  Hardware-Not-Halt. Kollisionsoption in UWA-Profilen bleibt deaktiviert;
  kein vollständiger Zellenschutz. Anleitung [UWA Arme](docs/ur_control_gui.md).

### Historische Netzwerkmessung vor Kabeltausch, 2026-11-10

- **Verbindliche Nutzerzuordnung:** hinten rechts=`right_rear`=192.168.8.170,
  vorne rechts=`right_front`=192.168.8.103. „Erster/zweiter“ sind zufällige
  Bezeichnungen, keine dauerhaften Arm-IDs. Separates Inventar in
  `config/hardware_inventory.yaml`; keine Hardware-IP in den Simulationslaunch.
- OAK4-D R9 weiterhin192.168.8.238, ID1479883285. PC wegen defektem langem
  LAN-Kabel vorübergehend per WLAN, Geräte weiter kabelgebunden am Router.
  Beobachtet PC192.168.8.209/24 aufwlp88s0f0, alle Zielrouten WLAN;
  enp87s0 DOWN. Alte LAN-Leistungswerte nicht als WLAN-Werte verwenden.
- **Alle drei Geräte erreicht.** UR-Dashboard-Leseabfragen erfolgreich:
  ModellfamilieUR5, Software5.10.1.106310, Seriennummern hinten20195501620 /
  vorne20195501617. Beide zum TestPOWER_OFF, StatusNORMAL, ProgrammSTOPPED,
  RemoteControl=false; nichts davon verändert. Keine Robotertreiber/Bewegung.
- Je40 Pings:0% Verlust; RTT-Mittel hinten6,87ms, vorne5,02ms, OAK6,52ms.
  Maxima30,92 /45,82 /14,52ms: sichtbarer Jitter, keine Echtzeitgarantie.
- OAK-Agentinfos erfolgreich; kurzer SDK-Stream640×480NV12@5fps lieferte
  gemessen4,997fps über10,21s, etwa18,9Mbit/s Bildnutzdaten. Danach geschlossen.
  Kein Maximalbandbreitentest, keine Wiederholung der LAN-Extremprofile.
  Hardware-OAK- und Simulations-Livedienste waren vor Test bereits inaktiv.
- [Prüfbericht](docs/hardware_network_2026-11-10.md); lokale Rohdaten unter
  `setup/logs/hardware-wifi-2026-11-10/`. WLAN-Bildprofile zunächst klein halten,
  Kalibrieraufnahmen bei Stillstand; spätere Rückverbindungen benötigen die
  aktuelle PC-IP. Keine URCap-/Netzwerk-/Firmwareänderung ausgeführt.

### Erster realer Wrist-/Hand-Auge-Test, 2026-11-10

- Neuer Nutzerwunsch: zunächst ausschließlich hinten rechts (`right_rear`,
  192.168.8.170) reale Tests vorbereiten, insbesondere Kamerabildzugriff klären.
- [Konkretes Vorgehen](docs/right_rear_hardware_first_test.md): Robotiq dokumentiert
  HTTP4242`/current.jpg?type=color` am UR-Controller für das letzte Kamerabild.
  Bildfrische, tatsächlichen Bildmodus/Intrinsics und Fokus separat prüfen.
- Lesender Versuch: HTTP`No route to host`, Dashboard29999Timeout. PC weiterhin
  192.168.8.209 aufWLANwlp88s0f0, Route vorhanden. Kein Bild/Zustand bestätigt,
  Ursache offen. Lokaler Bericht`setup/logs/right-rear-wrist-2026-11-10/report.json`.
  Keine Treiberstarts, Bewegung oder Power-/Brake-/Programm-/Kameraänderungen.
- Empfehlung, noch keine Umsetzung: zunächst am Pendant manuell angefahrene
  Stellungen, hardwareseitiger Bild-/Pose-Recorder mit gesicherter Bildfrische,
  reale Intrinsics/Werkskinematik und unabhängige Prüfstellungen. Automatischer
  Backend/Stopp derzeit weiterhin Simulation, nicht für echte Arme freigegeben.
- right_rear allein liefert Hand-Auge und Basis-zu-Board; relativer Abstand zum
  right_front erst mit dessen Messreihe am gleichen unbewegten Board. Vorhandene
  parallele Hardware-GUI-Arbeit bleibt erhalten und wurde nicht als fertige
  Kalibrier-Hardwareanbindung ausgegeben.
- Folgefrage Bildqualität am selben Tag: Nutzer meldet falschen Fokus und
  geringe Auflösung. Erneuter lesender HTTP-Abruf jetzt erfolgreich: **640×480**,
  83379Bytes, HTTP200. Frühere Nichterreichbarkeit damit historisch; keine
  Netz-/Kameraänderung durch diesen Agenten. Bild/Report`quality_check.jpg/json`
  unter`setup/logs/right-rear-wrist-2026-11-10/`. Sichtprüfung: Pendant überbelichtet,
  kein Board; genaue Fokusursache/Bildfrische noch nicht nachgewiesen.
- Herstellerdaten2019:2560×1920 bei2fps,640×480 bei bis30fps, Flüssiglinse70mm–∞.
  Sensorfähigkeit von tatsächlich gelieferten HTTP-Pixeln unterscheiden. Fokus
  über Robotiq-Teach-/Configure-Model-Kameraeinstellungen/Retake prüfen;
  HTTP-GET ist kein belegter Autofokus-Trigger. Höhere Auflösung noch nicht
  praktisch erschlossen; Bedienhinweise/Quellen in obiger Anleitung ergänzt.
- Fernfokus-Folgefrage2026-11-10: Nutzer möchte Skript/PC-Schieberegler und
  distanzbasierte Einstellung. Frühere Formulierung „Fokus nur per URCap“ zu
  pauschal: Primärbericht eines Anwenders im Robotiq-Forum beschreibt Fokus via
  OpenCV bei direktem USB; Hersteller unterstützt diese Integration nicht
  offiziell. Keine Prüfung am eigenen Gerät, Beispiel-Link inzwischenHTTP404.
  Für den bestehenden Controllerpfad weiter kein dokumentierter Netzwerksetter
  gefunden; installierten URCap-/Programmskriptpfad künftig lesend untersuchen.
- Physikalischen Zielabstand von elektronischem Stellwert unterscheiden:
  V4L2-Fokuseinheit nicht definiert; Kennlinie oder Board-ROI-Schärfesuche nötig.
  Kein Fokussetter/Schieberegler implementiert, keine Kamera-/Roboteränderungen.
  Für Hand-Auge Fokus und passende Intrinsics konstant halten; Fokusprofile
  wären bei distanzabhängiger Verstellung zusätzlich zu kalibrieren.
- Anschlussfrage zu Skriptdateien/Zugang2026-11-10: `.urp` ist das grafische
  Programm, vorhandener erzeugter URScript-Code als gleichnamige`.script`
  üblicherweise unter`/programs`/Unterordner. Zum Auslesen nicht ausführen.
  SSH zu right_rear erreichbar; Standard-Key-Anmeldung und genau ein Versuch
  mit dokumentiertem Hersteller-Standardkennwort abgewiesen. Keine Dateien
  vom Controller gelesen, keine Programme ausgeführt oder Zustände geändert.
  Für weitere URCap-/Fokusuntersuchung funktionierender SSH-/SFTP-Zugang oder
  lokale Dateikopie nötig. Keine Zugangsdaten in Dokumentation übernommen.
- Nutzer möchte anschließend temporäres Kennwort einrichten. Offiziellen Weg
  abPolyScope5.10 überSettings→Password→Admin erklärt, gültiges bisheriges
  Admin-Kennwort nötig; SSH-Authentifizierungsart separat prüfen. Schlüsselimport
  als Alternative ohne Kennwortweitergabe genannt. Keine Kennwortänderung
  durchgeführt und kein neues Kennwort empfangen/gespeichert.
- Neuester Befund2026-11-10: Nutzer kennt Admin-Kennwort derzeit nicht und stellt
  UCC1.11.3-ZIP bereit. Lokale statische Analyse findet internen HTTP-Kameraclient:
  GET`/getcamerasettings` und`/getcamerasettingsdetails` tatsächlich erfolgreich
  am right_rear, ohne SSH. Server meldet u.a.`focusAuto:true`, Fokus-Suchbereich
  150…1023; gemeldeter`focus:0` im Auto-Modus nicht als Linsenposition ausgeben.
- Originalclient verwendet POST`/setcamerasettings`, JSON`cameraSettings` und
  booleschen Queryparameter`setManualValuesIfModeChanged`; Fokus-Trigger ebenfalls
  rekonstruiert. Pendant-Regler0…1023 mitAPI-Wert=`1023−Reglerwert`.
  **Kein Schreibtest**, keine Kamera-/Roboter-/Installationsänderung. Nachweise
  unter`setup/logs/wrist-urcap-2026-11-10/`, eigener
  [Analysebericht](docs/wrist_urcap_analysis_2026-11-10.md). Früherer Befund
  „kein Netzwerksetter gefunden“ ist durch diese Archivuntersuchung überholt.
- Korrektur SSH-Empfehlung: regulärer Key-Import im geschützten Security-Menü
  benötigt ebenfalls Admin-Kennwort, umgeht es nicht. Für die gefundene
  Kamera-HTTP-Schnittstelle ist SSH momentan nicht nötig. Archivversion nicht
  mit bestätigter installierter URCap-Version gleichsetzen; nichts installiert.
- Folgeauftrag2026-11-10 ausgeführt: Kamera-only-Schreibtest und separates
  englisches Qt-Fenster mit2Hz-HTTP-Vorschau, Regler/Readback, Autofokus, Foto+JSON,
  Restore beim Knopf bzw. standardmäßig normalen Schließen nach eigener Änderung.
  `ros2 run uwa_cell_control wrist_camera_gui`; IP ausHardwareinventar.
- ManuellerAPI-Fokus512 nachgewiesen, sichtbare Schärfeänderung. Ursprünglicher
  Auto-Modus wiederhergestellt und reiner Fokus-Trigger erfolgreich. Autofokus
  wählt dabei neuen numerischen Wert408; kein Meterwert/kein Boardoptimum.
  Erste Prüfbedingung verlangte fälschlich exakt alten Zahlenwert im Auto-Modus;
  korrigiert. Verzögerte Bildpipeline berücksichtigt, späteres Bild wieder scharf.
  Andere Kameraeinstellungen unverändert; keine Roboter-/Treiber-/Adminbefehle.
- Vier lokale HTTP-Tests und Paketbuild bestanden, echte Qt-Knöpfe inkl.
  Speichern/Restore geprüft. Bericht`setup/logs/uwa-wrist-focus-window/report.json`,
  Screenshots/Fotos daneben; GUI zur Bedienung geöffnet. Anleitung
  [Wrist-Fokusfenster](docs/wrist_camera_focus.md). Daten unterWorkspace-setup,
  keine Rohbilder eingecheckt. Sensorbelichtungszeit weiterhin nicht verfügbar.
- Nutzer bestätigt Fokusfunktion und bittet um native Auflösung/Helligkeit.
  Server meldet tatsächlichUCC1.11.1.10337/FirmwareCQ0-1.3.5; `/restapi` enthält
  live API-Beschreibung. Begrenzter Vollauflösungsversuch über Kamera-OperationMode
  und captureimage quittiert, lastCapture-Export ohne Bild/kurzer Dienstausfall,
  automatische Erholung nachNormal. Alternative Aufnahme mit Wartezeit/Quellmap
  bleibt640×480. Keine native höhere Auflösung behauptet; kein Failing-HD-Knopf.
- Kameramoduswechsel setzt Fokus zurück; ursprünglichen Benutzerwert404/Manual
  ausdrücklich wiederhergestellt. Keine Roboterbefehle, keine Treiber-/Simulations-
  oder Firmware-/URCap-Neustarts/Updates. Eigenes altes Kamerafenster zur Erweiterung
  gezielt ersetzt, aktuelle Nutzerwerte erhalten bzw. nach Versuch zurückgestellt.
- Kamerafenster jetzt mit1…66604µs, Gain1…63, EV−7…+7 und LEDAuto/Off/Manual0…100%.
  Belichtungs-/LED-Writes partiell ohne Fokusfelder; Originalwerte sichern/Restore.
  Hardwarewirkung20→40ms/Gain2 nach Einlauf: mittlerer Grauwert39,87→72,93,
  Fokus404/Manual unverändert. LED30% und echte Qt-Knöpfe/Speichern/Restore geprüft.
  Sechs lokale HTTP-Tests und Build bestanden, neues Fenster geöffnet.
  [Details/Bedienung](docs/wrist_resolution_exposure_2026-11-10.md), Nachweise unter
  setup/calibration/wrist_resolution_exposure/20261110 und
  setup/logs/uwa-wrist-appearance-window/. Vollauflösung bleibt offen.
- Nutzer bestätigt Beleuchtung und liefertUCC4.1.0 plusDoF-Thema2227. Archiv nur
  statisch analysiert, nichts installiert oder an Kamera/Robotern geändert.
  NativeHD-Funktionen vorhanden, aber geprüfter captureimage-Client/Handler
  weiterhin ohne frei wählbare HD-/Auflösungsparameter, separater HD-Modulpfad.
  lastCapture liefert nur vorher erzeugten normalen/HD-Puffer. Kein Erfolg oder
  Upgrade-Nutzen für5MP behauptet. [Befund](docs/wrist_ucc4_analysis_2026-11-10.md).
- Verlinkter Workaround: Barcode-Knoten erzeugt5MP, SaveImage speichert, dannFTP.
  Nutzer findet diesen Weg unattraktiv. Alternative als nächster Untersuchungsweg:
  temporärenHD-Modulpfad direkt vomPC/HTTP auslösen und Bild aus Speicher abrufen,
  ohne PolyScope-Programm/SaveImage/FTP; weiterhin modulabhängig, noch ungetestet.
  Andere Optionen Controller-Konfigurationsprüfung mit legitimemSSH oderUSBdirekt;
  vorhandene gut funktionierende LED-/Fokussteuerung dabei berücksichtigen.
- Konkretisierung auf Frage „wie würde ich das machen?“: Kamera-Wizard-Endpunkte
  beginbarcode/create/process sind aus gesicherter API/Client bekannt. Nativer
  Export aus diesem Zustand noch ungeklärt; lastCapture ist nurOperationMode,
  nichtBarcode registriert. Daher keine scheinbar fertige curl-/Python-Sequenz
  ausgeben. Vorschlag bleibt ein zu entwickelndes Testtool mit vollständiger
  Zustandssicherung/-wiederherstellung, kein nachgewiesener5MP-Abruf. Keine
  neuen Hardwareaufrufe; parallele hardware-handeye-first-view-Arbeit erhalten.
- Weiterer statischer HD-Befund: untersuchte rejectmodule-/Normal-clearModules-
  Funktionen löschen Module/Kalibrierungen, keine explizite HD-Pufferlöschung
  erkannt. Kandidat: Barcode-HD→rejectmodule→Normal→OperationMode→lastCapture,
  ohne weitereVGA-Aufnahme. Strategiewechsel können dennoch Zustand/Bilder
  beeinflussen; echter Nachweis fehlt. Nächster Schritt einzelner exklusiver
  Kameratest mit Backup/Statuschecks/Pixeldimensionen/Restore, keine Installation.
  Wegen parallel aktiver ersterHardware-Hand-Auge-Arbeit hier nur lokal analysiert.
- Nutzer gibt danach Kamerazeitfenster frei (anderer Agent plant Bahn). Reale
  HD-Modultests20:16–20:18AWST: beginbarcode/create akzeptiert, process liefert
  49156/barcode process failed. Lizenzstatus true. Präzisierte Nachprüfung liest
  Modulbild/Mapping640×480; kein bestätigterHD-Puffer und kein erneuter nativer
  Export. Das beweist nicht grundsätzlich fehlendeHD-Fähigkeit; Ursache offen.
- Originalwerte in beiden Läufen vollständig gesichert, kritische Rücklesewerte
  ohne Abweichungen:404/Manual,60000µs/Manual,Gain16,LEDManual53. Kein Dienstausfall
  diesmal, keine Roboter-/Treiber-/Bahnplanungsänderung. Eigenes Kamerafenster
  gezielt pausiert und wieder mit Livebild geöffnet. Experimenteller Pythonhelper
  mit finally-Restore/Report/Dateisperre, drei lokale Fehlertests bestanden.
  [Prüfbericht](docs/wrist_hd_probe_2026-11-10.md), Sitzungen
  setup/calibration/wrist_hd/20261110_201622 bzw.201815. Native Auflösung offen.

### Zellgeometrie

Ursprung am Boden zwischen den Tischmitten. **X nach rechts, Y nach hinten,
Z nach oben**; „vorne“ ist die dem Nutzer zugewandte Seite (−Y).

| ID | UR-Typ | Tisch | Basis XYZ bei Standardaufstellung (m) | Basis-Yaw |
|---|---|---|---|---|
| `left_front` | UR5 | links | −0,45; −0,675; 0,90 | 0° |
| `left_rear` | UR7e | links | −0,45; +0,675; 0,90 | 180° |
| `right_front` | UR5e | rechts | +0,45; −0,675; 0,90 | −90° |
| `right_rear` | UR5e | rechts | +0,45; +0,675; 0,90 | +90° |

- Zwei Tische mit je **0,80 × 1,70 m**; Längskantenabstand **0,10 m**.
- Beide Roboter pro Tisch mittig über der Breite, längs symmetrisch mit **1,35 m**
  Montageabstand. Jeweils 0,175 m Abstand zur vorderen/hinteren Tischkante.
- Tischoberkante vorläufig **0,90 m**, Plattendicke und Beinbreite je **0,05 m**.
  Tische sind in dieser Simulationsversion fest zur Welt verankert; eine geänderte
  Tischpose wird nach Neustart übernommen und verschiebt beide montierten Roboter mit.
- Die echte Aufstellung ist beweglich: Maße/Posen zentral konfigurierbar halten.
- Die ursprüngliche aufrechte Anfangsstellung `[0, −π/2, 0, −π/2, 0, 0]`
  wurde am 2026-11-09 durch ChArUco-Zielansichten ersetzt (siehe unten).
  Robotiq 2F-85 und Wrist Camera sind seit demselben Tag ergänzt.
- Pro Arm kann eine individuelle Kinematik-Kalibrierdatei angegeben werden.
- Offizielle UR-Beschreibungen verwenden. UR7e hat eine eigene Parameterkonfiguration,
  teilt im installierten Upstream-Paket aber visuelle Meshes mit UR5e.

### Korrektur der Montageorientierungen, 2026-11-06

Der Nutzer gab die Kabelrichtungen als groben Anhaltspunkt an:

- Links vorne: Kabel zum Nutzer (−Y), ausdrücklich **−90° gegenüber der ersten Simulation**.
- Links hinten: Kabel nach hinten (+Y).
- Rechts vorne: Kabel nach links zur Mitte (−X).
- Rechts hinten: Kabel nach rechts außen (+X).

Daraus wurden die Yaw-Werte der obigen Tabelle übernommen und im laufenden TF-Baum
geprüft. Die vorherige pauschale Ausrichtung „vorne +90°, hinten −90°“ ist **überholt**.
Alle Winkel beziehen sich auf **`base_link`**. Der UR-Teach-Pendant-`base`-Frame
hat zusätzlich die in der offiziellen Beschreibung enthaltene 180°-Drehung.
Höhe, Yaw-Werte und Scan-Pose sind weiterhin **nicht kalibriert**.

## Implementierung und Schnittstellen

| Bestandteil | Zuständigkeit |
|---|---|
| `uwa_cell_description` | ament_cmake; Tische, offizielle UR-Modelle, gemeinsame Xacro-Datei |
| `uwa_cell_gazebo` | ament_python; Launch, Controller-Konfiguration, Scan-Import/Publisher, Prüfwerkzeuge |
| `uwa_cell_description/config/cell_layout.yaml` | Zentrale Layout-, Montage-, Anfangsstellungs- und Scan-Konfiguration |
| `uwa_cell_gazebo/rviz/cell.rviz` | Roboter, Tische, Grid, optionale Frames und Scan-Referenz |
| `scripts/` | Dienst-, Desktop-, RViz- und Scan-Helfer |

- Eine zusammenhängende Zelle `uwa_cell`, **24 eindeutige bewegliche Armgelenke**
  mit Präfixen `left_front_`, `left_rear_`, `right_front_`, `right_rear_`.
- Ein Manager `/uwa_cell/controller_manager`, ein `joint_state_broadcaster`, vier
  Arm- und vier Greifer-`JointTrajectoryController`, alle neun nach Start aktiv.
- Action je Arm: `/uwa_cell/<id>_trajectory_controller/follow_joint_trajectory`.
- Je Controller steht auch `joint_trajectory` als Topic bereit.
- Gazebo-Server und GUI getrennt starten. Der verpackte Jetty-GUI-Client wird
  direkt gestartet, damit Launch den richtigen Prozess beim Stoppen signalisiert.
- `clock_bridge.py` überträgt echte Gazebo-Simulationszeit über die installierten
  Python-Transport-Bindings und meldet sich vor dem ROS-Abbau explizit ab.

### Robotiq-Werkzeuge, Nutzerauftrag 2026-11-09

- Alle vier Arme sollen ihre Greifer und Wrist Cameras erhalten. Gemeldete
  Beispielgeräte: 2F Adaptive 2020 **S/N C-43008**, Wrist Camera 2019
  **S/N Q-021114**. Der Nutzer hat ausdrücklich **2F-85 (85 mm)** bestätigt.
  Die Nummern sind keine bestätigte Zuordnung zu einem bestimmten Arm.
- Montagekorrektur des Nutzers: Kameralinse auf der vom UR-Werkzeug-I/O-Stecker
  abgewandten Seite. UR-`tool0` +Y zeigt vom Stecker weg; `camera_yaw: 0`
  setzt die Linse entsprechend auf +Y. Kein zusätzlicher TCP-Offset angenommen.
- Greifer-Geometrie, Massen und Kinematik aus PickNik `ros2_robotiq_gripper`,
  festgehaltener Commit und BSD-Lizenz in `THIRD_PARTY.md` / `LICENSES/`.
  Nur Modelldaten übernommen; keine Hardwaretreiber oder seriellen Verbindungen.
- Ein antreibendes Knöchelgelenk je Greifer (0 offen, 0,8 rad geschlossen),
  fünf Mimic-Gelenke. Insgesamt 48 bewegliche Gelenke, 28 Positionsbefehle.
  Greiferaction: `/uwa_cell/<id>_gripper_controller/follow_joint_trajectory`;
  über denselben rqt-Controllerwähler bedienbar.
- Wrist Camera als primitive Geometrienäherung, 13,5 mm Zusatzhöhe ohne
  separate Werkzeugplatte, 160 g; Sensor `[0; 35,7; −0,1]` mm, 30° Neigung
  nach außen, nominell 50° horizontal, 640 × 480, zunächst 10 Hz je Kamera.
  Datenquelle: Robotiq-Handbuch 2019 (Links in `THIRD_PARTY.md`).
- `tools` in `cell_layout.yaml` enthält gemeinsame Einstellungen; je Roboter
  sind partielle Überschreibungen möglich. Kamera und Greifer einzeln abschaltbar.
- ROS-Topics: `/uwa_cell/<id>/wrist_camera/image_raw` und `camera_info`,
  Sensor-Data-QoS, Frame `<id>_wrist_camera_optical_frame`.
  `camera_bridge.py` verwendet wie die Uhrbrücke Gazebo-Python-Bindings mit
  expliziter Abmeldung vor Shutdown. Gazebo-Sensors-System ergänzt.
- Grenzen: Keine herstellergenaue Kameragehäuseform, Objektivkalibrierung,
  URCap-Bildverarbeitung, Autofokus-/LED-Steuerung oder adaptive Kontaktmechanik.
  Die spätere Kalibrier-Routine ergänzt MoveIt-Kollisionsprüfung;
  reale Hardware bleibt Folgearbeit.
- Prüfstand 2026-11-09: beide Pakete gebaut, **24 Offline-Tests erfolgreich**;
  vier gültige RGB-/CameraInfo-Streams, korrekte optische TFs und Zeitstempel,
  neun aktive Controller. Alle vier Greifer einzeln geschlossen/geöffnet und
  zurückgestellt, Mimic-Abweichung < 0,03 rad, andere Gelenke < 0,01 rad Drift.
  Alle vier Arme mit Werkzeugen am Handgelenk bewegt und zurückgestellt;
  tatsächliche Zellwurzel stabil. Installiertes rqt: acht Controller, je
  sechs Armeditoren/ein Greifereditor, gültige Haltebefehle.
  Belege: `setup/logs/uwa-cell-tools-{build,tests,verification,arm-verification,rqt-check}*`
  und `setup/logs/uwa-cell-camera-images/` im Workspace.
- EGL-Betrieb ohne Gazebo-Fenster ebenfalls mit vier Bildstreams und neun
  aktiven Controllern geprüft: `setup/logs/uwa-cell-tools-headless-verification.json`.
  Ein erster Start hatte Controller-Service-Timeouts; die Statusprüfung fragt
  nun höchstens alle 0,5 s ab, der erneute Headless-Start war erfolgreich.
  Uhr-/Kamerabrücke und Server beim Wechsel sauber beendet; Journalbeleg
  `setup/logs/uwa-cell-tools-restart.log`. Keine ungeprüfte Ursache des Timeouts behaupten.
- Das installierte Physik-Backend meldet fehlende native Mimic-Constraints.
  Die getestete Positionskopplung übernimmt `gz_ros2_control`. Kein Nachweis
  realistischer Kraftkopplung oder belastbarer Objektgriff-Physik.

### ChArUco und erster Basisabgleich, Nutzerauftrag 2026-11-09

- Je ein Board mittig zwischen den Robotern pro Tisch; zunächst linkes Paar in
  `left_table_top`, rechtes Paar in `right_table_top` prüfen. Der Nutzer will
  darauf aufbauend ein Werkzeug zur relativen Roboterkalibrierung entwickeln.
- Muster 7 × 5, Feldkante 40 mm, Marker 28 mm, Rand 20 mm, Träger 3 mm;
  `DICT_4X4_100`, links IDs 0–16, rechts 50–66. Alles unter `charuco` in YAML.
- Kamera-Zielansichten per URDF-FK/IK ermittelt und in `initial_positions`
  übernommen: 0,55 m über der Boardmitte, je ±0,28 m entlang Tisch-Y versetzt.
  Bestehende Basis-/Werkzeugmontagen erhalten; kein geplanter Bewegungsweg.
- `charuco_check`: OpenCV 4.10 `CharucoDetector`, PnP/IPPE und LM-Verfeinerung;
  zehn verschiedene Bildzeitstempel pro Kamera, PNGs und JSON-Bericht.
  Ground Truth erst nach der Bildschätzung für Fehlerprüfung aus TF lesen.
- Erste Basisformel: `T_table_base = T_table_board @ inv(T_camera_board) @ inv(T_base_camera)`.
  Die interne TF-Kette beginnt bei URDF `base_link`, ohne bekannte Weltmontage
  als Eingang. Boardplatzierung, Intrinsics, Hand-Auge-Transformation und
  Gelenkkinematik werden als bekannt vorausgesetzt. Noch keine Schätzung
  unbekannter Hand-Auge-/Gelenkparameter aus mehreren Armstellungen.
- Offizielle Boardframes `<table>_charuco`: Musterecke ohne Rand; X rechts,
  Y im Muster nach unten, Z in die Platte. Plattenmitte ist `<table>_charuco_mount`.
- Erster Live-Erfolg: alle vier Gazebo-Bilder mit jeweils 24 ChArUco-Ecken.
  Relative Basenfehler beider Tische ca. 1,9 mm / 0,17°, individuelle
  gemittelte Basisfehler ca. 1,1–1,2 mm / 0,08–0,09°. Idealisiertes Rendering,
  keine Genauigkeitszusage für echte Kameras. Konkrete Zahlen im
  [datierten Bericht](docs/charuco_validation_2026-11-09.json).
- Materialfehler beim ersten Liveversuch: Collada-Fläche ohne Normalen blieb
  unsichtbar. Explizite +Z-Normalen ergänzt, echter Vierkamera-Test danach bestanden;
  Assetprüfung dafür ergänzt. PNG-Muster bleiben deterministisch OpenCV-generiert.
- **33 Offline-Tests bestanden**, beide Pakete gebaut. Vollständiger Bildbericht:
  `setup/logs/uwa-charuco-second/report.json`, annotierte Bilder im selben Ordner;
  Logs `uwa-cell-charuco-{build,tests,live,cell-verification}*` im Workspace.
- Finaler Bestätigungslauf mit Roh- und Erkennungsbildern:
  `setup/logs/uwa-charuco-final/`; zehn erfolgreiche Bilder je Kamera,
  relative Fehler links **1,888 mm / 0,1645°**, rechts **1,843 mm / 0,1570°**.
  Neun Controller aktiv, Zellwurzel stabil, RViz wiederhergestellt. Der separate
  Scan-Publisher blieb erhalten; keine weiteren Zellneustarts geplant.
- Anleitung/Formeln/Bedienung: [docs/charuco_calibration.md](docs/charuco_calibration.md).
  `prepare_charuco_views` erzeugt nach Layoutänderungen eine alternative YAML,
  ohne die Quelle zu überschreiben oder Bewegungen auszuführen.
- Zusammenarbeit: Nutzer arbeitet mit mehreren unabhängigen Agenten im selben
  Checkout. [ACTIVE_WORK.md](ACTIVE_WORK.md) plus eigene Datei je Aufgabe unter
  `work/` eingeführt; vor Edits/Neustarts lesen, Änderungen bereichsweise anwenden.
  Der fremde Scanregistrierungs-Diff wurde erhalten. Für Uhrenreset RViz kurz
  schließen und danach wiederherstellen, separaten Scan-Publisher erhalten.

### Druckvorlagen, Nutzerauftrag 2026-11-09

- Dieselben ChArUco-Muster für echte Versuche angefordert. Originalmaß inklusive
  Weißrand **320 × 240 mm**; Muster 280 × 200 mm, Feldkante 40 mm, Marker 28 mm.
- `output/pdf/uwa_charuco_boards_A3_1to1.pdf`: zwei A3-Querformat-Seiten,
  links/rechts jeweils komplett. `uwa_charuco_boards_A4_tiled_1to1.pdf` im selben
  Ordner: vier A4-Hochformat-Seiten, je Board zwei Hälften mit 20 mm Überlappung.
  Keine verkleinerte A4-Einblatt-Version, da sie andere metrische Maße hätte.
- Beide PDFs als Vektorflächen aus derselben `board_image()`-Ausgabe wie Gazebo;
  IDs links 0–16, rechts 50–66 unverändert. Generator `scripts/print_charuco.py`
  liest die zentrale YAML; optionale PDF-Abhängigkeit `python3-reportlab`.
- Druck: **100% / Tatsächliche Größe**, keine Seitenanpassung; 100-mm-Kontrollstrecke
  und 40-mm-Feldkante nachmessen, plan auf festen Träger aufbringen. Für echte
  Kalibrierung die tatsächliche Boardoberflächenpose im Tisch-KS vermessen.
- Dateiprüfung: korrekte Seitenformate/-zahlen und metrische Vektorgeometrie,
  alle sechs Seiten gerendert und angesehen. OpenCV erkennt auf beiden A3-Seiten
  sowie den digital zusammengesetzten A4-Boards je alle 17 Marker und 24 Ecken.
  Beleg: `docs/charuco_print_validation_2026-11-09.json`, vollständiges Log unter
  `setup/logs/uwa-charuco-print-verification.log` im Workspace. Kein physischer
  Druckertest durchgeführt. Simulation und laufende Dienste nicht verändert.

## Bedienung: aktuelles Sollverhalten

- Startmenü: **UWA Cell Simulation** startet Gazebo, rqt, RViz **und Scan-Publisher**.
- Auch die Desktop-Aktion **RViz öffnen** startet den Scan. **Punktewolke anzeigen**
  bleibt als zusätzliche Aktion vorhanden; **Simulation beenden** stoppt alle drei Dienste.
- Dienste: `uwa-cell-sim`, `uwa-cell-rviz`, `uwa-cell-scan` (systemd-Benutzerdienste).
- Wiederholtes Anklicken verwendet laufende Dienste weiter; die bestehende Simulation
  und deren Gelenkzustände werden dabei nicht unnötig neu gestartet.
- Seit 2026-11-09 holt `scripts/show_cell_windows.py` die vorhandenen XWayland-Fenster
  nach vorne und stellt minimierte Fenster wieder her. Nur PIDs aus den Zell-Diensten
  werden berücksichtigt. Normaler Start fokussiert Gazebo, RViz-/Scan-Aktionen RViz.
  Der Desktop-Eintrag verwendet `StartupWMClass=Gazebo GUI`.
  Kurzlebige Splash-/Menüfenster werden ausgelassen; ein zwischenzeitlich
  verschwundenes Fenster darf den Launcher nicht mit X11-`BadWindow` abbrechen.
- Direktes `cell.sh start` / `ros2 launch ...` behält seine ursprünglichen Defaults:
  GUI und Controller-GUI an, RViz und Scan aus. Das ist bewusst vom Desktop-Start getrennt.
- `cell.sh rviz` öffnet direkt nur RViz; `cell.sh scan` schaltet nur den Scan hinzu.
  Die Desktop-Aktionen kombinieren diese Helfer für die gewünschte Bedienung.
- `MoveCamera` ist explizit das erste RViz-Werkzeug. Linke Maustaste: drehen;
  Mausrad: zoomen; mittlere Maustaste: verschieben. Views-Panel vorhanden.
- Icon: `assets/uwa-cell.png`, RGBA mit transparentem Außenrand. Installer verwendet
  einen inhaltsabhängigen Dateinamen unter `~/.local/share/icons/`, damit GNOME
  nach Bildänderungen nicht das alte Icon aus dem Cache weiterverwendet.
- Desktop-Datei: `~/.local/share/applications/uwa-cell.desktop`.
  Installer: `python3 scripts/install_desktop.py` (als normaler Nutzer, ohne sudo).

## Punktewolke und Grenzen der Referenz

- Original: `~/GoogleDrive/UWA/UR Setup.ply`, ca. **215 MB**, **867.068 Einträge**.
  Binäre Little-Endian-Gaussian-Splat-PLY, keine fertige Dreiecksgeometrie.
- Import übernimmt Zentren und Grundfarben aus SH-DC-Feldern; Opazität aus Logits,
  Ausdehnung aus logarithmischen Skalen. Keine Kollisionen aus dem Scan ableiten.
- Defaults: Mindestdeckkraft **0,1**, maximale Splat-Skala **0,05** Scan-Einheiten,
  Voxelgröße **0,01** Scan-Einheiten, höchstens **200.000 Punkte**.
- Ungültige Werte und ungeeignete Splats filtern; Reduktion und Punktbegrenzung
  deterministisch. Quelle unverändert auf Drive lassen und nicht ins Git aufnehmen.
- Cache: `$XDG_CACHE_HOME/uwa_cell/scans` bzw. `~/.cache/uwa_cell/scans`, NPZ ohne Pickle.
- Publisher: `/uwa_cell/scan_reference`, `PointCloud2`, Reliable / Transient Local.
  Frame `uwa_scan_reference`; statischer Transform von `world`.
- Ursprünglich Maßstab **1** und Identitätspose; diese Anzeige war deutlich gekippt.
  Seit 2026-11-09 ist eine grobe Tischflächen-Ausrichtung eingestellt (siehe unten).
  Die Referenz bleibt ausdrücklich **nicht kalibriert**.
- Ein fehlender Scan darf Gazebo nicht verhindern. Bei `scan:=false` liest der
  direkte Launch den Scan nicht. **Aktuelle Grenze:** Auch zur Cache-Auswahl fragt
  der Importer noch Dateimetadaten des Originals ab; kein garantierter Offline-Fallback
  bei vollständig fehlendem Drive-Mount. Das ist keine bereits erledigte Anforderung.

### Grobausrichtung des Scans, 2026-11-09

- Nutzerauftrag: Die deutlich verdrehte Punktewolke an der Szene ausrichten;
  bei nötigen Bezugspunkten unterstützt der Nutzer.
- Vorgehen: Dominante Boden-/Tischebenen im lokalen Scan-Cache bestimmen,
  zwei zentrale zusammenhängende Tischflächen isolieren und ihre Rechteckkanten
  an den nominellen 0,80 × 1,70 m ausrichten. Keine Roboterposen aus dem Scan ableiten.
- Maßstab **0,9531928102**, Translation **[−0,28749867; −0,43623572; +0,58765448]**,
  RPY in Grad **[−89,761396; +0,349501; +60,140648]**.
  Die Runtime-Werte bleiben zentral in `cell_layout.yaml`; der datierte
  [Fit-Bericht](docs/scan_alignment_2026-11-09.json) dokumentiert ihre Herleitung.
- Die zunächst mögliche 180°-Verwechslung wurde mit konkreten Nutzerangaben aufgelöst:
  **hinter** den Tischen steht eine hohe weitere Roboterzelle aus item-Profilen;
  **vorne** sind zunächst etwa zwei Meter freie Fläche. Die passende Scan-Richtung
  ist bereits eingestellt (+Y zur hohen Profilrahmen-Zelle, −Y zur freien Fläche).
- Der Nutzer konnte die abstrakte A/B-Draufsicht nicht eindeutig zuordnen.
  Bei weiteren Rückfragen besser konkrete reale Gegenstände/Bezugspunkte benennen.
- Nur `uwa-cell-scan` wurde neu gestartet; Simulation, Modellmaße, Robotermontagen,
  Greifer/Kameras und laufende Benutzer-RViz-Ansicht wurden nicht zurückgesetzt.
- Grenzen: Keine metrische Kalibrierung. Die vorläufige Modell-Tischhöhe 0,90 m
  ergibt bei diesem Scan-Fit ca. **0,132 m Bodenversatz**. Reale Höhe noch messen;
  die aktuelle Scan-Schätzung allein ist kein Auftrag, das Modellmaß zu ändern.
  Abweichende Armstellungen zwischen Aufnahme und Simulation sind erwartbar.
- Prüfung: 200.000 endliche Punkte, publizierter Maßstab und Welt-TF entsprechen
  der YAML, genau ein Publisher. Beide bestehenden Dienst-PIDs (Simulation/RViz)
  blieben erhalten. RViz meldet 200.000 dargestellte Punkte und Transform „Ok“.
  **24 vorhandene Offline-Tests bestanden**; protobuf meldet eine Deprecation-Warnung.
- Belege: `setup/logs/uwa-scan-alignment-{estimate,verification}.json`,
  `uwa-scan-alignment-landmarks.png`, `uwa-scan-aligned-rviz.png` und zugehöriges Log
  im Workspace. Analyseprogramme lagen temporär unter `/tmp/uwa-scan-alignment`.

### Scan-Bereinigung, Nutzerauftrag 2026-11-09

- Anforderungen: Keine Punkte weiter als **4 m vom Zentrum zwischen den Robotern**;
  die aufgenommenen Roboter entfernen, damit keine doppelten Arme neben den
  simulierten Robotern stehen.
- Umgesetzt als Kugelradius im Weltkoordinatensystem um den Mittelwert der vier
  Basispositionen, aktuell **[0; 0; 0,90] m**. `scan.crop_center: null` berechnet
  diesen Punkt aus Tisch-/Montageposen; alternativ ist ein expliziter Punkt möglich.
- Acht feste `scan.exclude_boxes` blenden die vier aufgenommenen Arme und ihre
  Basisbereiche aus. Die Aufnahmeposen unterscheiden sich von den Simulationsposen;
  deshalb keine dynamischen Modell-TFs als Entfernungsmasken verwenden.
- Grobe räumliche Masken, keine semantische Roboterdetektion. Sie können direkt
  angrenzende Punkte im selben Volumen mit ausblenden und sind nach einer neuen
  Aufnahme oder Registrierung erneut zu prüfen. Tischflächen und die meisten
  flachen Tischobjekte bleiben durch die Höhenbegrenzung erhalten.
- Modul `scan_filter.py`, Aufruf einmal im Scan-Publisher nach der Skalierung;
  nur die Auswahl wird in Weltkoordinaten berechnet. Publizierte Punkte bleiben
  im bisherigen Scan-Frame. Roh-PLY und Importcache unverändert.
- Konfiguration und Validierung: `crop_radius`, `crop_center`, `exclude_boxes`
  unter `scan`; Radius `null` bzw. leere Maskenliste schalten die Filter ab.
- Ergebnis für die aktuelle Aufnahme: **200.000 → 154.458 Punkte**. Entfernt:
  **27.133** außerhalb des Radius und **18.409** innerhalb der Roboter-Masken.
- Liveprüfung: größter Radius **3,999784 m**, keine veröffentlichten Punkte in
  den Masken, endliche Koordinaten, genau ein Publisher. Rohcache-SHA256 und
  Simulations-/RViz-Dienst-PIDs unverändert. Nur `uwa-cell-scan` neu gestartet.
- RViz-Sichtprüfung: 154.458 Punkte, Transform und Anzeige „Ok“, keine doppelten
  aufgenommenen Arme mehr; Umgebungsgeometrie und Tische sichtbar.
- **44 Offline-Tests bestanden**, inklusive 11 neuer Filter-/Validierungsfälle:
  Weltkoordinaten und Radiusgrenze, Farberhalt, bewegte Tische, feste Masken,
  Überlappungen/leere Ausgabe und ungültige Konfiguration. Eine bestehende
  protobuf-Deprecation-Warnung bleibt.
- Belege im Workspace: `setup/logs/uwa-scan-cleanup-{counts,tests,verification}.*`,
  `uwa-scan-cleaned-rviz.{png,log}` und `uwa-scan-cleanup-regions.png`.
- Parallel aktive ChArUco-Arbeit über `work/` abgestimmt; keine Board-, Werkzeug-,
  Roboter- oder Simulationsstartänderungen durch diese Bereinigung.

## Behobene Probleme und Entscheidungen

| Datum | Beobachtung / Entscheidung | Ergebnis |
|---|---|---|
| 2026-11-06 | Gazebo-Wrapper und Clock-Bridge beendeten sich nicht sauber | Direkter GUI-Client; eigener kleiner Clock-Adapter; gezielte Dienststeuerung |
| 2026-11-06 | Nur diese RViz-Konfiguration erlaubte kein Drehen/Zoomen | Fehlende `Tools`-Liste ergänzt; echte Maus-/Mausrad-Ereignisse geprüft |
| 2026-11-06 | Weißer Außenrahmen am ansonsten gewünschten Icon | Mit Imagegen transparent gemacht; Motiv und dunkelblaues Feld erhalten |
| 2026-11-09 | App zeigte keine Wolke, manuell gestarteter Scan schon | Scan fehlte im normalen Desktop-Start; Start und RViz-Aktion laden ihn jetzt automatisch |
| 2026-11-09 | Nutzer wünscht dauerhaftes Festhalten der Gespräche | Workspace-/Projekt-AGENTS und diese Übergabe angelegt; fortlaufende Pflege vereinbart |
| 2026-11-09 | Icon-Klick scheint nichts zu starten, obwohl alle drei Dienste und Fenster laufen | Vorher nur „läuft schon“; nun Wiederherstellen/Aktivieren der vorhandenen Zell-Fenster ohne Neustart |
| 2026-11-09 | Punktewolke deutlich gegenüber dem Modell verdreht | Grober Ebenen-/Rechteck-Fit; Vorderseite über freie Fläche und hintere Profilrahmen-Zelle identifiziert; keine Kalibrierungsbehauptung |
| 2026-11-09 | Ferne Scanpunkte und doppelte aufgenommene Arme stören | 4-m-Weltradius und feste Scan-Roboter-Masken; nur Referenzpublisher neu geladen |

Ein früher Tracing-Schalter löste den Clock-Bridge-Absturz nicht vollständig;
ihn nicht als fertige Lösung wieder einführen. Zusätzlich wurde am 2026-11-06
ein einzelner RViz-Absturz beim Fensterbetrieb/-ende im Journal beobachtet.
Dessen Ursache ist nicht abschließend geklärt; bei erneutem Auftreten Journal
und Backtrace untersuchen, nicht automatisch mit dem behobenen Kamerafehler gleichsetzen.

Am **2026-11-09** wurde während dieser Prüfung zusätzlich ein neuer Simulationsstart
mit rückwärts springender Uhr beobachtet. Das noch geöffnete RViz brach anschließend
mit `tf2::LookupException: Static cache is empty` für `uwa_scan_reference` → `world`
ab. Die Desktop-Aktion konnte RViz erneut öffnen. Eine grundsätzliche Behebung dieses
Zeitsprung-/TF-Problems ist damit **nicht** nachgewiesen; bei weiteren Simulations-Resets
beachten. Die Zell-Simulation wurde für die Fensteraktivierung selbst nicht zurückgesetzt.

## Prüfstand und Belege

Historisch geprüfte Ergebnisse, keine Behauptung einer erneuten Gesamtprüfung
bei jeder Dokumentationsänderung:

- **2026-11-06:** Beide neuen Pakete gebaut, Systemabhängigkeiten vorhanden;
  **11 Offline-Tests** erfolgreich (Layout/TF-Topologie, Tischumpositionierung,
  Scan-Farben, Filter, ungültige Zahlen, Punktlimit und fehlerhafte PLY-Dateien).
- **2026-11-06:** Simulationszeit läuft, 24 endliche Gelenkzustände, fünf aktive
  Controller; tatsächliche Gazebo-Wurzel bleibt verankert.
- Alle vier Arme einzeln per Action am Handgelenk um 0,1 rad bewegt und zurückgestellt;
  Zielabweichung < 0,03 rad, Drift anderer Arme < 0,01 rad.
- Standard-rqt-Plugin: vier Controller auswählbar, sechs Gelenkeditoren je Arm,
  gültige Haltebefehle publiziert. Drei erfolgreiche Clock-Start-/Stopp-Zyklen.
- RViz: Mausdrehen und Zoom am realen Viewport geprüft; Gegenprobe ohne Tools-Liste
  reproduziert den Fehler. RViz meldete 200.000 Punkte und Transform „Ok“.
- **2026-11-09:** Tatsächlichen installierten App-Eintrag über `gio launch` geprüft:
  200.000 endliche Punkte, Welt-Transform vorhanden, genau ein Scan-Publisher;
  vorhandene Simulations-/RViz-Prozesse erhalten; wiederholtes Anklicken ohne Duplikat.
- **2026-11-09, Fensteraktivierung:** Installierter App-Aufruf fokussiert das vorhandene
  Gazebo-Fenster; Dienst-PIDs von Simulation, RViz und Scan bleiben gleich.
  Eine gezielt minimierte RViz-Ansicht wurde über die echte Desktop-Aktion wiederhergestellt
  und fokussiert. Es war kein Reset der laufenden Roboter nötig.

Belege unter `~/UWA_ws/setup/logs/`, insbesondere:

- `uwa-cell-tests.log`, `uwa-cell-build.log`
- `uwa-cell-motion-verification.json`, `uwa-cell-mount-orientation-verification.json`
- `uwa-cell-rqt-check.log`, `uwa-cell-python-clock-verification.log`
- `uwa-cell-rviz-interaction.log`, `uwa-cell-rviz-negative-check.log`
- `uwa-cell-rviz-interaction.png`, `uwa-cell-scan-verification.json`
- `uwa-cell-desktop-scan-verification.json`
- `uwa-cell-app-window-verification.json`

Temporäre RViz-C++-Testprogramme lagen unter `/tmp/uwa-rviz-check`; deren
Fortbestand nicht voraussetzen. Dauerhafte Prüfkommandos stehen in der README.

Momentaufnahme am 2026-11-09 bei Anlage dieser Datei: Zell-, RViz- und Scan-Dienst
aktiv; separate MuR-Simulation inaktiv. Vor weiterer Prozessarbeit neu prüfen.

## Umgebung und vorherige Workspace-Arbeit

- Workspace `~/UWA_ws`; ROS `/opt/ros/lyrical`; Gazebo Jetty (bei Einrichtung 10.5.0).
- Zell-Umgebung: `source scripts/env.bash` innerhalb dieses Repositories;
  Domain **64**, lokale Discovery, Partition **`uwa_cell_sim`**, `GZ_IP=127.0.0.1`.
- Allgemeines Setup: `~/UWA_ws/setup/lyrical_env.bash`, standardmäßig Domain **62**.
- Separate MuR-Simulation: `setup/start_mur_simulation.sh`, Benutzerdienst
  `uwa-mur620a-sim`, Domain **63**, Partition **`uwa_mur620a_sim`**.
  Nicht mit der Vierarm-Zelle oder echter Hardware vermischen.
- Weitere vom Nutzer gewünschte Repositories: `match_mur_gui`,
  `match_mobile_robotics_jazzy`, `match_mir_camera_calibration`,
  `match_cooperative_handling`, `oak_camera_calibration`, `match_software_utilities`
  (ursprünglich aus der GitHub-Organisation `match-ROS`).
- Bestehende Lyrical-Portierungen mit lokalen Änderungen auch in Submodulen:
  [Patch-Übersicht](../../setup/patches/lyrical-controllers/README.txt),
  [Manifest](../../setup/patches/lyrical-controllers/manifest.json).
  Laut Übersicht sind die Patches bereits angewendet; nicht erneut blind anwenden.
- Ursprüngliche Einrichtungshelfer: `setup/install_lyrical.sh`, `setup/check_lyrical.sh`,
  `setup/test_controllers_lyrical.sh`. Interaktive sudo-Anmeldung erfolgt lokal durch den Nutzer.
- Google Drive wurde via rclone unter `~/GoogleDrive` eingebunden. Setup-Hinweise
  liegen unter `setup/google-drive/`; Mount/Anmeldung bei Bedarf prüfen. Keine
  Zugangsdaten in Git oder in diese Übergabe kopieren.

## Statische OAK4-Übersichtskamera (2026-11-09)

- **Wichtige Nutzerpräzisierung:** später einen Tisch absichtlich verschieben;
  Tisch-zu-Tisch-Pose und tatsächliche Bewegung messen, Fehler kompensieren.
  Beide Tischboards bleiben fest montiert. Option: kleine OAK auf rechtem Tisch
  sieht nur das gegenüberliegende Board. Tischfeste Kameramontage und variable
  Tischpose unbedingt getrennt behandeln, Bewegung nicht in Kalibrierung absorbieren.
- Neuer [Kalibrier-/Messansatz](docs/table_tracking_calibration.md): OAK sieht
  beide Boards -> relative Boardpose durch inv(T_C_BL)@T_C_BR, Weltpose der
  Kamera fällt heraus. Tischmontagen der Boards für definierte Tischframes ergänzen.
  Für OAK auf rechtem Tisch Montage X einmal separat bestimmen; danach bleibt X
  bei Tischbewegung konstant. Unbekannte Montage plus unbekannte Tischrelation
  sind aus einer einzigen gegenüberliegenden Boardansicht nicht getrennt schätzbar.
- Nutzer schlägt bekannte stationäre Wrist-Kameras und ein zusätzliches mobiles
  Kalibrierboard im gemeinsamen Sichtfeld vor. Als bevorzugter erster Ansatz
  empfohlen: lokale Kamera-Kamera-Transformation über viele Halteposen, dann
  bekannten FK-/Hand-Auge-/Tischbezug nutzen; weder Tischboards noch Kameras
  müssen sich bewegen. Alternative: UR hält Board für automatisierte Eye-to-Hand-
  Schätzung inklusive unbekannter Werkzeug-Board-Montage. Empfehlungen, noch
  kein Implementierungs-/Messfahrtauftrag. Frühere Konzeptannahmen entsprechend
  als eingeschränkt markiert; keine Dienste/Hardware/Simulationsposen verändert.

- Beratungsfrage zur empfohlenen Kalibrierung statischer Kameras:
  [Konzeptvorschlag](docs/static_camera_calibration_plan.md) festgehalten.
  Factory-Intrinsics für Bildmodus/Fokus prüfen, feste Tischboards als Referenz
  und zur Verbindung beider Tischgruppen, Zusatzkameras über gemeinsame/registrierte
  Targets, anschließend räumlich vielfältige gemeinsame Schätzung und unabhängige
  Validierung. Referenzbeziehung zum realen `world` definieren/vermessen, keine
  angenommenen Gazebo-Posen als Hardware-Messwerte. Dies ist eine Empfehlung,
  noch kein genehmigter Implementierungs-/Messfahrtauftrag oder Kalibrierergebnis.

- Nutzerangabe: OAK4-D auf einem Stativ neben den Tischen, derzeit rechts,
  nach unten auf die Tischplatten; Montage noch offen. Gewünscht ist Überblick
  über die ganze Szene bei genügend ChArUco-Detail. Dafür Simulation zum
  Vergleichen von Position, Höhe, Blickrichtung und Auflösung verwenden.
- Umgesetzt als eigene statische Gazebo-Entität `uwa_oak_overview`, außerhalb
  der Zell-URDF. Bestehende Zell-/Wrist-/Greifer-/Controllerkonfiguration erhalten;
  keine Gelenkbefehle und kein Zellneustart durch diese Aufgabe.
- Nutzerkorrektur: reales Stativ maximal **2 m**. Zwei zusätzliche OAK-Kameras
  verfügbar, falls tote Winkel ergänzend abgedeckt werden müssen. Die erste
  unbeschriftete Kamera per USB identifiziert: EEPROM **OAK-D Pro AF**, SDK
  **OAK-D-PRO-AF**, RVC2/DM9098, IMX378-Autofokus + zwei OV9282. Zweite Kamera
  noch ungeprüft; frühere gemeinsame Bezeichnung OAK-D-S2-FF ist überholt.
  Keine konkreten Zusatzkameraposen festgelegt. Diagnose im OAK-Repo-Handover.
- Aktuelle zentrale Konfiguration `overview_camera` in `cell_layout.yaml`:
  optisches Zentrum Welt[1.8,-0.8,2.0]m, Ziel[0,-0.1,0.95]m, etwa28,5° nach unten,
  nominell67,3° horizontal,4000×3000@3Hz Simulationszeit. Nicht kalibriert.
- Neue2m-Pose live geprüft: alle Tisch-Ecken geometrisch im Bild, vier Arme und
  Tischplatten im geprüften Bild sichtbar,12/24 Ecken links/rechts erkannt,
  RMS0,691/0,042px. Links wenig Reserve; Zusatzkameras für tote Winkel/Details
  sind eine Erweiterungsoption. Keine Garantie für alle Armstellungen.
- Mehrere Kandidaten verglichen: mittig rechts zu wenig linke Erkennung,
  starke Frontdiagonalen durch Arme verdeckt.6k lieferte CameraInfo, aber kein
  erfolgreich empfangenes RGB im Zeitfenster;5k ebenfalls nicht erfolgreich.
  Daher bei4k geblieben. Keine Behauptung einer Hardwaregrenze daraus.
  Belege `setup/logs/uwa-oak-2m/`, finale JSON/Bilder dort unter `final/`;
  neue Pose und Höhenlimit mit13 Offline-Tests geprüft. Aktiver Layoutpfad
  wieder zentrale Quelldatei. Kein Zellneustart und keine Arme durch uns bewegt.
- Getrennt vom echten Kameratreiber/SDK. RGB-Pinhole-Näherung, primitive Gehäuse-
  und Stativdarstellung. Keine Tiefenkanäle, realistische Verzeichnung,
  Rolling-Shutter-Verzerrung, Rauschen oder Autofokus simuliert.
- Starter `scripts/overview.sh start|view|reload|coverage|check`. Neue Zellstarts
  starten den Kameraknoten; zur laufenden Zelle wurde er separat über
  `uwa-cell-overview` ergänzt. Sperre pro Benutzer/Partition verhindert zwei
  Besitzer. `cell.sh stop` beendet auch Kamera und separaten Bildbetrachter.
- Pose-/Optikänderungen über `reload` ersetzen nur die Kamera und aktualisieren
  TF/Marker. Nach Anpassung der YAML kein Roboterneustart nötig. Erfolgreich
  zunächst mit2,6m/3m geprüft; diese Versuche sind nach der Nutzerkorrektur
  historisch. Aktueller Stand ist die oben dokumentierte2m-Pose.
- Themen `/uwa_cell/oak_overview/rgb/image_raw` und `camera_info`, optischer TF
  `world -> oak_overview_rgb_optical_frame`. RViz-Config ergänzt um Gehäuse,
  Stativ und Frustum-Marker auf `/uwa_cell/oak_overview/markers` (latched).
  Marker/TF ursprünglich empfangen: zehn Marker, damalige Weltposition[1.8,0,3.0].
- Historischer3m-Prüfstand: bei4k Marker-Minimalseite links/rechts
  ca17,6/28,4px. Sichtfeldrechnung prüft keine Verdeckungen. Echte Erkennung:
  Ausgangspose18/24 Ecken, RMS0,069/0,061px; niedrigere Variante20/24 Ecken,
  RMS0,054/0,096px. Beide Boards jeweils im selben Bild erkannt. Zahlen sind
  Momentaufnahmen, keine Genauigkeits-/Sichtbarkeitsgarantie für alle Armposen.
- Gefundene Grenze: OpenCVs Standard-Minimum3% Bildkante verwirft kleine Marker
  im4k-Gesamtbild. Neuer optionaler Parameter an `detect_pose` belässt den
  Wrist-Standard0,03; Overview verwendet32px minimalen Umfang. Kein GT-ROI oder
  bekannte Kamerapose zum Fit verwendet. Bild-/CameraInfo-Frame und Größe geprüft.
- Build abgeschlossen,70 passende Offline-Tests bestanden; bisherige
  Beschreibungs-/Scan-/Wrist-/ChArUco- und Kalibrierkern-Tests eingeschlossen.
  Belege unter `setup/logs/uwa-oak-overview-*`, Anleitung in
  [docs/oak_overview.md](docs/oak_overview.md). Simulationslivebild geöffnet.
- Grenze: Stativ ist derzeit visuell, ohne Gazebo-/MoveIt-Kollision. Separate
  Gazebo-Modelle gelangen nicht automatisch in die bestehende PlanningScene.
  Kollisionskörper vor entsprechendem Planungs-/Hardwareeinsatz ergänzen.
- Parallele Aufgabe `handeye-diagonal` gesehen: keine Zell-/Scan-Neustarts oder
  Armtests durch OAK-Aufgabe. Automatische Wrist-Hand-Auge-Kalibrierung um die
  externe OAK zu erweitern und reale Welt-Extrinsics zu bestimmen ist Folgearbeit.

## Automatische Hand-Auge-Kalibrierung (2026-11-09)

- **Aktueller Folgeauftrag:** diagonale Paare statt ausschließlich eines Arms:
  links vorne + rechts hinten, danach links hinten + rechts vorne. Die jeweils
  anderen Arme zuvor seriell zur Seite parken. Die frühere Einzelarmreihenfolge
  bleibt in der GUI mit ausgeschalteter Option **Diagonalpaare** bzw. CLI
  `--sequential` verfügbar. Der folgende ursprüngliche Genauigkeitsnachweis
  wurde noch mit dem Einzelarmablauf aufgenommen.
- Paarmodus: gemeinsame zukünftige Startzeit und Dauer beider Trajektorien;
  volle MoveIt-Szene für die Wege plus getrennte Hüllräume aller Kollisionskörper
  über beide Wege, mit 80 mm zusätzlichem Puffer je Arm. Die Freigabe bleibt auch
  bei unterschiedlichem Fortschritt nominal getrennt; keine pauschale
  Reichweitenannahme ersetzt diese Prüfung. Einrichtung und Rückfahrt seriell.
- Anfangs-Boardansichten aus der zentralen YAML dienen zum Wiederanstellen
  geparkter Arme. Die gemessenen tatsächlichen Sitzungsstartstellungen werden
  erst nach Abschluss aller Gruppen wiederhergestellt; Stopp/Fehler halten
  sämtliche aktiven Ziele an der aktuellen Stelle und sperren folgende Fahrten.
- Neuer Paar-Nachweis: **79 aktuelle Offline-Tests bestanden**, vollständiger
  40×4-Lauf `setup/calibration/20261109_133357_7e1130` bestanden; echte parallele
  native Gelenkbewegung in beiden Diagonalpaaren beobachtet. Mindestens 0,307 m
  bzw. 0,372 m Abstand der konservativen nominalen Hüllräume. Wartearme stationär
  (< 1,4e−11 rad Abweichung); alle Rückkehrstellungen < 1,5e−11 rad Fehler.
  [Paar-Prüfbericht](docs/handeye_diagonal_validation_2026-11-09.json).
- Paarlauf: maximale Kameraextrinsics-Abweichung **0,078 mm / 0,030°**;
  relative Basispose links **0,092 mm / 0,0231°**, rechts **0,085 mm / 0,0247°**.
  Basisabstände links **1349,987 mm**, rechts **1349,987 mm**. Fit/Validierung
  bleiben pro Arm 32/8 und relative Posen weiterhin pro linkem/rechtem Tisch.
- Gemeinsames Pause/Fortsetzen und anschließender Stopp beider Controller in
  **0,46 s** bestätigt: `setup/logs/uwa-diagonal-pause-stop.json`.
  Paar-Profil aktiviert, rohe/kalibrierte TFs und Rückfall bei ungültiger Qualität
  sowie kollidierendem Kandidaten geprüft: `uwa-diagonal-profile-check.json` im
  gleichen Logverzeichnis. GUI-Lebenszeichenverlust während simultaner Fahrt
  stoppt beide nach **2,33 s** einschließlich Timeout, paralleler Aufnahmestopp
  bestätigt Stillstand nach **0,30 s**. Danach keine weitere Fahrt/Aufnahme.
  `uwa-diagonal-{disconnect,capture}.json`; alter Einzelarmmodus mit echtem
  GUI-Stopp ebenfalls bestanden (`uwa-diagonal-legacy-gui-stop.json`).
- Vier Pakete gebaut; Zellprüfung bestätigt neun aktive Controller, zum Layout
  passende ursprüngliche Basen und stabile physische Gazebo-Verankerung.
  Das Paarprofil wird beim Start automatisch wiederhergestellt. **Diagonalpaare**
  standardmäßig aktiviert; geänderte Auswahl/Messzahl/Modus nach Vorbereitung
  sperren den Start bis zur passenden erneuten Vorbereitung.

- Nutzerauftrag: genehmigten Plan vollständig in der Simulation umsetzen;
  eigene Qt-GUI, 30–50 verschiedene Stellungen pro Arm (Standard 40), links/rechts
  getrennte relative Basen, unbekannte Kameraextrinsics und explizite Übernahme.
- Neue Pakete `uwa_cell_calibration_msgs` und `uwa_cell_calibration`. Start neben
  der bestehenden Zelle: `ros2 launch uwa_cell_calibration calibration.launch.py`.
  Anleitung: [docs/automatic_handeye.md](docs/automatic_handeye.md).
- Vollständiges MoveIt-Modell mit vier Gruppen und allen Kollisionskörpern;
  lokale quintische Wege mit maximal 0,10 rad/s und 0,20 rad/s² werden vollständig
  gesampelt geprüft. Blockierte Wege werden verworfen, keine OMPL-Umwegsuche.
  Deterministische Kugelkappenansichten mit acht Reserveposen bei 40 Messungen.
- Datensatz: rohe und annotierte Bilder, CameraInfo, Bild-/Objektpunkte,
  zeitlich passende Gelenkwerte und `T_base_link_tool0` unter Workspace
  `setup/calibration/`. Keine Sitzungsdaten ins Repository übernehmen.
- Fit ausschließlich aus Bildern und Werkzeugkinematik: Park-Initialisierung,
  robuste gemeinsame Bildeckenverfeinerung von `X` und `Y` in `M_i X C_i=Y`.
  Bei 40 Stellungen 32 Fit + acht vorab bestimmte, unabhängige Validierungen.
  Keine nominellen Extrinsics / Ground Truth im Fit. Boardpose erst für die
  abgeleiteten absoluten Tischkoordinaten erforderlich.
- Backend und Qt6-GUI getrennt; nicht befehlsfähiger Planungs-/Fit-Prozess,
  eigener Walltime-Watchdog, Besitzer-Lebenszeichen, Controller-Abbruch mit
  Abbremsparametern, Stillstandsbestätigung und Gazebo-Pause als Rückfall.
  Kein automatisches Zurückfahren nach Stopp oder Fehler. Geprüfte Rückfahrt zur
  gemessenen Startstellung nach regulärem Abschluss (im Paarmodus nach allen Gruppen).
- Übernehmen erzeugt ein versioniertes Profil und `calibrated/`-TF-/MoveIt-Modell.
  Physische Gazebo-Montagen und der ursprüngliche TF-Baum bleiben erhalten.
  Kandidatenprüfung vor atomarer Profilaktivierung; altes Profil bei Fehler behalten.
- Prüfnachweise: vier Pakete gebaut, **57 Offline-Tests bestanden**
  (`setup/logs/uwa-handeye-all-tests-final.log`). Vollständige Sitzung
  `setup/calibration/20261109_122753_b901ad`: **40 Aufnahmen je Arm**, jeweils
  32 Fit + acht Validierung, alle Qualitäts- und Ground-Truth-Ziele bestanden.
  [Datierter Bericht](docs/handeye_validation_2026-11-09.json).
- Kameraextrinsics-Fehler: links vorne **0,130 mm / 0,0345°**, links hinten
  **0,049 mm / 0,0306°**, rechts vorne **0,073 mm / 0,0279°**, rechts hinten
  **0,047 mm / 0,0304°**. Validierungs-Reprojektion 0,075–0,122 px medianer RMS.
- Relative Basispose links **0,640 mm / 0,0533°** Fehler, Abstand **1350,012 mm**;
  rechts **0,128 mm / 0,0269°**, Abstand **1349,989 mm**. Park-Bootstrapintervalle
  des Abstands links 1349,736–1350,809 mm, rechts 1349,629–1350,664 mm.
- `setup/logs/uwa-handeye-profile-check.json`: Rückkehrfehler aller Armgelenke
  < 1,4e−11 rad; getrennte rohe/kalibrierte TFs stimmen mit ihrem jeweiligen Modell
  überein. Schlechte Qualität und ein absichtlich kollidierendes Kandidatenmodell
  behalten vorheriges Profil und Modell; gültige Reaktivierung erfolgreich.
  Gespeichertes Profil wird beim Backend-Neustart wieder geladen.
- Echte GUI-Knöpfe live geprüft: Stopp während Planung, tatsächlicher Fahrt und
  Aufnahme; Stillstand bei Fahrt/Aufnahme nach rund **0,30 / 0,29 s** bestätigt.
  Eingefrorenes GUI-Lebenszeichen trotz weiterlaufendem ROS-Thread stoppt nach
  rund **2,27 s** einschließlich Lease-Frist. Keine folgende Bewegung/Aufnahme.
  Direkte Gazebo-Pause bestätigt und anschließend Welt erfolgreich fortgesetzt.
  Logs/JSON: `setup/logs/uwa-handeye-gui-{planning,exercise,capture,freeze,world-pause}.*`.
- GUI zeigt Livebilder und die vollständige Ergebnistabelle in getrennten Tabs,
  bei unverändert erreichbaren Steuerknöpfen. Statusmeldungen verwenden eine
  Steady-Clock und bleiben auch bei pausierter Simulationszeit verfügbar.
- Nur die besitzende GUI fordert bei verlorener Backend-Verbindung automatisch
  die Weltpause an. Beobachterfenster dürfen eine laufende Sitzung nicht durch
  ihre eigene verzögerte Verbindung unterbrechen; Profilwiederherstellung hat
  noch keinen GUI-Besitzer und versendet keine Fahrbefehle.
- Beim ersten Freeze-Test trat erst nach erfolgreicher Stillstandsbestätigung
  ein Prozessabsturz beim Beenden auf. ROS-Executor-Threads werden nun vor der
  Node-/Kontextzerstörung beendet; wiederholter Freeze-Test beendet sich sauber.
- Behobene Simulationsbesonderheit: passive Robotiq-Mimic-Geschwindigkeiten
  können trotz Stillstand stark rauschen. Für den Bewegungsstopp alle
  angetriebenen Gelenke prüfen und zusätzlich unerwartete Gelenkpositionsänderungen
  überwachen; vor Fahrbefehlen ein stabiles Geschwindigkeitsfenster verlangen.
- Grenzen: Simulation mit idealen Intrinsics und angenäherter Kamerageometrie;
  keine reale Stoppsystem-/Hardwarefreigabe. Bootstrapwerte sind
  Wiederholungsstreuung, keine Garantie absoluter Genauigkeit.

## Offene Ziele / noch nicht freigegebene Genauigkeitsannahmen

1. Echte Tischhöhe und Montageposen messen, Basisorientierungen kalibrieren.
2. Individuelle UR-Kinematikdateien übernehmen, sobald verfügbar.
3. Vorhandene grobe Scan-Ausrichtung metrisch kalibrieren, insbesondere reale
   Tischhöhe und Bodenversatz klären. Keine unbestätigte Montagekalibrierung
   automatisch als wahr übernehmen.
4. MoveIt über die nun vorhandene Kalibrier-Kollisionsprüfung hinaus für allgemeine
   und kooperative Bewegungsplanung ergänzen.
5. Später explizit geplante Hardware-Anbindung und Synchronisation untersuchen.

Die Liste beschreibt offene Arbeitspakete, keinen Auftrag, sie ohne weitere
fachliche Abstimmung sofort alle umzusetzen. Aktuelle Konfigurationswerte und
Bedienung haben Vorrang vor überholten Gesprächsständen.

## Reale Rücksetzung für Simulationsgriff,26.11.2026,ab17:30AWST

Nutzer bestätigt ausdrücklich: niemand im Arbeitsbereich. Session
4dcbdf235d344357b4a57a32eac7ab7c regulär freigegeben. Library-Lauf
400d02e5c2034417a97300bc60236030 über normale API gestartet, Browserzugriff
nicht verfügbar. Frischer Plan f1bdbb01a699e87a9c005ded50b3f5eb2e16e4879e1414619abb535f3775d5cd,
zusätzlicher Halternachweis `release-current-holder-audit` bestanden.
Aktuelle native Bilder vor Öffnen und nach Ablage geprüft. Öffnungsreview
1903aa0f569b4ee8bb0b961e21a716ea delegiert freigegeben; beide Greifer
POS3, ACT1/STA3/FLT0, FOR0/SPE16, regulär erfolgreich. Keine beladene
Armbewegung. Karton im Folgefoto auf Tisch, beide Finger geöffnet.
Rückzugsreview3297a61b66ef48b79facb1877dfa58a4 freigegeben und gemeinsame
senkrechte Fahrt erfolgreich. Home-Review6226dac55fba40c7ad161f23486cbd4c
für geprüfte unbeladene Wege freigegeben; Abschluss noch zu beobachten.
Neuer Griff noch nicht ausgeführt. Sicherheitsprogramm unverändert.

## Home-Restweg nach verspäteter Abschlussmeldung,26.11.2026,17:35–17:43AWST

Originaler Library-Home-Abschnitt scheitert nach erfolgreicher RF-Fahrt
vor Dispatch des RR-Ziels: `right_front: controller still owns an action
or has not acknowledged the current state`. Phase-2-Bericht bestätigt
RF-Ziel per erfolgreichem FollowJointTrajectory, maximal49µrad vom
Homeziel. Aktueller Schutzstatus anschließend RUNNING, keine Konflikte,
alle action_active:false. Passender Schutz-Journalausschnitt ohne Einträge;
kein neuer Schutzstopp beobachtet. Ursache ist die Aufgabenübergabe nach
erfolgreichem Aktionsresultat bei noch älterer Aktionsstatusmeldung.

Endlicher Executor kann jetzt mit `--resume-completed` die bestätigte
Präfixfahrt prüfen und ausschließlich identische verbleibende Homegruppen
zur neuen Motion Review vorlegen. Originalplan, ursprünglicher Fehlerbericht
und beide vorhandenen Nachweise bleiben erhalten. Keine neue Bahnplanung,
kein Schutzdienstwechsel, kein automatisches Resume. Die erste noch nicht
gefahrene Review wurde wegen einer irrtümlichen Gesamtvorschau zurückgenommen;
Vorschau zeigt jetzt nur RR,51,657430s, und den abgelegten Karton.
23 gezielte Home-Tests bestanden, einschließlich bestätigter Präfixe,
geänderter Resultate und ausschließlicher Restweg-Vorschau.

Neue Review f16b33c3e97447daa2884e1f10b73d58 wurde vom Bediener freigegeben
(nicht von diesem Agenten); RR-Fahrt erfolgreich17:43:18AWST.
`remaining-home-result.json` bestätigt beide rechten Homeziele nach
Original-RF-Abschluss und unverändertem RR-Restweg. Beide Greifer offen,
Karton auf Tisch. Original-Library-Lauf bleibt korrekt als abgebrochen
dokumentiert; die erfolgreiche Restfahrt ist ein separater Nachweis.

## Neuaufnahme: Kameravergleich führt zu Höhenverdacht,26.11.2026,18:03–18:13AWST

Library45f22c120ab84daa98750cb502c1e9c3 vor Bewegung am Versionsvergleich
carton_depth_geometry.py beendet; alte Aufgabendatei gesichert und mit
lokaler geprüfter Fassung abgeglichen. Erneuter normaler Librarylauf
038645e531d1444c81dfe3045ae6a7d6 erfasst neue HQ-RGB-D-/native Bilder
und beide unabhängigen geometrischen Kartonposen. Kein neuer Arm-/Greiferbefehl.
Vergleich nach180°-Symmetrie:48,581mm Zentrumsdifferenz,1,188728°,
zulässige30mm/3° unverändert; vor Anfahrt abgebrochen.

Beide Landmarkenbilder plausibel. Einmalige gezielte Fehlerdiagnose
vergleicht aktuell sichtbare feste Marker mit Referenzphotos13:30AWST:
13 gemeinsame OAK4-Marker/17 USB-Marker, mediane Verschiebung1,207/1,0px.
Kein deutlicher Hinweis auf Kameraversatz; dies ist kein routinemäßiger
erneuter Boardcheck oder neue Laufzeitüberwachung.

Unabhängige diagnostische Zweikamera-Triangulation der markierten Ecken
(keine Übernahme als Metrikquelle für den Greifablauf): Kanten400,89/
402,30mm und328,76/329,70mm; Eckhöhen179,89–189,75mm. Abstände der
korrespondierenden Sehstrahlen0,68–5,56mm. Asset carton_avocado_v1
enthält dagegen404,04×342,33×163,31mm, obere Eckhöhen159,38–163,31mm;
Metadaten ausdrücklich image_based_estimate, measured_accuracy_validated:false.
User fragt nach Nutzung bekannter Maße: erklärt, dass diese Geometrie bereits
im Fit steckt und die Höhenannahme beide monokularen Zentren verschieben kann.

OAK4-HQ-Tiefe separat gegen eine im selben Frame geschätzte lokale Tisch-
ebene geprüft, RMS5,734mm. Reprojizierte EckpatchesB/C mit136/169 gültigen
Tiefenpunkten: Mediane190,96/182,07mm; D175,41mm; A durch Wand/Tisch-
Mischpunkte nicht aussagekräftig. Rohdaten nicht korrigiert, kein Genauigkeits-
nachweis. Stützt den Höhenverdacht ohne USB als Greif-Metrikquelle zu verwenden.
Diagnosen fixed-marker-comparison.json, triangulation-diagnostic.json,
rim-depth-diagnostic.json unter setup/tasks/carton-air-demo-20261126.

Nutzer nach unabhängig bekannten Außenmaßen/Eckhöhen gefragt; vor Betreten
für eine nötige Messung Arbeitsbereich widerrufen. Noch keine Modelländerung
oder Grenzaufweitung. Aktuell beide rechten Arme Home, beide Greifer offen,
Karton auf Tisch. Linke Programme einmal rein lesend bestätigt: beide
RUNNING/NORMAL/PLAYING ros.urp, Reverse aktiv, commands:[], keine Power/
Brake/Play-Aktionen nötig. Vollständiger alter Nachweis bleibt an alte
Assetgeometrie gebunden; Geometriekorrektur muss ausdrücklich berücksichtigt
werden, kein unveränderter Cache-Nachweis für ein anderes Objekt behaupten.

Neues Luftprobe-Profil anschließend bis zur Maßklärung `enabled:false`
gesetzt, um keine bekannte ungesicherte Modellkorrektur auszuführen. Nur
lokale Aufgabenverfügbarkeit, keine Änderung/Stop des Schutzdienstes,
keine Power-/Brake-/Play-Aktion. Standardprofil unverändert. Aktive Library
weiter Port34911, foreground-Sitzung4627.82 vorherige Workflowtests sowie zuletzt60 fokussierte Tests einschließlich
der endlichen Plausibilitätsentscheidung bestanden
(model-clarification-tests.log). Arbeitsbereich bleibt in dieser
Sitzung freigegeben, solange niemand zur Messung eintritt; vorher widerrufen.
