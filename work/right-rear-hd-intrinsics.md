# Native HD-Intrinsics hinten rechts aufnehmen

- Status: **in Arbeit**,2026-11-12,Hauptagent.
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
  V4L2-Readbacks anbeidenBurstenden bestätigt. Weitere Tests32PASS.
  VerworfeneVerdeckungsaufnahme archiviert; temporäreUVC-Übergabefehler und
  ungültigeJPEGsbleibendiagnostisch. Kamera-Worker wartetexaktenVision-PID-
  Exit,begrenztS_FMT-Busy/EIO-Recovery,behältVersuchslogs; gültigeJPEGs
  erforderlich. StandaloneRestore teilt dieselbeRemote-Kamerasperre.
- JetztFreigabeumsetzung: nurRRros.urp überMATCHplay starten,dann40Ansichten
  mitnativerSafety/Link/Stationär-/KollisionsprüfungundabschließenderIntrinsics-
  Auswertung. DiagonalerLFistfreigegebenseparat beweglich; übrigeArme überwacht.
- LÄUFT: Execsession1925, Log setup/logs/uwa-right-rear-hd-acquisition-early-action.log.
  sample_001 accepted24Ecken, sample_002 inFahrt. NativeprogrammPLAYING,
  Remote/Linktrue/SafetyNORMAL unabhängigbestätigt; MATCHplay meldetezwar
  fehlendeROSprogram_running-Serviceverifikation, tatsächlicherProgramstart
  warerfolgreich. Nichterneutstarten. ErsterReihenversuch endetevorFahrziel
  wegen spätregistrierterAction; gemeinsamerMATCHClient frühvorMoveItinit
  erstelltundproBatchwiederverwendet, Guards/Controllercleanupbeibehalten.
- RemoteCameraWorker/NativeC nun eingefroren währendReihe. Abschluss:
  nurRR-Bewegungscontrollerdeaktivieren, alleRecords/NativeControls prüfen,
  Intrinsics-onlyFit/Prüfbericht erstellen. BeiAbbruchkeineRückfahrt/keinReset.
