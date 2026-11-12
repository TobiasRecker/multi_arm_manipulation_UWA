# Kalibrierung des UR5 vorne links

Stand: 2026-11-12, Australia/Perth. Arm `left_front`, UR5 CB3, Seriennummer
2017356443, PolyScope 3.15.8.106339. Die Ergebnisse sind separat gespeichert.

## Messung

- 41 reale VGA-Aufnahmen mit **640 × 480**; 33 Fit- und acht vorab reservierte
  Prüfbilder. Jede Aufnahme enthält alle 24 Ecken des festen linken ChArUco-
  Boards. Kein Fitbild ausgeschlossen, alle dekodierten Bilder verschieden.
- Kamera: eigener manueller Fokus **245**, Belichtung **60.590 µs**, Gain **19**.
  Aufnahme im überwachten Stillstand; HTTP-Empfangszeit ist keine Belichtungszeit.
  Gültig für diesen Bildmodus und Fokus. Kein HD-Ergebnis abgeleitet.
- Die freigegebenen 40 zusätzlichen Wege wurden nach dem Wechsel der OAK-Pose
  auf Modell v3 unverändert neu geprüft: 3.607 Punkte, alle vier Arme, ohne
  diagonale Ausnahme. Originalplan und neue Prüffassung separat erhalten.
  Die erste Flanschpose ist im Modell v3 identisch. Lokaler UDP-Transport nur
  für den Messclient löste die beobachteten Discovery-Probleme im Ablauf.

## Ergebnisse

| Prüfung | Ergebnis |
| --- | ---: |
| Intrinsics, Fit-RMS | 0,097 px |
| Intrinsics, medianer Prüf-RMS | 0,092 px |
| Hand-Auge, medianer Prüf-Reprojektionsfehler | 0,359 px |
| Boardpose, Prüf-Translationsstreuung | 0,543 mm |
| Boardpose, Prüf-Rotationsstreuung | 0,114° |

Beide Fits bestanden die unabhängigen Prüfungen. Für die relative Basislage
wurde das Nutzer-bestätigte unveränderte linke Board mit der validierten
Kalibrierung von hinten links verknüpft. Der Transform
`T_left_rear_base_link_from_left_front_base_link` hat im `left_rear_base_link`
Translation **[13,92; 1414,32; 0,62] mm** und XYZ-Eulerwinkel
**[−0,049; +0,124; +179,143]°**. Der Abstand der Basisursprünge beträgt
**1414,39 mm**. Das Bootstrap-Intervall **1413,26–1415,33 mm** beschreibt die
Wiederholbarkeit des Fits; eine absolute Genauigkeit wurde nicht vermessen.
Der Wert registriert die Zelle nicht im Weltkoordinatensystem.

## Ablage und Abschluss

`setup/calibration/hardware_handeye/left_front_20261112/series_current_model_checked/`
enthält Originale, markierte Bilder, Beobachtungen, Intrinsics, Hand-Auge,
relative Basispose, SHA256-Manifest und Bewegungsprotokoll. Beide Ergebnisse
wurden nicht als aktives Profil übernommen. Nach letzter Aufnahme: Safety
NORMAL, External Control verbunden, eigener Trajektoriencontroller inaktiv,
Endwinkelfehler 0,000091 rad; keine Rückfahrt.
