# Wrist-Camera-USB sichern und Update vorbereiten

- Status: **abgeschlossen – Backup und4.1.0-Stick verifiziert; Pendanttest offen**,2026-11-11.
- Nutzer meldet nach selbst ausgeführtem URCap-Update „Vision system down … files extracted correctly“. Robotiq-Stick am PC; vollständiges Image und passende neue Dateien ausdrücklich beauftragt. Nutzer bestätigt installierte Zielversion4.1.0.
- Gerät identifiziert: Kingston DataTraveler3.0, Seriennummer E0D55EA574E5F3A1E91F0FDB,14,4GiB,/dev/sda,Partition KINGSTON/FAT32(UUID289C-1ADC). Systemlaufwerke NVMe bleiben unberührt.
- Erst Stick aushängen, gesamtes Gerät in setup/backups/robotiq-usb/ sichern und per SHA256 unabhängig gegenlesen; erst dann Dateiaustausch. Keine Formatierung geplant.
- Bereiche: dieser Arbeitsstatus, eigene Wiederherstellungsanleitung, gezielte Ergänzungen README/HANDOVER; Rohimage/Herstellerdateien außerhalb Git. Andere Agenten bearbeiten Front-Kalibrierplanung; keine Roboter-/ROS-Dienste ändern, keine Motion/SSH/Installer ausführen.
- Ergebnis Sicherung: vollständiges Image15472047104Bytes und unabhängiger
  Originalgegenlesevorgang identisch(SHA2566319d3513efcef0cc76e38bbbcf1827b1e6ac22a26ed3a45f302e0d1583ab746).
  Zusätzliche Dateikopie310 Dateien/1263252963Bytes samt SHA256-Manifest.
  UCC4.1 ZIP vollständig außerhalb Stick bereitgestellt(303 Dateien), keine
  Herstellerprogramme ausgeführt. Stick bisher ausschließlich gelesen.
- Nächster Schritt: aktuell installierte Kamera-URCap-Version vom Nutzer
  bestätigen lassen; anschließend den passenden vision_system-Ordner vollständig
  ersetzen und neue URCap-Datei direkt ins Root kopieren/gegenlesen.

- Zielversion4.1.0 bestätigt. Nun neues Paket separat kopieren, vollständig gegen Manifest prüfen, alten vision_system-Ordner ersetzen, alte Camera-URCap entfernen. Andere Dateien erhalten. Danach sync/aushängen/schreibgeschützt neu einhängen und alle303 Paketdateien erneut gegenlesen; abschließend aushängen.

- Abschluss16:42AWST: vollständiger Kameraordner durch UCC4.1.0/VSL2.0.0
  ersetzt, neue Camera-URCap4.1.0.164735 im Root, alte Camera-URCap entfernt.
 303 Paketdateien nach Aushängen/RO-Neumount SHA256-identisch, exakt neuer
  vision_system-Dateibaum;7 übrige Originaldateien SHA256-unverändert.
  Stick abschließend erfolgreich ausgehängt. Nachweis usb-update-report.json
  im Backupordner. Kein Roboter-/Firmware-/ROS-Installationsschritt ausgeführt.
- Dokumentation README/HANDOVER/Anleitung aktualisiert. Nächster Bedienerschritt:
  Stick an Kamera-Hub, Dashboard/Install oderStart camera prüfen, Livebild testen.
