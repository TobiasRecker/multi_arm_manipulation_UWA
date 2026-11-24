# ChArUco PRO v1 - Druckdaten

Am 24.11.2026 vom Nutzer beauftragte neue Druckgeneration. Die Dateien sind
getrennt von den bisherigen A3-/A4-Boards und den aktiven Kalibrierprofilen.

## Dateien und Maße

| Board | PDF unter `output/pdf/` | Plattenmaß | Muster | Feld / Marker | IDs |
|---|---|---|---|---|---|
| Tisch links | `uwa_charuco_table_left_550x400mm_1to1.pdf` | 550 x 400 mm | 10 x 7 Felder, 500 x 350 mm | 50 / 36 mm | 0-34 |
| Tisch rechts | `uwa_charuco_table_right_550x400mm_1to1.pdf` | 550 x 400 mm | 10 x 7 Felder, 500 x 350 mm | 50 / 36 mm | 50-84 |
| Mobil | `uwa_charuco_mobile_450x360mm_1to1.pdf` | 450 x 360 mm | 9 x 7 Felder, 405 x 315 mm | 45 / 33 mm | 100-130 |

Alle drei verwenden **DICT_5X5_250**, einen schwarzen Rand von einem Modul,
`legacy_pattern=false` und oben links ein schwarzes Schachbrettfeld.
Markermaß bezeichnet die schwarze Außenkante einschließlich schwarzem Rand.
Die beiden festen Boards haben jeweils 35 Marker und 54 innere ChArUco-Ecken;
mobil sind es 31 Marker und 48 Ecken. Keine ID wird innerhalb dieser Generation
auf mehreren Boards verwendet.

## An den Druckservice

- Jedes PDF ist genau eine Seite im endgültigen Plattenformat, einschließlich
  Außenrand. **1:1 / 100 Prozent / tatsächliche Größe** drucken.
- Keine Anpassung an DIN-Papiergrößen, keine Skalierung oder Verzerrung.
  Die PDF-Seitenkante ist die Zuschnittkante. MediaBox, CropBox, TrimBox und
  BleedBox entsprechen dem vollständigen Plattenformat.
- Muster nicht beschneiden. Gleichmäßiger Außenrand: 25 mm fest,
  22,5 mm mobil. Kleine Kennungen und Kontrollstrecken liegen im äußeren Rand;
  die inneren 10 mm neben dem Muster bleiben frei.
- Schwarz-Weiß-Vektordruck auf einer matten, reflexarmen, dauerhaft planen und
  steifen Platte, beispielsweise Aluverbund. Schriftarten sind eingebettet;
  Muster und Kontrollstrecken bestehen aus Vektoren.
- Tatsächliche Maßhaltigkeit in X und Y sowie Ebenheit vom Hersteller nennen
  lassen. Die 100-mm-Kontrollstrecken in beiden Achsen und das Muster nach
  Fertigung nachmessen. Der digitale Nachweis ersetzt diese Prüfung nicht.

## Definition, Reproduktion und Prüfung

Quelle: `config/print_designs/charuco_professional_v1.json`. Das ist eine eigene
Druckdefinition und keine aktive Runtime- oder Kalibrierkonfiguration.

Aus `~/UWA_ws`:

```bash
.venvs/charuco-print/bin/python src/multi_arm_manipulation_UWA/scripts/print_professional_charuco.py
.venvs/charuco-print/bin/python src/multi_arm_manipulation_UWA/scripts/validate_professional_charuco.py
```

`output/pdf/uwa_charuco_professional_v1_manifest.json` bindet Maße, IDs und
Dateihashes. Der unabhängige PDF-Prüfer rendert die fertigen PDFs mit Poppler
bei 300 dpi und prüft Seitenformat, Vektorausgabe, vollständige Marker- und
ChArUco-Erkennung sowie die metrische Geometrie. Ergebnis:
`output/pdf/uwa_charuco_professional_v1_validation.json`.

Die PDF-Erzeugung verwendet sieben Quellpixel pro Millimeter und führt die
binären Flächen verlustfrei in Vektorrechtecke über. Damit liegen Feldkanten,
Markerkanten, Markerzentrierung und alle sieben Markermodule exakt auf dem
Quellraster; es entsteht keine Rundung unterschiedlich breiter Module.

Die PDF-Seitendarstellung wird zusätzlich visuell geprüft. Die digitale Prüfung
belegt keine reale Kameraerkennung, Plattenebenheit oder absolute Messgenauigkeit.

## Späterer Einbau

Die bisherigen Boards und die aktiven Basis-/Kamerareferenzen bleiben erhalten.
Vor einem physischen Austausch den neuen Musterursprung und die bedruckte
Oberflächenhöhe auf den bisherigen Tischbezug übertragen und die passende
neue Boarddefinition im Auswertepfad verwenden. Die größeren mobilen Abmessungen
verkleinern den alten A4-Bewegungsbereich. Entwurfsbegründung und Modellgrenzen:
`work/charuco-professional-print-20261124.md`.
