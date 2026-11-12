# Hinten links: native HD-Intrinsics, 12.11.2026

**Abgeschlossen: 41/41 Aufnahmen, Intrinsics bestanden.** Eigene native HD-K/D
waren bisher nicht vorhanden; die älteren VGA640×480-/Hand-Auge-Ergebnisse
bleiben unverändert. Sitzung:
`setup/calibration/hardware_handeye/left_rear_hd_20261112/`.

## Aufnahme und Freigabe

Kamera `06561F1400090106`, UCC3.44.0.149696 am UR192.168.8.169,
native2592×1944, Fokus406 manuell, Belichtung33333/Gain16 manuell.
Festes linkes40mm-A3-Board, MarkerIDs0–16. Keine skalierten VGA-K/D,
keine Parameter anderer Kameras und keine Simulationsoptik als Fitvorgabe.

Erstaufnahme im überwachten Stillstand bestanden. Weitere40Ansichten mit
vorher festgelegten Rollen: insgesamt33Fit/8unabhängige Prüfung. 20–24Ecken
pro Bild, keine laufende Aufnahme ausgeschlossen. NativeSensorreadbacks und
vollständiger Originalkonfigurations-Restore für alle41 bestätigt. Alle123
Burst-JPEGs gegen die gespeicherten Original-SHA geprüft,41 unterschiedliche
Messbilder. Die sichtbare wechselnde Grünfärbung betrifft die Farbwiedergabe;
es wurde keine nachträgliche Farbkorrektur an Messbildern vorgenommen.

Vorne links endete am12.11. um18:24:46AWST mit41Bildern und inaktivem Regler.
Die LR-Vorschau aufDomain73 zeigte zunächst dessen prognostizierte Endpose;
Forecast ausdrücklich nicht ausführbar. Nutzerfreigabe:
**„Vorschau passt, Fahrbereich und Kabel frei – nach vorne links starten“**.
Anschließend alle realen Armstellungen gelesen, dieselben40Ziele/Reihenfolge/
Rollen vollständig neu geprüft. Neuer Batch `reviewed_after_left_front/`,
Fingerprint `d0cb381a24345ef6327bb260417a8941d143893c3040e41c69dee06a154630ee`,
Freigabe mit SHA gebunden.535,57s reine Bewegung,5418 Modellprüfpunkte,
Gelenkfenster±45°, native Grenzen unverändert. Diagonalausnahme ausschließlich
left_rear↔right_front gemäß bestehender Nutzerregel. Vorne links und hinten
rechts während der Reihe stationär überwacht, keine anderen Arme kommandiert.

## Ergebnis und empfohlene Version

**Empfohlen: `result_v2/`**, Brown5 mit k3=0 fixiert. Dieselben33Fitbilder und
8Prüfbilder, keine Punkte entfernt und keine Qualitätsgrenzen gelockert.

| Größe | Empfohlen v2 | Unveränderter erster Fit v1 |
|---|---:|---:|
| Fit-RMS |0,3036px|0,2995px|
| Median der Prüf-RMS |0,3177px|0,3167px|
| Größter Prüf-RMS |0,3925px|0,4441px|
| Fokus / Auflösung |406 /2592×1944|406 /2592×1944|

Empfohlene K-Werte in Pixeln: fx2625,2353; fy2608,7368;
cx1369,2135; cy1018,3033. Brown-Koeffizienten k1,k2,p1,p2,k3:
`[0.11855075, -0.41444239, -0.00054493, 0.00605939, 0]`.
Formale relative fokale Fitunsicherheit0,230%/0,189%, maximale Board-
Neigungsdiversität49,67°. Alle unveränderten automatischen Fehler-/Plausibilitäts-
und Beobachtbarkeitsgrenzen bestanden.

Der erste unbeschränkte Fit bestand ebenfalls die Reprojektionsprüfung,
sein freier hoher Term k3 führte jedoch außerhalb der beobachteten Punkte zu
nicht monotoner radialer Extrapolation (minimale radiale Ableitung−1,554 über
dem nominellen Sensorbereich). Deshalb gezielt k3=0 fixiert und neu aus den
Trainingsbildern geschätzt. Die Wahl begründet sich durch diese physikalische
Modellprüfung; Prüfpunkte bleiben vom K/D-Fit ausgeschlossen. Das reduzierte
Modell hat dort positive radiale Ableitung (Minimum0,778) und auf einem101×101-
Gitter positive Vorwärts-Jacobi-Determinante (Minimum0,737). Der ursprüngliche
PASS-Fit und seine Flags wurden nicht überschrieben.

Die Ecken reichen ungefähr von[494;494] bis[2217;1614]px; ihre gemeinsame
konvexe Hülle umfasst32,1% der Bildfläche. Positive Modellableitung ist keine
Messvalidierung der äußersten Bildränder. Reprojektionswerte und formale
Unsicherheit sind keine absolute3D-/Hand-Auge-/Basis-/Tisch-/Weltgenauigkeit.

Dateien relativ zur Sitzung:

- `selected_result.json`: empfohlene Version und SHA-Verweis.
- `result_v2/intrinsics.json`, `camera_info.yaml`: eigenes empfohlenes HD-Profil.
- `result_v2/manifest.json`, `quality_summary.json`, `heldout_contact_sheet.jpg`:
  ursprüngliche Dateihashes, Rollenprüfung, Qualitätswerte und Prüfbilder.
- `result_v1/` / ursprüngliches `intrinsics.json`: unveränderter erster PASS-Fit.
- `intrinsics_fix_k3.json`, `model_extrapolation_diagnostic.json`: Modellauswahl.
- `completion.json`: Controllerstatus, Endfehler und123Original-Burst-SHA.

## Ausführung, Abschluss und technische Nachweise

Reihe18:29:18–18:49:53AWST erfolgreich, inklusive Kameraaufnahmen/Auswertung
etwa20,6Minuten. Letztes Ziel erreicht, maximaler Gelenkfehler0,0000099rad.
Eigener Fahrcontroller danach erfolgreich deaktiviert und über direkte
Controllerliste **inaktiv** bestätigt. Joint-State-Broadcaster bleibt aktiv.
URRUNNING/NORMAL/Remote, ros.urpPLAYING; KameraNormal, Fokus406 manuell,
LED-Wert0. Keine automatische Rückfahrt, kein Safetyreset, keine fremden
Dienste/Treiber gestoppt. Eigene bestätigte Vorschau vorher geschlossen,
Kamera-only-Dienst `uwa-left-rear-wrist-hd.service` bleibt im Leerlauf verfügbar.

Controller zunächst über den Spawner ohne passende Namespace-Zuordnung nicht
initialisierbar; anschließend korrekte Parameter über getrennte SetParameters,
Load/Configure-Dienste gesetzt und nur inaktiv geladen. Erster Startversuch vor
jedem Fahrziel wegen zunächst fehlender frischer RR-Gelenkdaten abgebrochen.
Startphase wartet jetzt begrenzt16s auf gleichzeitig frische Daten; keine alten
Snapshots zusammenführen, alle Laufzeitguards unverändert.13Sequenztests und
9Exporttests bestanden; native C-/Workerressourcen für diese Reihe eingefroren.

Read-only-Endnachweise `final_controllers.log`, `final_native_status.json`;
Runtime und automatische Controller-Deaktivierung unter `preparation/`.
Logs `setup/logs/uwa-left-rear-hd-*`, einschließlich ursprünglicher Fehlversuche.
Offline-Archivtool unterstützt explizites alternatives Fit-Artefakt, prüft
weiterhin PASS, Anzahl, Optikprofil, Originalbilder und feste Prüfrollen.

**Kein neuer Hand-Auge-Fit und keine globale Profilaktivierung.** Für zukünftige
HD-Auswertung ausdrücklich `result_v2` bei406Manual verwenden. Bestehendes
VGA-/Hand-Auge-Profil und vorläufige Welt-/Tischanker bleiben unverändert.
