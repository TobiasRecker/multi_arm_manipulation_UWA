# Grobe OAK-Pose und gemeinsame Wrist-Sichtfelder

Stand: **2026-11-12**, Australia/Perth. Nutzerauftrag: erste OAK-Pose relativ
zum rechten Tisch schätzen und geeignete UR-Stellungen für freie Tischsicht und
geteilte Sichtbereiche finden. **Keine echten Arme bewegt.**

## Pose aus dem echten8K-Bild

Original `setup/oak4/captures/boards_20261112/rgb_full-sample.png`,8000×6000,
alle drei Boards mit17Markern/24Ecken erkannt. Factory-EEPROM der OAK238 rein
lesend ausgelesen: CAM_A/IMX586,Standard-K für4000×3000 auf8000×6000 skaliert,
volle14 Brown-/Rational-Verzeichnungskoeffizienten verwendet. Keine nominelle
Sichtfeldschätzung als gemessene Intrinsics ausgegeben.

PnP nutzt die24 metrischen inneren Ecken je Tischboard. Beide IPPE-Kandidaten
wurden geprüft und anhand positiver Tiefe und Bildfehler ausgewählt, danach
LM-Verfeinerung. Kein Ground-Truth-/Roboterpose-Prior für die Lösungsauswahl.

**Relativ zur Mitte der rechten Tischplatte**, mit X nach rechts, Y nach hinten,
Z nach oben, bei der bisherigen angenommenen Boardposition/-ausrichtung:

| Größe | Grobe Schätzung |
|---|---:|
| X | +0,806m |
| Y | +0,025m |
| Z über Tischplatte | +0,958m |
| Höhe über Boden bei0,90m Tischhöhe | 1,858m |
| Seitlicher Abstand außerhalb rechter Tischkante | 0,406m |
| Blickneigung unter Horizontale | 33,54° |

Die optische Achse trifft die Tischplattenebene ungefähr0,634m links und0,137m
hinter der rechten Tischmitte. Sie schaut damit über den Spalt zur linken Seite.
Optische Transformationen stehen in `setup/calibration/oak_pose_20261112/
pose_estimate.json` und im experimentellen
[Designprofil](../config/view_designs/oak_shared_views_20261112.yaml).

RechterBoard-Bildfehler1,708px, linker0,460px auf8000Pixel Bildbreite. Das linke
Board ergibt unabhängig0,960m Höhe und33,58° Neigung. Die beiden Boardposen
implizieren etwa0,959m seitlichen Abstand statt nominal0,90m; rund6cm sind
noch nicht in Tischbewegung versus Boardplatzierung auflösbar. **Keine Tisch-
oder Basisanker daraus verschoben.**

Das ist eine **grobe Einbildschätzung**, keine abgeschlossene OAK-Kalibrierung.
Die Factory-Kalibrierung gehört zur Linsenstellung116; der Autofokuswert des
ursprünglichen Fotos wurde nicht protokolliert. ±2% angenommene Brennweite
ändern die geschätzte Höhe über der Tischplatte hier um ungefähr±1,8cm.
Ein0,5px-Eckenrauschtest ergibt nur etwa1mm interne Streuung, deckt aber weder
Fokus-/Intrinsicsfehler noch Boardplanheit/Boardlage ab und ist keine absolute
Genauigkeit. Die Tischhöhe bleibt ebenfalls eine Annahme.

## Gefundene Beobachtungsstellungen

Die Suche verwendet das aktuelle gemeinsame Modell `hardware_20261112_v2`:
linke/rechteRear-Optik validiert, Front-HD auf separaten ausdrücklichen
Nutzerauftrag trotz nicht bestandener automatischer Qualitätsgrenzen übernommen,
links vorne nominelle Optik. Dieses Profil wurde durch diese Aufgabe nicht geändert.
Die drei erreichbaren Arme wurden nur gelesen; links vorne ist weiterhin die
bestätigte nominelleHome-Angabe, keine Encodermessung.

Die Kameras stehen an vorderer/hinterer Tischseite, schauen zur jeweiligen
Board-/Tischmitte und halten die Mitte möglichst frei. Gleichwertige Bildrotationen
wurden zugelassen, um zusätzliche Wrist-Umdrehungen zu vermeiden. Entwurfspräferenz:
Wrist2 innerhalb±180°, Wrist3 höchstens90° Änderung zum Ausgangsstand. Das sind
Suchpräferenzen, keine neuen GUI-/UR-Sicherheitsgrenzen.

| Arm | Kamera X/Y/Z im vorläufigen Weltmodell [m] | Gemeinsam freie Tischfläche mit OAK, ungefähr |
|---|---|---:|
| left_front | −0,691 / −0,493 / 1,351 | 0,59m² |
| left_rear | −0,331 / +0,627 / 1,501 | 0,70m² |
| right_front | +0,630 / −0,620 / 1,503 | 0,97m² |
| right_rear | +0,270 / +0,500 / 1,503 | 0,77m² |

- Vierarm-Zielzustand vollständig mit MoveIt kollisionsgeprüft, ohne diagonale
  Kollisionsausnahmen. Jede Wrist sieht im Modell24/24 eigeneBoard-Ecken;
  die OAK sieht beide Tischboards mit48/48Ecken.
- Konservativer Vergleich mit lokalen Bounding-Boxen der URDF-Kollisionsmeshes,
  einschließlich Greifer/Wrists,5mm Kameranahbereich: ungefähr **54%→78%** der
  gesamten Tischfläche sind zugleich im OAK-Bild und nicht von Modellarmen verdeckt.
  Das ist keine gemessene Pixel-Verdeckungsquote. Das echteFoto erkannte bereits
  alle48 Tischboard-Ecken; die konservative Ausgangsschätzung zählte47.
- Für ein horizontales mobiles266×190mm-Muster wurden proWrist54 Kandidaten
  auf dem eigenen Tisch geprüft,8/16/24cm über der Platte. Muster vollständig
  in OAK und Wrist sowie ohne modellierte Armverdeckung:11/28/39/28 Kandidaten
  in obiger Armreihenfolge. Holz-/Papierrand ist nicht enthalten, andere Neigungen
  und tatsächliche Erkennung sind vor einer Kalibrierreihe noch zu prüfen.
- Serielle Modellverbindungen in Reihenfolge left_front→left_rear→right_rear→
  right_front vollständig gesampelt geprüft:959/413/927/1386 Zustände,
  maximal0,005rad Gelenkschritt,0,05rad/s,0,10rad/s²; zusammen367,9s reine
  Modellbewegung. **Kein ausführbarer Hardwareauftrag:** links vorne ohne
  Live-Zustand, Montagegeometrie noch vorläufig. Vor jeder echten Fahrt frische
  Zustände, konkrete Wegvorschau und tatsächlichen freien Bereich prüfen.

Keine Kabel, Menschen, lose Gegenstände oder Stativkollisionen werden modelliert.
Die Sichtbewertung ersetzt weder echte Bilder in den Zielstellungen noch eine
metrische Registrierung der ganzen Zelle.

## Vorschau und Wiederholung

Die geöffnete RViz-Vorschau ist **statisch und isoliert auf Domain70**, ohne
Hardwareclients. Rot: grobe OAK-Lage/Blickachse, gestrichelt: Wrist-Blickrichtungen,
grün: aus dem Foto bestimmteBoard-Umrisse. Keine realen Joint-/TF-Topics verändert.

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 -m uwa_cell_control.oak_view_preview \
  --source setup/calibration/oak_pose_20261112 \
  --proposal setup/calibration/oak_pose_20261112/design_wrist/proposal.json
```

Vergleichsbild, optionale separate Simulations-YAML und alle Zahlen:
`setup/calibration/oak_pose_20261112/design_wrist/` mit
`configuration_comparison.png`, `layout_proposal.yaml`, `proposal.json`,
`connections.json`, `shared_mobile_board.json`. Die optionale YAML setzt
Initialstellungen **nur bei eigenem Simulationsstart**; sie ist kein globaler
Standard und wurde nicht auf eine laufende Simulation angewendet.

Reproduzierbare Suche mit denselben eingefrorenen Modell-/Zustandsdaten:

```bash
python3 -m uwa_cell_control.oak_view_design \
  --source setup/calibration/oak_pose_20261112 \
  --output /tmp/uwa_oak_view_design
```

Fünf gezielte Geometrieprüfungen bestanden: endliche Sichtstrahlen, gedrehte/
verschobene Geometrie, Nahbereich, Punkte hinter der Kamera und optische
Transformationskonvention. Keine breiten Hardwaretests und keine Bewegung.
