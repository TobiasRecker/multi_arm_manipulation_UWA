# Mobiles A4-ChArUco-Board fuer externe Kameras

- Status: **in Arbeit**,2026-11-11, Hauptaufgabe.
- Nutzer hat ein am UR montierbares A4-Holzboard. Papier soll plan aufgeklebt
  werden; Muster soll moeglichst gross auf A4 sein. Eigenes mobiles Board fuer
  spaetere externe OAK-Einmessung, bestehende Tischboards erhalten.
- Vorschlag: A4 quer,7x5 Felder38mm, Marker28mm, Muster266x190mm,
  weisser Rand15,5mm seitlich/10mm oben-unten. DICT_4X4_100,IDs75…91,
  getrennt von Tischboards0…16/50…66.100mm Kontrollstrecke seitlich.
- Bereiche: eigener Druckgenerator, eigene Board-YAML, PDF/Pruefbericht und
  Dokumentation. Keine Kamera-/Robotereinstellungen, keine Dienste/Bewegung.
- Pruefung: metrische PDF-Geometrie, Rasterrender/Sichtpruefung, Wiedererkennung
  aller Marker/ChArUco-Ecken aus dem tatsaechlich gerenderten PDF.
