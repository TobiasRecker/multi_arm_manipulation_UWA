# Vier URs fahren die Seitenmitten des Avocado-Kartons an

[Neue Vorschau öffnen](../../../setup/research/offline-carton-sides-20261117/standard/viewer.html).
Standard ist die geglättete Trajektorie mit Echtzeitwiedergabe. Oben zeigen
Tabelle und Draufsicht die eindeutige Zuordnung der vier Seiten A–D;
**Play preview** startet die Bewegung, der Zeitschieber zeigt Zwischenstellungen.
Die Seitenbuchstaben erscheinen auch an den festen TCP-Zielen in der 3D-Ansicht.

## Aufgabe und Zuordnung

Nutzerauftrag vom 17. November 2026: dieselbe Kiste und derselbe aufrechte
Start wie beim Eckfall, jetzt jeweils mittig an einer Seitenwand anfahren.
Anflug weiterhin senkrecht von oben, 120 mm Voranflug, nominaler TCP 15 mm
unter der Oberkante. Die Backenschließrichtung liegt quer zur Wand. Es wird
nur bis zur offenen Greifpose geplant, nicht geschlossen oder angehoben.

Eine einfache Vergabe an das jeweils nächste freie Roboter-Seiten-Paar
verdrängte left_front auf Rang 3; dafür wurden keine IK-Kandidaten gefunden.
Dieser negative Vorversuch bleibt unter `primitive/` erhalten. Die endgültige
Zuordnung betrachtet deshalb alle eindeutigen Belegungen innerhalb der
**je zwei nächstgelegenen Seiten** und minimiert die Summe horizontaler
Basis-Seiten-Abstände. So erhält jeder tatsächlich seine erste oder zweite Wahl.
Dies optimiert eine Zuordnung, nicht die Trajektoriendauer.

| UR | Seite im Kartonframe | Präferenz | Horizontaler Basisabstand |
|---|---|---|---:|
| left_front | A, x_min | nächste | 712 mm |
| left_rear | D, y_max | zweitnächste | 757 mm |
| right_front | C, y_min | zweitnächste | 741 mm |
| right_rear | B, x_max | nächste | 656 mm |

Zielpose und Zuordnung bleiben über die IK-Alternativen hinweg fest.
12 IK-Kandidaten je Arm, 20.736 Kombinationen vollständig innerhalb dieser
begrenzten Kandidatenmenge geprüft: 315 geometrisch gültige Endstellungen,
10 gültige Einzelwege (2/2/3/3), 36 kompatible Wegkombinationen.
Empfohlen: `goal-0-2-3-0`. Keine Vollständigkeit der IK-Suche behauptet.

## Ergebnis

| Größe | Seitenanflug, geglättet |
|---|---:|
| Zeit bis alle vier ankommen | **12,746 s** |
| Geschwindigkeitsobergrenze | 0,450 rad/s |
| Beschleunigungsobergrenze | 0,400 rad/s² |
| Ruckobergrenze | 1,105 rad/s³ |
| Kleinster geprüfter Armhüllabstand | **53,697 mm** |

Der [geglättete Eckfall](offline_carton_smoothing.md) dauerte 15,995 s bei
155,147 mm Mindestabstand. Der Seitenfall ist damit enger, aber kürzer;
schwierigere Kollisionsgeometrie bedeutet nicht automatisch längere Bewegung.
Der zusätzliche 10×-Vergleich im neuen Viewer bezieht sich auf dieselben
Seitenwege: 15,478 s, a≤1,451 rad/s², Ruck≤12,188 rad/s³.

Die Gelenkgeraden bleiben beim Glätten exakt erhalten. Maximale gemessene
TCP-Bahnänderung des quintischen gegenüber dem kubischen Anflugspline:
0,000640 mm im Modell. Das ist keine physische Positioniergenauigkeit.
Zwischenstopp vor dem senkrechten Anflug bleibt erhalten; v/a/Ruck sind dort null.

32.008 isolierte Prüfstellungen und 1.276 gemeinsame Zeitpunkte (≤10 ms)
ohne geometrische Kollision oder Unterschreitung der statischen 20-mm-Paarreserve.
Nachprüfung: 2.551 gemeinsame Zeitpunkte (≤5 ms), alle sechs Armpaare, volle
FCL-Szene, max. Gelenkschritt 0,002250 rad; ebenfalls bestanden.
Unabhängige Zeitgesetzrekonstruktion an 800.008 Punkten bestätigt die
Ableitungsgrenzen; Spitzen v/a/Ruck: 0,450/0,400/0,791.

## Geometrie und Bremsreserve getrennt

Der Vorversuch mit der ursprünglichen Zielauswahl (`case02/`) verwarf alle
20.736 Kombinationen bereits wegen der pauschalen Bremsreserve. Die erlaubte
Geometrie war damit noch nicht geprüft. Für diesen Offline-Anfahrtest verwendet
die Zielauswahl ausdrücklich `static_margin`: mindestens 20 mm für alle sechs
Paare und volle Szenenkollision. Der bisherige Modus `stop_reserve` bleibt
verfügbar; aktive Simulations-/Hardwarekonfigurationen wurden nicht verändert.

Die unveränderte dynamische Reserve wird anschließend separat ausgewertet:
1.145/1.276 Zeitpunkte überschreiten sie. Auch im Stillstand fordert die alte
Betriebsgeschwindigkeitsuntergrenze bei Nachbarpaaren etwa 196–199 mm. Orange
ist deshalb eine Bremsreservediagnose, kein festgestellter geometrischer Kontakt.
Dieser Versuch ist **keine Freigabe unter jener Bremsreserve**.

Alle Aussagen gelten für diskrete Kinematikprüfung im vorhandenen Modell,
mit festen Basen und offenen Greifern. Kein kontinuierlicher Kollisionsbeweis,
keine Kontaktphysik, keine native MoveJ/MoveL- oder Hardwareausführung.
Kalibrierung, Lasten, Tracking und reale Stoppeigenschaften bleiben unqualifiziert.

## Glättung als Standard

Neuer gemeinsamer Einstieg für weitere Eck- und Seitenanflüge:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/plan_carton_grasp_paths.py \
  --grasp-pattern sides \
  --layout setup/research/offline-carton-paths-20261117/case03/layout.yaml \
  --config setup/research/offline-carton-paths-20261117/case03/motion.yaml \
  --output-dir /tmp/uwa-carton-side-test
xdg-open /tmp/uwa-carton-side-test/viewer.html
```

Für Ecken `--grasp-pattern corners`. Der Einstieg erzeugt immer geglättete
Trajektorien und führt die dichte Nachprüfung aus. Die langsamen Primitive
und der 10×-Fall bleiben als Vergleichsdaten erhalten. Der historische
`plan_carton_corner_paths.py` ist nur noch die Primitive-Stufe dieser Pipeline.
Die Entwurfsgrenzen 0,45 rad/s, 0,4 rad/s² und 2 rad/s³ bleiben Modellwerte.
Unabhängiges Retiming gilt nur vor einem bestätigten tragenden Greifverbund.

Build, 31 gezielte Tests und 20 Browserfälle bestanden. Ansicht mit Draufsicht
und Endstellung visuell kontrolliert. Vollständiger Standardlauf einschließlich
Nachprüfung unter `setup/research/offline-carton-sides-20261117/standard/`;
Ergebnisse `smoothed/result.json`, `smoothed/verification.json`, `run.json`.
Vorversuche und erste erfolgreiche Auswertung bleiben daneben erhalten.
Logs unter `setup/logs/uwa-carton-sides-*`.
