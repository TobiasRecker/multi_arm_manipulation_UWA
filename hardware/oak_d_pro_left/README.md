# Hohe USB-Kamera am linken Tisch · Vorentwurf

## Anordnung

Die am N100 getestete Kamera ist eine **OAK-D Pro AF (RVC2)**, USB-ID
`18443010314F3B1300`, mit IMX378-Autofokus. Sie bekommt links außen eine
Ansicht Richtung Zellmitte, gegenüber der Ethernet-OAK4. Ziel für die erste
Sichtprobe sind **1,85–2,0 m optische Höhe über Boden**. Zum Vergleich liegt
die dokumentierte frühere OAK4-Registrierung bei etwa 1,86 m. Das nominale
Modell setzt die linke Tischplatte auf 0,90 m. Daraus folgen ungefähr
0,95–1,10 m von Tischoberkante bis Optik. Mast erst nach der Sichtprobe
auf Länge bringen. Die Optik liegt etwas über dem Rohrende.

```text
Schnitt senkrecht zur linken Außenkante    Blick Richtung Zellmitte →
                                                 LOS zur Arbeitsfläche
   OAK-D Pro + kurzer Metall-Neigekopf     ╲
                 ║                         ╲
                 ║ Stahl 40 × 40 × 1,6
                 ║
                 ║ ╲ Aussteifung
                 ╚══╧════════════════════ Klemmplatte auf Tisch
                     ┌─────────────────── Tischplatte
               Klemme└──▲────────────────
                        Druckteller unten

Draufsicht: zwei Klemmen entlang der Tischkante, Mast mittig dazwischen.
```

1. **Mast und Fuß**  
   40 × 40 × 1,6 mm Stahl-Vierkantrohr. Für die Klemmplatte sind als
   Layoutannahme etwa 220 mm entlang der Kante × 140 mm in die Tiefe
   vorgesehen, mit dem Mast außen, zwei Stahlgussets in unterschiedlichen
   Ebenen und dem Plattenüberstand auf der Tischplatte. Die Endausführung
   hängt von der Kante und der Unterseite ab. Mastposition nahe einem
   steifen Tischrahmenbereich wählen. Kein langer horizontaler Ausleger.
2. **Anschluss an den Tisch**  
   Zwei mechanisch gesicherte Stahl-Schraubklemmen greifen oben an der
   Fußplatte und unten an tragfähiger Tischsubstanz. Zielgrößen für die
   Anordnung sind 160–180 mm Abstand entlang der Kante und etwa 60–80 mm
   Einbindetiefe bis zur Drucktellerachse. Oben nimmt der tiefe
   Fußplattenüberstand das Kippmoment auf. Druck über Metallauflagen mit
   dünner rutschfester Schutzlage verteilen. Vor Auswahl der Klemmen
   Plattenstärke plus Fußplatte, freien Untergriff und Lage einer
   Zarge prüfen. Falls die Zarge im Weg ist, an ihre Geometrie anpassen oder
   alternativ mit zwei vertikal versetzten Metallklemmen an ein geeignetes
   Tischbein anbinden. Die Maße sind Layoutwerte ohne Belastungsnachweis.
3. **Kamerakopf**  
   Kompakter Metall-Neigekopf mit gekonterter Verbindung am Mast und
   kurzer Metallplatte mit zwei Rückenschrauben zur Kamera. Als erste
   Orientierung 35° nach unten ansetzen und anhand des Bilds einstellen.
   Alternativ lässt sich die Neigung nach der Sichtprobe in einen festen,
   gekanteten Metallwinkel übernehmen. Laut Luxonis-Zeichnung hat die
   Rückseite zwei M4-Gewinde im Abstand von 75 mm mit 8 mm eingezeichneter
   Gewindetiefe. Lochbild und nutzbare Tiefe am Gerät prüfen. Schrauben
   nach Plattendicke und Scheiben auswählen, sodass sie beim Anziehen
   an der Platte klemmen und vor dem Gewindegrund enden. Kühlrippen,
   Optik und USB-Stecker brauchen Freiraum. Eine separate kurze
   Sicherungsleine verbindet Kamera bzw. Kamerahalter mit dem Tischrahmen.
4. **USB und Registrierung**  
   Kabel am Mast abfangen und mit einer kleinen Serviceschlaufe zum
   Stecker führen. N100 in der Nähe des Masts platzieren. Mast, Klemmen,
   Kabel und eventuelle Sicherungsleine vor Montage gegen den Arbeitsraum
   der beiden linken UR prüfen. Nach der Montage starren ChArUco-Anker
   beobachten, während der Tisch typisch belastet wird. So fallen Wackeln
   und bleibendes Wandern auf. Die USB-OAK anschließend zum linken Tisch
   registrieren. Bei einem Tischversatz folgt die Kamera dem Tisch, ihre
   Weltpose folgt entsprechend dem Tischtransform.

## Warum der größere Querschnitt

Idealisiertes Kragarm-Beispiel bei 1 m freier Länge, 10 N seitlicher
Spitzenlast und starrer Einspannung, mit Δ = FL³/(3EI). 10 N ist eine
Vergleichslast. Sie ersetzt keine Auslegung der Klemme oder des Tisches.

| Rohr | Flächenträgheitsmoment ca. | Auslenkung des Rohrs ca. |
|---|---:|---:|
| Alu rund Ø10 × 1 mm | 290 mm⁴ | 167 mm |
| Stahl quadratisch 40 × 40 × 1,6 mm | 60.500 mm⁴ | 0,28 mm |

Die 167 mm zeigen die Größenordnung der linearen Rechnung. Bei realer
Montage kommen Verdrehung, Tischbewegung und Spiel hinzu. Der linke Tisch
trägt zwei Roboter. Die erreichbare optische Stabilität hängt deshalb
auch von dessen Bewegung ab.

[Bunnings 10-mm-Alurohr](https://www.bunnings.com.au/metal-mate-10-x-1mm-1m-aluminium-round-tube-1m_p1067742) ·
[Bunnings 40-mm-Stahl-Vierkantrohr, 2 m, I/N 0910112](https://www.bunnings.com.au/australian-handyman-supplies-40-x-40-x-1-6mm-x-2m-galvanised-square-hollow-section_p0910112) ·
[Luxonis-Gehäusezeichnung, S. 6](https://www.mouser.com/datasheet/2/1139/Luxonis_4_13_2022_OAK_D_Pro_AF_Datasheet_4_12_22-2939269.pdf)

## Druckdateien

- [Lochschablone](oak-rear-hole-template.stl), 91 × 18 × 4 mm.
  Zwei Ø4,5-mm-Öffnungen im 75-mm-Raster. Erst von Hand an das
  Kameralochbild halten, dann die Bohrmitten auf einer Metallplatte
  übertragen. Beim Bohren bleibt die Kamera getrennt.
- [USB-Kabelsattel](usb-cable-saddle.stl), 46,6 × 14 × 24 mm.
  Auf das 40er Profil setzen und per Klettband um Mast, Sattel und Kabel
  legen. V-Nut für ungefähr 6 mm Kabelaußendurchmesser. Das Band so anziehen,
  dass das Kabel gehalten wird und der Mantel seine Form behält.
- Beide mit der bereits flachen STL-Unterseite auf das Druckbett legen.
  Einheiten mm, ohne Stützstrukturen. PETG für den Kabelsattel als Start.
  Die STLs sind als geschlossene Volumenkörper überprüft. Druckpassung und
  reale Last-/Vibrationsprüfung stehen aus. Mast, Tischklemmung
  und Kamerakopf übernehmen die Traglast über Metall.
- [Parametrischer Export](make_prints.py) per `python3 make_prints.py`
  mit Python-VTK. `--tube`, `--clearance`, `--cable` und `--spacing`
  passen die Teile an gemessene Maße an.

Für die Maßzeichnung des Fußes fehlen ein Foto der linken Außenkante
schräg von unten mit Maßstab, **Plattenstärke und freie Tiefe bis zur
Zarge** sowie die reale Tischhöhe. Für die endgültige Mastlänge
und Kopfneigung braucht es die gewünschte Position entlang der Kante
und eine Sichtprobe auf Arbeitsfläche und Referenzboards.
