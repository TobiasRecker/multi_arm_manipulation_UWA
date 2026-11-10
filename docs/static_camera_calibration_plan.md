# Vorschlag: statische OAK-Kameras in die UWA-Zelle einmessen

Stand 2026-11-09. **Empfehlung zur Diskussion**, keine bereits implementierte
Kalibrierung und keine Freigabe für reale Roboterbewegungen.

**Durch Nutzerpräzisierung ergänzt/teilweise ersetzt:** Das Ziel ist die Messung
absichtlich bewegter Tische, deren Boards an den Tischen bleiben. Der aktuelle
Ansatz steht in [table_tracking_calibration.md](table_tracking_calibration.md):
Montagen einmal separat kalibrieren, Tisch-zu-Tisch-Pose laufend messen.
Die nachfolgende ursprüngliche Referenzannahme gilt nur für tatsächlich
feststehende Referenzen. Eine Tischboard-Weltpose nicht während beabsichtigter
Bewegung als bekannt konstant voraussetzen. Sieht eine OAK beide Tischboards,
benötigt deren relative Messung keine absolute Welt-Extrinsik der Kamera.

## Referenz und zwei getrennte Aufgaben

Intrinsics beschreiben das Objektiv/den Sensor einschließlich Verzeichnung,
Extrinsics die Kamerapose im gemeinsamen Zellbezug. Die OAK-Werkskalibrierung
liefert Intrinsics und die Beziehungen der internen Sensoren, aber keine
Stativpose gegenüber unserer Zelle.

Einen Referenzframe an einem fest montierten Board oder am linken Tisch wählen.
Die Beziehung dieses Frames zum bisherigen `world` (Boden zwischen Tischmitten)
gesondert definieren/vermessen. Keine angenommene Simulationstischpose als realen
Messwert übernehmen. Die bestehende Wrist-Kalibrierung schätzt die Basisbeziehungen
pro Tisch; deren absolute Tischzuordnung hängt von der Boardmontage im Tisch ab.

## Empfohlener erster Ablauf

1. Boards maßhaltig drucken, tatsächliche Feldmaße prüfen und plan/steif montieren.
   Boardmontage am jeweiligen Tisch festhalten. Kameras auf ihrer späteren
   Position lassen, Betriebsauflösung/Crop festlegen, Arbeitsabstand fokussieren
   und anschließend Fokus fixieren. Profile an Seriennummer, Bildmodus und Fokus
   binden. Die USB-Zusatzkamera ist als OAK-D Pro AF identifiziert.
2. Passende Factory-Intrinsics auslesen und für den tatsächlichen Bildmodus
   validieren. Bei systematischen Abweichungen zusätzliche Intrinsics-Kalibrierung
   mit einem bewegten ChArUco-Board über Bildfläche, Neigungen und Arbeitsabstände.
   Keine Intrinsics aus nur einem stillliegenden Tischboard ableiten; keine
   EEPROM-Werte ungeprüft überschreiben.
3. Zunächst die OAK4 über dem bekannten linken Referenzboard extrinsisch einmessen.
   Mehrere stationäre Bilder robust auswerten. Bei bekannter Boardpose gilt
   `T_world_camera = T_world_board @ inverse(T_camera_board)`.
   `T_A_B` bildet Koordinaten aus B nach A ab. PnP verwendet Bildpunkte,
   metrische Boardpunkte und Intrinsics; keine Simulations-Ground-Truth zum Fit.
4. Sieht diese Kamera auch das rechte Board, lässt sich dessen Lage über
   `T_world_right_board = T_world_camera @ T_camera_right_board` bestimmen.
   So entsteht eine Messbrücke zwischen den beweglichen Tischgruppen. Für die
   Übertragung auf Roboterbasen deren separat erfasste Board-/Hand-Auge-Beziehungen
   benutzen; es existiert bisher nur ein Simulationsnachweis, keine bestätigte
   entsprechende Hardwarekalibrierung.
5. Jede Zusatzkamera über ein bereits eingemessenes Board oder gemeinsame
   Beobachtungen eines bewegten Kalibriertargets anbinden. Der Verbund aus Kameras
   und gemeinsamen Boardbeobachtungen muss zusammenhängend sein; nicht alle
   Kameras müssen dasselbe Board gleichzeitig sehen. Ein allein von einer
   isolierten Kamera beobachtetes, frei bewegtes Board liefert keine Beziehung
   zu den anderen Kameras.

## Verbesserte gemeinsame Schätzung

Für höhere Genauigkeit nach der ersten Registrierung ein zusätzliches, für die
Übersicht groß genuges, steifes Board an verschiedenen Positionen, Höhen und
Neigungen im Arbeitsraum aufnehmen; bei gemeinsamen bewegten Targets zeitlich
passende Bilder oder stationäre Haltephasen verwenden. Kameras bleiben fest.
Startumfang als Vorschlag etwa 20–40 ausreichend unterschiedliche Halteposen,
nicht bloß viele Bilder derselben Pose. Beispielsweise 20 % vorab für unabhängige
Validierung zurückhalten. Dies sind vorgeschlagene Startwerte, keine Vorgabe
des Nutzers oder garantierte Stichprobenzahl.

Mehrere Beobachtungen gemeinsam robust nach Reprojektionsfehler optimieren;
Kameraposen konstant, Targetpose je Haltepose variabel, mindestens ein
Referenzframe fixiert (sonst freie globale Lage). Bei schwacher Sicht der
Referenz weitere unabhängige räumliche Constraints ergänzen. Wiederholungen
eines unbewegten planaren Boards senken Zufallsrauschen, beseitigen aber weder
falsche Intrinsics noch schlechte Geometrie/Verzeichnung oder Maßfehler.

Das entfernte linke Tischboard hat in der aktuellen 2-m-Ansicht nur 12 erkannte
Ecken bei etwa 15 px Marker-Seitenlänge. Für Genauigkeit/Reserve ein größeres
zusätzliches Kalibrierboard oder eine nähere Zusatzansicht vorsehen; die
bestehenden PDF-Maße nicht ändern, ohne das metrische Boardmodell mitzuändern.

Eine spätere automatisierte Eye-to-Hand-Erfassung mit einem starr am Werkzeug
montierten Board ist möglich: verschiedene Roboterstellungen, bekannte oder
mitgeschätzte Tool-Board-Montage, gemeinsame Kamera-/Roboterbeziehung lösen.
Die Genauigkeit hängt dann auch von Roboterkinematik und Montage ab. Sie ist
eine zusätzliche Messroutine, kein bloßes Ausführen der vorhandenen Wrist-
Routine mit ausgetauschtem Kameratopic.

## Prüfen, speichern, nachführen

- Zurückgehaltene Bilder und unabhängige bekannte Abstände/Höhen im Arbeitsraum
  prüfen. Reprojektionsfehler in Pixeln und räumliche Abweichungen in mm/Grad
  getrennt ausweisen. Kleine Pixelresiduen beweisen allein keine mm-Genauigkeit.
- In der Simulation Ground Truth erst nach dem Fit vergleichen. In Realität
  keine Genauigkeit allein durch Wiederverwendung derselben Referenz bestätigen.
- RGB zuerst registrieren; andere OAK-Sensoren über deren Werks-Extrinsics und
  die tatsächlichen Raw-/Rectified-/Depth-Frames zuordnen. Bild-CameraInfo-TF-
  Konsistenz prüfen, nicht RGB und native Stereo-Frames gleichsetzen.
- Versionierte Profile mit Geräte-ID, Fokus, Betriebsmodus, Boardmaßen,
  Referenzdefinition, Rohdaten und Validierung speichern; explizite Übernahme.
  Nominale Simulationsmontagen von geschätzten Frames getrennt halten.
- Feste Tischboards als laufende Plausibilitätsprüfung verwenden. Verschobenes
  Stativ erfordert neue Kameraextrinsics; verschobener Tisch aktualisierte
  Tisch-/Board-/Basisbeziehungen. Geänderter Fokus/Bildmodus erfordert Prüfung
  passender Intrinsics. Bei möglichen Bewegungen von Kamera und Tisch helfen
  zusätzliche stabile Referenzmarker, die Ursache zu unterscheiden.

## Primärquellen

- [Luxonis Factory-/Stereo-Kalibrierung](https://docs.luxonis.com/hardware/platform/depth/manual-calibration)
- [Luxonis interne und virtuelle Kameraframes](https://docs.luxonis.com/software-v3/depthai/depthai-components/coordinate-systems)
- [OpenCV ChArUco-/Intrinsics-Kalibrierung](https://docs.opencv.org/4.9.0/da/d13/tutorial_aruco_calibration.html)
- [OpenCV ChArUco-Erkennung und Posen](https://docs.opencv.org/4.11.0/df/d4a/tutorial_charuco_detection.html)
