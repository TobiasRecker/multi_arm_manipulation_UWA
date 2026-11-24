# ChArUco-Neudruck: Größe und Muster

- Status: Beratung abgeschlossen, 24.11.2026 (Australia/Perth), Hauptagent dieses Chats.
- Nutzerauftrag: bisherige zwei feste A3-Boards und mobiles A4-Board für
  professionellen Druck beurteilen; Außenmaß, Musterfläche, Feld-/Markermaß
  und Pattern empfehlen. Freie Formate einschließlich größerer Platten erlaubt.
- Bereiche: lesende Bestands-/Kameraprüfung; anschließend dieser Nachweis und
  `HANDOVER.md`. Bestehende Konfigurationen und Kalibrierprofile erhalten.
- Keine Kamera-/Roboteraktion oder Dienstneustarts vorgesehen.
- Bestand: feste Muster280×200mm (7×5,40/28mm), mobil266×190mm
  (7×5,38/28mm), alle DICT_4X4_100. A3 ist das bisherige Papierformat,
  nicht die aktive Mustergröße.
- Ergebnis: bevorzugter Entwurf, kein nachgewiesenes globales Optimum und noch
  keine bestätigte Nutzerentscheidung zum Austausch.

## Empfohlene Auslegung

| Merkmal | Zwei feste Boards, jeweils | Mobiles Board |
|---|---:|---:|
| Plattenaußenmaß | 550×400mm | 450×360mm |
| Aktive Musterfläche | 500×350mm | 405×315mm |
| Anzahl Schachbrettfelder | 10×7 | 9×7 |
| Feldkante | 50mm | 45mm |
| Markerkante inkl. schwarzem Ein-Modul-Rand | 36mm | 33mm |
| Gleichmäßiger weißer Außenrand | 25mm | 22,5mm |
| Marker / innere ChArUco-Ecken | 35 / 54 | 31 / 48 |

DICT_5X5_250 als Ingenieurkompromiss:101Marker für alle drei Boards benötigen
mehr als100IDs; gleichzeitig bleibt beim mobilen Board das physische Modulmaß
33/7=4,71mm ungefähr beim bisherigen28/6=4,67mm. Bei6×6Bits und gleicher
Markerkante würden die Module kleiner. Größere Bitmuster ermöglichen andere
Codeabstände, erfordern aber mehr Bildauflösung; keine gemessene Überlegenheit
von5×5behaupten. ID-Bereiche und vollständige OpenCV-Mustergeometrie vor
neuen Druckdaten versionieren. Alte4×4Stiftmarker92–99 separat erhalten.

## Quellen und kurze Modellprojektion

- Feste Definition: `uwa_cell_description/config/cell_layout.yaml`, `charuco`;
  Erklärung `docs/charuco_calibration.md`. Mobil:
  `uwa_cell_description/config/mobile_charuco_a4.yaml` und
  `docs/mobile_charuco_a4.md`. Alle alten Boards17Marker/24Ecken.
- Externe Posen/K/D vom23.11.:
  `../../setup/calibration/external_pair_20261123/external_camera_poses.json`,
  `lenses`, `T_right_charuco_oak4`, `T_right_charuco_oak_usb`,
  `T_right_charuco_left_charuco`. OAK48000×6000/Fokus107,
  USB4056×3040/Fokus112. Bestehende Mustermittelpunkte erhalten, neue
  Platten-/Musterecken mit `cv2.projectPoints` und gespeicherten K/D projiziert.
  Minimaler nativer Bildrandabstand der550×400mm-Platte:
  OAK4 rechts387px/links1700px, USB rechts171px/links91px.
  Die600×450mm-Platte lässt USB links nur etwa9px Reserve.
  Dies ist eine kurze Modellrechnung ohne neue Aufnahme oder Verdeckungsprüfung.
- Vier Wrists: `../../setup/calibration/mobile_volume_20261123/proposal.json`,
  `selected.*.camera_world` und `optics`;2592×1944, f etwa2609–2688px,
  Abstand zur Mitte etwa1,294m. Analog `tools/design_calibration_volume.py`
  die450×360mm-Platte über eine288,1mm-Umkugel und26Richtungen angenähert.
  Bei Boardmitte world=(0,0,1.28)m mindestens353px Randreserve, bei z1,40m
  mindestens77px. Bei z1,45m ragt die konservative Umkugel um etwa2–29px
  aus den Bildern. Kein kontinuierlicher Sichtnachweis; der alte Quader
  für A4 gilt für diesen Entwurf nicht unverändert.
- Grobe Markerprojektion im Zentrum:
  `0.9*f_min*0.033*cos(45deg)/1.294 ≈ 42px`, etwa6px je5×5-Modul
  einschließlich schwarzem Rand. Schärfe, Fokus, Belichtung und reale
  Erkennung sind dadurch nicht bewiesen.

## Druck und Referenzübertragung

Plane, steife Aluverbundplatte als praktikabler Vorschlag, etwa4–6mm je nach
Größe/Aufbau, matte reflexarme Oberfläche, Maßhaltigkeit in beiden Achsen und
Ebenheit vom Hersteller angeben lassen. Druck aus Vektordaten1:1, keine
Anpassung an ein Papierformat; weiße Ränder und Kontrollstrecken außerhalb
des Musters erhalten. Musterfläche, nicht nur Zuschnitt vermessen.

Für das tatsächliche Genauigkeitsziel keine unbelegte Fertigungstoleranz
vorgeben. Vor Bestellung verfügbaren Tischplatz, Sicht und mögliche Verdeckung
bei der vorgesehenen Lage prüfen. Beim Austausch den neuen Musterursprung
und die bedruckte Oberflächenhöhe auf die bestehende Tischreferenz übertragen;
die übernommenen Armbasisbindungen nicht pauschal neu untersuchen.

Primärquellen, abgerufen24.11.2026:

- [OpenCV ChArUco](https://docs.opencv.org/4.13.0/df/d4a/tutorial_charuco_detection.html):
  Teilansichten, Schachbrettecken und Abstand Marker zu Feldrand.
- [OpenCV Wörterbuchwahl](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html):
  Codeabstand, Anzahl IDs und Auflösungsbedarf gegeneinander abwägen.
- [Calib.io Best Practices](https://calib.io/blogs/knowledge-base/calibration-best-practices):
  Arbeitsabstand, Punktdichte, Neigungen und Qualität der Kalibrierfläche.
- [Calib.io Targetfertigung](https://calib.io/products/charuco-targets):
  matte präzise bedruckte Aluverbundplatten als industrielles Beispiel.

Keine Druckdatei erstellt, keine Bestellung, Profilaktivierung oder Hardware-
aktion. Nur Arbeitsnachweis, AGENTS.md und HANDOVER.md ergänzt.
