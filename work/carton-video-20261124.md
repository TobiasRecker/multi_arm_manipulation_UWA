# Kartonvideo mit nativer Gazebo-Darstellung · 24.11.2026

Nutzerauftrag: anschauliches Video der bestehenden Dreiarmdemo mit Greifen,
Anheben, Drehen, Zeichnen und virtuellen Bohrzustellungen. Etwa15 Bilder/s
Ablaufzeit aufnehmen und gleich2× beschleunigen; gelbe und rote Spuren am
Karton wie in der Browseransicht.

Quelle: abgeschlossener Gazebo-Lauf
`setup/tasks/house_drill_home_20261120_01/run05`, Szene`scene05`.
54 geprüfte gespeicherte Bewegungsphasen ab Hub, zusätzlich Anfahrt/Einfahrt.
Neues Video verwendet die Solltrajektorien und kinematische Griffbindung;
es ist keine erneute Kontaktphysik und keine neue reale Ausführung.
Greiferöffnung/-schluss werden für die Ansicht interpoliert, nicht als
aufgezeichnete passive Fingerpositionen ausgegeben.

Implementierung unter`tools/carton_video/`: isoliertes Assetpaket mit
Quellhashes, Hermite-Interpolation der gespeicherten Gelenkstützstellen,
Vorwärtskinematik, native`gz-rendering`/Ogre2-Kameras, gelbe Spuren und rote
Bohrmarken im Kartonframe, deterministischer Export mit15 Zuständen/s nach
30fps bei2×. Übersicht und mitgeführte Werkstücknahansicht in1920×1080.
Kein ROS-/Controller-/Hardwarezugriff und kein neuer Laufzeitwächter.

Compute: eigener`carton-render.sif` auf titanpc aus`planning.sif`, ergänzt
um`ros-lyrical-gz-rendering-vendor`, EGL/Mesa und FFmpeg. Vorab Last/GPU/RAM/
Datenträger geprüft: GPU0%,175MiB belegt, etwa21GiB verfügbar,502GiB frei.
Voransicht vor dem Gesamtrendern visuell prüfen. Ausgangsdaten/Container/
Joblog und Renderparameter liegen unter`setup/tasks/carton_video_20261124/`
bzw. im eigenen UWA-Compute-Verzeichnis auf titanpc.

Standbildprüfung: Job`carton-video-preview04-20261124` erfolgreich. Sieben
native Kamerapaare gerendert; Home, Seitenkreis, Haus mit sechs roten Stellen,
Bodenkreis, Gegenwandkreis und Ende visuell kontrolliert. Gelbe Linien und
rote Stellen liegen sichtbar am Karton, beide Ansichten zeigen dieselbe
Situation. Vorschau lokal`setup/tasks/carton_video_20261124/preview04/`.
Vorherige technische Fehlversuche bleiben in den Compute-Joblogs erhalten:
ROS-Setup unter`set -u` sowie nicht explizit geladene Meshes; beide korrigiert.

Offline-Aufbereitung erfolgreich:2711 Zustände bei15Hz,180,733s mit kurzen
Ansichtshalten,54 Quellbewegungsphasen,307 gelbe Segmente und6 rote Stellen.
Maximale Abweichung der aus beiden Haltearmen rekonstruierten Objektposition
0,000248mm. Alle60 Quelldateien perSHA-256 gebunden,34 visuelle Assets
einschließlich Texturen separat paketiert. Python-Syntaxprüfung und nativer
C++-Build erfolgreich.

Erster vollständiger Export`carton-video-final-20261124` technisch bestanden:
1920×1080,H.264,30fps,2711 Bilder,90,366667s. Zusätzliche Zwischenbilder
zeigten aber eine Tischverdeckung der Nahkamera bei Rückdrehungen; diese
Fassung wird nicht abgegeben. Kamera korrigiert: mindestens1,12m über dem
Boden und hinreichender horizontaler Abstand zum Karton, geglättete Führung.
Alle2711 Kameraziele offline kontrolliert. Kleinster tatsächlicher
geglätteter Abstand zum Kartonzentrum0,433m, kleinste Kamerahöhe1,12m.
Dies betrifft nur die Videokamera, keine Roboterbahn.

Job`carton-video-final02-20261124` rendert die korrigierte Fassung.
17 Standbilder einschließlich zehn Dreh-/Rückfahrzwischenständen erzeugt;
die vorher verdeckten Situationen sind jetzt sichtbar. Prüfung lokaler
JPEGs unter`setup/tasks/carton_video_20261124/preview-final02/` bestanden.
Export und abschließender Videoabruf folgen.

Bedienung: [Videoexport](../docs/gazebo_carton_video.md).
