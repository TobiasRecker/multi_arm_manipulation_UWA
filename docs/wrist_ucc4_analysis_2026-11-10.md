# UCC4.1.0: HD-Fotofunktionen und Alternativen

Statische Untersuchung2026-11-10, Australia/Perth. Nutzerdatei
`/home/rosmatch/Downloads/UCC-4.1.0.zip`, SHA256
`dc83962080d1ac2924e9a66529057aff753f0929ee981a97e47d34c01fcbbbaa`.
Enthält`Robotiq_Wrist_Camera-4.1.0.164735.urcap`. **Nicht installiert**, kein
enthaltener Installer/Daemon ausgeführt; bestehende Kameraeinstellungen und
geöffnetes Bedienfenster erhalten.

**Folgetest am selben Tag:** Nutzer hat danach ein Kamerazeitfenster freigegeben;
der[praktische HD-Modultest](wrist_hd_probe_2026-11-10.md) wurde ausgeführt.
Modulerzeugung akzeptiert, Verarbeitung mit49156 abgewiesen; kein nativesHD-Foto,
Einstellungen wiederhergestellt. DasUCC4-Archiv wurde weiterhin nicht installiert.

## Antwort auf die Nutzerfrage

**Interne HD-Aufnahmefunktionen vorhanden, aber kein neuer einfacher,
frei konfigurierbarer Vollauflösungs-Fotoaufruf nachgewiesen.** Aus diesem Archiv
allein folgt weder ein funktionierender5MP-Download noch eine Empfehlung,
den laufenden URCap zu aktualisieren. Der aktuell laufende Server ist laut
vorheriger tatsächlicher Abfrage1.11.1.10337; die Archivversion ist davon getrennt.

## Was das verlinkte Thema beschreibt

Der[Robotiq-Beitrag vom2020-11-06](https://dof.robotiq.com/discussion/2227/wrist-camera-connection-to-external-application-with-full-resolution)
nennt keinen direkten5MP-Ethernet-Bildabruf. Der Support beschreibt stattdessen
Scan-Code-/Barcode-Knoten für die5MP-Aufnahme, danach Save Image zum Speichern
des letzten Bildes und anschließenden Dateitransfer zum PC.
Dies ist genau der vom Nutzer als unattraktiv bezeichnete Workaround;
nicht als neue eigene Lösung präsentieren.

## Was im neuen Archiv nachgewiesen ist

- Eingebettetes`vision.core-1.0.0.jar` mit`VisionClient`: Methode
  `captureImageInOperationMode` ruft weiter`/captureimage` ohne zusätzliche
  Auflösungs-/HD-Parameter auf.
- Native, dynamisch sichtbare Funktionen`VisionManager::captureHDImage`,
  `currentImageHD`, `getLastCapture`; also ein echter interner HD-Pufferpfad.
  Solche HD-Funktionen existieren bereits im früher untersuchten1.11.3-Archiv.
- `VisionServerStateOperationMode::processCaptureImageRestRequest` verwendet
  weiterhin`VisionManager::captureImage`, nicht direkt`captureHDImage`.
  Sein expliziter Queryvalidator ist leer; kein frei wählbarer`HD=true`- oder
  Width/Height-Parameter an diesem untersuchten Aufruf nachgewiesen.
- `VisionServerStateModule::captureImage` enthält getrennte Aufrufe für normale
  und HD-Aufnahme. Das ist ein Ansatzpunkt für eine modulgesteuerte PC-Aufnahme,
  noch kein funktionsfähiger, geprüfter Workflow.
- `/lastCapture.jpg` greift auf`getLastCapture` zu. Diese Funktion unterscheidet
  weiterhin zwischen normalem Bild und HD-Puffer anhand des letzten Aufnahmetyps.
  Sie löst selbst keine neue HD-Aufnahme aus. Ein größer eingestelltes Display
  allein erzeugt ebenfalls keinen nativen höheren Detailgehalt.
- `/exportlastcapture` bleibt ein Dateiexportpfad; ein vorhandener Endpunkt
  beweist keinen externen Download ohne vorgelagerte gültige HD-Aufnahme.
- Die enthaltene`videoconfig.rcf` nennt Video640×480 und Still2592×1944. Das ist
  eine Paketkonfiguration, kein Nachweis, dass die installierte Kamera damit
  tatsächlich ein5MP-Bild liefert. Zusätzliche erkennbare Pfade
  `/getcameralist`/`/selectcamera` betreffen Kameraauswahl, keinen HD-Nachweis.
- Keine vollständigen Kompatibilitäts-/Migrationsnachweise für die installierte
  PolyScope5.10.1 aus dem Archiv abgeleitet. Nichts aktualisiert oder neu gestartet.

## Andere Möglichkeiten: Priorität und Grenzen

1. **Direkter PC-Aufruf des internen HD-Modulpfads.** Temporäre Kamera-/Scan-Code-
   Operation per HTTP statt grafischem PolyScope-Programm, anschließend gültigen
   HD-Puffer direkt über HTTP herunterladen. Das könnte Speicherknoten, Dateien
   auf dem Controller und FTP vermeiden. Es verwendet weiterhin den internen
   HD-Pfad der Scan-Code-/Modulfunktion; nicht als unabhängig davon darstellen.
   Bisher keine geprüfte Aufrufsequenz, kein Bildnachweis. Nach vorherigem
   Dienstabbruch nicht blind `/lastCapture.jpg` wiederholt aufrufen.
2. **Controller-Aufnahmekonfiguration gezielt untersuchen.** Mit legitimem
   SSH-/Dateizugriff prüfen, ob ein nativer hochauflösender Modus ohne Modulpfad
   möglich ist. Eine Änderung kann Vorschau/URCap-Verarbeitung beeinflussen;
   derzeit keine Änderung ausgeführt, gültiger SSH-Zugang fehlt weiterhin.
3. **Direktes USB zum PC.** Native angebotene UVC-Modi am Gerät prüfen und ein
   Bild tatsächlich decodieren. Dafür Verbindung ändern; die inzwischen gut
   funktionierenden Robotiq-Fokus-/LED-Controls stehen dann nicht automatisch
   über denselben Controller-HTTP-Pfad bereit. Eigene Steuerung wäre erneut zu
   prüfen. Kein ungeprüftes FullHD-/5MP-Versprechen.

Empfehlung: zunächst Möglichkeit1 untersuchen, ohne blind aufUCC4.1.0 zu wechseln.
Das ist Forschungs-/Integrationsarbeit, noch kein implementierter HD-Button.
Wird dieser Weg unzuverlässig, zwischen legitimem Controllerzugriff und USB
entscheiden. Der Nutzer wünscht Erhalt der gut funktionierenden Beleuchtung;
in dieser Analyse keine Bild-/Fokus-/LED-Werte verändert.

### Konkretisierung auf Nutzerfrage: noch keine ausführbare Anleitung

Die bereits lokal gesicherte API des laufenden1.11.1-Servers enthält
`POST /beginbarcode`, im Barcodezustand`POST /create?barcodeType=<0…11>` und
`/process`, außerdem`/streamoutmodule` und`/streaminmodule`. Der Java-Client
bestätigt POST für Begin/Create. Ein Testtool könnte diesen Kamera-Wizard-
Pfad ohne PolyScope-Programm bedienen. Barcodetyp und gültige Moduldaten sind
aus dem Client/Schema passend zu wählen, nicht willkürlich mit Beispielwerten.

**Noch ungeklärt ist der gültige native Bildexport nach dieser HD-Aufnahme.**
`/lastCapture.jpg` ist laut gesicherter API imOperationMode registriert, im
Barcodezustand nicht. Eine direkte Reihenfolge`beginbarcode → create → process
→ lastCapture.jpg` darf daher nicht als funktionierende Anleitung ausgegeben
werden. Notwendigen Zustands-/Puffererhalt bzw. nativen Bildzugriff zuerst
nachweisen. Anfrageparameter allein ersetzen keine vollständigen Moduldaten.

Geplanter Toolablauf: Kamera-Einstellungen/Modus sichern, temporärenHD-Modulpfad
konfigurieren, verifizierte Aufnahme auslösen, Bildbytes nativ herunterladen
und Pixelmaße prüfen, in`finally` Zustand/Fokus/Belichtung/LED wiederherstellen.
Es ist weiterhin keine geprüfte5MP-Aufnahmesequenz vorhanden. Auf diese
Erklärungsfrage keine neuen Kameraoperationen ausgeführt; parallel aktive
Hardware-Hand-Auge-Arbeit bleibt unberührt.

Weiterer statischer Befund auf die Frage nach dem nächsten Schritt: im alten
Archiv ruft`processRejectModuleRestRequest` ModuleManager::clear und leaveState
auf. Normal::clearModules verwirft Module/Modellsätze/Kalibrierungen. In diesen
untersuchten Funktionen keine explizite HD-Bildpufferlöschung erkannt. Der
Kandidat ist daher`Barcode-HD-Aufnahme → rejectmodule → Normal →
beginoperationmode → lastCapture.jpg`, **ohne zusätzliche VGA-captureimage-
Anforderung zwischen HD-Aufnahme und Export**. Zustandswechsel wählen auch
AcquisitionStrategies und können Kameraeinstellungen ändern; allein dieser
statische Befund beweist daher keinen erhaltenen gültigen HD-Puffer.

Nächster praktische Nachweis: ein einzelner exklusiver Kameraversuch mit
gesicherten Einstellungen, Statusprüfung je Schritt, verifizierter HD-Aufnahme,
JPEG-Decodierung/Pixeldimensionen und Wiederherstellung in`finally`, auch nach
automatischer Diensterholung. Ein größerer angeforderter Displaywert ist kein
Erfolgsnachweis. Parallel aktive`hardware-handeye-first-view`-Arbeit muss für
diesen kurzen Kamerazustandswechsel frei sein. Kein solcher Versuch in der
vorliegenden statischen Analyse ausgeführt und kein fertiger HD-Client behauptet.

## Nachweise

`$UWA_WS/setup/logs/wrist-ucc4-2026-11-10/`: Archivkopie, Manifest, verschachtelte
JARs, Bytecode-/Symbol-/Disassembly-Auszüge und`report.json`. Auswertung mit
Python-ZIP,`javap`,`nm -D -C`,`objdump`; keine enthaltenen Binaries ausgeführt.
Herstellerartefakte nicht einchecken. Diese eigene Befundbeschreibung gehört
ins Repository; keine neuen Laufzeit-/Hardwaretests behauptet.
