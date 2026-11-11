# Mobiles A4-ChArUco-Board

Stand2026-11-11: separates, am UR montierbares Ziel für die spätere Einmessung
der externen OAK-Kamera. Papier wird auf einen A4-Holzträger geklebt.

[Druckvorlage](../output/pdf/uwa_mobile_charuco_A4_1to1.pdf) auf **A4 quer mit
100% / Tatsächliche Größe** drucken. „An Seite anpassen“ deaktivieren. Die PDF
fordert keine Skalierung an; der Druckdialog kann diese Einstellung überschreiben.
Nach dem Druck die **100mm-Kontrollstrecke** und eine **38mm-Feldkante** messen.
Bei falschem Maß den Druck korrigieren; nicht mit den nominellen Maßen auswerten.

Mattes Papier vollflächig, eben und ohne Falten oder Blasen aufkleben. Den weißen
Rand erhalten, Halter/Klemmen außerhalb des Musters anbringen. Glänzendes
Klebeband über dem Muster vermeiden. Nach dem Kleben erneut Maße und Ebenheit
prüfen. Die Holzplatte muss für die spätere Kalibrierung starr bleiben.

| Parameter | Wert |
|---|---|
| Papier | A4 quer,297×210mm |
| Muster | 7×5 Felder,266×190mm |
| Feldkante | 38mm |
| Marker-Außenkante inklusive schwarzem Rand | 28mm |
| Dictionary | `DICT_4X4_100` |
| Marker-IDs | 75–91,17 Marker |
| Innere ChArUco-Ecken | 24 |
| Marker-Rand / Legacy-Muster | 1Bit / aus |
| Weißrand | links/rechts15,5mm, oben/unten10mm |

Die zentrale [Board-Definition](../uwa_cell_description/config/mobile_charuco_a4.yaml)
gehört genau zu dieser Vorlage. Das Muster ist **kein verkleinerter Ersatz** für
die fest montierten Tischboards mit40mm-Feldern und IDs0–16 bzw.50–66.
Ein Detektor für dieses mobile Board muss seine eigene Definition laden;
bestehende Tischdetektoren wurden nicht umgeschaltet.

Der Board-Frame beginnt an der linken oberen Musterecke ohne Papier-Rand:
X nach rechts, Y nach unten, Z in die Platte. Die Werkzeug-Board-Transformation
ist noch unbekannt. Eine gedruckte Vorlage liefert noch keine Kameraextrinsics
oder kalibrierte Robotermontage.

Reproduzieren im Workspace mit der eingerichteten Druckumgebung:

```bash
cd ~/UWA_ws
.venvs/charuco-print/bin/python src/multi_arm_manipulation_UWA/scripts/print_mobile_charuco.py
```

Der Generator benötigt OpenCV mit ArUco, NumPy, PyYAML und ReportLab; er greift
weder auf ROS noch auf Roboter/Kameras zu. Neben der Vektor-PDF entsteht ein
JSON-Manifest mit Parametern und SHA256. Die digitale
[Prüfung](mobile_charuco_a4_print_validation_2026-11-11.json) bestätigt die
PDF-Abmessungen und die Erkennung aller17 Marker/24 Ecken im300-dpi-Render.
Der physische Ausdruck ist damit noch nicht vermessen.
