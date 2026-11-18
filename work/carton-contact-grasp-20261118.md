# Reale Karton-Kontaktaufnahme18.11.2026

- Status: aktiv, Hauptagent Kartongriff. Nutzer beauftragt Greifversuch und
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
