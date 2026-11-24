# Supported carton grasp mit zwei OAK-Kameras

Stand 24.11.2026. Das Library-Programm nutzt neben der Ethernet-OAK4 optional
die gegenüberliegende **OAK-D Pro AF** am N100 (kurz OAK Pro). Beide messen
denselben bekannten, auf dem rechten Tisch stehenden Karton. Die Ermittlung
der Pose läuft auf ROSmini; N100 übernimmt die USB-Aufnahme und weiterhin
die bisherige Robotersteuerung.

| Bildbefund | Verwendete Pose |
| --- | --- |
| Beide unabhängigen geometrischen Fits gültig und übereinstimmend | Gleiches Gewicht: mittlere Position und sphärischer Orientierungsmittelwert |
| Nur ein geometrischer Fit gültig, andere Ansicht bestätigt den projizierten Karton | Unveränderte Pose der gültigen Kamera |
| Nur ein geometrischer Fit gültig, andere Ansicht verdeckt, unklar oder nicht verfügbar | Unveränderte gültige Einzelpose, fehlende Bestätigung ausdrücklich ausgewiesen |
| Zwei gültige Posen widersprechen sich oder zweite Ansicht zeigt einen klaren Widerspruch | Keine Pose für die Bahnplanung |
| Keine gültige Einzelpose | Keine Pose für die Bahnplanung |

Eine gültige Einzelpose verlangt unverändert lokale Bildmerkmale, die
vorhandenen Inlier-/Projektionskriterien, Tischauflage und mindestens zwei
übereinstimmende Bildhypothesen. Gemini-Konfidenz ersetzt diese Nachweise
nicht. Für den Vergleich der beiden Kameraposen gelten zunächst dieselben
Übereinstimmungsgrenzen wie innerhalb einer Registrierung: **unter 10 mm
und unter 2°**, nicht einschließlich der Grenze. Keine gelockerte Pose geht
in den Mittelwert ein. Die beiden Kameras und die Originalpixel werden
getrennt protokolliert und über Prüfsummen an die ausgewählte Pose gebunden.

Hydrogen Low kann je Kamera wie bisher bis zu drei gezielte Nachmessungen
anfordern. OAK Pro hat eigene native Pixelkoordinaten und Suchbereiche,
keinen OAK4-Suchfenstercache. Reicht ihr geometrischer Fit nicht aus,
erhält Gemini das unveränderte Bild und eine getrennte Projektion der aus
der anderen Kamera bestimmten Kartonhülle. Es unterscheidet `confirmed`,
`occluded`, `uncertain` und `contradicted`, ohne eine metrische Pose zu
liefern. Das Overlay allein gilt ausdrücklich nicht als Bildnachweis.
Unklare oder ausgefallene Zusatzprüfung erhöht die bisherige Einzelbild-
Konfidenz nicht und ist im Laufbericht sichtbar.

## Bedienung und Referenzen

**Program library → OAK camera calibration → Start calibration** bestimmt
weiterhin zuerst die OAK4-Referenz und zusätzlich die konfigurierte OAK Pro.
Jede Referenz läuft zwölf Stunden ab ihrer eigenen Aufnahme. Bei gültigen
Referenzen wird das Tischboard beim Kartonstart nicht erneut geprüft.
Nach Verstellen einer Kamera oder des Boards neu kalibrieren. Scheitert
die USB-Referenz, wird dies angezeigt; die gültige OAK4-Referenz bleibt nutzbar.

**Supported carton grasp → Start program** nimmt beide nativen Ansichten
vor der Registrierung auf. Den Karton während der Aufnahmen still halten;
die Aufnahmen sind nacheinander, keine synchronisierte Stereomessung. Im
Laufstatus erscheinen `TWO ACCEPTED VIEWS`, `SINGLE POSE` oder `POSE REJECTED`
sowie Messquelle, Zweitbildbefund und verfügbare Bildlinks. Die aktuelle
offene Einfahrt wird weiterhin mit der OAK4 für die Kontaktprüfung aufgenommen.
Auch bei einer ausschließlich aus der OAK Pro bestimmten Kartonpose bleibt
die vorhandene OAK4-Aufnahmeanbindung für diesen Bedienpfad erforderlich.

Aktive lokale Konfiguration: `setup/skill_library/live-carton.json`, darin
`secondary_camera: "carton-usb.json"`. Die zweite Datei enthält `enabled`,
`intrinsics`, `roi`, `face_roi`, `camera_session`, `planar_texture` und
`gemini_enabled`. Der Nutzer hat den externen Bildversand an Hydrogen über
Antigravity für diese Zweikamera-Kartonauswertung ausdrücklich erlaubt;
`gemini_enabled` ist in der lokalen USB-Datei daher `true`. Pfade sind
relativ zur jeweiligen Konfigurationsdatei. USB-Sitzung:
`setup/skill_library/carton-usb-camera-session.json`. Optik:
`config/carton_usb_intrinsics_112.json`, übernommen aus der getrennten
Kamerapaar-Auswertung vom 23.11., Geräte-ID `18443010314F3B1300`, Fokus 112,
4056 × 3040. Rohbilder bleiben trotz kopfüber montierter Kamera ungedreht.

Je Lauf liegen `multiview-input.json`, `multiview/decision.json`, die gebundene
`multiview/object-pose.json` und die getrennten Registrierungen vor.
`oak-usb/initial-photo/native/` bewahrt unveränderte USB-Metadaten, Kamerabackup
und Originalbild. Normalisierte Metadaten geben die Arbeitsplatz-Auftragszeit
als konservative Zeituntergrenze an, keinen synchronisierten Belichtungszeitpunkt.

Mittelung ist noch kein Nachweis höherer absoluter Genauigkeit. Gemeinsame
Board-/Modellfehler können beide Ansichten betreffen. Die Genauigkeit am
Karton muss gesondert anhand realer Vergleichsmessungen beurteilt werden.
Geschwindigkeit, Bewegungsfreigaben, aktuelle Einfahrbildentscheidung und
bestehende Schutzkette gehören weiterhin zum bisherigen Kartonablauf.

## Prüfergebnis vom 24.11.2026

35 gezielte Offline-Softwareprüfungen bestanden. Aktuelle native Aufnahmen
beider Kameras zeigten eine annähernde 180°-Mehrdeutigkeit der eigenständigen
Kartonfits. Auch die nur diagnostische Rechtecksymmetrie-Gegenprobe liegt mit
10,679 mm und 2,253° knapp außerhalb der bisherigen Grenzen. Diese aktuelle
Zweibildmessung liefert deshalb keine Mittelpose. Die Zuordnung der
gegenüberliegenden Wand zum gemeinsamen Kartonframe bleibt offen.

Der reale zusätzliche Hydrogen-Low-Bildcheck bestätigte den Karton im
OAK-Pro-Bild an der aus OAK4 projizierten Stelle. Dieser Anwesenheitsbefund
setzt den widersprüchlichen metrischen Vergleich nicht außer Kraft.
Kein Roboterprogramm oder Fahrziel für diese Prüfung gestartet.
Nachweise: `setup/tasks/carton-multiview-20261124/`.
