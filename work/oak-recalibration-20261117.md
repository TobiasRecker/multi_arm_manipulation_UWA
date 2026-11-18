# OAK-Neukalibrierung und deutliche Fünfkamera-Aufnahme

- Status: **Vier Aufnahmestellungen angefahren und Fünfkamera-GUI geöffnet.
  Dynamische Reserve auf Nutzerwunsch aus, Kommandogrenze0,1rad/s.
  Spätere Endabfrage alle Antriebe POWER_OFF; keine Kalibrieraufnahme/Übernahme**,
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
