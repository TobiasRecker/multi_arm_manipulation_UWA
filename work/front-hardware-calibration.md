# Front-Kalibrierung mit größerer, räumlich vielfältigerer Reihe

- Status: **60 Bilder nach C153A5 gesichert; Kabel wieder frei, letzte zwei Ziele neu prüfen**,2026-11-11.
- Nutzer bestätigt erneute Kabelspannung an Wrist3 und beseitigt sie. Native
  C153A5/ProtectiveStop, Pending-Action per SIGINT gecancelt/Front inaktiv,
  kein automatischer Reset. Danach Front wieder NORMAL/PLAYING; neue Winkel
  eingelesen.60 Bilder=49 Fit/11 Prüfung (vorherige Zählung12 korrigiert).
  Offline60er-Auswertung: Intrinsics bestanden, Hand-Auge-Rotations-RMS0,670°
  >0,5°, deshalb nicht freigegeben/aktiviert. analysis_60_views/ archiviert.
  Zwei Originalziele060/061 werden aus neuem Stand neu geprüft.
- Ablauf reagiert nun auf natives SafetyMode3 trotz Linktrue mit sofortigem
  Cancel/Deaktivieren;14 Offline-/Parktests gut. Keine neuen manuellen GUI-Gates.
- Nutzer bestätigt unveränderte Kamera/Board. Fünf frische Bilder24 Ecken;
  alter043-Versuch unter rejected/sample_043_attempt_01/ mit SHA256 erhalten.
 043 stationär neu akzeptiert (24 Ecken/3 Payloads/435Manual). Ziele44…61 und
  Rollen unverändert zum freigegebenen Original, neu geprüft und fortgesetzt.
  Resume-Fingerprint b0308b61fc525fe78a451a01f28847106ef9d66ab20c48738fe3b3486a53bda6;
  Log setup/logs/uwa-front-calibration-resume.log. Noch kein Endergebnis.
-43 gültige Bilder bis042 (18…24 Ecken);043 wegen9 Ecken abgelehnt. Dickes Kabel
  diagonal vor Kamera/Board im tatsächlich geprüften Bild. Runner deaktiviert
  Front-Bewegungscontroller, keine Rückfahrt; nativeStatus/Encoder gesichert in
  interrupted_043_state.json. Nutzer um Kabelsicherung gebeten, Kamera-/Board-
  montage und Arme dabei unverändert lassen. Danach fehlgeschlagene Dateien
  archivieren,043 stationär neu aufnehmen und nur bereits freigegebene44…61
  weiterfahren. Keine Gütegrenzen absenken oder alte Bilder überschreiben.
- Erstpose SUCCEEDED/0,0,0000318rad Endfehler,24 Ecken. Autofokustrigger hatte
  HTTP-Reset; danach kein weiterer Trigger. Vorher scharfen Fokus435 manuell
  fixiert,5 Bilder/ForceRefresh stabil435Manual,60000µsManual/Gain16,24 Ecken.
  sample_000 akzeptiert (3 Payloads).61 identische freigegebene Ziele/Rollen
  an aktuelle gemessene Pose gebunden/komplett neu geprüft; Batch-Fingerprint
 840b1bfeb6d794120cef3c81c079f1ea0d7b0b689902b7a96bc9d3427aab82d0.
  Front-Reihe läuft, Log setup/logs/uwa-front-calibration-run.log. Rear geparkt.
- Eigene Domain68-Gesamtvorschau nach erteilter Freigabe geschlossen, um
  unnötige Last während realer Reihe zu entfernen; Hardware-GUI/Treiber erhalten.
- Separates Offline-Modul count_comparison ergänzt (keine laufende Steuerung
  geändert): verschachtelte20/33/50-Fit-Teilmengen mit denselben12 Prüfbildern,
  alle Ergebnisse statt Best-Subset-Auswahl berichten. Zwei Tests zu Holdout,
  Datenimmutabilität und Fehlerberichten bestanden.
- Nutzer bestätigt Gesamtvorschau/Fahrbereich und Start der Erstpose/Reihe nach
  Bild-/Fokusprüfung. operator_approval.json unter reviewed_sequence/ bindet
  Erstpose-Fingerprint und unveränderte Folgeziele/Rollen. Keine neue Freigabe
  für denselben geprüften Weg verlangen; bei Bild-/Link-/Kollisionsfehler stoppen.
- **Rear-Parkfahrt erfolgreich**,17:00Perth: native skalierte JTC SUCCEEDED/0,
  maximaler Endfehler0,0000296rad. Ergebnis unter parking/right_rear_20261111/
  execution_result.json. Front unverändert unkommandiert; erste Front-Bildpose
  wird nun aus aktuellem realem Zustand neu geplant.
- Front-Erstansicht78,903s neu geplant/Check-only erfolgreich, Fingerprint
  ca3bf0fb4831f529b0a1642d9a5718e54d006c9cc4f29163f891e7f0b367cf77.
  Konkrete61 breite Restziele nach Erstansicht erneut gegen ganze Zelle geprüft;
  kombinierte Gesamtvorschau auf Domain68 offen (vorherige Parkvorschau beendet).
  Weitere Bewegungszeit1216,3s, Gesamtversuch ca25–30min. Neue Front-Gesamt-
  freigabe inklusive vorgelagerter Bild-/Fokusprüfung beim Nutzer pending.
  reviewed_sequence/batch.json enthält noch absichtlich geplanten statt
  gemessenen Front-Start; vor Reihe mit denselben geprüften Zielen neu binden.
- Nutzer bestätigt „passt alles“, Kamera nach eigener Aktualisierung hoffentlich
  bereit. Status/Kamera und Starts werden erneut geprüft, dann genau der
  freigegebene57s-Parkweg. Fremde USB-/URCap-Recovery-Dokumentation erhalten.
-16:46Perth: KameraHTTP jetzt gut640×480, vorherige Front-Einstellungen
  gesichert. Front nach Update-Neustart POWER_OFF/Programmunnamed, Linkfalse,
  ROS sechs Nullwerte; Nutzer um Prepare/ros.urp53002 gebeten. Rear-Link gut.
  operator_approval.json für genau denselben Rear-Parkweg gespeichert; keine
  erneute Freigabe für denselben Plan nötig. Noch keine reale Fahrt.
- Nachprüfung16:49Perth: Front weiterhin POWER_OFF/Linkfalse und sechs Nullen,
  auch Ausgabe-only-RTDE bestätigt. URControl-Version am Front jetzt5.26.3.0.
  Nicht als reale Nullstellung behandeln; Nutzer muss Power/Brake/ros.urp
  vorbereiten. Für Rear-Parken genügen bereits verlässliche Front-Gelenkdaten,
  Front-External-Control wird erst für die spätere eigene Fahrt benötigt.
- Nutzer akzeptiert Vorschlag: Rear kollisionsgeprüft parken, Front ungefähr62
  Aufnahmen mit50 Fit/12 vorab reservierten Prüfbildern; kleinere Teilmengen
  gegen dieselben Prüfbilder vergleichen. Rechtes Board bleibt unverändert.
- Zunächst neue aktuelle Zustände/Kamera lesen und konkrete Park-/Aufnahmewege
  prüfen/visualisieren. Keine alten Rear-Fahrfreigaben auf neue Ziele umdeuten.
- Bereiche: Hardware-Aufnahmewerkzeug/Planungsvarianten, Anzahlprüfung des
  Ergebnisprofils, gezielte Tests und Dokumentation; bestehende Diffs erhalten.
- Weiterhin eine reale Armfahrt gleichzeitig, komplette MoveIt-Zelle, native
  UR-Grenzen erhalten. Keine automatischen Power-/Brake-/Play-/Reset-Aktionen.
- Dienste: bestehende rechte Treiber/GUIs erhalten, eigene Vorschau Domain68;
  zunächst keine geplanten Neustarts.
- Rear-Parkplan56,5s/567 Zwischenstände und erneuter Check-only gut. Fingerprint
 49e218e0b86a4910826d23c5d1250a82366e32c5d0ef3892f4dc0944259869f3, Vorschau offen.
  User-Frage zur konkreten neuen Fahrt pending; noch kein Ziel gesendet.
- Front-Dashboard gut, aber HTTP4242 Connection refused und keine anderen
  üblichen HTTP-Kameraports. Nutzer prüft Kamera/Livebild am Pendant.
- Hardwarezählung bis79 neue/80 gesamt erweitert; Simulation30–50 bleibt.
  Neues optionales Wide-Design deckt Bildposition/Distanz/Neigung/Roll ab;
 61 neue+erste Fit-Ansicht ergeben50 Fit/12 Prüfung.18 Tests gut.
- Hypothetische Front-Erstpose nach geparktem Rear und61 breite Folgeziele
  offline gegen ganze Zelle geprüft, keine ausführbare Hardwarefolge:
  right_front_20261111/design_preview/. Reale Kameraprüfung steht aus.
- Zustand/Daten/Nächste Schritte in HANDOVER.md, Bedienung hardware_handeye.md.
