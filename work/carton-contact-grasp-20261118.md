# Reale Karton-Kontaktaufnahme18.11.2026

- Status: **19.11.2026 abgeschlossen mit gehaltenen beidseitigen Kontakten; Gesamtablauf beim Abschluss-Ruhecheck abgebrochen.** Hauptagent Kartongriff. Beide rechten Greifer am aufliegenden Karton; RR-Programm STOPPED, alle4Arme aktuell gehalten/stationär. Kein Reset/Play/Öffnen oder unabhängiges Armziel nach Kontakt. Aktuell maßgeblich ist der letzte Abschnitt; frühere Tageszustände sind historische Belege.

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

## Erneuter ausdrücklicher Fahr-/Greifauftrag

- Nutzer beauftragt erneut Vorpose plus Greifen. Aktuelle0,1rad/s beibehalten,
  kein Hub geplant. Einmaliger expliziter ROS-Programmstart im Runner jetzt nach
  abgeschlossener Geometrie unter frischen All4Holds/Stationarität/offenen
  Greifern/nativeNORMAL; Telemetrie während CLI im Hintergrund weitergespinnt.
  Keine Safetyquittierung/Fristlockerung/automatische Fehlerschleife. Neuer
  Flag --start-ros-programs;12 gezielte Eligibility-/Discovery-/Timingtests PASS.
- `setup/tasks/carton_grasp_20261118_go_real01/result.json`: beide hohen
  Vorpositionen tatsächlich erreicht, alle Endholds und unabhängigen Ruhefenster
  PASS. Keine Fingerkommandos/Kontakt/Hub. Jetzt offene Einfahrt vorbereiten.

- Offene Einfahrt mit C2-Cartesian-Line offline geprüft: `open_entry_plan01`,
  beide Arme ALIGN+ENTRY geometrisch frei, voller Primär-Interarm-/Tischschutz,
  zusätzliche offene Meshgeometrie und35mm-Kurz-Wandhülle/5mmRandannahme.
  Keine Touchausnahme bewegterArm/Karton,2×etwa6,4s Einfahrt bei0,1rad/s.
  Noch NICHT ausgeführt; Annahmen sind keine gemessenen Toleranzgrenzen.
- Aktuelle Wristfotos an neuen Vorgriffen beidePASS. Boardcheck OAK68Ecken/
  1,344px, RF20Ecken/3,850px. Konkreter Konflikt: direkte rechte Boardanbindung
  vs bisheriger globaler OAK-zu-Basis-Kandidat ergibtRF42,9/RR40,1mm Differenz.
  Basisprofile bleiben übernommen; bisherige Einfahrt NICHT freigeben. Jetzt
  aktuelle Pose direkt über sichtbares festes rechtes Board erneut bestimmen.

- Aktuelle OAK-Aufnahme17:32:31, drei unverändert gültige Texturhypothesen
  28/30/26Inlier,2,752/2,819/2,290px. Board68Ecken/1,394px. Unterstützte
  aufrechte Pose zusätzlich aus sichtbarer Tischauflage geschätzt: RMS3,331/
  3,385/2,950px innerhalb unveränderter jeweiliger Registrierungsschwellen;
  Positionsstreuung0,370mm. Das ist eine explizite Support-Estimatorprior, keine
  Lockerung des2°-Targets-Gates. FreierFit hatte2,122° Frame-Neigung.
  `scene04/per-arm-board-supported-binding.json`: gemeinsamer Objektframe
  direkt über rechtesfestesBoard; übernommeneBasisanbindungen unverändert.

- Weitere Board-Korrekturanfahrten vor FJT-Ziel abgebrochen: real01
  Driveralignment-Lücke während Controlleraktivierung, All4Holds restauriert;
  real02 danach LRnativeDatenSTALE noch vor Reset. Kein korrigierter Board-
  Vorgriff erreicht. Beide tatsächlichen hohen Vorgriffe ausgo_real01 bleiben
  aktueller Stand, keine Einfahrt/Finger-/Hubaktion.
- ROS-Serviceclients imApproachClient persistent vor Driverhistory aufbauen;
  RMW-Create/Destroy nicht mehr bei jeder Aktivierungsabfrage. Laufzeiten werden
  protokolliert, Diagnosehypothese für Callbacklücken, keine bewiesene Alleinursache.
- Hostmessung:22GiBRAM,8GiBSwapfastvoll; eigener Hardwaredienst111MBresident/
  614MBausgelagert, hoherIO-Durchsatz. Eigenen Hardwaredienst mit identischen
  Grenzen neu geladen, BLAS/OMP/MKL/Numexpr1Thread; runtimeMemoryLow1GiB,
  SwapMax0,CPUWeight1000. Danach637MBresident/Swap0. KeinefremdeSimulation
  geändert. Vortrace unvollständig(Guardtopicfehlte), Assertion stoppte wegen
  fehlendemShellset-e den genehmigten Neustart nicht; ExecStopPostnativeSTOP
  aller4 aktiv. KorrigierteFolgekommandossetzen-e. NochkeineFahrt daraus.
- Voller20s-Nachtrace:alle4gehalten/stationär,GuardModelMatch/keineFaults,
  Witness beimStart gelatcht. EinmaligerWitnessresetunterLivequorum vorgelagert
  scheitert bereits an reinemGreifer-Read-RPC3s, keinReset/Play/Fingerziel dabei.
  PrüfeaktuellDevicesdirektlesend undverbinde eigenenMonitor-Greiferdienst neu.

- Geräte-Direktlesetest nachSpeicherschutz:alle4Arme beobachtet/stationär,
  beideRechtsgreiferACT0/STA0/OBJ0/POS3/PRE0/FLT0, weiterhinkeineFingerbefehle.
  EigenerMonitor-Greiferdienstwar199MBresident/149MBausgelagert; ebenfalls
  runtimeMemoryLow256MiB/SwapMax0/CPUWeight500gesetztundMONITOR ONLYneu
  verbunden. Anschließend erneuter einmaligerWitnessresetnurbeiLivequorum.

- Um17:56 gleichzeitigSIGTERM/beendeteROS-Kontexte in Simulation, Overlay,
  HardwareGuard/Witness/Supervisor, Grippern und allen vier UR-Treibern.
  Dashboardnachweisalle4NORMAL/STOPPED, keineReverseListenermehr. Nutzer
  erläutertspäter, UWA Robot Power fürTestsgehaltenundbeendet zuhaben.
  CodecloseEventbeendetnurStatusprozess, nichtdauerhafteTreiber; breite
  Signalbeendigungdamitnichtabschließendkausalzugeordnet. KeineFremdprozesse
  vonunsdafürbeendet. NurHardwareanbindung/MonitorAPI/Schutzdiensterestauriert
  undneueinaktiveHoldcontrollerprovisioniert. Alle4Holds/Stationarität belegt.
- AktuelleWiederherstellung: WitnessnachliveQuorumeinmalzurückgesetzt,
  Programmstartall4READY. ErsterFahrvorcheck(real04) nochvorReset/Zielabgebrochen,
  weilLRnachStartnochkeine0,5sGuardruhehatte. Runnerwartetjetztbis3s auf
  exaktbestehendesRuhekriteriumbeiweiterfail-fastHealth, stattsofortabzubrechen.
  KeinerleiGrenzlockerung. NutzerwunschkeineweitereTestreihefestgehalten.
  VorhandeneKorrekturbahnwirdnunmitbereitslaufendenProgrammen ohnePlay erneut
  ausgeführt(real05), keineNeuplanung.

## Offline-Abschluss nach ausdrücklichem Hardwarestopp

- Nutzer18.11.: Hardware heute stoppen, Software fertigstellen, morgen testen.
  Eigene Schutz-/Greiferdienste kontrolliert beendet (Schutzdienstinactive/dead),
  nur abschließender nativer STOP über existierende Nachbehandlung. Danach keine
  weiteren Geräte-/Fahr-/Fingerzugriffe. Tatsächlicher letzter hoher Armstand
  bleibt go_real01; Board-Korrekturen, Einfahrt und Fingeraktionen NICHT ausgeführt.
- Armweise Freigabe fertig: Interlock bestätigt nur angefragte Mitglieder aus
  der unverändert geometrisch/zeitlich geprüften Guard-Antwort. Andere Holds
  bleiben aktiv; neue STOPs und Guardneustarts gewinnen. Supervisor-Resetaufrufe
  serialisiert. Runner übernehmen vorhandene andere Holds statt sie nach
  globalem Release erneut perRPC anzufordern. Reale Bestätigung morgen offen.
- Expliziter Programmstart unter freien hohen/all4gehaltenen Armen setzt nur
  den bestehenden Softwarewitness einmal zurück und wartet dessen bereits
  ausgegebene native STOP-IO ab. Kein Safetyack/Retryloop. Andere RPCs persistent.
  Fehlerberichte enthalten bestehende Hold-/Frischeflags, keine weitere Gateebene.
- Bausteine: prepare_carton_recipe.py, register_carton_from_oak.py, hohe Anfahrt,
  offene Einfahrt, carton_gripper_phase.py prepare/close. Statischer Schluss
  minimumFOR0/SPE16; anschließend nur HOLD und eingefrorene virtuelle Gruppe,
  kein unabhängiges Armziel/kein Hub. NativeOBJ2 ist kein4-Pad-/Kraftnachweis.
- Neue Rezeptdaten direkt aus versioniertem Asset statt inzwischen entferntem
  historischen16.11.-Simulationsordner. Neue vollständigeOfflinekette liegt in
  setup/tasks/carton_grasp_20261118_offline_finish/: recipe-v2, registration-v2,
  high-plan-v2, entry-plan-v2, entry-recheck-v2. Nur archiviertes Foto/alte
  Gelenkmessung und geplanter zukünftiger Hochpunkt, keine aktuelle Morgenpose.
- Offline: aktuelle Bildregistrierung reproduziert, hohe Zukunftsziele und
  offeneEinführung ohnejedeArm/Karton-Kollisionsausnahme geometrisch gültig,
  kompletterEinfahr-ReplayPASS. ZentraleStopp-/Reset-/Zeit-/Statuslogik mit
  gezieltenSoftwarechecks geprüft; keine reale neueQualifikation daraus ableiten.
  Bedienung docs/carton_supported_grasp.md; Fahrprofil hardware_carton_supported.yaml
  unverändert0,1rad/s/geometric_only/40mm. BLAS1 und Schutz gegenSwap nur für
  eigene Hardware-/Greiferdienste in Startskripten; keine fremden Dienste geändert.

## Fortsetzung19.11.2026

- Nutzer sagt ausdrücklich „okay, wir können weitermachen“; gestriger Stopp damit für diese Aufgabe aufgehoben. Normalen gestützten Greifablauf fortsetzen, keine zusätzliche Testkampagne. Unverändert0,1rad/s, zunächst kein Hub/Transport.
- Erste reine Dashboardabfrage: alle4 erreichbar, POWER_OFF/NORMAL/STOPPED. Regulärer bereits freigegebener Bringup läuft; noch keine Fahr-/Fingerziele. Aktuelles Foto über vorhandenen Dienst/Fokus107 angefordert. Daten in `setup/tasks/carton_grasp_20261119/`. Eigene Schutz-/Greiferdienste für normalen Ablauf erneut bereitstellen; fremde Prozesse erhalten.

- Aktuelles OAK-Foto10:30:39/Fokus107: Board68Ecken/1,562px; Textur44/47/27Inlier, drei Supportfits3,201/3,115/3,107px; interne Streuung0,319mm/0,060°, keine absolute Genauigkeitsbehauptung. Overlay visuell passend. Pendantbestätigungen vom Nutzer erledigt.
- Regulärer Bringup scheitert an den seit18.11.18:00 weiterlaufenden vier Treibern: alle ros2_control_node exakt1024FD bei Softlimit1024, Logs „Too many open files“, Manager ohne Antwort/Reverse nicht verbunden. Eigene Dienste waren beendet, persistente Treiber blieben bestehen. Gezielter nativer STOP und Ersatz nur dieser4Dienste; keine Änderung an Sicherheits-/Frische-/Geschwindigkeitsgrenzen. Erste Offline-Planerstellung mit noch POWER_OFF-LR-Snapshot korrekt abgelehnt; nach Bringup neue Messung/Plan erforderlich.

- Frische Treiber/Betriebsanbindung und alle4Messzustände RUNNING/NORMAL bestätigt; inaktive Holds provisioniert, eigener Schutz-/Greiferdienst bereitgestellt. Erste hohe Ausführung `high/` vor jedem Ziel korrekt abgebrochen: ein im vorbereiteten Runner übersehener Aufruf nutzte noch globalen Supervisorreset, während RPC-Vorprovisionierung/Entry bereits armweise waren. Nichtselektierte Latches dadurch nicht bestätigt. Fehlerhold bestätigt alle4 Ressourcen/Latches, arm_commands[]/finger_commands[]. Eine Zeile auf `collision_supervisor/<arm>/reset` korrigiert, Syntax geprüft; neuer Lauf `high-scoped/`. Keine Grenzänderung, keine eigene weitere Testkampagne.

- `high-scoped/`: armweiser Reset erfolgreich, übrige3Ressourcen/Latches erhalten. Goal akzeptiert, aber noch vor nennenswerter Bewegung Datenalterfehler LR im Ablaufmonitor. RF-Nativepeak0,000445rad/s und Gesamtänderung<0,04mrad, kein Greiferbefehl. NativeSTOPalle4 bestätigt; anschließende vollständige Live-Lesung bestätigt alle4Holds/frischeManager, Guard ohne aktuelle Faults, Witness nicht getrippt. Keine reale Vorpose erreicht.
- Enger Befund: voller zusätzlicher FCL-Check nur3,47ms, Guard-Auswertung12,21ms/100msBudget/0Overruns, Schutzprozess0Swap, System69%idle. Kein belastbarer Hardware-/Netzwerkfehler daraus abgeleitet. Bestehende20Hz native Daten wurden nur10Hz weitergegeben; Aufgabeprofil auf20Hz gesetzt, um diesen zusätzlichen bis100msPublikationsanteil zu verkürzen. Keine Frischegrenze/Abstände/Tempolimits geändert, keine neue Prüffunktion. Eigener Schutzdienst gezielt neu geladen; neue evidenzgebundene Anfahrt erforderlich.

- `high-20hz/result.json` tatsächlicher PASS: beide korrigierten Hochpositionen erreicht, je1akzeptierte/gefahrenePhase,0Guardstopps, Endholds und beide Stillstandsnachweise bestanden. BahnrestfehlerRF0,123/RR0,234mrad. Jetzt Greiferprepare an den hohen freien Positionen und offene Einfahrplanung, noch kein Greifschluss/Hub.

- Erste Aktivierung gelang, Öffnungsparameterbestätigung scheiterte vor POS/GTO: SPE0, RR-FOR16 statt0 trotz ACK. Arme unverändert hoch gehalten. Transport setzt nun FOR mit bestätigtem Readback vor SPE (zuvor beide SETs direkt nacheinander); keine automatische Wiederholung, unveränderte Parametergrenzen.10gezielte vorhandene Transporttests PASS. Öffnungs-prepare akzeptiert aktivierten Bootzustand OBJ0/POS≤8/COU0 ausschließlich für Öffnen an hoher gehaltenenPose, niemals für Einfahrt/Schließen;4gezielte Tests PASS. Lokaler HeldMonitor leert vorhandene Callbackqueue vor identischer Altersprüfung.
- `grippers-open-parameters/result.json` tatsächlicher PASS: beideACT1/STA3/OBJ3/POS3/PRE0/SPE16/FOR0/FLT0/COU0; ACTIVE_OPEN_HELD, kein Hardwarefault. Keine erneute Aktivierung, kein Kontakt/Hub. Offene Einfahrgeometrie `entry-plan/` PASS ohne Arm/Karton-Touchausnahmen. Aktuelles Hoch-/Offenbild vor Einfahrt angefordert.

- Hoch-/Offenfoto10:47:38 visuell geprüft: beide freien Backenpaare über den vorgesehenen kurzen Wänden, Karton auf Tisch. Planinputs unverändert/hashgeprüft. Vor Erst-Einfahrt weiteren deterministischen Übergabefehler verhindert: zwei follow()-Aufrufe hätten zwischen ALIGN/ENTRY erneut refresh_after_validation unter bereits eigenem aktivenController verlangt. Identische geprüfte Primitiven deshalb proArm in einer Action mit unveränderten Einzelzeitgesetzen/Null-v/a-Verbindung übertragen, keine zusätzliche Halte-/Resetfolge oder Streckung.5gezielte Tests PASS; realer Einfahrversuch `entry/` jetzt gestartet.

- Reale offene Einfahrt `entry/result.json` PASS: BOTH_OPEN_AT_WALL_HELD_NO_CLOSE, beideEndholds/Stillstände bestätigt,0Guardstopps; RF/RRRestfehler0,122/0,196mrad. NativeSpitzen0,10327/0,10180rad/s innerhalb bestehender5%Monitortoleranz; keine Wrench-Deltaabschaltung. Keine Backenkraftmessung daraus ableiten.
- Aktuelles OAK-Einfahrfoto10:50:29 (`20261119-105029-standard-65334fd8`) und Nahbild `entry-jaws.jpg` visuell geprüft: je ein Backenpaar beidseits der jeweiligen kurzen Wand, Karton unterstützt auf Tisch, kein sichtbarer unerwünschter Kontakt. Dies ist OAK-Sichtprüfung, keine neue Wrist-Zentrierbehauptung. Statischer minimaler Greifschluss jetzt explizit ausgeführt; nach Kontakt nurHOLD, keine unabhängigen Armziele.

## Abschluss19.11.2026: Kontakt vorhanden, nurHOLD

- `grasp/` schließt beide Greifer tatsächlich mitFOR0/SPE16. Beide Aktionen melden
  Erfolg/Objektkontakt: ACT1/STA3/FLT0/OBJ2/PRE255, RF-POS204/RR-POS202.
- Gesamtablauf bewusst nicht PASS: während Schließen RR-Ruhebeleg länger als1s
  verletzt. Native qd-Spitzen bis0,005016rad/s gegenüber bestehend0,001;
  Positionsspanne maximal0,000313rad. Supervisor sendet10:51:24 nativenRR-STOP,
  Guard verriegelt betroffene Paare wegen PROGRAM INTERRUPTED. Kein Kollisions-
  oder50N-Verletzungsnachweis daraus ableiten. Keine Schwelle geändert oder
  Wiederaufnahme versucht; Greiferziele erhalten. Original `grasp/result.json`
  mit HELD_NO_AUTOMATIC_RECOVERY und Native-Readinessfehler bleibt erhalten.
- Rein lesende Nachaufnahme `grasp/final-held-state.json`: frische4Quellen,
  alle4Holds/Manager bestätigt, alle4nativstationär, SafetyNORMAL. RR STOPPED,
  übrige3PLAYING. Beide Kontaktmitglieder mit gemeinsamem virtuellem Objektframe
  und festen Objekt→TCP-Offsets gesichert; ausschließlichHOLD, keine unabhängigen
  Armziele/geladenen Bewegungen freigegeben. Quelle ist kein Post-Clamp-Posefit.
- Abschlussfoto10:52:24 `setup/oak4/photos/20261119-105224-standard-949b772a/`,
  Vorschau/Nahbild `setup/tasks/carton_grasp_20261119/grasp-{preview,jaws}.jpg`:
  beide Backenpaare sichtbar an den kurzen Wänden, Karton weiter auf Tisch,
  keine offensichtliche Beschädigung. Keine Tragfähigkeit/Backenkraft qualifiziert.
- Softwarefehler im Fehlerpfad korrigiert: bestätigte Kontaktmitglieder und
  HOLD-only-Gruppe sofort nach Statusreadback speichern, BEVOR abschließende
  Armprüfung eventuell fehlschlägt. Gezielter Offline-Fehlerpfadtest bestätigt,
  dass Native-Readinessfehler keinen geklemmten Karton als unbeladen hinterlässt;
  `contact-retention-check.log`:5PASS. Keine reale Wiederholung zum Testen.
- Nächste physische Aktion muss ausdrücklich den vorhandenen Kontaktzustand
  berücksichtigen. Keine normale unbeladene Vorpose/Programmerholung ausführen.
