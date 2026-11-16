# Modulare Karton-Greifpipeline

- Status: **in Arbeit**, 2026-11-13, Hauptagent Greifpipeline.
- Auftrag: wiederverwendbare Skills/CLI/Reviews, zuerst Simulation mit beiden
  rechten URs, leerer Karton, physischer Kontakt, kurzer Hub und Absetzen.
- Nutzerentscheidung: Agent prüft und setzt im konkreten Auftrag selbst fort;
  keine zusätzlichen manuellen Freigaben je Phase. Hardware ist spätere Arbeit.
- Verbindlich: ab bestätigtem Griff starres Multirobotersystem; ausschließlich
  Objektpose/-twist vorgeben, feste Objekt→TCP-Transformationen. Keine unabhängig
  geplanten tragenden Arme. Prinzip/Kern aus match_cooperative_handling nutzen.
- Bereiche: neues uwa_cell_tasks, kontaktfähiges optionales Simulationsprofil,
  gemeinsamer geometrischer Kern im Cooperative-Repo, gezielte Integration und
  Tests/Anleitung. Bestehende Motion-/Tracking-Diffs erhalten.
- Gemeinsame Simulation: laufender Vierarmvergleich hat Vorrang; keine fremden
  Dienste stoppen/neustarten. Zunächst Offlinearbeit. Eigene Kontaktprüfungen
  getrennt benennen; Zellneustart erst nach tatsächlicher Nutzungsprüfung.
- Annahmen: starrer leerer Karton, 0,3kg, Reibwert0,6; ungemessen. Hub30mm,
  Halten2s, keine künstliche Objektbefestigung als Haltenachweis.
- Noch offen: vollständige Kontakt-/Hubprüfung und fünf volle Zellläufe.
  Nur tatsächlich ausgeführte Nachweise als bestanden dokumentieren.
- Implementiert/gebaut: uwa_cell_tasks, geometrischer Cooperative-Kern,
  Skill-/Review-/Plan-/Run-/Stop-CLI, Kontaktbackend und isolierter Zell-Launch.
 9Softwaretests PASS. Kontaktgeometrie STL mit Normalen, exakt konvex
  zusammengeführt122→41Teile ohne geschlossene Ausschnitte; Spawn-Pose explizit.
- Eigene Livewelt/Namespaces: uwa_grasp_lab, uwa_grasp_validation, private Uhr
  und TF. Keine gemeinsamen Dienste neu gestartet. Entwicklungslogs v1–v4
  erhalten. V12 trennt bildsensorfreie Kontaktphysik und eigenen statischen
  Snapshot-Renderer; Robotik/Objekt während Foto auditiert, Bild- und Physikuhr
  ausdrücklich getrennt, GroundTruth nur für Renderingdefinition/Auswertung.
- Bildlokalisierung PASS: OAK67Inlier/0,69px, Wristquellen korrektLOST; keine
  Genauigkeitsfreigabe. Strategie-/Plan-Review in run11 passiert: geprüfte
  51s-Anfahrt,30s-Einfahrt und gemeinsamer11,5s-Hubzeuge. ErsteAnfahrt nach
  ca3mrad wegen passiverFingerspeed0,208rad/s gestoppt, beideHolds bestätigt.
- Korrektur V13: Drehmoment-PD pro1ms-Physikschritt statt gehaltenem ROS-
  Schreibzyklus; Sollwertslew auch im Physikschritt. Grenzen bleiben unverändert.
  Eigener neuer Gazebo-Servoplugin gebaut; noch kein erfolgreicher Kontaktgriff.
  Run12 stoppte erneut nachca1,2s auf passivemFingergelenk0,0673rad/s;
  beideHolds bestätigt, Verbesserung ist noch kein bestandener Anfahrtest.
- V14 ergänzt ausschließlich im optionalen Kontaktprofil native viskose
  Fingergelenkdämpfung0,02Nm·s/rad als ungemessene Modellannahme. Speed-/Stopp-
  grenzen unverändert. Run13 erhielt beim Start nur Teilreset; beideHolds
  bestätigt. Runner wartet jetzt zusammenhängendes0,5s-Stillstandsfenster.
  Run14 hat Bild-/Strategie- und geometrischePlanprüfung passiert, danach erneut
  SpeedstoppRF0,06864rad/s amTreiber; Recorder maß kurz max0,1048rad/s ampassiven
  Tip bei0,52mrad Auslenkung. BeideHolds bestätigt, kein Griff.
- V15: separater Physikschritt-Positionssteller für12rechteArmgelenke;
  gemesseneaktuellePosition statt zwischengespeichertemROS-Read, v≤0,05rad/s,
  a≤0,5rad/s². Ein gemeinsamer12Joint-Controller bleibt. Keine unabhängige
  Neuplanung, nativeGazebo-Geschwindigkeitsaktuation bleibt idealisiert.
  Paketneugebaut,9TestsPASS; Kontakt-/Hubnachweis weiterhin offen.
- Run15/V15 durchAgentgestoppt: Sollverlauf lief, tatsächlicheArme bewegten
  sich nicht; beideHolds bestätigt. Ursache: Gazebo entferntJointVelocityCmd
  proPhysikschritt, ursprünglicherECS-Filter verlor dadurch denSteller.
  V17 erzeugtBefehl proSchrittneu; explizites READY für12Gelenke beobachtet.
  Anfahraktionen haben nun5mradPfadtoleranz gegen nichtreagierendeAktuatoren.
  Run16 prüfte dieKorrektur: tatsächlicheFahrt vorhanden, erneuterFinger-
  Speedstopp0,06132rad/s, beideHolds bestätigt. V16 war nurVorbereitung.
- V18: gemeinsamerJTC liefert zusätzlichGeschwindigkeitsvorsteuerung;
  Physiksteller extrapoliert denselbenSollzustand zwischenROS-Zyklen, statt
  Positionsstufen nachzuregeln. Positions-Holds deaktivierenVorsteuerung beim
  Ressourcenwechsel. NativeSpeed-/Beschleunigungsgrenzen unverändert.
  Run17 bestand volle51sAnfahrt und30sEinfahrt, Bildausrichtung0,118mm/
  0,000727rad. Schließen nach44sEchtzeit aufAktionsfrist gestoppt: q0,3362,
  nochkeinPadkontakt, Tischsupport, keineGuardfaults, beideHolds bestätigt.
  DeadlinejetztwieArmfahrten aufbis5facheSimdauer+10s begrenzt, Frische- und
  Sicherheitswatchdogs unverändert. Run18 öffnetunbelasteteGreifer explizit
  vorPlanung; eigenerGuardgezieltneugeladenfürFreigabequittierung/DONE-Status.
  NamespaceübergreifendeRunner-Lease verhindert paralleleRezepte
  aufdenselbenControllern;10SoftwaretestsPASS. KeineGriffbehauptung.
- Wiederverwendbarer Repository-Skill uwa-manipulate angelegt und mit
  skill-creator quick_validate geprüft. Keine Hardwareaktion.

- Spätere Kontaktentwicklung: Run18/21 erreichten alle vier Padkontakte,
  wurden aber vor Hub auf passiver Speed gestoppt (Run21 RR0,54689rad/s).
  Feinschluss allein genügte nicht. V22 nutzt einen Motor jeGreifer und
  elastische Gear-Kopplungen mit korrekten Gegenmomenten; nativer Test für
  virtuelleArbeitsbalance und dissipativeDämpfung bestanden. Motor10Nm/rad,
  Kopplung3Nm/rad sind ungemessene Modellannahmen. 14PythonTests plus nativer
  Transmissionstest, alle4colcon-Suites PASS. EigeneV22-Kontaktszene startet
  deklariert an bereitsgeprüfterVorposition (development-fixture.json), keine
  Rücksetzung währendGreifen. Run22 bislang Einfahrt/Schließen ohneStopp.
- Zeitpfad seitV20 nativeprivate100Hz-Uhr; V21 JointState-Ausgabe auf100Hz
  statt doppelter1kHz-Werte reduziert. GanzeAnfahrt Run21 danach PASS;
  12sMessung420Joint-Nachrichten, max47,3ms Quellenfortschrittsabstand.
  Frischegrenze150ms erhalten. Kein vollständigerKontakt-/Hubnachweis bisher.


## Entwicklungsbefunde bis V40, 2026-11-13

- Entwicklungsbefunde bleiben unter `setup/tasks/carton_grasp_run*/` und
  `setup/logs/uwa-tasks-*`: Run11/12/14 stoppten Anfahrten auf passiven Fingern;
  Run15 erkannte fehlende Aktuation (verbrauchtes Gazebo-Geschwindigkeitskommando).
  V18 behob Anfahrspitzen durch Vorsteuerung. Run17 bestand ganze Anfahrt und
  Einfahrt; Schließfrist war für RTF≈0,37 zu kurz. Aktionsfrist jetzt wie bei
  Armfahrten bis 5×Simdauer+10 s; Frische-/Stoppfristen unverändert.
- Run18: Anfahrt, Einfahrt und tatsächlicher beidseitiger Kontakt an beiden
  Greifern erreicht. Speedstopp vor Lastaufnahme: erster Wächterwert
  0,08994 rad/s, aufgezeichneter passiver Spitzenwert 0,64764 rad/s. Karton
  unterstützt, beide Holds bestätigt. Dies begründet den Feinschluss; kein Hub.
  Run19 stoppte vor Kontakt auf Quellzeitstillstand 0,1747 s; beide Holds bestätigt.
- V20 ergänzt getrennte native private ROS-Uhr mit 100 Hz Simulationszeit,
  statt Python-Uhrpublikation mit Kontaktarbeit. Aktuelle eigene Welt:
  `setup/tasks/carton_contact_20261113_v21/` wird vorbereitet. V20 erste
  12-s-Quellenmessung max.61,5ms Fortsetzungsabstand, später aber fehlende
  echte Gelenknachrichten über0,1735s: Anfahrt vorEnde gestoppt, beideHolds.
  V21 senkt JointState-Publikation auf100Hz statt doppelter Werte jePhysikschritt;
  Steller/Frischegrenze bleiben erhalten. Offline-Auswertungstool
  `tools/validate_manipulation.py` klassifiziert Run18 korrekt als INCOMPLETE/FAIL.
- Run21: kompletteAnfahrt/Einfahrt undFeinschluss bisKontakt; keineZeitstörung,
  aber Kontakt-Speedstopp hintenrechts0,54689rad/s. BeideHolds/Tischsupport.
  V22 ersetzt unabhängigeFinger-PDs durch einenMotor jeGreifer und elastische
  Kopplungen mitGegenmomenten (Motor10Nm/rad, Kopplung3Nm/rad, beideungemessen).
  NativerTest fürReaktionsbalance/Dämpfungsdissipation PASS;14PythonTestsPASS.
  Kontakt-Testszenev22 startet explizit abbereitsgeprüfterVorposition, dokumentiert
  in development-fixture.json; keineRücksetzungwährendGreifen, keinHubnachweis.
- Run22: neueKopplung reduzierte Kontaktspitze auf0,05546rad/s passiv;
  beideMotoren bliebenunter0,01988rad/s. TrotzdemkonsequenterSpeedstopp,
  beideHolds/Tischsupport. V23 prüft dieselbeVorpositions-Testszene mit
  höhererpassiverDämpfung0,04statt0,02Nm·s/rad; Geschwindigkeitsgrenzen erhalten.
- Run23/24 scheiterten vorKontakt an Überwachungs-/Quellenpausen, beideHolds
  bestätigt. Direkte nativeZeitprobe: Empfangslücken≈100ms bei zugehöriger
  Gazebo-Echtzeitdifferenz≈2,5–3ms, Transportanteil plausibel; keine Ursache
  durch bloßes Aufweiten vonWatchdogs verdeckt. V24 publiziert Uhr, echte
  Objektpose und Kontaktkomponenten direkt aus Physik-ECM nachROS; keine
  Gazebo-Transport-/Python-Bridge mehr imLaufzeitpfad. 12sSmokeCheck max36,2ms
  Quellabstand überalleKanäle, Objektz≈0,899999m, Tischsupport bestätigt.
  14PythonTests+nativerTransmissionstest/alle4CTest-Suites PASS. Run25 prüft
  unveränderteKopplung/Dämpfung mit neuemTelemetriepfad; vollständigerHub offen.
- Run25: Telemetrie/Einfahrt/erstePadkontakte stabil, bei zweitemPadkontakt
  hintenrechts passiv0,32622rad/s; beideHolds, Tischsupport. V26 verwendet
  analytische konservative Gehäuse-/Padboxen aus geclipptenOriginalmeshes;
  innereGreifebene erhalten, eigene festePadlinks. NurPad/Karton erlaubt,
  Gehäuse/Karton bleibtgeprüft. Vorhandene interneViergelenk-Hingefreistellung
  auf festesPadteil vererbt, keineUmgebungs-/Interarmfreistellung hinzugefügt.
  14Tests inkl.Meshüberdeckung/innererPlane/FCL-Startcheck PASS, 4SDF-Pads
  nachKonvertierung erhalten, alle4CTest-Suites PASS. V25 war nur Geometrie-
  Vorbereitung, nicht gestartet. Run26 erreichte erstmals stabilen
  Vierpadkontakt ohne Speedstopp; Kontaktbestätigung gespeichert. Erst bei
  nachfolgender Snapshot-Aufnahme STATE STALE nach166,7ms, beideHolds
  bestätigt und Kartonweiter unterstützt. Noch keineGreifgruppe/Lastaufnahme.
  V27 begrenzt eigenenRenderer auf letztesCPU-Viertel, Nice10 und2Worker;
  alleWatchdoggrenzen unverändert, Wirkung imKontaktlauf nochzuprüfen.
- Run27: Vierpadkontakt erneut erreicht, aber beim Vorspannen hintenrechts
  Speedstopp0,51850rad/s amAntriebsgelenk, Holds/Tischsupport bestätigt.
  Kontaktprotokoll zeigt entgegengesetzteNormale anPrismennähten desselbenPads.
  V28 zerlegt jedeWand exakt in durchgehendeuntereRechteckfläche und obere
  Konturprismen, untereFlächen als nativeBoxen. GleicheWandflächenbilanz und
  je120701Rasterpunkte ohneAbweichung; interneLöcher würden abgelehnt.
  40Kontaktteile/7Boxen, originaleAusschnitte erhalten. Greifpunkte7mm tiefer,
  komplettePads unterobererKontur; FCL/Hubvorprüfung bestanden, Lauf28 offen.
  15PythonTestsPASS inkl.Kontursprung-/Lochabwehrtest. Renderer-CPU-Maßnahme
  weiterhin nicht amgeschlossenenGriff nachgewiesen (Run27 stoppte vorher).
- Run28 erreichteVierpadkontakt, erneutSpeedstopp0,33128rad/s amhinteren
  Antriebsgelenk; Holds/Tischsupport. FKderganzenPadbox zeigte obereKante noch
  überWand-Basisfläche: pauschalerReferenzpunkt warfür47mmhohePads unzureichend.
  V29 berechnet höchstePadkante aus gesamterBox undFinger-FKbei0,76–0,8rad,
  legt sie3mm unterdurchgehendeWandfläche. DieseBedingung wirdjeKandidat
  gespeichert undgetestet; 15PythonTestsPASS. NochkeinKontaktlaufnachweisV29.
- Run29: erstmals stabilerbestätigterVierpadgriff plusfrischeBildaufnahme,
  starreGreifgruppegebildet undObjekthub begonnen. VorLastaufnahmeRelativdrift
  ≈2,06/2,01mm, Verbund-Schlupfstopp, beideHolds/Tischsupport. PassiveSpitze
  drehteunterLast≈0,020rad relativzurBaseline: bisherigeGear-Steifigkeit3Nm/rad
  nachgiebig. V30 nutzt explizitkonfigurierte10Nm/rad (Motorweiter10Nm/rad,
  Momentcap0,35Nm unverändert), alsungemesseneAnnahmegekennzeichnet. Schlupf-
  fehler enthältjetztMember/gemesseneAbweichung/Grenze. ErsterV30-Lauf soll
  wieder ab den normalen Homezuständen starten, keinVorpositions-Fixture.
- Run30 abHome stopptebereitsvorFahrt: keinRRT-Weg. V31nurvorbereitet,
  Anfahrabstand60→80mmwegentieferemGriff. ZusätzlichNative-RRT-Inkonsistenz
  gefunden: vierPad-/Innengelenk-Ausnahmen nurimPython-ACM, nichtimSRDFdes
  separatenRRT-Prozesses. V32 persistiertdieselbenvierinternenNachbarschaften
  imSRDF. NativerProzesstest bestätigtjetzt denselben gültigenStartwiePython;
  15TestsPASS. KeinezusätzlichenUmgebungs-/Interarmfreistellungen. V32-Lauf
  abHome nochzuprüfen, V31wurde nichtgestartet.
- Run32: ganzeHome-Anfahrt50,31s/Einfahrt30s undstabilerGriffmitfrischemBild
  bestanden, Objektgruppegebildet. ErstephysischeBewegung≈0,12mm, dann
  transienterTASK-FULL-SCENE-COLLISION-Stopp; beideHolds/Tischsupport. Spätere
  Zustände und20Hz-Replay kollisionsfrei, daherkeineUrsache behaupten.
  V33 speichertdenexaktgeprüftenKollisionszustand undverboseMoveIt-Paar
  erstnachPublikationdesStopps; eigenesVorpositions-FixtureausRun32-Plan,
  keinePoseänderungwährendManipulation. VollständigerHubweiteroffen.
- V33-Startdiagnose erfassteKartonkollisionmitbeidenTischen, Objektposefrisch,
  KontaktdatennochNone; Run33danachStartzeitüberschreitung, Holdsbestätigt.
  V34 wartetvorFCLaufbeidefrischeKanäle. Karton-/Tisch-Kontakterlaubnisnutzt
  jetztwiePlanung ausschließlichgeometrischen±1mmBodenkorridor, unabhängig
  vomasynchronenSupportflag; tieferePenetrationauchbeiSupportTrueabgelehnt.
  TatsächlicherSupportfürLastaufnahme/FreigabebleibtseparaterKontaktbeleg.
  RegressionstestprüftKorridorgrenzen undnurObjekt-/Tischpaar; 16PythonTestsPASS.
  ExakteFCL-DiagnosewirdproReset archiviert, nichtdurchStartupfehlerverbraucht.
- Run34: stabilerGriff/Gruppe, keinFCL-AlarmbeimLastübergang; stattdessen
  passiverSpeedstopp hintenrechts0,06370rad/s, beideHolds/Tischsupport. V35
  reduziertObjektspeed5→2mm/s und erhöht expliziteungemessene Fingerdämpfung
  0,04→0,08Nm·s/rad, Grenzwerte0,05rad/s undRelativfehler2mm bleiben erhalten.
  16PythonTestsPASS, Kontakt-/HubnachweisfürV35noch offen.
- Run35: langsamerHub/mehrDämpfung reduzierte passiveSpitzeauf0,05379rad/s,
  dennochSpeedstoppundbeideHolds/Tischsupport. V36 testetstattzusätzlicher
  elastischerKopplungen dievorhandenenURDF-Getriebebeziehungen alsnative
  Gazebo/DART-MimicConstraints, einMotorjeGreifermit0,35NmCap. Kartonbleibtfrei,
  keinAnheften/Teletransport; idealisierteparalleleTransmission, keineadaptive
  Mechanikvalidierung. NurphysischesSpawn-URDFenthältConstraints; Planungs-/TF-
  Modellbehältunabhängige gemesseneFingerzustände. ros2_controlpassivesstate-only,
  keinesynthetischenMimic-Positionsresets. NativeKonvertierunggeprüft und16Tests
  PASS; realerKontakt-/HubnachweisV36nochzuprüfen. ElastischerModusbleibtals
  ausdrücklichunqualifizierterVergleich reproduzierbar.
- V36-DART meldete fehlendeMimicConstraint-Unterstützung; Run36vomAgenten
  schonimStrategiereviewvorGriffgestoppt, beideHoldsbestätigt. V37 wähltfür
  nativeGearsversioniertBulletFeatherstone(9.5.2) nurineigenerWelt. Inkompatible
  nativeGear/DART-KonfigurationwirdbereitsvorStartabgelehnt. Enginebinary,
  world.sdfundcarton.sdfjetztzusätzlichSHA-gebunden; 17PythonTestsPASS.
  NativeKopplungundKontaktphysikaufdieserEngineweiterzuqualifizieren.
- V37nochvorRezeptabgebrochen: BulletFeatherstone lehntgetrennteTischbäume
  unterreserviertemworldab unddeaktivierte rechteÄste. V38 ergänzt ausschließ-
  lichimphysischenSpawnmodelleinenfesten gemeinsamenAnker und verbindet
  Kamerakörper/Stativfest. Geometrie/alleWerkzeug-Weltposen unverändert, FK-
  RegressionPASS; 17TestsPASS. Fehlende/disabledModelle nichtalsTestlaufzählen.
- V38 startetmitvollständigemBullet-Modell. Unbelasteter3sKopplungsnachweis:
  145Messungen,max7,08e-8radRelationsfehler,max3,80e-7rad/s passiveBewegung.
  Run38jedochbeimBeobachtenabgebrochen: linkerunbeteiligterGreiferbewegte
  sich(stockKinematiktreiber+zusätzlichenativeMimicConstraint), LF-Speed0,2195rad/s.
  RechteHoldsbestätigt, keinGriff. V39 entferntnurphysischelinkeMimicConstraints;
  derenbisherigeStock-TreibermimicsimBasisURDFbleiben. NativeConstraintsnurfür
  rechteGreifer. 17TestsPASS, Startup-/KontaktprüfungV39offen.
- V39: linkeunbeteiligteGelenke3sruhig(max5,95e-6rad/s,2,04e-10radSpan),
  Bild-/Plan-/Alignment/Einfahrtbestanden. FreierSchlussvordemKarton numerisch
  instabil, passiv11,33rad/s→konsequenterSpeedstopp, keinePadkontakte. Native
  RelationsfehlerwuchsenbeimAusschlag; V40 reduziertvonDARTübernommeneexplizite
  Fingerdämpfung0,08→0,001Nm·s/rad. KeineGrenzegeändert. V40nochzuprüfen.
  **Noch kein erfolgreicher vollständiger Kartongriff/Hub nachgewiesen.**
  Offen: vollständiger Kontakt-/Hubnachweis, fünf volle Läufe, Masse-/Reibungs-
  variationen und Laufzeit-Fehlerinjektionen. Kein Stand als freigegeben ausgeben.


### Native Vergleichsvariante V39/40 und Rückkehr V41

- V39/40: Bullet-native Kopplung in Ruhe genau, aber freier Schluss ohne
  Kartonkontakt instabil. V40 trotz Dämpfung0,001 passiv13,23rad/s; Stoppholds
  nicht vollständig bestätigt. Eigene instabile Welt beendet, niemals als
  Kontakt-/Haltekraftnachweis zählen. Logs/Primärdiagnosen erhalten.
- V41: DART, elastische Gear-Steifigkeit100 statt10Nm/rad, Dämpfung0,08,
  Motor10Nm/rad und0,35NmCap, Objekt2mm/s. Steifigkeit reduziert Nachgiebigkeit,
  ohne Grenzwerte zu lockern. Noch zu prüfen. 17PythonTestsPASS.

### 2026-11-13: Latest-state transport and executor overhead

V44 observation stress passed12/12; full recipes47 and48 independently passed
(29.654/29.616mm). Recipe49 failed during initial unloaded opening on the
runner reception check, while independent guard remained CLEAR; stop RPC
timeout was recorded, not claimed confirmed. Own world was ended explicitly.
V50 uses the workspace MotionNode for runner/guard/snapshot camera and binds
that helper source. Health diagnostics distinguish joint/guard/supervisor ages
and record all reception ages plus executor liveness. No watchdog threshold
changed. Initial V50 stress failed before capture: partial stationary reset
accepted only left arms, with343ms startup source gap. Subsequent read-only
measurement found both right arms and all physical finger joints stationary
(q spans below1.1e-17rad); a fresh observation-only test is in progress.

### 2026-11-13: Receiver discovery and photo-age qualification

V50 stress12/12 PASS; full runs50/53 rejected before arm motion on
157.6/196.2ms guard reception gaps. Explicit own CPU affinities retain all
watchdog limits. Idle diagnostic guard120ticks:14.67ms max/13.09ms p95,
30.41ms max joint gap. Run51/52/54 image-age rejections5.049/5.299/5.029s
preserved; all confirmed both holds. Run54 approach completed without guard
fault but its intended trace had exited before creating a ROS node: constructor
RunStore did not persist CREATED. No independent trace claim for54.
`trace_manipulation --prepare` now creates a fresh persisted CREATED run and
starts recorder before runner. DDS discovery during armed operation remains a
hypothesis, not proven causation. V62–64 explicit RTF0.6/1ms profile binds
nominal/low/high configs. Run55 independent trace is live before reset and
three agent reviews passed. Photo pregrasp delta0.532mm/0.00596rad; all actual
images reviewed, invalid wrist localization excluded. V65–67 fault fixtures
preserve initial pregrasp provenance; none is a Home-start claim.

### Consolidated evidence before damping comparison

## Modulare Karton-Greifpipeline: Kontaktqualifikation offen, 2026-11-13

- Auftrag: agentbedienbare Skills mit Voraussetzungen, Ergebnisprüfungen und
  begrenzten Wiederholungen. Erste Simulation: beide rechten URs greifen den
  leeren Karton, heben 30 mm, halten 2 s, setzen ab und öffnen. Agent prüft
  Strategie, Plan und Vorpositionsbilder selbst. Kein Hardwareauftrag.
- Implementiert: `uwa_cell_tasks`, 11 Skill-Verträge, CLI/Review/HTML-Vorschau,
  exklusive Ressourcenlease, SHA-gebundene Modelle/Code/Binärdateien/Physik,
  bildbasierte Beobachtung, unabhängiger FCL-/Kugel-/Kontakt-/Schlupfwächter
  und bestehender Ressourcen-Supervisor. Einstieg:
  `.agents/skills/uwa-manipulate/SKILL.md`, `docs/manipulation_pipeline.md`.
- Ab bestätigtem Griff nur ein Objektframe, feste Objekt→TCP-Transformationen,
  ein 12-Gelenk-Controller und eine gemeinsame Zeitparametrierung. Geometrischer
  Kern in `match_cooperative_handling.rigid_object`. Keine unabhängige Planung
  tragender Arme, kein Nachführen der Offsets gegen Schlupf. Andere Arme bleiben
  gemessene Hindernisse. Stopp erhält den Griff, keine automatische Öffnung,
  Rückfahrt oder Wiederaufnahme. Unterstützte stationäre Freigabe mit Guard-Ack.
- Eigene Welt `uwa_grasp_lab`, Namespace `/uwa_grasp_validation`, private Uhr/TF,
  Domain64/LOCALHOST. Gemeinsame Zellsimulation/Vierarmvergleich erhalten.
  Uhr, Objektpose und Kontakte direkt aus Physik-ECM; JointStates100Hz.
  Bildsensorfreie Physik; separater statischer Snapshot-Renderer mit auditierten
  Zuständen, eigenem Zeitbereich und CPU-Hintergrundlimit. Tracking bildbasiert,
  ohne Ground-Truth-Prior. OAK bisher VALID, untexturierte Wrist-Sichten LOST.
- Kontaktgeometrie: 40 dünne konvexe Teile/7 native Boxen, offener Karton und
  obere Ausschnitte erhalten. Wandflächenbilanz und je120701 Rasterpunkte ohne
  Änderung zur ursprünglichen Zerlegung. Durchgehende untere Wandflächen;
  ganze nominale Padbox aus Finger-FK mit3mm Reserve darunter. Nur Pad/Karton
  freigegeben; Gehäuse geprüft. Vier bestehende interne Gelenknachbarschaften
  für feste Pads vererbt, identisch im Python-ACM und nativen RRT-SRDF getestet.
- Aktuelles Testmodell V42: DART9.5.2, energieausgeglichene elastische rechte
  Getriebekopplungen100Nm/rad, ein Motor je Greifer mit0,35Nm Cap und10Nm/rad.
  Fester physischer Anker erhält alle Werkzeug-Weltposen; Karton frei, kein
  Anheften/Teletransport. Masse0,3kg, Reibung0,6, Dicke2,5mm, Dämpfung0,08Nm·s/rad
  und Steifigkeiten sind ungemessene Annahmen. Objektgeschwindigkeit2mm/s;
  Arm-/Fingergrenze0,05rad/s und Relativgrenze2mm/1° unverändert.
  Optionale native Bullet-Variante besteht unbelastete Ruhemessung, wird aber
  beim freien Schließen numerisch instabil und ist ausdrücklich unqualifiziert.
- Software: 17 Python-Tests PASS, einschließlich nativer RRT-Prozessparität,
  Rotations-/Hebelarmregel, gemeinsamem Grenzfaktor, unveränderlichen Offsets,
  Kontakt-/Verbundstopp, Ressourcenlease, Frische/Rendering, Geometrie und
  Engine-Kompatibilität. Nativer Reaktions-/Dämpfungstest des elastischen
  Vergleichsmodells ebenfalls PASS; letzter vollständiger colcon-Lauf4Suites.
- Erster vollständiger mechanischer Nachweis: Run42/V42 **DONE + unabhängige
  Auswertung PASS**, `setup/tasks/carton_grasp_run42/validation-report.json`.
  Tatsächlicher Hub29,661mm, freie2s-Haltephase, Absetzen, Öffnen, aufgelöste
  Gruppe und bestätigte rechte Holds. 1834 geladene Auswertungssamples;
  maximaler Relativfehler0,2383mm/0,001722rad, gemessene Spitzengeschwindigkeit
  über alle rechten Gelenke/Phasen0,04307rad/s. Alle vier Pads unter Last
  erhalten, Offsets unverändert. Kein Anheften. Dies ist ein Vorpositions-
  Fixture aus Run32, kein aktueller Home-Nachweis und keine Hardwarefreigabe.
- Aktueller Softwarecheck: 17PythonTests plus nativer Reaktions-/Dämpfungstest,
  alle4colcon-Testsuites PASS. Logs `setup/logs/uwa-tasks-colcon-test.log`.
- Aktueller vollständiger Home-Nachweis: Run43/V43 **DONE + Auswertung PASS**,
  Hub29,664mm, maxRelativfehler0,2365mm/0,001709rad, maxgemesseneGeschwindigkeit
  0,050000000021rad/s (numerische1e-8-Toleranz),1818 geladene Samples. Vollständige Anfahrt49,31s/Einfahrt30s. Gleiche Code-/Profil-
  version wieRun42. Report `setup/tasks/carton_grasp_run43/validation-report.json`.
- Eigene V43-Welt bleibt für Wiederholungen aktiv; Run44 startete nach bestätigter
  Freigabe aus dem gemessenen Endzustand, ohne Objekt-/Szenenreset. Auswertung
  prüft jetzt zusätzlich gemessene Geschwindigkeitsgrenze und fehlende Guard-
  faults während Bewegung; Gegencheck mit ausschließlich synthetischem0,051rad/s
  verwirft DONE korrekt. Originaldaten unverändert. Log
  `setup/logs/uwa-tasks-validator-regression.log`.
- Agenten-Kurzprüfung: `tools/inspect_manipulation_review.py RUN` prüft Hashes
  und gibt pending-Status, Bilder, Kandidaten, Poseabweichung/Bahnkennwerte aus.
  Keine automatische Zustimmung. Gegen reale pending/nicht-pending Pakete
  geprüft; Repo-Skill quick_validate erneut PASS.
- Run44/V43 ebenfalls **DONE + Auswertung PASS**: Hub29,622mm, dritte
  vollständige Kontaktfolge; gemessener Endzustand ohne Szenenreset.
- Run45 stoppte bereits beim Strategiereview vor Armfahrt/Kontakt auf
  STATE STALE nach176,7ms und Scene-Telemetrieverlust; beide Holds bestätigt,
  Objekt unterstützt und offen. Kein Erfolg/kein Neustart dieses Laufs.
  Run46 ist ein neuer Versuch nach erneuter Frische-/Stillstandsprüfung.
  Watchdoggrenzen unverändert; gelegentliche Quellenpausen bleiben ein
  Abbruchgrund und werden in der Erfolgsquote mitgeführt.
- Run46 wieder vor Armfahrt im Strategiereview auf Daten-/Guardverlust
  gestoppt, beide Holds bestätigt. Deshalb V44-Transportänderung: native
  Objekt-/Kontaktstreams KeepLast1/BestEffort, Runtime/Guard/Kamera/Trace mit
  Sensor-QoS. Keine erneute Datierung alter Posen und keine Frischegrenze
  geändert. Aktuelle Codeversion benötigt eigene Nachweise; Run42–44 bleiben
  historische mechanische PASS-Belege des gleichen Greifprofils.
- V44 aus Home aktiv für zwölf komplette Beobachtungen ohne Arm-/Greiferziele;
  separater `tools/stress_manipulation_observation.py`, exklusive Lease und
  unabhängige Guard-/Quellfortschrittsmessung. **Stresstest PASS**: zwölf VALID-Beobachtungen/85,95s, keine Guardfaults,
  keine Arm-/Greifertrajektorien, beide Holds bestätigt. Maximaler gemessener
  Quellenfortschrittsabstand124,5ms über Clock/Joints/Object/Contacts, Grenze
  bleibt150ms. Report `setup/tasks/camera_transport_stress_v44/report.json`.
  Run47 prüft jetzt wieder den vollständigen Ablauf ab Home auf dieser Version.
- Run47/V44 aktueller vollständiger Home-Lauf **DONE + unabhängige Auswertung
  PASS**: Hub29,654mm, maxRelativfehler0,2435mm/0,001764rad, 1822 geladene
  Samples, maximale gemessene Geschwindigkeit0,050000000021rad/s (numerische
  Toleranz1e-8). Keine Guardfaults während Bewegung. Run48 wiederholt aus
  freigegebenem gemessenem Endzustand ohne Reset.
- Run48/V44 ebenfalls **DONE + Auswertung PASS**, Hub29,616mm und max.
  Relativfehler0,2637mm/0,001917rad. Run49 scheiterte schon beim anfänglichen
  unbeladenen Öffnen an eigener Empfangsfrische; unabhängiger Guard CLEAR,
  Stop-RPC ohne Bestätigung. Kein Kontakt-/Bewegungserfolg. V44-Welt danach
  gezielt beendet; gespeicherte Daten bleiben erhalten.
- V50 übernimmt `uwa_cell_motion.node.MotionNode` für Runner/Guard/Kamera:
  explizit deaktivierte unbenutzte QoS-Warncallbacks vermeiden deren bekannten
  Waitset-Aufwand. Transport- und Frischegrenzen unverändert. Eigene Diagnose
  benennt jetzt den veralteten Kanal und speichert Empfangsalter/Threadstatus.
  Hilfsknotenquelle zusätzlich SHA-gebunden. Build und17PythonTests PASS;
  zwölf Beobachtungen und erneute Kontaktqualifikation auf V50 laufen noch.
- V50-Stress erneut12/12 PASS (84,85s, maximal131,44ms, beide Holds).
  Run50 danach vor Armfahrt durch157,57ms STATE STALE gestoppt, beide Holds.
  Eigene Prozessaffinität trennt jetzt Physik0–3, Guard4, Supervisor5; Kamera
  bleibt unverändert. Run51/52 zeigen ohne Guardfault Bildalter5,05/5,30s
  und werden bei unveränderter5s-Grenze korrekt verworfen, beide Holds bestätigt.
- V56–58: expliziter Simulations-Echtzeitfaktor0,7 bei unveränderter1ms-Physik,
  monotone Watchdogs unverändert. Beschleunigte Kontaktqualifikation wird
  abgewiesen, neuer Grenztest (jetzt18PythonTests PASS). Reproduzierbare eigene
  CPU-Zuteilung: `tools/configure_manipulation_cpu.py --scene SCENE`, exakte
  Launch-Nachfahren/Scene-SHA geprüft, kein fremder Prozess verändert und keine
  CPU-Reservierung behauptet. Runner CPU6–11. Noch keine Erfolgsbehauptung auf
  diesem Profil; V56 nominal/V57 leicht/V58 schwer vorbereitet.
- Run53/V56 ebenfalls vor Armfahrt STATE STALE196ms, beide Holds. Separater
  diagnostischer Guard im unbeladenen Stillstand:120Ticks, max14,67ms/p95
  13,09ms, maximaler eigener Joint-Empfangsabstand30,41ms. Keine generelle
  Geometrieüberlastung bewiesen. Neue Hypothese: Start des ROS-Auswertungs-
  knotens während bereits armiertem Ablauf/DDS-Discovery. Run54 hat Trace
  deshalb schon im CREATED-Zustand vor Runner/Reset gestartet; Strategie-
  review ist erstmals auf V56 stabil passiert, Planung läuft. Ursache noch
  nicht als bewiesen ausgeben; keine Frischegrenze geändert.
- Run54 erreichte ohne Guardfault die Vorposition, scheiterte danach korrekt
  an Bildalter5,029s. Beide Holds bestätigt, kein Griff. Wichtige Korrektur:
  der vorgesehene Trace war tatsächlich vor ROS-Initialisierung abgebrochen,
  da `RunStore(...)` allein state.json nicht schreibt. Kein unabhängiger
  Trace-/Kontaktnachweis für54 behaupten. Neues `trace_manipulation --prepare`
  legt CREATED explizit in frischem Verzeichnis an und startet vor dem Runner.
- Aktuell V62/V63/V64 mit explizitem RTF0,6 (1ms-Physik unverändert), nominal/
  leicht/schwer. Run55 hat nachweislich aktiven Trace schon vor Runnerstart,
  Strategie/Plan/Vorpositionsprüfung bestanden und führt jetzt den Griff aus.
  Vorpositionsdelta0,532mm/0,00596rad, OAK66Inliers/0,588px, kein Guardfault.
  CPU-Profil wie oben. Fault-Fixtures V65–67 vorbereitet, noch nicht gefahren.
- Varianten vorbereitet, noch nicht gefahren: V45 Masse0,2kg/Reibung0,4 und
  V46 Masse0,4kg/Reibung0,8; unveränderte sonstige Parameter. Konfigurationen
  `setup/tasks/manipulation_qualification_20261113/variants/`.
- Noch offen: Wiederholungen
  bis fünf vollständige Läufe, Masse-/Reibungsvarianten und Laufzeit-
  Fehlerinjektionen. Erfolg von Run42 nicht auf andere Bedingungen übertragen.
  Rein lesende Auswertung: `tools/trace_manipulation.py`,
  `tools/validate_manipulation.py`. Historische Fehlschläge und inkompatible
  native Bullet-Variante bleiben unqualifiziert; Entwicklungshistorie:
  `work/carton-grasp-pipeline.md`, `setup/tasks/carton_grasp_run*/` und
  `setup/logs/uwa-tasks-*`. Primärfehler vor Stoppeffekten gesichert;
  FCL-Diagnose mit exaktem Zustand und MoveIt-Paar pro Reset.


### Evidence before explicit COM lift reference,2026-11-14

## Modulare Karton-Greifpipeline: Qualifikation läuft, 2026-11-13

- Nutzerauftrag: wiederverwendbare agentbedienbare Skills; zwei rechte URs
  greifen leeren Karton, heben30mm, halten2s, setzen ab und öffnen. Strategie,
  Plan und Vorposition prüft Agent selbst. Ausschließlich Simulation.
- Implementiert: `uwa_cell_tasks`,11Skill-Verträge, CLI/Review/HTML-Vorschau,
  exklusive Ressourcenlease, SHA-gebundene Szenen/Quellen/Binärdateien/Physik,
  bildbasierte Beobachtung, unabhängiger FCL-/Kugel-/Kontakt-/Schlupfwächter
  und Ressourcen-Supervisor. Einstieg `.agents/skills/uwa-manipulate/SKILL.md`
  sowie `docs/manipulation_pipeline.md`.
- Ab tatsächlichem Griff ausschließlich ein Objektframe, eingefrorene Objekt→TCP-
  Transformationen, ein12Gelenkcontroller/gemeinsame Zeitparametrierung. Kern
  `match_cooperative_handling.rigid_object`. Andere Arme gemessene Hindernisse.
  Verbundstopp erhält Griff, keine automatische Öffnung/Rückfahrt/Wiederaufnahme.
  Unterstützte stationäre Freigabe mit Guard-Ack; kein künstliches Anheften.
- Eigene Welt `uwa_grasp_lab`/`/uwa_grasp_validation`, Domain64/LOCALHOST,
  private Uhr/TF. Hauptsimulation und Hardware unangetastet. Native100Hz-
  ECM-Uhr/Objekt-/Kontaktdaten,1ms-Physik. Bildsensorfreie Physik, separater
  Snapshot-Renderer. OAK-Pose bildbasiert ohne Wahrheit als Prior; Wrist LOST
  korrekt ausgeschlossen. Rendererzustände nur für Bildgenerierung/Audit.
- Greifstrategie: aufrechter starrer Karton/horizontale Unterstützung, bildbasierter
  Yaw mit gravitationsparallelen Greifern; geschätzte Neigung>2° abweisen.
  Gegenüberliegende untere Wandbereiche; ganze nominale Padbox3mm unter oberen
  Ausschnitten.40konvexe Teile/7native Boxen, Flächen-/Rasterbeleg unverändert;
  vier bestehende innere Gelenknachbarschaften im Python-ACM/nativen RRT identisch.
- Mechanische Annahmen: DART9.5.2, starre2,5mm-Wand, Masse0,3kg/Reibung0,6,
  energieausgeglichene elastische Getriebekopplung100Nm/rad, Motor10Nm/rad,
  Cap0,35Nm. Unvermessen: Masse/Reibung/Dämpfung/Steifigkeiten/Geometrie;
  idealisierte Armantriebe. Native Bullet-Vergleichsvariante instabil beim
  freien Schließen und ausdrücklich unqualifiziert. Kein Hardwareadapter.
- Historisch fünf vollständige **DONE + unabhängige PASS**: Run42/43/44/47/48;
  verschiedene frühere Transportstände, gleicher mechanischer0,08-Dämpfungs-
  stand. Hub29,62–29,66mm, maxRelativfehler0,264mm/0,001918rad.42 ist eine
  Vorpositions-Fixture;43/47 Home,44/48 Wiederholung ohne Szenenreset.
  Berichte `setup/tasks/carton_grasp_run*/validation-report.json` nicht als
  pauschale aktuelle Versionsqualifikation ausgeben. Fehlerläufe bleiben erhalten.
- Gegenwärtige Frischemaßnahmen: latest-state/BestEffort für native Objekt-/
  Kontaktdaten, MotionNode ohne unbenutzte QoS-Warncallbacks; Hilfsquelle gebunden.
  Monotone Grenzwerte unverändert. Empfangsalter/Kanal/Threadstatus in Stopdiagnose.
  Zwei12fach-Beobachtungs-Stresstests PASS, maxQuellenabstand131,44ms<150ms.
  Andere Startversuche mit Datenpausen150–343ms wurden korrekt abgebrochen.
- Rechnerprofil: expliziter RTF0,6 bei1ms-Schritt, keine Beschleunigung erlaubt.
  `tools/configure_manipulation_cpu.py --scene SCENE`: nur exakte Launch-
  Nachfahren, Physik CPU0–3/Guard4/Supervisor5, keine fremden Prozesse ändern.
  Runner CPU6–11; Kamera-Hintergrundprofil unverändert, keine CPU-Reservierung.
  `tools/trace_manipulation.py RUN --prepare` vor Runner starten und Existenz
  der Trace-Datei prüfen; Konstruktor-RunStore allein persistiert CREATED nicht.
  Neue DDS-Teilnehmer während armiertem Lauf korrelieren mit Frischefehlern,
  Ursache nicht endgültig bewiesen. Bildalter5s bleibt unverändert; RTF0,7
  lieferte knapp zu alte Vorpositionsbilder und wurde als Fehler erhalten.
- Run55/V62: vollständiger Home-Zyklus **DONE**, Holds bestätigt, Hub29,663mm,
  alle Pads unter Last/Offsets erhalten, maxRelativfehler0,2374mm/0,001714rad.
  Unabhängige Auswertung dennoch **FAIL**: passives rechtes Rear-Fingertipgelenk
  beim Abheben0,050147rad/s>0,05. Basisknoten erlaubt5% Toleranz; Task hatte noch keine eigene strikte Prüfung.
  Keine Grenzlockerung/kein PASS behaupten. Rohtrace vollständig vorhanden.
- Aktuell: Vergleich mit Dämpfung0,12Nm·s/rad (vorher0,08), übrige Mechanik
  unverändert. V68 nominale Vorpositions-Fixture, V69 leicht0,2kg/0,4 und
  V70 schwer0,4kg/0,8 ab Home; V71–73 Fault-Fixtures vorbereitet. Run56 aufV68
  läuft, noch kein Qualifikationsanspruch für diesen Dämpfungsstand.
- Run56 unbeladen per explizitem Agent-Abbruch beendet, beide Holds bestätigt.
  Task-Wächter prüft jetzt jeden empfangenen rechten Gelenkzustand gegen0,05
  plus1e-8 und verriegelt Peaks bis zum expliziten unbeladenen Reset. Kurze
  Peaks bleiben auch nach einem folgenden ruhigen Sample erhalten. Allgemeiner
  Basisknoten/Main-Benchmark unverändert. Neuer Regressionstest für den echten
  Run55-Gegenfall; Laufzeitprüfung19PythonTests/4colcon-Suites. Neuer Scene-/
  QuellstandV74, Run57 mit0,12-Dämpfung aus dokumentierter Vorpositions-Fixture.
- Run57/V74: vier Pads bestätigt, erster Objektbahnpunkt stimmt mit gemessenem
  Start auf1,1e-16rad überein (kein Sollwertsprung). Trotzdem beim beginnenden
  Abheben passives Rear-Fingertip0,058883rad/s; neuer strikter Peak-Wächter
  stoppt beide Arme, beide Holds bestätigt, alle Pads erhalten, Objekt noch
  unterstützt. Dämpfung0,12 ist deshalb **nicht qualifiziert**. Keine Öffnung/
  Wiederaufnahme, eigene virtuelle Episode danach explizit beendet.
- Aktuell Run58/V80: nächster isolierter Dämpfungsvergleich0,5Nm·s/rad,
  unveränderte übrige Mechanik/Bahn/Grenzen. Start-Fixture wie oben, Recorder
  vor Runner gestartet. Kein PASS vorwegnehmen. V75–79 mit0,12-Dämpfung sind
  nur vorbereitete, nicht gefahrene und nicht qualifizierte Varianten.
- Fortschritt2026-11-14: Run58 scheiterte unbeladen an ListControllers-RPC-
  Timeout trotz frischer Zustände; beide Holds. Nur diese lesende Abfrage wird
  jetzt einmal wiederholt. Mutationen werden nicht automatisch wiederholt.
  Stoppanforderungen werden an beide Mitglieder vor jedem Warten gesendet;
  Fehler einer Anfrage verhindert die andere nicht. Holdnachweis verlangt
  frische Messungen plus aktive unabhängige Controller (Regressionstests).
- Run59/V81 vor Einfahrt per Agent-Review abgebrochen: Open-Action meldete
  Erfolg, tatsächliche Finger aber bei0,798rad geschlossen. Dämpfung0,5 damit
  unqualifiziert. Keine alten Gazebo-Welten gefunden, kein Doppelserverbeleg.
  Neue Open-Prüfung: explizite aktive Goal-Toleranz und alle12 tatsächlichen
  Fingergelenke offen(|q|<0,02), ruhig(<0,003rad/s) über0,3sim-s. Action-SUCCESS
  allein reicht nicht. Regression mit geschlossenem passivem Finger/missing/
  NaN/bewegten Zuständen. Jetzt22PythonTests PASS; kein Schluss auf Hardware.
- Aktuell Run60/V82: Originaldämpfung0,08 und langsamere gemeinsame Objektbahn
  mit1mm/s statt2mm/s; übrige Mechanik/absolute0,05-Grenze unverändert.
  Vorpositions-Fixture, Recorder vor Runner, neue Sourcebindung. Noch kein
  PASS für diese Kombination. Konfiguration `variants/nominal-slow.yaml` unter
  `setup/tasks/manipulation_qualification_20261113/`.
- Run60/V82 **DONE + unabhängige Auswertung PASS** auf aktuellem striktem
  Quellstand: tatsächlicher Hub29,566mm, maxRelativfehler0,3081mm/0,002248rad,
  gemessener rechter Peak0,046573rad/s,4290 geladene Samples. Alle Pads unter
  Last, eingefrorene Offsets, freie Haltephase, unterstützte gemessene Öffnung,
  aufgelöste Gruppe und beide finalen Holds. Kein Anheften. Vorpositions-Fixture,
  kein neuer Home-Nachweis. Report `setup/tasks/carton_grasp_run60/validation-report.json`.
  Run61 wiederholt ohne Szenen-/Objektreset aus freigegebenem gemessenem Zustand.
- Aktuelle vorbereitete Profile mit gleicher Software: V83 leicht0,2kg/0,4 ab
  Home, V84 schwer0,4kg/0,8 ab Home, V85–87 Fault-Fixtures. Alle nutzen
  Dämpfung0,08/Objekttempo1mm/s/RTF0,6; noch nicht gefahren/qualifiziert.
- Run61/V82 Wiederholung ohne Reset ebenfalls **DONE + unabhängige PASS**:
  Hub28,082mm (nur0,082mm über unterer28mm-Akzeptanzgrenze), maxRelativfehler
  1,3543mm/0,010342rad, gemessenerPeak0,050000000118rad/s (numerisch1e-8
  toleriert),4318 geladene Samples. Alle Pads erhalten, unterstützte Freigabe,
  beide finalen Holds. Streuung/geringere Reserve ausdrücklich erhalten.
  Report `setup/tasks/carton_grasp_run61/validation-report.json`; Run62 aktiv.
- Run62/V82 dritte aktuelle Folge **DONE + unabhängige PASS**: Hub28,807mm,
  maxRelativfehler0,8419mm/0,006394rad, maxPeak0,050000000118rad/s (numerische
  Toleranz1e-8),4299 geladene Samples, alle Kontakte/Offsets erhalten, unterstützt
  freigegeben und beide finalen Holds. V82 samt allen Nachfahren danach gezielt
  beendet. Standardkartonprofil übernimmt jetzt geprüftes Objekttempo1mm/s.
- Run63/V83 leichte Variante0,2kg/Reibung0,4 ab Home aktiv; gleiche Software/
  Mechanik/Timing wie60–62. Noch kein Varianten-PASS behaupten.
- Fault-Probe ergänzt strikten Positions-Stillstand: mindestens0,3s Fenster,
  Armspan≤10µrad, Objekt-Achsenspanne≤0,1mm und Rotationsmatrixspanne≤1e-4.
  Erst danach0,6s beide Holds halten. Gegenbeispiel einer weiterlaufenden
  langsamen starren Bewegung unter3mrad/s wird abgewiesen. Software jetzt
  23PythonTests PASS; Regelprüfung erfordert weiterhin echte Injektionen.
- Software23PythonTests plus nativer Energie-/Reaktions-/Dämpfungstest, alle
  vier colcon-Suites PASS; Skill quick_validate PASS. Synthetischer0,051rad/s-
  Gegencheck verwirft DONE korrekt. Agenten-Kurzprüfung:
  `tools/inspect_manipulation_review.py RUN` ist rein lesend, stimmt nie zu.
- Offen: aktueller vollständiger PASS, Wiederholungen, Masse-/Reibungsvarianten
  und echte Laufzeit-Fehlerinjektionen (Memberstop/Runner-/Guardpause) unter Last.
  `tools/test_manipulation_fault.py` implementiert, noch nicht live nachgewiesen.
  Weitere Entwicklungsbelege: `work/carton-grasp-pipeline.md`.



## Zwischenstand vor Live-Störfalltests, 2026-11-14

### Technische Entwicklung und Einzelbelege

- Nutzerauftrag: wiederverwendbare agentbedienbare Skills; zwei rechte URs
  greifen leeren Karton, heben30mm, halten2s, setzen ab und öffnen. Agent prüft
  Strategie, Plan und Vorposition selbst. Ausschließlich Simulation.
- Implementiert: `uwa_cell_tasks`,11Skill-Verträge, CLI/Review/HTML-Vorschau,
  Ressourcenlease, SHA-gebundene Szenen/eigene Quellen/Binärdateien/Physik,
  bildbasierte Beobachtung, unabhängiger FCL-/Kugel-/Kontakt-/Schlupfwächter
  und Ressourcen-Supervisor. Einstieg `.agents/skills/uwa-manipulate/SKILL.md`,
  `docs/manipulation_pipeline.md`.
- Ab bestätigtem Kontakt ein Objektframe, unveränderliche Objekt→TCP-Offsets,
  ein12Gelenkcontroller/eine gemeinsame Zeitparametrierung. Geometrischer Kern
  `match_cooperative_handling.rigid_object`. Andere Arme gemessene Hindernisse.
  Verbundstopp erhält Griff; keine automatische Öffnung/Rückfahrt/Wiederaufnahme.
  Unterstützte stationäre Freigabe mit Guard-Ack. Kein künstliches Anheften.
- Eigene Welt `uwa_grasp_lab`, Namespace `/uwa_grasp_validation`, Domain64/
  LOCALHOST, private Uhr/TF. Hauptsimulation und Hardware unangetastet. Native
  ECM-Telemetrie100Hz,1ms-Physik; bildsensorfreie Physik plus separater statischer
  Snapshot-Renderer mit auditiert ruhendem Zustand. Bildpose ohne Ground-Truth-
  Prior; OAK VALID, Wrist LOST wird ausgeschlossen. Absolute Bildgenauigkeit
  nicht nachgewiesen. Wahrheit nur Rendererdefinition/Audit/Auswertung/Guard.
- Aktuelles mechanisches Profil: DART9.5.2, starrer2,5mm-Karton, elastische
  energieausgeglichene Getriebekopplung100Nm/rad, Motor10Nm/rad/Cap0,35Nm,
  Dämpfung0,08Nm·s/rad. Masse0,3kg/Reibung0,6 unvermessen. Objektgeschwindigkeit
  jetzt1mm/s; Arm-/Fingergrenze0,05rad/s und Relativgrenze2mm/1° unverändert.
  Material, Reibung, Steifigkeit, Dämpfung und ideale Armantriebe sind Annahmen.
- Aufrechter Karton/horizontale Unterstützung: Greifer gravitationsparallel,
  bildbasierter Yaw, Neigung>2° abweisen. Gegenüberliegende untere Wandbereiche,
  ganze nominale Padbox3mm unter oberen Ausschnitten.40konvexe Teile/7native
  Boxen erhalten Geometrie; Raster-/Flächenbeleg. Vier bestehende interne
  Gelenknachbarschaften im Python-ACM und nativen RRT identisch vererbt.
- Strikte Task-Peakprüfung: jeder empfangene rechte Gelenkzustand gegen0,05+1e-8,
  Peaks bis zum expliziten unbeladenen Reset verriegelt. Basisknoten5% Toleranz
  wird nicht als Taskgrenze verwendet.100Hz-Beleg, keine kontinuierliche Garantie.
  Open benötigt Actionerfolg plus alle12 tatsächlichen Finger(|q|<0,02,
  |v|<0,003) über0,3sim-s. Action-SUCCESS allein genügt ausdrücklich nicht.
- Nur lesendes ListControllers wird bei fehlender Antwort einmal wiederholt.
  Mutationen nicht automatisch wiederholen. Stopp sendet vor dem Warten beide
  Anfragen; Fehler der ersten verhindert die zweite nicht. Frische Messdaten
  und aktive unabhängige Holdcontroller sind für Bestätigung erforderlich.
- Rechnerprofil: RTF0,6/1ms, beschleunigte Kontaktqualifikation abgewiesen.
  `tools/configure_manipulation_cpu.py --scene SCENE` verändert nur exakte
  eigene Launch-Nachfahren: Physik CPU0–3/Guard4/Supervisor5; Runner CPU6–11.
  Kamera-Hintergrundprofil unverändert, keine CPU-Reservierung behaupten.
  `tools/trace_manipulation.py RUN --prepare` vor Runner starten und Trace-Datei
  prüfen; RunStore-Konstruktor allein persistiert CREATED nicht. Keine neuen
  ROS-Teilnehmer während armiertem Lauf. Kausalität der beobachteten DDS-Pausen
  nicht endgültig bewiesen; Frischegrenzen bleiben unverändert. Zwei12fach-
  Beobachtungsstresstests PASS, maxQuellenabstand131,44ms<150ms.
- Frühere mechanische PASS:42/43/44/47/48. Auf späterem striktem Softwarestand
  drei vollständige **DONE + unabhängige PASS**60/61/62 mit1mm/s und0,08Dämpfung:
  Hub am alten Eckursprung29,566/28,082/28,807mm, maxRelativfehler0,308/1,354/
  0,842mm.60 initiale Vorpositions-Fixture,61/62 Wiederholung ohne Szenenreset.
  Diese früheren Source-/Prüfpunktstände nicht als aktuelle Byteversion ausgeben.
- Run63 leicht0,2kg/0,4 erreichte frei tragend den Endpunkt, wurde aber am
  Eckursprung-Hub27,973mm gegen28mm-Untergrenze abgewiesen, beide Holds/Griff
  erhalten. Gegenprüfung: modellierter Schwerpunkt-Hub29,810mm, Kippwinkel
  0,01084rad (~0,62°). Ursache des Akzeptanzfehlers: Hubprüfpunkt in Ecke
  vermischt Translation mit erlaubter Rotation. Unterschiedliche Griffhöhen
  sind allein kein Beleg eines unzulässigen Kraftmoments; keine Greifgeometrie-
  Änderung aus dieser Hypothese abgeleitet. Run63 bleibt FAILED, nicht umetikettieren.
- Neuer eindeutiger Hubnachweis: Scene enthält SHA-gebundenen
  `lift_reference_point_object_m` = Schwerpunkt desselben uniformen Material-
  modells wie die Physik-Inertialdaten ([0,201215;0,170013;0,048267]m).
  Runtime/Validator messen dort30mm±2mm; Eckursprung wird separat protokolliert,
  Rotations-/Relativgrenzen unverändert. Assetpose und starre Objektkommandos
  unverändert; reine Translation bewegt jeden Punkt gleich. Regression prüft
  Dekopplung einer erlaubten kleinen Rotation vom COM-Hub.24PythonTests PASS.
- Zielmatrix: fünf aktuelle vollständige Kontaktzyklen einschließlich Varianten,
  danach Memberstop/Runnerpause/Guardpause unter tatsächlich frei getragener
  Last. V91–93 Fault-Fixtures mit derselben Mechanik/Software vorbereitet.
- Run64/V88 **DONE + unabhängige Auswertung PASS** auf aktueller COM-Definition:
  Schwerpunkt-Hub29,921mm, Eckursprung29,557mm; maxRelativfehler0,3146mm/
  0,002299rad, maxgemessenerPeak0,042798rad/s,4290 geladene Samples. Alle Pads
  unter Last/Offsets erhalten, unterstützt geöffnet, Gruppe aufgelöst und beide
  finalen Holds bestätigt.64 ist initiale Vorpositions-Fixture. Run65 wiederholt
  aus gemessenem freigegebenem Endzustand ohne Objekt-/Szenenreset.
- Run65/V88 **DONE + unabhängige PASS** ohne Reset: COM-Hub29,821mm,
  Eckursprung28,182mm, maxRelativfehler1,2835mm/0,009797rad, maxPeak
  0,050000000118rad/s (1e-8 numerisch),4327 geladene Samples. Kontakte/Offsets
  erhalten, unterstützt geöffnet und beide finale Holds bestätigt. V88 samt
  Nachfahren danach beendet; Run66/V89 leicht0,2kg/0,4 ab Home aktiv.
- Aktueller vollständiger colcon-Lauf: alle4Suites PASS (24PythonTests plus
  nativer Getriebe-/Energietest). Skill quick_validate erneut PASS.
- Run66/V89 scheiterte vor Griff im Beobachtungsstart an eigener Joint-
  Empfangslücke0,200368s; Objekt unterstützt, alle Pads frei, beide Holds bestätigt.
  Guardzustand vor Fehler CLEAR; eigene Empfangsalter0,20–0,29s. Nicht als
  Erfolg zählen. Neuer Run67 nach unabhängiger Recorder-Vorbereitung und
  Stillstands-/Frische-Reset, kein Resume des alten Laufs. Byteversion unverändert.
- Run67/V89 leicht0,2kg/Reibung0,4 ab Home **DONE + unabhängige PASS**:
  COM-Hub29,809mm, Eckursprung27,978mm (diagnostisch), maxRelativfehler
  1,4244mm/0,010912rad, maxPeak0,050000000022rad/s (numerisch1e-8),4298
  geladene Samples. Kontakte/Offsets erhalten, unterstützt geöffnet und finale
  Holds bestätigt. Dritter aktueller vollständiger COM-PASS; Startfehler66
  bleibt erhalten. Run68 wiederholt leichte Variante ohne Objekt-/Szenenreset.
- Run68/V89 leichte Wiederholung ohne Reset **DONE + unabhängige PASS**:
  COM-Hub29,813mm, Eckursprung27,762mm diagnostisch, maxRelativfehler1,5815mm/
  0,012105rad, maxPeak0,050000000118rad/s (1e-8 numerisch),4317 geladene
  Samples. Alle Kontakte/Offsets erhalten, unterstützt geöffnet/finale Holds.
  Vierter aktueller vollständiger COM-PASS. V89 danach samt Nachfahren beendet;
  Run69/V90 schwer0,4kg/Reibung0,8 ab Home aktiv. Source/Grenzen unverändert.
- Run69/V90 schwer0,4kg/Reibung0,8 **NEGATIVER GRENZTEST**: beim beginnenden
  Lastübergang passives Rear-Left-Fingertip0,078645rad/s. Strikte Prüfung stoppt
  Verbund, beide Holds bestätigt, alle Pads erhalten, Objekt noch unterstützt.
  Dieses Profil ist **nicht qualifiziert**, keine Grenzlockerung/kein positiver
  Hubnachweis. Virtuelle Episode explizit ohne Öffnen/Resume beendet.
- Varianten sind damit geprüft: leichte Variante positiv, schwere durch Grenze
  abgewiesen. Für fünf vollständige positive aktuelle Folgen läuft jetzt
  Run70/V94 Standard0,3kg/0,6 ab Home, sonst identischer Quell-/Physikstand.
  Bisher vier Positivfolgen64/65/67/68; Startfehler66 bleibt separat erhalten.
- Run70/V94 Standard0,3kg/0,6 ab Home ebenfalls **FAILED** am Lastübergang:
  Rear-Left-Fingertip0,059102rad/s, alle Pads erhalten, Objekt unterstützt,
  beide Holds bestätigt. Kein positiver Hubnachweis;1mm/s-Homeprofil nicht
  qualifiziert. Ein separater Datenprofilversuch Run71/V95 mit0,5mm/s folgt;
  Quellcode und Grenzwerte bleiben unverändert.
- Run71/V95 Standard0,3kg/0,6 aus Home bei0,5mm/s **DONE + unabhängige PASS**:
  COM-Hub29,893mm, Eckursprung29,309mm; maxRelativfehler0,5110mm/0,003783rad,
  maxPeak0,050000000022rad/s (1e-8 numerisch),8495 geladene Samples. Alle
  Pads/Offsets erhalten, unterstützt gemessen geöffnet, Gruppe freigegeben,
  finale Holds bestätigt. Fünf aktuelle Positivzyklen64/65/67/68/71;64/65
  nominale Fixture/Wiederholung,67/68 leichte Home/Wiederholung bei1mm/s,
  71 nominal Home bei0,5mm/s. Nur diese Datenprofile/Startbedingungen belegt.
  Defaultgeschwindigkeit nun0,5mm/s (reine YAML-Datenänderung).
- Störtests starten in frischen eigenen nominalen1mm/s-Vorpositions-Fixtures:
  Run72/V91 Memberstop,73/V92 Runnerpause,74/V93 Guardpause. Noch kein PASS.
- Fault-Probe `tools/test_manipulation_fault.py` hat zusätzlich≥0,3s Positions-
  fenster: Arme≤10µrad, Objektachsen≤0,1mm, Rotationsmatrixelementspanne≤1e-4;
  danach beide Holds0,6s halten. Gegenbeispiel weiterlaufender langsamer starrer
  Bewegung wird abgewiesen. Noch keine echten Injektionen als PASS behaupten.
- Verworfene Vergleiche: native Bullet-Kopplung instabil beim freien Schließen;
  Dämpfung0,12 überschritt0,05 beim Abheben, strikter Verbundstopp bestätigt;
  Dämpfung0,5 blieb tatsächlich geschlossen trotz Open-Actionerfolg und wurde
  per Bildreview vor Einfahrt abgebrochen. Alle Rohdaten/Fehlerläufe erhalten.
- Software:24PythonTests einschließlich Peak-/Open-/COM-/Stop-/ReadOnly-Retry-
  Regressionen sowie nativer Energie-/Reaktions-/Dämpfungstest. Letzter voller
  colcon-Lauf einschließlich COM-Ergänzung bestand; nach Manifestergänzung
  abschließend erneut prüfen. Skill quick_validate
  bestand. Entwicklungsbelege `work/carton-grasp-pipeline.md`. Kein Hardwareadapter.

## Implementierter Harness und abschließende Testmatrix, 2026-11-14

- Codebasis `uwa_cell_tasks` und gemeinsamer Geometriekern
  `match_cooperative_handling.rigid_object`;11agentbedienbare Skill-Verträge,
  versionierte Reviews mit tatsächlichen Bildern, ein eingefrorener Objektframe
  und eine12Gelenk-Zeitparametrierung ab tatsächlichem Kontakt.
- Aktuelle vollständige COM-Definition:64/65/67/68/71 DONE+unabhängige PASS.
  Nominal0,3kg/0,6-Fixture und Wiederholung bei1mm/s; leicht0,2kg/0,4 Home
  und Wiederholung bei1mm/s; nominal Home bei0,5mm/s. COM-Hübe29,809–29,921mm,
  maxRelativfehler0,315–1,581mm. Kontakte/Offsets erhalten, unterstützt gemessen
  geöffnet und finale Holds bestätigt. Keine nachträgliche Umdeutung alter Fälle.
- Bestandene Last-Störtests:72/V91 Memberstop nominal1mm/s-Fixture,
  75/V98 Runnerpause und77/V100 Guardpause leicht0,2kg/0,4/0,5mm/s aus Home.
  Vier Pads/freie Last erhalten, maxRelativfehler0,271/1,421/1,419mm; stationäre
  Holds einschließlich Bestätigungsfenster nach0,394/0,920/0,617s. Jeweils
  erwartetes FAILED mit Stopp bestätigt, kein Öffnen/Home/Bewegungs-Resume.
- Unabhängiger Traceaudit bestätigt vor Injektionen störungsfreie Bewegung ohne
  rechte Holds/Blocks (822/1790/1998Samples);75/77 zusätzlich frischer CLEAR-
  Snapshot direkt im Report.900sVorbereitungs-Wartebudget getrennt vom
  unveränderten5s-Stoppdeadline. Probeprozesspausen nur eigener Runner/Guard.
- Einschränkungen:66Empfangslücke vor Kontakt;69schwer0,4kg/0,8 Peak0,078645;
  70nominal Home1mm/s Peak0,059102;73Fixture1mm/s vor Injektion0,070306;
  74nominal Home0,5mm/s vor Injektion0,052335;76vor Fahrt linker passiver
  Finger nicht stationär. Alle abgewiesen, rechte Holds bestätigt, unterstützt.
  Fünf positive Einzelzyklen sind **keine nominale Wiederholsicherheit**.
  Default bleibt experimentell0,5mm/s; keine Massendaten/Schutzgrenzen geändert.
- Finaler Build2,85s, alle4CTest-Suites PASS (24Pythonfälle+nativer Getriebetest),
  Skill valide. Quellen/native Binärbindungen aller11genutzten Szenen nach
  Build unverändert. Hauptsimulation erhalten, eigene Greifwelten beendet.
- Vollständige versiegelte14Versuchs-Matrix: Workspace
  `setup/tasks/manipulation_qualification_20261114/result.json`, Status
  `test_matrix_complete_with_limitations`, nominale Wiederholsicherheit false.
  Dort Einzelreports, Softwarebeleg, Traceaudit sowie reproduzierende lokale
  Auswerteskripte. Anleitung/Bedienung `docs/manipulation_pipeline.md`, Skill
  `.agents/skills/uwa-manipulate/SKILL.md`. Keine Hardwareausführung.
