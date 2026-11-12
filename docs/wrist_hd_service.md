# HD-Bilddienst und Hardwarekalibrierung

Stand2026-11-12,ROS2Lyrical. Echte Drei-Bilder-Probe auf **right_front** bestanden.
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

Im Workspace-Terminal:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
# Einmal pro SSH-Sitzung; SSH selbst fragt interaktiv nach Authentifizierung:
ros2 run uwa_cell_control wrist_hd_service --arm right_front --connect
# Danach eigener Prozess, Domain66. Start löst noch keine Aufnahme aus:
ros2 run uwa_cell_control wrist_hd_service --arm right_front
```

Kein Kennwort als Argument,Umgebungsvariable,ROS-Parameter oder Datei übergeben.
Verwendet wird ein privater SSH-ControlMaster-Socket unter
`/tmp/uwa-wrist-hd-<uid>/`,1h ControlPersist bei Inaktivität. Key-/SSH-Agent-
Authentifizierung ist ebenfalls möglich. `--connect` benötigt ein Terminal.
Neue Hostschlüssel werden vom normalen SSH-Client beim initialen Connect
angenommen, spätere Änderungen abgewiesen. Bei abgelaufener SSH-Sitzung erneut
`--connect` ausführen. Socket/known_hosts sind nur für den lokalen Nutzer lesbar.

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
verwendet die IP aus dem zentralen Inventar. Andere Arms können ausgewählt
werden, sind über diesen Dienst aber noch nicht real getestet.

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
