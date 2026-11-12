# HD-Bilddienst und Hardwarekalibrierung

Stand2026-11-12,ROS2Lyrical. Echte Drei-Bilder-Proben auf **right_front** und
**left_rear** vollständig bestanden. Rechts hinten nativeBilder erhalten;
UCC1.11.1 mit Autofokus wird wegen nachgewiesener Fokusfenster-Restore-Abweichung
vor weiteren Moduswechseln abgewiesen. [Nachweise beider Rear-Kameras](wrist_hd_other_arms_2026-11-12.md).
Es wird ausschließlich der Kameradienst kurz unterbrochen; keine Roboterbefehle.

## Grünstich und geometrische Kalibrierung

ChArUco verwendet Grauwertkanten. Ein Farbstich allein verhindert daher die
geometrische Kalibrierung nicht. Am echten nativen Foto wurden24 Ecken sowohl
im Farbbild als auch im Graubild mit identischen IDs/Pixelkoordinaten erkannt.
Drei weitere echte HD-Servicebilder lieferten jeweils24 Ecken.

Schärfe, ausreichender Schwarz-Weiß-Kontrast und nicht ausgewaschene Kanten
bleiben erforderlich. Der Dienst speichert Schärfe-/Helligkeits-/Clippingwerte;
Aufnahme und Fit behalten ihre bisherigen Eckenzahl-/Validierungsanforderungen.
Das beweist noch keine neue Intrinsics-/Hand-Auge-Genauigkeit. Farbwiedergabe
ist separat offen. Keine Farbkorrektur oder Skalierung der Messbilder.

## Start und Foto

Seit Nutzerauftrag2026-11-12 ist der schlüsselbasierte Zugriff auf allen vier
UR-Controllern eingerichtet und mit frischen BatchMode-Verbindungen geprüft.
Der Fotodienst verbindet bei Bedarf selbst neu; die frühere stündliche manuelle
Passwortanmeldung ist damit für diesen PC nicht mehr nötig.

- Drei e-Serie-Controller verwenden den dedizierten Ed25519-Kameraschlüssel.
- Links vorne(CB3/OpenSSH6.0) verwendet einen eigenen RSA3072-Schlüssel;
  notwendige alteRSA-Signaturkompatibilität gilt nur für diesen explizit
  provisioniertenHost, nicht allgemein für SSH.
- Private Schlüssel liegen unter `~/.ssh/uwa_wrist_camera_ed25519` bzw.
  `~/.ssh/uwa_wrist_camera_192_168_8_2_rsa`, bekannteHostschlüssel dauerhaft in
  `~/.ssh/uwa_wrist_known_hosts`, jeweils privat und außerhalbGit.
- Auf den URs wurden nur eigenePublicKeys ergänzt, fremdeSchlüssel erhalten.
  Die Einträge sind aufPC192.168.8.209 begrenzt; keineWeiterleitungen/PTY.
  GeänderteHostschlüssel werden weiterhin abgewiesen. KeineKennwörter gespeichert.
- SSH bleibt auf die ausdrücklich beauftragten Kameraoperationen begrenzt;
  Hardware-GUI und Armstart bleiben SSH-frei.

Start ohne Passwortdialog:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control wrist_hd_service --arm right_front
```

Fallback auf einem noch nicht eingerichteten PC: `--connect` stellt wie bisher
interaktiv eine temporäre SSH-Sitzung her. Kein Kennwort als Argument,
Umgebungsvariable, ROS-Parameter oder Datei übergeben. Laufende Multiplex-Sockets
liegen unter `/tmp/uwa-wrist-hd-<uid>/`; Schlüssel und Hostvertrauen sind dauerhaft.

Aufnahme und Status:

```bash
ros2 service call /uwa_hardware/right_front/wrist_camera_hd/capture std_srvs/srv/Trigger '{}'
ros2 service call /uwa_hardware/right_front/wrist_camera_hd/status std_srvs/srv/Trigger '{}'
```

Antwort: success plus JSON mit lokalem Verzeichnis,Original-/Restorewerten,
drei Bilddateien/Prüfsummen,2592×1944-Größe,Qualitätswerten und Zeitgrenzen.
Unter `setup/calibration/wrist_hd/service/right_front/<id>/` liegen drei native
JPEGs,Gerätelog,Rohreport und `validated.json`. Keine Daten überschreiben.
Das letzte Bild wird außerdem auf
`/uwa_hardware/right_front/wrist_camera_hd/image/compressed` veröffentlicht.
Dessen ROS-Zeitstempel ist **Empfangszeit**,kein Belichtungszeitstempel.

Statusabfragen bleiben während der Transaktion erreichbar. Parallele Aufnahmen
werden im ROS-Prozess und zusätzlich auf dem Controller gesperrt. Der Dienst
verwendet die IP aus dem zentralen Inventar. Links hinten ist vollständig getestet. Rechts hinten liefert nativeBilder,
wird im getesteten alten Autofokusmodus wegen fehlgeschlagenem ROI-Restore
konservativ vor weiteren Kameraänderungen abgewiesen.

## Eigene HD-Kalibriersitzung

Das vorhandene Hardwarewerkzeug unterstützt jetzt eine explizite Bildquelle:

```bash
ros2 run uwa_cell_control handeye_hardware capture \
  --arm right_front --camera-source wrist_hd_service \
  --session "$UWA_WS/setup/calibration/hardware_handeye/right_front_hd_NEUE_SITZUNG" \
  --sample-id sample_000 --role fit
```

Erst bei eingerichtetem **festem manuellem Fokus**,korrektem Board und frisch
gemessener stationärer Roboterpose aufnehmen. Der obige Capture-Befehl fährt
nicht. Er prüft Gelenkdaten und nimmt eine reale Messpose auf; während HD wartet
der Client nicht blockierend,sondern verarbeitet fortlaufend Telemetrie und
prüft den Stillstand. Bei Bewegung/Telemetrie-/Guardfehler wird kein Messbild
akzeptiert. Auch nach erkannter Bewegung wartet er auf Abschluss der Kamera-
Wiederherstellung,bevor er den Fehler weitergibt.

Danach mit den bestehenden `plan-series`-/Vorschau-/`run-series`-Schritten eine
**frisch geprüfte und freigegebene** Reihe erstellen. Bildquelle wird aus
`session.json` automatisch übernommen; `run-series` braucht keinen erneuten
HD-Schalter. Freigegebene Wege nicht allein aufgrund dieses Diensttests als
neu ausgeführt/geprüft betrachten. Die Poseplanung darf nominelle bzw. vorhandene
VGA-Intrinsics als Planungshilfe verwenden; das garantiert keine HD-Sichtbarkeit.
Erste echte HD-Aufnahme und weitere Qualitätsprüfungen bleiben entscheidend.

Pro Stellung liefert ein Serviceaufruf drei neue Frames. Gewählt wird zunächst
nach Eckenzahl,dann Schärfe; die komplette native Burst-Evidenz bleibt erhalten.
Fokus-/Bildquellenwechsel und Mischen von HD/VGA in derselben Sitzung werden
abgewiesen. Der Fit prüft zusätzlich unveränderte physische HD-Kamera-ID.
Intrinsics werden vollständig aus den neuen HD-Trainingsbildern geschätzt;
die vorab reservierten Prüfbilder bleiben ausgeschlossen. Alte640×480-K/D
werden nicht in den neuen Fit übernommen. Vorhandene erfolgreiche/abgelehnte
Profile und alte Sitzungen bleiben erhalten; keine automatische Profilaktivierung.

## Was während eines Aufrufs passiert

1. Tatsächlicher Normalzustand und vollständige Settings werden gelesen.
2. Nur der aktuell identifizierte Visionserver/sein eigener runit-Supervisor
   wird verwendet; keine fest codierten Bundle-/PID-Werte und keine Prozesskills
   über Namensmuster. Nicht eindeutig zugeordnete Dienste werden abgewiesen.
3. Temporäres selbst kompiliertes C-Werkzeug handelt2592×1944/MJPEG aus,
   verwirft drei Einlaufbilder und speichert drei weitere Frames. Bei noch
   belegtem Gerät begrenzt warten; sonst Fehler und Wiederherstellung.
4. Stream/Puffer freigeben,VGA-Modus/Bildintervall zurücksetzen,Visiondienst
   wieder starten und auf tatsächliches **Normal** warten.
5. Vollständige Originalsettings zurückschreiben und forceRefresh vergleichen.
   Verzögerte Rückmeldungen begrenzt abwarten. Automatische Fokus-/Belichtungs-
   Ausgabewerte dürfen bei aktivemAutomodus variieren, sämtlicheKonfigurations-
   felder müssen stimmen. Beide manuell gesteuerten Werte bleiben exakt geprüft.
   Nur bei getestetenLegacy-Zweigen1.11.1/3.44.0 LED-Schreibcodierung korrigieren;
   entscheidend bleibt der tatsächlicheReadback.
   Firmware4.1 meldet beim Auto-LED-Setter teilweise Fehler15 trotz angewandtem
   Wert; vollständiger identischer Rücklesevergleich ist entscheidend.
6. Erst nach bestätigtem Restore und nativer JPEG-Dekodierung Erfolg melden.
   Ein unabhängiger Controller-Watchdog versucht Restore bei SSH-/Prozessverlust.
   Erfolgreich lokal gesicherte Requestdaten werden auf dem Controller entfernt.

Die Transaktion ist derzeit absichtlich langsam: real gemessen ca16s für einen
Dreierburst einschließlich Wiederherstellung.40 Stellungen benötigen dadurch
ca11min zusätzliche Aufnahmezeit neben den Bewegungen. Normaler URCap-Livefeed
ist pro Aufnahme kurz unterbrochen. Nicht parallel zu einem anderen Kamera-
Wizard/Bildsammler auf demselben Controller verwenden. Ein Verbindungs-/Restore-
Fehler verwirft die Messung; vor Fortsetzung tatsächlichen Normalzustand prüfen.

## Prüfung

- Reale ROS-/Kalibrieradapterprobe: drei2592×1944-JPEGs,je24 Ecken,16,04s,
 502 Monitorhook-Aufrufe,maximal32,8ms Abstand. Dies ist ein Reaktivitätsnachweis,
  kein realer Bewegungs-/Stopptest. Keine Fahrziele gesendet.
- Gleichzeitige Statusabfrage antwortet CAPTURING,konkurrierende Aufnahme abgewiesen.
  Originalsettings nach Rückkehr vollständig identisch,Normaldienst wieder aktiv.
- Offline-Tests: falsche Pixelgröße,identische Frames,fehlender Restore,
  Restore trotz Aufnahmefehler,Warten aufNormal,LED-Fehler mit gültigem Readback,
  richtiger runit-CWD,fremde Wrapperabweisung,fortgesetztes Warten auf Restore
  nach kurzzeitiger Bewegung,Bildquellen-/Kamerawechsel und bestehende Capture-/
  Fit-/Sequenzregressionen.
- Nachweise `$UWA_WS/setup/logs/uwa-wrist-hd-{tests,build,service}.log`,
  `uwa-wrist-hd-live-adapter.json`,native Datenpfad im Report. Erstes Service-
  Discoveryproblem wurde vor jeder Zustandsänderung erkannt und korrigiert;
  ursprüngliches Fehlerlog bleibt erhalten.

Ausgangspunkt: [einmaliger nativer Foto-Nachweis](wrist_native_photo_2026-11-12.md).

## Abgeschlossener40erFrontlauf2026-11-12

Alle40 nativen2592×1944-Ansichten aufgenommen,32Fit/8vorabPrüfung,20–24Ecken,
40 verschiedene ausgewählte Bilder. Fokus435Manual/60000µs/Gain16 konstant;
jeweils Restore bestätigt. Front konnte nach Nutzerkorrektur unabhängig vom
Diagonalpartner links hinten arbeiten. Dessen Nichterreichbarkeit ist eine
Nutzerangabe; übrige Kollisionsprüfung/native Safety bleiben erhalten.

**Qualität abgelehnt, kein neues Profil aktiv:** Intrinsics-Fit1,1984px bei1px
Grenze. Zusätzliche Offline-Diagnose: Hand-Auge-Prüfung1,9248px, Boardstreuung
1,2669mm/0,5884°. Alle Rohdaten und Diagnoseversion lokal unter
`setup/calibration/hardware_handeye/right_front_hd_20261112/` erhalten.
Kamera am Ende wiederNormal, vollständige Einstellungen identisch bestätigt.
Details: [Front-HD-Bericht](front_hd_calibration_2026-11-12.md).

## Ausdrückliche Übernahme der Front-HD-Kalibrierung

Nach der Fehlererklärung hat der Nutzer dieFront-HD-Daten ausdrücklich
übernommen. Standardprofil ist **hardware_20261112_v2**, Front-K/D und
Hand-Auge bleiben als `operator_accepted_below_threshold` mit `passed:false`
gekennzeichnet. HD-CameraInfo gilt für2592×1944/Fokus435Manual, nicht für
HTTP-VGA oder andere physischeKameras. Bestehende validierteRear-Profile erhalten.
Details: [übernommene Kalibrierungen](applied_calibrations.md).
