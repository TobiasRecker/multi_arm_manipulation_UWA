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

Ergebnis/Prüfung: wird nach Standbildprüfung und Videoexport ergänzt.
