# OAK4-Kamerapose als Library-Programm

Stand 24.11.2026. **OAK4 camera calibration** (`oak4-camera-calibration-v1`)
bestimmt die Kamerapose relativ zum festen rechten Tischboard und veröffentlicht
die gemeinsame Referenz für zwölf Stunden ab Aufnahme.

## Bedienung

1. Die [Programmbibliothek](http://127.0.0.1:8780/#library) auf ROSmini öffnen.
   Eine bereits geöffnete Seite einmal neu laden.
2. **OAK4 camera calibration → Open program → Start calibration** wählen.
3. Rechtes Tischboard vollständig sichtbar halten; Kamera und Board während
   der Aufnahme nicht verstellen. Eine belegende Vorschau vorher regulär
   pausieren. Das Programm benötigt keine Roboterdienste.
4. Nach **COMPLETE** zeigt die Seite **REFERENCE VALID** und das Ablaufdatum
   in AWST. Vorschau und Prüf-RMS stehen im Ergebnis.

Das Programm nimmt zunächst ein natives Standardfoto mit dem Fokus aus
dem hinterlegten Intrinsics-Profil auf. OpenCV prüft den Fit des rechten
Boards an zurückgehaltenen Markern. Mindestens zwölf eindeutige Marker
und weniger als 2 px Prüf-RMS sind erforderlich. Falls der Fit aus
diesem Bild nicht genügt, übernimmt der ChArUco-Suchdienst die
Fokus- und Belichtungssuche. [ChArUco-Suchmodus](../../oak_camera_calibration/OAK4_CHARUCO_SEARCH.md)

## Gemeinsame Gültigkeit

Die aktuelle Sitzung bleibt unter `setup/skill_library/carton-camera-session.json`
im Workspace. Der vorhandene Dateiname bleibt für die bisherigen Verbraucher
kompatibel. Weitere Programme verwenden dieselbe Sitzung und den vorhandenen
Baustein `carton_camera_session.validate_session`.

- `valid_from` stammt aus dem Aufnahmevorgang. Beim Einzelbild ist es
  der protokollierte Triggerzeitpunkt, bei der Suche der Kameraschluss.
  `valid_until` liegt genau zwölf Stunden danach. Lesen oder Ausführen
  verlängert die Frist nicht. Alte Laufkopien sind historische Nachweise.
- Kamera-ID, Fokus, native Optik, Boarddefinition und übernommene
  Basisbindungen sind an die Sitzung gebunden.
- Nach Verstellen von Kamera oder Board **vor dem nächsten Greifen neu
  kalibrieren**. Eine physische Änderung wird ohne neue Aufnahme nicht erkannt.
- Beginn einer neuen Kalibrierung widerruft die alte Referenz. Bei einem
  Fehler wird sie nicht erneut freigegeben. Erst nach vollständiger
  Ergebnisablage samt Vorschau wird die neue Sitzung atomar veröffentlicht.
- Nach Ablauf zeigt die Library **CALIBRATION REQUIRED**. Der vorhandene
  Verbraucher prüft die Frist beim Start und bei der Verwendung.

Das Kartonprogramm nutzt dieselbe gültige Referenz ohne erneute Prüfung des
Tischboards im Kartonbild. Aktuelle Kartonaufnahme, Posefit und tatsächliches
offenes Einfahrbild bleiben Teil seines Ablaufs. Kalibrieren löst keine
Bewegungs- oder Kontaktfreigabe aus.

## Schnittstelle und Dateien

`GET /api/catalog` enthält den eigenen Programmeintrag und `camera_reference`
mit Status und Zeitraum. Start über den üblichen Library-Endpunkt:

```json
{"program":"oak4-camera-calibration-v1","mode":"calibrate"}
```

Dieser Programmeintrag unterstützt ausschließlich `calibrate`, keine
Roboter-Live- oder Demoausführung. Laufdaten unter
`setup/tasks/uwa_program_library/<ID>/`: `progress.json`, `run.log`,
`camera-session.json`, `camera-preview.jpg`. Die Oberfläche meldet RUNNING,
COMPLETE oder FAILED als deutlichen Text.

Bereits laufende ältere Server eines offenen Power-Fensters können den
Eintrag nach Neuladen über den bisherigen Kalibrieraufruf anzeigen. Der
aktualisierte Server auf8780 führt die neue Programm-ID direkt. Das
Power-Fenster muss dafür nicht neu gestartet werden.

## Prüfnachweis20.11.2026

Sechs gezielte Offline-Tests prüfen Katalog, ausschließlich Kalibriermodus,
Dispatch, exakte12h-Ablaufgrenze ohne Erneuerung und vollständige
Veröffentlichung. JavaScript-Syntax und Zuordnung älterer Server wurden
im Node-VM geprüft. CUA-Browserzugriff war nicht verfügbar; HTTP-Schnittstellen
und Programmablauf wurden direkt geprüft.

Realer Library-Lauf `043a0df2880b41a69d08370275014118` erfolgreich:
17Marker/1,53px Prüf-RMS, gültig20.11.17:50:42 bis21.11.05:50:42 AWST.
Nachweise `setup/tasks/camera_library_program_20261120/` und der originale
Library-Laufordner. Keine Roboter gestartet oder bewegt.

## Erweiterung 24.11.2026

Der sichtbare Library-Titel lautet jetzt **OAK camera calibration**; die
Programm-ID `oak4-camera-calibration-v1` bleibt bestehen. Bei konfigurierter
OAK Pro wird zusätzlich eine eigene zwölfstündige USB-Referenz aufgenommen.
Die optischen Profile und Fristen bleiben je Kamera getrennt.
[Bedienung des Zweikamera-Kartongriffs](carton_multiview.md).
