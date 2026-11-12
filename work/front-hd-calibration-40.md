# Reale Front-Kalibrierung mit 40 HD-Messstellungen

- Status: **abgeschlossen – 40/40 aufgenommen, Qualitätsprüfung abgelehnt**.
- Stand:2026-11-12,12:37Australia/Perth; Hauptagent Front-HD.
- Nutzerauftrag: volle40erReihe auf right_front mit neuemHD-Dienst; zuletzt
  ausdrücklich unabhängig von left_rear arbeiten. Diagonale Nichterreichbarkeit
  ist Nutzerangabe. Frühere Wartepriorisierung ist damit überholt.
- Umsetzung: neuer gefingerprinteter Hardwarebatch mit genau einem unabhängigen
  Diagonalpartner; nur dessen gegenseitigeKollisions-/Stillstandsabhängigkeit
  entfällt. Eigene-/Tisch-/Werkzeug-/übrigeArmkollisionen undUR-Safety erhalten.
  26gezielteTests/Build positiv. Keinen anderen Arm zumAbschluss gesteuert.
- Durchführung: sample000+39unveränderteZusatzziele; genau32Fit/8vorabPrüfung.
  Batch6c70b73a…, alle40angenommen,20–24Ecken, native2592×1944,konstanteOptik,
  verschiedenePixelhashes,NativeRestorebestätigt. Frontreihe ohneUnterbrechung.
- Regulärer FitExit1: Intrinsics1,1984px>1px. Getrennte Offline-Diagnose ohne
  Ausschlüsse/GT/PrüfbilderimFit: Intrinsics-Prüfung1,0031px;Hand-Auge1,9248px,
  Boardstreuung1,2669mm/0,5884°. KeineGrenzwertegeändert/Profilaktiviert.
- Daten: setup/calibration/hardware_handeye/right_front_hd_20261112/;
  evaluation_v1 enthältsummary,diagnosticIntrinsics/Handeye,verifizierten
  SHA256-Rohdatenmanifest undread-onlycompletion-state.json. Rohdatenignoriert.
- Schlusszustand: RUNNING/NORMAL/PLAYING,0gemeldeteGelenkgeschwindigkeit,
  letzteAufnahmestellung gehalten;skalierterTrajektoriencontrolleraktiv.
  KameraNormal/alleSettingsunverändert. KeineRückfahrt/Quittierung.
- Dokumentation: docs/front_hd_calibration_2026-11-12.md,README,HANDOVER,
  docs/wrist_hd_service.md; dauerhafte diagonaleRegel inAGENTS.md.
- Dienste: nur zuvor fehlendenFront-Dashboardclientwiederverbunden;keinFront-
  Treiberneustart. HD-Dienst/eigenesSTOP-Fenster bleiben vorhanden; keine
  weiterenBewegungengeplant. OffeneQualitätsursache kannofflineuntersuchtwerden.
