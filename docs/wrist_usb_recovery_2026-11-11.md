# Robotiq-Kamerastick: Sicherung und Versionsabgleich,2026-11-11

## Auftrag und Befund

Nutzer meldet nach eigenem Kamera-URCap-Update „Vision system down … make sure
the files extracted correctly“ und beauftragt ein vollständiges USB-Backup sowie
die passenden neuen Dateien. Nutzer bestätigt anschließend **URCap4.1.0**.

Identifiziert: Kingston DataTraveler3.0,Seriennummer
`E0D55EA574E5F3A1E91F0FDB`,14,4GiB,ein FAT32-Volume `KINGSTON`,UUID
`289C-1ADC`. Zum Prüfzeitpunkt `/dev/sda`,keine NVMe-Systemplatte.
Vorhandener Ordner `vision_system/version` meldet `UCC-1.11.1.10337` und
`VSL-1.0.23`. Dazu liegen alte Camera-/Gripper-URCaps und ein PolyScope-Update
5.10.1 auf dem Stick. Dessen Vorhandensein beweist keine aktuell installierte
PolyScope-Version.

Das bereitgestellte `~/Downloads/UCC-4.1.0.zip` enthält Camera-URCap
`4.1.0.164735` und `vision_system/version` mit `UCC-4.1.0` / `VSL-2.0.0`.
Die statisch gelesenen Start-/Installationsskripte verlangen passende
VSL-Versionen. Alte USB-Bibliotheken sind daher eine plausible Fehlerursache
nach dem vom Nutzer bestätigten4.1-Update; der Start am Pendant wird nach dem
USB-Dateiaustausch separat geprüft.

## Sicherung / aktueller Arbeitsstand

Ziel: `$UWA_WS/setup/backups/robotiq-usb/20261111-before-ucc-update/`.
Der Stick wurde vor der Rohkopie ausgehängt. `kingston-full-device.img`
enthält15472047104Bytes einschließlich Partitionstabelle und freiem Speicher.
Ein unabhängiger vollständiger Gegenlesevorgang des Originalgeräts bestätigt
denselben SHA256-Wert wie das Image:
`6319d3513efcef0cc76e38bbbcf1827b1e6ac22a26ed3a45f302e0d1583ab746`.
Nachweis: `image.sha256`, `device.sha256`, `backup-verification.json`.
Zusätzlich enthält `files/` alle310 ursprünglichen Dateien (1263252963Bytes),
mit `original-files-manifest.json` als Dateiliste/Größen/SHA256.
Der Stick wurde dafür ausschließlich schreibgeschützt wieder eingehängt.
Die Dateisicherung und das Image sind Rückfallkopien; vor einer späteren
Image-Rückschreibung das Zielgerät erneut per Seriennummer identifizieren.
Nach Bestätigung4.1.0 wurde ausschließlich die Kamera-Komponente ausgetauscht:
`vision_system/` vollständig ersetzt, neue
`Robotiq_Wrist_Camera-4.1.0.164735.urcap` direkt ins Root kopiert und alte
Camera-URCap entfernt. Kein Mischen alter/neuer Bibliotheken, keine Formatierung.
Alle303 Paketdateien gegen SHA256-Manifest geprüft, anschließend Stick
ausgehängt/schreibgeschützt neu eingehängt und erneut alle303 Dateien erfolgreich
geprüft. Keine zusätzlichen alten Dateien im neuen vision_system-Ordner.
Sieben übrige ursprüngliche Dateien, einschließlich Gripper-URCap und altem
PolyScope-Update, unverändert per SHA256 bestätigt. Leere/fremde Ordner erhalten.
Um16:42AWST abschließend erfolgreich ausgehängt; Stick bereit zum Abziehen.
Nachweis `usb-update-report.json`. Kamerastart am UR noch nicht geprüft.
Rohimage und Herstellerdateien liegen außerhalb des Quell-Repositories.

UCC4.1 wurde separat in `staged-UCC-4.1.0/` entpackt:303 Dateien,373018589Bytes.
ZIP-CRC wurde beim Lesen aller Dateien geprüft, SHA256-Manifest erstellt.
Archiv-SHA256:
`dc83962080d1ac2924e9a66529057aff753f0929ee981a97e47d34c01fcbbbaa`.
Die im URCap eingebettete alte SHA1-Tabelle passt teilweise **schon nicht zum
unveränderten ZIP-Inhalt**:29 Treffer,58 fehlende alte Bibliotheksnamen und7
abweichende Qt-Bibliotheken. Sie ist kein geeigneter Vollständigkeitsnachweis
für dieses Paket. Dateien niemals aus verschiedenen Versionen zusammenmischen,
um diese Tabelle zu erfüllen. Kopierprüfung erfolgt gegen das gelieferte ZIP.
Kein Hersteller-Installer oder Binärprogramm wurde am PC ausgeführt.

## Weiter am Pendant

Robotiq verlangt `vision_system/` und die dazugehörige `.urcap` direkt im
USB-Wurzelverzeichnis, nicht unter einem zusätzlichen UCC-Unterordner. Der
Speicherstick und der separate USB-Lizenzdongle müssen beide am Kamera-Hub
verbleiben. Nach dem Dateiaustausch im Kamera-Dashboard den Installationsstatus
prüfen; bei erforderlicher Vision-Server-Neuinstallation die zur installierten
URCap passende Herstellerprozedur verwenden. Eine eventuell geforderte
Kamerafirmware-Aktualisierung ist ein eigener Schritt am Pendant.
Konkrete nächste Bedienung: Stick wieder am Kamera-USB-Hub einstecken, den
separaten Lizenzdongle angeschlossen lassen. Im Pendant
**Installation → URCaps → Camera → Dashboard** den Status prüfen. Falls angeboten
**Install** für den Vision Server verwenden, andernfalls **Start camera**.
Abwarten und anschließend im Camera-Tab das Livebild prüfen. Bei einer
Firmware-Aufforderung den genauen Hinweis prüfen; das4.1-Paket nennt CQ0-1.4.0,
der frühere Rear-Befund CQ0-1.3.5. Das ist keine Messung der aktuellen
Front-Firmware. Bleibt der Fehler, exakten Dashboardtext und PolyScope-Version
notieren; bisher ist nur die korrekte Stickvorbereitung nachgewiesen.

Aktuellen PolyScope-Stand und Paketkompatibilität vor Installation prüfen; kein
PolyScope-Upgrade allein wegen der alten `.urup`-Datei starten.

Herstellerquellen:
- [Robotiq: Connectivity / Vision Server troubleshooting](https://blog.robotiq.com/knowledge/troubleshooting-steps-for-robotiq-wrist-camera-connectivity-issues)
- [Robotiq: Wrist Camera manual2021](https://assets.robotiq.com/website-assets/support_documents/document/Wrist_Camera_Instruction_Manual_PDF_20210615.pdf)

Keine Roboterfahrt, Controller-/ROS-Dienständerung oder SSH-Anmeldung gehört
zu dieser Stick-Vorbereitung. Andere Agenten bearbeiten die Bahnplanung.
