# Vier Eckanflüge mit zehnfacher Trajektoriengeschwindigkeit

[Vergleich in Echtzeit öffnen](../../../setup/research/offline-carton-speed10-20261117/viewer.html).
**Trajectory timing** wählt220,67s oder22,07s geplante Dauer.
**Playback** verändert nur die Darstellung und steht hier anfangs auf1×.
Die frühere Vorschau hatte standardmäßig20×Wiedergabe: ihre220,67s wurden
bereits in etwa11s angezeigt. Deshalb kann die neue22s-Echtzeitvorschau
langsamer aussehen als die alte beschleunigte Darstellung.

## Was tatsächlich geändert und geprüft wurde

Die gespeicherten vier empfohlenen Wege aus
`offline-carton-paths-20261117/case03` wurden gemeinsam in der Zeit komprimiert.
Alle Abschnittsdauern werden durch10 geteilt. Gelenkstützstellen, Splineknoten,
Greifziele, Stopps an Abschnittsgrenzen und relative Fortschritte bleiben gleich.
Das neue `trajectory-10x.json` enthält diese veränderten Zeiten, ausdrücklich
`executable:false`. Das Original wurde nicht überschrieben.

Für eine gemeinsame Skalierung gilt exakt:

| Größe | Veränderung |
|---|---:|
| Zeit | ÷10 |
| Gelenkgeschwindigkeit | ×10 |
| Gelenkbeschleunigung | ×100 |
| Gelenkruck | ×1000 |

Im idealen Modell ist der Vierarmzustand bei`t/10` derselbe wie ursprünglich
bei`t`. Unterschiedliche Skalierungsfaktoren pro Arm hätten diese Eigenschaft
nicht. Reale Regelabweichungen/Verzögerungen sind in dieser Aussage nicht enthalten.

## Ergebnis

Die folgenden Werte sind konservative analytische Obergrenzen über die
geplanten Kurven, keine gemessenen Motorwerte:

| Größe | Ursprünglich | Zehnfach |
|---|---:|---:|
| Gesamtdauer | 220,671s | 22,067s |
| Geschwindigkeit | ≤0,045459rad/s | ≤0,454584rad/s |
| Beschleunigung | ≤0,012231rad/s² | ≤1,223044rad/s² |
| Ruck | ≤0,010086rad/s³ | ≤10,085925rad/s³ |

Unabhängige dichte analytische Auswertung findet beim10×Fall Spitzen von
0,454556rad/s,1,153333rad/s² und10,085924rad/s³, jeweils unter den Grenzen.
Der Geschwindigkeitswert entspricht ungefähr26°/s. Alle24Gelenke bleiben
unter ihren Geschwindigkeitsgrenzen in der eingefrorenen URDF. Das ist kein
Abgleich mit der aktuellen Sicherheits-/Speedscaling-Konfiguration der Hardware.

Das ursprüngliche Planungsprofil begrenzt auf0,05rad/s und0,10rad/s² und wird
beim10×Fall überschritten. Diese bewusst langsamen Werte sind **keine
physischen UR-Maxima**. Für eine Ausführung braucht es ein geeignetes Profil
mit qualifizierten Beschleunigungs-, Ruck-, Drehmoment-, Werkzeug-/Last- und
Trackingannahmen. Diese Untersuchung liefert keinen gemessenen Hardwaregrenzwert.

Bei2.208gleichen normierten Zeitpunkten:0geometrische FCL-Kollisionen,
identischer kleinster Armhüllabstand155,755mm. Maximale numerische Abweichung
der zeitlich zugeordneten Gelenkstellungen1,87e−14rad. Bei10×liegen diese
Prüfpunkte höchstens0,010s statt0,100s auseinander. Die Geometrie wurde dadurch
nicht gröber abgetastet. Es bleibt diskrete Modellprüfung, kein kontinuierlicher
Kontakt-/Dynamiknachweis und kein tatsächlicher Griff.

## Orange Reserveanzeige

Die Reserve wird zusätzlich mit den jeweiligen geplanten Gelenkgeschwindigkeiten
ausgewertet. Die alte Geschwindigkeitsuntergrenze0,05rad/s,20mmModellreserve,
0,35s zusammengesetzte Verzögerung und angenommene0,5rad/s²Bremsung bleiben
unverändert. Vier Nachbarpaare erhalten diese dynamische Reserve; die beiden
Diagonalen behalten wie im bisherigen Beispiel die statische20mmReserve.

So entstehen423Reserveverletzungen beim1×Fall und1.606beim10×Fall, jeweils
von2.208Zeitpunkten. Die größte berechnete Paaranforderung steigt von199mm auf
1.357mm. Das sind konservative, **nicht real vermessene** Stopphüllen und keine
beobachteten Kollisionen. Die Auswertung mit momentaner Sollgeschwindigkeit und
alter Geschwindigkeitsuntergrenze qualifiziert auch keinen neuen maximalen
Betriebsgeschwindigkeitsbereich oder zusätzliche Beschleunigung während einer
Reaktionsverzögerung. Sie ist eine Diagnose, keine automatische Fahrfreigabe
und kein Beweis, dass die Hardware diese Bewegung grundsätzlich nicht kann.

## Umsetzung und Nachweis

`uwa_cell_motion/path_speed.py` skaliert Zeiten ohne Änderung der Geometrie,
berechnet Geschwindigkeiten und lokale analytische Ableitungsgrenzen für die
Zusammensetzung des kubischen Gelenksplines mit dem quintischen Zeitgesetz.
Splineknoten werden als Intervallgrenzen berücksichtigt; Intervallmaxima und
Dreiecksungleichung liefern konservative Obergrenzen. Gleitkomma-/Inversions-
reserve ist numerisch, keine physische Unsicherheit. C2-Stetigkeit bedeutet
nicht, dass der Ruck an allen Spline-/Abschnittsgrenzen stetig ist.

16gezielte Tests bestanden (9neu,7bestehende Bahntests), Build bestanden.
Unabhängige Nachrechnung mit100.001Punkten pro Abschnitt bestätigt Ableitungs-
grenzen und unveränderte Stützstellen/Splineknoten.15Browser-Bedienszenarien
bestanden, alle241paarweisen Vorschauzustände geometrisch identisch.
Standard10×Trajektorie/1×Wiedergabe und echte Modellsekunden geprüft,
fertige Darstellung visuell kontrolliert. Keine Roboter-, Kamera- oder
Physiksimulationsaktion, keine Änderung aktiver Grenzen oder Dienste.

Daten: `setup/research/offline-carton-speed10-20261117/` mit `comparison.json`,
`trajectory-10x.json`, `verification.json`, `verify.py`, `viewer.html`.
Logs: `setup/logs/uwa-carton-speed10-*`.

Reproduzieren nach dem üblichen Lyrical-Motionpaket-Build aus`~/UWA_ws`:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/compare_carton_path_speed.py \
  setup/research/offline-carton-paths-20261117/case03 \
  --output-dir /tmp/uwa-carton-speed10-new
xdg-open /tmp/uwa-carton-speed10-new/viewer.html
```
