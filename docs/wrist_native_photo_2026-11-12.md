# Natives5MP-Foto der vorderen rechten Wrist-Kamera

Geprüft2026-11-12,Australia/Perth. Ziel `right_front=192.168.8.103`.

## Ergebnis

**Ein echtes natives JPEG mit2592×1944Pixeln wurde vom Controller heruntergeladen
und mit OpenCV decodiert:**5038848Pixel,332800Bytes,SHA256
`51e8224a37e89cf6d0ca60a6281c143a3e9040117689ca49848253d6361c3b2a`.
Keine Hochskalierung und kein Barcode-/SaveImage-/FTP-Programm verwendet.
Übertragung mit SCP über den ausdrücklich vom Nutzer bereitgestellten SSH-Zugang.
Zugangsdaten wurden nicht in Dateien übernommen; SSH-Sitzung anschließend beendet.

Datei im Workspace:
`setup/calibration/wrist_hd/right_front_20261112/controller-artifacts/native-2592x1944.jpg`.
Das Direktbild hat einen sichtbaren Grünstich. Die native Pixelzahl ist bewiesen,
aber Farbwiedergabe/Weißabgleich dieses direkten Aufnahmewegs sind noch nicht
qualifiziert. Das Foto wurde weder farbkorrigiert noch geometrisch verändert.
Bestehende Intrinsicsprofile für640×480 gelten nicht automatisch für diesen Modus.

## Tatsächliche Hardware-/Softwarebefunde

- HTTPhello: UCC4.1.0.164735,FirmwareCQ0-1.4.0,uniqueCamId01D10E1900090912.
- Reguläre HTTP-Vorschau weiterhin640×480. Vollständige Einstellungen und
  Vorher-JPEG vor Änderungen gesichert.
- SSH zunächstPort22 Connection refused; nach Aktivierung am Pendant Anmeldung
  erfolgreich. Python2.7.9 undGCC auf dem Controller, keine v4l2-ctl-/ffmpeg-
  Tools vorhanden. Keine Pakete installiert und keine dauerhaften
  Kamera-/URCap-Konfigurationsdateien geändert.
- Direkt aus `/dev/video0`: uvcvideo,MJPEG640×480,1280×960 und2592×1944;
  letzter Modus meldet15fps als angebotenes Intervall. Das beweist keine
  gemessene dauerhafte5MP-Bildrate. `/dev/video1` ist ein Metadatenknoten.
- Die tatsächlich verwendete `videoconfig.rcf` des installierten Servers nennt
  Video640×480 undStill2592×1944. Es blieb bei dieser Originaldatei.

## Aufnahme und Wiederherstellung

Ein selbst kompiliertes kleines V4L2-C-Werkzeug lief temporär unter `/tmp/`.
Es handelt2592×1944/MJPEG aus, richtet MMAP-Puffer ein, verwirft die ersten
Dreibilder und speichert das vierte JPEG direkt aus dem Treiberpuffer. Es gibt
Buffer/Stream wieder frei und stellt den vorgefundenen640×480-Modus samt
Bildintervall zurück. Ein außerhalb des Capture-Prozesses vorbereiteter
Wiederherstellungs-Watchdog sichert den Kameradienst zusätzlich ab.

Nur der exakt identifizierte Robotiq-**Vision-Dienst** wurde über seinen
bestehenden runit-Supervisor (`sv down/up`) kurz gestoppt/gestartet. Keine
Roboterprogramme, UR-Control-/ROS-Treiber, Controller oder Simulationen gestoppt.

Erster Versuch: `S_FMT: Device or resource busy`,kein Bild. Der Dienstmanager
hatte den Stopp quittiert, das Kameragerät war aber noch nicht frei. Zweiter
Versuch: beschränktes Wiederholen ausschließlich dieses EBUSY-Falls, Erfolg
beim zweiten Öffnungsversuch. Log:

```text
NEGOTIATED width=2592 height=1944 sizeimage=10077696
FRAME 0 bytes=277504 sequence=1
FRAME 1 bytes=291840 sequence=2
FRAME 2 bytes=325632 sequence=3
FRAME 3 bytes=332800 sequence=4
RESTORED_FORMAT 640x480
```

Die ursprüngliche automatische Wiederherstellung fragte zu früh nach HTTPhello
schon beim Serverstart Settings an; dabei Verbindungs-/Initialisierungsfehler.
Die Kamera wurde anschließend gezielt vom PC im bestätigten **Normal**-Zustand
wiederhergestellt. Rohberichte mit diesen Fehlern bleiben unverändert erhalten;
**der abschließende Nachweis ist `final-restoration.json`**,nicht das frühe
`controller-artifacts/transaction-report.json`.

Aktuelle Firmware gibt beim Setzen vonAuto-LED0 teilweise Fehler15
`Unable to set CameraSettings` zurück, obwohl der Wert angewandt wird. Daher
nicht allein den Setterstatus als Wiederherstellungsnachweis verwenden:
abschließend **sämtliche** gesicherten Einstellungsfelder forceRefresh gelesen
und mitOriginal verglichen,keine Abweichungen. Dazu Fokus435Manual,
Belichtung60000µsManual,Gain16,lightingMode0/lightingValue0. Normale Vorschau
wieder640×480,regulärer Supervisor undVisionserver aktiv. Erscheinungsbild/
Weißabgleich können trotz gleicher zurückgelesener Werte nach Streamwechsel
abweichen; Grünstich bleibt offene Qualitätsfrage.

## Nachweise und Wiederverwendung

Unter `setup/calibration/wrist_hd/right_front_20261112/`:

- `native-photo-validation.json`: tatsächliche decodierte Pixelmaße/SHA256.
- `original-settings.json`, `final-restoration.json`, `restored-preview.jpg`.
- `controller-artifacts/capture.log`, nativeJPEG und unveränderte Rohberichte.
- `v4l2_probe.c`, `capture_v4l2.c`: lesende Modusabfrage/native Aufnahme.
- Temporäre Python-Transaktionsskripte dokumentieren den Versuch einschließlich
  frühem Wiederherstellungsfehler. Sie sind **kein fertiges allgemeines Tool**.

Für eine spätere Integration zuerst ein robustes Wiederherstellungswerkzeug
mit Warten auf tatsächliches Normal, begrenztem Gerätefreigabe-Retry und
Settings-Rückleseprüfung erstellen. Runit-Verzeichnis-/Bundle-IDs aus diesem
Versuch nicht auf andere URs oder nach einem Update kopieren. Identifikation
jeweils aus tatsächlich laufendem Kamera-Prozess und dessen Supervisor ableiten.
Keine Betriebsunterbrechung dieses Wegs während einer anderen Kameraaufnahme.

Der HTTP-Modulversuch vom2026-11-10 bleibt ein separater erfolgloser Versuch;
[damaliger Bericht](wrist_hd_probe_2026-11-10.md). Ein notwendiger Zusammenhang
„erst4.1 ermöglicht5MP“ ist nicht bewiesen: dieses Mal wurden zusätzlich
legitimer SSH-Zugang und ein anderer Aufnahmeweg verwendet.
