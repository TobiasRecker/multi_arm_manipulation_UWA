# Mobiles A4-ChArUco-Board fuer externe Kameras

- Status: **abgeschlossen**,2026-11-11, Druckvorlage erstellt und geprüft.
- Nutzer hat ein am UR montierbares A4-Holzboard. Papier soll plan aufgeklebt
  werden; Muster soll moeglichst gross auf A4 sein. Eigenes mobiles Board fuer
  spaetere externe OAK-Einmessung, bestehende Tischboards erhalten.
- Umgesetzt: A4 quer,7x5 Felder38mm, Marker28mm, Muster266x190mm,
  weisser Rand15,5mm seitlich/10mm oben-unten. DICT_4X4_100,IDs75…91,
  getrennt von Tischboards0…16/50…66.100mm Kontrollstrecke seitlich.
- Bereiche: eigener Druckgenerator, eigene Board-YAML, PDF/Pruefbericht und
  Dokumentation. Keine Kamera-/Robotereinstellungen, keine Dienste/Bewegung.
- Pruefung: metrische PDF-Geometrie, Rasterrender/Sichtpruefung, Wiedererkennung
  aller Marker/ChArUco-Ecken aus dem tatsaechlich gerenderten PDF.
- Ergebnis:17/17 Marker,24/24 Ecken; maximal0,082mm Raster-Eckabweichung.
  Vektor-PDF einseitigA4,38mm-Felder und100mm-Strecke geprueft. Report:
  `docs/mobile_charuco_a4_print_validation_2026-11-11.json`.
- Lieferung `output/pdf/uwa_mobile_charuco_A4_1to1.pdf`, eigene YAML und
  Generator; Anleitung `docs/mobile_charuco_a4.md`. Physischer Ausdruck und
  Werkzeug-Board-Montage noch nicht vermessen/kalibriert. Keine Hardwareaktion.
