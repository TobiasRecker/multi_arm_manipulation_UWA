# Kartonzyklus und Betriebsübergabe auf N100,19.11.2026

- Status: abgeschlossen (Griff gehalten; störungsfreier Zeitbenchmark offen), Hauptagent dieses Kartonchats. Nutzer bestätigt ausdrücklich den korrekten realen Griff. Neuer Auftrag: Karton auf Tisch loslassen, nach oben ausfahren, Home, vollständigen Griffzyklus wiederholen und Gesamtdauer messen; UR-Steuerung auf vorbereitetem N100.
- Lösen zuerst auf bestehendem ROSmini-Host ohne Armbewegung, damit Steuerungswechsel unbeladen erfolgt. Danach gezielte Übergabe aller4Treiber/Guard/Greifer an N100; GUI bleibtROSmini. Keine Doppel-Treiber, keine Fremddienständerung.0,1rad/s unverändert.
- N100 aktuell erreichbar,7.0.0-43-realtime, realtime1, echte UR-Dienste inaktiv. Installation/Mock vorbereitet; External-Control-Hosts an Pendants laut Übergabe noch nicht umgestellt. Vor Liveübergabe aktuellen Quellstand und nötige Taskdaten übertragen; keine neue separate Testkampagne.
- Zeitlogger `setup/tasks/carton_cycle_n100_20261119/timing.json`: Vorbereitung/Hostwechsel/Rücksetzen und eigentlichen Wiederholungszyklus getrennt protokollieren; erste Dokumentlesung vor Logger als ausgeschlossen markieren. Keine Vorbereitung als reine Zykluszeit ausgeben.
- Geplante eigene Neustarts: vorhandene ROSmini-Hardwaredienste erst nach bestätigtem Loslassen kontrolliert stoppen; N100-Dienste anschließend exklusiv starten. Kontakt zunächst nurHOLD, Loslassen ausdrücklich neu beauftragt.

- Loslassen tatsächlich erfolgt: beide ACT1/STA3/OBJ3/POS3/PRE0/FOR0/SPE16, remaining_contact_members[]. Lokaler Öffnungsmonitor registriert wieder kurz fehlende Ruhe, Ergebnis HELD_OPEN_UNCONFIRMED bleibt erhalten; danach explizite frische Holds/Stillstände mit erlaubtem STOPPED-Programm nachgewiesen (`pre-host-switch-held.json`). Keine Kontaktbindung mehr.
- NativerSTOPaller4 bestätigt. Standard-Hardware-stopCLI erzeugte eigene neue StopPorts und bestätigte Ruhe nicht innerhalb5s; keinen Erfolg erfunden. Anschließende bestehende aktuelle Hold-/Ruheprüfung PASS, danach nur eigene6Hardwaredienste kontrolliert geschlossen; `rosmini-services-stopped.txt` alleinactive. N100nochkeineechtenDienste.
- AktuellerQuellstand übertragen, fehlende zwei Carton-PrepareTools im Staging ergänzt. Isolierter N100-Build18Pakete/21,1sPASS. Pendant-Hostumstellung aller4auf192.168.8.5/Ports51002,52002,53002,54002 beimNutzer angefragt, nochabzuwarten.

- Nutzer bestätigt Pendant-Hostumstellung mit „erledigt“. Regulärer N100-Livebringup/Provisionierung/Schutz- und Greiferstart jetzt beauftragt ausgeführt; ROSmini-Dienste bleiben aus. N100-Retreatplan tatsächlich geometrischPASS, je6,412/6,374snominal bei0,1rad/s. Home-Direktpfad und erster Zwischenvorschlag noch verworfen; keineHomefahrt freigegeben, weitere Offlineplanung nötig.

- Tatsächlicher N100-Bringup alle4ready, Holds provisioniert, Guard/Greiferservice aktiv. `retreat/result.json` realPASS: beide150mmhoch, Endholds/Stillstand bestätigt. Keine ROSmini-Hardwaredienste mehr.
- Home-Direktpfad RF verletzt Modell-Nachbarpuffer (nativeFCL/Carton am ersten verworfenen Zustand frei). Alternative zuerst aufrichten, dann Basisdrehen vollständig geprüft. Homefahrt RF erreicht nominalenGrenzbereich-360°, stoppt an 1,26µrad Unterlauf durch Encoderrauschen. Kein Kartonkollisionsnachweis; vorhandene Fehlermeldung war ungenau und enthält jetzt Modellprüfungsgrund. Alle4Holds im Fehlerpfad bestätigt.
- Homeziel an physischen Winkelgrenzen1mrad nachinnen gelegt (keine Mess-/Stopptoleranz gelockert), aktueller Wiederanlauf `home-interior/` aus neuerMessung. Geschwindigkeiten unverändert. NochkeinneuerGreifzyklus begonnen.

- Nutzer meldet RF-Vorpose „Ellenbogen unten“, RR gut. Vorpose hatteRFq_elbow+1,143 statt zuvorerfolgreich-1,15. IsolierteVorposewarModellgültig, nachfolgendeEinfahrtaberbei59,8% wegenprimäremNachbarpuffer verworfen, keineEinfahrt/Schließungausgeführt. ZusätzlichnativerAll4STOPaufNutzerkorrektur bestätigt. ErsteZeitserie bleibtalsFehlversuch erhalten; keine„saubere Zykluszeit“ daraus ableiten.
- VerbindlicheLehre Nutzer19.11.: vor Zahlen logisch über Aufgabeneignung nachdenken; EllenbogenuntenbeiTischgriffnachteilig, HandgelenkinnenbeiNähezumanderenRoboternachteilig, beideskontextbezogenkeineGlobalverbote. Danach Gelenkreserven, ManipulierbarkeitundweiterebegründeteMaße. InAGENTSalsübertragbareRegelfestgehalten.
- Umsetzung: Kartonrezept RFphysischerEllbogenzweignegativ (sin desWinkels, unabhängigvon2piWinding), nächstliegendesWindingbeibehalten. NachGeometriefilterParetorangfürGelenkreserven, skalierteJacobi-Singularität, Wrist-NachbarabstandundWeg; Kennzahlen/BegründungimKandidatenartefakt. GesamteEinfahrtkünftigvorhoherReal-Anfahrtprüfen. AktuelleKorrekturplantnurRF, RRbleibtIstpose.

- ErsteKonfigurationskorrektur direkt/überaufrechteZwischenpose ohnegeprüftenPfad. LängereOffline-RRT-SucheRFallein gestartet (60sjeKandidat, keinProfilwechsel). KeinGoalaufdiesen negativenBefundhin. NumerischeBranch-Invarianztests2PASS; ersteTestimporteimnichtneugebautenOverlayfehlgeschlagen undquellbasierterImportkorrigiert. VollständigeEinfahrprüfungimzeitprotokolliertenWorkflowvorhoheRealbewegungverschoben, keinezusätzlichePrüfkampagne.

- Ursache der erfolglosen branchnegativenKorrektursuche zusätzlichaufgeklärt: reineZufalls-IK hattezwarnegativenEllbogen, aberanderen Schulter-/Handgelenkzweigmitfast2piSchulter gewählt. Vorhandenen realbewährtenRFSeednunalsreineIK-StartschätzungfüraktuellenBildtargetverwendet (keinReplay); RRSeed ausvomNutzerakzeptierterPose. `rf-vetted-plan` GEOMETRIC_PATH_FOUND, direktergeprüfterPfad, RF-Ziel[-5,2390;-2,0767;-1,1448;-1,4917;1,5743;-0,5436]. Kein RR-Ziel.
- GesamtebeidseitigeEinfahrtvorRFKorrekturbewegungofflineprüfen, dannRFhoheKorrekturfahrtgestartet; Erfolg erstnachErgebnisbehaupten. NeueRezeptur `recipe-vetted`, gespeicherteSeeddatenmitHerkunft undfrischerIK-/Geometrieprüfung stattZufallszweigwahl.

- KorrigiertebeidseitigeEinfahrt `corrected-entry-plan` bestehtvorab. RF-Korrekturlauf aber VORControlleraktivierung/FollowJointTrajectoryabgebrochen: neuerNativeSTOPRR12:06:20 wegenRuhegeschwindigkeit0,0010157rad/s beiPositionsspannen<0,000089rad, obwohlalleRessourcenholdsbestätigt. KeineKorrekturfahrtstattgefunden, RRweiteramgutenHochpunkt/RFweiterpositiverEllbogen. KeinRücksetzenimBlindloop.
- Konkreter Kandidat offline vorbereitet, NICHTaktiv: `hardware_carton_supported_trend_candidate.yaml`. ArmruheüberlinearenPositionstrend stattjedemrawqdPeak; vorhandene0,0005radSpanne/0,5s bleibtgleich, rawGeschwindigkeitsstop0,1rad/s/Frische/Kollision/UR-Sicherheitunverändert. DefaultprofilbehältPeakmodus. LokalerGuard/HeldMonitorunterstützenOpt-in, N100laufenderDienstnichtgeändert. GezielteDefault-/Drift-/Sprung-/Rohspeed-/Stale-Prüfungenbestanden; NutzerrückfragewegenBestandsschutzSicherheitsstoppsvorAktivierungnotwendig.

- Nutzer gibt neuenRuhenachweis ausdrücklichfrei: „Ja, Ruheprofil aktivieren“. AktiveFassung `hardware_carton_supported_trend.yaml` erzeugt; nachaktuellenHoldsnurN100Guardgezieltneu laden, keineDriver-/Greiferneustarts. AnschließendFreshObservation/PlanbindungmitneuemProfil. BestehendePeakdefaultprofile unverändert, RawSpeedstop/Positionsspanne/Frische/Abstände unverändert.

- RF-Korrektur unter explizitgenehmigtemTrendprofil tatsächlichPASS (`rf-trend-correction/result.json`, AT_HIGH_PREGRASP_HELD_NO_CONTACT). NurRFgefahren, RRunverändert. GanzeEinfahrtzuvorPASS. AktuellesHochbildfürvisuelleKonfigurationsprüfungangefordert.
- FürgewünschtebrauchbareGesamtzeit jetztklarseparierterNeustartabHomegeplant, ohneerstnochKontaktzuverursachen. UnterbrochenerErstversuch/Korrekturbleibenseparat. KeinAusschlussvonFehlernauseinerbehauptetensauberenSerie. Profile/Config0,1 unverändert.

- KorrigierteHochposevisuellbestätigt (`corrected-high-preview.jpg`): beide passenderGriffzweig, RRunverändert. Rücksetzen `clean-home/result.json` realPASS beideoffenHome. SeparaterZeitlaufcycle02abHomejetztgestartet, korrigierteRezeptur/VorprüfungganzerEinfahrt.
- Auto-Review lehnte dauerhafteTrendprofil-StandardumstellungmehrererWerkzeugeab (FreigabenuraktuellerKartontest). Nichtumgangen: lokaleDefaultänderungenzurückgenommen, N100Standardsunverändert, aktuellerZyklusnutztgenehmigtesProfilnurexplizitvia--config. PhysischeAufgabeimzulässigenUmfangweitergeführt.

- ErweiterteNutzerfreigabe: „Du kannst das Ruheprofil auch in Zukunft verwenden ... auch noch etwas laxer machen.“ DauerhafteNutzungundfachlichbegründeteweitereRuheanpassungdamitgenehmigt; keineimpliziteFreigabeandererGrenzen. AktuellerAbbruchcycle02betrifftSupervisor-/Watchdogherzschlag, nichtRuheprofil; getrennteUrsachenprüfungstattblindRuheweiterlockern.

- 12:42: N100-Guard mit vorprovisionierten Cancel-Clients/RR20 aktiv; Scheduler
  tatsächlich geprüft. Aktuell alle4 frische Holds, keine Guardfehler, nur
  Start-Witnesslatch. Keine Frischegrenzen gelockert. Neuer cycle03 mit frischem
  OAK-Foto12:42:12 gestartet, Taskprozess mit1CPU-Quota getrennt von Treibern/
  Guard; .1rad/s unverändert. Trendprofil nun genehmigter Karton-Toolstandard,
  ältere Auto-Review-Blockade durch neue ausdrückliche Nutzerfreigabe aufgelöst.

- cycle03 abHome erneut unterbrochen: RF erreicht gewünschte hohePose tatsächlich
  undEndholdPASS (Bewegung beiqd>.003 etwa28,21s). VorRR-Ziel nativerRRSTOP,
  Hardwarekomponenten-RPC0,319533salt; RRbleibtHome, beideGreiferoffen. Keine
  offeneEinfahrt/Schließung, keinebehauptetesaubereZykluszeit. Phasenlaufzeiten:
  Snapshot3,04s/Registrierung19,88s/Planhoch37,18s/Planeinfahrt50,24s/High203,41s.
- KonkreterÜbergangbehandelt: beideArm-Clients/ObserverundalleGripper-Read-RPCs
  vorProgrammstartprovisionierenundbisSerienendeerhalten; keinNode-/Action-
  Auf-/AbbauzwischenRFundRR. ZusammenhangmitRPC-Aussetzerzeitlichbeobachtet,
  UrsachennachweisnochkeineDauerstabilitätsgarantie.7gezieltePrüfungenPASS.
- Fortsetzung`continuation/` ausfrischerPose/Fotografie12:50:57gestartet, kein
  zusätzlicherHome-Reset. Zeitseitcycle03HomeinklusiveFehler/Korrekturerhalten.
  ErstnachaktuellerEinfahrtaufnahmevisuellprüfenundschließen. RealeDienste
  weiterhinN100; keineparallelenArmzugriffeandererAgenten.

## Kartonzyklus N100 abgeschlossen,19.11.2026,13:01

- **Aktuell beide rechten Greifer am aufliegenden Karton geschlossen. Nur HOLD.**
  RF/RR melden ACT1/STA3/FLT0/OBJ2/PRE255/FOR0/SPE16, POS204/202.
  Abschlussprüfung `continuation/grasp-started/result.json` tatsächlich PASS,
  `SUPPORTED_TWO_ARM_CONTACT_HELD`, beide Kontaktmitglieder und statischer
  Endhalt bestätigt. Gemeinsamer virtueller Objektframe/TCP-Offsets eingefroren.
  Keine unabhängigen Armziele, kein Reset/Play/Öffnen, kein Hub als automatische
  Erholung nach Kontakt. Geladene Hardwarebewegung bleibt nicht implementiert.
- Abschließender unabhängiger Lesesnapshot `final-held/observations.json`:
  alle4 Programme RUNNING/runtime2, safety1, stationär; Positionsspannen im
  kurzen Snapshot maximal0,000125rad. Aktuelles OAK-Abschlussbild unter
  `setup/tasks/carton_cycle_n100_20261119/final-{preview,jaws}.jpg` (ROSmini).
- Betriebsanbindung nun N100 `~/uwa-ur-runtime`, Domain66/LOCALHOST, GUI ROSmini
  `--n100`. Alle4 External-Control-Hosts192.168.8.5, Ports unverändert.
  Keine parallelen ROSmini-Hardwaredienste starten. Geschwindigkeitsgrenze
  unverändert0,1rad/s, Beschleunigung0,2rad/s², Modellpuffer40mm.
- Ruheprofil `hardware_carton_supported_trend.yaml` aktiv und auf neue
  ausdrückliche Nutzerfreigabe auch künftig Karton-Toolstandard. Armruhe über
  Positionstrend, weiterhin0,0005radSpanne/0,5s. Weitere fachlich begründete
  Ruhelockerung erlaubt, aktuell nicht nötig vorgenommen. Keine Freigabe zur
  Lockerung von Frische-/Kollisions-/Geschwindigkeits-/nativenUR-Stopps.
- RF-Ellenbogenkonfiguration wie vom Nutzer gewünscht korrigiert. Tatsächliche
  hohe Anfahrt und offene Einfahrt in `continuation/` beide PASS. Vor Schließen
  aktuelle OAK-Fotos12:56:19/12:59:51 visuell geprüft: Backenpaare straddeln
  kurze Wände, Tischauflage. Keine neue Wrist-Zentriermetrologie behauptet.
- **Zeit:** seit letztem Home-Start12:42:12 bis beobachtetem Griffabschluss
  13:01:16 rund19min05s, einschließlich Softwareabbruch/Korrektur/Fortsetzung.
  Ab initialem Logger11:18:30 insgesamt1h42min46s inklusive Hostwechsel,
  Nutzerwartezeiten, Konfigurationskorrektur und Fehlversuchen; erste
  Dokumentlesung vor Logger ausgeschlossen. **Kein störungsfreier Zykluswert.**
  Lokale Zeitbasis/Einzelphasen: `setup/tasks/carton_cycle_n100_20261119/`
  `timing.json` und `completion.json`; keine Host-Monotonzeiten subtrahiert.
- Beobachteter Blocker war nach Ruhekorrektur wiederholt eine Hardware-/Manager-
  RPC-Antwort >0,3s beim ROS-Schnittstellenwechsel. Keine Frischegrenze gelockert.
  Bekannte Cancel-Clients jetzt vor Timern, Arm-/Read-Schnittstellen für beide
  seriellen Arme vor Programmstart, bis Serienende erhalten; Gripper-Read-RPCs
  persistent mit jeweils neuen Geräteanfragen. Hohe Anfahrt und Einfahrt danach
  bestanden. Zeitlicher Zusammenhang belegt, keine allgemeine Middleware-
  Ursachen- oder Dauerstabilitätsgarantie. Gezielte Offlineprüfungen bestanden.
- Erster Schlussversuch vor Fingerziel wegen STOPPED-Programm verweigert.
  Nach gezielter Korrektur **expliziter** regulärer Start erst nach vollständigem
  Graphaufbau unter allen4 offenen stationären Holds; danach nurRF/RRgeschlossen.
  Neuer Opt-in `carton_gripper_phase.py close --start-ros-programs` ist nur bei
  `--execute --visual-confirmed` zulässig. Kein Sicherheitsstopp quittiert,
  keine automatische Wiederanlaufserie. Frühere Fehlerdateien bleiben erhalten.
