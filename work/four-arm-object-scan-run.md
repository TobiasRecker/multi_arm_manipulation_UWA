# Erster realer Scan mit vier parallelen Armen

- Status: **angehalten; Nutzer wählt OAK-Stabilisierung ohne weitere Armbewegungen**, 2026-11-13, Hauptagent Digitalisierung.
- Nutzer beauftragt Durchführung mit allen Robotern parallel und bleibt am
  physischen Nothalt. Das ist die Freigabe zur Vorbereitung/Ausführung eines
  tatsächlich kollisionsgeprüften Ablaufs; ungeklärte hintere Zusatzpfade nicht
  unverändert parallel senden, Native-Safety/Kollisionsprüfungen erhalten.
- Zuerst reale Starts, laufende Arbeiten, Controller-/Programmanbindung lesen;
  abgeschlossene LR-HD-Reihe erhalten. Neue Ziele mit größerer Trennung prüfen.
- Bereiche: Scanplaner (optionale räumliche Grenzen), eigener Hardware-Runner,
  Tests und Sitzungsdaten unter setup/digitization/. Keine pauschalen Kills,
  keine Safety-Quittierung, kein automatisches Rückfahren.
- Vor Bewegung konkreten Pfad/Modellnachweis dokumentieren und Nutzer deutlich
  über Bewegungsbeginn informieren. Bei Stop/Fehler alle eigenen Ziele canceln
  und eigene Fahrcontroller deaktivieren; keine automatische Wiederaufnahme.

## Stand vor externem Blocker

- Neue60mm-Wandziele/Reserveposen,21Blickpunkte/5Runden/2400Prüfpunkte.
  Alle4Arme übergesamteWege mit50mmRestabstand inkl±0,005radTracking getrennt;
  kleinsteModelluntergrenze339,0mm. Quell-MoveIt-Modell separat nachgeprüft.
- ParallelerRunner+separateStop-GUI implementiert. Build/34gezielteTestsPASS.
  ViernativeFake-URs/Domain75: gemeinsam Zielerreichung,STOPwährendBewegung,
  GUI-Heartbeatverlust,alleFahrcontrollerinaktiv/Stillstand,Resume-SperrePASS.
  Mock-ProzesseanhandPID+Startticksgezieltbeendet,keinefremdenDiensteangepasst.
- RealeZustände zunächst gelesen: FrontsPOWER_OFF;späterenp87s0DOWN,
  NMunavailable/CarrierOFF,allevierDashboardsTimeout. ROSJointStateslaufen
  ausCacheweiter,deshalbLiveDashboardWatchzusätzlichimplementiert.
- KeinePower/Brake/Play-/Armziele/Safetyquittierunggesendet. GUI zeigtBLOCKED.
  Nutzer um physischeVerbindung/Steuerungszustandgefragt,Antwortstehtaus.
- StatusreaderhatLatest-Snapshotdateiüberschrieben;Originalq-WerteimPlan
  erhalten,aberSnapshotbindunghistorischerPlanvariantenistungültig.
  Reader aufeindeutigeZeitdateien umgestellt,Runnerrejectaufgeänderten/fehlenden
  Snapshotsgetestet.VorFortsetzung frische immutablePlan-/Proofketteanlegen.
- ErstefünfHardwarefotosundrealeBewegungstehenaus,ersterSatzsollvorExtras
  zurBildkontrollepausieren. Dokumentationdocs/parallel_object_scan.md.

- Abschließender Retest auch nach serverweitem Cancel ohne Zielbestätigung:
  erneute vier native Fake-UR-Trajektorien, STOP und GUI-Heartbeatverlust PASS,
  eigene Prozesse im finally sauber beendet. Mock-Rohlogs/Erstresultate erhalten.
  34gezielteTestsPASS. Echter Hardwarestart bleibt wegen CarrierOFF offen.

## Wiederaufnahme 2026-11-13

- Nutzer kündigt Wiederherstellung der Verbindung an. Ethernet wieder UP,
  CarrierON und PC192.168.8.209. Erste echte Dashboard-Abfrage: LF RUNNING/
  NORMAL/PLAYING; LR und RR RUNNING/NORMAL/ros.urpSTOPPED. RF .103 Timeout.
- Nur lesende Prüfungen; neue Daten unter setup/digitization/four_arm_scan_20261113/.
  Keine neue Bewegung/Power/Brake/Play. Alte Quellen nicht überschreiben;
  vor jeder echten Fahrt frischen vollständigen Zustand und Aufbau prüfen.

- Wiederholte RF-Prüfung:22/29999/30004 NoRouteToHost,ARP FAILED. Andere
  Dashboards erreichbar, alle4Fahrcontrollerinaktiv; Cache-Joints vonRF zählen
  nicht als vollständiger Hardwarezustand. Factual question an Nutzer gestellt.
- Aktueller OAK-Prüffotoversuch13.11. fehlgeschlagen: MessageQueue closed,
  SDK meldet missed ping/device gone/FW crash. Fehlerdaten vollständig unter
  setup/oak4/photos/20261113-110935-standard-2810009d/. Kein erfolgreiches Bild,
  kein Firmwareflash/manuellerReset und keine Roboteraktion. Ursache noch offen.

- Begrenzter zweiter OAK-Versuch erfolgreich: native8000×6000/Fokus116,
  setup/oak4/photos/20261113-111253-standard-5b8d982b/. Prüfbild durchgesehen,
  gleicher Karton zwischen den Tischen. Neue assistierte Grobmaße43,3×34,3×16,2cm,
  rechte Board-PnP1,83px. Scheinbare Referenzänderung gegenüber12.11.
  1,77mm/0,34°, enthält Bild-/PnP-Unsicherheit; keine vermessene Tischbewegung.
- RF bleibt nach zweiter Dashboard-/ARP-Prüfung unerreichbar; keine Programme
  oder Fahrziele gestartet. Volle neue Hardware-Planung wartet auf seinen
  echten Livezustand und anschließend aktuelle Bediener-/Aufbaubestätigung.

- RF jetzt erreichbar: Dashboard RUNNING/NORMAL/PLAYING, zunächst Local; Nutzer
  bestätigt Remote-Umstellung, Anwesenheit am Nothalt, unveränderten Aufbau und
  freie Fahrbereiche/Kabel. Alle vier alten RTDE-Reader melden nach Netzausfall
  „Background reading is not running“. Gezielter Neustart ausschließlich der
  vier identifizierten Hardwarelaunches vorgesehen, Fahrcontroller inaktiv.

- Gezielter Neustart der vier alten Launches abgeschlossen, neue PID-/Lognachweise
  unter four_arm_scan_20261113/new_drivers.json. LF-Fahrcontroller inaktiv
  nachgeladen. LR/RR ros.urp über MATCH gestartet; RF-SetMode wegen verpasster
  initialer Modusmeldung abgewiesen, anschließend echte RUNNING/NORMAL/Remote-
  Lesung und Dashboard stop/play des vorhandenen Programms. Alle4 ROS-Modi7,
  Safety1, External-Control=true und Stillstand bestätigt. Kein Fahrziel.
- Neuer OAK-basierter Plan plan_wall60_reserves: alle4 Grundansichten und
  je4Zusatzansichten,20geprüfteWege; neuer unveränderter Snapshot/Inventarhash.
  Zeitunabhängiger50mm-Trennnachweis mit±0,005radKorridor läuft.

- Neuer Trennnachweis abgeschlossen: initial/extra/all alle4PASS, kleinste
  projektive Untergrenze339,89mm nach Polstern, gefordert50mm. FünfRunden,
  modellierte Bewegungszeit101,16s statt238,92s seriell, Kamera-/Stillstandszeit
  zusätzlich. Frisches einziges Stopfenster gestartet und Screenshot geprüft.
  Readiness-Check vor Ausführung läuft; noch keine Armziele.

- run01 vor jeder Fahraktion abgebrochen: LR-Fokus-Teilwrite änderte LED-Modus.
  Fehlerrestaurierung zeigte zusätzlich LF-gcc-falschenNativeCapture und
  LR-Autofokus-ROI-Abweichung beim unnötigen Vision-Neustart. AlleArme stehen,
  keineFahrziele. Bearbeitet: board_capture.py Fokus-/Restorepfad, modularer
  erprobter CB3-Helfer aus scripts/left_front_wrist_hd.py, gezielteTests.

- Kamera-Fokusvorlauf korrigiert: nur Fokus+expliziterManaged-LED-Setter, keine
  Rückschreibung alter Getter-ROI-Koordinaten und kein Visionneustart zur
  Fokusrestaurierung. Erprobter CB3-32bit-Helfer nach wrist_hd.py modularisiert,
  alter Servicewrapper erhalten.45gezielteKameratestsPASS, danach geänderter
  Fokus-Teilpfad38TestsPASS. Sandbox-HTTP-Testserver benötigte Hostnetz.
- Ursprüngliche LF/LR-Autofokus-ROIs vollständig wiederhergestellt, Feldprüfung
  inklusive LED bestätigt. Alte URCap-ROI-Setter konvertieren Koordinaten und
  benötigen gemeinsamen begrenzten Suchlauf; Nachweis roi_recovery_bounded.json.
- Neuer stationärer Fünfkamera-Vorlauf: alle4 festen Foki bestätigt; native
  Fotos laufen. Noch keine Armziele gesendet. Fremder Agent baut ausschließlich
  uwa_cell_motion/Simulation; work/four-arm-collision-planning.md gelesen.

- Stationärer Vorlauf: alle4 nativeWrist-HD-Fotos und StillstandPASS; OAK bei
  gleichzeitigem Start erneutSDK-Pingverlust, separate WiederholungPASS8K.
  Fünfkamera startet daher OAK erst nach den parallelenWrists, bei durchgehendem
  Stillstandsaudit. Auto-ROI-Restaurierung mit begrenztemgemeinsamenFeedback
  implementiert/testet; alle4 Originalkonfigurationen bestätigt.40TestsPASS.
- run02 am13.11.11:46:50AWST inMOVING/Runde1, alle4 gleichzeitig beauftragt.
  Gleiche immutablePlan-/Proofkette, frischer Modell-/Startcheck; Nutzer vorher
  ausdrücklich auf Bewegungsbeginn hingewiesen. ErsteBildkontrollpause geplant.

- Erste4Ziele11:48:06AWST erreicht, Fahrcontrollerdeaktiviert/Stillstand bestätigt.
  Runde1nativeFototransaktionen laufen; nochkeineExtras vorBildkontrolle.

- run02 um11:49:10 nach erfolgreicher erster4Arm-Anfahrt wegenGUI-Heartbeatverlust
  gestoppt, Stillstand bestätigt; OAK erneutgescheitert, keineZusatzfahrten.
- Kamera-Prozessisolierung implementiert: echter stationärer Retest alle4HD-
  Fotos/StillstandauditPASS, Parent-Spinmax18,2ms, OAK weiterhinSDK-Ausfall.
  Alle4Originalkonfigurationen restauriert. GUI-Singleton/Signalende real geprüft;
  alte eigeneZombie-Qt-Fenster gezielt entfernt, ein frisches HALTED-Fenster.
- Geprüfte ursprüngliche Runde2 ohneInitialfahrt explizit auswählbar; kein
  automatischer Neustart. Nutzer um Entscheidung OAK-Diagnose vsRest-Wrist-
  Runden+zeitlichseparatesOAK-Referenzfoto gebeten. VierRundenstehenaus.

- Abschließende68gezielteTestsPASS; letzte echte Prüfung alle4RUNNING/NORMAL,
  ExternalControlverbunden, Stillstandbestätigt, sämtlicheFahrcontrollerinaktiv.

- Nutzer wählt ausdrücklich: zuerst OAK stabilisieren, keine weiteren
  Armbewegungen. Neuer Diagnoseeintrag work/oak-connection-stabilization.md.
