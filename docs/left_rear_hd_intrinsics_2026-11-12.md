# Hinten links: native HD-Intrinsics, 12.11.2026

Status: **freigegebene Reihe läuft seit18:29 AWST**.
Bislang existieren bestandene VGA-Intrinsics (640×480/Fokus406) und Hand-Auge;
einzelne native HD-Fotos waren erfolgreich, eigene HD-K/D fehlten jedoch.
Neue getrennte Sitzung:
`setup/calibration/hardware_handeye/left_rear_hd_20261112/`.

## Nachgewiesene Vorbereitung

- Physische Kamera `06561F1400090106`, UCC3.44.0.149696 am UR192.168.8.169.
- Native2592×1944, Fokus406 manuell, Belichtung33333/Gain16 manuell.
  Kein VGA-K/D-Skalieren und keine Parameter anderer Kameras übernehmen.
- `sample_000` im überwachten Stillstand akzeptiert:24 ChArUco-Ecken des
  festen linken40mm-A3-Boards, IDs0–16. Drei unterschiedliche nativeFrames,
  tatsächlicher V4L2-Fokus/Auto-/Belichtungs-/Gain-Readback während beider
  Burstenden und vollständiger Originalkonfigurations-Restore bestätigt.
- Eigener kamera-only Dienst `uwa-left-rear-wrist-hd.service`, ROS-Domain66,
  `/uwa_hardware/left_rear/wrist_camera_hd/capture`. Originale C-/Workerressourcen
  mit SHA unter `preparation/native_resources/` eingefroren, keine parallelen
  Aufnahmebeschleunigungsänderungen während dieser Reihe übernehmen.
- Trajektoriencontroller über getrennte SetParameters/Load/Configure-Dienste
  geladen und ausdrücklich **inaktiv** bestätigt. Zuvor spawner-Aufrufe ohne
  passende Namespace-Parameterzuordnung fehlgeschlagen; Diagnosen erhalten.
  Kein Treiberneustart, kein Bewegungsziel und keine Controlleraktivierung.
- UR bei Vorbereitung RUNNING/NORMAL/Remote, ros.urp geladen, noch STOPPED.
  Programmstart erst nach Ende vorne links und erfolgreichem Live-Wegcheck.

## Gezeigte und freigegebene Reihe

40 weitere Ansichten, zusammen33Fit/8vorabPrüfung. Breite Lage-/Neigungs- und
Abstandsvariation, lokales Gelenkfenster±45° um den gemessenen Start, native
Grenzen unverändert. 535,57s reine Bewegung,5418 Kollisionsprüfpunkte im
Planungsmodell. Keine automatische Rückfahrt. Nur left_rear erhält Ziele.
Die bestehende dokumentierte Diagonalausnahme betrifft ausschließlich
left_rear↔right_front; vorne links bleibt stationär überwacht.

Vorschau `forecast_after_left_front/plan.json`, eigener Dienst
`uwa-left-rear-hd-preview.service` / Domain73. Vorne links ist dort ausdrücklich
mit seiner **vorhergesagten Endpose** dargestellt. Der Forecastbatch trägt
`mode:forecast`, `executable:false` und kann nicht direkt ausgeführt werden.
Er ersetzt keine aktuellen Hindernisstellungen oder Kalibrierung der Montage.

Nutzer bestätigt: **„Vorschau passt, Fahrbereich und Kabel frei – nach vorne
links starten“**, gebunden an Forecastfingerprint/Datei-SHA in
`operator_approval.json`.

Nach allen41 akzeptierten LF-Bildern und dessen inaktivem Bewegungscontroller
liest `preparation/recheck_after_left_front.py` die realen vier Armstellungen.
Nur die unveränderten Ziele/Reihenfolge werden übernommen, alle Verbindungen
erneut kollisionsgeprüft und als `reviewed_after_left_front/` gespeichert.
Das Skript fährt selbst nicht. Geänderte LR-Startstellung oder abweichende
Geometrie sind ein Abbruchgrund; keine ungeprüfte Verbindung ergänzen.

Danach ursprüngliche Freigabe für diese konkrete Reihe umsetzen: ros.urp
über bestehenden MATCH-Pfad starten, External-Control-Link/native Safety prüfen,
`run-series … --intrinsics-only`. Nach Messende nur eigenen Fahrcontroller
deaktivieren, unabhängige Prüfansichten auswerten und Ergebnis archivieren.
Keine automatischen Safetyquittierungen, keine Rückfahrt oder globale
Kalibrierprofilaktivierung. VGA-/HD-/Fokusprofile getrennt erhalten.

Logs: `setup/logs/uwa-left-rear-hd-*`; Steuerparameter und Readinessnachweise
unter `preparation/`. Arbeitsstand `work/left-rear-hd-intrinsics.md`.

## Durchführung

Vorne links endete um18:24:46 mit41/41 Bildern, NORMAL und inaktivem Regler.
Frische Modell-/Wegprüfung bestanden, alle40Ziele und Rollen unverändert.
Ausführbarer Batchfingerprint:
`d0cb381a24345ef6327bb260417a8941d143893c3040e41c69dee06a154630ee`.
Programstart über vorhandenen ROS-Play-Dienst erfolgreich.

Ein initialer Discoveryabbruch endete vor dem ersten Fahrziel. Die Startphase
wartet jetzt höchstens16s auf gleichzeitig frische Gelenkzustände, ohne alte
Snapshots zu vereinigen. 13Sequenztests bestanden, darunter Timeout und
Nichtwiederverwendung inzwischen veralteter Daten. NativesSafety und sämtliche
Laufzeitguards erhalten. Der neue Start erreicht sample_001.

Laufender Exec69707,Runtime/PID/Startzeit unterpreparation/runtime.json.
`preparation/run_approved_series.py` führt nach Ende/Interrupt in finally die
LR-Deaktivierung aus; Ergebnis incontroller_deactivation.log kontrollieren.
Messauswertung folgt nach vollständiger Reihe, noch kein neuer Fit.
