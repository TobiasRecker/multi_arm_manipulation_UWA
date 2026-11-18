# Reale Karton-Kontaktaufnahme18.11.2026

- Status: **aktuelle Pose/Ziele neu berechnet, Fahrvorprüfung vom Schutzdienst abgebrochen; Greifen nicht versucht**. Hauptagent Kartongriff. Nutzer beauftragt Greifversuch und
  fragt ausdrücklich nach mittiger Ausrichtung durch Wristkameras. Bisher nur
  OAK/FK-Bildabgleich; dies offen erklärt. Jetzt zunächst zwei native Wristfotos
  im gehaltenen150mm-Vor-Greifstand, keine Arm-/Fingerbewegung dabei.
- Auftrag: Greifen, zunächstkeinHub/Transport. AbKontakt keineunabhängigen
  Armbewegungen; tragendergekoppelterHardwaremaster bleibtseparat.
- Profil0,1rad/s/0,2rad/s²beibehalten,keineTemposenkung. Greiferbisheroffen
  ACT0/POS3/PRE0, gemeinsameAPIMONITOR ONLY. KeineAktivierungbisher.
- GeplanteSchritte: Wrist-BildprüfungmitpassenderOptik/FK, offeneGreifer
  aktivierenundbestätigen, geometrischgeprüfteAnnäherungbeiderArmevorjeglicher
  Klemmung, Bildcheckpoint, minimaleGreifereinstellungraw0/SPE16beibehalten,
  Kontakt-/Haltbefundeprüfen. KeinautomatischesÖffnen/ZurückfahrenbeimFehler.
- AndereAgentenbetreibenparalleleSimulationskampagne; derenProzesse/CPUprofile/
  Paketeerhalten, keinegemeinsamenSimulationsneustarts.

## Erste Wristprüfung

- Beide native2592×1944-Fotos imgehaltenenStand, FokusRF435/RR388 passendzur
  vorhandenenOptik. UnabhängigeRTDEbeideqd0, GelenkspannenRF0,000174/RR0,000136rad;
  Kamera-DienstrestoresPASS. setup/tasks/carton_grasp_20261118_wrist01/.
- InbeidenBildernkurzeWand sichtbar; vorgesehenerRF-KontaktpunktunterBildrand,
  aktuellerPinchframeebenfallsaußerhalbFOV. Bildmitteistwegen31°Optikschräge
  undKameraoffsetkeinGreifzentrum. OAK-FK-VorpositionistkeineWrist-Zentrierprüfung.
- RFsichtbaresfestesBoard36Markerpunkte/1,799px-PnP, bietetkameralokalenBezug.
  DiagnoseausgelberWandkante: RFextrapolierteKorrektur−34,9mmbei27pxRestfehler
  undZielaußerhalbBild; ausdrücklichNICHTalsFahrkorrekturfreigegeben. RR9,5mm
  groberNormalabstand, ebenfallskeineabschließendeMittigkeitsprüfung.
- GeprüfteRF-Blickposition:80mmTangentversatzam150mm-Hochpunkt, nurunbeladene
  Kamerasicht, keinendgültigerGreifpunkt. Offlinevollmodellgültig,2,27snominal
  beiunverändert0,1rad/s. RealstartvorjedemFahrzielabgewiesen,weilinzwischen
  alle4ProgrammeSTOPPED; AnfangdiesesAuftragswarenalle4PLAYING/NORMAL.
  Armcommands[]/Fingercommands[], ursprünglicheVor-Greifstellungenunverändert.
  NativeStoppursachewirdanhandJournalgeprüft, keineSafetyquittierung/keinblindes
  Play/keinGreifbefehl. inspect_real01/result.json bleibtalsnegativerNachweis.

- Journalzuordnung15:46:25: Controller-/Hardware-RPC-Frische0,27–0,38s löst
  All4nativeSTOPaus; danachWatchdoggelatcht, wiederholteSTOPs. EigeneOpenCV-
  Lastbegrenzungauf2Threads/BLAS/OMP1alsMitigation, CPUursachenurHypothese.
  LängererTrace6sbestätigttatsächlichwiederfrische3Peerströme/alle4stationär/
  keineGuardfaults/alle4Holds. Witnessalleinexplizitzurückgesetzt, Haltungen
  beibehalten; reguläresPlayaller4danachREADY, keineSafetyquittierung.
- ZweiterBlickvorcheckohneArmziel: globaleSoftwarelatcheszurückgesetzt,
  anschließendDriveralignment-SamplelückebeimService-Discovery. Ursache:
  blockierendeswait_for_serviceverarbeiteteArmcallbacks nicht. ApproachClient
  nutztjetztservice_is_ready+eigenesSpinning; Frische-/Lipschitz-/Raumgrenzen
  unverändert,11gezielteTestsPASS. FehlendeFehlerholds nachglobalemResetebenfalls
  korrigiert: nacherfolgreichemResetbeiAbbruchalle4stoppen, auchnochownedleer.
  ExistierendeHoldssofortperSupervisorrückgestellt/bestätigt, keineFahrziele.
- DritterBlicklauf tatsächlichPASS: RF80mmTangentfahrt,2,27snominal0,1rad/s,
  echteHolds/Latches/Guardruhe/unabhängigeRuhefensterbestätigt. Andere3gehalten,
  FingerweiterACT0/offen. NativeNahbildRFausneuerStellungläuft(wrist02).
  UrsprünglichermittigerVorgriffwirdnichtalsaktuellerRF-Stand ausgegeben;
  aktuelletelemetriegebundeneBlickposeistnachfolgenderPlanstart.

- Wrist02nachRF80mm-Blickfahrt: nativeFotoPASS/qd0. GanzeWandmitteschlecht
  sichtbar; gewünschterRim-PunktnachkorrekterKamerageometrieamunterenRand,
  keineFreigabeausExtrapolation. TatsächlicherRandmehrlagigmitZwischenraum,
  dahervereinfachtes2,5mm-SinglewallmodellnichtalsbelegteIstgeometrieausgeben.
- ReineOffline-FrustumplanungliefertneuevollständigeWristansicht: RFaußerhalb
  derkurzenWandbeiObjektx−180mm, y171,16mm, Hochabstand300mm, Greiferum90°
  gedreht(keineGreiforientierung!). GesamterModellrandundGreifpunktsamt±35mm
  NormalvarianteninnerhalbBild, mindestens84,5pxRand. DieseBlickzielestellen
  KEINErealenKlemmstellen dar. VollständigerWeg/FCLnochvorderFahrtprüfen.

## Zwischenzustand / Poseabweichung

- RF-Vollansicht tatsächlich ausgeführt: `carton_grasp_20261118_fullview_real01`,
  27,63s nominal bei unverändert0,1rad/s, Endholds und beide Ruhebelege PASS.
  Native Wrist03 zeigt die ganze kurze Wand mit verstärktem mehrlagigem Rand.
- Zweiter Blick60mm weiter außerhalb: erster Start vor Armziel wegen fehlender
  ROS-Greiferdiscovery abgebrochen. Eigener MONITOR-ONLY-Dienst neu verbunden,
  ohne Aktivierung/Fingerziel. `stereo_real02` tatsächlich PASS,2,35s nominal;
  Wrist04 danach nativ/stationär PASS. RF steht nun außerhalb in um90° gedrehter
  **Inspektionspose**, nicht mehr im ursprünglichen mittigen Vorgriff. RR blieb
  gehalten am alten Vorgriff. Kein Absenken/Greifen/Hub in diesem Auftrag.
- Wrist-Stereopaar geometrisch verworfen: Korrespondenzen passen nicht zur
  gemessenen starren Kamerabewegung. Keine Qualitätsgrenze heruntergesetzt und
  keine Korrektur aus diesem Paar gefahren. Frühere Zuordnung zur physischen
  Kartonbewegung war voreilig und wird zurückgenommen: Nutzer bestätigt danach,
  der Karton blieb zwischen den Wristaufnahmen stehen. Bild-/Kamerabezug bleibt
  als Ursache zu untersuchen, keine Basisneukalibrierung.
- Neue OAK-Texturpose mit gleichem Fokus107/K/D und unverändertem Estimator:
  29Inlier/2,938px, Schätzdifferenz109mm/7,71° gegenüber der ursprünglichen
  Erkennung. Neue Pose und per-Basis-Bindung unter `carton_grasp_20261118_scene02/`;
  reine Beobachtung, keine Manipulationsfreigabe/Absolutgenauigkeitsqualifikation.
  Alte Greifziele und das Stereopaar nicht wiederverwenden. Mittigkeit beider
  Greifer damit weiterhin **nicht verifiziert**, keine Fingeraktion versucht.
- Neuer lesender Endcheck `carton_grasp_20261118_final_hold_check/summary.json`:
  alle4 Ressourcensperren/Softwareholds bestätigt, alle4 stationär, Guard CLEAR/
  keine Faults, Watchdog nicht getrippt. Rechte Finger ACT0/STA0/OBJ0/POS3/PRE0.
  RR-Programm inzwischen STOPPED; Journal16:28 ordnet dies einem bestehenden
  Stillstandswächter zu (ein kurzzeitiger qd-Peak0,003865rad/s beim gehaltenen
  Arm). Keine Safetyquittierung/kein automatisches Play am Ende.
- Abschlussindex `carton_grasp_20261118_current_check/grasp-status.json` nennt
  die tatsächlichen Positionen und offenen Schritte. Vor Fortsetzung Szene
  stationär erfassen, Ziele neu bauen und offenen Einfahrkorridor prüfen. Ab
  Kontakt weiterhin keine unabhängigen Armbewegungen; kein geladener Reset.

## Nutzerkorrektur und aktuelle Neuberechnung

- Nutzer bestätigt: keine Kartonbewegung zwischen Wristaufnahmen; aktuelle Pose
  nochmals berechnen. Schätzdifferenz und physische Bewegung strikt getrennt.
- Neues OAK16:50:12/Fokus107:27Inlier/3,051px, identische unveränderte Kriterien.
  Gegenüber16:40-Schätzung0,506mm/0,438°; interne Wiederholbarkeit, kein Nachweis
  absoluter Greifgenauigkeit. Neue reine Pose/Basisbindung und Bildoverlay in
  `setup/tasks/carton_grasp_20261118_scene03/`. Feste Basisprofile unverändert.
- Wrist05 am unveränderten RF-Stand: native FotoPASS, Gelenkänderungmax0,000088rad,
  1277Homographie-Inlier, mediane Bildverschiebung[0,056;−0,151]px,95%-Quantil
  0,985px. Aktuelle neue OAK-Kontur stimmt visuell wesentlich besser zur kurzen
  Wand; Rand bleibt Modellapproximation, keine automatische Zentrierfreigabe.
  `carton_grasp_20261118_wrist05/check.json` und current-wall-projection.jpg.
- Als nächstes neue hohe Vor-Greifziele mit frischem Iststart offline aufbauen;
  weiterhin keine Finger-/Absenk-/Hubaktion allein aus Textur-PoseVALID.

- Neue beide150mm-Ziele tatsächlich offline berechnet: Start gültig,16gültige
  IK-Kombinationen, GEOMETRIC_PATH_FOUND; serielle vollständige Wiederprüfung
  durch Realrunner ohne --execute PASS. Kommando/Monitor0,1rad/s unverändert,
  nominal RF28,78s/RR4,26s. `recalc_plan01` und `recalc_checked01`.
- Vor Vorbereitung alle4Holds/stationär/GuardCLEAR/Watchdognichtgetrippt frisch
  bestätigt. Bekannt softwaregestopptes RR-ROS-Programm einmal regulär gespielt,
  READY/Reverse bestätigt, keine Safetyquittierung/kein Fahrziel allein dadurch.
- Anschließende tatsächliche Fahrvorprüfung `recalc_real01` vor erstem Ziel und
  vor Reset abgebrochen: RFnative Programm nicht bereit. Journal16:57:12 zeigt
  erneuten bestehenden Frische-Stopp für alle4 wegen Hardware-/Manager-Alter
  0,26–0,32s. Armcommands[]/Fingercommands[], keine neuen Positionen erreicht.
  Keine Grenzlockerung/Temposenkung und keine erneute Play-/Reset-Schleife.
- Aktueller Abschlussindex `carton_grasp_20261118_scene03/result.json` trennt
  abgeschlossene Neuberechnung von nicht ausgeführter Anfahrt/Greifen. RFweiter
  in ursprünglicher Inspektionspose, RRamvorigenVorgriff. Wiederkehrende Frische-
  verletzung vor weiterer Hardwareausführung diagnostizieren; keine belegte
  Kartonbewegung aus Schätzdifferenzen ableiten.
