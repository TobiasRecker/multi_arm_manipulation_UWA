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
