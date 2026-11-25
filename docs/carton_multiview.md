# Supported carton grasp mit zwei OAK-Kameras

Stand 24.11.2026. Das Library-Programm nutzt neben der Ethernet-OAK4 optional
die gegenüberliegende **OAK-D Pro AF** am N100 (kurz OAK Pro). Beide messen
denselben bekannten, auf dem rechten Tisch stehenden Karton. Die Ermittlung
der Pose läuft auf ROSmini; N100 übernimmt die USB-Aufnahme und weiterhin
die bisherige Robotersteuerung.

| Bildbefund | Verwendete Pose |
| --- | --- |
| Beide unabhängigen geometrischen Fits gültig und übereinstimmend | OAK4-Pose unverändert, OAK Pro als Gegenprüfung |
| Nur ein geometrischer Fit gültig, andere Ansicht bestätigt den projizierten Karton | Unveränderte Pose der gültigen Kamera |
| Nur ein geometrischer Fit gültig, andere Ansicht verdeckt, unklar oder nicht verfügbar | Unveränderte gültige Einzelpose, fehlende Bestätigung ausdrücklich ausgewiesen |
| Zwei gültige Posen widersprechen sich oder zweite Ansicht zeigt einen klaren Widerspruch | Keine Pose für die Bahnplanung |
| Keine gültige Einzelpose | Keine Pose für die Bahnplanung |

Eine gültige Einzelpose verlangt unverändert lokale Bildmerkmale, die
vorhandenen Inlier-/Projektionskriterien, Tischauflage und mindestens zwei
übereinstimmende Bildhypothesen. Gemini-Konfidenz ersetzt diese Nachweise
nicht. Nutzerentscheidung24.11. zum Zentrum und Ergänzung25.11. zum Winkel:
Der kamerübergreifende Vergleich erlaubt **Mittelpunktabweichung bis
einschließlich30mm und Winkelabweichung bis einschließlich3°**. Die strengeren Kriterien innerhalb einer Einzelbildregistrierung
bleiben erhalten. Auf Nutzerkorrektur vom
24.11. werden die aufrechten180°-Darstellungen vorher als gleichwertig
zugeordnet. Die zweite Pose bleibt beim selben physischen Karton, ihr
Eckursprung wird mit umgerechnet. Verglichen werden die Positionen des
Grundflächenmittelpunkts und die so angeglichenen Rotationen im gemeinsamen
Zellkoordinatensystem. Bei zwei gültigen Fits wird die OAK4-Pose verwendet,
einschließlich unveränderter Armtransformationen; die USB-Pose wird nicht
eingemittelt.90° gilt bei diesem rechteckigen Karton nicht
als Symmetrie. Alle vier Wände sind laut Nutzer bedruckt; eine eindeutige
Vorderseite ist für diesen Griff nicht erforderlich. OAK4 wird auf Nutzerwunsch
bevorzugt; ihre höhere Genauigkeit ist dadurch nicht neu nachgewiesen.
Die beiden Kameras und die Originalpixel werden
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
Laufstatus erscheinen `OAK4 POSE · Second view checked · Centre limit 30 mm`,
`SINGLE POSE` oder `POSE REJECTED`
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

Die Gegenprüfung ist kein Nachweis höherer absoluter Genauigkeit. Gemeinsame
Board-/Modellfehler können beide Ansichten betreffen. Die Genauigkeit am
Karton muss gesondert anhand realer Vergleichsmessungen beurteilt werden.
Geschwindigkeit, Bewegungsfreigaben, aktuelle Einfahrbildentscheidung und
bestehende Schutzkette gehören weiterhin zum bisherigen Kartonablauf.

## Prüfergebnis vom 24.11.2026

31gezielte Kalibrier-/Multiviewprüfungen für die aktuelle OAK4-Vorrangregel
bestanden:30mm akzeptiert, darüber abgelehnt, Winkelgrenze und180°-
Zuordnung erhalten, keine Verschiebung oder Rotation der OAK4-Pose und
keine Abhängigkeit von der Reihenfolge im Bildmanifest. Offline-Nachlauf
von Lauf `1bcfd25ade114d5fb8e0d834b7bcc3a3`:14,392mm/1,304° akzeptiert,
OAK4-Pose und beide Armbindungen exakt erhalten.

Historischer Stand vor dieser Nutzerentscheidung:

Die180°-Gleichwertigkeit ist berücksichtigt und mit28 gezielten
Kalibrier-/Multiviewtests geprüft. Die aktuellen Aufnahmen aus Library-Lauf
`7e14069f070d442e9a2bbd236aab01a2` verbleiben danach bei12,987mm Abstand
der Grundflächenmittelpunkte und2,954° Restwinkel. Sie werden weiterhin
abgelehnt. Der halbe Meter Rohabstand gehörte größtenteils zu zwei
unterschiedlich benannten Eckursprüngen, nicht zu zwei physischen Kartons.
`pose_comparison` im Entscheidungsbericht nennt Roh- und Restabweichung
sowie die angewendete180°-Zuordnung. Es ist keine weitere Toleranz freigegeben.

Vor der Symmetriebehandlung bestanden35 gezielte Offline-Softwareprüfungen.
Damals ausgewertete native Aufnahmen
beider Kameras zeigten eine annähernde 180°-Mehrdeutigkeit der eigenständigen
Kartonfits. Auch die nur diagnostische Rechtecksymmetrie-Gegenprobe liegt mit
10,679 mm und 2,253° knapp außerhalb der bisherigen Grenzen. Diese aktuelle
Zweibildmessung lieferte deshalb keine Mittelpose. Die damalige Forderung
nach eindeutiger Vorder-/Rückseitenzuordnung ist durch die Nutzerkorrektur
überholt; offen bleibt die tatsächliche metrische Übereinstimmung.

Der reale zusätzliche Hydrogen-Low-Bildcheck bestätigte den Karton im
OAK-Pro-Bild an der aus OAK4 projizierten Stelle. Dieser Anwesenheitsbefund
setzt den widersprüchlichen metrischen Vergleich nicht außer Kraft.
Kein Roboterprogramm oder Fahrziel für diese Prüfung gestartet.
Nachweise: `setup/tasks/carton-multiview-20261124/`.
