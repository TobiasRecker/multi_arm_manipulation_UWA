# Greifadapter und Tischaufnahme für den COS-Whiteboardmarker

[CAD-Vorschau und Schnitt](vorschau.png) · [STEP-Baugruppe](marker-werkzeug.step)

Der Adapter klemmt den Stift am hinteren Ende in zwei Ebenen. Die
Stiftachse bleibt frei für eine axiale Entnahme von oben. Zwei flache
Flächen im Abstand von 34 mm nehmen die Backen des Robotiq 2F-85 auf.
Seitliche Leisten begrenzen das Verdrehen des Blocks in den Backen.
Die Klemmung der runden Stifthülse im Block beruht auf Reibung.

Der Fuß hat Ø64 mm und ist 102,5 mm hoch. Der Stift hängt darin nach
unten. Ein Trichter führt den Zapfen des Adapters in die Ablage. Eine
abgeschrägte Ecke legt die Orientierung fest. Der Anschlag trägt am
Adapter, die Stiftspitze behält nominell 5 mm Luft zum Boden. Zwei
Durchgangslöcher Ø4,5 mm im 50-mm-Raster dienen zur Befestigung an
einer geeigneten Unterlage. Der offene Ablageplatz ist für den
Arbeitszyklus gedacht. Für längere Lagerung bleibt die Originalkappe
erforderlich, damit der Stift nicht austrocknet.

## Druck, Montage und Abgleich

| Druckteil | Datei | Montage |
|---|---|---|
| Adapterhälfte mit Schraubenkopfsitzen | [STL](greifadapter-schraube.stl) | Vier M3 × 30 mm Zylinderkopfschrauben |
| Adapterhälfte mit Sechskanttaschen | [STL](greifadapter-mutter.stl) | Vier M3-Sechskantmuttern |
| Tischaufnahme | [STL](tischaufnahme.stl) | Zwei M4-Schrauben an geeigneter Unterlage |

1. Zuerst die beiden Adapterhälften drucken. Die STLs liegen mit der
   Außenfläche auf dem Bett, die Mulde ist offen nach oben. PETG ist
   ein Startmaterial. Slicer-Vorschau an Schraubentaschen und unter
   dem kurzen versetzten Zapfen kontrollieren und dort bei Bedarf
   lokale Stützen setzen. Zapfen und Greifflächen entgraten.
2. Den offenen Stift hinten bis zum inneren Anschlag einlegen und die
   Schrauben gleichmäßig anziehen. Zwischen den Hälften bleibt ein
   Spalt. Der Marker soll sich von Hand weder drehen noch längs
   verschieben lassen, ohne dass die Hülse sichtbar gequetscht wird.
   Falls er rutscht, Sitz und Durchmesser nachmessen und den
   Klemmsitz korrigieren.
3. Die Tischaufnahme aufrecht drucken und gegen Verschieben sichern.
   Den Adapter zuerst von Hand einsetzen. Die abgeflachte Ecke zeigt
   zur entsprechenden Ecke im Trichter. Korrekten Sitz und den
   Abstand der Spitze zum Boden mit dem echten Stift prüfen.
4. Für die spätere Aufnahme am Roboter die Greifhöhe so festlegen,
   dass die Backen in den Leisten sitzen und ihre Unterkanten über
   dem Rand der Aufnahme bleiben. Danach senkrecht ausheben, bis die
   Spitze komplett frei ist. Beim Absetzen senkrecht einfahren und
   erst am Sitzanschlag öffnen. Die reale Pose und Backenfreiheit
   vor einer automatischen Sequenz prüfen. Anschließend den
   TCP an der tatsächlichen Stiftspitze einmessen.

## Maße und Nachweis

- Nutzermaße am offenen Stift vom 19.11.2026. Ø20 mm bei 10 mm
  Abstand vom hinteren Ende, Ø19 mm bei 35 mm, Gesamtlänge etwa
  125 mm. Zwischen diesen Stationen ist ein leichter Konus
  angenommen. Für den unteren Schaft ist im Trichter und
  Schacht ein maximaler Ø21 mm als Modellannahme angesetzt.
- Für die Greifflächen ist eine **22 mm breite Standardbacke** aus
  der Robotiq-Zeichnung angenommen. Der lichte Abstand zwischen den
  Leisten beträgt 23,2 mm. Bei anderem Pad das tatsächlich montierte
  Maß prüfen und den Adapter neu exportieren.
  [Robotiq-Zeichnung, Fig. 6-14](https://assets.robotiq.com/website-assets/support_documents/document/2F-85_2F-140_Instruction_Manual_e-Series_PDF_20190315.pdf)
- Der Trichter erweitert den Einlauf um 4 mm pro Seite. Die trocken
  geprüfte CAD-Passung umfasst den lotrechten Aus-/Einzug und
  ausgewählte, zum Sitz hin korrigierte Versätze. Der um 180°
  gedrehte Adapter kann im CAD den Sitzanschlag nicht erreichen.
  Daraus folgt keine reale Einführ- oder Drehwinkeltoleranz für den
  Roboter. Druckpassung, Klemmsitz, Grifferreichbarkeit und
  Schreiblast sind noch praktisch zu prüfen.
- Der Produktlink bezeichnet die verwendete Stiftfamilie.
  [COS-Whiteboardmarker, 2 mm](https://www.cos.net.au/p/marker-whiteboard-bullet-cos-2mm-black-box-12-black)

## Export aus dem Workspace

Mit der vorhandenen OpenCascade-Umgebung neue Varianten erzeugen:

```bash
.venvs/oak-model/bin/python \
  src/multi_arm_manipulation_UWA/hardware/marker_tool/make_marker_tool.py \
  --d10 20 --d35 19 --length 125 --max-od 21 --pad-width 22 \
  --output /tmp/uwa-marker
```

STEP zeigt den montierten Adapter ohne Schrauben und Marker als drei
CAD-Körper. Die Vorschau zeigt die angenäherte Stiftkontur im Schnitt.
Die drei STL-Dateien sind einzeln in Drucklage und in Millimetern.
