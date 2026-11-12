# Native HD-Intrinsics hinten rechts aufnehmen

- Status: **abgeschlossen**,2026-11-12,Hauptagent.
- Nutzer beauftragt als nächsten Schritt neue Intrinsics für right_rear im
  nativen2592×1944-Modus; eigenes Profil Fokus388 passend zu bisherigen
  Drei-Kamera-Fotos, keine VGA-K/D übertragen oder alte Fits überschreiben.
- Zunächst lesende Zustands-/Kameraprüfung und bestehende HD-Routine prüfen;
  erste Aufnahme in aktueller Stellung falls Board sichtbar. Neue Fahrwege
  vollständig planen/visualisieren und vor erster Ausführung konkret freigeben.
- Andere Aufgaben: LinksFront-Kalibrierung läuft, OAK-CAD/Stativintegration
  verändert parallel Modelle. Keine fremden Dienste stoppen oder fremde Arme
  kommandieren. Bei paralleler LF-Bewegung nur dokumentierte diagonale Ausnahme
  right_rear↔left_front, übrige Checks unverändert.
- Eigene Sitzung setup/calibration/hardware_handeye/right_rear_hd_20261112/,
  native Originale/Settings/Fokus, feste Fit-/Prüfrollen. Kein automatisches
  Übernehmen eines neuen Fits vor Ergebnisprüfung/Nutzerauftrag.
- Nutzer bestätigt rechtesA3unverändert/mobilesBoardweg und gibt konkrete
  Domain72-Vorschau frei: "Vorschau passt, Fahrbereich und Kabel frei – Reihe starten".
  Freigabe mitFingerprint in operator_approval.json; maßgeblich reviewed_series/
  batch.json,19d68cdeb45acc0a0f8278c494156bb780da0385309902e8d555f54d7770e651.
- 41geplanteAufnahmen (33Fit/8Prüfung),490,25sreineFahrt,45Grad lokales
  Gelenkfenster,keineRückfahrt. Erster Entwurf mitgroßenWicklungen verworfen;
  neueVerbindungen immerMoveIt-geprüft,kollidierendeReiseverkürzungverworfen.
- sample_000 accepted:24Ecken/2592×1944,388Manual,63410/19manuell; native
  V4L2-Readbacks anbeidenBurstenden bestätigt. Vorbereitung34TestsPASS; zusätzlicherOffline-Archivexport7TestsPASS.
  VerworfeneVerdeckungsaufnahme archiviert; temporäreUVC-Übergabefehler und
  ungültigeJPEGsbleibendiagnostisch. Kamera-Worker wartetexaktenVision-PID-
  Exit,begrenztS_FMT-Busy/EIO-Recovery,behältVersuchslogs; gültigeJPEGs
  erforderlich. StandaloneRestore teilt dieselbeRemote-Kamerasperre.
- JetztFreigabeumsetzung: nurRRros.urp überMATCHplay starten,dann40Ansichten
  mitnativerSafety/Link/Stationär-/KollisionsprüfungundabschließenderIntrinsics-
  Auswertung. DiagonalerLFistfreigegebenseparat beweglich; übrigeArme überwacht.
- Abgeschlossen18:01AWST:41/41 Bilder,33Fit/8Prüfung. IntrinsicsPASS,
  RMS0,7605px/Prüfmedian0,6742px/max0,9219px. AlleNativeControls/Restorechecks
  bestanden; Originalhashaudit+CameraInfo in result_v1/. KeineHand-Auge- oder
  globaleProfilaktivierung; VGA404 unverändert. 7Offline-ExporttestsPASS.
- Exec1925 beendet. RR-Fahrcontroller durchMATCHdeaktiviert, direkte
  ListControllers bestätigt alle3Motioncontrollerinaktiv/JSBaktiv. NativeUR
  RUNNING/NORMAL/Remote,ros.urpPLAYING. LetzterGelenkfehler0,000044rad.
  KeineRückfahrt/keinReset/fremderDienststopp. RR-Reihe nutztKamera nichtmehr;
  LF-Restprüfung kann echteRR-Endpose lesen. EigenerHD-Kameradienst bleibtidle.
- Ergebnisbericht docs/right_rear_hd_intrinsics_2026-11-12.md und HANDOVER
  aktualisiert. RuntimeKamerahelfer nachMessende nichtweitergeändert.
