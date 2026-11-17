# Glattere Trajektorien für alle vier Eckanflüge

[Interaktiven Vergleich öffnen](../../../setup/research/offline-carton-smoothing-20261117/viewer.html).
**Trajectory timing** wechselt zwischen dem bisherigen 10×-Fall und dem neuen
Verlauf. **Playback** steht auf Echtzeit. **Compare velocity, acceleration and
jerk over time** öffnet die Kurven: Gold = bisher, Blau = geglättet.
Die Kurven zeigen den jeweils größten Betrag über alle 24 Gelenke.

## Ergebnis vom 17. November 2026

Alle vier URs fahren weiterhin zu denselben Ecken des Avocado-Kartons.
Die Gesamtdauer sinkt um 27,5 %, bei praktisch gleicher Höchstgeschwindigkeit.
Die folgenden Ableitungswerte sind konservative analytische Obergrenzen der
geplanten Kurven, keine gemessenen Motorwerte:

| Größe | Bisheriger 10×-Fall | Geglättet |
|---|---:|---:|
| Gesamtdauer | 22,067 s | 15,995 s |
| Gelenkgeschwindigkeit | ≤0,454584 rad/s | ≤0,450000 rad/s |
| Gelenkbeschleunigung | ≤1,223044 rad/s² | ≤0,400000 rad/s² |
| Gelenkruck | ≤10,085925 rad/s³ | ≤1,084747 rad/s³ |

Die Gelenkgeraden bleiben geometrisch exakt erhalten. Im senkrechten Anflug
ersetzt ein quintischer interpolierender B-Spline den bisherigen kubischen
Gelenkspline; sämtliche IK-Stützstellen bleiben erhalten. Im dichten Vergleich
bei gleichem Bahnparameter beträgt die größte TCP-Abweichung **0,000508 mm**,
die größte Gelenkabweichung 1,5911e−6 rad. Das beschreibt nur den Unterschied
zweier Modellkurven, keine erreichbare Genauigkeit des realen Roboters.

## Weshalb gleichzeitig schneller und sanfter?

Der bisherige Verlauf verteilt Beschleunigung und Bremsung über den ganzen
Gelenkweg, erreicht die Spitzengeschwindigkeit nur kurz und erzeugt hohe
Ableitungsspitzen im kurzen senkrechten Schlussanflug. Das neue Zeitgesetz
nutzt glatte Rampen und längere Konstantfahrt auf den großen Gelenkwegen;
für den Schlussanflug nimmt es sich mehr Zeit. Die Beschleunigung wird dabei
nicht an jedem einzelnen Punkt kleiner: Auf den langen Wegen wird teils
kräftiger beschleunigt, während die globalen Spitzen deutlich sinken.

Geschwindigkeit, Beschleunigung und Ruck sind an Rampenübergängen stetig und
an den Abschnittsenden null. Der vollständige Zwischenstopp vor dem senkrechten
Anflug bleibt bestehen. Ohne Halt über dessen geometrischen Knick zu fahren
würde eine zusätzliche räumliche Verrundung erfordern.

Verwendete Vergleichsgrenzen: 0,45 rad/s, 0,40 rad/s² und 2,0 rad/s³.
Dies sind gewählte Entwurfswerte, keine identifizierten Hardwaregrenzen und
keine Behauptung einer zeitoptimalen Lösung. Die neue Dauer je Arm ist:
left_front 15,995 s, left_rear 9,107 s, right_front 12,353 s,
right_rear 8,266 s. Der letzte Arm wird für sich geringfügig langsamer;
die Zeit bis alle vier ankommen verkürzt sich trotzdem.

## Erneute gemeinsame Prüfung

Individuelles Retiming verändert die relativen Armstellungen. Deshalb wurde
die neue gemeinsame Bewegung erneut geprüft, zusätzlich zu 32.008 isolierten
Prüfstellungen entlang der acht Abschnitte:

- 1.601 gemeinsame Zeitpunkte, Abstand höchstens 0,010 s.
- Keine geometrische FCL-Kollision und keine Verletzung der statischen
  20-mm-Paarreserve; alle sechs Armpaare berücksichtigt.
- Kleinster Abstand der modellierten Armhüllen: 155,147 mm.
- Weiterhin 1.297 Zeitpunkte mit Verletzung der separaten konservativen
  dynamischen Reserve. Orange bedeutet diese Diagnose, nicht geometrischen Kontakt.

Die Reserveannahmen des [10×-Vergleichs](offline_carton_speed10.md) bleiben
unverändert; ihr höherer Verletzungsanteil ist kein Nachweis realer Bremswege.
Die Geometrieprüfung ist diskret, kein kontinuierlicher Kollisionsbeweis.
Aktuell stehen die Basen fest, Greifer bleiben offen. Kein Greifschluss,
Hub, Last-, Tracking- oder Hardwaretest; Artefakte bleiben `executable:false`.
Der Verlauf ist auch keine Zusage, dass native MoveJ/MoveL-Befehle genau
dieses Zeitgesetz reproduzieren. Aktive Profile und Dienste wurden nicht geändert.

## Umsetzung und Reproduktion

`smooth_paths.py` erzeugt quintische Geschwindigkeitsrampen mit Konstantfahrt
und quintische räumliche Interpolation. Ableitungsgrenzen entstehen aus lokalen
Bernstein-Koeffizienten und der Kettenregel; eine gemeinsame Streckung innerhalb
jedes Abschnitts erfüllt die gewählten Grenzen. `smooth_carton_paths.py` prüft
Geometrie, Bindung an eingefrorene Modelle und beide Zeitverläufe.

Build und 25 gezielte Tests bestanden (9 Glättung, 9 Zeitskalierung, 7 Bahnen).
Unabhängige Rekonstruktion an 800.008 Punkten bestätigt Zeiten, Übergänge und
Ableitungsgrenzen; ermittelte Spitzen 0,450000 rad/s, 0,400000 rad/s² und
0,835104 rad/s³ liegen unter den analytischen Obergrenzen.
15 Browserprüfungen bestanden; Vorschau und Kurvendarstellung visuell geprüft.

Artefakte: `setup/research/offline-carton-smoothing-20261117/`, insbesondere
`result.json`, `verification.json`, `verify.py`, `viewer.html`.
Logs: `setup/logs/uwa-carton-smoothing-*`. Die bisherigen Ergebnisse bleiben erhalten.

Nach dem üblichen Lyrical-Motionpaket-Build aus `~/UWA_ws`:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/smooth_carton_paths.py \
  setup/research/offline-carton-speed10-20261117 \
  --output-dir /tmp/uwa-carton-smoothing-new
xdg-open /tmp/uwa-carton-smoothing-new/viewer.html
```
