# Hinten rechts: native HD-Intrinsics, 12.11.2026

Status: **41/41 Aufnahmen abgeschlossen, Intrinsics PASS**. Eigene Sitzung
`setup/calibration/hardware_handeye/right_rear_hd_20261112/`.
Keine VGA-K/D auf native HD-Bilder übertragen, keine Hand-Auge-Auswertung
oder Profilaktivierung beauftragt. Das bestehende globale Modell bleibt erhalten.

## Aufnahmeprofil und Freigabe

- Physische Kamera hinten rechts,192.168.8.170, ID01D1111A00090912,
  UCC1.11.1.10337. Native2592×1944-MJPEG-Bursts, drei gültige Original-JPEGs.
- Manueller Fokus388 passt zur bisherigen Drei-Kamera-Aufnahme. Belichtung
  63410/Gain19 manuell wie beim verifizierten Startbild. V4L2-Readbacks während
  erstem/letztem behaltenem Frame müssen Fokus388/Auto0 und die manuellen
  Belichtungs-/Gainwerte bestätigen. Diese Gerätewerte sind kein physisch
  vermessener Brennweitenwert oder synchronisierter Belichtungszeitstempel.
- Festes rechtes A3-Board,7×5Felder40mm,Marker28mm,IDs50–66. Nutzer bestätigt
  unveränderte Befestigung und entfernt das mobile A4-Board aus Sicht/Fahrraum.
- Erste gültige Aufnahme `sample_000`:24Ecken,3unterschiedliche nativeFrames,
  Stillstand aus frischen Gelenkdaten und vollständiger Kamera-Restore geprüft.
- Weitere40Ansichten mit breiter Bild-/Neigungs-/Abstandsvariation. Rollen
  vorab fest: insgesamt33Fit/8Prüfung. HD-FOV nur als nominaler Planungsproxy;
  alteVGA-Intrinsics werden weder skaliert noch dem neuen Fit übergeben.
- Endgültiger Plan `reviewed_series/batch.json`, Fingerprint
  `19d68cdeb45acc0a0f8278c494156bb780da0385309902e8d555f54d7770e651`.
  Reine Bewegung490,25s, lokale Planungsgrenze±45° um jede Startgelenkstellung,
  unveränderte native Gelenklimits. Jede gefahrene Verbindung MoveIt-geprüft.
- Nutzerfreigabe nach eigener RViz-VorschauDomain72: **„Vorschau passt,
  Fahrbereich und Kabel frei – Reihe starten“**, gespeichert in
  `operator_approval.json`. Keine neue Freigabe für unveränderte Wege nötig.
- Nur hinten rechts erhält Ziele. Diagonaler Partner links vorne darf gemäß
  bereits bestätigter physischer Reichweitentrennung separat arbeiten. Nur
  dieses Paar von gegenseitiger Collision-/Stillstandsabhängigkeit ausgenommen;
  Selbst-,Tisch-,Werkzeug-/übrigeArmprüfung und native UR-Sicherheit bleiben.
- Keine automatische Rückfahrt, kein Stop-/Safetyreset. Nach Abschluss bleibt
  der Arm am letzten Ziel; eigener Bewegungscontroller wird deaktiviert.

## Bereits geprüfte technische Punkte

NativeV4L2-Moduswechsel wartet jetzt auf den tatsächlichen Visionserver-Exit.
Begrenzt wiederholbare S_FMT-Busy/EIO-Übergabefehler bleiben protokolliert;
fehlerhafte MJPEG-Frames werden nur innerhalb einer begrenzten Warmup-Schleife
verworfen, drei decodierbare native Bilder und veränderte Pixel-Hashes bleiben
zwingend. Originalversuche und Restoreberichte erhalten. Standalone-Fokusrestore
teilt die Remote-Kamerasperre, um keine andere native Aufnahme zu unterbrechen.

Eine verdeckte Aufnahme vor dem Freiräumen wurde ausdrücklich abgelehnt und
unter `preparation/rejected_occluded_sample_000/` mit Hashes archiviert.
NativeFehlversuche/IO-/JPEG-Diagnosen bleiben in den HD-Dienstordnern erhalten.

Der erste Reihenstart endete vor jedem Fahrziel wegen spät registrierter Action.
Der MATCH-Trajektorienhelfer unterstützt nun einen vom Aufrufer gehaltenen Client.
Die Reihenaufnahme registriert ihn vor MoveIt-Initialisierung/erstem Spin und
prüft die Verfügbarkeit vor Controlleraktivierung; danach Wiederverwendung für
alle Ziele. Fehler-Cancel und Deaktivierung bleiben erhalten, andere Arme werden
nicht angesteuert. Native Programmverbindung/Safety wurden unabhängig bestätigt;
die MATCH-Play-Verifikation meldete eine nicht verfügbare ROS-Abfrageschnittstelle,
obwohl DashboardPLAYING und echter External-Control-Link bereits vorlagen.

Reiseverkürzung darf keinen kollidierenden neuen Abschnitt einführen: nächster
erreichbarer Kandidat und vollständig geprüfte Reihenfolge; andernfalls erneut
geprüfte ursprüngliche Reihenfolge. Kein hypothetischer direkter Rückweg wird
für diesen ausdrücklich rückfahrtfreien Hardwarebatch vorausgesetzt.

## Auswertung und Nachweise

Die Reihenaufnahme verwendet `run-series … --intrinsics-only`. Nur die vorab
markierten Fitbilder bestimmen K/D; Prüfbilder bleiben ausgeschlossen. Native
Pixel-RMS und geometrische Beobachtbarkeit werden getrennt berichtet. Die bisher
absolute1px-Grenze ist beiHD strenger als beiVGA; ein eventueller Abbruch darf
nicht ohne auflösungsbewusste Diagnose als schlechtere Optik interpretiert werden.
Alte Qualitätsflags/Ergebnisse bleiben erhalten, keine Grenzwerte still ändern.

Logs: `setup/logs/uwa-right-rear-hd-*`; abgeschlossene Reihe:
`uwa-right-rear-hd-acquisition-early-action.log`. Rohbilder/Beobachtungen unter
`records/`, vollständige nativeBurst-/Sensor-/Restoreberichte unter
`setup/calibration/wrist_hd/service/right_rear/`.

## Abgeschlossenes Ergebnis

Alle 41 Bilder akzeptiert, 33 Fit und 8 vorab festgelegte unabhängige Prüfbilder.
18–24 Ecken pro Bild; keine Aufnahme aus der laufenden Reihe ausgeschlossen.
Alle 41 Sensorprüfungen, drei unterschiedlichen nativen Burstbilder und
vollständigen Kamera-Rückstellungen bestätigt. Originale unverändert archiviert.

| Größe | Ergebnis |
|---|---:|
| Native Auflösung / manueller Fokus | 2592×1944 / 388 |
| Fit-RMS | 0,7605 px |
| Median der Prüf-RMS | 0,6742 px |
| Größter Prüf-RMS | 0,9219 px |
| Relative geschätzte Unsicherheit fx / fy | 0,496 % / 0,396 % |
| fx / fy | 2620,1125 / 2652,4330 px |
| cx / cy | 1281,1096 / 682,7713 px |

Brown5-Koeffizienten in OpenCV-Reihenfolge k1,k2,p1,p2,k3:
`[0.04160375, 0.20683262, -0.03320096, 0.00286006, -0.98821155]`.
Keine VGA-Matrix oder nominelle Optik in den Fit übernommen.
Die unveränderten absoluten Qualitätsgrenzen wurden bestanden.

Die gemessenen Ecken reichen ungefähr von [263;216] bis [2066;1365]px;
ihre gemeinsame konvexe Hülle umfasst rund 34,9 % der Bildfläche.
Die äußersten Bildränder sind dadurch nicht gleichermaßen validiert.
Reprojektionsfehler und formale Fitunsicherheit sind keine absolute
3D-/Hand-Auge-/Tisch-/Weltgenauigkeit. Reflexionen verdecken in den letzten
vier Ansichten einzelne Ecken; die übrigen 18–22 Ecken bleiben nutzbar.

Versionierte lokale Ergebnisse unter `result_v1/`:

- `intrinsics.json`: unveränderte bestandene K/D und Prüffehler.
- `camera_info.yaml`: ROS-Export, native Auflösung, plumb_bob.
- `manifest.json`: Originaldatei-/Bild-/Burst-/Freigabe-Hashes und Rollenprüfung.
- `quality_summary.json` und `contact_sheet.jpg`: Kontrollwerte und Bildübersicht.

Offline-Archivprüfung und Export: `python3 -m uwa_cell_control.intrinsics_report`
nach Laden der Zell-Control-Umgebung; 7 gezielte Tests bestanden. Zusätzlich
34 Vorbereitungs-/Adaptertests und native C-Kompilierung bestanden.

Abschluss 18:01 AWST: letzte Pose erreicht, maximaler Gelenkfehler
0,000044rad. MATCH-Deaktivierung erfolgreich; direkter ListControllers-Nachweis
bestätigt Admittanz- und beide Trajektoriencontroller inaktiv, Joint-State-
Broadcaster aktiv. Dashboard RUNNING / NORMAL / Remote, ros.urp bleibt PLAYING.
Keine Rückfahrt, kein Safetyreset, keine fremden Arme oder Dienste gestoppt.
Der schnelle Statushelfer meldete wegen kurzzeitiger Service-Discovery
`driver_available:false`; die anschließende direkte Liste bestätigt den Treiber.
Nachweise `final_controllers.log`, `final_status.log`,
`setup/logs/uwa-right-rear-hd-final-inactive-network.log`.

Kein neues Hand-Auge-Ergebnis berechnet und kein globales Profil geändert.
Das aktive Rear-VGA404-/Hand-Auge-Profil bleibt erhalten; diese HD388-K/D
stehen für spätere native Aufnahmen und deren separate Auswertung bereit.
