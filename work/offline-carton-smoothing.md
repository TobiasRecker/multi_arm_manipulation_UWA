# Glattere Zeitgesetze für alle vier Eckanflüge

- Status: abgeschlossen, 2026-11-17 (Australia/Perth), Hauptagent.
- Nutzer bestätigt alle vier URs. Geschwindigkeit aus10×Vergleich grundsätzlich
  okay; Beschleunigung/Ruck reduzieren, geometrische Wege möglichst erhalten.
- Ansatz: neue glatte Beschleunigungs-/Konstantfahrt-/Bremszeitgesetze entlang
  derselben Kurven. Kein Verschieben der Eckziele. Relative Zeitabläufe können
  sich ändern, daher erneute gemeinsame Geometrieprüfung erforderlich.
- Eigenes Motionmodul/Tests, Auswertung/Viewer, neuer Forschungsordner und
  Dokumentation. Alte Beispiele, parallele Arbeiten/Dienste erhalten.
  Nur offline, keine Hardware-/Kontakt-/ROS-Knotenaktion.
- Ergebnis: 15,995 statt 22,067 s; analytische Obergrenzen
  v=0,450 rad/s, a=0,400 rad/s², Ruck=1,085 rad/s³.
  Gelenkgeraden exakt erhalten, maximal gemessene TCP-Bahnänderung
  0,000508 mm durch quintische statt kubische Anfluginterpolation im Modell.
- 32.008 isolierte Prüfstellungen und 1.601 gemeinsame Zeitschritte ohne
  geometrische Kollision; min. Armhüllabstand 155,147 mm. Dynamische
  Reservediagnose weiterhin verletzt (1.297/1.601), keine Hardwarequalifikation.
- Build, 25 gezielte Tests, unabhängige 800.008-Punkte-Nachrechnung und
  15 Browserfälle bestanden; Vorschau/Kurven visuell geprüft.
- Anleitung: [offline_carton_smoothing.md](../docs/offline_carton_smoothing.md).
  Artefakte: setup/research/offline-carton-smoothing-20261117/.
