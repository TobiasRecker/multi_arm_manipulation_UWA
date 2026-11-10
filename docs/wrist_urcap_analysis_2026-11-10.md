# Wrist Camera: lokale Analyse von UCC1.11.3

Datum:2026-11-10, Australia/Perth. Nutzer stellt die Datei
`/home/rosmatch/Downloads/UCC-1.11.3_20210913.zip` zur Verfügung und bittet um
Untersuchung der Kamera-Steuerung ohne unbekanntes Admin-Kennwort.

**Nachfolgend umgesetzt und geprüft:**[Fokusfenster mit echten Schreib-/Bildtests](wrist_camera_focus.md).
Dieser Bericht beschreibt den vorherigen statischen Analysezeitpunkt; die dort
noch nicht ausgeführten Kameraaufrufe sind im Folgeauftrag überprüft worden.

## Ergebnis und Grenzen

**Eine interne HTTP-Schnittstelle für Fokus-/Kameraeinstellungen ist im Archiv
nachgewiesen. Die beiden lesenden Einstellungsabfragen funktionieren auf
right_rear ohne SSH-Authentifizierung.** Der Schreibaufruf ist statisch aus
dem Robotiq-Client rekonstruiert, aber noch nicht am echten Gerät ausgeführt.
Damit ist die frühere Aussage „keine dokumentierte Netzwerk-Fokusfunktion
gefunden“ als Stand der öffentlichen Recherche überholt: der konkrete Client
im Nutzerarchiv liefert jetzt Implementierungsnachweise. Eine öffentliche,
versionsstabile Hersteller-API ist damit nicht zugesagt.

Keine enthaltenen Installer, Daemons oder Kalibrierprogramme ausgeführt; keine
Fokuswerte, Kameraeinstellungen, Roboterprogramme oder Betriebszustände verändert.
Kein SSH-Zugang hergestellt. Die lokal analysierte Archivversion ist nicht
automatisch die nachgewiesene installierte URCap-Version.

## Untersuchte Bestandteile

- ArchivSHA256:`d68edbe2a6aa5506d2957d13a309a1195b576909314e2c020cb53f4c7d8a83d7`.
- `Robotiq_Wrist_Camera-1.11.3.13312.urcap`: ZIP/JAR, unverändert kopiert.
- Darin`OSGI-INF/lib/vision.core-1.0.0.jar`, insbesondere
  `com.robotiq.vision.client.CameraSettingsClient`,
  `com.robotiq.vision.client.model.response.CameraSettingsBody`,
  `com.robotiq.vision.gui.image.tool.cameraSetting.FocusViewController`.
- Client-Bytecode mit installiertem`javap -p -c` gelesen, nicht ausgeführt.
- Native`visionserver`-Datei statisch mit Strings/Symbolen/Disassembly geprüft:
  Setter parst JSON, kopiert bestehende Einstellungen, ruft
  `CameraSettings::fromJson` und`CameraSettingsApplyer::applyChanges` auf.
- Release Notes nennen fürUCC1.11.3 PolyScope3.15/5.11, für1.11.2/1.11.1 auch5.10.
  **Kein Update vorgenommen**; das Archiv wird nur als Informationsquelle genutzt.

## Rekonstruierte HTTP-Aufrufe

Basis am geprüften Gerät:`http://192.168.8.170:4242`.

| Methode/Pfad | Befund | Prüfung |
|---|---|---|
| GET`/getcamerasettings` | Antwort enthält`cameraSettings` und`status` | HTTP200,`succeeded`, echte Antwort gespeichert |
| GET`/getcamerasettingsdetails` | JSON-Typen der Einstellungsfelder | HTTP200,`succeeded`, echte Antwort gespeichert |
| POST`/setcamerasettings?setManualValuesIfModeChanged=true` | JSON-Objekt mit`cameraSettings`; boolescher Queryparameter wird vom Robotiq-Client gesetzt | Nur statisch nachgewiesen, nicht gesendet |
| POST`/trigger?focus=true&exposure=false&whiteBalance=false` | Client bietet gezielten Fokus-Trigger; Pendant-Fokusbutton ruft diesen Weg auf | Nur statisch nachgewiesen, nicht gesendet |
| GET`/triggerinprogress` | Client fragt laufende automatische Einstellung ab | Nur statisch nachgewiesen, nicht aufgerufen |

`setManualValuesIfModeChanged` ist im Client ein boolescher Parameter; ob er in
einem späteren konkreten Bedienfall true sein soll, muss passend zur gewünschten
Auto/Manual-Umschaltung geprüft werden. Vor Schreibtests aktuellen Zustand
sichern, nur beabsichtigte Felder verändern und über Antwort/Rücklesen plus
Bildwirkung prüfen. Keine Blindübernahme aller Beispiel-/Defaultwerte.

## Tatsächlich gelesene Einstellungen

Momentaufnahme der Serverkonfiguration:

```json
{
  "focus": 0,
  "focusAuto": true,
  "focusMin": 150,
  "focusMax": 1023,
  "focusStep": 24,
  "focusSensitivity": 10,
  "focusStrategy": 0,
  "focusWindowEnabled": 3,
  "focusWindowX1": 192,
  "focusWindowX2": 448,
  "focusWindowY1": 144,
  "focusWindowY2": 336
}
```

`focus:0` bei aktivem Auto-Modus ist kein Nachweis einer tatsächlichen
Linsenposition oder falschen Schärfe. Insbesondere ist der Wert kein Meterwert.
Die Bedeutung des numerischen`focusWindowEnabled`-Modus ist noch nicht geprüft.
`focusMin/Max` sind Konfigurationsparameter des Suchbereichs, kein unabhängig
gemessener gültiger Hardwarebereich. Die Details-Abfrage meldet für Integer
generisch−2147483648 bis2147483647; das sind **keine brauchbaren Linsengrenzen**.

## Fokusregler aus dem Originalclient

`FocusViewController` erzeugt einen Regler mit Bereich0…1023, Schritt1,
Initialwert512 und leerer Einheit. `setManualSettings` sowie
`onFocusSpinboxTriggered` verwenden in beide Richtungen:

```text
angezeigter Reglerwert = 1023 - API-Fokuswert
API-Fokuswert         = 1023 - angezeigter Reglerwert
```

`writeControlMode` setzt`focusAuto`; der Triggerbutton fordert nur Fokus,
nicht Belichtung oder Weißabgleich an. Ein eigener Schieberegler kann diesen
Bedienpfad nachbilden. Seine tatsächliche Wirkung und Rückkehr zum Ausgangswert
müssen anschließend separat am Gerät nachgewiesen werden. Für spätere
Hand-Auge-Messungen Fokus und dazu passende Intrinsics konstant halten.

## SSH-Schlüssel und unbekanntes Admin-Kennwort

Regulärer Weg bei PolyScope5.10+: auf dem PC Schlüsselpaar erzeugen, **nur den
Public Key** per USB übertragen, am Pendant unterSettings→Security→Secure Shell
nach Admin-Entsperrung überManage Authorized Keys hinzufügen. Bestehende
Anmeldemethoden anderer Nutzer nicht ungeprüft entfernen.

Da das Admin-Kennwort laut Nutzer derzeit unbekannt ist, ersetzt diese Anleitung
keine gültige Admin-Anmeldung. Meine frühere Empfehlung eines Schlüssels war
in diesem Punkt unvollständig. Für die jetzt entdeckte Kamera-HTTP-Schnittstelle
ist dieser SSH-Weg momentan nicht erforderlich. Keine Passwortwiederherstellung
oder Änderung an Anmeldedaten unternommen.

[Offizieller UR-Schlüsselimport und Admin-Schutz](https://www.universal-robots.com/articles/ur/cybersecurity/secure-setup-of-ur-cobots/).

## Lokale Nachweise

`$UWA_WS/setup/logs/wrist-urcap-2026-11-10/` enthält Originalkopien/Auszüge,
`camera-settings-javap.txt`, `focus-controller-javap.txt`,
`camera-service-javap.txt`, native Disassembly sowie die beiden echten
`getcamerasettings*.json`-Antworten. Herstellerbinaries und vollständiger
Bytecode bleiben außerhalb des Repositorys; eingecheckt wird nur diese eigene
Befundbeschreibung. Prüfung: Archiv/Bytecode/JSON gelesen, kein Build oder
Bewegungstest erforderlich, kein Fokus-Schreibtest behauptet.
