# Langsamer Kartongriff in der echten Zelle

- Aktualisierung17.11.ausseparatemunbeladenemVierarmtest: alle4Greiferreal
  aktiviert/vollgeöffnet; SPE16/FOR0zurückgelesen. TransportjetztParameter
  einzelnvorPositionsänderungbestätigen. Alter16.11.-Readiness-Codehashdes
  Greifertransportsüberholt; keinbeladenerGriff/keineN-Kalibrierungqualifiziert.
  Bericht docs/hardware_commissioning_2026-11-17.md. VierArmeabschließend
  verriegelt/stationär, kein automatischerKartonhub ausdiesemNachweis.

- Status18.11.: **beide rechtenURs real in Vor-Greifpose erreicht**, neue
  Kartonerkennung/OAK107/aktuellerFit und festeBasisanbindungen verwendet.
  Kommando0,1rad/sbeibehalten; alle4Armeabschließendgehalten/stationär, Greifer
  weiteroffen/inaktiv. KeinGriff/Hub. AktuellerIndex
  `setup/tasks/carton_pregrasp_20261118_completed/`; Details
  [aktueller Arbeitsstand](carton-pregrasp-20261118.md). Nachfolgende17.11.-Notizen
  sindHistorie, einschließlich damaligemfehlgeschlagenenBildabgleich.

- Nutzerauftrag: bestehenden Zweiarm-Kartonablauf zuerst deutlich langsamer
  real testen. Jetzt alles vorbereiten; Nutzer startet URs erst auf Bereitschaft.
  Bis16.11.ausschließlichlesend; nachÜbergabe17.11.vierexpliziteROS-
  Greiferteilhubziele ausgeführt, sieheunten. KeinePower-/Brake-/Play-, Armfahr-
  oderControllerschaltbefehle.
- RechtsRF192.168.8.103/RR192.168.8.170, Domain66; Mock67, Simulation64.
- Gemessener Anfangsstatus beidePOWER_OFF/NORMAL, ros.urpSTOPPED, vorhandene
  Treiberlauscher, commands[], keine eigenen Treiberstarts. Statusdatei
  setup/logs/carton-hardware-preparation-status-20261116.json.
- Lücken vor Realgriff: Taskbackend bisherSimulation-only; Klemmkraft-/
  Öffnungsabgleich offen, Welt-/Tisch-/Basenextrinsiken vorläufig.
  Reine Timestamp-Gleichheit unabhängiger UR-Trajektorien reicht für tragenden
  starren Verbund nicht; gemeinsames Objektzeitgesetz und Ist-Relativfehler
  einschließlich UR-Speedscaling erforderlich. Kein Simplan direkt ausführen.
- Nutzerfrage zur bisherigen Realgreiferbedienung gestellt; lesbaren Zugang
  zuerst prüfen. Vorbereitung darf keine automatische Aktivierungsfahrt enthalten.
- Bereiche: neue getrennte Hardware-Vorbereitung/Read-only-Prüfwerkzeuge,
  eigenes langsames Profil, Dokumentation und zielgerichtete Tests. Bestehende
  laufende Dreh-/Vierarmarbeiten und Treiber erhalten; keine Dienstneustarts.

## Stand der Vorbereitung

- Nutzer: Greifer bislang nicht benutzt; ROS-Steuerung erkunden. Beide echten
  Robotiq-Server63352 GET-erreichbar, ACT0/STA0/FLT0; keineAktivierung.
- Neues Interfacepaket+ROS-Adapter, MONITOR ONLY alsDefault.23Tests und eigene
  ROS-Mockintegration67PASS; Read-Services beider echtenGreifer66PASS, Nodes
  danachExit0. Nur eigenes neues Interfacepaket gebaut, laufendePakete erhalten.
- Alle4nativeOutputstreams aufgenommen; aktuelle rechteTCPoffsets0.
  FactoryFK inURbase gegenüber nativenTCPs <1µm als interner Konsistenzcheck,
  keinerlei Weltregistrierungs-/externeGenauigkeitsfreigabe.
- Eigene Erststufenparameter0,5mm/s/5mmHub/.005rad/s/.005rad/s² dokumentiert,
  echterGreiferKraft-/Geschwindigkeitsabgleich offen. Profil nicht ausführbar.
- Software/Tests für Live-Vorprüfung fertig. VollständigerRealgriff bleibt
  offen: Greiferleerfahrt/realerGeometrieabgleich/gekoppelterHardwareObjektmaster
  mitgemeinsamerZeitbasis undGruppenstopps. NachNutzerstart zunächst nur frische
  Liveprüfung, kein automatischerHub. docs/carton_hardware_commissioning.md.

- Abschließender Readiness-Index: eigener Vorbereitungspfad/readiness-index.json
  bindet Code-/Profil-/Report-/Testdateien; Livebeobachtung vorbereitet,
  automatic_carton_lift_ready=false. EigeneROS-Testknoten beendet, keine
  Hardware-Aktivierung/-Fahrt; Nutzer kann als nächsten Schritt URs starten,
  danach zunächst frische lesende Prüfung.

## Vorbereitung während fremdem UR-Test,2026-11-17

- Nutzer meldet beideURsbereit, aber andererAgent nutzt Arme. Keine eigenen
  UR-/Greiferabfragen, Nodes, Controllerwechsel oder Schreibbefehle während
  dessen Zugriff; ausschließlich Offline-/eigeneMockarbeit. FremdeQuellen im
  Task-/Motionpaket werden nicht bearbeitet oder neugebaut.
- Karton lautNutzer wiederamPlatz. Nutzer erlaubt jederzeitigeOAK-Szenenprüfung;
  vorhandenenKameradienst/Lease nutzen, laufendenZugriff erhalten. NeuePose
  nach tatsächlicherÜbergabe messen, keinealtenHomeziele übernehmen.
- Arbeit: eigener reiner gemeinsamerObjekt-/Zeitbasiskern und Mockprüfungen,
  konkrete vorbereiteteÜbergabesequenz. VollständigerRealgriff bleibt offen;
  bloße Beendigung eines fremdenProzesses ist keine Bewegungsfreigabe.

## Tatsächliche Übergabe und frische Szene,2026-11-17

- Nutzer bestätigt „Jetzt frei“. Beide rechtenURs RUNNING/NORMAL/Remote,
  ros.urpPLAYING/Reverseverbunden. ViernativeOutputstreamsstationärbeobachtet;
  rechteHoldsaktiv, Bewegungskontrollerinaktiv. KeineeigenenSchreibbefehle.
- Default-FastDDS-Client findet beideManager; erzwungenesUDPv4war inkompatibel
  zumheutigenTreibertransport. KeineTreiberänderung/keinNeustart.
- OAKStandard8K/Fokus116/10:31:25bestätigtKartonamPlatz, Kamerageschlossen.
  OfflinePose69Inlier/2,458px, vorläufigeWeltpose1,43degNeigung. Keinabsoluter
  Genauigkeits-/Greifnachweis. setup/tasks/carton_hardware_preparation_20261117_01/.
- Gemeinsamer transportfreierObjektreferenzkern14TestsPASS, festeOffsets/eine
  Uhr/nativeMinimalskalierung/Quellfrische/Relativfehler/Gruppenverriegelung.
  KeineechteIK-/Kommandotransport-/Stillstandsbestätigungsintegration. Taskpaket
  wegenparallelerSimkampagnenichtneugebaut. SoftwareprüfungkeinRealhub.
- Offline-Anfahrprüfung mitaktuellenFactorykinematiken, vollständigenFingerhüllen,
  aktuellem99,1cmLayout undKamera-Posekandidat: dritterFall findetgeprüften
  RF-dannRR-Weg in80mmVorposition. ZusätzlicheäquivalenteGelenkwindungen nahe
  Iststellung lösenSuchproblem; FK/volleSegmente erneutgeprüft. ZweiSuchfehl-
  versucheerhalten. KeineZeitplanung/Realtrajektorie; Modellnachweisallein.

## Echte ROS-Greiferteilfahrt nach Übergabe,2026-11-17

- GemeinsameROS-API inzwischenalsMonitor verfügbar. EinStartversucheines
  zweitenAdaptersanGeräteLeaseabgewiesen,0Goals. Harnessnutztjetztbestehende
  Read-/Capabilities-/Command-Endpunkte; reineLiveprüfungPASS.
- Nutzerauftrag langsamerRealtest: gemeinsamenDienst mitcapsFOR0/SPE16explizit
  enabled; RFundRRjeweils0→128→0,einzeln. Alle4ActionGoalsPASS, OBJ3/keinKontakt,
  Ziel128ist128undÖffnungsziel0istPOS3bestätigt. KeineAktivierung/Armbewegung.
- DanachDienstzurückMONITOR ONLY/caps0/16, beidenGreiferbleibenoffen.
  Alle4nativenArmstreamserneutstationär/letzteqd0. KeineArmcontrollerverändert.
- Artefakte setup/tasks/carton_gripper_ros_empty_stroke_20261117_01/ und
  carton_hardware_post_gripper_20261117_01/.24Referenz-/PregrasptestsPASS,
  ROS-MockmitseparaterFOR/SPE-BestätigungPASS. KeinN/mm-/Loadedstopnachweis.
- NächstertechnischerSchritt: realengekoppeltenObjekt-Kommandopfad integrieren
  undinMockprüfen, physischeAusrichtungvorKontakt; historisches.005rad/s-
  Profilnichtunteraktuellem.003rad/sWächterausführen. BestehendeGrenzen erhalten,
  KommandoboundmitgemessenenGeschwindigkeitspeaksabgleichen. NochkeinKartonhub.

## Wiederholter Programmstopp bei unveränderten Armen,2026-11-17

- NachTeilfahrt um11:22:42/43beideRechtsprogrammeSTOPPED, safetyNORMAL,
  qweiterhingleich (ca40µradDifferenz), keineeigeneArmfahrt. Nutzerzunächst
  „solltenweiterlaufen“, dannandererAgentvermutlichfertig/„kannstweitermachen“.
- GemeinsamerBringupdanachjeeinreguläresPLAY, beideReverseverbunden; keine
  Power/Brake/Load-/Safety-/Fahraktionen. FrischeBeobachtung11:40erneutrechts
  runtime_state1, links2. NichtdurchweiterePLAY-Schleifeübergehen.
- AktuellerGuard: alteSPEED-LIMIT-LatchesausVierarmtest sowieNativeProgram-
  Interrupted rechts; keinefrischeAbstandsstörung. UrsprünglicherStoppinitiator
  ausbisherigenLogsnochunbekannt, alteNativeACKsbereitsvorhervorhanden.
- ErgänzegezielteDiagnostik inHardwareStopPort/Nodes: Zeit/Ursache/Antwort jeder
  tatsächlichenNativeSTOP-Anforderung, begrenzteHistoryundJournal. Keine
  Frische-/Stopp-/Abstands-/Geschwindigkeitsgrenzengeändert. VorneuemArmtest
  reproduzieren/aufklären. EigeneAnfahrtnochNICHTausgeführt.
- Diagnostikregression53Hardware-/Guard-/Native-Stop-FällePASS;32eigeneObjekt- /
  Pregrasp-/Approach-FällePASS. NeueAnfahrtserweiterung offlinevollmodelliert
  RF/RR-SegmentePASS, kleineresKommando.0015gegenunverändertenMonitor.003.
  Alte80mm-VorpositionnochkeineFahrt; physischerRunnererfordertmindestens150mm.
  Timingaktuellca1961+2830s(80min)füralteModellziele, nichtalsrealeFahrzeitbelegt.
- GeplantnurSchutzdienstneuladen, umPython-Diagnostikaktivzumachen; vorhandene
  HardwareHoldsbleibenbestehen. RegulärerExecStopPoststopptdabeiProgrammesaller4,
  danachProgrammläufeunterHoldsherstellen; keineController-/Fahrziele. Andere
  Treiber/Kamera-/Greiferdienste undSimulationenerhalten, Parameterunverändert.
- **NeuladenNICHTausgeführt:** automatischeFreigabeprüfunglehntsystemctlstop
  ab, weilExecStopPostallevierrealenUR-Programmestoppt undkonkreteFreigabe
  bisheraufrechteURsbezogenwar. KeineUmgehung/keineanderenKills. Nutzerper
  asyncnachgenaudiesemVierprogramm-Stop/Neuladen/Wiederverbindengefragt;
  Antwortstehtaus. AlteSchutzinstanzläuftunverändert. ReinlesenderTraceaktiv
  setup/tasks/carton_interlock_diagnostic_20261117_01/(900sbegrenzt).
- NutzerhatanschließenddenStop/Neuladen/Wiederverbindenfür**allevierURs**
  ausdrücklichfreigegeben. GeordneterDienststoppjetztausgeführt, Neustartmit
  identischerKonfiguration; keinUmgehungswegundkeinegelockertenGrenzen.
- NeuerOfflineSchritt: expliziteGeschwindigkeitsgrenzenjeArm inMotionkern;
  dieselbenWertefürIstgeschwindigkeitundBremsreserve/Signatur. DefaultohneMap
  unverändert. NochkeinehöhereGrenzeinderHardwareaktiviert. Zielnurunbeladene
  Anfahrtbeschleunigen, ruhendeArmenichtmitfiktivhohenGeschwindigkeitenbudgetieren.
  Aktuelle.003-KonfigurationundalleHoldsbleibenzunächstaktiv.
- NacherstemgenehmigtenNeuladenalle4ProgrammeperPLAYwiederverbunden. NeuerTrace
  erfasst12:01:14/monotonic7363.944515LF-nativeSTOP **vomSupervisor**:
  „Blockedarm:measuredstandstillnotconfirmedwithinstoplatency“. Keine
  Abstands-/Speedstörung. AlteStopfristliefseitVerriegelungweiter, trotzvieler
  zwischenzeitlichbestätigterRuhefenster. DadurchreichteinfehlendesRuhefenster
  Minuten späterfürsofortigesNativeSTOP. UrsachefehlendenFensters(noise/coverage/
  echtekleineBewegung)nochgetrenntzumessen; frühererechteStoppsnichtendgültig
  demselbenTriggerzugeschrieben. QuelleTraceundJournal.
- FixinPrüfung: FristproerneuterAbwesenheit**frischer**Stillstandsevidenz;
  AnkeristGuard-Evaluationsstempel, nichtwiederholtePaketrezeption. Alte/stale
  QuietpaketekönnenFristnichtverlängern, initialerStoppweiter1s. KeineRohwert-
  Filterung/Fristverlängerung/Schwellenänderung. Port-/Witnessfehlereskalieren
  weiterhinseparat. GuardgibtjetztWindow/Samples/qd-/q-Spannen/Grundmitaus.
- PerArm-Grenzen85gezielteTestsPASS; ersterFehlerwarTest-absaufeinerListe,
  korrigiert. NeueRF.03/RR.008-OfflineProfile**nochNICHTdeployed**. Alleanderen
  Armgrenzenje.003, volle40mmReserve/1sStopplatenz/.2Bremsung/.2Frischebleiben.
  NurunbeladeneEinzelphasen; Loadedbackendweiteroffen. Hohe150mmVorposition
  mit11:40OAK63Inlier/2,853px/1,798degalsGeometriekandidat, nochkeinRealflug.
- ZweiterDiagnostikreloadmitFristfixausgeführt, alle4ProgrammeperPLAYwiederher-
  gestellt. Frischer12:39Outputcheck: alle4RUNNING/NORMAL/runtime2/stationär.
  VollständigesMotiontestverzeichnis**212PASS**, eigeneTaskvorbereitung35PASS.
- ZusätzlicheClientSTOP-Korrektur: neueleereStopPort-RPC-Cachesdürfennicht
  bekanntefrischeSupervisorHoldsüberschreiben. Clientbestätigtbewaffnete/
  Witness-/Hardware-/Manager-/Konfig-/Hold-/Latch-EvidenzderbestehendenInstanz;
  beiVerlustsofortNativeFallback, beiunbestätigtemHaltweitermax1s.98gezielte
  Stop-/Guard-/Limits-/PlanungstestsPASS; keinfrischerLocalPortzwangsstopptmehr
  einbereitsgehaltenesgesundesProgramm. PhysischerStillstandgetrenntbestätigen.
- Kamerakoordinatenfehlerentdeckt: eingefroreneOAKWorldposehingamanominalen
  RF-Anchorx.45, aktuellerModellanchor.4955. Task-lokaleReexpressionderalten
  vorläufigenT_anchor_oak ergibt+45,5mmWeltX; keinephysischeNeukalibrierung,
  keineglobaleKameraprofiländerung. AltemAbsoluteWorldPoseistkeinFahrzielmehr.
  Modulhardware_registration.py/3Tests; actualRunnerverlangtpassendenaktuellen
  Anchorbezug. AnnahmeunveränderterphysischerKamera/Basisrelationbleibtvorläufig.
- Aktueller**nurRF**-GeometriekandidatmitkorrigiertemBezug/150mmVorposition:
  setup/tasks/carton_hardware_rf_envelope_20261117_02/, Overlayvisuellgeprüft;
  frisches12:39FotobestätigtKarton/keineHändeinArbeitsfläche. Dryrun02PASS,
  nom196,13sbeiKommando.015/MonitorRF.03, andereArmeje.003. Stopreservenfür
  RF-Nachbarpaarejetzt266mmstatt79mm, vollständigerWegbestehtneueReserven.
  Historischer Stand vor der unten dokumentierten echten RF-Anfahrt. agent-review.jsongilt**nurfourunloadedhighpregrasp**,
  keinKontakt/Greiferziel/Hub. RealeAnfahrtmitunabhängigem20HzObservergeplant.


## Erste reale RF-Anfahrt und visueller Prüfhalt,17.11.

- Nutzer erlaubt für diesen Kartontest explizit die unbeladenen Profilwechsel
  einschließlich kurzer STOP/Wiederverbindung aller vier UR-Programme. RF-Profil
  `carton_hardware_unloaded_rf.yaml` aktiv: Kommando0,015rad/s, RF-Monitor0,03,
  andereArme0,003; volle Abstands-/Frische-/Stoppreserven erhalten.
- RF allein erreicht die geprüfte150mm-Vorposition, andere3gehalten. Ergebnis
  `setup/tasks/carton_hardware_rf_approach_20261117_01/result.json`: SUCCESS,
  AT_HIGH_PREGRASP_HELD_NO_CONTACT, Halt/Softwarelatch und unabhängiges strenges
  Ruhefenster bestätigt.4250nativeSamples/212,448s, max0,0169364rad/s,
  maximale Bahnabweichung0,000133567rad; keine unnötigen NativeSTOPs.
- Foto13:02 (`20261117-130240-standard-ddd114fb`) zeigt deutlichen seitlichen
  Versatz zum Karton. Gelenkziel erreicht bedeutet hier **keine bestandene
  Greifausrichtung**. Kein RR-Ziel, Absenken, Schließen oder Hub ausgeführt.
  Greifer weiteroffen/MONITOR ONLY; alleArmegehalten, Programme später lesend
  alleRUNNING/NORMAL/PLAYING/Reverseverbunden bestätigt.
- Tischboard-basierte Diagnose schätzt gegenüber der historischen, nur am
  Modellanker nachgeführten OAK-Registrierung etwa6,29° Rotationsabweichung.
  RF-boardbasierte Projektion passt sichtbar besser zur realen RF-Geometrie.
 24Ecken/16Fit/8Check, Fit1,185px, heldout2,087px **besteht1px-Grenze nicht**;
  keine Kalibrierung aktiviert. Historische RF-Handeye ebenfalls failed/accepted
  preliminary; RR-Handeye bestanden. Mit beiden historischen Boardfits
  ergeben sich etwa54mm Unterschied im Kamera-WeltY, vermutlich nominale
  Front/Rear-Basislage mitbetroffen; Ursache noch nicht unabhängig bestätigt.
- Diagnose/Overlay unter RF-Lauf `board-alignment/`. Keine stille globale
  Kamera-/Basisverschiebung oder ad-hoc Zielkorrektur. Nächster Schritt: natives
  RF-Wristfoto aus gehaltenem Stand, Board/Handeye unabhängig vergleichen;
  konsistente gemeinsame rechte Referenz und Kollisionsgeometrie vor Kontakt.
- Client-STOP zusätzlich gegen fehlschlagende ROS-Spin-/Observer-Callbacks
  abgesichert: bestehende Supervisor-Holds bevorzugt, bei unbestätigtem Halt
  bounded nativer Vierarm-STOP-Fallback vor Prozessende.38gezielteTestsPASS,
  Log carton-hardware-stop-fallback-regression-20261117.log. Kein physischer
  geladener Stopp- oder Kraftnachweis dadurch erbracht.


## OAK-Neuregistrierung und mobiles Brett,17.11.,13:40

- Nutzer: OAK/Stativ möglicherweise bewegt, Boards/Tische eher unverändert;
  neue OAK-Kalibrierung angeboten. Nicht als bestätigte Kamerabewegung ausgeben.
  Mobiles38mm-ChArUco-Brett verfügbar; gemeinsame OAK/RF-Bildreihe vorbereitet.
- Neuer Wunsch: gute Kameraeinstellungen bestehen lassen statt ständig vollständig
  zurückzustellen. RF jetzt Fokus435MANUAL, Belichtung5000µs/Gain16, Werte im
  `carton_hardware_rf_board_wrist_20261117_01/manual-focus-choice.json`.
  NativeErstfoto vorherAUTOfokus435→498, keinepassendeIntrinsics; nur1Marker,
 0ChArUco-Ecken. NativeWerkzeug meldetROI-Restorefehler, einbegrenzterHTTP-
  Restoreversuch ebenfallsabweichend. Nach eigenemKamera-Watchdog alleoriginalen
  ROI-Wertewiederda/DienstNORMAL, anschließendexplizitnurguteManualwertegesetzt.
  KeineUR-/Arm-/GreiferaktionenindieserKameradiagnose.
- OAKHQ8Frames/Fokus116 um13:33:12, Kamera danach geschlossen. RechterBoard-
  Prüf-RMS2,098px, links0Ecken. `tools/register_oak_table.py`: wiederverwendbarer
  Offlinekandidat mitdisjunktenFit-/Prüfecken, geprüfterFokus-/Bildgrößenbindung,
  QuellhashesundexplizitemhistorischenAnker. KeineKalibrieraktivierung/Fahrziele.
  ReferenzRRweilHandeyebestanden; RF-Fitbleibtfalse/acceptedpreliminary.
- DreiunterschiedlicheAufträge11:40/13:02/13:33: maxAbweichungvonMittelpose
 0,599mm/0,0271°, Prüf-RMS1,998/2,087/2,098px. WiederholbarkeitamgleichenBoard,
  keinunabhängigerAbsolutgenauigkeitsnachweis;1px-KriteriumweiterNICHTbestanden.
  Resultat `setup/tasks/carton_oak_reregistration_20261117_01/three-capture-fit/`.
  HistorischebeideBoardfits implizierenFront/Rear1,4002mstattnominal1,35m;
  keineglobaleBasisänderung/keineuntergeschobeneFramekorrekturangewandt.
- GemeinsameKamera-App unterstütztjetzt `--cameras right_front oak4` und
  `--keep-camera-settings`; letzteres liest/speichertEndwerteohneRückstellwrites.
  LED-LeaseundFormat-/Dienstwiederherstellungweiteraktiv. DefaultandererSitzungen
  erhalten.26gezielteKamera-/Board-/RegistrierungstestsPASS; DiffcheckPASS.
- ReineKameraansichtläuftsichtbaralsBenutzerdienst
  `uwa-carton-oak-registration-view-20261117.service`, eigenesDataset
  setup/calibration/carton_oak_reregistration_20261117/20261117_134040_4b64828d/.
  OAK-LivepreviewhältjetztKamera-Lease; fürweitereFotosdieseeigeneAnsichtnutzen/
  Previewgeordnetpausieren, keinekonkurrierendeSDK-Aufnahme. Nutzerstelltmobiles
  BrettfürbeideSichtenbereit, danachgemeinsameEinzelaufnahmen mitBrettstillstand.
  Armzustandweitergehalten/offeneGreifer; nächsteArmfahrtwartetaufRegistrierung.

- Abschließender lesenderCheck13:42: alle4nativeArmeRUNNING/NORMAL aber
  runtime1/ProgrammSTOPPED, alle4stationär; RF/RRACT1/STA3/FLT0/OBJ3/POS3/PRE0.
  NeueTrace carton_camera_hold_checkpoint_20261117_01: alle4Ressourcenholds
  bestätigt, Supervisor WATCHDOG LOST OR TRIPPED, Watchdogtripped, keinefrischen
  Guard-Decision-Paketeim3sFenster. JournalordnetersteNativeSTOPsum13:27:14
  fehlenderHardware-/Managerfrischezu (ca0,26–0,30s), danachgelatchterWatchdog.
  KeinSafetyStop/NativbewegungbeiKontrollmessung; UrsachenichtdurchneuesPLAY
  übergangen. Foto-Apperst13:40gestartet, daherderenStartnichtalsAuslöser
  behaupten. VorjeglichernächsterArmfahrtGuard-/Frischeproblemaufklären.
  FürmobileFoto-ReihekeineProgramm-/Reset-/Profilaktionerforderlich.
