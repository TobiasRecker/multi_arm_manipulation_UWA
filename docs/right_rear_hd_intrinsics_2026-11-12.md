# Hinten rechts: native HD-Intrinsics, 12.11.2026

Status: **Messreihe läuft**. Neue eigene Sitzung
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

Logs: `setup/logs/uwa-right-rear-hd-*`; laufende Reihe:
`uwa-right-rear-hd-acquisition-early-action.log`. Rohbilder/Beobachtungen unter
`records/`, vollständige nativeBurst-/Sensor-/Restoreberichte unter
`setup/calibration/wrist_hd/service/right_rear/`. Ergebnis folgt nach Messende.
