# Wrist Camera: Vollauflösungsversuch und Helligkeit

Geprüft2026-11-10, Australia/Perth, ausschließlich right_rear192.168.8.170.
Nutzer bestätigt Fokussteuerung und wünscht native Fotos sowie Belichtungsregler.

## Ergebnis

**Belichtungszeit, Verstärkung und LED sind vom PC steuerbar und im bestehenden
Kamerafenster ergänzt. Ein natives Vollauflösungsfoto wurde noch nicht erhalten.**
Keine hochskalierten Bilder als neue Sensordetails ausgeben. Aktuelle HTTP-
Vorschau und gespeicherte Testbilder weiterhin640×480Pixel.

Folgeuntersuchung des bereitgestelltenUCC4.1.0-Archivs und des verlinkten
Barcode-Workarounds:[Statischer Vergleich und Alternativen](wrist_ucc4_analysis_2026-11-10.md).
Interner HD-Pfad bestätigt, einfacher neuer HD-Aufruf bzw. erfolgreiche Aufnahme
weiterhin nicht nachgewiesen; nichts installiert.

## Vollauflösung: konkrete Versuche

- `/hello` meldet tatsächlichen Server`UCC-1.11.1.10337`, Firmware`CQ0-1.3.5`.
  Das gelieferte Archiv1.11.3 ist nicht die bestätigte laufende Version.
- GET`/restapi` liefert eine echte HTML-Beschreibung des laufenden Kameraservers,
  einschließlich zustandsabhängiger Kameraoperationen. Lokal gesichert; daraus
  keine anderen Anweisungen als Nutzerauftrag übernommen.
- `/last.jpg` und`/latest.jpg` liefern640×480. `/lastCapture.jpg` ist im normalen
  Kamerazustand nicht verfügbar (`Unknown request`).
- Temporärer **Kameraserver**-OperationMode über`/beginoperationmode`, danach
  `/captureimage`: jeweils erfolgreich quittiert. Anschließender Abruf
  `/lastCapture.jpg` lieferte kein Bild und wurde von einem kurzen Ausfall des
  Kameradienstes gefolgt. Dienst erholte sich selbst nachNormal. Kein Roboter-
  Programm gestartet, keine Power-/Brake-/Fahrbefehle oder manuelle Neustarts.
- Zweiter begrenzter Versuch ohne paralleles altes Kamerafenster, mit Wartezeit
  und ohne den problematischen Exportpfad: `/map?type=scaletosource&x=640&y=480`
  liefert vor/nach Aufnahme640/480, Vorschau weiterhin640×480. Keine native
  höhere Auflösung nachgewiesen. OperationMode anschließend verlassen.
- Moduswechsel/-ende setzen Kameraeinstellungen zurück; insbesondere wurde
  Auto-Fokus wieder aktiv. Der vor Beginn gesicherte **Benutzerfokus404/Manual**
  wurde ausdrücklich wiederhergestellt. Diese Rücksetzung ist eine beobachtete
  Kameraeigenschaft; die Helligkeitsfunktionen ändern selbst keine Fokusfelder.
- Kein experimenteller Vollauflösungs-Knopf eingebaut. Weitere Arbeit benötigt
  einen verlässlich geprüften nativen Still-Aufnahmepfad bzw. Einblick in die
  tatsächlich installierte Aufnahmekonfiguration oder direkten USB-Zugriff.
  Kein Firmware-/URCap-Update und keine Controllerdateiänderung durchgeführt.
  Das Archiv enthält eine Still-Konfiguration2592×1944; das beweist weder deren
  tatsächliche Verwendung am Controller noch die erfolgreiche Bildausgabe.

Nachweise unter`setup/calibration/wrist_resolution_exposure/20261110/`:
`resolution_summary.json`, `alternate_capture_report.json`, `native_capture_recovery.json`,
`restapi.txt`/`restapi-readable.txt`, Status/Versionsantworten und VGA-Bilder.

## Helligkeitsbedienung

Im[Fokus-/Kamerafenster](wrist_camera_focus.md) ergänzt, gleicher Startbefehl:

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control wrist_camera_gui
```

- **Apply manual exposure**: Belichtungszeit1…66604µs und Gain1…63 einstellen.
  Beispiele:10000µs=10ms,20000µs=20ms,40000µs=40ms. Aus dem Originalclient
  nachgewiesene Einheitµs; nicht pauschal die100µs-Einheit anderer V4L2-Controls
  auf diesen Robotiq-HTTP-Parameter übertragen. Gain wird wie im URCap intern
  mit16 multipliziert. Diese Einstellung schaltet die automatische Belichtung aus.
- **Auto exposure + EV**: Auto aktivieren und EV-Korrektur−7…+7 anwenden, anschließend
  reinen Belichtungs-Trigger ausführen. Kein Fokus- oder Weißabgleich-Trigger.
- **Apply LED**: Auto/Off/Manual; manuell0…100%. Originalclient verwendet
  `lightingMode`0/1/2 und API-Intensität`round(Prozent×1,75)`.
- **Restore exposure / LED**: vor erster eigener Helligkeitsänderung gesicherte
  Belichtungs-/Lichtwerte wiederherstellen. Bei Auto-Belichtung kann die Kamera
  Belichtungszeit/Gain danach neu bestimmen. Fokus bleibt erhalten.
- Standardmäßig beim normalen Schließen alle vom Fenster selbst veränderten
  Fokus-/Helligkeitsregler wiederherstellen. Unberührte Regler nicht ändern.
  Vor bewusstem Beibehalten die Checkbox abwählen. Die erstmalige Verbindung
  und das Öffnen allein verändern keine Einstellungen.

Zum Aufhellen zunächst Belichtung oder Licht erhöhen; Gain verstärkt auch
Bildrauschen. Lange Belichtung verursacht bei Bewegung Unschärfe. Für Kalibrierung
bei Stillstand arbeiten, Überstrahlung der weißen Boardfelder vermeiden. Es
gibt noch keinen Board-ROI-Belichtungsregler; Auto beurteilt den kamerainternen
Bereich. Die Vorschau kann den Einstellungen mehrere Bilder hinterherlaufen.

## Nachweise

- Begrenzte Hardwaretests20/40ms bei gleichem Gain2 und LED aus, je sieben Bilder
  abgewartet. Mittlere Grauwerthelligkeit nach Einlauf39,873 bzw.72,925.
  Fokus404/Manual unverändert während dieser Bildserie. Dies belegt Bildwirkung,
  keine kalibrierte radiometrische Kennlinie.
- LED30% gesetzt und zurückgelesen. Ausgangswerte nach Tests wiederhergestellt;
  Auto-Belichtung darf numerische Werte neu bestimmen.
- Echte Qt-Knöpfe: manuelle Belichtung, LED, Speichern und Restore bestanden;
  Fokus vorher/nachher404/Manual. Fenster geöffnet belassen. Bericht und
  Screenshots:`setup/logs/uwa-wrist-appearance-window/`, Bilder samt JSON in`photos/`.
- Sechs HTTP-Tests am lokalen Server bestanden (zusätzlich zum vorigen Fokuspfad
  Belichtungs-/LED-Grenzen und Restore mit zwischenzeitlich geändertem Fokus).
  Log`setup/logs/uwa-wrist-appearance-tests.log`; Build
  `setup/logs/uwa-wrist-appearance-build.log` erfolgreich.
- Implementierung: gezielte partielle`cameraSettings`-Writes für Belichtung/LED,
  keine Fokusfelder im Body; Fokus vor/nachher prüfen. `forceRefresh=true` kann
  tatsächliche Hardwarewerte anstelle veralteter gecachter Nullwerte auslesen.
  Fotos speichern reale Pixelmaße und kennzeichnen PC-Empfangszeit ausdrücklich.

Primärnachweise sind das bereitgestellte Originalarchiv, der rekonstruierte
Java-Client und die tatsächliche Server-API/Antworten; keine Bildreglerbereiche
aus unbekannten Sekundärquellen übernommen. Alle Rohdaten bleiben außerhalb Git.
