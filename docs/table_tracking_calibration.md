# Tischbewegung messen und Kameramontagen getrennt kalibrieren

Stand: 2026-11-09. Präzisierter Nutzerzweck: einen Tisch absichtlich bewegen,
die relative Tischpose und die Änderung messen und die Abweichung kompensieren.
Die Tischboards bleiben an ihren Tischen. Dies ersetzt die Annahme dauerhaft
bekannter weltfester Tischboardposen aus dem ersten Konzept. Methoden sind
Empfehlungen; noch keine Implementierung oder Freigabe für Messfahrten.

## Körper, Koordinaten und unveränderliche Größen

`T_A_B` bildet Koordinaten aus B nach A ab. `L,R` sind die Tischframes,
`B_L,B_R` die fest montierten Boards, `C` eine OAK, `U` eine Wrist-Kamera,
`M` ein zusätzliches mobiles Kalibrierboard.

- `T_L_B_L`, `T_R_B_R`: Boardmontagen, bleiben während Tischbewegungen konstant.
  Entweder vermessen oder Boardframes als erste Tischreferenzen definieren.
- Tischlokale Robotermontagen und eine tischfeste Kameramontage bleiben konstant.
- `T_L_R(t)`: gesuchte, veränderliche relative Tischpose.
- Raumfeste OAK4: Montage in einem raumfesten Referenzframe konstant.
  Ihre Beziehung zu einem bewegten Tisch ist veränderlich.
- Tischfeste OAK: Montage im Trägertisch konstant, Raumlage bewegt sich mit.

Für relative Bewegung einen beim Versuch stehenbleibenden Tisch als Referenz
wählen. Das bestehende geometrische `world` nicht bei jeder Bewegung als neue
Mitte zwischen den Tischen definieren. Absolute Bewegung beider Tische im Raum
erfordert eine zusätzliche raumfeste Referenz; nur ihre relative Lage lässt
sich ohne diese bestimmen. Montageänderung, Tischbewegung und Intrinsics-
Änderung sind verschiedene Zustandsänderungen.

## OAK4 sieht beide Tischboards: relativer Bezug ohne Welt-Extrinsik

Pro Bild beide Boardposen aus passenden Intrinsics/Verzeichnung und metrischen
ChArUco-Ecken schätzen. Bei gemeinsamem Aufnahmezustand gilt:

```text
T_B_L_B_R(t) = inverse(T_C_B_L(t)) @ T_C_B_R(t)
T_L_R(t) = T_L_B_L @ T_B_L_B_R(t) @ inverse(T_R_B_R)
```

Die Weltpose der Kamera fällt heraus. Für diese relative Messung muss die
Stativpose nicht vorher absolut eingemessen sein; auch eine geänderte Stativpose
ist bei erneuter Sicht auf beide Boards algebraisch unschädlich. Intrinsics,
korrekte Frames, Bildqualität und Boardmaßfehler bleiben relevant. Bewegte
Aufnahmen/Rolling-Shutter-Zeitversatz können das gemeinsame Moment verletzen;
zunächst an stationären Tischzuständen messen.

Gegenüber dem Startzustand:

```text
Delta_local = inverse(T_L_R(t0)) @ T_L_R(t)   # Bewegung im initialen rechten Frame
Delta_left  = T_L_R(t) @ inverse(T_L_R(t0))   # aktive Änderung im linken Frame
```

Translationen/Rotationen nur mit explizitem Bezugsframe berichten. Als einfache
Anzeige im linken Frame zusätzlich p(t)-p(t0) und R(t)@R(t0).T ausgeben.
Zeitlich mehrere stationäre Bilder robust mitteln; bei schlechter/fehlender
Boarderkennung Qualität/Alter melden statt eine frische sichere Pose zu behaupten.

## Kleine OAK auf rechtem Tisch, Blick zum linken Board

Nach separater Montagekalibrierung `X=T_R_C` gilt laufend:

```text
T_R_L(t) = X @ T_C_B_L(t) @ inverse(T_L_B_L)
```

X bleibt auch dann konstant, wenn der rechte Tisch bewegt wird. Nicht nach
jedem Tischversatz neu gegen eine angenommene alte Weltpose kalibrieren.
Die Kamera kann zeitweise zusätzlich ihr eigenes Board sehen, muss es nach
erfolgreicher Montagekalibrierung für diese Formel aber nicht sehen.

Sind sowohl X als auch die initiale Tisch-zu-Tisch-Pose unbekannt, liefert eine
einzige Ansicht des gegenüberliegenden Boards nicht beide Größen getrennt.
Viele Bilder genau derselben Anordnung lösen diese Mehrdeutigkeit nicht.
Bei bekannter Referenzpose und Intrinsics ist einzelne metrische Board-PnP
grundsätzlich möglich, als präzise Montagekalibrierung sind mehrere geometrisch
unterschiedliche Beobachtungen vorzuziehen. Planare Ziele können bei schwacher
Perspektive mehrere ähnlich plausible Posen erzeugen.

## Bevorzugte Einmessung: bekannte Wrist-Kamera und mobiles Zusatzboard

Der Nutzer schlägt den MoCap-ähnlichen Ablauf vor; Empfehlung: so beginnen.
Die vorhandenen Tischboards bleiben dabei montiert, beide Tische während der
Einmessung stehen lassen.

1. Wrist-Kamera mit auf echter Hardware validierter Hand-Auge-Kalibrierung in
   eine geeignete bekannte Haltepose bringen. Zu jedem Bild passende Gelenkpose
   und TF verwenden. Simulierte Gütewerte ersetzen keinen Hardware-Nachweis.
2. Ein separates steifes ChArUco-Board im gemeinsamen Sichtfeld von Wrist und
   OAK bewegen. Kameras dürfen währenddessen fest stehen. Größer/kleiner so
   wählen, dass Übersicht und nahe Wrist-Kamera beide ausreichend Details sehen.
3. Etwa 20–40 verschiedene Halteposen als Startvorschlag: seitlich versetzt,
   mehrere Höhen und unterschiedliche Neigungen. Pro Haltephase Board ruhig,
   passende Bildpaare aufnehmen. Keine präzise externe Boardposition nötig.
4. Pro Aufnahme aus den beiden bildbasierten Posen:

```text
T_U_C = T_U_M(i) @ inverse(T_C_M(i))
T_Base_C = T_Base_U @ T_U_C
```

   Das Board bewegt sich, die feste Kamera-Kamera-Transformation bleibt gleich.
   Bei variierenden Robotermessstellungen `T_Base_U(i)` verwenden und direkt
   das konstante `T_Base_C` schätzen. Robuste gemeinsame Optimierung der
   Bildecken ist besser als bloß Eulerwinkel der Einzel-PnP-Ergebnisse zu mitteln.
5. Lokalen Tischbezug aus dessen bereits kalibrierten Robotermontagen bzw.
   Boardbeziehungen herstellen. Für die tischfeste OAK einen Referenzarm desselben
   Tisches benutzen; für die raumfeste OAK den während des Versuchs festen Bezug.

Weder Tischboard noch Kamera müssen sich bei diesem Verfahren bewegen. Das
Zusatzboard kann von Hand oder von einem UR gehalten werden. Seine Werkzeug-
Montage muss nicht bekannt sein, solange beide Kameras dasselbe Board in
derselben Haltephase beobachten. Ein Referenzarm kann genügen; mehrere bekannte
Wrist-Kameras liefern zusätzliche Verbindungen und unabhängige Querprüfungen.
Absolute Genauigkeit im Roboterframe hängt auch von deren Hand-Auge-/FK-Güte ab.

## Alternative: Board am UR, klassische Eye-to-Hand-Kalibrierung

Wird das Zusatzboard starr am Werkzeug gehalten, kann die OAK allein dessen
Posen zusammen mit Roboterkinematik über viele verschiedene Orientierungen
auswerten. Für unbekannte Werkzeug-Board-Montage Z und Basis-Kamera-Montage Y:

```text
T_Base_Tool(i) @ Z = Y @ T_C_M(i)
```

Beide konstanten Transformationen gemeinsam schätzen. Eine bekannte genaue
Board-Werkzeug-Montage vereinfacht das Problem, ist aber nicht zwingend nötig.
Ausreichend unterschiedliche Rotationen um nicht parallele Achsen erforderlich;
nicht nur parallel verschobene Boardstellungen aufnehmen. Ein einziges mobiles
Kalibrierboard kann dafür zwischen Armen umgesetzt werden, keine dauerhaften
Marker an jedem UR erforderlich. Diese Variante ist gut automatisierbar,
übernimmt aber Kinematikfehler und ist eine eigene neue Messroutine.

## Kalibrieren, dann bewusst bewegen und validieren

Erst Montageprofile mit feststehenden Tischen bestimmen und unverändert halten.
Danach den gewünschten Tisch verschieben, Tischboards erneut erfassen und nur
`T_L_R(t)` beziehungsweise Tisch-/Basisbeziehungen aktualisieren. Tischlokale
Wrist-/Robotermontagen und Tischkamera-Montage nicht mitoptimieren und damit die
gesuchte Bewegung absorbieren. Kooperative Ziele anschließend in die aktuellen
Basisframes umrechnen; Bewegungskompensation ist ein eigener Umsetzungsschritt.

Validierungsbilder/-positionen vor dem Fit zurückhalten. Bekannte unabhängige
Weg-/Winkelreferenzen in Realität und ausschließlich nachgelagerte Ground Truth
in Gazebo zum Bewegungsvergleich verwenden. Raum- und Tischfehler, Pixelresiduen
und mm/Grad getrennt ausweisen. Die 2-m-OAK4-Ansicht hat links wenig Reserve;
eine nähere Zusatzkamera ist dafür sinnvoll. In dieser Beratung keine Kameras,
Tische, Roboter oder Dienste verändert.

## Primärquellen

- [OpenCV PnP und planare Kandidaten](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html)
- [OpenCV Hand-Eye / Robot-World-Hand-Eye](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- [Basler stationäre Kamera und Hand-Eye-Ablauf](https://docs.baslerweb.com/stereovisard/rc_cube/en/handeye_calibration)
