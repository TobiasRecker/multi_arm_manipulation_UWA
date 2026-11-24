# Gazebo-Kartonvideo mit Werkstückspuren

Stand24.11.2026. Die Dreiarmdemo kann ohne Bildschirmaufnahme mit Gazebos
nativer Ogre2-Renderbibliothek exportiert werden. Die Fassung zeigt eine
Zellübersicht und eine mitgeführte Kartonnahansicht. Gelbe Spuren entstehen
beim Zeichnen, sechs rote Markierungen bei den virtuellen Bohrzustellungen.
Die Spuren bleiben im Kartonframe erhalten.

Fertige Fassung: [Video,90s/1080p/30fps/2×](../../../setup/tasks/carton_video_20261124/uwa-carton-gazebo-2x.mp4)
· [Vorschaubild](../../../setup/tasks/carton_video_20261124/video-preview.jpg).
2711 Bilder und zehn dekodierte Stichproben geprüft; lokale Kopie stimmt
perSHA-256 mit dem titanpc-Ergebnis überein.

Quelle ist der erfolgreiche Kontaktlauf vom20.11.2026:
`setup/tasks/house_drill_home_20261120_01/run05`, Szene`scene05`.
Der Videoexport spielt dessen gespeicherte geprüfte **Sollbahnen** mit einer
starren kinematischen Griffbindung ab. Er führt keine neue Kontaktphysik aus
und ist keine Aufzeichnung gemessener passiver Finger. Greifer schließen und
öffnen für die Ansicht interpoliert. Die virtuelle Werkzeuglänge beträgt
wie im Quelllauf300mm ab`left_front_tool0`.

## Format und Zeitbezug

- 1920×1080, H.264/MP4 mit schneller Startwiedergabe.
- 15 unterschiedliche Zustände je Sekunde gespeicherter Ablaufzeit.
- Dieselben Bilder bei30fps exportiert: genau2× schneller, ohne künstliche
  Zwischenbilder. Etwa90,4s Video für180,7s Bahn-/Ansichtszeit.
- Alle54 Phasen ab Hub sowie gespeicherte gemeinsame Anfahrt und Einfahrt.
  Kurze Ansichtshalte am Anfang, beim Greifen/Öffnen und am Ende. Keine
  Berechnungswartezeiten aus dem ursprünglichen Versuch.
- Die tatsächliche Roboterplanung wird für das Video nicht umparametriert.

## Wiederholen

Aus dem Workspace ein neues Eingabeverzeichnis verwenden:

```bash
python3 src/multi_arm_manipulation_UWA/tools/carton_video/pack.py \
  --trial setup/tasks/house_drill_home_20261120_01 \
  --output setup/tasks/carton_video_repeat/input

python3 setup/titanpc/compute.py host-status
python3 setup/titanpc/compute.py submit \
  --image carton-render.sif --cpus 6 --memory-gib 12 --seconds 1200 \
  gpu carton-video-repeat-preview setup/tasks/carton_video_repeat/input \
  -- bash /input/run.bash preview
```

Nach Abschluss mit`compute.py fetch` abrufen und die17 JPEGs im
Unterordner`output/preview/` visuell prüfen. Für den vollständigen Export
einen neuen Job mit denselben Eingaben,1800s Zeitbudget und
`bash /input/run.bash full` starten. Dieser rendert ebenfalls die
Standbildübersicht einschließlich Dreh-/Rückfahrübergängen. Die Nahkamera
bleibt oberhalb der Tischplatte und außerhalb des Kartons. Erst nach
erfolgreichem Abschluss abrufen:

```bash
python3 setup/titanpc/compute.py fetch carton-video-repeat-final \
  setup/tasks/carton_video_repeat/result
```

Der eigene Container auf titanpc liegt unter
`/media/ubuntu22/RAID1_L/uwa-compute/images/carton-render.sif`.
Basis`planning.sif`, ergänzt um`ros-lyrical-gz-rendering-vendor`,
`ffmpeg`, `libegl1`, `libgl1-mesa-dri`. Rezept des ersten Aufbaus:
`setup/tasks/carton_video_20261124/render.def`; Containerhash beim Job.
Native Gazebo-Bibliotheken in der vorhandenen Lyrical-Umgebung, kein
Simulator- oder Controllerstart. EGL ermöglicht die Kamerabilder ohne
Desktop; siehe[Gazebo-Dokumentation](https://gazebosim.org/api/sim/7/headless_rendering.html).

## Nachweise und Grenzen

`provenance.json` bindet Originaldateien und die54 gespeicherten Bahnen per
SHA-256. Das Assetpaket enthält nur die benötigten visuellen Modelle und
Texturen. `movie.json` enthält alle Zustände, Spuren und Kameraphasen;
`video.json` enthält Kapitel, FPS, Laufzeit und Markierungsanzahl.
`ffprobe.json` bestätigt das tatsächliche Videoformat und die Bildanzahl.
Die Aufbereitung prüft, dass beide Haltearme dieselbe Objektposition ergeben;
das ersetzt keine bestehende Offline-Bahnprüfung.

Die Linien/Bohrmarken illustrieren die Werkzeugreferenz. Materialabtrag,
gemessene Strichqualität und reale Ausführung sind damit nicht nachgewiesen.
Rohpuffer der Kamerabilder werden nach erfolgreicher Kodierung und
Formatprüfung entfernt; Quellen, Posen, Stichproben und MP4 bleiben erhalten.
