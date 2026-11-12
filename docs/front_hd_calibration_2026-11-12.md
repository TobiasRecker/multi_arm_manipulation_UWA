# Front rechts: 40 native HD-Aufnahmen, 2026-11-12

Die beauftragte Aufnahme ist vollständig abgeschlossen: **40 unterschiedliche
Roboterstellungen, 32 Fit- und 8 vorab reservierte Prüfbilder**, jeweils native
**2592 × 1944 Pixel** aus dem neuen ROS-HD-Dienst. Alle 40 Bilder wurden angenommen
(20–24 ChArUco-Ecken), alle ausgewählten Pixel-Hashes sind verschieden.
Die automatische Kalibrierfreigabe ist **fehlgeschlagen**; kein Profil aktiviert.

## Qualitätswerte

| Prüfung | Messwert | Bisherige Grenze | Ergebnis |
|---|---:|---:|---|
| Intrinsics: Fit-RMS | 1,1984 px | 1 px | FAIL |
| Intrinsics: medianer Prüf-RMS | 1,0031 px | 1 px | FAIL |
| Hand-Auge: medianer Prüf-RMS | 1,9248 px | 1 px | FAIL |
| Board-Translationsstreuung | 1,2669 mm | 5 mm | PASS |
| Board-Rotationsstreuung | 0,5884° | 0,5° | FAIL |

Der reguläre Ablauf beendet die Auswertung bereits beim Intrinsics-Fit.
Die obigen zusätzlichen Prüfwerte stammen aus einer getrennten Offline-Diagnose
unter `evaluation_v1/`: ausschließlich die 32 Trainingsbilder liefern K/D,
anschließend unveränderter Park-/robuster Hand-Auge-Solver. Acht feste Prüfbilder
bleiben vom Fit ausgeschlossen. Kein Bild ausgeschlossen, keine Ground Truth
oder nominelle Extrinsics für den Fit benutzt, keine Grenzwerte geändert.
Diagnose-Transformationen sind ausdrücklich **nicht freigegeben**.
Die Boardstreuung ist eine interne Konsistenzprüfung, kein Nachweis absoluter
Genauigkeit. Mit nur einem rechten Arm entsteht keine neue relative Basispose.

Der ältere Front-VGA-Versuch hat andere Ansichten und Bildzahlen; daraus lässt
sich kein kontrollierter HD/VGA-Genauigkeitsvergleich ableiten. Für weitere
Verbesserungen können zuerst die gesicherten Bilder offline untersucht werden.
Eine neue reale Fahrt ist dafür nicht nötig.

## Warum HD an der Pixelgrenze scheitert: Offline-Diagnose

Nachfrage des Nutzers am12.11.: gleiche Kamera und unverändertes Board, weshalb
scheitert HD gegenüber VGA? Der belegte Hauptgrund für den **Intrinsics-Abbruch**
ist die unverändert absolute1-Pixel-Grenze.2592/640=1944/480=**4,05**:
bei gleicher Bildgeometrie entspricht1VGA-Pixel4,05HD-Pixeln. Die verwendete
Schwelle ist damit beiHD erheblich strenger. Das war eine unzureichende
Berücksichtigung der Auflösung in unserer Qualitätsauswertung.

Kontrollierte Offline-Prüfung mit **denselben40HD-Aufnahmen**,32/8-Rollen fest,
keine Ansichten entfernt; keine neuen Aufnahmen oder Hardwarekommandos:

| Daten/Auswertung | Fit-RMS [px] | Median Prüf-RMS [px] |
|---|---:|---:|
| Frühere echte Front-VGA-Reihe,62Ansichten |0,289 |0,299 |
| HD,Originalpunkte undOriginalauflösung |1,198 |1,003 |
| Dieselben HD-Punkte auf640×480-Koordinaten umgerechnet |0,296 |0,248 |
| Dieselben40HD-JPEGs auf640×480 verkleinert,alleEcken neu erkannt |0,315 |0,276 |

Die letzten zwei Zeilen sind zwei getrennte Kontrollen: reineEinheitenänderung
und tatsächliche erneute Erkennung im verkleinerten Bild. Das ist ein deutlicher
Nachweis, dass größere Pixelzahlen hier keine entsprechende Verschlechterung
der Geometrie belegen. Die verkleinerteDateiversion ist kein neuer Sensor-VGA-
Datensatz. Sichtfeld/ISP/Firmwareverarbeitung zwischen nativerHD- undHTTP-VGA-
Quelle sind damit nicht als identisch nachgewiesen. [OpenCV beschreibt die
Skalierung der Pixel-Intrinsics bei geänderterAuflösung](https://docs.opencv.org/4.12.0/d9/d0c/group__calib3d.html).

**Die frühere Front-Hand-Auge-Kalibrierung hatte insgesamt bereits nicht bestanden:**
0,652°Rotationsstreuung bei0,5°Grenze. Aktuell0,588°; dieser Fehler inGrad
verschwindet durch Umrechnung der Pixel nicht. Positionsstreuung alt2,344mm,
aktuell1,267mm. AnderePosen/Prüfmengen(alt50/12,aktuell32/8) erlauben daraus
keine kontrollierte Aussage über einenHD-Genauigkeitsgewinn.

### Was noch nicht als Ursache nachgewiesen ist

Für die verbleibende Rotationsinkonsistenz kommen Bild-Pose-Schätzung und
Optikmodell, Druck-/Board-Unebenheit, mechanischeMontagestabilität sowie
Restbewegung/Zeitzuordnung in Betracht. Keiner dieser Beiträge wurde hier
als Hauptursache isoliert. BeideReihen verwendetenFokus435/60000µs/Gain16;
LED-Settings unterscheiden sich(alt1/53,aktuell0/0), ebenso Aufnahme-/Bildpipeline.
WiederhergestellteHTTP-Einstellungen belegen nicht allein die tatsächlichen
V4L2-Linsen-/Belichtungswerte während desHD-Streams: das nativeWerkzeug liest
sie derzeit nicht während der Aufnahme zurück. Das ist eine Prüflücke, kein
Nachweis eines Fokuswechsels. Der Grünstich ist ebenfalls keine isoliert
nachgewiesene Ursache des geometrischen Fehlers.

Eine konkrete Softwarehypothese wurde separat geprüft: [OpenCV empfiehlt bei
ChArUco ohneK/D, ArUco-Marker-Subpixelverfeinerung auszuschalten](https://docs.opencv.org/4.12.0/df/d4a/tutorial_charuco_detection.html).
Mit dieserÄnderung als reinerOffline-Variante bleibt derHD-Fit1,19834px gegenüber
1,19841px; medianeEckenverschiebung0,0046HD-Pixel. Sie erklärt diesenFehler
also nicht wesentlich. Produktionsdetektor undOriginalpunkte unverändert.

Nächster sinnvollerSchritt ist eine auflösungsbewusste Fehlerdefinition
(z.B.vergleichbare normierteBild-/Winkelfehler), einschließlich der momentan
pixelbasierten robustenGewichtung/Ausreißergrenzen imSolver. Millimeter- und
Gradgrenzen bleiben eigenständige Kriterien. Anschließend die verbliebene
Rotationsabweichung offline untersuchen; bloßes Freigeben mit größeren
Pixelgrenzen würde die0,588°-Abweichung nicht beheben. Hier wurde keine
Freigabegrenze/Optimierung geändert und keinProfil aktiviert.

Nachweis: `resolution_diagnosis_v1/{analyze.py,results.json,*-corners.json}`
unter derHD-Sitzung; Log `$UWA_WS/setup/logs/uwa-front-hd-resolution-diagnosis.log`.
80Originaldatei-Hashes nach Auswertung erneut bestätigt.

## Durchführung und diagonale Unabhängigkeit

Fokus435 manuell, Belichtung60000µs manuell, Gain16, dieselbe physische Kamera und
native Bildquelle während aller 40 Aufnahmen. Je HD-Aufruf drei Originalbilder
mit Servicebericht; nach jedem Aufruf bestätigter Restore des Visionservers und
der Kameraeinstellungen. Empfangszeiten sind keine Belichtungszeitstempel.

Nach neuester Nutzerkorrektur arbeiten `right_front` und `left_rear` unabhängig.
Die Aussage, dass die diagonalen Arme physisch nicht zusammenreichen, stammt vom
Nutzer; sie ist keine hier vermessene Reichweitenkalibrierung. Nur dieses Paar ist
von gegenseitiger Kollisions- und Stillstandsprüfung ausgenommen. Selbst-, Tisch-,
Werkzeug- und übrige Armkollisionen sowie native UR-Sicherheit bleiben erhalten.
Neue Batches protokollieren die Ausnahme im Fingerprint. 26 gezielte Tests und
Lyrical-Build bestanden. Der Frontlauf wurde nicht unterbrochen.

39 Zusatzfahrten nach der stationären Erstaufnahme; Originalziele und feste Rollen
unverändert. Ausgeführter Batch `6c70b73a1a4fecd9d177f0ff7bcfdc325d47ee980a5fe0e1f4a88186a71ed894`.
Kein Schutzreset, keine automatische Rückfahrt oder Profilübernahme.

## Daten und Abschlusszustand

Lokales Sitzungsverzeichnis:
`$UWA_WS/setup/calibration/hardware_handeye/right_front_hd_20261112/`

- `records/`: 40 Originalmessungen, ausgewählte JPEGs, Annotationen, Ecken,
  Gelenkstellungen, `T_base_tool0`, Kameraeinstellungen und HD-Burstreferenzen.
- `preparation/fixed-goals-and-roles.json`: vorab fixierte Ziele/32-8-Rollen.
- `final_plan/batch.json`: ausgeführte kollisionsgeprüfte Verbindungswege.
- `preparation/run-exit.json`: regulärer Exit1 nach vollständiger Aufnahme,
  ausdrücklich wegen fehlgeschlagener Intrinsics-Qualitätsprüfung.
- `evaluation_v1/summary.json`: abgelehntes Gesamtergebnis mit Kennzeichnung.
- `evaluation_v1/diagnostic_{intrinsics,handeye}.json`: Diagnosewerte, nicht aktiv.
- `evaluation_v1/raw-data-sha256.json`: verifizierte Hashes aller 40 ausgewählten
  Originalbilder und Messdatensätze. Rohdaten/Sitzungen werden nicht eingecheckt.
- `evaluation_v1/completion-state.json`: ausschließlich lesende Abschlussprüfung.

Abschlussprüfung am12.11. um12:37Perth: Front RUNNING/NORMAL, ros.urp PLAYING,
Remote=true; keine Fahrziele mehr anhängig, tatsächliche Geschwindigkeiten0.
Maximale Positionsspanne über0,5s 0,000169rad, Abweichung zur letzten gemessenen
Aufnahmestellung0,0000453rad. Der skalierte Trajektoriencontroller bleibt aktiv
und hält diese Stellung; keine Rückfahrt. Kamera wieder **Normal**, sämtliche
Einstellungen identisch mit der letzten Aufnahme. Bestehendes Kalibrierprofil
unverändert. Andere Arme/Dienste wurden zum Abschluss nicht gesteuert.
