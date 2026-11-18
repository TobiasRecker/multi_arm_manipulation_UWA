# OAK-Neukalibrierung und deutliche Fünfkamera-Aufnahme

- Status: **Offline-Berechnung abgeschlossen: vorläufiger OAK-Posekandidat aus
  14Fünfkamera-Sätzen/70Fotos,10Fit- und4Prüfstellungen. Mehrkameraabweichung
  noch2,32–9,22nativeOAK-Pixel; keine Millimetergenauigkeit bestätigt und keine
  globale Übernahme. GUI/Fokus107 bleiben bestehen**,
  2026-11-18, Hauptagent.
- Auftrag: aktuelle OAK-Pose nach möglicher Stativbewegung beurteilen; danach
  vier URs in geeignete Aufnahmeposen und Fünfkamera-GUI öffnen. Aufnahmezustand,
  Abschluss und Anzahl gespeicherter Sätze deutlich darstellen.
- Zuerst aktuelle Bilder und Gerätenutzung prüfen. Alte OAK-Registrierung ist
  kein aktueller Nachweis; keine Kalibrierung automatisch aktivieren.
- Bereiche: board_capture_gui.py, gezielte GUI-Prüfung, Kamera-/Zellübergaben.
  Vorhandene Nutzeränderungen erhalten. Eigene neue GUI erst nach Prüfung öffnen;
  gegebenenfalls bestehende Kamera-App geordnet schließen, keine fremden Kills.
- Armfahrten erst nach geeigneter Kamerapose, frischen Hardwarezuständen und
  vollständiger aktueller Wegprüfung. Bekannter Frischestopp vom17.11. beachten.

## Nachweise und aktueller Stand

- Neueste Nutzerentscheidung18.11.: bisher keine Probleme beobachtet,
  Basisanbindungen aller vier Arme als fest übernehmen und Problemhinweise
  aus aktiven Ausgaben entfernen. Neues Standardprofil
  hardware_20261118_base_fixed_v1 mit vier unveränderten T_base_board-Quellen,
  Statusfixed_user_accepted und expliziter Nutzerentscheidung. LF-Boardframe
  wird unabhängig von der optischen Hand-Auge-Anwendung geladen. Keine
  ursprünglichen Messberichte umgeschrieben. OAK-Export jetzt alle vier
  Transformationen regulär unter transforms, gleiche numerische Werte;
  separate diagnostic_transforms-Gruppe/Ankerproblemtexte entfernt.
- Neues Profil installiert und aus Standardlayout geladen, alle vier
  base_binding-Statusfixed_user_accepted. Beschreibung/Overlay-Boardframes,
  bestehende Optik-/Kinematikbytes und Export geprüft;16gezielte TestsPASS.
  Veraltete90cm-Erwartung im vorhandenen Overlaytest auf bereits geltende
  99,1cm berichtigt, keine Modellpose geändert. Erneuerter Fotokontext führt
  feste Basisanbindungen aus dem aktiven Profil mit. Keine laufenden Dienste
  neu gestartet oder Roboteraktionen aus dieser Übernahme ausgelöst.
- Zusätzlich11bestehendeFoto-KontexttestsPASS (gesamt27); global übernommene
  Basisanbindungen und separat gespeicherte neue OAK-Pose im Export eindeutig
  als unterschiedliche Übernahmestände gekennzeichnet.

- Nutzer bittet nach manuellen Fotos um Berechnung.15Manifeste eingefroren,
 14vollständige stationäre Sätze/70nativeFotos; ein vor Aufnahme abgebrochener
  Versuch ohne Kamerabilder ausgeschlossen. Alle Originalbild-SHAs, Formate
  und Fokuswerte geprüft. Boarddetektion separat für beide40mm-Tischboards
  und mobiles38mm/IDs75–91 wiederholt. Dadurch alle14OAK-Mobileansichten
  verwendbar, auch frühere GUI-Reviewbilder. Vorbestehende Rollenfolge und
  vor Fit definierte Dublettenregel ergeben10Fit-/4Prüfstellungen.
- Fokus107-Intrinsics: Factory-Verzeichnung/Hauptpunkt/Aspekt behalten,
  gemeinsame Brennweitenskalierung aus10Trainingsansichten0,978326,
  fx5832,357/fy5831,934px. Trainings-RMS0,802px, disjunkte Prüfecken neuer
  Ansichten Median1,242/Maximum1,375px. Freier Brown4-Diagnosefit ist wegen
  begrenzter Abdeckung/Parameteränderungen keine automatische Ersatzwahl.
- Zuerst beide festen OAK-Boardposen getrennt geschätzt; zurückgehaltene
  Boardbilder links0,287–0,339/rechts0,899–0,940px. Das sind Reprojektion und
  Wiederholbarkeit, kein absoluter Genauigkeitsnachweis. Mobile Gegenprüfung
  zeigt besondersRR deutliche Abweichungen. Anschließend robuste gemeinsame
  Schätzung aller fünf stationären Kameraposen, relativer Tischboardpose und
  mobilen Brettposen mit festen passenden Intrinsics. Linksboard fixiert,
  historische T_base_board-Anker erhalten; keine nominale Basenlage zum Fit.
- Gemeinsame Schätzung konvergiert (sparse Initialisierung, dichter Abschluss).
  OAK-Mobilevorhersage nur aus Wristbildern auf vier zurückgehaltenen Stellungen
  RMS9,222/2,875/8,607/2,322px. OAK feste Boards im gemeinsamen Fit0,829–1,710px.
  Verfeinerung nach Sichtung erster Prüfungen als explorativ kennzeichnen;
  diese vier Ansichten sind kein neuer unangesehener Abschlusstest.
- Kandidat nach allen vier Roboterbasen; vorhandene gemessene T_base_board
  laut Nutzerentscheidung18.11. fest übernehmen. LF gleichberechtigt enthalten.
- Ausgabe calibration_candidate_v1/{oak_pose_candidate.json,.yaml,Ergebnis.txt,
  calibration_quality.png,numerical_checks.json} unter Aufnahmewurzel; vollständige
  Daten, Skripte, Split und beide Fits daneben. Rigidität/Inverse, getrennte
  Rollen/keine identischen OAK-Bilder über Splits, Fokus107, Bild-SHAs und
  Konvergenz geprüft. Mobiles Brett deckt nurx25–58%/y27–79% des OAK-Bildes ab;
  zusätzliche geneigte linke/rechte Randansichten und neue unabhängige Prüfungen
  wären für umfassendere Optikvalidierung hilfreich. Keine Roboteraktion,
  keine globale Registrierung/EEPROM-Änderung oder Geschwindigkeitssenkung.

- Nutzer beauftragt Fokus für vorderes und hinteres statisches Board gemeinsam.
  Eigene Fünfkamera-GUI im nicht aufnehmenden Zustand geordnet geschlossen;
  über bestehenden OAK-Fotopfad vier native8000×6000-Vergleichsfotos bei
  100/107/112/116, tatsächliche Lens-Readbacks jeweils bestätigt. Montage
  unverändert; beide Boardregionen separat an denselben Bildkoordinaten
  ausgewertet. Kontrastnormalisierte Schärfemetrik und visuelle Kantenprüfung
  bevorzugen107 an BEIDEN Boards. Detektion links/hinten bzw. rechts/vorne:
  100=9/18,107=24/24,112=19/24,116=0/21Ecken. Keine globale Fokusoptimalität
  oder Kalibriergenauigkeit daraus behaupten; AE/ISO waren leicht verschieden.
- Nachweis focus_both_static/{captures,comparison,decision}.json und
  comparison.jpg unter Aufnahmewurzel; Rohbilder weiter setup/oak4/photos/.
  Neues datensatzlokales acquisition_active.yaml enthält weiterhin107 und
  unveränderte Wristwerte. pose_gui.py nutzt diesen Fokus für Vorschau UND
  Fotos, Titel/Kontext dynamisch; beim Wiederöffnen frühere importierte Sätze
  rekursiv aus Herkunftsliste erhalten. Kein bereits gespeichertes Fokus107-
  Bild umetikettiert, keine Intrinsicsfreigabe oder Roboteraktion.
- Wiederhergestellte Sitzung20261118_140754_8caebf54: alle fünf Feeds frisch,
  fehlerfrei; tatsächlicher OAK-Vorschau-Readback107 bestätigt. Vorige vier
  Sätze/20Fotos in GUI erhalten. restored_gui.json enthält Vorschau-Metadaten.

- Nutzer hinterfragt reine OAK-Aufnahmen: Ziel ist ausdrücklich Extrinsics
  gegenüber Robotern/Welt. Klarstellung: mobile OAK-only-Bilder helfen nur der
  Optikprüfung bei Fokus107. Bekannte unveränderte Tischboards erlauben dagegen
  die Basisanbindung auch ohne neue Wristbilder; absolute Weltanbindung bleibt
  von deren bisherigem Weltanker abhängig/provisorisch. Für die weitere Reihe
  alle fünf Kameras speichern und mobile gemeinsame Sicht OAK+mindestens eine
  angebundene Wristkamera herstellen. Keine Pflicht, dass alle fünf dasselbe
  Board gleichzeitig sehen. Vorige OAK-only-Reihe bleibt erhalten.
- Eigener tasklokaler Wrapper pose_gui.py gestartet: mobiles38mm und beide
  Tischboardmodelle mit unterschiedlichen IDs/Skalen, eindeutige Referenznamen,
  vorhandene fünfteilige Sätze in Zählern wiederverwenden; keine Aufnahme
  automatisch, kein Fit/Profilwechsel und keine Roboterkommandos.
- Eigene OAK-only-GUI über SIGTERM/Qt-Schließablauf beendet, Dienst inaktiv;
  Fünfkamera-Dienst uwa-oak-pose-view-20261118 aktiv. Neue Sitzung
  five_camera_pose/20261118_140254_3e66161f, Zeiger pose-viewer-session.txt,
  Zustand/Screenshot pose-viewer-status.json/pose-viewer.png. Alle fünf Feeds
  frisch und fehlerfrei im geprüften Fenster; LF24/LR19/RF24/RR19/OAK24Ecken.
  RF/OAK beide uwa_mobile_a4, übrige feste Tischboards. Vier frühere native
  Fünfkamera-Sätze in Zählern enthalten:20Fotos,2usable/2Review nach damaliger
  Detektion. Zähler sind kein Nachweis vollständiger Extrinsics-Kalibrierung.

- Nutzer möchte weitere Bilder direkt in passender GUI auslösen. Dafür eigene
  OAK-Einzelansicht geöffnet (`uwa-oak-intrinsics-20261118`), mobiles38mm-Brett,
  IDs75–91, Fokus107fest, native8000×6000. KeineWristaufnahmeninIntrinsics-
  Phase, keineRoboterkommandos. FünfkameraansichtfürspäterePoseregistrierung
  bleibtseparatvorhanden. AlteGUIwarbeimUmstellenschonbeendet, keinFremdprozess
  gestoppt. NeueSitzungintrinsics_focus107/20261118_135449_64a7a980.
- VierOAK-BilderbestehenderSätze überOriginalbild-Symlinksimportiert, mobile
  Referenzerkennungneu:24/24/2/9Ecken. Zählerkorrekt4Fotos/2usable/2Review,
  OriginalmanifestalsHerkunftgespeichert. ErsteflacheundgeneigteAnsichtFit,
  weiterebrauchbareunterschiedlichePosenmitvorabdefinierter8/4-Rollenfolge;
  DublettennichtalsunabhängigeValidierungverwenden. Ziel12verschiedenePosen.
- Oberflächevisuellgeprüft: großesOAK-Bild, aktuellemobileErkennung24/24grün,
  Capture-All-1speichertnurOAK. NativeModusohneVerstellenvonFokus/Belichtung,
  Kamera-LeaseweiterüberbestehendenFotopfad. KeineAufnahmeautomatischausgelöst.

- Referenzset set_133728_183314 erfolgreich: nativeWrists2592×1944/OAK8000×6000,
 5/5gespeichert, all_usable=true, Stillstand während gesamter Aufnahme bestätigt.
  EckenLF20/LR19/RF24/RR24/OAK24. GUIzeigt1kompletten/1verwendbarenSatz,
 5Fotos/DONE. FokusWrist245/406/435/388, OAK107. KeineOptikwerte zurückgesetzt.
- NativeOAK-ErkennungseparatbeiderTischboardsje24Ecken. MitFactoryK/D
  (an116gebunden, aktueller107unvalidiert) disjunkteEckenprüfunglinks0,283px,
  rechts1,402px gegen1px-Kriterium. LinkeAnkerposealsInitialkandidatberechnet,
  beideT_base_oak-KandidatenundrelativeRearbasenmatrixgespeichert, nichtangewandt.
  Quellefirst-oak-reference-check.json, StatusINITIAL_POSE_CANDIDATE_NOT_APPLIED.
- FürpassendeFokus107-Intrinsics12mobileAnsichtenalsStartumfangvorgeschlagen,
 8Fit/4vordefinierteValidierung. ProtokollvorMobileaufnahmenfixiert.
  Bedienergebetenmobiles38mm-BrettamrechtenTisch30–45°stabilanzulehnen;
  nächsteAufnahmewartetaufBereitschaft. KeineArmbewegung/Geschwindigkeitsänderung.

- Neue Nutzerangabe18.11.: Antriebe wieder aktiviert; Fortsetzung der
  Kalibrierung beauftragt. Lesender Status nach RR-Hochlauf alle4RUNNING/NORMAL.
  Keine neuen Armfahrten/Startaktionen;0,1rad/s/Geschwindigkeitspolitik erhalten.
- Nutzer bestätigt beide festen Tischboards seit vorheriger Kalibrierung
  unverändert relativ zu den Basen. Historische Board-Anker für Posefit
  verwendbar, ihre Messunsicherheit bleibt. OAK-Fokus107 weiterhin ohne eigene
  intrinsische Validierung, keine finale Genauigkeit/Profilübernahme behaupten.
- Kamera-GUI geordnet auf vorhandene Tischboardmodelle `both` umgestellt:
  LF/RF/RR/OAK24Ecken, LR19bereits in der Vorschau. Vorherige linke0/24 waren
  im gewählten Mobile-Modell, kein fehlender Bildfeed. Neue Sitzung
  five_camera/20261118_133517_0068a219. Expliziter nativerCapture angefordert;
  Bedienerfeedback/Counts laufen in derselben GUI. Keine Bewegung/Fitaktivierung.

- Abschluss18.11.: LF01 und LR/RR/RF im geometric_only-Modus erfolgreich.
  Restfahrten wall inklusive Vorprüfung39,66/82,81/47,25s, nominelle Bewegung
 25,55/56,80/29,53s. Kein Wächterstopp im neuen Modus. Beim letzten Fahrtende
  alle vier nativen Gelenkstellungen gemeinsam innerhalb0,001rad am Ziel;
  maximale Abweichung0,000295rad (0,0169°). Abschlussbeleg final-result.json.
- Spätere native Abfrage: alle4POWER_OFF/STOPPED/NORMAL, Ursache/Akteur nicht
  festgestellt. Eigene Fahrfolge enthält kein Power-off, keine erneute
  Einschaltung. PowerOff liefert erneut teils stale qd und kleine Positions-
  abweichungen bis0,57°; deshalb diese spätere Beobachtung vom erreichten
  Endzustand unterscheiden. final-native-observation.json/final-actual.json.
- Fünfkamera-GUI neu geöffnet: uwa-oak-recalibration-view-20261118.
  Alle5Feeds frisch und fehlerfrei, Fensterbild visuell geprüft. Gewähltes
  Mobile38mm-Profil erkennt links0/24 trotz deutlich sichtbarer Boards,
  rechts teilweise, OAK24/24. Kein fehlender Feed. Zähler0, keine Aufnahme,
  kein Fit oder Profil aktiviert; OAK-Fokus107 bleibt intrinsisch unvalidiert.

- LF01erfolgreichamZiel, LR02Zwischenstellungerfolgreich; LR03bzuerstmit
  altemReserveprofilweitergefahren. NutzerfordertdanachexplizitEntfernung
  deszusätzlichenStoppschutzesund0,1rad/s. Deshalbgezieltgehalten:
  StopCLIbestätigtnativeSTOP/Holds/Stillstandaller4; alterExec03binaktiv,
  FehlrecorddurchgeplantenBedienerhaltbewahrtnichtalsZielerreichunggewertet.
- Opt-in-policygeometric_onlyimplementiert: dynamischeKörperdistanzbudgets0,
  geometrischer40mmPuffer/FCL, Geschwindigkeitsgrenzen, State-/Heartbeat-
  WatchdogsundnativeSicherheitbleiben. ZeitlichedynamischePaarleasentfallen
  zugunstenbestehender250msHeartbeatfrist; Policy-Signatur/Mismatchprüfung.
  Standardverhaltenenforceunverändert.33gezielteTestsPASS/1,56s.
- NeuesProfilalle24AchsenKommando/Monitor0,1rad/s, amax0,2, bestehendeHold-
  Verzögerung/Frische/Hystereseunverändert. DreiRestplänevonfrischemHaltzustand
  vorbereitet. NeuerModusnachgeordneterProfilumschaltung/QuietProof/Reset/
  ROS-Neuverbindungaktiv. RuntimeOFF(GEOMETRICONLY), CLEAR/keineFaults;
  LRinBewegung. TailjobsetztRR/RFnurbeiErfolgfort, keineFehlerwiederholung.

- Bedienerbestätigt18.11.Sicherheitskonfigurationanallen3Pendants.
  GemeinsamerBringupdanachalle4Ready/RUNNING/NORMAL/PLAYING/Reverseverbunden.
  FrischerMessstartmax0,358°vomreviewtenStartentfernt(mod2π), LF-Direktweg
  ausActualStartfrischgeprüft47,926s. Schutzprofilq6=.1scharf, aktueller
  Native-/Holds-/StillstandsnachweisPASS, expliziterResetundROS-Neuverbindung.
- EigenesExecuwa-capture-motion-20261118-01läuft; LFtatsächlichinBewegung,
  WächterCLEAR/keineFaults, andere3stationär. Quelle01-left-frontim18.11.-Ordner.
  FürhinterenAbschnittkannZeitaufteilungaufderselbenreviewtenGelenkgeraden
  nötigsein; geometrischeReihenfolgebleibtLF→LR→RR→RF.

- FreigegebenerBringupausgeführt: LFPowerOn/BrakeRelease/Playerfolgreich,
  RUNNING/NORMAL/PLAYING/Reverseverbunden. LR/RF/RRros.urpgeladen(gespeicherte
  tobias.installation), danachjeweilsCONFIRM_SAFETY. NativeSchrankenicht
  quittiert/umgangen; BedienerzurPrüfungundBestätigungandreiPendantsgebeten.
  NeuerStartdanachbereitsfreigegeben, keineerneuteallgemeineFreigabenötig.
  Quellebringup.jsonimVorschlagsordner. KeinneuesFahrzielgesendet.
- KollisionsdienstMONITORgestartet, alle4Haltereglerausschließlichinaktiv
  provisioniert. KeinArming/ResetunterunbestätigterKonfiguration. Wegennoch
  uninitialisierterArmekeineaktuellenNullwertealsHindernisposenverwenden.

- AusdrücklicheAntwort18.11.: Bereichfrei; Startaller4/Power/Brake/ROS,
  erforderlicheSchutzprofilwechselinklLFq6=.1undFahrtfreigegeben.
  FrüherekonkreteFreigabelückeistdamitgeschlossen. GemeinsamerBringup--apply
  gestartet; KollisionsdienstzunächstMONITOR, Haltereglerinaktivvorbereitet.
  KeineerneuteAbfragegleicherFreigabe; nachNativeReadyfrischenStartverwenden.

- Nutzer18.11.: „bitteführediebewegungenaus“ nachRViz-Vorschlag.
  GezeigteFolgedamitzurAusführungbeauftragt; notwendigePower/Brake/ROS-
  Startaktionenaller4lautWorkspace-Regelseparat, bishernurLF-Diagnoseneustart
  am17.11.freigegeben. GebündelteFreigabeStart/ProfileinklLFq6=.1undfreie
  Bewegungsbereicheangefragt; keineabhängigeAktionvorAntwort.
- FrischerDashboardstatusalle4POWER_OFF/NORMAL/STOPPED; LFros.urpgeladen,
  andere3gespeichertesunnamed.urp. Schutzdienstund4Einzeltreiberinaktiv.
  KeinevorgegebeneNullpositionfahren. Quellepre-execution-status.jsonim
  Vorschlagsordner. NachStartaktuelleEncoderdatenmitVorschlagabgleichen;
  keineerneutenBenchmark-/Regressionsreihen.
- Inzwischenalle4fehlendenlokalenTreiberübergemeinsamenBringup-Einstieg
  vorbereitetundScript-Listenerbestätigt. dashboard_commands[]leerbei allen4,
  keineAntriebs-/Programm-/Fahraktion. driver-preparation.jsongespeichert.
  Antriebs-/Profilfreigabebleibtausstehend; Schutzdienstnochinaktiv.

- NeueVorgabe18.11.: keineumfangreichenPrüfwiederholungen, einfachenplausiblen
  PfadzeigenundBedienerbewertungabwarten. AktuellelesendeNativeabfragealle4
  POWER_OFF/NORMAL/STOPPED mitq=0; nichtalsphysischenStartverwendet.
- EinmaligerVorschlagvomzuletztgültigenMessstart17.11. aus
  hardware-views-01/lf-speed-stop-snapshot.json. SerielleDirektsegmente
  LF→LR→RR→RF, jeweilskürzestezulässige2π-GelenkäquivalenzzualtenSichtzielen.
 266FCL-Stützstellen≤0,035rad, alle6Armpaaremit40mmstatischemHüllabstand,
  vollständigeGreiferöffnungshüllen. Berechnung2,122s, nominell170,09sbei
  ≤0,1rad/s/0,2rad/s²; Vorschau4×standardmäßig. KeineRealtrajektorie.
  setup/calibration/oak_capture_proposal_20261118/proposal.json.
- EigenesRViz+Play/Pause/Slider/Endposenfenster über
  tools/preview_capture_approach.py, Domain74/LOCALHOST, eigeneTF-/JointTopics.
  KeinPower/Brake/Play/Reset/Profilwechsel/Fahrziel. HistorischerStartimFenster
  deutlichgekennzeichnet. VisuelleBewertungersetztnichtdenspäterenStartabgleich.
- ViewerlebtmitfrischemStatusPREVIEW_PAUSED/t0/RVizrunning/Domain74,
  RViz-OpenGLgestartetundnachRessourcenpfadkorrekturohneLadefehler.
  AnfangsflüchtigeBoarddateienaufpersistentesmodel/umgestellt; nureigener
  Vorschauprozessneugeladen. EigenenQt-SIGTERM-Abschlusskorrigiert.
  KeinezusätzlicheRegressionssuite, keineHardwareaktion.

- FolgefragezurKollisionsmethode: neuerkörperbezogenerPlanungszweignutzte
  altenArm-AABB-Vorfilternicht; jetztkompatibelergänztundstandardmäßigaktiv.
  AktuellerLF-Plan20,18→10,07sBerechnung, +1,47sModellaufbau,
 895Punkteexaktgleich;316MotiontestsPASS. work/body-reserve-prefilter.md.
  Fahrdauer47,89sunverändert; keineHardwareaktion/FreigabeausdieserÄnderung.

- Lauf01c vorAktivierungohneFahrzielabgebrochen: blockierendevollständige
  TimingprüfungverursachteROS-Historienlücke. VorAktivierungjetzt erneutes
  `connect`/unveränderteHealthprüfungnachGeometriearbeit; nachControllerbesitz
  explizitverboten, keineLaufzeitwiederanlaufwartezeit. SnapshotCLIwartetebenfalls
  auffrischeStartpakete. 41TestsundgetrennterProzessmockinklAusfällePASS.
- Lauf01d/`01c-left_front/execution-refreshed.json` tatsächlichbewegt, nach
 42,69s inklVorprüfungvomq6-SpeedLimitgehalten: −0,03811rad/s gegen0,00755.
  LFdanachwiederstationär/held, keinKollisions-/TrackingfehleralsUrsache.
  NichtalsfertigeAufnahmestellungausgeben.
- NeuerKandidat01e: LFq6überwacht0,1rad/s, Fahrkommando≤0,1,
  vollständigneuberechneteStoppreserveundFCLPASS, Dauer47,89s. NochNICHTaktiv.
  AutomatischeFreigabeprüfunglehntgeordnetenProfilwechselab: konkreteErhöhung
  derSicherheitsüberwachungundProgrammstoppsaller4nichtklarvondamaliger
  Allgemeinfreigabegedeckt. KeineTeilaktionausgeführt, keineUmgehung.
  ExakteZustimmungfürdiesenVertrag/Programmstopps/ROS-Neuverbindung/Fahrt
  angefragt; bisAntwortkeineabhängigeHardwareaktion.
- ReineOfflinefolgeprüfung: LR-Schulterlift−0,7rad verschafftamEndefürLR/RR
 0,1rad/s-Kandidatenca62/68mmReserve. VorläufigerTrennwegkandidat0,01601rad/s
  (Startreserve20mmZiel). Ganze82s-TrennbahnmitprojiziertemLF-Ende
  vollständigmodellgeprüftPASS, ForecastnurBericht/keinausführbarerPlan.
  EchterStartnachLF-Zielnochfrischzuprüfen. `rear-separation-forecast.json`.
- LetzterStatuswährendFreigabewarten: alle4stationär, keineaktuellenFaults,
  LFheld/blocked, Schutzdienstweiterarmed. KeineabhängigeHardwareaktionnach
  automatischerAblehnung; keinerleiFahrprozessläuftweiter.

- LF-Power/Brake-Neustart bestätigtRUNNING/NORMAL/STOPPED, nochohnePlay/Fahrziel.
  AnschließendeursprünglichePrüfungPASS: alle4stationär, nativeLF2,016s/vmax0,
  Positionsspanne≤83,9µrad. WiederanlaufdesSoftwarepfadsnachfrischemNachweis.
  Standby selbstliefertebeiunverändertenPositionen eingefrorenenqd-Wert an
  anderemGelenk; darauskeineStillstandsqualifikationbeiPowerOffableiten.

- BedienerbestätigtpartielleleichteRucke amLF, nichtnurMessrauschen annehmen.
  AusschließlichLF-StandbyundNeustartausdrücklicherlaubt. TatsächlicherBefehl
  `power off`, RücklesePOWER_OFF/NORMAL/STOPPED; LF-StandbyJSONgespeichert.
  SchutzdienstundübrigeArmeerhalten. KeinneuesFahrziel/keinResetdieserPhase.

- Wiederaufnahme17.11. gegen17:34AWST: keine neue Fahrt/kein Reset gesendet.
  Native10s-Messung `hardware-views-01/resumed-native.json`: LF-q6
  Positionsspanne0,001079rad (0,0618°), Geschwindigkeitspeak0,04446rad/s,
  übrigeLF-Achsen0; dreiandereArmeohnevergleichbareGeschwindigkeit.
  LF RUNNING/NORMAL, ProgrammSTOPPED; übrige3PLAYING/Reverseverbunden.
  FrischerSchutzstatusSTOPPING, LF nichtstill; unabhängigeMessung bestätigt
  Wertequelle, Ursache(Servoschwingung/Messrauschen)nochungeklärt. KeineFilterung
  oderStillstandslockerung. SchutzdiensthältLF/LR/RF undfordertwiederholt
  nativenLF-STOP. NichtalsvollständigbestätigtenVierarmstillstandausgeben.
  Bedienerbeobachtung und expliziteFreigabe für ausschließlichLF-Standby/
  Power/Brake/ROS-Neustart angefragt; andereArme/Diensteerhalten.
- FünfkameraGUIweiteraktiv, frischeUI-Diagnosedateien, VorschauPAUSED/SNAPSHOT,
  keineAufnahmeläuft. Pauseunverändertgelassen.

- Aktueller Realversuch unter `setup/calibration/oak_recalibration_20261117/hardware-views-01/`:
  LF fuhr tatsächlich bis ca.[125,38,-91,05,6,22,-94,33,-7,67,0,65]°;
  noch nicht am Aufnahmeziel. Automatischer Halt wegen direktem Vergleich
  zeitversetzter ROS-/RTDE-Gelenkwerte; Hold und Verriegelung bestätigt.
  Native UR-Sicherheit nicht quittiert/umgangen. Erstes Reset während
  STOPPING durch automatische Prüfung abgelehnt; nach frischem unabhängigem
  Stillstandsnachweis expliziter Reset zugelassen. Keine offene Umgehung.
- Vergleich korrigiert: ROS-Historie klammert nativen Quellzeitpunkt ein,
  keine Extrapolation; Lipschitz-Interpolationsunsicherheit verbraucht die
  unveränderte5mrad-Grenze. Frische-/Epoch-/Modell-/Stoppprüfungen erhalten.
 40gezielteTests, Paketbuild und separaterDomain67-Prozessmock bestanden.
  Real ausschließlich lesend1.616Proben, maximale konservative Abweichung
 0,000520rad; kein Uhrsprung. Quellen: `alignment-live.json`,
  `setup/logs/uwa-state-alignment-{tests-host,mock,build,live}.log`.

- Frisches natives Standardfoto14:04/Fokus116: rechts24/24, links0/24;
  Detektion unter setup/calibration/oak_recalibration_20261117/current-board-check.json.
  Ansicht zeigt gute zentrale Übersicht, fernes Board deutlich unschärfer/kleiner.
  Empfehlung: bis maximal2m höher, steiler zur gemeinsamen Mitte; Fokus prüfen.
  Diese erste Ansicht ist seit bestätigter Neumontage durch den Nutzer überholt.
- Alle4URs lesend RUNNING/NORMAL, ros.urpSTOPPED, keineROS-Treiber/Reverse-Links.
  KeinePower/Play/Controller-/Fahr-/Greiferbefehle in diesem Auftrag ausgeführt.
  Abschlussabfrage: inzwischenalle4POWER_OFF/NORMAL/STOPPED, eigenecommands[]leer;
  jüngsterSnapshot ur-status.json imDiagnoseordner. Anfangsstatus damitüberholt.
- GUI umgesetzt: dauerhafter Aufnahmebanner, gespeicherte Fotos während laufender
  Aufnahme, Abschluss erst nach Backendrückkehr; Zähler komplett/verwendbar/Fotos/
  Review, letztes Resultat gegen Live-/Pausenmeldungen erhalten. Workerabbruch
  beendet RUNNING und sperrt neue Aufnahmen.12gezielteTestsPASS inklusive
  Livebild-Layoutregression; gitdiff--checkPASS.
- Kamera-only-GUI geöffnet: uwa-oak-recalibration-view-20261117.service;
  mobile38mmReferenz, alle4Wristkameras+OAK, keep-camera-settings, RTDE nur lesend.
  Lokale UI-Nachweise viewer-status.json/viewer.png im obigen Diagnoseordner.
  Alle5Feeds tatsächlich frisch/fehlerfrei empfangen undFensterbildvisuellgeprüft.
  Livepixmaps zuvorvergrößertenBildfelder; SizePolicy korrigiert, Fortschritt und
  letztesResultat platzsparend nebeneinander. NachletztemLayoutupdate eigeneGUI
  übernormalesCloseEvent beendet undneugeöffnet. KeineKalibrieraufnahmen.

## Bestätigte Neumontage / Prüfung gegen15:10

- Nutzer bestätigt Kamera neu montiert. NeueVorschau zeigt beideTische/Zentrum,
  nochvielHintergrundoben undwenigunterenRandamnahenBoard; kleinerzusätzlicher
  Schwenknachunten sinnvoll. KonkreteHöhe nichtgemessen.
- Natives8KStandardfoto151025-standard-6bc0b63c beiFokus116: rechts13/24,
  links0/24; nichtkalibrierbereit. Quelle/Detektion/Übersicht separat unter
  setup/calibration/oak_recalibration_20261117/remounted/.
- EigeneGUI fürnativePrüfung geordnetbeendet; zusätzlicheAutofokusaufnahme
  zumTrennenvonMontageundSchärfeangefordert. KeinFit/Profilaktivierung/UR-Befehl.

- Letztes Bild15:12 zeigt inzwischen stärker nach unten gerichtete Ansicht mit
  mehr unterem Rand. Diese Montage vorerst beibehalten. Autofokus tatsächlich107:
  rechts24/24, links15/24. Fokus100 im ähnlichen Ausschnitt schlechter:19/8.
  Fokus116 und107 wegen zusätzlich verändertem Ausschnitt nicht isoliert
  vergleichen; kein globales Fokusoptimum nachgewiesen.
- Eigene GUI mit festem107 wieder geöffnet, nur datensatzlokales Aufnahmeprofil
  remounted/acquisition_focus107.yaml. Globale Profile unverändert. Bestehende
  Factory-K/D sind an116 gebunden;107 noch nicht intrinsisch validiert. Kontext
  der neuen Sitzung markiert alte OAK-Registrierung ausdrücklich als historisch.
- Prüfquellen151245-standard-15690ce1 und151413-standard-f8e7dbe9, Detektion und
  Entscheidung im remounted/-Ordner. Vorläufige Montageeignung ist kein fertiger
  Kalibriernachweis. Nutzer zur festen Montage/freiem Bewegungsbereich gefragt,
  weil im15:12-Bild Personen direkt hinter den Tischen stehen. Keine Armfahrt.

## Freigabe und aktuelle Vorbereitung

- Nutzer bestätigt feste Kamera und freien Bewegungsbereich aller4URs.
  Erstabfrage danach: alle4RUNNING/NORMAL, ros.urpPLAYING und Reverse verbunden;
  vorhandene vier Einzeltreiberdienste wiederverwenden, kein Start erforderlich.
- Ziele aus historischem Sichtentwurf nur als Gelenkziele übernehmen, Wege mit
  aktuellem99,1cm-Modell/Livezuständen neu prüfen. Moderne Gerätefrische und
  Kollisions-/Stoppschutz beibehalten; keine Greifer-/Kontaktaktion.

- Frischer Start ist im vollständigen FCL-Modell frei. Kleinster Nachbarabstand
  hinten133,50mm zwischen Hüllenoberflächen; Standardreserve172,90mm blockiert
  Planstart. Aufteilung:40mm Modellreserve,30,09mm Takt/Datenalter,
 100,31mm angenommene1sStopplatenz,2,51mm angenommener Bremsweg. Keine gemessene
  feste Abstandsvorschrift; Hüllenradien sind bereits abgezogen.
- Nutzer widerspricht der Notwendigkeit zusätzlicher17,3cm wegen großer Hüllen.
  Vor jeder Fahrt angehalten und Rechnung offengelegt. Kleiner langsamer
  Trennweg(+0,26radLR-Schulterlift,325s) zwar offline geprüft, aber nicht
  ausgeführt und nach Einwand zunächst zurückgestellt. Alternative ohne
  Trennweg nur offline in Prüfung: Kommando0,004rad/s, überwacht0,006rad/s,
  unveränderte Modell-/Stoppparameter ergeben etwa119mm statt173mm.
- Vier Halteregler ausdrücklich inaktiv provisioniert. Wächter bleibt
  MONITOR ONLY. Keine Aktivierung, kein Fahrziel, kein Power/Brake/Play/Greifer.

- Folgeentscheidung des Nutzers: Reserve allgemein überarbeiten statt72min
  fahren. Umsetzung/Prüfung abgeschlossen, Details work/stopping-reserve-revision.md.
  Dieselben Wege mit neuem opt-in-Modus rechnerisch9,24min; keine reale
  Aktivierung oder Fahrt daraus durchgeführt. Alte langsame Pläne nur Vergleich.

## Reale Aufnahmestellungen nach Stopptest05

- Nutzer weist auf gerade abgeschlossenen Stopptest hin, berichtet eigene
  frühere0,3rad/s-Fahrten und beauftragt erneut ausdrücklich die Aufnahmeposen.
  Stopptest05 tatsächlich PASS; dessen langsamer RF-q6-Lauf bleibt von einer
  allgemeinen0,3rad/s-Stoppqualifikation zu unterscheiden.
- Aktuelle lesende Abfrage alle4RUNNING/NORMAL/PLAYING/Reverse verbunden.
  Vorhandener Schutzdienst scharf mit hardware_right_front_stop_test.yaml,
  RF nachTest gehalten/verriegelt. Vor neuer Fahrt aktuelle vollständige Wege
  und separate Achsverträge prüfen; bestehenden Dienst übernehmen statt zweiten
  Schutzpfad starten. Serielle Ausführung, keine Greiferaktion.
