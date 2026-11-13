# UWA-Zelle – Ziele, Anforderungen und Übergabe

## Zusätzliche NVIDIA-Workstation für FoundationPose, 2026-11-13

- Nutzer stellt titanpc/192.168.2.137 über WLAN für Compute bereit. Gemeinsame
  Workstation anderer Nutzer: vorhandene Umgebungen/System/Dienste erhalten.
- TITAN RTX24GiB, Ubuntu22.04.5, Treiber570.211.01, Toolkit12.3 real gelesen.
  Docker ohne Benutzerzugriff; Systempartition nur5,5GiB frei. Deshalb eigener
  Ordner und eigene Conda-Umgebung auf Datenlaufwerk RAID1_L, keine Adminänderung.
- FoundationPose-Installation und begrenzte offizielle RGB-D-Demo in Arbeit;
  noch kein Inferenzerfolg. CPU-Tracker und alle lokalen Roboter-/Simdienste
  erhalten. Stand/Bedienung: docs/foundationpose_titanpc.md,
  laufender Status work/foundationpose-titanpc.md.
- Fachlicher Anschluss: bekannte Karton-/PTFE-Assets, statische Lokalisierung
  und dynamische Verfolgung. Reale OAK-Anbindung benötigt noch passende
  RGB-ausgerichtete Tiefe, Intrinsics und Initialmaske; keine direkte Nutzung
  der Mono-HQ-Tiefe mit RGB oder neue Manipulationsfreigabe.

## Schnellere Digitalisierung: Bestandsprüfung und Umsetzungskonzept, 2026-11-13

- Nutzer möchte weniger Wartezeit und niedrigeren Reasoning-Aufwand bei
  möglichst gleicher Qualität/Sicherheit. Noch keine Modelleinstellung geändert.
- Bestandsprüfung: Aufnahme/Optik/Fit/Export/Prüfung teilweise wiederverwendbar;
  Formbeschreibung, Bildzuordnung und Texturflächen noch objektspezifisch.
  Erfolgreiches PTFE-Fünferset laut Manifest44,34s, ohne Vorbereitung/Restore,
  Fehlversuch und nachfolgende Entwicklungszeit; vollständiges Timing fehlt.
- Geplant: Runner mit festen Daten-/Qualitätsverträgen, konfigurierbare Kasten-
  und Plattenvorlagen, Wiederaufnahme, kompakte Statusausgabe, kurze Skill für
  schnellen Agenten; gezielte Fachbearbeitung bei unbekannter Form/Fehlern.
  Geometrie/Darstellung/Tracking/Manipulation getrennt bewerten.
- Abnahme zuerst auf gespeicherten Karton-/PTFE-Daten plus Fehlerfällen,
  anschließend Vergleich der Reasoning-Stufen und neues Objekt ohne neue
  Objektskripte. Keine Laufzeit-/Genauigkeitsgarantie vor dieser Messung.
- Diese Runde nur Konzept/Dokumentation, keine Implementierung, Kameraaktion,
  Armfahrt oder Dienständerung. Plan docs/digitization_pipeline_plan.md.

## PTFE-L-Konstruktion aufgenommen und als Asset exportiert, 2026-11-13

- Separater Nutzerauftrag: neues Objekt mit vier Wristkameras und OAK aufnehmen,
  Asset für anschließendesTracking anlegen. Nutzer bestätigt20×20mm-Profile und
  10mm-Platten; Außenmaße bildbasiertca300×177×181mm. Keine Armbewegung.
- Set setup/digitization/ptfe_l_20261113/acquisition/20261113_153425_f9234640/
  set_153436_409595/ vollständig aufgenommen/brauchbar und kontinuierlich
  stationär bestätigt; nicht alle Boards vollständig sichtbar. Erster Versuch
  ohne ROS-Joints bleibt gescheitert. Zweiter Versuch explizit mit neuem rein
  lesendem RTDE-Ausgabebeobachter; keine Treiber-/Programm-/Poweraktionen.
- Asset description/assets/ptfe_l_assembly_v1 mit STEPmm, STL/GLB/DAEm,
  fünf Fototexturen, Manifesthashes. Ein geschlossener Körper/116Dreiecke,
  STEP-/Mesh-Rückimport geprüft,21gezielteTests bestanden. Platten/Profilnuten/
  Schraubdetails teilweise vereinfacht; keine absolute Genauigkeit validiert.
- Geometriefit OAK/LR/RR, RF ausschließlich geometrische Prüfansicht mit25,20px
  Restfehler bei1600px-Breite. LF wegen nativer Optik-/Boardinkonsistenz metrisch
  ausgeschlossen. Schätzgrenzen in docs/ptfe_l_assembly.md, keine PASS-Umdeutung.
- Trackingreferenz1494Merkmale vorbereitet. Offline-OAK/LR/RR/RF jeweilsLOST;
  regelmäßige Lochstruktur/glatte Flächen erschweren SIFT. Keine Online-
  Tracking- oder Manipulationsfreigabe für dieses Objekt. Mehrskaliger Versuch
  ebenfalls erfolglos, Diagnosen erhalten, bisherigen Trackerstandard beibehalten.
- Laufende Karton-Simulations-/Greifarbeit unverändert; neues Asset installiert,
  noch keine aktive Szeneinstanz. Anleitung und Vorschau docs/ptfe_l_assembly.md.

## Modulare Karton-Greifpipeline: Implementierung und erste Prüfungen, 2026-11-13

- Nutzerauftrag: agentbedienbare Skills/Pipeline, zunächst beide rechten URs
  greifen leeren Karton in Simulation, kurzer Hub und Absetzen, Kontaktphysik.
  Agent prüft Strategie, Plan und Vorpositionsbilder selbst innerhalb des
  Auftrags. Hardware ist spätere Arbeit; keine neue manuelle Freigabe je Phase.
- Verbindliche Präzisierung: nach Greifen starres Multirobotersystem, nur
  Objektbewegung vorgeben, feste Objekt→TCP-Offsets; keine getrennte Planung
  oder Zeitparametrierung tragender Arme. Gemeinsamer geometrischer Kern im
  bestehenden match_cooperative_handling, andere Arme bleiben außerhalb.
- Neues uwa_cell_tasks mit Skill-Verträgen, SHA-gebundenen Reviews, eigenem
  Kontaktprofil, Bildworker, gemeinsamem12-Gelenk-Stellverlauf aus Objektbahn,
  unabhängiger Geometrieprüfung und bestehendem Ressourcen-Supervisor.
  Separater Greifziellatch erhält Stellkraft bei Armstopp. Keine Objektbefestigung.
- Paket/C++-Backend gebaut,7gezielte Softwaretests bestanden. Eigene Gazebo-Welt
  uwa_grasp_lab/Namespace uwa_grasp_validation mit privater Uhr/TF in Domain64,
  gemeinsame Zelle/Planungsvergleich nicht neu gestartet. Kein Hardwarezugriff.
- Entwicklungsfehler erhalten: erste OBJ-Prismen ohne Normalen verworfen,
  auf normalehaltigeSTL gewechselt; Spawn-CLI überschreibtSDF-Pose, deshalb
  explizitePoseargumente ergänzt. Erstes100-Hz-PD-Profil instabil; eigenes1-kHz-
  Profil/kd0,003 steht gemessen ruhig. ROS-Clientname/privaterUhranschluss und
  Reset nach altemRunnerverlust korrigiert. Keine Grenzwerte der altenZelle gelockert.
- Aktuell noch **kein erfolgreicher Kartongriff/Hub nachgewiesen**. Eigene
  Simulationsläufe unter setup/tasks/carton_contact_20261113_v*/ und Logs
  setup/logs/uwa-tasks-*. Übergabe während Umsetzung, kein Abschlussbericht.
  Anleitung docs/manipulation_pipeline.md, Status work/carton-grasp-pipeline.md.

## CPU-Objektpose mit statischem und dynamischem Modus, 2026-11-13

- Neuer Nutzerauftrag: bekannte digitalisierte Assets wiederfinden, statisch vor
  Manipulation Genauigkeit priorisieren, dynamisch Onlinegeschwindigkeit.
  Ursprünglich zunächst Intel-Mini-PC; zusätzlicher NVIDIA-Rechner seit13.11.
  ausdrücklich für isolierte FoundationPose-Versuche verfügbar (siehe oben).
- Neues Paket uwa_cell_tracking: assetgebundeneSIFT-/3D-Merkmale ohne bekannte
  Objekt-/Boardpose, globale/panelweisePnP-Hypothesen,3-Frame-Static mit robustem
  Fit, dynamischesLK/PnP und Wiederinitialisierung. ROS-Pose/Status/Overlay,
  expliziteLocalize/Start/Stop-Services; Worker unabhängig vom ROS-Spin.
- Echte OAK opt-in auf65/LOCALHOST mit bestehender Fotolease. VorhandenerSDK-
  Previewworker unterstützt zusätzlich1600×1200/10fps und tatsächlichesK/D/
  SDK-Bildalter; alte2fps-GUI-Vorschau unverändert. Keine Roboteraktionen.
-6Kernel-/Referenztests und isolierterROS-Replay71 bestanden. Begrenzterrealer
  OAK-Lauf:188Frames/10,012fps, statischVALID0,42pxRMS/Ergebnisalter1,39s;
  116OnlineVALID-Ausgaben inca12s, Kernmedian7,53ms, maxSDK-Bildalter128ms.
  24Boardecken/0,256pxRMS prüfenAusgabeoptik separat, nicht alsTrackerprior.
  OAK danach geschlossen/Fotosperrefrei. Keine Dienste/Roboter neu gestartet.
- Grenzen: Objekt stand still; echte Bewegung/Verdeckung/Wiederfinden und
  absolute Kontrollmaße offen. OAK/RR im finalenBildtest brauchbar; LR/RFLOST.
  Frühere falsche Entwicklungshypothesen erhalten, keine universelle Freigabe.
  VALIDbedeutetBildkonsens; manipulation_approved/absolute_accuracy bleibenfalse.
- AusgabeT_camera_object, keine ungeprüfte Welt-/Basisübernahme. Näherungsmodell
  und vorläufige Weltkalibrierung begrenzen Genauigkeit. M3T und FoundationPose
  als späterevergleichbare Backends geprüft, noch nicht angebunden.
- Bedienung docs/object_tracking.md; Einstieg scripts/object_tracking.sh
  oak/localize/track/stop/view. Rohdaten setup/tracking/carton_cpu_20261113/.

## Texturierter Karton als Zell-Asset eingefügt, 2026-11-13

- Nutzer wünscht das fertige Modell als wiederverwendbares Asset und in der
  virtuellen Zelle an der real beobachteten Position. Paketiert unter
  uwa_cell_description/assets/carton_avocado_v1/: COLLADA+vierJPEGs für beide
  Renderer, GLB/STL/STEP und Manifest mit Herkunft/Hash/Qualitätsgrenzen.
- Zentrale Instanz scene_objects/avocado_carton in cell_layout.yaml; Ursprung
  aus Bildfit relativ zum rechtenChArUco-Board, dessen bestehende Zellpose
  wird weiterverwendet. Unterer Mittelpunkt etwa(-0,013;0,007;0,903)m zwischen
  denTischen. Keine neue absolute Weltkalibrierung oder höhere Genauigkeit.
- Separater statischer Visualspawn, ROS-TF asset/avocado_carton und texturierter
  RViz-Marker teilen eine Pose. Normaler Zellstart lädt automatisch; laufende
  Zelle ergänzt durch cell.sh assets, Reloadservice/uwa_cell/scene_assets/reload.
  Eigener Benutzerdienst uwa-cell-assets; bestehendeZelle nicht neu gestartet.
-17Offlineprüfungen bestanden; liveGazebo-Modellpose/TF/Marker abgeglichen,
  Zell-PID274663 unverändert. RViz geöffnet; keine Texturladefehler imLog.
  Direkter RViz-Renderexport visuell geprüft; Fototextur und Position sichtbar.
  Vorschau output/images/carton_in_virtual_cell.png.
  Sim-OAK vom parallelenReplay entfernt, daher dessen Einstellungen bewahrt
  und kein Kamerabildnachweis behauptet. Bericht unter Kartonordner/scene-live/.
- Visual-only ohne neue Gazebo-/MoveIt-Kollision oder Hardwareaktionen;
  laufenden Planungsvergleich erhalten. Keine vollständigen Rohfotos/Sitzungen
  ins Asset kopiert. Bedienung/Grenzen docs/carton_scene_asset.md.

## Großer Karton aus gespeicherten Farbfotos rekonstruiert, 2026-11-13

- Nutzerauftrag nach Scan:3D-Modell des neuen offenen Avocado-Kartons.
  Erster assistierter CAD-Entwurf ca.404×342×163mm, Boden/vierWände mit
  nachgezeichneten Griff-/Oberkantenausschnitten und optionalen Fototexturen.
  Dateien setup/digitization/carton_multiview_20261113/cad/: STEP/mm, STL/m,
  GLB/m, editierbare SCAD/mm; carton_preview.png im übergeordneten Ordner.
- Alle25Originalfotos geprüft,20metrisch verwendet. LF wegen widersprüchlicher
  nativer Bildgeometrie ausgeschlossen; seine Kalibrierflags unverändert.
  LR/RF/RR eigene passende HD-K/D, OAKWerksoptik; keine VGA-Substitution.
  Direkt sichtbares rechtesBoard und aus Trainingsbildern geschätzte Relation
  beiderBoards, keine nominellen Tischabstände/FK/Hand-Auge-Weltanker.
- ZehnFit-/zehnPrüffotos, davon vierOAK-Prüfungen nur zeitliche Wiederholungen.
  Prüfkameraposen nur ausBoardpunkten. MedianPunkt-RMS bei1600px Breite:
  Training14,05px/Prüfung13,68px. Daher ausdrücklich keine metrische Freigabe
  oder Millimetergenauigkeit. Reale Kontrollmaße und Ursache der systematischen
  Kameradifferenzen offen. Dicke2,5mm angenommen; verdeckte Details vereinfacht.
- STEP-Rückimport/Einheiten, geschlossenes zusammenhängendes STL292Dreiecke,
  GLB-Rückimport, Transformationsrichtung und Kontur-Rückprojektion geprüft.
  Gezielte100/70px-Störung sämtlicher Prüf-Objektpixel verändert Fitparameter
  nicht. Ergebnis/Hashes/Prüfungen lokal erhalten; Vorschau visuell geprüft.
- Neue Offlinewerkzeuge tools/reconstruct_carton_scan.py,
  export_scanned_carton.py, preview_scanned_carton.py. Keine Kamera-/Arm-
  oder Dienstaktionen, keine Profil-/TF-/Gazebo-Änderung, keine Installation.
  Anleitung und Grenzen: docs/carton_multiview_2026-11-13.md.

## Kamerabeleuchtung im Leerlauf geprüft, 2026-11-13

- Nutzer erinnert nach Scanabschluss an Abschalten der Kamerabeleuchtung bei
  Nichtbenutzung. Bestehende Regel gilt weiter: erster Foto-/Videonutzer an,
  letzter Nutzer aus; aktive parallele Nutzer erhalten.
- Keine laufende Kameranutzung und alle vier Nutzungssperren frei. LED0 bei
  LF/LR/RF/RR bereits beim ersten Readback, nochmals explizit gesetzt und erneut
  an der Kamera bestätigt. Automatischer LED-Wächter aktiv/aktiviert; aktive
  Nutzungsintensitäten der Profile beibehalten. Kein aktueller Abschaltdefekt
  nachgewiesen, keine Arm-/Treiber-/Programmaktion.
- Historischen Rolloutstand bereinigt: LR-Job ist seit12.11. COMPLETE; alle vier
  Kameras verwaltet. Nachweis setup/wrist_lighting/idle_check_20261113/verified_off.json.


## Vierarm-Kollisionswächter/PTP: nach Neustart fortgesetzt, 2026-11-13

- Nutzerpause und erlaubter PC-Neustart durchgeführt; Nutzer hat danach die
  Fortsetzung ausdrücklich beauftragt. Keine automatische Bahnfortsetzung.
  Checkpoint `setup/logs/uwa-motion-reboot-checkpoint.json`;28/55verschiedene
  Bahnen erfolgreich in Gazebo,27noch offen, Offlinevergleich300/300fertig.
  Alle vier Simulationsarme/Resource-Holds bestätigt, eigener motion-Dienst
  kontrolliert beendet. Physik1ms/RTF1 und ursprüngliche Kameraraten bestätigt.
- Letzter Replay-Abbruch blocked_direct_03 erfolgte vor Zielbewegung wegen
  Restgeschwindigkeit eines gerade vorbereiteten Hindernisarms. Rohdaten
  `executions/development-before-obstacle-settling/` bleiben im Bericht.
  Korrektur: vor Start100ms Ruhe abwarten, vollständigen Start danach erneut
  prüfen; unbekannte Hindernis-/Greiferbewegung während Fahrt weiter abbrechen.
  Nach Neustart keine automatische Pose-/Bahnwiederaufnahme. Anleitung und
  genaue Fortsetzungsaufgaben in work/four-arm-collision-planning.md.
- Nach Neustart vollständiger Stoppcheck einschließlich besonders knapper
  Paarlease PASS: setup/logs/uwa-motion-live-guard-check-complete.json.
  Abstandsfault→Stillstand182ms, knappe Paarlease→Hold127ms, gesamter
  Wächterverlust→Hold281ms. Eigene Simulation und normaler Wächter gestartet,
  Replay der27restlichen verschiedenen Bahnen fortgesetzt.
-29.Bahn bestätigt. Danach native Vorbereitung wegen Greifer-Nullpunkt-
  Rundung(-7e-14rad) abgewiesen. Native Grenztoleranz auf dieselben1e-8rad
  wie gemeinsame Prüfung gesetzt; echte Überschreitung -1e-5 bleibt ungültig.
  Alle300Offline-Startzustände nutzen exakt0rad am Greifer, Audit gespeichert;
  Abfragegeometrie/Benchmarkfälle bleiben unverändert. Fehlversuch/Diagnose
  in development-before-native-bound-tolerance/ bzw. uwa-motion-*.log erhalten.
- Neu53automatische Prüfungen PASS(CTest56mit3Wrappern). Stillstand-CLI
  prüft wie Wächter/Hold die unabhängigen Antriebe, statt passive Gazebo-
  Mimic-Geschwindigkeitsgeräusche als Antriebsbewegung zu behandeln. Ungültige
  oder fehlende Antriebsdaten sperren weiter; Bestätigung ausdrücklich drive
  standstill. Reale Hardware unverändert.
-31Bahnen bestätigt; folgende Vorbereitung wurde wegen Paarlease bei
  langsamer Simulationszeit angehalten. Ursache Zeitbasis korrigiert:
  Protokollv3 prüft Geometrie mit10Hz monotone Echtzeit, passend zu Watchdog
  und Reserve. Grenzwerte unverändert. Ehemaliger Versuch erhalten unter
  development-before-wall-timer/. Geprüfte Sim-Grundstellungsfahrt PASS;
  vollständiger Livecheck samt pausierter Physik/STATE STALE PASS:
  setup/logs/uwa-motion-live-guard-check-steady-wall.json. Beobachtete63ms
  Abstandsfault→Stillstand,132ms knappe Paarlease,321ms Wächterverlust→Hold,
  keine garantierten Obergrenzen. Replay mit24offenen verschiedenen Bahnen
  nach bewusstem Reset fortgesetzt.

- Neuer Nutzerauftrag/Entscheidungen: unabhängiger10Hz-Kugelwächter für vier
  Nachbarpaare, verriegelter Paarstopp statt pauschalem Vierarmstopp; offene
  Greifer/Wrist-Gehäuse einschließen. Zunächst PC-/ROS-Fahrten nur in Simulation64.
  PTP vorab planen, Warten erlaubt, RRTConnect und unabhängige zirkulare Felder;
  CDF später. Keine Hardwareaktionen aus dieser Aufgabe.
- Neues Paket uwa_cell_motion: konservative Vollkörper-Kugelhüllen,
  geometrischer Wächter plus unabhängiger Watchdog, Ressourcen-Haltecontroller
  je Arm, gemeinsame Zielauflösung/MoveIt-FCL-Prüfung/Quintik-Zeitparametrierung,
  native OMPL-RRTConnect und CF-inspirierte Offline-Rollouts ohne RRT-Fallback.
  Anleitung docs/four_arm_motion.md; Arbeit work/four-arm-collision-planning.md.
- Paket gebaut,50Offlineprüfungen bestanden (CTest zusätzlich3Wrapper,
  zusammen53/0Fehler), einschließlich Hindernis-Einschwingen vor Start und
  Greiferbewegung während Arm-PTP. Gazebo-Wristfahrt0,04rad
  bestanden. Live-Stoppprüfung der Protokollv2-Version bestanden:
  nurLF/RF stoppen/LRerreichtZiel, Topic-/Reaktivierungssperre, Mehrfachfehler,
  Datenverlust und Wächterausfall/Wiederkehr verriegelt. Fehler→Stillstand125ms,
  Wächterverlust→Halteverriegelung419ms; Teilreset/WeiterfahrtRR bei fehlendem
  LF-Zustand bestanden. setup/logs/uwa-motion-live-guard-check-final.json.
  Simulation, keine reale Stoppreserve.
- Endgültiges Offlinevergleichssetv4 komplett300Versuche: RRT102/125,
  zirkulare Felder115/125 gültige Zielversuche erfolgreich, je25ungültige
  Ziele verworfen. Kreuzungen3/25gegen15/25; Kugelbahnüberschneidung jetzt
  nachgewiesen, Meshkontakt separat.250unveränderte Versuche mit Herkunft zu
  v2 verlinkt,50korrigierte Kreuzungsversuche ergänzt. Feste Suite im Paket.
-55verschiedene erfolgreiche zeitparametrierte Bahnen zum Gazebo-Replay;
  identische Wiederholungen bekommen denselben Ausführungsnachweis. Nach
  IDE-Absturz kontrolliert fortgesetzt; Fortschritt/Fehler inkrementell in
  setup/logs/uwa-motion-comparison-v4/summary.json. Vollständige Abnahme offen.
  Normale1ms/RTF1-Physik; RTF3-Versuch mit5ms-Schritt löste STATE STALE aus
  und wurde vor Fahrt verriegelt abgebrochen, alle Einstellungen restauriert.
  Temporäre Replay-Kamerarate0,2Hz wird per EXIT-Trap auf10Hz restauriert.
- Einzelarmfahrten unter stationären Hindernisarmen folgen vollständiger
  geprüfter Bahn mit gemessenem1mrad-Geometriekorridor; zeitlicher Lag separat
  erfasst. Mehrarmfahrten weiter mit unabhängigen Fortschrittsbarrieren.
  SIGTERM während Bewegung hinterließ bestätigte Holds+Latches:
  setup/logs/uwa-motion-signal-check.json. Keine automatische Wiederaufnahme.
- Auditkorrektur in Protokollv2: Paarlease im Supervisor begrenzt die Dauer
  einer alten geometrischen Freigabe anhand ihrer verbleibenden Abstandsreserve,
  statt stets400ms Heartbeat auszuschöpfen. Monotonzeit enthält Transportalter,
  20ms Pollintervall abgezogen. Protokollv2-Liveprüfung bestanden; zusätzlicher
  Test der besonders knappen Paarlease im Testfixture ergänzt, noch auszuführen.
  Ein früherer Live-Stoppversuch scheiterte an unerwartetem zusätzlichen Hold;
  Rohdaten erhalten, instrumentierter Wiederholungslaufv2 vollständig PASS.
- Gemeinsame Simulation einmal für Plugin-Erkennung neu gestartet; vorherige
  Gelenke gesichert und identisch zu den konfigurierten Anfangsstellungen.
  Reale Scan-/Kamera-/Treiberarbeit anderer Aufgabe erhalten.

## Vierarm-Scan und OAK-Update abgeschlossen, 2026-11-13

- Alle vier Arme haben ihre fünf geplanten Stellungen erreicht. Gültiger Index:
  `setup/digitization/four_arm_scan_20261113/scan_dataset.json` mit **25/25 Fotos**,
  20 Wrist-Ansichten und fünf OAK-Aufnahmen, 21 verschiedenen Kamerastandpunkten.
  Native 2592×1944 bzw. 8000×6000, feste Foki, Bildhashes, Sollpose und tatsächlicher
  Stillstand geprüft. Mindestens12Boardecken je Wrist-Bild,24in jedem OAK-Foto.
  Bildübersicht `scan_all_rounds.jpg`; metrische Rekonstruktionsgenauigkeit noch
  nicht ausgewertet. Keine Qualitätsflags früherer Fehlversuche umgeschrieben.
- OAK nach zunächst erfolgreichem Nutzerneustart erneut Pipeline-Startfehler.
  Nutzer hat darauf das angebotene OS-Update ausdrücklich mit „ja bitte“ erlaubt.
  Herstellerpaket erneut SHA256-/Identitäts-geprüft, exklusiver Kamerazugriff,
  OTA **1.32.1→1.47.0**, Agent **0.28.0**, gleicher OAK4-D R9/1479883285.
- Werkskalibrierung vor/nach Update exakt gleich: SHA256 a07141cce771738c713df4ef62f3719ed2ede411c556bc920089270cc4689eae.
  Produktiver SDK bleibt3.12.0; keine Kalibrierprofile/TFs oder Gazebo-Montagen
  verändert. Quellen/Paket/Updaterlog unter setup/oak4/stability_20261113/ota/.
- Nach OTA15direkt aufeinanderfolgende native8K-Start-/Fotozyklen bestanden:
  Fokus116, gleiche Geräte-ID, durchgehend steigende Gerätezeit, verschiedene
  vollständig dekodierte Bilder. Danach kompletter Fünfkamera-Bildsatz an den
  bereits erreichten Endstellungen mit unabhängigem Stillstandsaudit PASS.
  Insgesamt16nativeOAK-Aufnahmen nach Update erfolgreich. Das ist ein begrenzter
  Wiederholungsnachweis, keine Zusicherung dauerhafter Fehlerfreiheit.
- Letzte Gruppe ersetzt nur die zuvor fehlgeschlagene letzte Aufnahme. Initiale
  gültige Gruppe nach Nutzerneustart, Runde2–4 aus run03_rest, Runde5 aus
  last_round_post_os147. OAK-OS1.32.1 in Gruppen1–4,1.47.0 in Gruppe5 ist im Index
  ausdrücklich festgehalten. Statisches Board vor/nach OTA:24gemeinsame Ecken,
 0,52nativePixelRMS Bildverschiebung; enthält Detektions-/Licht-/Montageeinflüsse,
  keine neue Genauigkeitskalibrierung.
- Bewegungswächter, Kameraarbeit und read-only Stillstandsaufzeichnung sind
  getrennte Prozesse; Frische-/Driftgrenzen unverändert. Bildprozess verwendet
  zwei OpenCV-Threads, temporäres Planungsobjekt wird vor Fotos nicht gehalten.
 87gezielte Softwaretests vor OTA PASS; Firmware zusätzlich real wie oben geprüft.
- Während des letzten ursprünglichen Fotoversuchs wurden Telemetrielücken und
  ein2,18-s-PC-Treiberzyklus protokolliert; Stopp/Stillstand bestätigt. Diese
  Fehlversuche bleiben als Diagnose erhalten. Hostressourcen für spätere
  automatische Hardwarefahrten weiter beachten; Ursache nicht abschließend belegt.
- Während OTA und Nachprüfung **keine Arm-, Power-, Brake- oder Programmaktion**.
  Letzte reale Prüfung: alle vier RUNNING/NORMAL, Stillstand bestätigt,
  Fahrcontroller inaktiv. Linke External-Control-Programme bleiben STOPPED,
  rechte PLAYING; kein automatisches Rückfahrziel. Keine weitere Fahrt offen.
- Abschlussnachweis: setup/oak4/stability_20261113/ota/update_validation.json.
  Bedienung: docs/parallel_object_scan.md und OAK-Repo OAK4_STABILITY_2026-11-13.md.

## Schnellere HD-Fotos und nutzungsabhängige LEDs,2026-11-12

- Nutzerauftrag: HD-Aufnahme beschleunigen ohne wesentliche Qualitätseinbußen,
  Wrist-LEDs aller vier Arme nur während Foto-/Videonutzung. Andere Agenten
  parallel erhalten; keine Armfahrt oder Profiländerung aus dieser Arbeit.
- Doppelte nativeVGA-Rückschaltung entfernt, tatsächliches Originalformat/
  Pixelformat/Bildintervall nach Visionneustart unabhängig geprüft. Strenger
  expliziter Rückfall; vollständige Settings-/Sensor-/Watchdog-Prüfungen erhalten.
  Originalworker/-helfer für fremde eingefrorene Reihen unverändert.
- Bei identischem LED30%-Ablauf RF18,221→15,271s(−16,19%), CB3LF16,522→13,714s
  (−17,00%). RF je24Ecken, praktisch gleiche Schärfe/Clipping, mittlere Ecken
  RMS0,064px auseinander; Nutzer bestätigt statische Szene. Kein Genauigkeits-
  nachweis. RR-TestPASS,24,36s wegen vorhandener strenger Legacy-ROI-Korrektur.
- LED-Nutzung über gemeinsame Prozesssperren. Erster Nutzer an, letzter aus;
  Guardian `uwa-wrist-led-policy.service` installiert/aktiviert, Absturzbereinigung
  mit zwei echten Viewern geprüft: erster Crash bleibt an, letzter Crash aus,
  alle übrigen Settings identisch. CLI/GUI/HD/Kalibrierung/Drei-/Fünfkamera erfasst.
- Aktive Intensität standard30%, im Wrist-Fenster manuell änderbar, Leerlauf0.
  Manueller Setter2/Gettermode1 auf getestetenFirmwares: Bestätigung+Intensität
  statt falschem Enumvergleich. Gesonderter Managed-Restore-Shim. Keine Fokus- /
  Belichtungsänderung durch LED-Befehl. Fremde Pendant-/HTTP-Viewer melden keine
  Nutzung; für eigene Streams activity()-Kontext verwenden.
- AktivRF/RR/LF nach Abschluss ihrer Messreihen; nur ihre Kameradienste neu geladen.
  LR-Rollout bewusst nach eigener laufender Reihe: Job
  setup/wrist_lighting/pending/left_rear.json. Guardian wartet Abschlussstatus
  und freien Kameralock, ersetzt dann ausschließlich altenLR-Kameradienst durch
  uwa-wrist-hd-left-rear-managed.service und bestätigt LED0. Keine UR-/Motionaktion.
- Bau und45gezielte RegressionenPASS; reale Qt-Vorschau/LED-Knopf/Schließen
  sowie ROS-HD-Aufrufe LF13,57s/RR24,39s mit abschließendem LED0 bestanden.
  Wrist-Fenster --arm wählt alle vier IDs bei unverändertem StandardRR.
- [Bedienung/Prüfgrenzen](docs/wrist_speed_led_2026-11-12.md), Rohdaten
  setup/calibration/wrist_speed_led_20261112/, Test-/Buildlogs
  setup/logs/uwa-wrist-speed-led-*.log. Frühe verworfene LED-/Restoreversuche erhalten.

Stand der Zusammenfassung: **2026-11-12**, Zeitzone Australia/Perth.
Diese Datei fasst die bisherigen Gespräche und die überprüfte Implementierung
zusammen. Sie soll bei weiterer Arbeit mitgepflegt werden, nicht als unveränderlicher
Abschlussbericht dienen. Arbeitsregeln: [AGENTS.md](AGENTS.md); Bedienung: [README.md](README.md).

## Native HD-Intrinsics hinten links abgeschlossen,2026-11-12

- Nutzer beauftragt eigeneHD-Reihe nachLF-Ende und bestätigt konkreteVorschau:
  "Vorschau passt, Fahrbereich und Kabel frei – nach vorne links starten".
  NachLF41/41/Controllerinaktiv18:24:46 die gleichen40LR-Ziele mit echten
  Endstellungen erneut vollständig geprüft,Start18:29:18/Ende18:49:53AWST.
- **41/41 Bilder,PASS**,33Fit/8vorabPrüfung,20–24Ecken. Kamera06561F1400090106,
  native2592×1944/Fokus406Manual/33333/Gain16. AlleSensor-/Restoreprüfungen
  bestanden,123Burst-JPEGs gegenOriginal-SHA verifiziert. KeineBilderentfernt.
- **Empfohlen result_v2:Brown5/k3=0**,Fit0,3036px/Prüfmedian0,3177px/
  Prüfmaximum0,3925px. FreierOriginalfitv1 ebenfallsPASS,aber außerhalbder
  beobachtetenEcken nichtmonotoneRandextrapolation. Deshalb geringereModell-
  Ordnung aus denselbenFitbildern,unveränderteGrenzen/Prüfrollen;Originalv1
  erhalten. PositiverJacobi-GittercheckistkeinegemesseneRandgenauigkeit.
  Eckenhülle32,1%Bildfläche,keineabsolute3D-/Weltgenauigkeitbehaupten.
- Sitzung setup/calibration/hardware_handeye/left_rear_hd_20261112/,
  selected_result.json verweistaufv2/CameraInfo/Manifest/Kontaktbogen.
  NativeSafetyNORMAL,Remote/RUNNING,ros.urpPLAYING;LRControllerinaktiv
  direktnachgewiesen,JSBaktiv,KameraNormal/LED0,Endfehler0,0000099rad.
  Exec69707 beendet/Code0/Cleanup0,keineRückfahrt/keinSafetyreset.
- NativeKameraServiceuwa-left-rear-wrist-hd bleibtkamera-only/idle verfügbar,
  eigeneDomain73-Vorschaugeschlossen. AndereArme/Dienste/Treibererhalten.
- AnfänglicherSpawner-Namespace-/Parameterfehler vorAktivierung behoben;
  ersterStartvorFahrziel wegenfehlenderfrischerRR-Datenabgebrochen.
  Initialwartephase16s begrenzt,keineUnionalterSnapshots/keineGuardlockerung.
  13Sequenztests+9ExporttestsPASS. EingefroreneC-/Workerressourcen erhalten.
- Kein Hand-Auge-Fit oder globaleAktivierung;VGA406-/Hand-Auge-Profilbleibt.
  [Bericht](docs/left_rear_hd_intrinsics_2026-11-12.md),Arbeitsstand abgeschlossen.

## Native HD-Intrinsics hinten rechts abgeschlossen, 2026-11-12

- Nutzerfreigabe für genau die Domain72-Vorschau umgesetzt. Alle **41/41**
  Aufnahmen gespeichert, 33 Fit / 8 vorab ausgeschlossene Prüfung. Physische
  Kamera01D1111A00090912, native2592×1944, Fokus388 manuell,
  Belichtung63410/Gain19. Festes rechtes40mm-A3-Board unverändert laut Nutzer.
- **Intrinsics PASS**, unveränderte Qualitätsgrenzen: Fit0,7605px,
  Prüfmedian0,6742px, Prüfmaximum0,9219px. Fokale Fitunsicherheit0,496/0,396%.
  18–24Ecken jeBild; alle Sensorreadbacks,3unterschiedlichenBurstframes und
  vollständigeKamera-Restores bestätigt. Originale/Prüfrollen/Hashes auditiert.
- Sitzung setup/calibration/hardware_handeye/right_rear_hd_20261112/;
  unverändertesErgebnis/ROS-CameraInfo/Manifest/Bildübersicht in result_v1/.
  Boardeckenhülle34,9% derBildfläche, äußersteRänder nichtgleichvalidiert;
  Reprojektionsfehler keine absolute3D-/Welt-/Hand-Auge-Genauigkeit.
- Abgeschlossen18:01AWST. LetzterGelenkfehler0,000044rad, RR-Fahrcontroller
  nachweislichinaktiv (direkteListControllers),UR RUNNING/NORMAL/Remote.
  ros.urp bleibtPLAYING, keineRückfahrt/keinSafetyreset, fremdeDiensteerhalten.
  EigenerExec1925 beendet; Domain72-Vorschau bereitsgeschlossen. DiagonaleLF-
  Aufgabe darf ihren eigenenRestweg jetzt anhandrealerRR-Endpose neuprüfen.
- Kein Hand-Auge-Fit oder globaleAktivierung beauftragt; bestehendesRear-
  VGA404-/Hand-Auge-Profilunverändert. NeueHD388-K/D separatverwendbar.
- NativeAufnahmepfad mitSensorreadback,gebundenerVision-PID-Freigabe,
  begrenzterIO-/JPEG-Recovery und gemeinsamerRestore-Kamerasperre geprüft.
  FrüherActionClient vorMoveIt,proBatchwiederverwendet; nativeSafety/Guard/
  Cancel/Deaktivierungerhalten. 34Vorbereitungstests+7Offline-ExporttestsPASS.
- Freigabe/Fingerprint19d68cdeb45acc0a0f8278c494156bb780da0385309902e8d555f54d7770e651
  in operator_approval.json. VerworfeneVorbereitungsbilder/Fehllogs separat
  erhalten. SchnellerStatushelper hattefalschnegativeROSDiscovery;
  direkteControllerlistebestätigtTreiber/Inaktivität. Nachweise/Bedienung:
  [Bericht](docs/right_rear_hd_intrinsics_2026-11-12.md).

## Links vorne: native HD-Reihe abgeschlossen, 2026-11-12

- CB3 i686, Kamera `028E1F350009061C`, 41 native JPEGs mit 2592 × 1944;
  33 Fit / 8 unabhängige Prüfung, feste V4L2-Werte Fokus 245, 60.590 µs,
  Gain 19, Originalkameraeinstellungen nach jedem Burst verifiziert.
- Intrinsics **PASS**: medianer Prüf-RMS 0,336 px; Hand-Auge **FAIL**: 1,593 px
  bei Grenze 1,00 px. Boardstreuung 0,899 mm / 0,173°. HD-Basislage nur
  diagnostisch, 1,86 mm / 0,172° Abweichung von VGA, kein Profil aktiviert.
- Erster Abbruch: ROS-Stillstandsprüfung reagiert auf gestartete RR-Reihe.
  Nach RR-Ende dieselbe Reststrecke mit allen vier realen Zuständen geprüft.
  Zweiter Abbruch: External Control nach 56-ms-Überlauf getrennt, Safety
  NORMAL und geladenes `ros.urp` STOPPED; ROS-Play, neuer Live-Check, weiter.
  Nach lokalem Prozessende in erreichter Pose 037 dort stationär aufgenommen.
  Am Ende LF-Fahrcontroller inaktiv, External Control verbunden, keine Rückfahrt.
- [Bericht](docs/left_front_hd_calibration_2026-11-12.md), Sitzung unter
  `setup/calibration/hardware_handeye/left_front_hd_20261112/`.
  Kamera-Dienst: [wrist_hd_service.md](docs/wrist_hd_service.md).

## Links vorne: Kamera und relative Basislage kalibriert,2026-11-12

- Nutzer hat die vollständige Serie freigegeben. 40 weitere Bilder erfolgreich
  aufgenommen, insgesamt **41/41** unterschiedliche VGA-Ansichten mit jeweils
  24 Boardecken, 33 Fit / 8 Prüfung. Fokus 245 manuell, 60.590µs, Gain 19.
- Nach OAK-Profilwechsel v3 wurden die 3607 Punkte der unveränderten Nutzerwege
  erneut gegen alle vier Arme geprüft. Kinematik-Inhalte identisch, `sample_000`
  Flanschpose exakt gleich; neue Sitzung und Originalplan separat erhalten.
  Frühe Discovery-Abbrüche vor jedem Fahrziel. Erfolgreicher Lauf mit lokalem
  UDP-Messclient und gemeinsamer Einrichtung von Action und Telemetrie.
- **Intrinsics und Hand-Auge PASS:** mediane Prüf-Reprojektion 0,092px / 0,359px;
  Board-Translations-/Rotationsstreuung 0,543mm / 0,114°. Keine ausgeschlossenen
  Bilder, keine angenommene absolute Messgenauigkeit.
- Relative LF-Basis im LR-`base_link`: [13,92; 1414,32; 0,62]mm, XYZ-Winkel
  [−0,049; +0,124; +179,143]°, Abstand 1414,39mm. Linkes Board nach Nutzerangabe
  seit LR-Kalibrierung unverändert. Kein Weltanker/Profil aktiviert.
- Abschluss NORMAL, External Control verbunden, eigener Controller inaktiv,
  letzte Pose erreicht (0,000091rad), keine Rückfahrt. Nur eigene Vorschau beendet.
- [Bericht](docs/left_front_calibration_2026-11-12.md), Daten unter
  `setup/calibration/hardware_handeye/left_front_20261112/series_current_model_checked/`.


## Vorläufige OAK-Schätzung global übernommen,2026-11-12

- Nutzer akzeptiert nach erklärter5,85/7,40mm- und0,361/0,576°-Prüfkonsistenz
  die erste OAK↔Front-Wrist-Schätzung für erste Versuche und beauftragt Anwendung
  überall einschließlich digitaler Zelle/Gazebo/RViz. Neues Standardprofil
  **hardware_20261112_v3**, vorherigev1/v2 und alle Originalresultate erhalten.
- Profilkopie enthält relative Schätzung/Protokoll, gemessenen Front-q-Snapshot
  vor15:59:05, originale Factory-K/D, SHA-Referenzen und explizite pro-Artefakt-
  Nutzerannahme. passed:false/diagnostic_only:true des Ursprungs unverändert.
  Alte Roboterartefakte und Gelenkstartwerte bytegleich; keine Rear-HD-K erfinden.
- Ableitung: T_world_frontBase(nominal) @ FK_factory(q_measured) @ übernommenes
  T_tool0_frontOptical @ inverse(T_oak_front). Pose ca.[1,2203;0,0522;1,8578]m.
  Weltanker ausdrücklich weiterhin vorläufig, keine neue Tisch-/Basisvermessung.
  OAK raumfest eingefroren, folgt später verschobenen Tischen nicht automatisch.
- Gemeinsamer Description-Loader validiert Starrheit, komplette Ableitung,
  Kamera-/Referenzidentität, Hashes und konkrete Annahme. Sim-/View-Planung nutzt
  dieses Profil, vorhandene Planfingerprints müssen regulär neu geprüft werden.
  Nominalmodus weiterhin ausdrücklichladbar, keine alten Fingerprints ändern.
- Gazebo-Sensorpose/ROS-optical gleich; zusätzlich Referenzframe
  real_oak4_rgb_optical_frame inDomain64, kein echter LIVE-Streamnachweis.
  RViz-Gehäuse/Stativ/Frustum mit PRELIMINARY/USER ACCEPTED/Weltankerhinweis.
  overview.sh nutzt kalibriertes Standardlayout; neue Fotosessions speichern
  calibration_context.json. BestehendeFotos/Manifeste unverändert.
- Physische8K-K/D Rational14 bei116 vollständig archiviert/exportiert als
  oak4_camera_info.yaml. Jetty/Ogre2 meldet BrownDistortionModel unsupported.
  Deshalb simulierteOAK ehrlichPinhole mit skaliertenK/D=0; keine nichtgerenderte
  Verzeichnung als Bildgeometrie ausgeben. Brown5-Näherung nur archiviert für
  spätereRenderer, maxca6,32px/8K auf unabhängigem Prüfgitter. Reale Auswertung
  behält Rational14. Stativ wie bisher visual-only, kein neues Kollisionshindernis.
- Drei Pakete gebaut;40gezielte TestsPASS, einschließlichFK-/SDF-/Optikgleichheit,
  Weltfestigkeit beiTischbewegung, alteRoboterbytes, SHA-/Akzeptanz-/Matrixfehler,
  MoveIt/Overlay undFoto-/Auswertungsregressionen.
- DigitaleZelle über normalenApp-Launcher inDomain64/Partitionuwa_cell_sim
  geöffnet,Gazebo+RViz+Scan+rqt. Erster Kamerasensor beim frühen Szenenaufbau
  verloren, nurKamera neu geladen: Bildempfang wiederhergestellt, keineZell-
  oderRoboterzustände zurückgesetzt. KünftigerLaunch startet Overview erstnach
  Zellmodell-Spawn. Für ehrliche Pinhole-Metadaten nur verifiziertenOverview-PID
  22847 sauber mitSIGINT beendet und als eigener uwa-cell-overview gestartet.
- FinaleLiveprüfungPASS:4000×3000,2verschiedeneBildzeitstempel,D=[0,0,0,0,0],
  K passtFactoryskalierung, beideTFs exaktProfil, GazeboSceneSensorlinkpose
  stimmt, RVizMarkerabonnent nachgewiesen, Simuhr26,406sweiter, Gelenkeendlich,
  alle9Simulationscontrolleraktiv. KeineHardwaredienste/Power/Play/Armfahrt.
- Nachweise setup/calibration/three_camera_evaluation_20261112/adoption-live/
  {report.json,simulated-overview.jpg}, Logs setup/logs/uwa-oak-profile-adoption-*
  (frühereFehlversuchebehalten). Beschreibung docs/oak_preliminary_adoption_2026-11-12.md.

## Links vorne: erste Boardaufnahme erfolgreich,2026-11-12

- Nutzer hat den nach Absturz neu geprüften 53-Sekunden-Weg freigegeben. Der
  UR5 vorne links hat ihn erfolgreich ausgeführt (Result 0, Endfehler 0,0000623 rad).
  Andere Arme wurden nur beobachtet; keine Rückfahrt. Der eigene Trajektorien-
  controller wurde nach der Aufnahme wieder deaktiviert.
- Zwei frühere Versuche endeten vor einem Fahrziel: fehlender Controller und
  zu kurze Action-Discovery. Korrekte LF-Parameter im passenden Namensraum
  gesetzt; Laden und Konfigurieren über getrennte ROS-Dienste, anschließend
  Action-Discovery vor der Aktivierung. Keine Treiber oder Sicherheitsfunktionen
  geändert. Die Ausführung nutzte weiterhin native Safety, External Control
  und frische Zustände aller vier Arme.
- `sample_000` akzeptiert: 640×480, 24 ChArUco-Ecken, drei unterschiedliche
  HTTP-Frames im überwachten Stillstand. Eigener Fokus 245 manuell, Belichtung
  60.590 µs manuell, Gain 19. Originaleinstellungen und Diagnosebilder erhalten.
- 40 zusätzliche Ansichten mit allen vier Armen als Hindernisse und ohne
  diagonale Ausnahme geplant. Zusammen mit sample_000: 33 Fit- und
  8 unabhängige Prüfansichten. Reine Bewegung 354.6s,
  zusätzlich Stillstand und Aufnahme. Vollständiger Check-only bestanden;
  keine Serienfahrt ausgelöst. Fingerprint `a23608cb8cccf2c7ddf1c806451eb8de6f364df601a9368d3886fbdc74915d3b`.
- Messung, Diagnosen und Pläne unter
  `setup/calibration/hardware_handeye/left_front_20261112/`. RViz-Vorschau der
  Serie getrennt von Hardware. Nächster Schritt: Freigabe des neuen Wegs.
  Die relative LF-Basislage wird erst nach bestandenem Fit über das gemeinsame
  feste linke Board und die validierte LR-Referenz bestimmt. Keine globale Pose
  und kein Kalibrierprofil aktiviert.


## Sechs mobile Drei-Kamera-Fotosets offline ausgewertet,2026-11-12

- Nutzer bittet um Einschätzung seiner bisherigen Fotos, nach PC-Absturz
  fortgesetzt. Nur lokale Dateien verwendet, keine Kamera-/ROS-Dienststarts,
  keine Roboterkommandos und kein aktives Kalibrierprofil geändert. Parallel
  laufende LinksFront-Vorbereitung unverändert erhalten.
- Benutzer-Session three_camera_mobile/20261112_155233_897f400a enthält6Sets/
  18nativeOriginale. Alle Bild-SHA256 stimmen mit den Manifesten überein.
  5Sets haben >=12Ecken in allen3Kameras,3Sets alle72Ecken. ErsteTeilansicht
  15:57:44 separatdiagnostisch; kein nachträgliches Entfernen nach Fitfehler.
- Feste Rollen vor Posenfit gespeichert:15:59:05/16:03:42/16:11:47 Training,
  16:12:46/16:14:34 unabhängige Prüfung. Front-HD435 mit ausdrücklich bereits
  akzeptiertem Untergrenzenprofil und OAK-Factory8K/Fokus116 festgehalten.
  Keine hochskalierte Rear-VGA-Matrix: Rear-HD388 weiter ungeprüft, kein Fit.
- Neuer reinlokaler Python-Modul board_photo_evaluation: PnP-Initialisierung
  jeBild ohneNominal-/GT-Posen, gemeinsamer robuster relativer OAK↔Front-Fit
  mit brennweitennormierten Bildresiduen. Resultat ausdrücklich diagnostisch,
  passed:false,calibration_applied:false; keinTF/keineWelt-/Tischkalibrierung.
- Zwei Prüfansichten: Unterschiede unabhängiger relativer PnP-Pose zum Fit
  5,85/7,40mm und0,361/0,576°. OAK-Kreuzprojektions-RMS10,29/6,53px,
  Front8,00/1,28px. Interne Konsistenz, keine vermessene Hardwaregenauigkeit.
- Zusätzlich erste/letzte native Burstbilder neu detektiert: mediane
  Eckenverschiebung0,056–0,157px, Maximum0,456px über ca.0,13s. Kein auffälliger
  Kurzzeitbewegungshinweis, kein Synchronitäts-/Dauerstillstandsnachweis.
  Gelenk-Endpunkte proSetmax0,000105rad auseinander. Optik-Readbacks sind
  kein zusätzlicher Sensor-Fokusnachweis während nativem Burst.
- Fünf gute Boardnormalen ca.26,2° gespreizt, Boardmittenbereich22×16×12cm
  im vorläufigen OAK-Frame. Sichtfeldabdeckung weiterhin begrenzt, vor allem
  OAK. Mehr verschieden geneigte/verschobene/entfernte Ansichten sinnvoll,
  etwa15–20zusätzliche als praktischer Zielwert; keine Garantie durch Anzahl.
- Ergebnisse setup/calibration/three_camera_evaluation_20261112/diagnostic_v1/
  (protocol/result/image-audit.json,coverage.png),all_sets.jpg im Elternordner.
  Bericht docs/three_camera_photo_evaluation_2026-11-12.md; 5synthetischeTests
  PASS für Transformationsrichtung, unabhängige Prüfung, Geometrie-/Hashfehler.

## Links vorne: Kamera-/Basis-Kalibrierung vorbereitet,2026-11-12

- Nach PC-Absturz und Neustart16:17: alle vier URs RUNNING/NORMAL, ros.urp STOPPED.
  Vier flüchtige ROS-Hardwaretreiber mit inaktiven Bewegungscontrollern neu gestartet.
  Nach längerem DDS-Einlesen echte Gelenkstellungen aller vier Arme verfügbar.
  Aktueller Plan `preparation/first_view_rechecked/plan.json`: 53.0s,
  532 Kollisionssamples, voller Check-only bestanden.
  Fingerprint `9ad63ff3dd6c4da5fc9cf8666ec77fa6457b8d399179b7da5e1002a4379ecff0`; alte Vor-Absturz-Pläne nicht ausführen.
  Eigene Vorschau auf Domain68 wieder geöffnet. Vor realer erster Fahrt fehlen
  erneutes External Control links vorne und konkrete Freigabe des gezeigten Wegs.
  Keine Fahr-/Power-/Brake-/Play-Befehle gesendet.

- NeuerNutzerauftrag: Position undKamera des jetztROS-erreichbarenUR5links vorne
  kalibrieren. Nutzerbestätigt linkes40mm-A3-Board seitLeftRear-Kalibrierung
  unverändertbefestigt. DamitspäterLF-Basis relativLR aus gemeinsamemT_base_board
  bestimmbar; keineabsoluteWelt-/Tischanker-Vermessung darausbehaupten.
- KameraHTTP640×480funktioniert,StatusNormal. Erstbildstarküberbelichtet,kein
  Board/keineBewegung. Kamera-only-AE-Trigger liefertbrauchbaresaktuellesBild
  vomBoden/Pendant. Triggerstellt exposureAuto vontrueauffalse; Originalsettings
  gesichertundvorFahrtfreigabewiederzurückgeschrieben,Readbackprotokolliert.
- NativeHD-Probe vorModuswechselgestoppt: alterCB3 i686/32bit hat kein gcc/cc,
  vorhandenerNativeCapture.bootstrap kannC-Helfernichtbauen. KeinKamera-/UR-
  Dienst/OSupdate,keinKalibrierfit;VGA-Pfadfunktioniert. KompatiblerHD-Helfer
  bleibtbeiBedarfvorzubereiten,kein2592×1944-Erfolg fürLF behauptet.
- KonkretererstergerechneterWeg53,0s/531Kollisionssamples,max0,005radSampling,
 0,05rad/s/0,10rad/s². Alle4Armefrischliveerfasst,volleMoveIt-ZellemitLF-
  Werkskinematik,keineDiagonal-Ausnahme. Zielkamera nominell[-.45,-.28,1.453]m.
  park_arm execute --check-only PASS,keinFahrzielgesendet.
- Artefakte setup/calibration/hardware_handeye/left_front_20261112/preparation/,
  first_view/plan.json Fingerprint4c734fab2a835ba373d04acb71a1af748a66c8ac4dc14d4f0bae5fbe9ee7f456.
  EigeneDomain68-RViz-Animationuwa-left-front-calibration-preview geöffnet.
  ErsteFahrt wartetzurSichtprüfung aufkonkreteFreigabe. AndereArme/KameraGUI
  undbestehendeKalibrierprofileerhalten;keineAufnahmefolge/Fit/Aktivierung.


## Links vorne: External-Control-Verbindung bestätigt,2026-11-12

- Nutzer startetros.urp amUR5. JetztDashboardPLAYING/running:true,RobotmodeRUNNING,
  SafetymodeNORMAL. ROSrobot_program_running=true,Hardwareactive,frische6Gelenke
  rund123Hz im10s-Prüffenster(1230Samples,max331msHostlücke).
- KonkreteReverse-Verbindung192.168.8.209:51001↔192.168.8.2 aufgebaut;Trajectory-
  undCommandkanal51003/51004ebenfallsESTAB. NativeTreibermeldung15:54:46:
  Robot connected to reverse interface. Ready to receive control commands.
- ImProgrammstartfenster15:54:37ersteVerbindung/15:54:43Drop/15:54:46Neuaufbau;
  Benutzerstartphase,nichtalsbewiesenerunerklärterDauerausfallausgeben. Bei
  nachfolgendenChecks keinneuerAbbruchgesehen,keinLangzeitnachweis.
- Alle9ControllerunabhängigperROSListControllersnachgewiesen:5Broadcasteractive,
 4Motioncontrollerinactive. ErsterasynchronerListencheckliefertebinnen10skeine
  Antwort;separaterCLI-Serviceaufruferfolgreich. FollowJointTrajectory-Schnitt-
  stellenbeiderTrajektoriencontroller vorhanden. KeineControlleraktivierung,
  keinFahrziel/Power/Brake/Play/SafetyresetdurchdiesenCheck.
- Ergebnis: **ROS-Steuerverbindung bereit**,tatsächlicheTrajektorienausführung
  nochnichtgetestet. FrühereRTDE-BlockadedurchEtherNet/IP-Deaktivierungbehoben.
  Quelle `setup/logs/left-front-ros-readiness-20261112/external-control-155746/`.


## Links vorne: RTDE-Blockade nach EtherNet/IP-Aus behoben,2026-11-12

- Nutzer meldet EtherNet/IP deaktiviert/Installation gespeichert. Nur eigenen
  uwa-left-front-hardware-driver neu gestartet. Laufzeit-KillSignal konnte per
  systemctlset-propertynichtgeändertwerden;normalerNeustart dennochsoforterfolgreich,
  keineSource-/Servicekonfiguration dafür verändert.
- UR5/Serial2017356443/PolyScope3.15.8.106339: Hardware **active**,RTDE125Hz,
  Werkskinematikcheck erfolgreich; speed_slider_mask-Konflikt nichtmehrvorhanden.
  Alle5Broadcaster aktiv,4Motioncontroller ordnungsgemäß geladen/inactive.
  Reverse/Script/Trajectory/Command-Listener51001–51004 offen.
- ROS-Stabilitätsprobe20s:2320gültige6-Gelenk-Samples,124,95Hz innerhalbempfangener
  Zeitspanne,max334,5msLücke,Streuungmax0,000144rad. Keinefehlenden/nichtendlichen
  Gelenkwerte;keinenBewegungs-/Langzeitrobustheitsnachweis darausableiten.
- Historisch vor manuellem Programmstart: NativeRUNNING/NORMAL,ros.urp geladen,
  aber **STOPPED**;nochkeineReverse-
  Verbindung undkeinBewegungstest. Nutzergebeten,ExternalControl ros.urp am
  Pendant laufenlassen(Host192.168.8.209/Port51002),danachSteuerverbindungprüfen.
  KeinePower/Brake/Play/Fahrziele/Safetyquittierung durchdiesenCheck.
- Nachweise `setup/logs/left-front-ros-readiness-20261112/ethernetip-off-155447/`.
  Andere3Roboter-,Kamera-/RVizdiensteerhalten;paralleleDrei-Kamera-Arbeitunverändert.


## Historisch: Links vorne vor EtherNet/IP-Deaktivierung,2026-11-12

- Nachtrag vom Nutzer: **EtherNet/IP am linken vorderen UR5 ist aktiviert**.
  Damit konkrete, zur RTDE-IN_USE-Meldung passende Feldbuskonfiguration bestätigt;
  tatsächlicher Registerbesitz noch nicht separat ausgelesen. Nutzer gebeten,
  EtherNet/IP bei fehlender SPS-Nutzung zu deaktivieren und Installation zu
  speichern. Später vom Nutzer deaktiviert; positiver neuer ROS-Check im aktuellen Abschnitt oben.

- Nutzer bittet zuprüfen,obUR5links vorne inzwischen perROS steuerbar ist.
  Identität192.168.8.2/Serial2017356443 bestätigt; PolyScope3.15.8.106339 im
  Inventar aktualisiert. NativeRUNNING/NORMAL,ros.urp geladen,aberSTOPPED.
- AlteFehlinitialisierung des eigenen uwa-left-front-hardware-driver bestätigt;
  gezielterNeustart. AlterDienst brauchte90sSystemd-Stopp,letzterRSP perTimeout
  beendet; fremdeDiensteunverändert. NeuerStart erneutdreimal RTDE-IN_USE:
  speed_slider_mask vonanderemClient/Feldbusbelegt. Hardwareunconfigured,
  keinJointState/Broadcaster,keineMotioncontroller/Reverse-/Scriptlistener.
- Lokalkein konkurrierenderTCP-Client nach192.168.8.2:30004 gesehen. Tatsächlicher
  Besitzer nichtbewiesen; Nutzer perFrage umEtherNet/IP-/PROFINET-Status gebeten.
  KeineFeldbus-/Safety-/Inputrecipeänderung,keinePower/Brake/Play/Fahrziele.
- Output-only-Gegentest mit vorhandenemReadOnlyStream ohneInputrecipe/Writer:
 71Samples/7s,6echteWinkel,qd0,Robotmode7/Safetymode1. SomitlesbareNetzwerk-
  telemetrie; ROS-Steuerfähigkeit aktuellweiterverneint,keinBewegungstest.
- Diagnose/JSONs/neuerStartlog/ReadOnlyNachweis unter
  `setup/logs/left-front-ros-readiness-20261112/153340/`.
  NachBeseitigungInputbesitz Treibererneutinitialisieren,danachExternalControl
  prüfen. EinSTOPPEDProgramm allein erklärtkeinenRTDE-IN_USE-Konflikt.


## Drei-Kamera-GUI für mobiles A4-Board,2026-11-12

- Nutzer bestätigt mobilesA4-Board IDs75–91 für beide rechtenWristkameras und
  OAK. NeueenglischeApp **UWA Camera Capture**, StartmenüeintragundLauncher
  `scripts/camera_capture.sh`; Bedienung `docs/three_camera_capture.md`.
- Readinesslesend: beideRechtsarme aktuelleJointStates, SafetyNORMAL,
  External-Control verbunden, Bewegungscontrollerinaktiv. KeineArmfahrt,
  Power-/Bremsen-/Programmaktion. ParallelaufgabeLinksFront unverändertlassen.
- DreiVorschauen mitMarker-/Eckenzahl,Empfangsalter,STALE/PAUSED/SNAPSHOT.
  Sichtbarkeitsbanner >=4Previewecken jeKamera; dasistkeineKalibriergüte.
  Capture-All-Button mitRECEIVED/RUNNING/DONE/FAILED undLaufzeit. Native
  Wrist2592×1944 + OAK8000×6000 Einzelbild übervorhandeneFotopfade; Quick
  optionalWristVGA. Originale,Annotationen,metrischeBoardkorrespondenzen,
  physischeKameraID/Fokus,Readback,Hash undZeitfenster jeunveränderlichemSet.
- Fokusprofil config/three_camera_capture.yaml: RF435,RR388,OAK116manual.
  Wristoriginale vorhergesichert,beiFensterschließen strengwiederhergestellt.
  RR-HD388 hatnochkeinevalidiertenIntrinsics; VGA-/HD-/Fokusprofilenichtmischen.
  KeineFits/Kalibrieraktivierung. Hostzeiten sindkeineBelichtungszeiten;
  BoardbisDONEstillhalten,keineHardware-Synchronisierungbehaupten.
- OAKVorschau2000×1500/2fps,voller4:3-Bildausschnitt,5sAE-Einlauf. VorFoto
  nurdieseSDK-Pipelinebeenden,Dateisperrfreigabeabwarten: oakctl-Wrapper kann
  vorherenden. PausegibtOAKfürTiefentoolfrei,keinefremdenDiensteabgeschossen.
- LegacyUCC1.11.1-Restore imvorhandenenWristworkerrepariert: ROI-Korrektur
  nachgemessenerAbweichung,begrenzteIterationen/Koordinaten,temporärerAFbei
  manuellemROI nötig,LegacyLEDmapping; amEndealleOriginalkonfigfelder exakt
  (automatischeAusgabefelder nurbeiaktivemAutomatikmodusausgenommen).
  RealAF-/ManualnativePASS; frühereFehlberichtebleibenunverändert. Erste
  überbelichteteRear-HTTP-Aufnahme durchneuenBelichtungstriggerkorrigiert.
- ErstesnativeDreierset
  `setup/calibration/three_camera_20261112/first_sets/20261112_154033_06fc8276/set_154037_784566/`:
  OAK24/RR24/RF8von24Ecken. VorneBoardobenabgeschnitten; Bildergesichert,
  Setabsichtlichall_usable=false. MobilesBoardinFrontbildmitteausrichten;
  keinezusätzlicheArmbewegung beauftragtoder ausgeführt.
- EchterGUI-AbnahmelaufPASS:
  `setup/calibration/three_camera_20261112/gui_check/20261112_154921_20ecc2ad/gui-check.json`.
  DreiaktuelleVorschauen,Buttonklick+nativesDreierset,Live-Rückkehr,
  PausemitnachgewiesenerDateisperrfreigabe,Originalfokus-RestorePASS.
  Screenshotslive-before/after.png; erneutRF8/RR24/OAK24nativeEcken.
  FrüherefehlgeschlageneAbnahmeläufenichtgelöscht (Freigaberaceaufgedeckt).
- ZusätzlichlesendeDomain66-Telemetrie vor/nachneuenFotosets gespeichert,
  fehlendeSamplesexplizitmarkiert; EndpointdifferenzistkeinDurchgehend-
  Stillstandsnachweis. LiveProbe beiderRechtsarmePASS unter
  setup/calibration/three_camera_20261112/telemetry-check/. KeineROS-Writer.
- Build uwa_cell_control PASS,30gezielteTestsPASS (Detektionsidentität,
  Teilansicht,Datenfehler,Setfehler,SDK-Sperrrace,QtKlick/STALE/Snapshot,
  vollständigerLegacyRestore undbestehendeOAK-Transaktionsgrenzen).
- InstallierterStartmenüeintrag tatsächlichpergioinpersistenterBenutzersitzung
  geöffnet: temporärerDienst uwa-camera-capture (ExitType=cgroup), Session
  setup/calibration/three_camera_mobile/20261112_155233_897f400a/.
  GUI-/SDK-Prozesse aktiv,frische2000×1500-Frames,Fokus116readbackbestätigt.
  BeimnormalenFensterschließenwirdOriginalfokuswiederhergestellt. Laufende
  PreviewbelegtOAKexklusiv; fürTiefen-/andereFotoaufträge **Pause live view**.

## HQ-Tiefenaufnahme als RViz-Punktwolke,2026-11-12

- Nutzer bittet nach HQ-Tiefenmodus um sichtbare RViz-Anzeige. Vorhandene
  Domain70-Designvorschau erhalten; eigene Domain65-Snapshotansicht geöffnet.
- CLI `bash src/oak_camera_calibration/tools/oak4_photo.sh view-depth`, optional
  --capture DIR. OAK-Tools oak4_depth_rviz.py/geometry.py, keine ROS-Neubaupflicht.
  HQ standardmäßig aktiv, Standardwolke optional, klarer STATIC-/Datumshinweis.
- Frische nativeHQ-Aufnahme: setup/oak4/depth/20261112-145646-depth_hq-437c09ec/.
  Worker speichert jetzt tatsächliche rektifizierte Frame-K/Größe und Referenz-
  extrinsics in Metern. K fx=fy800.60913,cx637.89282,cy398.7670 für1280×800.
  Keine unrektifizierteFactory-K als Ausgabe-K verwendet; alte Aufnahmen ohne
  projection für3D abgewiesen. SDK-Metadatenquelle im JSON protokolliert.
- Kamera-lokale PointCloud2,273323HQ-/429717Standardpunkte, EinheitenMeter;
  TF nur oak4_snapshot_view→oak4_snapshot_rectified_right_optical. Kein world-
  TF/kein global aktiviertes Kalibrierprofil, keine angenommene Weltregistrierung.
- Geöffnet per temporäremBenutzerdienst uwa-oak4-depth-rviz; Config/Quelle/Counts
  unter setup/oak4/rviz/. ROS-Empfang mit endlichen Punkten/korrektemPayload/TF,
  RViz-Abonnent und GUI GlobalStatusOk nachgewiesen.17TestsPASS, neue bekannte
  Pixelprojektion/mm→m/Nullwert-/Kalibrierfehlerprüfungen enthalten.
- Rendererbilder perDesktop-/RViz-Qt-Grab unterWayland nicht zuverlässig prüfbar
  (schwarz); deshalb kein visueller Screenshot-Nachweis behauptet. Punkte-
  empfang/GUIstatus sind unabhängig geprüft. Keine fremdenDienste/Roboter geändert.


## Statischer HQ-Tiefendienst ergänzt,2026-11-12

- Nutzer fragt nach ähnlichem HQ-Verfahren für Tiefe. Bestehenden Fotodienst
  erweitert, keine separate permanente Kamera-Pipeline. Neue Trigger-Services
  `/oak4/depth/capture_{hq,standard,compare}` und `/oak4/depth/status`, Domain65.
  CLI über oak4_photo.sh capture --mode depth_hq (Standard16Frames).
- Native1280×800-Stereo/FAST_ACCURACY/SoftwareLR,10fps; Mono-AE nach Einlauf
  sperren. Keine räumlichen/historischen Softwarefilter, stattdessen zeitlicher
  Median gültiger Werte, mindestens75% Support/Inlier und MAD-Grenze
  max10mm/1%Tiefe. Instabile Werte0, keine Lochfüllung. Keine ISO100-Behauptung.
- Worker/Fusion im OAK-Repo tools/oak4_depth_{capture,fusion}.py, Anleitung
  OAK4_DEPTH.md. Rohframes/Count-/Inlier-/MAD-/Maskenkarten,16bit-mm-PNGs und
  Factorybackup unter setup/oak4/depth/. Gleiche Thread-/Dateisperre wie RGB.
- Installierten Vergleichsservice real PASS geprüft, native1280×800,uint16,
 16Frames57–72/1,500s: setup/oak4/depth/20261112-144815-depth_compare-97e070f4/.
  Standard41,67% gültig, HQ26,87% nach konservativer Aussonderung. Akzeptierter
  medianer zeitlicherMAD3mm; kein absoluterGenauigkeitsnachweis. AndereArm-
  arbeit parallel; kein garantierterStillstand/Kamera-Roboter-Zeitsync.
- Regulärer HQ-Endpunkt ebenfalls real PASS: setup/oak4/depth/20261112-145220-depth_hq-29c6117c/.
  Status CAPTURING währendAufnahme, parallelesRGB abgewiesen,danachREADY.
  14automatisierteTestsPASS; intakte16bit-PNGs/NPZ und Supportmasken geprüft.
- Mono links3000µs/ISO188,rechts3135µs/ISO200 währendBurst konstant. Kein
  Firmware-/Flash-/Kalibrierprofil-/Roboterkommando. Foto-/Tiefenaufträge exklusiv.
  Neue Tests für Fusion/ungültigeDaten/Bewegungskanten; bestehende Foto-Sperr-
  Fehler-/Timeouttests erhalten. Agentenhinweise/README in beiden Repos ergänzt.


## Gemeinsame Sichtstellungen real abgeschlossen,2026-11-12

- Nutzer stellt LinksFront vorerst zurück. **NurLR→RR→RF** nacheinander in
  unveränderte vorgeschlagene Ziele gefahren, danachnative2592×1944-Fotos.
  LinksFront bekommtkeinZiel; echteWinkelalsHindernisfortlaufendoutput-onlyRTDE
  überwacht(keineInputs/Writer/URScript),keineerfundeneNull-/Home-Stellung.
- Alle3Ziele erreicht; Abschluss größteGelenkfehler LR2,78e-5/RR4,56e-5/
  RF2,82e-5rad. SafetyNORMAL,alleMotioncontrollerinaktiv,keineRückfahrt.
  NativeIstwinkel/Werkskinematik/volleMoveIt-Zelle,keineDiagonal-Ausnahmen.
- ErsteRR-Fahrt wegenLF-Datenlücke gecancelt/deaktiviert. 25s/258Pakete danach
  stabil(max101msLücke),Restwege frischgeprüft,LRalsalreadyAtTargetübersprungen.
  ReaderverkraftetNichtdaten-/Reconnectpakete,0,5s-Frischeguardunverändert.
  KeinSchutzreset;UrsacheerstemAussetzernichtabschließendbelegt.
- Alle3Wrist-Fotos je24Ecken,NativeJPEGsundÜbersicht unter
  setup/calibration/shared_views_20261112/photos/. LR/RF-DienstaufnahmenPASS
  nachfrischemTelemetrieeinlesennachblockierendemHTTP. RRNativeBildvorhanden,
  DienstRestorefehlgeschlagen(ROI): ausdrücklichdiagnostisch/keineFitbeobachtung.
- RR-Konfiguration anschließendaufursprünglicheWertezurückgeführt: gemessenen
 16pxY-Schreiboffset undLegacyLED-Codierung kompensiert; tatsächlicherReadback
  allerKonfigurationsfelderidentisch,Normal. AlteFehlberichteunverändert,
  automatischerLegacyDienstdamitnichtallgemeinalsrepariertausgeben.
- NeuesOAK-HQ-FotoalsGegensicht:alle3Boards gleichzeitigje17Marker/24Ecken.
  Original setup/oak4/photos/20261112-150024-hq-6a5b0dea/,Annotation/Detektion
  .../shared_views_20261112/oak_post_motion/. KeineOAK-Extrinsicsneuaktiviert.
- Schlüsselzugangaufallen4URsfrischverifiziert: drei e-SerieEd25519,CB3LF
  eigenerRSA3072wegenOpenSSH6.0,LegacySignaturnurfürdiesenHost. FremdeKeys
  erhalten;ZugriffnurPC209,keineWeiterleitungen/PTY. PrivateKeys/Hostvertrauen
  unter~/.ssh,keinePasswörtergespeichert;Backendreconnectautomatisch.12TestsPASS.
- LF192.168.8.2/UR5/Serial2017356443,WerkskinematikimInventar. Benutzerhat
  inzwischenPolyScope3.15.8/ros.urp eingerichtet; nativeSteueranbindungnoch
  prüfen. EigenerFehlstartDienstuwa-left-front-hardware-driver:Inputbesitz
  speed_slider_maskwarblockiert,keineLF-Motioncontrolleraktivierung. Ursprünglich
  Power-on fürIstwinkelohneBrake/Play;späteresRUNNINGvomNutzer,keineeigeneLF-Fahrt.
- Bericht [reale Sichtstellungen](docs/shared_view_hardware_2026-11-12.md),
  Arbeitsstatus work/shared-view-hardware-captures.md abgeschlossen; Ergebnis
  summary.json/manifest.json. Profile/Weltankerunverändert,keinAuto-Rückweg.

## Wiederverwendbarer OAK4-Fotodienst,2026-11-12

- Nutzer beauftragt nach erfolgreichem Standard/HQ-Vergleich dauerhafte Ablage
  als Service und sichtbare Dokumentation für spätere Agenten.
- Implementierung im OAK-Repo `tools/oak4_photo{.sh,_service.py,_capture.py}`,
  Anleitung `OAK4_PHOTOS.md`. CLI ohne ROS, Trigger-Services unter `/oak4/photo/`
  (capture_hq/capture_standard/capture_compare/status), Domain65/LOCALHOST.
- Installiert/aktiviert: systemd-user `uwa-oak4-photo.service`; idle ohne Kamera.
  Bestehende isolierte Laufzeit `.venvs/oak4` (DepthAI3.12) und oakctl verwendet;
  Inventar-IP/Geräte-ID zentral aus Zellrepo, keine temporären Chatabhängigkeiten.
- HQ ISO100, max90ms, acht echte48MP-Frames mit konstantemFokus/WB, nativePNG.
  Sensor10fps, nur angeforderte Vollbilder übertragen. Keine Rohsensor-/HDR-
  Aufnahme, keine Bewegungskompensation oder automatische Roboterfahrt.
  Exklusiver SDK-Zugriff, kein automatisches Stoppen fremder Kameradienste.
- Reale Serviceprobe PASS: setup/oak4/photos/20261112-135950-compare-cf3a4ee9/,
  drei intakte8000×6000-PNGs, StandardISO309/16,666ms, HQISO100/51,498ms,
  Fokus107/WB4138K, achtverschiedeneFrames. Status währenddessen erreichbar,
  zweiteAufnahme abgewiesen, danachREADY. Sechs Fehler-/Sperr-/TimeouttestsPASS.
- Finale reguläre HQ-Serviceprobe nach dem letzten Dienstupdate ebenfalls PASS:
  setup/oak4/photos/20261112-140403-hq-f3cec77a/, ISO100, acht unterschiedliche
  native48MP-Frames, exposure_limited=false. Benutzerdienst aktiv und enabled.
- Agentenhinweise/README in beiden Repos und Workspace-Einstieg ergänzt.
  Ergebnisse dauerhaft in setup/oak4/photos/; keine Bilddateien im Git.


## Grobe OAK-Pose und Beobachtungsstellungen,2026-11-12

- Nutzer bittet um grobe OAK-Pose relativ rechtemTisch sowie UR-Stellungen mit
  freier Tisch-/gemeinsamerOAK-Wrist-Sicht. Keine neue realeFahrt ausgeführt.
- EEPROM-K/D derOAK238 reinlesend,8K-Bildecken beiderTischboards perIPPE/LM
  ausgewertet. Relativ angenommenerrechterTischplattenmitte **[+0,806;+0,025;
  +0,958]m**,33,54°nachunten; bei0,90m Tischhöhe etwa1,858mBodenhöhe.
  LinkesBoard unabhängig0,960m/33,58°. Boardabstand0,959m statt0,90mNominal:
  Tischbewegung/Boardlage noch nicht trennbar, keine Welt-/Basisanker verschieben.
- Einbild-/Factory-Intrinsics-Schätzung mit unbekanntemFoto-AF-Wert, keine endgültige
  OAK-Kalibrierung. Eigenes experimentellesDesignprofil ohne globaleAktivierung:
  config/view_designs/oak_shared_views_20261112.yaml. Aktuellesparallelübernommenes
  hardware_20261112_v2 unverändert benutzt, Front-Qualitätskennzeichnung erhalten.
- Vierarm-Zielkonfiguration kollisionsfrei, jeWrist24Board-Ecken, OAK48Ecken.
  KonservativeMesh-Box-Sichtschätzung freieGesamttischfläche54%→78%; keine
  echtePixel-Messung. GemeinsamfreieTischflächen ungefähr0,59/0,70/0,97/0,77m².
  HorizontalesmobilesA4-Muster passt vollständig in beideKameras bei
 11/28/39/28 der54geprüftenPlatzierungen jeArm(LF/LR/RF/RR).
- Serielle reineModellwege LF→LR→RR→RF mit368s/3685Samples vollständig geprüft;
  echteAusführung bleibt false(linksFront nurNutzer-Home,provisorischeMontagen).
  Keine zusätzlichenWrist2-Umdrehungen, Wrist3-Änderungmax90° alsSuchpräferenz.
- StatischeRViz-Vorschau aufDomain70 geöffnet(28Gelenke/9Marker gelesen), ohne
  Hardwareclients oderTF-/Joint-Kommandobrücke. FünfGeometrietestsPASS.
  Vergleichsbild undlokaleYAML/Posen/Hashnachweise unter
  setup/calibration/oak_pose_20261112/design_wrist/; Geometrie-/Wegprüfung und
  Grenzen in [Bericht](docs/oak_pose_and_shared_views_2026-11-12.md).

## Aktuell: Front-HD übernommen und weitere HD-Kameras geprüft, 2026-11-12

- Nach Erklärung der Qualitätsabweichungen ausdrücklicher Nutzerauftrag:
  Front-HD-Daten übernehmen. Neues Standardprofil **hardware_20261112_v2**,
  baut aufv1 auf; beide validiertenRear-Optiken und Werkskinematiken unverändert.
  Front-Intrinsics2592×1944/Fokus435Manual und Hand-Auge übernommen mit
  `operator_accepted_below_threshold`; ursprüngliche `passed:false` bleiben.
  Nutzerentscheidung pro Artefakt anSHA256/Qualitätsbericht gebunden; keine
  Grenzwerte geändert. Ohne diese konkrete Ausnahme weiterhin strenge Ablehnung.
- Standardloader und generierteFront-Optikmatrix geprüft; keine Welt-/Basen-
  verlegung, keine Arm-/Dashboardbefehle, keine Hardware-/Gazebo-Neustarts.
  Neue Modell-/Planaufrufe nutzenv2; bereits geladene Modelle erst nachNeuladen.
  HD-K/D nicht auf640×480-HTTP-Bilder oder andere Kameras anwenden.
- **left_rear HD-Service PASS:** drei2592×1944-Bilder,je24Ecken,16,12s,
  Restore/Normal und sämtlicheOriginalsettings identisch. UCC3.44.0.149696,
  Kamera06561F1400090106. NativeDaten service/left_rear/c1990d41963846b78e3346ee5b3a8b5d.
- **right_rear nativeHD erhalten**,3×2592×1944,UCC1.11.1.10337,
  Kamera01D1111A00090912. Decke/Leuchte stattBoard,keineArmfahrt fürsMotiv.
  VollständigerService-Restore imAutofokusmodus FAIL: FokusfensterX1/Y1 von
  165/134 über158/118 auf158/102 verschoben; ursprünglicheROI nicht exakt
  wiederhergestellt. Autofokus/Autoexposure-Modi,LED und übrigeFelder erhalten,
  KameraNormal. Dies wird nicht als vollständigerErfolg verschwiegen.
- Weitere UCC1.11.1-Autofokus-Aufrufe vorKamera-/Modusänderung abweisen;
  echter Guardtest2,88s, state_changed:false, vollständigeVorher-/Nachhergleichheit.
  VerifiziertesManualprofil oderUpdate+Restoretest vorweitererSerie nötig.
- LegacyLED-Schreibwerte0/1 bei tatsächlich getestetenZweigen1.11.1/3.44.0
  invertiert; jetztgezieltberücksichtigt, tatsächlicherReadbackmaßgeblich.
  BegrenztesWarten aufSettings;automatischbestimmteFokus-/Exposureausgaben
  dynamisch,Konfigurations-/manuelleWerte weiterhinstrenggeprüft.
- **45Tests PASS**,3LyricalPaketegebaut;Logs uwa-front-hd-adoption-{tests,build}.
  Berichte [Profile](docs/applied_calibrations.md),
  [Rear-HD-Bildtests](docs/wrist_hd_other_arms_2026-11-12.md).
  Daten setup/calibration/wrist_hd/other_arms_20261112/;Sitzungen/RohbildernichtimGit.

## OAK-CAD und eigenes Stativ eingebettet,2026-11-12

- Nutzer beauftragt Modell ausDownloads und optional Stativdarstellung.
  Archiv oak4-pro-3d-model.zip enthält117MB-STEP-Baugruppe. InMeter konvertiert,
  Gehäuse/Frontglas getrennt und auf52169Dreiecke/2,61MB reduziert; Quell-/Mesh-
  Hashes undKoordinatenzuordnung in meshes/visual/oak4_pro/provenance.json.
- Generisches Fotostativ selbst erstellt: Teleskopbeine/Klemmen/Gummifüße,
  Spreizstreben/Mittelsäule/Schwenkkopf/Platte. Höhe aus tatsächlicher OAK-Pose,
  Füße bodenfest. VisuelleNäherung, keine vermesseneStativ-/CAD-Optikmontage.
- GemeinsameGeometrie fürGazebo undRViz; Mesh-/Zylinder-/Boxmarker. Optische
  Transformation/K-D/aktivesProfilv3 erhalten, keine Roboter-/Tischparameter
  geändert. Stativ bleibt wievorher visuell, keine neueMoveIt-Kollision.
- **21TestsPASS**,2Paketegebaut. Live:2CAD-Meshes+27Stativvisuals inGazebo,
  32Marker undRViz-Abonnent, frische4000×3000Bilder/K-D/TFs/9Controllerpositiv.
  Nur uwa-cell-overview.service neu gestartet, keine Zelle/Hardwareprozesse.
  MaxSim-Gelenkänderung0,00001064rad. KeineHardwarekamera/Armkommandos.
- Vorschau visuell geprüft, nativeFensteraufnahmen schwarz und nichtals
  sichtbarerRenderbeleggewertet. Bericht [OAK-CAD](docs/oak_camera_cad.md),
  Vorschau output/images/oak4_cad_tripod_preview.png; Nachweise
  setup/models/oak4-pro/live/ unduwa-oak-cad-{build,tests,live}.log.

## Karton nur aus Farbbildern alsCAD rekonstruiert,2026-11-12

- Nutzer beauftragt erste Pipeline zumDigitalisieren einfacherObjekte; Beispiel
  realerKarton aufTisch aus dreiFarbbildern. NativeDreieraufnahme17:09Perth,
  OAK8000×6000/beideWrist2592×1944, all_captured:true, Restore bestätigt.
  KeineTiefe, Armfahrt oderProfiländerung.
- OffenerKarton mit3Fächern rekonstruiert: ca.524×102×100mm Außenmaße,
  Trennwände ca172/347mm abLängsanfang. Wand/Boden/Trennwand2,5mmangenommen.
  Labels/Klammern/Faltungen/Verformungen nichtrekonstruiert; keineabsolute
  Genauigkeitbestätigt. Gegenmessung stehtaus.
- Maßstab aus rechtem40mm-Tischboard; neu geschätzteBild-Boardposen aus20
  OAK-/28Front-ArUco-Markerecken. OAKFactory14K/D116 undFront-HD-K/D435;
  Rear-HD388 mangelsMatchingK/D nurSichtprüfung. KeineHand-Auge-/FK-/Welt-
  Extrinsics imGeometriefit, keineLive-Gelenke erfunden (CaptureTelemetriefehlte).
- AssistiertesWerkzeug `ros2 run uwa_cell_control digitize_box`: Aufnahme
  vorbereiten/Intrinsics einfrieren, expliziteEckpunktdatei, robuster6Parameter-
  Fit+Trennwände, Overlays undAnnotationssensitivität. Keineallgemeineautomatische
  Segmentierung oderarbiträreOberflächenrekonstruktion behaupten.
- STEPmm/STLm/SCADmm unter setup/digitization/carton_20261112/result_v1/cad/,
  gültigerSolid/STEP-Rückimportmaße/geschlossenesSTL undrechtshändigerPoseexport
  geprüft.6SyntheticTestsPASS,Control-Paketgebaut,CLIinstalliert,Vorschaugeprüft.
- FinaleFit-RMSbei1800px:OAK5,41px/Front6,60px; keineunabhängigeValidierung.
  Zufalls-Annotationssensitivität umfasstnichtKalibrier-/Druck-/Modellfehler.
- Bericht [Objektdigitalisierung](docs/object_digitization.md), Vorschau
  output/images/carton_digitization_preview.png. Rohdaten/Hashmanifest/Overlays
  undKameraprofile untersetup/digitization/carton_20261112/, Logs uwa-carton-*.

## Echter Vierarm-Scan beauftragt, Start wegen Netzverlust offen, 2026-11-12

- Nutzer will Durchführung mit allen4parallel und bleibt amNothalt. Neue Ziele
  mit60mmTrennwandreserve/Reserveansichten gefunden:4Extras jeArm/21Blickpunkte,
  allePhasen unabhängiggetrennt mit50mmRestabstand nach±0,005radBahntoleranz.
  KleinsteModelluntergrenze339,0mm,2400MoveIt-Prüfpunkte. NochkeineArmfahrt.
- NeuerparallelerRunner+separateStop-GUI, GUI-Verlust/NativeSafety/Korridor/
  Datenverlust führenzugemeinsamemCancel/Deaktivieren/Stillstandsprüfung.
  BekannteZielevorWartenaufspäteBestätigungen canceln. ErsteFoto-Runde pausiert
  zurBildkontrolle,STOPbleibtverriegelt,keineHeimfahrt. KeinPower/Brake/Play imRunner.
- Build/34TestsPASS. IsolierteDomain75 mitviernativenMock-Controllern: gemeinsam
  Zielerreichung,STOPwährendFahrtundHeartbeatverlust/Resume-SperrePASS.
  EigeneMock-Prozessegezieltbeendet. RealeTreiber/Programmeunverändert.
- Gegen19:35Roboternetz enp87s0DOWN/CarrierOFF/keine8.209-Adresse,alleDashboards
  timeout. ROSlieferteweiterJoints/RobotMode3,RearSafety9;keineverifizierten
  aktuellenGerätezustände.BeideFrontwarenvorherbereitsPOWER_OFF. KeinStart/
  Safetyresetgesendet;NutzerumKabel/Switch/Steuerungengebeten.
- DeshalbLiveDashboard-HeartbeatzusätzlichzuROSFrischeimplementiert. Reader-
  Latest-SnapshotwurdebeiStatusabfrageersetzt;StartwerteimPlanerhalten,aber
  alteSnapshotbindungnunbewusstabgewiesen,vorFahrtneueimmutableLive-Planung.
- Anleitungdocs/parallel_object_scan.md;Datum/Sitzung
  setup/digitization/four_arm_scan_20261112/. StopfensterzeigtBLOCKEDNetworkDown,
  keineBewegungsschnittstellegestartet.KeineechtenScanbilderaufgenommen.

## Bewegungsraum-/Parallelprüfung der Scanwege, 2026-11-12

- Nutzer will maximale Vorstöße über mittige virtuelle Wände und daraus mehr
  parallele Bewegung. Implementiert Offline-CLI scan_separation, keine Motion-
  Clients/Dienst-/Kameraaktionen. Ganze68Kollisionskörper einschließlich Greifer
  und Kameras, Originalquintiken und konservative Zwischenpunktpolster geprüft.
- Quelle new_carton_plan_current, Modellhardware_20261112_v3. Über gesamte Wege
  LF/RF keine Mittellinienüberschreitung; LR≤34,1mm und RR≤60,4mm gegeneinander,
  tatsächliche Stichproben32,5/58,9mm. Greiferfinger begrenzen diese Vorstöße.
- Anfangswege aller4Arme zeitunabhängig getrennt, trotz hinterer Ebenenübertritte:
  gedrehte3D-Ebene liefert28,6mm Abstanduntergrenze. Technische Prüfschwelle20mm,
  keine gemessene Reserve realer Montagefehler. Alle übrigen Paarabstände größer.
- Zusatzansichten hinteres Paar nicht vollständig mit20mm nachgewiesen, auch
  bei289Einzelkörperpaaren: linke Finger gegenüber rechtemwrist_2 bleiben offen.
  Kein tatsächlicher Kollisionsfund behauptet. Andere5Armpaare getrennt.
- Prüfablauf: alle4Anfangswege parallel; Zusatzketten LF/LR/RF parallel inRunden,
  dannRR. Nicht nachgewiesene Paarreihenfolge LR→RR unverändert; Gelenkpunkte/
  Zeitparameter unverändert, Stillstands-/Fotobarriere nachjederRunde.
  Reine Fahrzeit193,5→80,9s(−58,2%), ohne Aufnahme/Stillstand. Nur Prüfartefakt,
  keine Integration/Aktivierung paralleler Hardwarebewegungen.
- Quell-/URDF-/Mesh-SHA gebunden; Greiferwerte explizite Modellannahme, Weltanker
  vorläufig, Kabel/Personen/Stativ nicht modelliert. Neue Wege neu prüfen.
- Build und12neueTests/Planungs-/Parkregressionen geprüft. Anleitung
  docs/scan_separation.md, Daten setup/digitization/five_camera_design_20261112/
  separation_review/, separater installierterCLI-Lauf separation_installed/.

## OAK zuerst und Fünfkamera-Softwarestufe, 2026-11-12

- Nutzer beauftragt Umsetzung; korrigierter Aufbau: neuer größerer Karton in der
  Mitte zwischen beiden Tischen, Unterseite auf Tischhöhe. Grobe Nutzerangabe
  40×30×20cm. Gewünschter Ablauf zuerst OAK-Foto/Größenschätzung, dann UR-Planung.
- Ein natives OAK-Standardfoto18:20AWST beiFokus116, keine Arm-/Wrist-Aufnahme.
  Automatische rechte Board-PnP24Ecken/1,33px. Assistierter Sechspunktfit schätzt
  43,9×34,6×15,8cm; kein finales CAD/Genauigkeitsnachweis. Overlay durchgesehen.
  Planungsreserve max(Bild,Nutzer)×1,15+4cm ergibt54,5×43,7×27cm.
- Neue CLI object_scan_bootstrap (Foto/assistierte Schätzung), object_scan_plan
  (nur Lesen/Modellprüfung/RViz-Vorschau Domain74) und scripts/object_capture.sh
  (vier Wrist+OAK, Kamera-only). Dreikamera-Standard erhalten. Keine Bewegungs-
  Clients im neuen Planer; alle Ergebniswege bleiben executable:false.
- Neue gemeinsame Modellansichten mit beiden Referenzboards; enger Suchbereich
  wegen Bildausschnitten verworfen, weiter Bereich fand5Grund-/15Zusatzansichten.
  Volle MoveIt-Wege mit gepolstertem Objekt, andere Arme nicht ausgenommen;
  reine Planung, keine reale Ausführung. Alte rechte-Tisch-Kartonpläne überholt.
- Fünfkamera-Telemetrieaudit vor/während Fotos, Roh-JointStates mit Stempeln und
  Geschwindigkeiten. Bewegung/Stale verweigern statische Bestätigung. Echte reine
  Leseprobe alle4frisch/ruhig, maximale beobachtete Gelenkänderung0,000071rad.
  Keine Bilder während dieses Audits. Fotos bei Fehler bleiben diagnostisch.
- Gespeicherte fünf Kameras in digitize_box vorbereitet; fehlende native K/D
  explizit ausgeschlossen. Linkes/rechtes Board nur mittels beider PnP-Posen aus
  demselben OAK-Foto verbinden, Transformationsrichtung synthetisch geprüft.
- Build PASS,35gezielte Tests inklusive Parkregressionen PASS, englische Fünfkamera-GUI mit synthetischen
  Snapshots offline geprüft. Keine laufenden Messreihen/Dienste unterbrochen;
  neue Pfade/Szenen nur offline. Noch kein realer Fünfersatz, kein neuronales Mesh.
- Frische reine Zustandslesung18:35:48AWST und neue Planung bestätigt:20Ansichten,
  19Wege/1963Punkte,139sGrundpositionierung+55sZusatzwege. Aktuellster Entwurf
  new_carton_plan_current/, frühere Entwürfe separat. Statische Vorschau geprüft;
  alle Artefakte weiterhin nicht ausführbar, kein echter Fünfkamera-Scan.
- Anleitung docs/object_scan.md, Daten setup/digitization/five_camera_design_20261112/.
  Welt-/Montageanker teils vorläufig; reale Wege brauchen frische Prüfung und
  konkrete Durchsicht, passende Kalibrierprofile sind teilweise noch separat.

## Vier Wrist-Kameras plus OAK: Scan-Konzept, 2026-11-12

- Nutzerziel: gemeinsames Objekt in Tischmitte, fünf Fotos je Aufnahmeschritt,
  optional kleine Zusatzbewegungen und Nutzung von Literaturverfahren.
  Gemeinsamer Scanbereich und Wege sind noch nicht nachgewiesen; bisherige
  Designposen zielen jeweils auf das eigene Tischboard.
- Empfehlung: fünf feste Ansichten, danach 3–5 Stellungen je Wrist plus feste
  OAK, also 13–21 verschiedene Blickpunkte. Kleine TCP-Bewegungen erfordern
  weiterhin vollständige Wegprüfung. Zunächst seriell positionieren und vor
  nicht belichtungssynchronen Fotos gemessenen Stillstand bestätigen.
- Designprofil config/digitization/five_camera_scan_design.yaml: nicht ausführbar,
  keine Bewegungsschnittstelle; Syntax und Ansichtszähler geprüft. Keine laufenden
  RR-/LF-HD-Kalibrierungen unterbrochen, keine Hardwareaufnahme oder Armfahrt.
- Primärquellen: COLMAP/OpenMVS als geometrische Vergleichsbasis, MASt3R oder
  VGGT als gelernte Initialisierung, anschließend Mesh und parametrischer CAD-Fit.
  Intrinsics je Sensor, Pose je Aufnahme; Maßstab, Objektmasken und zurückgehaltene
  Prüfansichten erhalten. NeRF/Splats benötigen zusätzliche Geometrie-/CAD-Schritte.
- Host mit Intel-Grafik, kein erkanntes CUDA-Gerät. COLMAP Sparse auf CPU möglich,
  dessen eigene dichte Rekonstruktion benötigt CUDA. Keine Modelle installiert
  oder ausgeführt. Stand und Quellen: docs/five_camera_reconstruction.md.

## Nutzerziele und Vorlieben

- Neue Roboter-Codebasis auf **ROS 2 Lyrical** unter **Ubuntu 26.04** aufbauen.
  Die bestehenden Jazzy-Repositories wurden dafür lokal angepasst.
- Einen digitalen Zwilling der echten Roboterzelle in Gazebo erstellen, im Repository
  `multi_arm_manipulation_UWA` unter `~/UWA_ws/src/`.
- Zunächst Geometrie und steuerbare Kinematik. Seit 2026-11-09 zusätzlich automatische
  Hand-Auge-Kalibrierung mit MoveIt-Kollisionsprüfung; allgemeine kooperative Planung
  und Synchronisation mit echter Hardware bleiben Folgearbeit.
- rqt für manuelle Gelenksteuerung erhalten. Neuer ausdrücklicher Auftrag vom
  2026-11-09: eine eigene Qt-GUI für Vorbereitung, Aufnahme, Überwachung, Stopp und
  Übernahme der automatischen Kalibrierung (ersetzt die frühere Einschränkung dafür).
- Bequemer Start wie eine Desktop-App mit eigenem Icon und RViz-Konfiguration.
- **Neuester Bedienwunsch, 2026-11-09:** Der normale App-Klick soll die Punktewolke
  mitladen. Keine zusätzliche Rechtsklick-Aktion zum erstmaligen Anzeigen verlangen.
- Das Vier-Roboter-Icon gefällt dem Nutzer; nur der weiße Außenrahmen sollte
  transparent werden. Das ist umgesetzt, der dunkelblaue Hintergrund bleibt erhalten.
- Deutsch als bisherige Gesprächssprache; praktische, nachvollziehbare Bedienhinweise.
- **Explizit seit 2026-11-09:** Wichtige Ziele, Anforderungen, Entscheidungen und
  Vorlieben parallel in AGENTS-/Handover-Dateien festhalten.

## Globales Profil aktiviert und drei Boards mit OAK erkannt,2026-11-12

- Nutzer beauftragt explizit globale Aktivierung. Neues versioniertes
  `hardware_20261112_v1` ergänzt linkeRear-VGA-Intrinsics/Hand-Auge aus bestandenem
 41er-result_v1. Alte rechte gültige Werte/kinematics/namedposes bytegleich;
  vorherigesBündel unverändert erhalten. FehlgeschlageneFront-HD-/VGA-Extrinsics
  ausgeschlossen. Keine neuen Welt-/Basis-/Tischanker oder OAK-Extrinsics.
- Gemeinsame Standardreferenz umgestellt,description gebaut, installiertes
  Standardprofil bestätigt. Sieben Modell-/K-D-/Sensor-/MoveIt-Consumerprüfungen
  bestanden, einschließlich linker optischerPose und unveränderter Gehäuse/Weltanker.
  Neue Modellloads/Planungen verwendenProfil; keine aktiveSimulation neu gestartet,
  keine UR-Kommandos/Treiberneustarts. Aktivierungsaudit untersetup/calibration/.
- Ethernet-OAK238 exklusiv geöffnet (Live-Dienst vorher inaktiv), natives
  **8000×6000**-NV12-Foto vomIMX586 aufgenommen; kein Upscaling, danach geschlossen.
  OriginalPNG und annotiertes8K-JPEG/Übersicht sowieID-/Eckbericht lokal unter
  `setup/oak4/captures/boards_20261112/`. Keine privaten Fotos imGit.
- Alle drei gleichzeitig vollständig erkannt: linkes/hinteresTischboard IDs0–16,
  rechtes/vorderesTischboard50–66,mobilesA4-Board75–91. Je **17/17Marker und
 24/24ChArUco-Ecken**. Detektion aufOriginal8K ohne GroundTruth/Robotermodell.
- ReineErkennungsprüfung, noch keine OAK-Extrinsics oder metrischeRegistrierung.
  MobilesBoard liegt imFoto untenlinks; Werkzeug-zu-Board-Montage bleibt unbekannt.
  NächsterKalibrierschritt getrennt planen, keine neueRoboterfahrt hieraus ableiten.

## Front-HD-Reihe vollständig aufgenommen, Qualität abgelehnt, 2026-11-12

- **40/40 native HD-Ansichten** von right_front,2592×1944;32Fit/8vorab
  reservierte Prüfungen. Alle angenommen,20–24Ecken,40 verschiedene Pixel-Hashes.
  Eigener Frontlauf ohne Unterbrechung. Rohdaten und getrennte Diagnoseversion
  unter `setup/calibration/hardware_handeye/right_front_hd_20261112/` erhalten.
- **Zum ursprünglichen Abschluss keine automatische Qualitätsfreigabe:** Intrinsics-Fit1,1984px überschreitet1px;
  regulärer Ablauf daher Exit1 nach vollständiger Aufnahme. Zusätzliche reine
  Offline-Diagnose: Intrinsics-Prüfung1,0031px, Hand-Auge-Prüfung1,9248px,
  Boardstreuung1,2669mm/0,5884°. Keine Bilder entfernt/Prüfbilder zumFit benutzt,
  keine Grenzwerte geändert. Diagnosewerte ausdrücklich nicht aktiviert.
- Neueste Nutzerkorrektur ersetzt vorheriges „erst links fertig“: diagonale
  reale Arme erreichen einander laut Nutzer nicht. Bedienerangabe, kein eigener
  Messnachweis. Fingerprinted `independent_diagonal_arm=left_rear` für Front;
  nur dieses Paar von gegenseitiger Kollision/Stillstandsabhängigkeit befreit.
  Selbst-/Tisch-/Werkzeug-/übrige Armkollisionen und native UR-Safety erhalten.
 26 gezielte Tests und Lyrical-Build bestanden.
- Fokus435Manual/60000µs/Gain16 während der gesamten Reihe. HD-Transaktionen
  jeweils mit bestätigtem Restore. Abschlusslesetest12:37Perth: KameraNormal,
  Originalsettings vollständig identisch; FrontRUNNING/NORMAL/PLAYING,Velocity0,
  hält letzte Aufnahmestellung mit aktivem skaliertem Trajektoriencontroller.
  Keine Rückfahrt/Schutzquittierung/Profilaktivierung. Andere Arme nicht gesteuert.
- Vollständige Werte und Nachweise: [Front-HD-Bericht](docs/front_hd_calibration_2026-11-12.md).
  Arbeitsstatus `work/front-hd-calibration-40.md`. Weitere Auswertung der Bilder
  ist offline möglich, ohne neue reale Bewegung. Ältere VGA-Profile erhalten.

## Front-HD: Grund des Intrinsics-Abbruchs eingegrenzt,2026-11-12

- Nutzer fragt nach gleicherFrontkamera/Board mit bestandenerVGA-Kalibrierung.
  WichtigePräzisierung: Front-VGA-Intrinsics bestanden; Front-Hand-Auge bereits
  wegen0,652°>0,5°abgelehnt. HD hat0,588°,nochimmernichtfreigegeben.
- Absolute1Pixel-Grenze berücksichtigt4,05fachhöhereHD-Auflösung nicht:
  1,198HDpx entsprechen0,296VGApx,alt0,289px. KontrollierteOffline-Auswertung
  derselben40HD-Bilder(32/8fest):Verkleinernauf640×480+Eckenneuerkennung ergibt
  Fit0,315px/Prüfmedian0,276px. KeinBelegfürgenerellschlechtereHD-Geometrie.
- ArUco-Subpixelablation bringt praktischkeineÄnderung(1,19834vs1,19841px).
  Rotationsursache nochungeklärt:Optik-/Bildpose,Boardplanheit,Montagestabilität,
  Restbewegung/Zeitzuordnung möglicheBeiträge,keinernachgewiesen.
  NativeHD-KontrollwertewährendStreamwerdennochnichtzurückgelesen;
  Vorher-/Nachher-HTTP-SettingsbelegenkeinevollständigeIn-Stream-Konstanz.
- Diagnosev1 unterHD-Sitzung/resolution_diagnosis_v1/,80Originalhashesbestätigt.
  KeineRealbefehle,Produktions-/GrenzwertänderungenoderProfilaktivierung.
  Bericht docs/front_hd_calibration_2026-11-12.md ergänzt. Auflösungsbewusste
  Bildfehler/robusteGewichtungkünftiggemeinsamdefinieren;mm/Gradseparatprüfen.

## Links hinten: reale Kalibrierung abgeschlossen, 2026-11-12

- Vollständige **41 Ansichten** mit eigenen HTTP-VGA-Bildern (640×480):
  **33 Fit / 8 vorher reservierte Prüfbilder**, alle akzeptiert, jeweils24 Ecken,
  41 verschiedene decodierte Bilder. Kein Bild ausgeschlossen oder überschrieben.
  Fester Fokus406Manual,33333µsManual/Gain16; kein fremdes Kamera-/HD-Profil.
- **Intrinsics PASS:** Fit-RMS0,1143px, medianer Prüf-RMS **0,1481px**.
  **Hand-Auge PASS:** Prüf-Reprojektion **0,2496px**, Board-Translationsstreuung
  **0,7402mm**, Rotationsstreuung **0,1671°**. Interne zurückgehaltene Prüfung,
  keine absolute Genauigkeitsgarantie. HTTP-Empfang ist kein Belichtungszeitstempel.
- Ergebnis und Rohdaten versioniert unter
  `setup/calibration/hardware_handeye/left_rear_20261112/result_v1/`:
  `summary.json`, `intrinsics.json`, `handeye_result.json`, vollständige41er-
  Roh-/Annotationsdaten und SHA256-Manifest. Quelle/Originalrollen erhalten.
  Ergebnis zunächst nicht automatisch aktiviert. Auf späteren ausdrücklichen
  Nutzerauftrag am selben Tag global in **hardware_20261112_v1** übernommen;
  archiviertes ursprüngliches `activated:false` bleibt als Historie erhalten.
- Abschluss: SafetyNORMAL, alle linken Motioncontroller inaktiv, Endfehler
  **0,0000338rad**, Positionsänderung über das letzte0,5s-Prüffenster0,0000424rad.
  Keine Rückfahrt; Arm bleibt an letzter Aufnahmeansicht. Kein fremder Arm gestoppt.

### Unterbrechungen und Wiederaufnahme

- Bei sample029 nativer **C159A5/Wrist3**;29 Bilder gesichert, eigene Action
  gecancelt und linke Motioncontroller inaktiv. RTDE bestätigte0kg/CoG[0,0,0].
  Nutzer meldet Ursache behoben; anschließend1kg/CoG[0,0,0],NORMAL/PLAYING/Link
  geprüft. Kein Nutzlastwert vom Agenten geraten/gesetzt, keine Autoquittierung.
  Separater29er-Diagnosefit bleibt historisch/inaktiv (Mindestzahl30).
- Zwölf Originalrestziele neu aus tatsächlichem Start verbunden; zuerst vor jeder
  Bewegung wegen fehlender rechter Rear-Telemetrie abgebrochen. Alter Manager18298
  stürzte nach PrimaryClient-Pipeline-Überlauf mitExit−11 ab. Nur diesen Treiber
  als `uwa-right-rear-calibration-observer` wieder gestartet, Motion inaktiv,
  kein Power/Play/Armziel. Linker Dienst und Frontmanager erhalten.
- Nach32 Aufnahmen Abbruch wegen Frontbewegung unter alter Stillstandsregel.
  Nutzer bestätigt hier ausdrücklich: **„Ja, diagonale Arme erreichen sich nicht;
  Restreihe ausführen“**. Das ist eine Nutzerangabe zur Reichweite, keine Messung.
  Neue neunRestziele `resume_diagonal/batch.json` (d913d5c2…) samt unveränderten
  Originalzielen/Prüfrollen geprüft; nur gegenseitigeLR/RF-Kollisionen und deren
  Stillstandsabhängigkeit ausgenommen. Übrige Kollisionsprüfung/nativeUR-Sicherheit
  erhalten. Vorherige pauschale Warte-/Einarmangaben sind für dieses Paar überholt.
- AutoReview hatte die neue Ausnahme zunächst mangels konkreter Freigabe im
  aktuellen Gespräch abgelehnt; dabei keine Fahrt. Erst nach obiger ausdrücklicher
  Bestätigung und erneutem Gesamtcheck gestartet. Diagonaltests2/2 bestanden.
- Fortsetzung bis sample040 und Auswertung Exit0; Originaldaten/Haltebilder
  erhalten. Logs `preparation/{series-run,resume-run-after-observer,
  resume-diagonal-run}.log`, Abschluss `completion-state.json` und Freigaben dort.
  Weitere Front-HD-Arbeit läuft separat und wird hier nicht gesteuert.

### Abgeschlossene Erstpose und Bildprüfung

- Aktueller Abschluss nach Nutzerfreigabe „Vorschau passt, Fahrbereich frei –
  erste Pose anfahren“: genau `approach_ready/plan.json`(f6296105…) ausgeführt,
 34,173s, native Action erfolgreich/Result0, unmittelbarer größter Zielwinkel-
  Fehler0,0000158rad; späterer Stillstandssnapshot0,0000513rad. NativeSafetyNORMAL,
  ExternalControltrue, velocities0; skalierter JTC hält die erreichte linke Pose,
  andere linke Bewegungscontroller inaktiv. Keine Rückfahrt oder anderen Armziele.
- Front-Endvergleich0rad, Rear-Endvergleich0,0000246rad zum Wegstart, keine
  kontinuierlichen Maximalwerte behaupten. Erledigte eigene Domain68-Animation
  geschlossen, Hardware-GUIs/drei Treiber erhalten.
- Wirkliches640×480-Bild: erstes AF-Übergangsbild unscharf, danach viermal
  alle17 Marker/24 Ecken links(IDs0–16), Muster vollständig/unverdeckt im
  geprüften Bild. Fünf unterschiedliche Payloads, Fokus406Auto/33333µsAuto/Gain16
  nur gelesen, keine Kameraparameter geschrieben. Inspektionsbilder sind keine
  Fit-/Prüfaufnahmen; noch kein sample000/Kalibrierfit/aktives linkes Profil.
- Zusätzlich nur geplant:40 Zusatzansichten in `left_rear_20261112/batch_plan/`,
 8 unabhängige Prüfrollen, später41 Gesamtansichten/33Fit/8Prüfung. Reine
  Bewegungsdauer709,57s plus Stillstand/Aufnahme. Damals noch keine ganze Folge freigegeben
  oder gestartet; diese Vorbereitung ist durch die oben dokumentierte Serienfreigabe
  und tatsächliche Aufnahme überholt. `first_view_inspection/inspection.json` und
  `preparation/first-view-completion.json` halten aktuellen Stand fest.

### Vorherige Vorbereitung und Verbindungsdiagnose

- Nutzer beauftragt Vorbereitung left_rear192.168.8.169 und ausdrücklich
  Remote-Einschalten/Bremsenlösen/Programmstart über vorhandenen MATCH-Ablauf.
  Linkes40mm-A3-Tischboard(IDs0–16) und links vorne aufrechtes Home unverändert
  bestätigt. Mobile38mm-A4-Vorlage ist hierfür nicht das Ziel.
- Native Verbindung/Wrist-HTTP640×480 nachgewiesen; drei unterschiedliche Bilder,
  Fokus439Auto/Belichtung33333µsAuto/Gain16 nur gelesen. Aktuell noch kein Board
  im Bild; passende feste Optik nach erster tatsächlich erreichter Sicht prüfen.
- Hardware-CLI für alle vier Arm-IDs erweitert,25 gezielte Tests inkl. linker
  MoveIt-/IK-Sweeps und zwei Startup-Warnpfade. MATCH-Startup `.warn`→`.warning`
  für Lyrical korrigiert. Individuelle gespeicherte UR7e-Werkskinematik genutzt.
- Wiederholte Startfehler schließlich lokalisiert: alter linker Manager8998FDs,
  davon8967Sockets. Scriptserver verwarf tatsächlich eingehende Verbindungen
  mit FD8997/8998 wegen FD_SETSIZE1024. Kein URCap-Konfigurationsfehler als
  Ursache behaupten; ursprüngliche PLAYING/Link-false-Diagnose ist überholt.
- Nur geprüften linken Launcher nach bestätigter Inaktivität sauber ersetzt,
  neuer Benutzerdienst `uwa-left-rear-calibration-driver`, neuer Manager48FDs.
  MATCH-Start jetzt Exit0 und tatsächlicher `robot_program_running=true`,
  Safety NORMAL, vier Motioncontroller inaktiv. Rechte Manageridentitäten
  unverändert, parallele Front-Kameraarbeit erhalten. FD-Wachstumsursache noch
  ungeklärt; Neustart beseitigt konkreten Zustand, kein Langzeitfix nachgewiesen.
- Hinten rechts jetzt RUNNING mit plausiblen Livewinkeln. Front bleibtPOWER_OFF/
  Local, nicht-null gemeldete Winkel unabhängig per reinem RTDE gegengeprüft
  (max4,5e−16rad Unterschied). Keine Power-/Programm-/Kameraänderung vorne rechts.
  Linke Home-Hindernispose weiterhin Nutzerangabe, keine Encodermessung.
- Damals frische erste Sicht `setup/calibration/hardware_handeye/left_rear_20261112/
  approach_ready/plan.json`:34,173s, vollständiger MoveIt-Sweep, `--check-only`
  bestanden; RViz-Vorschau Domain68 offen. Nominelle Kamera[-0,45;0,28;1,453]m,
  etwa55cm über linkem Board. Diese erste Fahrt ist inzwischen wie oben
  dokumentiert ausdrücklich freigegeben und erfolgreich abgeschlossen.
- Erst konkrete Vorschau/Fahrbereich freigeben, erste Pose ausführen und echtes
  Board-/Fokusbild prüfen. Vorgesehen41 Ansichten(33Fit/8vorabPrüfung), wide;
  ganze Reihe erst danach planen/freigeben. Keine Rückfahrt oder Profilaktivierung
  aus dieser Vorbereitung ableiten. Frühere reine Entwurfsvorschau bleibt
  nicht ausführbar und wurde nicht ausgeführt.
- Diagnose/Snapshots/aktueller Ablauf unter .../preparation/;
  [Wiedereinstieg](docs/left_rear_calibration_preparation_2026-11-12.md),
  Arbeitsstatus work/left-rear-calibration-preparation.md. Bisherige Messprofile
  und rechte Hardwaretreiber erhalten, neuer linker Dienst bleibt bereit.

## HD-Bilddienst für neue Hardwarekalibrierung,2026-11-12

- Nutzer möchte nativen5MP-Aufnahmeweg als Dienst für erneute Kalibrierung und
  fragt nach Grünstich. Auf echtem Foto24 ChArUco-Ecken; Farbbild/Graubild
  identische IDs/Pixelkoordinaten. Farbstich allein somit hier kein Erkennungs-
  hindernis, neue Geometrie-/Genauigkeitsaussage erst nach unabhängiger Prüfung.
- Neuer ROS-Dienst `wrist_hd_service`,HardwareDomain66,
  `/uwa_hardware/right_front/wrist_camera_hd/{capture,status}`(std_srvs/Trigger),
  dazu `image/compressed`. Drei native2592×1944-JPEGs pro Trigger mit Settings,
  Gerätezeiten/Sequenz im Capturelog,Schärfe-/Clippingwerten,Prüfsummen.
  Kamera-/ROS-Empfangszeit nicht als synchronen Belichtungszeitpunkt ausgeben.
- Nur real ermittelten Kamera-Vision-runit-Dienst kurz freigeben, temporäres
  V4L2-C-Werkzeug,Normal abwarten und alle ursprünglichen Parameter forceRefresh
  vergleichen. Unabhängiger Remote-Watchdog bei Verbindungs-/Prozessverlust.
  Keine Kennwörter im Code/Parametern/Dateien; private SSH-ControlMaster-Sitzung.
- Hardwareaufnahme `--camera-source wrist_hd_service` integriert. Client spinnt
  Telemetrie während RPC, behält Stillstands-/Guardfehler und wartet vor Fehler-
  weitergabe auf erfolgten Restore. Eckenzahl/Schärfe wählen bestes Burstbild.
  Eigene neue HD-Sitzung, kein HD/VGA-/Kamera-ID-Wechsel. Neuer Intrinsicsfit
  ausschließlich aus HD-Trainingsdaten; reservierte Prüfbilder bleiben getrennt.
- **Reale Service-/Clientprobe bestanden:**3×2592×1944,je24 Ecken,16,04s,
  502 Monitorhook-Aufrufe,max32,8ms Abstand; Status weiter CAPTURING erreichbar,
  zweite Aufnahme abgewiesen. Kein echter Bewegungs-/Stopptest daraus ableiten.
  Alle Originalsettings wieder identisch, normaler Kameradienst wieder aktiv.
  Vorangehendes reines Discoveryproblem vor Kameraänderung behoben; Log erhalten.
- Paket gebaut,29 gezielte Offline-Tests bestanden (u.a.Nativegröße,Framewechsel,
  Restorefehler/Erholung,Mode-/Identitätsmix,runit-Zuordnung und transienter
  Bewegungsfehler bis Restore abwarten). Nachweise setup/logs/uwa-wrist-hd-*.log,
  uwa-wrist-hd-live-adapter.json; Rohbilder in dessen Burstverzeichnis.
- Dienst/SSH-Sitzung fürright_front aktuell offen,keine neue Kalibrierfahrt
  gestartet. Noch keine40–50-Posen-HD-Reihe/HD-Genauigkeit nachgewiesen.
  Andere Kameras über diesen Dienst ungetestet. Pro Stellung rund16s Zusatzzeit,
  reguläre URCap-Vorschau dabei kurz unterbrochen,Grünstich weiter sichtbar.
  [Start/Bedienung/HD-Sitzung](docs/wrist_hd_service.md),work/wrist-hd-service.md.

## Natives5MP-Foto Front-Wrist erfolgreich,2026-11-12

- Nutzer beauftragt erneuten Vollauflösungstest right_front192.168.8.103 und
  stellt legitimen temporären SSH-Zugang bereit. Zugangsdaten nicht speichern.
  Nach Aktivierung des SSH-Diensts Anmeldung erfolgreich, Sitzung danach beendet.
- Tatsächlich UCC4.1.0.164735/CQ0-1.4.0,uniqueCamId01D10E1900090912.
  HTTP-Vorschau640×480; direktes V4L2-Gerät bietet MJPEG2592×1944 an.
- **Native Datei2592×1944/5038848Pixel/332800Bytes** per V4L2-MMAP-Aufnahme
  auf Controller erzeugt und perSCP heruntergeladen, lokal decodiert/Größe und
  SHA256 bestätigt. Kein Upsampling, kein Barcode-/SaveImage-/FTP-Programm.
  Datei setup/calibration/wrist_hd/right_front_20261112/controller-artifacts/
  native-2592x1944.jpg; [Prüfbericht](docs/wrist_native_photo_2026-11-12.md).
- Nur Kamera-Vision-Dienst über seinen vorhandenen runit-Supervisor kurz
  gestoppt/gestartet. Erster Versuch Gerätnochbusy, zweiter mit begrenztem
  Freigabe-Retry erfolgreich. Keine Roboterprogramme, Motion, UR-/ROS-Treiber
  oder Simulationen angefasst. Kamera-Konfigurationsdateien unverändert.
- Früher automatischer Restore zu früh während Initialisierung fehlgeschlagen;
  anschließend im tatsächlichen Normal vom PC vollständig wiederhergestellt.
  Alle Originalfelder forceRefresh-identisch(Fokus435Manual/60000µsManual/
  Gain16/AutoLED0). final-restoration.json ist abschließender Nachweis; frühe
  fehlgeschlagene Rohberichte separat erhalten. AutoLED-Setter meldet teilweise
  Fehler15 trotz angewandtem Wert, Rücklesen entscheidend. Normaldienst und
  reguläre640×480-Vorschau wiederhergestellt.
- **Grünstich im direkten JPEG**, Farbwiedergabe/Weißabgleich noch zu qualifizieren.
  Bestehendes640×480-Intrinsicsprofil nicht als5MP-Kalibrierung verwenden.
  Native Aufnahme bewiesen, kein fertiges allgemeines GUI-Aufnahmewerkzeug und
  kein isolierter Nachweis, dass erst das4.1-Update5MP ermöglicht hätte.
- Eigene Aufgabe work/front-wrist-hd-ssh.md abgeschlossen; parallele aktive
  left-rear-Kalibrierungsvorbereitung erhalten. Bild-/Herstellerdaten bleiben
  außerhalb Git unter setup/calibration/wrist_hd/right_front_20261112/.

## Gemessene Kalibrierungen gemeinsam übernommen,2026-11-11

- Expliziter Nutzerauftrag: ermittelte Posen/Kalibrierungen dauerhaft speichern
  und in Simulation, Visualisierung, Kollisionsprüfung und weiteren Verbrauchern
  verwenden. Kein Bewegungsauftrag. [Bedienung/Umfang](docs/applied_calibrations.md).
- Installiertes versioniertes Bündel unter
  `uwa_cell_description/config/calibration/hardware_20261111_v1/`: unveränderte
  Ergebniskopien, drei Werkskinematiken, CameraInfo-YAMLs, benannte Posen und
  SHA256-Manifest `profile.json`. Rohbilder/ursprüngliche Ergebnisse erhalten;
  deren damaliges `activated:false` ist historisch, nicht aktueller Profilstatus.
- Aktiv: individuelle Kinematik left_rear/right_front/right_rear, Intrinsics
  beider rechten Kameras(640×480, Rear404/Front435Manual), Rear-Hand-Auge
  tool0→optical sowie Rear-Basis→Board als Referenzframe. Front-Hand-Auge
  weiterhin abgelehnt(0,652°>0,5°), keine relative rechte Basispose aktiviert.
- `cell_layout_calibrated.yaml` ist jetzt Standard, verweist auf die unveränderte
  zentrale Nominalgeometrie und das Profil. `cell_layout.yaml` bleibt expliziter
  Nominal-Rückfall. Gemeinsamer Python-Loader im Beschreibungs-Paket wird von
  Gazebo und Overlay verwendet; MoveIt/Hardwareplanung verwenden denselben
  Renderpfad. Kein Visualisierungsimport aus Gazebo erforderlich.
- Neue Aufnahmeplanung verwendet gespeicherte K/D inklusive Verzeichnung und
  kennzeichnet erforderlichen Fokus; nomineller Rückfall nur ohne passendes
  Intrinsicsprofil. Keine Übernahme dieser Planungswerte als neue Fit-Beobachtung.
- Inventar verweist auf archivierte Werksdateien, bytegleich zu den zuvor
  verwendeten Dateien. Treiber/GUI nicht neu gestartet. Optische TFs/Sensorpose
  werden geändert, angenäherte Gehäuse-/Greifer-Kollisionskörper nicht aus einem
  Optikfit versetzt. Welt-/Tisch-/Basisanker, OAK-Pose, Scan und Startgelenke
  bleiben vorläufig/unverändert. Intrinsics erfordern passenden Fokus/Bildmodus.
- `named_poses.json`: tatsächliche Park-Snapshots und erste Aufnahme-Snapshots
  beider rechter Arme, rad/Gelenkidentitäten/Quellenhashes; ursprüngliche
  Parkzielwinkel zusätzlich erhalten. Keine Live-Hinderniszustände, keine
  automatischen Fahrten und keine Wiederverwendung alter geprüfter Wege.
- Zusätzliche Simulationsfits je Messprofil getrennt unter
  `setup/calibration/profiles/measured_<Profilhash>/`; bisherige ideale
  `profiles/active.json` bleiben für das Nominalmodell erhalten. Kein alter
  Simulatorfit überschreibt ungeprüft reale Messwerte.
- Fünf Pakete gebaut;99 gezielte Offline-/MoveIt-Prüfungen bestanden, einschließlich
  identischer FK in Simulation/Planung/Overlay. Gespeicherte reale FK-Matrizen
  sample000 beider rechter Kamerareihen mit neuem Modell exakt reproduziert.
  Live-Gazebo: neun aktive Controller, fortschreitende Uhr, endliche Gelenke,
  zwei rechte640×480-Streams, K/D und Rear-Optik-TF passend zum Profil.
  Simulationsbackend IDLE ohne Aktivierung früherer Idealprofile, alle vier
  Kameras24 Ecken erkannt. Eigene Headless-Testsimulation und eigener Backend
  wieder sauber beendet; ursprünglicher inaktiver Simulationszustand erhalten.
- Nachweise `setup/logs/uwa-calibration-integration-{build,tests}.log`,
  `uwa-calibration-integration-{live,backend}.json`; kompakter
  [Prüfbericht](docs/calibration_integration_validation_2026-11-11.json).
  Keine Hardware-Fahrten/Power/Brake/Play. Die vorhandene J-PARSE-Online-
  Kollisionsoption bleibt deaktiviert; MoveIt-Modellverbesserung ist kein
  vollständiger aktiver Online-Zellenschutz und keine absolute Vermessung.

## Mobiles A4-ChArUco-Board für externe OAK,2026-11-11

- Nutzer besitzt einen am UR montierbaren A4-Holzträger und möchte Papier flach
  aufkleben; Muster soll die nutzbare A4-Fläche weitgehend ausfüllen.
- Eigene einseitige Vektorvorlage `output/pdf/uwa_mobile_charuco_A4_1to1.pdf`:
  A4 quer297×210mm, Muster266×190mm,7×5 Felder38mm, Marker28mm,
  DICT_4X4_100 IDs75–91, weiße Ränder15,5mm seitlich/10mm oben und unten.
  Kontrollstrecke100mm. Tischboards40mm/IDs0–16 und50–66 bleiben unverändert.
- Definition `uwa_cell_description/config/mobile_charuco_a4.yaml`, Generator
  `scripts/print_mobile_charuco.py`, Bedienung `docs/mobile_charuco_a4.md`.
  Isolierte Druckumgebung `.venvs/charuco-print`, keine ROS-/Hardwareänderung.
- Prüfung am tatsächlichen300-dpi-PDF-Render:17/17 Marker,24/24 Ecken,
  maximale metrische Eckabweichung0,082mm. PDF-Geometrie38mm-Felder,
  100mm-Strecke, A4/1Seite und Vektorinhalt geprüft, abschließende Sichtprüfung
  bestanden. Report `docs/mobile_charuco_a4_print_validation_2026-11-11.json`.
- Physischer Ausdruck noch nicht nachgemessen.100%/Tatsächliche Größe drucken,
  Seitenanpassung aus;100mm-Strecke und38mm-Feld nachmessen. Mattes Papier
  vollflächig faltenfrei kleben, weißen Rand erhalten, Halter außerhalb Muster.
  Bewegliches Board noch nicht in Detektoren aktiviert; eigene Definition
  explizit verwenden. Werkzeug-Board-Transformation unbekannt/nicht kalibriert.

## Left rear: GUI-/ROS-Treiberstart geprüft,2026-11-11

- Nutzer beauftragt Aufnahme in GUI und echten Treiber-/Starttest. Individuelle
  Werkskinematik erfolgreich rein lesend aus192.168.8.169 extrahiert, im Inventar
  hinterlegt. Datei setup/calibration/hardware_first_view/ur_kinematics/left_rear.yaml,
  Hashcalib_12205487632174246172; konfigurierter Typur7e, Modellressourcen vorhanden.
- Zusätzliches echtes Qt-UWA-Fenster **UWA · Direct UR Test · Left rear** offen,
  eigener Treiber ausschließlich left_rear/Domain66/Ports52001–52004. Bestehendes
  rechtes Besitzerfenster18120 und dessen Treiber18238/18239 erhalten. Nicht als
  allgemeine zukünftige PID-Konfiguration verwenden; laufender Stand neu prüfen.
- GUI Start drivers, Read joint angles undPrepare UR erfolgreich. Sechs reale
  präfixierte Gelenke/2592Samples/493,94Hz, gemeldete Geschwindigkeiten0rad/s,
  maximale Positionsstreuung0,000102rad. Fünf Broadcaster aktiv, vier Motion-
  Controller inaktiv, keine Fahrziele. Prepare bei bereits RUNNING/NORMAL ist
  kein Nachweis eines Kaltstarts ausPOWER_OFF oder echten Bremsenlösens.
- Nach Nutzerbestätigung Host192.168.8.209/Port52002 undRemote: UR bereits
  PLAYING ros.urp/Remote=true vor PC-Prüfung. Kein Programmneustart gesendet.
  Treiberlog bestätigt Programmanfrage/-übertragung und Reverse-Verbindung.
  External-Control-Link18:23AWST per reliable/transient_local gelatchtem
  robot_program_running=true bestätigt, nativer SafetyMode1/NORMAL.2430
  Gelenksamples bei492,55Hz, alle gemeldeten Geschwindigkeiten0rad/s,
  Positionsstreuung0,000104rad. Alle vier Bewegungscontroller weiter inaktiv.
  Programm-/ROS-Verbindung damit geprüft, keine Bewegungserprobung behauptet.
  Erster Diagnoseempfang mit volatile-Sensor-QoS lieferte keinen gelatchten
  Linkwert; korrigierter Empfänger mit passender QoS liefert den Status.
- Gelegentliche500Hz-Overrun-Warnungen beobachtet; kein Echtzeit-/Fahrnachweis
  aus bloßem Gelenkempfang. Report/Screenshots unter setup/logs/uwa-left-rear-driver/,
  Sitzung20261111_181624_259914_22b7a96c; Werkskinematiklog
  setup/logs/uwa-left-rear-factory-kinematics.log. [Bedienung](docs/ur_control_gui.md).
- Arbeitsstatus work/left-rear-driver.md abgeschlossen: GUI/Treiber-/Prepare-/
  External-Control-Verbindungstest erfolgreich. Nachweise external-control-result.json
  undgui-status-confirmed.json unter setup/logs/uwa-left-rear-driver/.
  Neues linkes Besitzerfenster/Treiber offen lassen; rechte Treiber unverändert.
  Keine Trajektorien-/Jog-/Kalibrierfahrt ausgeführt. Andere Front-Ergebnisse erhalten.

## Hinterer linker UR erreichbar,2026-11-11

- Nutzer meldet hinteren linken Roboter unter8.169. Zugeordnet als
  **left_rear=192.168.8.169**,Inventar und Arbeitsregeln ergänzt; kein neuer
  Hardwaretreiber gestartet. Nur lesende Netzwerk-/Dashboard-/Kameraabfragen.
- Ethernet enp87s0/PC192.168.8.209;3/3 Pings,0% Verlust,0,278ms im Mittel.
  Ports29999,30001,30002,30003,30004 und4242 erreichbar.
- Dashboard18:07AWST: RUNNING,NORMAL,STOPPED ros.urp,Remote=false;
  PolyScope5.25.0.130258,Seriennummer20265701623,ModellantwortUR5. Vorhandenen
  konfigurierten Typur7e erhalten: Dashboardfamilienname allein ist kein
  unabhängiger Nachweis der tatsächlichen UR5e-/UR7e-Variante.
- Kamerahello: UCC3.44.0.149696,FirmwareCQ0-1.4.0,Normal,
  uniqueCamId06561F1400090106. Kein Bild-/Fokus-/Beleuchtungswechsel vorgenommen.
  Nachweis setup/logs/uwa-left-rear-reachability-20261111.json.
- Eintrag work/left-rear-reachability.md abgeschlossen; keine Power-/Brake-/
  Play-/Reset-/Bewegungsbefehle, Front-Kalibrierarbeit erhalten.

## Kamera-USB nach Nutzerupdate sichern,2026-11-11

- Nutzer aktualisiert Kamera-URCap selbst, meldet anschließend „Vision system
  down … files extracted correctly“ und stellt den Robotiq-Stick am PC bereit.
  Neues Ziel: vollständiges Image plus Dateisicherung, danach passendes Paket
  direkt ins USB-Wurzelverzeichnis. Nutzer bestätigt Zielversion **4.1.0**.
- Kingston16GB,Seriennummer E0D55EA574E5F3A1E91F0FDB,FAT32/KINGSTON/289C-1ADC:
  alter Stand UCC1.11.1.10337/VSL1.0.23. Vollständiger Gerätelesevorgang erfolgreich,
 15472047104Bytes; unabhängige SHA256-Gegenprüfung **identisch**, Hash6319d351…83ab746.
  Zusätzlich310 Dateien/1263252963Bytes unter files/ gesichert und manifestiert.
  USB-Dateiaustausch nach Zielversionsbestätigung4.1.0 erfolgreich: neuer
  vision_system-Ordner/VSL2.0.0 und Camera-URCap4.1.0.164735 direkt im Root.
  Alle303 Dateien nach Aushängen/RO-Neumount SHA256-identisch zum Paket, keine
  alten Zusatzdateien im vision_system. Sieben übrige Originaldateien unverändert.
  Um16:42AWST ausgehängt, bereit zum Abziehen. usb-update-report.json als Nachweis.
  Nutzer bestätigt anschließend: Wiederherstellung hat funktioniert.
  Dies ist eine Nutzerbestätigung, kein zusätzlicher eigener Pendanttest. Sicherung setup/backups/robotiq-usb/20261111-before-ucc-update/.
- Separat geprüftes ZIP UCC4.1.0 enthält303 Dateien undVSL2.0.0; Startskript
  verlangt diesen VSL-Stand. Versionsmischung ist plausible Fehlerursache,
  aktuelle Controllerinstallation nicht selbst geprüft. Dateien nicht aus
  verschiedenen Versionen mischen. Alte eingebettete SHA1-Tabelle passt schon
  nicht vollständig zum neuen Originalpaket; maßgeblich ist der ZIP-Abgleich.
- Arbeitsstatus work/wrist-usb-recovery.md; [Anleitung/Prüfbefund](docs/wrist_usb_recovery_2026-11-11.md).
  Andere Front-/Bahnplanungsarbeiten erhalten; keine Roboterfahrt, ROS-/
  Controllerneustarts, SSH-Anmeldung oder Hersteller-Installer am PC.

## Front-Versuch mit62 Bildern abgeschlossen; Hand-Auge nicht freigegeben,2026-11-11

- Nutzer hat neue Rear-Parkvorschau und anschließend die gesamte Front-
  Erstansicht/62-Bilder-Folge bei freiem Fahrraum konkret freigegeben.
  Ursprüngliche Ziele und Fit-/Prüfrollen in allen Wiederaufnahmen erhalten,
  nur Verbindungen aus jeweils neu gelesenen Winkeln neu geprüft. Genau ein
  Arm gleichzeitig, komplette MoveIt-Zelle; linke Nutzer-Home-Stellungen
  weiterhin nominell. Keine Power-/Brake-/Play-/Reset-Aktionen durch Agenten.
- Rear-Parken erfolgreich:56,5068s, native skalierte JTC SUCCEEDED/0,
  Zielabweichung0,0000296rad. Plan/Freigabe/Ergebnis unter
  setup/calibration/parking/right_rear_20261111/; Fingerprint
 49e218e0b86a4910826d23c5d1250a82366e32c5d0ef3892f4dc0944259869f3.
  Front-Erstansicht78,903s ebenfalls erfolgreich,0,0000318rad Endfehler;
  approach/ unter Front-Datensatz. Reales Board24 Ecken.
- Front-Kameradienst nach Nutzer-URCap-/USB-Recovery wieder erreichbar640×480.
  Ein Autofokustrigger verursachte HTTP-Reset; danach keinen weiteren Trigger
  verwendet. Tatsächlich scharfen Fokus435 manuell fixiert, mehrere frische
  Bilder/ForceRefresh bestätigen435Manual/60000µsManual/Gain16. LED-Readback1/53,
  keine physische LED-Leistungsbehauptung. Original-/Diagnosezustände erhalten.
- **Datensatz vollständig:** setup/calibration/hardware_handeye/right_front_20261111/.
 62 akzeptierte, unterschiedliche Bilder=50 Fit/12 vorab reservierte Prüfbilder,
 14…24 Ecken, fester435-Fokus. Observierte Bildpunkte x117…586/y76…402, breiter
  als Rear-Reihe; keine Behauptung vollständiger Randabdeckung. HTTP-Bilder
  stationär über wechselnde Payloads zugeordnet, ohne Sensorbelichtungszeit.
- **Intrinsics PASS:** Fit-RMS0,28901px, Median Prüf-RMS0,29924px.
  fx660,868/fy665,589px, cx328,433/cy176,219px; vollständige K/D/Unsicherheiten
  in intrinsics.json. Nicht als gleiche Optik wie Rear404-Fokus behandeln.
- **Hand-Auge FAIL:** unabhängige12 Prüfbilder Median-Reprojektion0,74780px,
  Boardpositions-RMS2,34399mm (beides innerhalb Grenze), Rotations-RMS0,65195°
  über0,5°. Keine Ausreißer ausgeschlossen. Profil **activated:false**,
  keine TF-/Hardware-/Gazebo-Montage geändert. Keine Gütegrenzen gesenkt und
  kein günstigeres Subset als Ersatzprofil gewählt.60er-Zwischenstand mit49
  Fit/11 Prüfung bereits bei0,670° gescheitert, separat in analysis_60_views/.
- **Bildzahlvergleich innerhalb Front-Kamera:** dieselben12 Prüfbilder,
  vier deterministische verschachtelte Teilmengen bei20/33 Fit-Bildern und
  einmal alle50. Rotations-RMS20:0,623…0,775°,33:0,607…0,745°,50:0,652°.
  Bildfehler ebenfalls ähnlich (etwa0,72…0,80px). Kein klarer großer Gewinn
  allein durch höhere Bildzahl; alle Varianten verfehlen Rotationsgrenze.
  Kein formaler Signifikanztest/kein absoluter Genauigkeitsnachweis.
- Versionierte Bewertung unter evaluation_v1/: intrinsics.json,
  handeye_result.json, manifest.json mit SHA256, count_summary.json,
  validation.png/count_comparison.png. Vergleichsdetails count_comparison/.
  [Befund/Bedienung](docs/front_calibration_2026-11-11.md).
- Unterbrechung043: Kabel verdeckt Board,9 Ecken -> automatischer Bildabbruch/
  Front inaktiv. Nutzer sichert Kabel ohne Kamera-/Boardbewegung; neun gemeinsame
  Ecken vor/nach Sicherung Median0,025px/Maximum0,063px Verschiebung. Abgelehnter
  Versuch mit SHA256 unter rejected/sample_043_attempt_01/ erhalten, gleiche
  Pose neu mit24 Ecken aufgenommen, Originalziele44…61 fortgesetzt.
- Unterbrechung060: nativer C153A5/Wrist3 am17:50:33Perth, vom Nutzer als
  gespannter/aufgewickelter Kabelstrang bestätigt und gelöst. Pending-Action
  per SIGINT gecancelt/Front inaktiv, kein automatisches Quittieren. Native
  Zustände danach NORMAL/PLAYING, tatsächliche neue Stellung eingelesen;
  letzte zwei Originalziele neu geprüft/erfolgreich ausgeführt. Kamera beim
  Wiederanlauf auf424Auto zurückgesetzt, vor Weiterfahrt435Manual identisch
  wiederhergestellt und dreifach per Hardware-Readback geprüft.
- Behobene Ablauf-Lücke: ProtectiveStop kann Programmlinktrue beibehalten.
  JointObserver liest jetzt tatsächliches natives SafetyMode und cancelt die
  eigene Action bei Stop-Modi sofort; NORMAL/REDUCED zulässig. Keine neuen
  Dashboard-/Remote-/Armzahl-/GUI-Besitz-Gates.22 abschließende gezielte Tests
  bestanden, zusätzlich3 Standard-Vierarm-/Fit-/Holdout-Regressionen.
- Endzustand18:03Perth: beide URs NORMAL/PLAYING/Linktrue. Rear hält Parkpose,
  Front hält letzte Aufnahmepose mit aktivem skalierten JTC; übrige Bewegungs-
  controller inaktiv. Frontzielabweichung0,0000460rad, Rear-Endvergleich zum
  letzten Wiederaufnahmestart0,0000858rad (kein Maximum über gesamte Reihe).
  completion_state.json. Eigene Vorschauen beendet, Hardware-GUI/Treiber offen.
- Front-Dashboardversion nach Nutzerupdate5.26.3.140631 gemessen und erst nach
  allen Fahrten im Inventar nachgeführt; Rear unverändert5.10.1.106310.
  Alte gespeicherte Planfingerprints dadurch zusätzlich veraltet, für neue
  Fahrten neu planen. Keine bestehende geprüfte Trajektorie nachträglich geändert.
- Nächster fachlicher Schritt: Ursache der Rotationsinkonsistenz gezielt prüfen
  (Bild-Pose-Schätzung/Intrinsics/Board und mechanische Stabilität), statt nur
  mehr gleichartige Bilder aufzunehmen. Hypothesen nicht als nachgewiesene
  Ursache ausgeben. Kabelführung muss den ganzen vorgesehenen Wrist-Bereich
  erlauben; Sichtblockade und Wrist3-Kabelspannung wurden real beobachtet,
  der lose Kabelverlauf ist nicht Teil der Kollisionsgeometrie. Kein validiertes
  Front-Hand-Auge-/relatives-Basisprofil
  übernehmen, bevor unabhängige Prüfgrenze bestanden ist.

## Erfolgreich abgeschlossen: reale Hand-Auge-Reihe, 2026-11-11

- **Qualitätsnachfrage, gleicher Tag:** Nutzer erwägt Rear-Parken und Front-
  Kalibrierung mit50% mehr Bildern. Offline-Test mit20/26/33 Fit-Bildern gegen
  dieselben8 Prüfaufnahmen zeigt keinen klaren monotonen Bildzahlgewinn;
  Intrinsics etwa0,22px, Hand-Auge etwa0,40–0,50px. Kein Beweis, dass mehr oder
  räumlich vielfältigere Bilder nichts bringen. Post-hoc-Diagnose, keine
  Änderung/Neuauswahl des gespeicherten Profils. Details und Vergleichsdesign
  [Qualitätsbewertung](docs/calibration_quality_review_2026-11-11.md).
  Empfehlung: Front separat ca62 Ansichten mit50 Fit/12 reservierter Prüfung,
  bessere Bildabdeckung und Teilmengenvergleich innerhalb derselben Kamera.
  Gleicher Kameratyp nicht als identische individuelle Intrinsics behandeln;
  gemeinsames Board dient später relativer Basispose. Noch kein neuer realer
  Park-/Frontweg aus diesem Vorschlag freigegeben oder ausgeführt. Dafür
  bisherige Code-Anzahlgrenzen gezielt anpassen, keine Gütegrenzen absenken.

- **Ergebnis15:43Perth:** alle32 Restaufnahmen ohne erneuten Schutzstopp
  abgeschlossen. Insgesamt41 akzeptierte Ansichten mit je24 Ecken,33 Fit/8
  vorab reservierte Prüfbilder, keine Ausreißer ausgeschlossen. Manuell404,
 640×480,60000µs/Gain16; alle41 decodierten Bildhashes unterschiedlich.
- Intrinsics **PASS**: Fit-RMS0,24368px, Median der Prüf-RMS0,22200px;
  fx659,800/fy664,507px, cx317,123/cy180,567px. Reale Daten, kein nominelles K.
- Hand-Auge **PASS** samt vorhandener Profilvalidierung: unabhängige8
  Prüfbilder Median-Reprojektion0,46553px, Boardpositions-RMS2,65977mm,
  Rotations-RMS0,24623°. Bootstrap der Kameramontage ungefähr1mm je Achse und
 0,137°; Wiederholbarkeit/interne Konsistenz, **keine absolute Genauigkeitszusage**.
  Geschätztes T_tool0_camera XYZ[0,808;50,141;22,583]mm; vollständige Matrix
  und Verzeichnung in den Ergebnisdateien. Kein Layout-/Ground-Truth-Fit.
- Ergebnis aktiviert **false**: keine TF-/Hardware-/Simulationsprofile geändert.
  Versionierte Kopie unter setup/calibration/hardware_handeye/
  right_rear_20261111/result_v1/{intrinsics.json,handeye_result.json,manifest.json,
  validation.png}. Manifest enthält SHA256 der Ursprungsdateien; ursprüngliche
 9 Aufnahmen unverändert erhalten. Rohdatensatz bleibt right_rear_20261110/.
- Abschlussprüfung: Rear-Zielabweichung0,0000343rad; Front-Abweichung gegenüber
  neuem Start0,0000472rad (Endvergleich, kein Maximum über die gesamte Reihe).
  Rear-scaled-JTC hält letzte Aufnahmepose aktiv, alle Front-Bewegungscontroller
  inaktiv. Beide URs NORMAL/PLAYING, Front Local und Rear Remote. Keine Befehle
  an andere Arme, keine Rückfahrt. Nur eigene Domain68-Vorschau sauber beendet;
  UWA-Arms-GUI und rechte Treiber bleiben offen. completion_state.json gesichert.
- Grenzen: stationäre HTTP-Bilder ohne Belichtungszeitstempel; Bildrand nicht
  validiert (beobachtete Ecken etwa x140…431/y123…341). Ergebnis gilt für
  den verwendeten Modus, Fokus und unveränderte Kameramontage. Noch keine
  Einmessung der Frontkamera, Tisch-/Basisrelation oder statischen OAK.
- Nächster fachlicher Schritt: Profil ausdrücklich/gezielt in ein separates
  kalibriertes Anzeigemodell übernehmen und an zusätzlichen, unabhängigen
  Prüfposen bzw. Messreferenzen prüfen; danach zweiter Arm gegen dasselbe
  feste Board. Keine weiteren realen Ziele aus diesem Abschluss ableiten.

### Historische Anlaufdiagnose der Wiederaufnahme

- **Aktueller Stand15:35Perth:** Front unter derselben IP wieder erreichbar,
  beide rechten echten Gelenkstände gelesen; Front-Parkpose annähernd erhalten.
  Rear PLAYING/native External Control true, beide NORMAL, Bewegungscontroller
  vor Aufnahme inaktiv. Alle32 ausstehenden Ziele unverändert zur freigegebenen
  Originalfolge, Wege aus aktuellen Winkeln neu berechnet und vollständig
  geprüft (`--check-only` erfolgreich). Nur erster Verbindungsweg geändert,
  Dauer2,54s; Gesamtbewegungszeit256,8s. Neue Vorschau Domain68 geöffnet.
  Resume-Fingerprint627571fd735af233510cdbc364a8d990fa46fdee6c874a3f5996af5889429f2b,
  Artefakte right_rear_20261111/resume_plan/, Nutzerkontext operator_context.json.
  Freigegebene Fortsetzung läuft ausschließlich Rear, Log
  setup/logs/uwa-handeye-resume-run.log. Noch keine Ergebnisse behaupten;
  ursprüngliche9 Bilder und Fit-/Prüfrollen erhalten. Keine anderen Armkommandos.

- Nutzer hat die Sicherheitsebenen nach eigener Aussage angepasst und die
  Fortsetzung beauftragt. Die gestrige Pause ist aufgehoben; die neue
  Ebenenposition ist noch nicht unabhängig vermessen/importiert.
- Aktuelle Erstprüfung: right_rear erreichbar, NORMAL/Remote, aber POWER_OFF
  und ros.urp STOPPED. right_front Dashboard nicht erreichbar. Nach Neustart
  keine bisherigen UWA-Prozesse vorhanden; UWA Arms gezielt mit beiden rechten
  Treibern geöffnet, sämtliche gestarteten Rear-Bewegungscontroller inaktiv.
  Rear liefert bei POWER_OFF sechs Nullwerte; diese ausdrücklich **nicht** als
  gültige reale Startstellung verwenden. Front bisher ohne Live-Zustände.
- Nutzer bestätigt Vorbereitung, unveränderte Board-/Kameramontage/linke
  Home-Stellungen und freien Fahrraum. Reale Nachprüfung: GUI-Prepare hinten
  rechts erfolgreich, echte plausible Encoderstände wieder verfügbar,
  RUNNING/NORMAL/Remote; Programm zunächst weiterhin STOPPED/kein natives
  Linkflag. Front-Prepare fehlgeschlagen: kein Ethernet-Nachbar, kein Ping/
  Dashboard/RTDE unter192.168.8.103. Nutzer um Front-Einschalten/IP-Prüfung
  (alternativ aktuelle Pendantwinkel) und Rear-Play gebeten. Keine eigenen
  Power-/Brake-/Play-Aktionen oder Bewegung; kein neuer ausführbarer Restplan
  ohne aktuelle Frontstellung. Diagnose uwa-handeye-resume-after-prepare.json.
- Spätere Prüfung13:33Perth: Rear RUNNING/NORMAL/Remote, ros.urp PLAYING,
  natives robot_program_running=true und54001/54003/54004 tatsächlich verbunden.
  Stationäre Diagnoseaufnahme unter right_rear_20261111/readiness/:
 24 Ecken, drei unterschiedliche Bildpayloads, Fokus404/Manual erhalten.
  Diese Aufnahme ist separat und zählt nicht als neue Haupt-Messansicht.
  Front laut Nutzer eingeschaltet, meldet am Pendant wiederholt kein Netzwerk.
  Rein lesende Dashboard-Suche im192.168.8.0/24 fand nur Rear; keine geänderte
  Front-IP nachgewiesen. Nutzer um sechs aktuelle Front-Pendantwinkel in Grad
  oder die aktuelle Pendant-IP gebeten. Danach Front als manuell gemessenes
  festes Hindernis möglich; keine Bewegung/Power-/Programmaktion für Front nötig.
  Diagnose uwa-handeye-network-dashboard-discovery.json, Aufnahmeprüfung
  uwa-handeye-resume-readiness-capture.log.
- Kamera wieder erreichbar640×480; nach Neustart zunächst Autofokus/Autoexposure.
  Vorherige Einstellungen gesichert und Fokus404/Manual,60000µs/Manual,Gain16,
  LED53 wieder gesetzt. ForceRefresh meldete zunächst LED-Modus1 statt
  angefragtem2. Nach Rear-Vorbereitung Modus2/53 erneut gesetzt und über drei
  HTTP-Bilder stabil zurückgelesen, Fokus404 unverändert; noch kein Nachweis
  physischer LED-Leistung. Livebild24/24 Ecken. Daten unter
  setup/calibration/hardware_handeye/right_rear_20261111/; Diagnose
  setup/logs/uwa-handeye-resume-{status,live}.json.
- `handeye_hardware resume-series` ergänzt: vorhandene akzeptierte Aufnahmen
  als zusammenhängendes Präfix verifizieren, IDs und Fit-/Prüfrollen erhalten,
  verbleibende Ziele mit neuen MoveIt-geprüften Wegen ab aktuellem Zustand
  planen. Originalbatch/Rohbilder unverändert, Hashbindung vorhandener Bilder/
  Records und Prüfung identischer Werkskinematik. Keine blinde Wiederholung
  des unterbrochenen Segments. Noch kein realer Fortsetzungsplan erzeugt.
-13 gezielte Offline-/MoveIt-/Aufnahme-/Intrinsics-Tests bestanden; Log
  setup/logs/uwa-handeye-resume-tests.log. Fit prüft zusätzlich die vorhandenen
  Profil-Gütegrenzen einschließlich Transformationsplausibilität;
  keine automatische Aktivierung. Bisher9 Aufnahmen,32 fehlen (25 Fit/7 Prüfung),
  kein fertiges Intrinsics-/Hand-Auge-Ergebnis.

## Historischer Pausenstand: reale Hand-Auge-Reihe, 2026-11-10

- **Damals auf Nutzerwunsch pausiert; am2026-11-11 aufgehoben.** Bestätigte Ursache des Stopps:
  eine konfigurierte Sicherheitsebene in der UR-Steuerung. Nutzer kann sie
  aktuell nicht deaktivieren und möchte sie morgen,2026-11-11, verschieben.
  Heute keine weiteren Hardwarefahrten/automatischen Wiederanläufe. Keine
  Sicherheitsparameter durch den Agenten geändert oder Stopps quittiert.
- Reale erste Aufnahmesicht hinten rechts erreicht und anhand echter Bilder
  bestätigt: nach freiem Sichtfeld24/24 ChArUco-Ecken. Nicht als exakt angefahrene
  Nominalpose ausgeben: erste Annäherung wurde bei0,0331rad Restabweichung beendet.
  Aufnahmen verwenden die tatsächliche gemessene Stellung und Werkskinematik.
- Nutzer bestätigt rechtes A3-Board1:1 und100mm Kontrollstreifen, Position etwa
  wie Modell. Keine bekannte Wrist-Intrinsics-Kalibrierung. Eigene ChArUco-
  Intrinsics vor Hand-Auge vorbereitet; URCap-Full-Calibration erklärt, nicht
  gestartet. Nominelles K/optische Montage nur für Planung, nicht für den Fit.
- Individuelle Werkskinematiken beider rechter URs rein lesend extrahiert und
  im Hardwareinventar referenziert: setup/calibration/hardware_first_view/
  ur_kinematics/{right_front,right_rear}.yaml. Kein Treiberneustart dafür.
- Nach gesonderter RViz-/Fahrraumfreigabe40 weitere Ansichten geplant und
  begonnen (native skalierte JTC,0,05rad/s,0,10rad/s²). Bei Bewegung zum Bild
  **sample_009** nativer PROTECTIVE_STOP/C400A0; Verbindungsverlust sofort
  erkannt, Action gecancelt, Rear-Bewegungscontroller deaktiviert. UR ordnet
  [C400 der Ellbogennähe zu Sicherheitsebenen zu](https://www.universal-robots.com/manuals/EN/HTML/SW10_8/Content/prod-err-codes/topics/CODE_400.html).
  Die konfigurierte Ebene war nicht Teil der bisherigen FCL-Kollisionsszene.
- **Datensatz:** setup/calibration/hardware_handeye/right_rear_20261110/.
  records/sample_000.json bis sample_008.json samt Roh-/annotiertenJPEGs:
  **9 akzeptierte Aufnahmen**, alle24 Ecken;8 Fit,1 Validierung. Kamerafokus404
  manuell,640×480, Belichtung60000µs manuell, Gain16, LED53Manual. Wechselnde
  Payloads bei Stillstand belegt, kein Sensor-Belichtungszeitstempel vorhanden.
  Keine ausreichende Datenzahl für validierte Intrinsics/Hand-Auge; nichts
  als kalibriertes Hardware-/TF-Profil aktiviert.
- Batch samt Betreiberfreigabe unter batch_plan/, Fingerprint
  80efa418b687052cf63d3010c608c3b4a91b16cdf5f07e630b30d60b8b3f8773.
  Aktueller Pausenzustand in paused_state.json; Diagnose
  setup/logs/uwa-handeye-hardware-{run.log,interruption-status.json}.
  Im zuletzt gelesenen Zustand UR NORMAL, ProgrammSTOPPED, Local stattRemote;
  nicht selbst wieder auf Remote/Play setzen. Front-Parkpose erhalten, linke
  Arme weiterhin nur nominell Nutzer-Home, keine Befehle an andere Arme.
- Software: handeye_hardware plan-view/capture/plan-series/run-series/fit;
  getrennt vom unveränderten Simulationsbackend.31 gezielte Tests bestanden,
  tatsächlicher ros2-run-Prozessgruppen-SIGINT im Mock prüft Cancel/Deaktivieren
  mit0rad Nachdrift. Erststart-Shell- und rclpy-Signalfehler wurden korrigiert.
  [Bedienung/Prüfpfade](docs/hardware_handeye.md).

**Historische Vorbereitung vor der inzwischen abgeschlossenen Fortsetzung:** aktuelle echte rechte
Stellungen und Kamera-/Boardzustand lesen, native Sicherheitsebene mit neuer
Position berücksichtigen, verbleibende Wege neu prüfen/visualisieren. Keine
alten Startstellungen oder alte Freigabe als blind gültig übernehmen. Bestehende
Bilder nicht überschreiben. Der aktuelle Batch-Runner verweigert absichtlich
einen Neustart bei bestehenden sample_001…-Dateien; für Fortsetzung neue Sitzung
oder eine explizit geprüfte Wiederaufnahme ergänzen. Alte Bilder lassen sich
für Hand-Auge nur bei unveränderter Board-/Tisch- und Kameramontage zusammenführen;
für Intrinsics muss zumindest das Optik-/Bildmodusprofil identisch bleiben.
Danach genügend Fit-/Validierungsansichten aufnehmen, Intrinsics und erst dann
Hand-Auge auswerten. Kein automatischer Profilwechsel oder Rückweg.

## Hardware-Wartepose vor Kamerakalibrierung, 2026-11-10

- Nutzer bestätigt erfolgreiches reales Jogging hinten rechts. Neuer Auftrag:
  allgemeines Parkskript, zunächst vorne rechts real testen. Linke Arme laut
  Nutzer bereits aufrecht in Default Home; nominell [0,-90,0,-90,0,0]° als
  user_nominal_home dokumentiert, keine gemessenen Encoderstände behaupten.
- Neues park_arm plan/preview/execute in uwa_cell_control. Zentraler Zelllayout-
  und Hardwareinventarbezug, bestehende vollständige MoveIt-Kollisionsszene,
  lokale quintische Wege mit maximal0,005rad Sampleabstand; keine OMPL-Umweg-
  Planung. Fehlende Zustände machen einen Plan zur nicht ausführbaren Vorschau.
  Vorschau getrennt in Domain68, echte Hardware66/Mock67/Gazebo64 unverändert.
  [Bedienung](docs/hardware_parking.md).
- Ausführung als generische MATCH-Funktion trajectory.execute_trajectory über
  nativen skalierten Hardware-JTC bzw. Mock-JTC. Genau ein Arm, keine Power/
  Brake/Play-/SSH-Kommandos oder automatische Rückfahrt. Aktuelle Startstände,
  Modell/Inventar und vollständigen Pfad vor Fahrt erneut prüfen. Andere rechte
  Live-Arme auf Poseänderung überwachen; Telemetrieverlust cancelt/deaktiviert.
- Vorne rechts alte ROS-Instanz41381 zeigte sechs Nullwinkel trotz RUNNING und
  aufgebauter Reverse-Verbindung. Unabhängiger Ausgabe-only-RTDE-Client lieferte
  plausible actual_q. Nur alten Front-Launch41338 nach Prüfung inaktiver Bewegung
  ersetzt; beide rechten Treiber in neuer GUI inaktiv gestartet. ROS-Winkel
  danach mit RTDE konsistent;53002/54002 lauschen, Programme zuletzt PLAYING.
  Keine Power-/Brake-/Play-Befehle durch den Agenten. Diagnose im Workspace
  setup/logs/uwa-parking-{front,rear}-rtde.json und uwa-parking-ready-*.json.
- Zwei Pakete gebaut und23 gezielte Offline-/MoveIt-/GUI-/Adaptertests bestanden.
  Vollständiger Mock-Parkweg etwa38,35s, Endfehler1,1e−16rad, andere simulierte
  Zustände unverändert. Ausfall einer stationären Mock-Zustandsquelle während
  tatsächlicher Fahrt cancelt/deaktiviert; Nachdrift0rad. Logs
  setup/logs/uwa-parking-{build,tests,live}.*. Bestehende Kalibrierung unverändert
  Simulation-only; keine zusätzliche automatische Hardwarekalibrierung aktiviert.
- Konkreter echter Front-Plan: setup/calibration/parking/right_front_hardware/
  plan.json; Fingerprint7044e86ce9029d3805047324fc87fceefd4d06e13ecd180e318e6b437d323bc6.
  tool0 Ziel ungefähr [0,8504,-0,6741,1,5500]m,620 geprüfte Zwischenstände,
  Dauer61,81s, Limits0,05rad/s und0,10rad/s². Rechte Startwerte live gemessen,
  linke nominell Home. Abschließender --check-only erfolgreich. PNG geprüft;
  eigene RViz-Animation auf Domain68 geöffnet. Fremdes Fenster-Screenshot ergab
  schwarz; deshalb keine erfolgreiche vollständige Screenshot-Sichtprüfung
  behaupten. Nutzer hat die konkrete Vorschau selbst geprüft und **„Vorschau
  passt, Fahrbereich frei – Parkversuch starten“** freigegeben; Freigabe mit
  Fingerprint lokal in operator_approval.json. Erster Realversuch nach16,5s mit
  nativer Pfadtoleranzverletzung0,200rad abgebrochen, Controller wieder inaktiv.
  Beobachtete Frontänderung nur0,000125rad, hinten0,000101rad (Messrauschen).
  Diagnose: DashboardPLAYING ist kein Nachweis einer Reverse-Verbindung;
  aktuell kein53001/53003/53004-Socket und kein robot_program_running-Sample.
  GPIO publiziert nur Zustandsänderungen; fehlendes Sample ist kein gemessener
  false-Wert. Nutzer um Stop→Play vorne rechts gebeten, Freigabe für denselben
  gespeicherten Weg gilt fort. Keine Toleranzgrenzen gelockert. Logs
  uwa-parking-hardware-execute.log, uwa-parking-hardware-motion.json und
  uwa-parking-front-external-control.json.
- **Folgeversuch erfolgreich:** Nutzer Stop→Play ausgeführt, alle drei53001/
  53003/53004-Verbindungen bestätigt und natives Programmflagtrue. Gemeldeter
  Displayfehler „Trajectory socket53003 connected:false“ war bei Prüfung nicht
  mehr aktuell;53003 war verbunden. Genau derselbe freigegebene Plan ausgeführt,
  native skalierte JTC-Action SUCCEEDED/0. Maximaler Endfehler0,0000356rad,
  unabhängige spätere Lesung0,0000291rad. Hinterer rechter Arm maximal0,000101rad
  Änderung im Beobachtungsfenster, linke nicht kommandiert/ohne Live-Telemetrie.
  Ergebnis in setup/calibration/parking/right_front_hardware/execution_result.json;
  Logs uwa-parking-hardware-attempt2.log und uwa-parking-hardware-motion2.json.
  Abschließend Front-JTC hält Ziel, Rear-Bewegungscontroller inaktiv, Hardware-
  GUI/Treiber erhalten; eigene RViz-Vorschau sauber beendet. Kein Rückweg oder
  automatischer Hardware-Kalibrierlauf. Gelegentliche500Hz-Overruns und nicht
  fatale Typesupport-/MoveIt-Loggingwarnungen bleiben als technische Folgefrage.

## Ethernet und manuelles Jogging, 2026-11-10

- Nutzer hat Kabel ersetzt; Roboterrouten geprüft über enp87s0, PC192.168.8.209.
  Aktive Hinweise/Inventar zur temporären Funkverbindung entfernt. Historische
  Messungen und deren Transportbezug bleiben als überholt gekennzeichnet.
- Gewünscht: zuerst right_rear manuell mit dem MuR-Jogging und demselben
  dezentralen IntegratedCartesianAdmittanceController/J-PARSE bewegen; zunächst
  Nachgiebigkeit AUS. Keine automatischen Testfahrten durch Öffnen des Dialogs.
- Gemeinsame Qt-unabhängige MuR-Richtungsberechnung, UWA-Dialog ohne Lift/SSH,
  Base-Frame, Translation/Rotation, 20Hz while held, Loslassen/Space/Fokusverlust
  stoppt. Idle-Fenster senden keinen dauernden Nullstrom an andere Befehlgeber.
- Standard admittance/wrench_twist_gain sechs Nullen, use_ft_sensor=false und
  require_wrench=false. Controller liest Gains in on_init: ausdrückliches
  Aktivieren erstellt ihn zunächst inaktiv neu und lädt danach denselben Plugin-
  Typ. Ein dynamischer Parameterwert allein wäre dafür nicht ausreichend.
- Kollisionsalgorithmen und MuR-Standardprofil erhalten; UWA-Kollisionsoption
  weiterhin nicht als vollständiger Zellenschutz konfiguriert.
- Hardware bleibt Domain66, Mock jetzt strikt Domain67 in GUI, Kindprozessen,
  Launch und Jog-Transport; dadurch keine echte Managerentdeckung im Mockmodus
  und keine Fake-JointStates im lesenden RViz-Twin. Testnamespaces zusätzlich
  separat. Bedienung: [Jogging](docs/ur_jogging.md).
- Drei Pakete gebaut,19 gezielte Adapter-/UWA-Tests und acht MuR-Kartesiktests
  bestanden. Live-Mock in Domain67: Öffnen ohne Twist; beim Halt maximal0,028rad
  Gelenkänderung, nach Loslassen0,0rad weitere Drift im Messfenster. Rotation,
  Fokusverlust-Stopp und effektive Null-Gains/FT aus bestätigt.
  Logs setup/logs/uwa-jog-{build,unit,live,mur-cartesian}.*; Screenshot
  uwa-jog-dialog.png. Breiterer MuR-Test enthält eine bereits im HEAD vorhandene
  MiR-Fixture-Störung (QMainWindow ohne modules), kein Kartesik-Regressionsbefund.
- Hinten rechts alten nicht antwortenden Manager gezielt ersetzt, nach
  Dashboard STOPPED und fehlender Reverse-Verbindung; vorne rechts unverändert.
  Reales Preset lesend bestätigt: sechs Null-Gains für beide Parameter,
  use_ft_sensor/require_wrench=false. Broadcaster aktiv, Bewegung inaktiv,
  UR RUNNING/NORMAL/Remote, geladenes ros.urp STOPPED. Belege
  setup/logs/uwa-jog-hardware-{preset,after-restart}.json.
- Nutzer meldet URCap-Port50002 bei korrekter PC-IP; benötigt wird54002 für
  right_rear. Aktuelle native Prüfung: Route enp87s0/src192.168.8.209,
  drei Pings ohne Verlust0,317–0,344ms, Dashboard erreichbar; Treiber lauscht
  auf54002, kein Server auf50002. Ursache der genauen UR-Meldung nach
  Portkorrektur erneut prüfen. Keine realen Power-/Brake-/Play-/Fahrbefehle
  durch den Agenten; erster physischer Hold-to-jog-Versuch noch offen.
- Abschließender realer JointState-Lesetest liefert alle sechs endlichen
  right_rear-Gelenkwinkel, trotz STOPPED-Programm:
  setup/logs/uwa-jog-hardware-joints.json. Die früheren fehlgeschlagenen
  Empfangstests sind damit für diesen Arm überholt.
- Vollständiger Vierarm-Mock-GUI-Regressionslauf in Domain67 bestanden:
  24 eindeutige Gelenke, Ein-/Zwei-/Vierarm-Wechsel, Kartesik-Neuladen,
  Save logs, STOP, gezielter Managerexit/Neustart und eigener Abbau.
  setup/logs/uwa-jog-full-gui.log und uwa-control/mock-gui-validation.json.
  Installierte Desktop-Aktion RightRearJog via Gio geöffnet und sichtbares
  Haupt-/Jog-Fenster per X11-Fensterinventar bestätigt. Bestehende
  Hardware-Besitzerfenster erhalten; keine reale Controlleraktivierung.

## Englische UR-GUI und Sitzungsdiagnose, 2026-11-10

- Neuer Nutzerhinweis: schwacher Monitorkontrast; Klickannahme deutlich
  rückmelden. GUI mit kontrastreichem Button-Highlight (1,2s), großer dauerhafter
  RECEIVED/RUNNING/DONE/FAILED-Anzeige, Aktionsname/Detail und Laufzeit umgesetzt.
  Hintergrund-Statuspolls überschreiben manuelle Fehler nicht; Klicks/Ergebnisse
  zusätzlich im Sitzungslog und aktueller Feedbackzustand im Exportmanifest.
- Nutzerexport14:35:45 ausgewertet: Dashboard erreichbar/NORMAL/Remote, aber
  Manager hinten rechts seit13:59:00 mit−11 abgestürzt; State-Helper ebenfalls−11.
  Verwaister Launch41339 blockierte neue Starts. Nur diesen Rest beendet;
  künftige Manager-Exits räumen zugehörigen Launch samt Sperre automatisch auf.
  Nativer Segfault selbst noch ungeklärt, keine bewiesene WLAN-Ursache.
  [Diagnose](docs/ur_log_diagnosis_2026-11-10.md).
- Abschluss:17 Offline-Tests, Zwei-Paket-Build und isolierter Live-Mock-Test
  inklusive gezieltem Manager-Exit, Bereinigung nur dieser Instanz und anschließendem
  erfolgreichem Armneustart bestanden. Fehlerhafter alter GUI-Status nach
  Treiberexit wird verworfen. Logs setup/logs/uwa-feedback-{tests,build,live}.log.
  Kontrastreiche Darstellung anhand zweier Screenshots geprüft; aktuelle GUI
  über Desktop-Aktion geöffnet, ohne lebende Hardwaretreiber zu unterbrechen.
- Nutzerauftrag: aktuelle UR-GUI ins Englische übersetzen und Save logs für
  die aktuelle Sitzung ergänzen. Eigene Beschriftungen/Tooltips/Meldungen,
  eigene MATCH-Adapterantworten und Startmenü UWA Arms übersetzt. Native oder
  alte gespeicherte Logs werden unverändert erhalten.
- Eindeutige Sitzungsverzeichnisse unter setup/logs/uwa-control/sessions/.
  Vollständiges GUI-Log und gesonderte Prozessdateien inklusive Statusausgaben,
  Exitcodes; sichtbarer Logpuffer darf weiterhin gekürzt sein.
- Save logs als dauerhaft erreichbarer Button; Export im Hintergrund als
  tar.gz nach setup/logs/uwa-control/exports/. Neuester erfolgreicher Pfad in
  latest-export.txt daneben. Manifest: Zeitpunkte, Modus, Auswahl, letzte
  Statusdaten, PIDs, whitelisted Profilwerte, Dateiliste/Warnungen und Screenshot.
  Kein automatischer Roboterbefehl/Upload, kein vollständiger Environment-Dump.
- Passende seit Sitzungsbeginn geschriebene ROS-Dateien und ältere, noch von
  angehängten Treiberprozessen verwendete ROS-Logs erfassen. Altes gemeinsames
  gui.log explizit als inherited_context, damit Diagnose früherer Treiberstarts
  möglich bleibt. Wiederholte Exporte überschreiben keine vorherigen Archive.
- Offline-Prüfung:16 Tests bestanden, darunter archivierte Fehlerausgaben,
  getrennte Sitzungen, ROS-Auswahl, keine externen Symlink-Dateien und echter
  GUI-Button-Export während einer als laufend markierten Operation.
  Logs setup/logs/uwa-english-log-{tests,build,live}.log; Details Bedienungsdatei.
- Beide Pakete gebaut, isolierter Live-Mock-Test inklusive Save logs bei vier
  aktiven Mock-Controllern bestanden. Archiv enthält Prozessdateien, ROS-Dateien,
  Status-Snapshot und vier Treiber-PIDs; anschließend Controllerstopp und
  sauberer Abbau bestätigt. Beispielarchiv im JSON-Bericht
  setup/logs/uwa-control/mock-gui-validation.json verzeichnet.
- Englischen Desktop-Eintrag installiert/validiert und dessen Hardware-Aktion
  geöffnet. Nur treiberloses Vorgängerfenster ersetzt; Besitzerfenster und beide
  Hardware-Launch-Prozesse41338/41339 erhalten. Neue GUI UWA · Direct UR Test,
  Hardwaremodus/rear right; keine realen Power-/Brake-/Play-/Bewegungsbefehle.

## Aufbau der realen Zelle und Modellannahmen

### Parallele Simulation und gemessene Modelle in RViz, 2026-11-10

- Nutzerziel: beide echten rechten URs zusätzlich zu vier simulierten Armen
  gleichzeitig darstellen. Paket `uwa_cell_visualization`, bestehende cell.rviz
  erweitert: Simulation teilweise transparent, right_front gold, right_rear cyan.
- Ausschließlich zwei JointState-Abos auf Domain66, separate real_-Gelenke/TFs
  und RobotDescriptions auf Domain64. Keine Steuer-Topics/Services/Actions
  überbrückt und keine simulierten Zustände verändert. Eigenständige ROS-Contexts,
  Anzeigezeit an Simulationsuhr angepasst; Originalhardwaredaten unverändert.
- Modelle erst bei sechs vollständigen endlichen Positionen zeigen; WAITING/
  LIVE/STALE-Marker, nach2s ohne Daten Modell ausblenden. Walltime-Timeout gilt
  auch bei pausierter Simulation. LIVE bezeichnet ROS-Empfang, keinen unabhängig
  nachgewiesenen frischen RTDE-Sensorzeitpunkt.
- Montage aus zentralem Zelllayout (base_link relativ Tisch) bleibt vorläufig.
  Individuelle Werkskinematik aus Hardwareinventar optional, aktuell nominell.
  Reale Anzeige hat sechs UR-Gelenke ohne erfundene Greifer-/Kamerazustände.
  Offizielle STL-Schalen farbig dargestellt, keine neue Kollisionsprüfung.
- `cell.sh rviz`/Desktop-App starten `uwa-cell-hardware-overlay` idempotent mit.
  `cell.sh twin` separat; direktes cell.launch rviz:=true enthält optionales
  Overlay. Zell-Stopp beendet nur Visualisierung/Simulation, keine Hardwaretreiber.
- **Beide echten Datenströme LIVE** nachgewiesen. Vorne rechts war Controllerliste
  leer; ausschließlich joint_state_broadcaster geladen/aktiviert. Keine Power-/
  Brake-/Play-/Bewegungscontroller-/Zielbefehle. Hardwaretreiber weiterverwendet.
- Tatsächliche Abnahme: je6 endliche echte Gelenkwinkel, parallel48 simulierte
  Gelenke inkl. Tools, beide real_base_link-/tool0-TFs zur Welt vorhanden.
  `setup/logs/uwa-twin-real-acceptance.json`, Status `uwa-twin-live-status.json`.
- Vier Offline-Tests und isolierte Domain174/175-Prüfung: Modelle/TFs/Werte,
  keine künstliche Initialpose, keine Kommandopublisher, TF-Änderung bei pausierter
  Sim-Uhr, Stale-Ausblendung und unabhängige Wiederkehr beider Arme bestanden.
  Logs `setup/logs/uwa-twin-*`, visueller Screenshot `uwa-twin-rviz.png`.
  Anleitung [RViz-Vergleichsansicht](docs/rviz_digital_twin.md).
- Gemeinsame Visualisierungs-/Gazebo-Suite:61 Tests bestanden. Abschließender
  Dienststatus aktiv für Simulation/RViz/Scan/Overlay, beide Datenströme LIVE;
  `setup/logs/uwa-twin-live-status-final.txt`. RViz-Fenster vergrößert und Marker
  ohne überbreite Ogre-Leerzeichen für bessere Lesbarkeit gesetzt.

### Lokale UR-Vorbereitung und direkte UWA-GUI, 2026-11-10

- Nutzerwunsch: gemeinsame Start-/Bereitstellungs-/Admittanz-/Kollisionsbausteine
  in MATCH belassen; einfache UWA-Oberfläche mit vier Armauswahlen oben links,
  ohne SSH/rsync/mobile Infrastruktur. Adapter `match_ur_hardware`, Client
  `uwa_cell_control`; bestehende MuR-Algorithmen und Launch-Defaults erhalten.
- **Neueste Nutzerkorrektur:** zusätzliche UWA-Sicherheitsgates entfernen, um
  Bremsenlösen, Gelenkwinkel und Controllerwechsel auch per WLAN direkt zu testen.
  Damit sind frühere pauschale bzw. Ein-/Zweiarm-Sperren ausdrücklich überholt.
  Entfernt: Armzahl-/Aktivarmzählung/-lock, Dashboard-NORMAL/Remote/RUNNING/
  PLAYING-Vorprüfungen, exakter Programmpfadvergleich, Inaktivpflicht vor
  Bereitstellung, GUI-Treiberbesitzpflicht und rqt-Statusfreigabe.
- Native UR-Sicherheitsfunktionen, Treiber-Controller-Stopper, bestehende
  Kollisionsalgorithmen/Reglergrenzen nicht verändert. Technische Profil-/Port-
  Validierung und doppelte-Treiber-Schutz bleiben. Keine transportspezifischen Sperren.
  Dashboard-/Treiberablehnungen werden angezeigt; keine automatischen
  Schutzstoppquittierungen, kein automatisches Power/Brake/Play beim Launch.
- Standard nur `right_rear`; App UWA Arme, neues Fenster **UWA · Direkter UR-Test**.
  Domain66/localhost; Gazebo64/OAK65 unverändert. Hardwareinventar separat,
  links weiterhin keine IPs. Eigene Werkskinematik noch nicht hinterlegt.
- Prepare verwendet vorhandenen UR-SetMode-Helfer, ohne Programmstart. Separates
  Play startet aktuell geladenes UR-Programm; `external_control_program` nur
  noch informativ. Native reale Trajektorien mit skaliertem UR-Controller.
- **Gelenkwinkel lesen** empfängt JointState ohne Programm-/Dashboardprüfung,
  Anzeige rad/Grad. **Broadcaster / Controller laden** holt fehlgeschlagene
  Spawner nach, Broadcaster aktiv/Motion inaktiv. Beim Schließen kein zusätzlicher
  Dashboard-Stopp mehr; eigene Prozesse werden beendet. Neues Fenster kann
  fremd gestartete Treiber bedienen, beendet deren Prozesse aber nicht.
- Hardwarediagnose: Log zeigt beide Spawner13:48/13:49 fehlgeschlagen, später
  Verbindungsabbrüche/Reconnects30001/30004. Lesender8-s-Test ohne JointState;
  echte Winkelübertragung noch nicht nachgewiesen. Native UR-read()-Logik liest
  RTDE actual_q unabhängig vom laufenden External-Control-Programm.
- 14 Offline-Tests und Zwei-Paket-Build bestanden, Live-Mock-Test getrennt unter
  /uwa_mock_validation: direkte Ein-/Zwei-/Vierarm-Aktivierung ohne Dashboard,
  JointState-Leser, vier Admittanzcontroller und GUI-Stopp/Prozessabbau bestanden.
  Logs setup/logs/uwa-direct-{tests,build,live}.log und finaler JSON-Bericht unter
  setup/logs/uwa-control/. Frühere gate-spezifische Tests sind historisch.
- Neues direktes Hardware-GUI-Fenster neben altem Besitzerfenster geöffnet,
  dessen laufende reale Treiber nicht gestoppt/neugestartet. Agent hat keine
  realen Power-/Brake-/Play-/Bewegungsbefehle gesendet. Softwarestopp ist kein
  Hardware-Not-Halt. Kollisionsoption in UWA-Profilen bleibt deaktiviert;
  kein vollständiger Zellenschutz. Anleitung [UWA Arme](docs/ur_control_gui.md).

### Historische Netzwerkmessung vor Kabeltausch, 2026-11-10

- **Verbindliche Nutzerzuordnung:** hinten rechts=`right_rear`=192.168.8.170,
  vorne rechts=`right_front`=192.168.8.103. „Erster/zweiter“ sind zufällige
  Bezeichnungen, keine dauerhaften Arm-IDs. Separates Inventar in
  `config/hardware_inventory.yaml`; keine Hardware-IP in den Simulationslaunch.
- OAK4-D R9 weiterhin192.168.8.238, ID1479883285. PC wegen defektem langem
  LAN-Kabel vorübergehend per WLAN, Geräte weiter kabelgebunden am Router.
  Beobachtet PC192.168.8.209/24 aufwlp88s0f0, alle Zielrouten WLAN;
  enp87s0 DOWN. Alte LAN-Leistungswerte nicht als WLAN-Werte verwenden.
- **Alle drei Geräte erreicht.** UR-Dashboard-Leseabfragen erfolgreich:
  ModellfamilieUR5, Software5.10.1.106310, Seriennummern hinten20195501620 /
  vorne20195501617. Beide zum TestPOWER_OFF, StatusNORMAL, ProgrammSTOPPED,
  RemoteControl=false; nichts davon verändert. Keine Robotertreiber/Bewegung.
- Je40 Pings:0% Verlust; RTT-Mittel hinten6,87ms, vorne5,02ms, OAK6,52ms.
  Maxima30,92 /45,82 /14,52ms: sichtbarer Jitter, keine Echtzeitgarantie.
- OAK-Agentinfos erfolgreich; kurzer SDK-Stream640×480NV12@5fps lieferte
  gemessen4,997fps über10,21s, etwa18,9Mbit/s Bildnutzdaten. Danach geschlossen.
  Kein Maximalbandbreitentest, keine Wiederholung der LAN-Extremprofile.
  Hardware-OAK- und Simulations-Livedienste waren vor Test bereits inaktiv.
- [Prüfbericht](docs/hardware_network_2026-11-10.md); lokale Rohdaten unter
  `setup/logs/hardware-wifi-2026-11-10/`. WLAN-Bildprofile zunächst klein halten,
  Kalibrieraufnahmen bei Stillstand; spätere Rückverbindungen benötigen die
  aktuelle PC-IP. Keine URCap-/Netzwerk-/Firmwareänderung ausgeführt.

### Erster realer Wrist-/Hand-Auge-Test, 2026-11-10

- Neuer Nutzerwunsch: zunächst ausschließlich hinten rechts (`right_rear`,
  192.168.8.170) reale Tests vorbereiten, insbesondere Kamerabildzugriff klären.
- [Konkretes Vorgehen](docs/right_rear_hardware_first_test.md): Robotiq dokumentiert
  HTTP4242`/current.jpg?type=color` am UR-Controller für das letzte Kamerabild.
  Bildfrische, tatsächlichen Bildmodus/Intrinsics und Fokus separat prüfen.
- Lesender Versuch: HTTP`No route to host`, Dashboard29999Timeout. PC weiterhin
  192.168.8.209 aufWLANwlp88s0f0, Route vorhanden. Kein Bild/Zustand bestätigt,
  Ursache offen. Lokaler Bericht`setup/logs/right-rear-wrist-2026-11-10/report.json`.
  Keine Treiberstarts, Bewegung oder Power-/Brake-/Programm-/Kameraänderungen.
- Empfehlung, noch keine Umsetzung: zunächst am Pendant manuell angefahrene
  Stellungen, hardwareseitiger Bild-/Pose-Recorder mit gesicherter Bildfrische,
  reale Intrinsics/Werkskinematik und unabhängige Prüfstellungen. Automatischer
  Backend/Stopp derzeit weiterhin Simulation, nicht für echte Arme freigegeben.
- right_rear allein liefert Hand-Auge und Basis-zu-Board; relativer Abstand zum
  right_front erst mit dessen Messreihe am gleichen unbewegten Board. Vorhandene
  parallele Hardware-GUI-Arbeit bleibt erhalten und wurde nicht als fertige
  Kalibrier-Hardwareanbindung ausgegeben.
- Folgefrage Bildqualität am selben Tag: Nutzer meldet falschen Fokus und
  geringe Auflösung. Erneuter lesender HTTP-Abruf jetzt erfolgreich: **640×480**,
  83379Bytes, HTTP200. Frühere Nichterreichbarkeit damit historisch; keine
  Netz-/Kameraänderung durch diesen Agenten. Bild/Report`quality_check.jpg/json`
  unter`setup/logs/right-rear-wrist-2026-11-10/`. Sichtprüfung: Pendant überbelichtet,
  kein Board; genaue Fokusursache/Bildfrische noch nicht nachgewiesen.
- Herstellerdaten2019:2560×1920 bei2fps,640×480 bei bis30fps, Flüssiglinse70mm–∞.
  Sensorfähigkeit von tatsächlich gelieferten HTTP-Pixeln unterscheiden. Fokus
  über Robotiq-Teach-/Configure-Model-Kameraeinstellungen/Retake prüfen;
  HTTP-GET ist kein belegter Autofokus-Trigger. Höhere Auflösung noch nicht
  praktisch erschlossen; Bedienhinweise/Quellen in obiger Anleitung ergänzt.
- Fernfokus-Folgefrage2026-11-10: Nutzer möchte Skript/PC-Schieberegler und
  distanzbasierte Einstellung. Frühere Formulierung „Fokus nur per URCap“ zu
  pauschal: Primärbericht eines Anwenders im Robotiq-Forum beschreibt Fokus via
  OpenCV bei direktem USB; Hersteller unterstützt diese Integration nicht
  offiziell. Keine Prüfung am eigenen Gerät, Beispiel-Link inzwischenHTTP404.
  Für den bestehenden Controllerpfad weiter kein dokumentierter Netzwerksetter
  gefunden; installierten URCap-/Programmskriptpfad künftig lesend untersuchen.
- Physikalischen Zielabstand von elektronischem Stellwert unterscheiden:
  V4L2-Fokuseinheit nicht definiert; Kennlinie oder Board-ROI-Schärfesuche nötig.
  Kein Fokussetter/Schieberegler implementiert, keine Kamera-/Roboteränderungen.
  Für Hand-Auge Fokus und passende Intrinsics konstant halten; Fokusprofile
  wären bei distanzabhängiger Verstellung zusätzlich zu kalibrieren.
- Anschlussfrage zu Skriptdateien/Zugang2026-11-10: `.urp` ist das grafische
  Programm, vorhandener erzeugter URScript-Code als gleichnamige`.script`
  üblicherweise unter`/programs`/Unterordner. Zum Auslesen nicht ausführen.
  SSH zu right_rear erreichbar; Standard-Key-Anmeldung und genau ein Versuch
  mit dokumentiertem Hersteller-Standardkennwort abgewiesen. Keine Dateien
  vom Controller gelesen, keine Programme ausgeführt oder Zustände geändert.
  Für weitere URCap-/Fokusuntersuchung funktionierender SSH-/SFTP-Zugang oder
  lokale Dateikopie nötig. Keine Zugangsdaten in Dokumentation übernommen.
- Nutzer möchte anschließend temporäres Kennwort einrichten. Offiziellen Weg
  abPolyScope5.10 überSettings→Password→Admin erklärt, gültiges bisheriges
  Admin-Kennwort nötig; SSH-Authentifizierungsart separat prüfen. Schlüsselimport
  als Alternative ohne Kennwortweitergabe genannt. Keine Kennwortänderung
  durchgeführt und kein neues Kennwort empfangen/gespeichert.
- Neuester Befund2026-11-10: Nutzer kennt Admin-Kennwort derzeit nicht und stellt
  UCC1.11.3-ZIP bereit. Lokale statische Analyse findet internen HTTP-Kameraclient:
  GET`/getcamerasettings` und`/getcamerasettingsdetails` tatsächlich erfolgreich
  am right_rear, ohne SSH. Server meldet u.a.`focusAuto:true`, Fokus-Suchbereich
  150…1023; gemeldeter`focus:0` im Auto-Modus nicht als Linsenposition ausgeben.
- Originalclient verwendet POST`/setcamerasettings`, JSON`cameraSettings` und
  booleschen Queryparameter`setManualValuesIfModeChanged`; Fokus-Trigger ebenfalls
  rekonstruiert. Pendant-Regler0…1023 mitAPI-Wert=`1023−Reglerwert`.
  **Kein Schreibtest**, keine Kamera-/Roboter-/Installationsänderung. Nachweise
  unter`setup/logs/wrist-urcap-2026-11-10/`, eigener
  [Analysebericht](docs/wrist_urcap_analysis_2026-11-10.md). Früherer Befund
  „kein Netzwerksetter gefunden“ ist durch diese Archivuntersuchung überholt.
- Korrektur SSH-Empfehlung: regulärer Key-Import im geschützten Security-Menü
  benötigt ebenfalls Admin-Kennwort, umgeht es nicht. Für die gefundene
  Kamera-HTTP-Schnittstelle ist SSH momentan nicht nötig. Archivversion nicht
  mit bestätigter installierter URCap-Version gleichsetzen; nichts installiert.
- Folgeauftrag2026-11-10 ausgeführt: Kamera-only-Schreibtest und separates
  englisches Qt-Fenster mit2Hz-HTTP-Vorschau, Regler/Readback, Autofokus, Foto+JSON,
  Restore beim Knopf bzw. standardmäßig normalen Schließen nach eigener Änderung.
  `ros2 run uwa_cell_control wrist_camera_gui`; IP ausHardwareinventar.
- ManuellerAPI-Fokus512 nachgewiesen, sichtbare Schärfeänderung. Ursprünglicher
  Auto-Modus wiederhergestellt und reiner Fokus-Trigger erfolgreich. Autofokus
  wählt dabei neuen numerischen Wert408; kein Meterwert/kein Boardoptimum.
  Erste Prüfbedingung verlangte fälschlich exakt alten Zahlenwert im Auto-Modus;
  korrigiert. Verzögerte Bildpipeline berücksichtigt, späteres Bild wieder scharf.
  Andere Kameraeinstellungen unverändert; keine Roboter-/Treiber-/Adminbefehle.
- Vier lokale HTTP-Tests und Paketbuild bestanden, echte Qt-Knöpfe inkl.
  Speichern/Restore geprüft. Bericht`setup/logs/uwa-wrist-focus-window/report.json`,
  Screenshots/Fotos daneben; GUI zur Bedienung geöffnet. Anleitung
  [Wrist-Fokusfenster](docs/wrist_camera_focus.md). Daten unterWorkspace-setup,
  keine Rohbilder eingecheckt. Sensorbelichtungszeit weiterhin nicht verfügbar.
- Nutzer bestätigt Fokusfunktion und bittet um native Auflösung/Helligkeit.
  Server meldet tatsächlichUCC1.11.1.10337/FirmwareCQ0-1.3.5; `/restapi` enthält
  live API-Beschreibung. Begrenzter Vollauflösungsversuch über Kamera-OperationMode
  und captureimage quittiert, lastCapture-Export ohne Bild/kurzer Dienstausfall,
  automatische Erholung nachNormal. Alternative Aufnahme mit Wartezeit/Quellmap
  bleibt640×480. Keine native höhere Auflösung behauptet; kein Failing-HD-Knopf.
- Kameramoduswechsel setzt Fokus zurück; ursprünglichen Benutzerwert404/Manual
  ausdrücklich wiederhergestellt. Keine Roboterbefehle, keine Treiber-/Simulations-
  oder Firmware-/URCap-Neustarts/Updates. Eigenes altes Kamerafenster zur Erweiterung
  gezielt ersetzt, aktuelle Nutzerwerte erhalten bzw. nach Versuch zurückgestellt.
- Kamerafenster jetzt mit1…66604µs, Gain1…63, EV−7…+7 und LEDAuto/Off/Manual0…100%.
  Belichtungs-/LED-Writes partiell ohne Fokusfelder; Originalwerte sichern/Restore.
  Hardwarewirkung20→40ms/Gain2 nach Einlauf: mittlerer Grauwert39,87→72,93,
  Fokus404/Manual unverändert. LED30% und echte Qt-Knöpfe/Speichern/Restore geprüft.
  Sechs lokale HTTP-Tests und Build bestanden, neues Fenster geöffnet.
  [Details/Bedienung](docs/wrist_resolution_exposure_2026-11-10.md), Nachweise unter
  setup/calibration/wrist_resolution_exposure/20261110 und
  setup/logs/uwa-wrist-appearance-window/. Vollauflösung bleibt offen.
- Nutzer bestätigt Beleuchtung und liefertUCC4.1.0 plusDoF-Thema2227. Archiv nur
  statisch analysiert, nichts installiert oder an Kamera/Robotern geändert.
  NativeHD-Funktionen vorhanden, aber geprüfter captureimage-Client/Handler
  weiterhin ohne frei wählbare HD-/Auflösungsparameter, separater HD-Modulpfad.
  lastCapture liefert nur vorher erzeugten normalen/HD-Puffer. Kein Erfolg oder
  Upgrade-Nutzen für5MP behauptet. [Befund](docs/wrist_ucc4_analysis_2026-11-10.md).
- Verlinkter Workaround: Barcode-Knoten erzeugt5MP, SaveImage speichert, dannFTP.
  Nutzer findet diesen Weg unattraktiv. Alternative als nächster Untersuchungsweg:
  temporärenHD-Modulpfad direkt vomPC/HTTP auslösen und Bild aus Speicher abrufen,
  ohne PolyScope-Programm/SaveImage/FTP; weiterhin modulabhängig, noch ungetestet.
  Andere Optionen Controller-Konfigurationsprüfung mit legitimemSSH oderUSBdirekt;
  vorhandene gut funktionierende LED-/Fokussteuerung dabei berücksichtigen.
- Konkretisierung auf Frage „wie würde ich das machen?“: Kamera-Wizard-Endpunkte
  beginbarcode/create/process sind aus gesicherter API/Client bekannt. Nativer
  Export aus diesem Zustand noch ungeklärt; lastCapture ist nurOperationMode,
  nichtBarcode registriert. Daher keine scheinbar fertige curl-/Python-Sequenz
  ausgeben. Vorschlag bleibt ein zu entwickelndes Testtool mit vollständiger
  Zustandssicherung/-wiederherstellung, kein nachgewiesener5MP-Abruf. Keine
  neuen Hardwareaufrufe; parallele hardware-handeye-first-view-Arbeit erhalten.
- Weiterer statischer HD-Befund: untersuchte rejectmodule-/Normal-clearModules-
  Funktionen löschen Module/Kalibrierungen, keine explizite HD-Pufferlöschung
  erkannt. Kandidat: Barcode-HD→rejectmodule→Normal→OperationMode→lastCapture,
  ohne weitereVGA-Aufnahme. Strategiewechsel können dennoch Zustand/Bilder
  beeinflussen; echter Nachweis fehlt. Nächster Schritt einzelner exklusiver
  Kameratest mit Backup/Statuschecks/Pixeldimensionen/Restore, keine Installation.
  Wegen parallel aktiver ersterHardware-Hand-Auge-Arbeit hier nur lokal analysiert.
- Nutzer gibt danach Kamerazeitfenster frei (anderer Agent plant Bahn). Reale
  HD-Modultests20:16–20:18AWST: beginbarcode/create akzeptiert, process liefert
  49156/barcode process failed. Lizenzstatus true. Präzisierte Nachprüfung liest
  Modulbild/Mapping640×480; kein bestätigterHD-Puffer und kein erneuter nativer
  Export. Das beweist nicht grundsätzlich fehlendeHD-Fähigkeit; Ursache offen.
- Originalwerte in beiden Läufen vollständig gesichert, kritische Rücklesewerte
  ohne Abweichungen:404/Manual,60000µs/Manual,Gain16,LEDManual53. Kein Dienstausfall
  diesmal, keine Roboter-/Treiber-/Bahnplanungsänderung. Eigenes Kamerafenster
  gezielt pausiert und wieder mit Livebild geöffnet. Experimenteller Pythonhelper
  mit finally-Restore/Report/Dateisperre, drei lokale Fehlertests bestanden.
  [Prüfbericht](docs/wrist_hd_probe_2026-11-10.md), Sitzungen
  setup/calibration/wrist_hd/20261110_201622 bzw.201815. Native Auflösung offen.

### Zellgeometrie

Ursprung am Boden zwischen den Tischmitten. **X nach rechts, Y nach hinten,
Z nach oben**; „vorne“ ist die dem Nutzer zugewandte Seite (−Y).

| ID | UR-Typ | Tisch | Basis XYZ bei Standardaufstellung (m) | Basis-Yaw |
|---|---|---|---|---|
| `left_front` | UR5 | links | −0,45; −0,675; 0,90 | 0° |
| `left_rear` | UR7e | links | −0,45; +0,675; 0,90 | 180° |
| `right_front` | UR5e | rechts | +0,45; −0,675; 0,90 | −90° |
| `right_rear` | UR5e | rechts | +0,45; +0,675; 0,90 | +90° |

- Zwei Tische mit je **0,80 × 1,70 m**; Längskantenabstand **0,10 m**.
- Beide Roboter pro Tisch mittig über der Breite, längs symmetrisch mit **1,35 m**
  Montageabstand. Jeweils 0,175 m Abstand zur vorderen/hinteren Tischkante.
- Tischoberkante vorläufig **0,90 m**, Plattendicke und Beinbreite je **0,05 m**.
  Tische sind in dieser Simulationsversion fest zur Welt verankert; eine geänderte
  Tischpose wird nach Neustart übernommen und verschiebt beide montierten Roboter mit.
- Die echte Aufstellung ist beweglich: Maße/Posen zentral konfigurierbar halten.
- Die ursprüngliche aufrechte Anfangsstellung `[0, −π/2, 0, −π/2, 0, 0]`
  wurde am 2026-11-09 durch ChArUco-Zielansichten ersetzt (siehe unten).
  Robotiq 2F-85 und Wrist Camera sind seit demselben Tag ergänzt.
- Pro Arm kann eine individuelle Kinematik-Kalibrierdatei angegeben werden.
- Offizielle UR-Beschreibungen verwenden. UR7e hat eine eigene Parameterkonfiguration,
  teilt im installierten Upstream-Paket aber visuelle Meshes mit UR5e.

### Korrektur der Montageorientierungen, 2026-11-06

Der Nutzer gab die Kabelrichtungen als groben Anhaltspunkt an:

- Links vorne: Kabel zum Nutzer (−Y), ausdrücklich **−90° gegenüber der ersten Simulation**.
- Links hinten: Kabel nach hinten (+Y).
- Rechts vorne: Kabel nach links zur Mitte (−X).
- Rechts hinten: Kabel nach rechts außen (+X).

Daraus wurden die Yaw-Werte der obigen Tabelle übernommen und im laufenden TF-Baum
geprüft. Die vorherige pauschale Ausrichtung „vorne +90°, hinten −90°“ ist **überholt**.
Alle Winkel beziehen sich auf **`base_link`**. Der UR-Teach-Pendant-`base`-Frame
hat zusätzlich die in der offiziellen Beschreibung enthaltene 180°-Drehung.
Höhe, Yaw-Werte und Scan-Pose sind weiterhin **nicht kalibriert**.

## Implementierung und Schnittstellen

| Bestandteil | Zuständigkeit |
|---|---|
| `uwa_cell_description` | ament_cmake; Tische, offizielle UR-Modelle, gemeinsame Xacro-Datei |
| `uwa_cell_gazebo` | ament_python; Launch, Controller-Konfiguration, Scan-Import/Publisher, Prüfwerkzeuge |
| `uwa_cell_description/config/cell_layout.yaml` | Zentrale Layout-, Montage-, Anfangsstellungs- und Scan-Konfiguration |
| `uwa_cell_gazebo/rviz/cell.rviz` | Roboter, Tische, Grid, optionale Frames und Scan-Referenz |
| `scripts/` | Dienst-, Desktop-, RViz- und Scan-Helfer |

- Eine zusammenhängende Zelle `uwa_cell`, **24 eindeutige bewegliche Armgelenke**
  mit Präfixen `left_front_`, `left_rear_`, `right_front_`, `right_rear_`.
- Ein Manager `/uwa_cell/controller_manager`, ein `joint_state_broadcaster`, vier
  Arm- und vier Greifer-`JointTrajectoryController`, alle neun nach Start aktiv.
- Action je Arm: `/uwa_cell/<id>_trajectory_controller/follow_joint_trajectory`.
- Je Controller steht auch `joint_trajectory` als Topic bereit.
- Gazebo-Server und GUI getrennt starten. Der verpackte Jetty-GUI-Client wird
  direkt gestartet, damit Launch den richtigen Prozess beim Stoppen signalisiert.
- `clock_bridge.py` überträgt echte Gazebo-Simulationszeit über die installierten
  Python-Transport-Bindings und meldet sich vor dem ROS-Abbau explizit ab.

### Robotiq-Werkzeuge, Nutzerauftrag 2026-11-09

- Alle vier Arme sollen ihre Greifer und Wrist Cameras erhalten. Gemeldete
  Beispielgeräte: 2F Adaptive 2020 **S/N C-43008**, Wrist Camera 2019
  **S/N Q-021114**. Der Nutzer hat ausdrücklich **2F-85 (85 mm)** bestätigt.
  Die Nummern sind keine bestätigte Zuordnung zu einem bestimmten Arm.
- Montagekorrektur des Nutzers: Kameralinse auf der vom UR-Werkzeug-I/O-Stecker
  abgewandten Seite. UR-`tool0` +Y zeigt vom Stecker weg; `camera_yaw: 0`
  setzt die Linse entsprechend auf +Y. Kein zusätzlicher TCP-Offset angenommen.
- Greifer-Geometrie, Massen und Kinematik aus PickNik `ros2_robotiq_gripper`,
  festgehaltener Commit und BSD-Lizenz in `THIRD_PARTY.md` / `LICENSES/`.
  Nur Modelldaten übernommen; keine Hardwaretreiber oder seriellen Verbindungen.
- Ein antreibendes Knöchelgelenk je Greifer (0 offen, 0,8 rad geschlossen),
  fünf Mimic-Gelenke. Insgesamt 48 bewegliche Gelenke, 28 Positionsbefehle.
  Greiferaction: `/uwa_cell/<id>_gripper_controller/follow_joint_trajectory`;
  über denselben rqt-Controllerwähler bedienbar.
- Wrist Camera als primitive Geometrienäherung, 13,5 mm Zusatzhöhe ohne
  separate Werkzeugplatte, 160 g; Sensor `[0; 35,7; −0,1]` mm, 30° Neigung
  nach außen, nominell 50° horizontal, 640 × 480, zunächst 10 Hz je Kamera.
  Datenquelle: Robotiq-Handbuch 2019 (Links in `THIRD_PARTY.md`).
- `tools` in `cell_layout.yaml` enthält gemeinsame Einstellungen; je Roboter
  sind partielle Überschreibungen möglich. Kamera und Greifer einzeln abschaltbar.
- ROS-Topics: `/uwa_cell/<id>/wrist_camera/image_raw` und `camera_info`,
  Sensor-Data-QoS, Frame `<id>_wrist_camera_optical_frame`.
  `camera_bridge.py` verwendet wie die Uhrbrücke Gazebo-Python-Bindings mit
  expliziter Abmeldung vor Shutdown. Gazebo-Sensors-System ergänzt.
- Grenzen: Keine herstellergenaue Kameragehäuseform, Objektivkalibrierung,
  URCap-Bildverarbeitung, Autofokus-/LED-Steuerung oder adaptive Kontaktmechanik.
  Die spätere Kalibrier-Routine ergänzt MoveIt-Kollisionsprüfung;
  reale Hardware bleibt Folgearbeit.
- Prüfstand 2026-11-09: beide Pakete gebaut, **24 Offline-Tests erfolgreich**;
  vier gültige RGB-/CameraInfo-Streams, korrekte optische TFs und Zeitstempel,
  neun aktive Controller. Alle vier Greifer einzeln geschlossen/geöffnet und
  zurückgestellt, Mimic-Abweichung < 0,03 rad, andere Gelenke < 0,01 rad Drift.
  Alle vier Arme mit Werkzeugen am Handgelenk bewegt und zurückgestellt;
  tatsächliche Zellwurzel stabil. Installiertes rqt: acht Controller, je
  sechs Armeditoren/ein Greifereditor, gültige Haltebefehle.
  Belege: `setup/logs/uwa-cell-tools-{build,tests,verification,arm-verification,rqt-check}*`
  und `setup/logs/uwa-cell-camera-images/` im Workspace.
- EGL-Betrieb ohne Gazebo-Fenster ebenfalls mit vier Bildstreams und neun
  aktiven Controllern geprüft: `setup/logs/uwa-cell-tools-headless-verification.json`.
  Ein erster Start hatte Controller-Service-Timeouts; die Statusprüfung fragt
  nun höchstens alle 0,5 s ab, der erneute Headless-Start war erfolgreich.
  Uhr-/Kamerabrücke und Server beim Wechsel sauber beendet; Journalbeleg
  `setup/logs/uwa-cell-tools-restart.log`. Keine ungeprüfte Ursache des Timeouts behaupten.
- Das installierte Physik-Backend meldet fehlende native Mimic-Constraints.
  Die getestete Positionskopplung übernimmt `gz_ros2_control`. Kein Nachweis
  realistischer Kraftkopplung oder belastbarer Objektgriff-Physik.

### ChArUco und erster Basisabgleich, Nutzerauftrag 2026-11-09

- Je ein Board mittig zwischen den Robotern pro Tisch; zunächst linkes Paar in
  `left_table_top`, rechtes Paar in `right_table_top` prüfen. Der Nutzer will
  darauf aufbauend ein Werkzeug zur relativen Roboterkalibrierung entwickeln.
- Muster 7 × 5, Feldkante 40 mm, Marker 28 mm, Rand 20 mm, Träger 3 mm;
  `DICT_4X4_100`, links IDs 0–16, rechts 50–66. Alles unter `charuco` in YAML.
- Kamera-Zielansichten per URDF-FK/IK ermittelt und in `initial_positions`
  übernommen: 0,55 m über der Boardmitte, je ±0,28 m entlang Tisch-Y versetzt.
  Bestehende Basis-/Werkzeugmontagen erhalten; kein geplanter Bewegungsweg.
- `charuco_check`: OpenCV 4.10 `CharucoDetector`, PnP/IPPE und LM-Verfeinerung;
  zehn verschiedene Bildzeitstempel pro Kamera, PNGs und JSON-Bericht.
  Ground Truth erst nach der Bildschätzung für Fehlerprüfung aus TF lesen.
- Erste Basisformel: `T_table_base = T_table_board @ inv(T_camera_board) @ inv(T_base_camera)`.
  Die interne TF-Kette beginnt bei URDF `base_link`, ohne bekannte Weltmontage
  als Eingang. Boardplatzierung, Intrinsics, Hand-Auge-Transformation und
  Gelenkkinematik werden als bekannt vorausgesetzt. Noch keine Schätzung
  unbekannter Hand-Auge-/Gelenkparameter aus mehreren Armstellungen.
- Offizielle Boardframes `<table>_charuco`: Musterecke ohne Rand; X rechts,
  Y im Muster nach unten, Z in die Platte. Plattenmitte ist `<table>_charuco_mount`.
- Erster Live-Erfolg: alle vier Gazebo-Bilder mit jeweils 24 ChArUco-Ecken.
  Relative Basenfehler beider Tische ca. 1,9 mm / 0,17°, individuelle
  gemittelte Basisfehler ca. 1,1–1,2 mm / 0,08–0,09°. Idealisiertes Rendering,
  keine Genauigkeitszusage für echte Kameras. Konkrete Zahlen im
  [datierten Bericht](docs/charuco_validation_2026-11-09.json).
- Materialfehler beim ersten Liveversuch: Collada-Fläche ohne Normalen blieb
  unsichtbar. Explizite +Z-Normalen ergänzt, echter Vierkamera-Test danach bestanden;
  Assetprüfung dafür ergänzt. PNG-Muster bleiben deterministisch OpenCV-generiert.
- **33 Offline-Tests bestanden**, beide Pakete gebaut. Vollständiger Bildbericht:
  `setup/logs/uwa-charuco-second/report.json`, annotierte Bilder im selben Ordner;
  Logs `uwa-cell-charuco-{build,tests,live,cell-verification}*` im Workspace.
- Finaler Bestätigungslauf mit Roh- und Erkennungsbildern:
  `setup/logs/uwa-charuco-final/`; zehn erfolgreiche Bilder je Kamera,
  relative Fehler links **1,888 mm / 0,1645°**, rechts **1,843 mm / 0,1570°**.
  Neun Controller aktiv, Zellwurzel stabil, RViz wiederhergestellt. Der separate
  Scan-Publisher blieb erhalten; keine weiteren Zellneustarts geplant.
- Anleitung/Formeln/Bedienung: [docs/charuco_calibration.md](docs/charuco_calibration.md).
  `prepare_charuco_views` erzeugt nach Layoutänderungen eine alternative YAML,
  ohne die Quelle zu überschreiben oder Bewegungen auszuführen.
- Zusammenarbeit: Nutzer arbeitet mit mehreren unabhängigen Agenten im selben
  Checkout. [ACTIVE_WORK.md](ACTIVE_WORK.md) plus eigene Datei je Aufgabe unter
  `work/` eingeführt; vor Edits/Neustarts lesen, Änderungen bereichsweise anwenden.
  Der fremde Scanregistrierungs-Diff wurde erhalten. Für Uhrenreset RViz kurz
  schließen und danach wiederherstellen, separaten Scan-Publisher erhalten.

### Druckvorlagen, Nutzerauftrag 2026-11-09

- Dieselben ChArUco-Muster für echte Versuche angefordert. Originalmaß inklusive
  Weißrand **320 × 240 mm**; Muster 280 × 200 mm, Feldkante 40 mm, Marker 28 mm.
- `output/pdf/uwa_charuco_boards_A3_1to1.pdf`: zwei A3-Querformat-Seiten,
  links/rechts jeweils komplett. `uwa_charuco_boards_A4_tiled_1to1.pdf` im selben
  Ordner: vier A4-Hochformat-Seiten, je Board zwei Hälften mit 20 mm Überlappung.
  Keine verkleinerte A4-Einblatt-Version, da sie andere metrische Maße hätte.
- Beide PDFs als Vektorflächen aus derselben `board_image()`-Ausgabe wie Gazebo;
  IDs links 0–16, rechts 50–66 unverändert. Generator `scripts/print_charuco.py`
  liest die zentrale YAML; optionale PDF-Abhängigkeit `python3-reportlab`.
- Druck: **100% / Tatsächliche Größe**, keine Seitenanpassung; 100-mm-Kontrollstrecke
  und 40-mm-Feldkante nachmessen, plan auf festen Träger aufbringen. Für echte
  Kalibrierung die tatsächliche Boardoberflächenpose im Tisch-KS vermessen.
- Dateiprüfung: korrekte Seitenformate/-zahlen und metrische Vektorgeometrie,
  alle sechs Seiten gerendert und angesehen. OpenCV erkennt auf beiden A3-Seiten
  sowie den digital zusammengesetzten A4-Boards je alle 17 Marker und 24 Ecken.
  Beleg: `docs/charuco_print_validation_2026-11-09.json`, vollständiges Log unter
  `setup/logs/uwa-charuco-print-verification.log` im Workspace. Kein physischer
  Druckertest durchgeführt. Simulation und laufende Dienste nicht verändert.

## Bedienung: aktuelles Sollverhalten

- Startmenü: **UWA Cell Simulation** startet Gazebo, rqt, RViz **und Scan-Publisher**.
- Auch die Desktop-Aktion **RViz öffnen** startet den Scan. **Punktewolke anzeigen**
  bleibt als zusätzliche Aktion vorhanden; **Simulation beenden** stoppt alle drei Dienste.
- Dienste: `uwa-cell-sim`, `uwa-cell-rviz`, `uwa-cell-scan` (systemd-Benutzerdienste).
- Wiederholtes Anklicken verwendet laufende Dienste weiter; die bestehende Simulation
  und deren Gelenkzustände werden dabei nicht unnötig neu gestartet.
- Seit 2026-11-09 holt `scripts/show_cell_windows.py` die vorhandenen XWayland-Fenster
  nach vorne und stellt minimierte Fenster wieder her. Nur PIDs aus den Zell-Diensten
  werden berücksichtigt. Normaler Start fokussiert Gazebo, RViz-/Scan-Aktionen RViz.
  Der Desktop-Eintrag verwendet `StartupWMClass=Gazebo GUI`.
  Kurzlebige Splash-/Menüfenster werden ausgelassen; ein zwischenzeitlich
  verschwundenes Fenster darf den Launcher nicht mit X11-`BadWindow` abbrechen.
- Direktes `cell.sh start` / `ros2 launch ...` behält seine ursprünglichen Defaults:
  GUI und Controller-GUI an, RViz und Scan aus. Das ist bewusst vom Desktop-Start getrennt.
- `cell.sh rviz` öffnet direkt nur RViz; `cell.sh scan` schaltet nur den Scan hinzu.
  Die Desktop-Aktionen kombinieren diese Helfer für die gewünschte Bedienung.
- `MoveCamera` ist explizit das erste RViz-Werkzeug. Linke Maustaste: drehen;
  Mausrad: zoomen; mittlere Maustaste: verschieben. Views-Panel vorhanden.
- Icon: `assets/uwa-cell.png`, RGBA mit transparentem Außenrand. Installer verwendet
  einen inhaltsabhängigen Dateinamen unter `~/.local/share/icons/`, damit GNOME
  nach Bildänderungen nicht das alte Icon aus dem Cache weiterverwendet.
- Desktop-Datei: `~/.local/share/applications/uwa-cell.desktop`.
  Installer: `python3 scripts/install_desktop.py` (als normaler Nutzer, ohne sudo).

## Punktewolke und Grenzen der Referenz

- Original: `~/GoogleDrive/UWA/UR Setup.ply`, ca. **215 MB**, **867.068 Einträge**.
  Binäre Little-Endian-Gaussian-Splat-PLY, keine fertige Dreiecksgeometrie.
- Import übernimmt Zentren und Grundfarben aus SH-DC-Feldern; Opazität aus Logits,
  Ausdehnung aus logarithmischen Skalen. Keine Kollisionen aus dem Scan ableiten.
- Defaults: Mindestdeckkraft **0,1**, maximale Splat-Skala **0,05** Scan-Einheiten,
  Voxelgröße **0,01** Scan-Einheiten, höchstens **200.000 Punkte**.
- Ungültige Werte und ungeeignete Splats filtern; Reduktion und Punktbegrenzung
  deterministisch. Quelle unverändert auf Drive lassen und nicht ins Git aufnehmen.
- Cache: `$XDG_CACHE_HOME/uwa_cell/scans` bzw. `~/.cache/uwa_cell/scans`, NPZ ohne Pickle.
- Publisher: `/uwa_cell/scan_reference`, `PointCloud2`, Reliable / Transient Local.
  Frame `uwa_scan_reference`; statischer Transform von `world`.
- Ursprünglich Maßstab **1** und Identitätspose; diese Anzeige war deutlich gekippt.
  Seit 2026-11-09 ist eine grobe Tischflächen-Ausrichtung eingestellt (siehe unten).
  Die Referenz bleibt ausdrücklich **nicht kalibriert**.
- Ein fehlender Scan darf Gazebo nicht verhindern. Bei `scan:=false` liest der
  direkte Launch den Scan nicht. **Aktuelle Grenze:** Auch zur Cache-Auswahl fragt
  der Importer noch Dateimetadaten des Originals ab; kein garantierter Offline-Fallback
  bei vollständig fehlendem Drive-Mount. Das ist keine bereits erledigte Anforderung.

### Grobausrichtung des Scans, 2026-11-09

- Nutzerauftrag: Die deutlich verdrehte Punktewolke an der Szene ausrichten;
  bei nötigen Bezugspunkten unterstützt der Nutzer.
- Vorgehen: Dominante Boden-/Tischebenen im lokalen Scan-Cache bestimmen,
  zwei zentrale zusammenhängende Tischflächen isolieren und ihre Rechteckkanten
  an den nominellen 0,80 × 1,70 m ausrichten. Keine Roboterposen aus dem Scan ableiten.
- Maßstab **0,9531928102**, Translation **[−0,28749867; −0,43623572; +0,58765448]**,
  RPY in Grad **[−89,761396; +0,349501; +60,140648]**.
  Die Runtime-Werte bleiben zentral in `cell_layout.yaml`; der datierte
  [Fit-Bericht](docs/scan_alignment_2026-11-09.json) dokumentiert ihre Herleitung.
- Die zunächst mögliche 180°-Verwechslung wurde mit konkreten Nutzerangaben aufgelöst:
  **hinter** den Tischen steht eine hohe weitere Roboterzelle aus item-Profilen;
  **vorne** sind zunächst etwa zwei Meter freie Fläche. Die passende Scan-Richtung
  ist bereits eingestellt (+Y zur hohen Profilrahmen-Zelle, −Y zur freien Fläche).
- Der Nutzer konnte die abstrakte A/B-Draufsicht nicht eindeutig zuordnen.
  Bei weiteren Rückfragen besser konkrete reale Gegenstände/Bezugspunkte benennen.
- Nur `uwa-cell-scan` wurde neu gestartet; Simulation, Modellmaße, Robotermontagen,
  Greifer/Kameras und laufende Benutzer-RViz-Ansicht wurden nicht zurückgesetzt.
- Grenzen: Keine metrische Kalibrierung. Die vorläufige Modell-Tischhöhe 0,90 m
  ergibt bei diesem Scan-Fit ca. **0,132 m Bodenversatz**. Reale Höhe noch messen;
  die aktuelle Scan-Schätzung allein ist kein Auftrag, das Modellmaß zu ändern.
  Abweichende Armstellungen zwischen Aufnahme und Simulation sind erwartbar.
- Prüfung: 200.000 endliche Punkte, publizierter Maßstab und Welt-TF entsprechen
  der YAML, genau ein Publisher. Beide bestehenden Dienst-PIDs (Simulation/RViz)
  blieben erhalten. RViz meldet 200.000 dargestellte Punkte und Transform „Ok“.
  **24 vorhandene Offline-Tests bestanden**; protobuf meldet eine Deprecation-Warnung.
- Belege: `setup/logs/uwa-scan-alignment-{estimate,verification}.json`,
  `uwa-scan-alignment-landmarks.png`, `uwa-scan-aligned-rviz.png` und zugehöriges Log
  im Workspace. Analyseprogramme lagen temporär unter `/tmp/uwa-scan-alignment`.

### Scan-Bereinigung, Nutzerauftrag 2026-11-09

- Anforderungen: Keine Punkte weiter als **4 m vom Zentrum zwischen den Robotern**;
  die aufgenommenen Roboter entfernen, damit keine doppelten Arme neben den
  simulierten Robotern stehen.
- Umgesetzt als Kugelradius im Weltkoordinatensystem um den Mittelwert der vier
  Basispositionen, aktuell **[0; 0; 0,90] m**. `scan.crop_center: null` berechnet
  diesen Punkt aus Tisch-/Montageposen; alternativ ist ein expliziter Punkt möglich.
- Acht feste `scan.exclude_boxes` blenden die vier aufgenommenen Arme und ihre
  Basisbereiche aus. Die Aufnahmeposen unterscheiden sich von den Simulationsposen;
  deshalb keine dynamischen Modell-TFs als Entfernungsmasken verwenden.
- Grobe räumliche Masken, keine semantische Roboterdetektion. Sie können direkt
  angrenzende Punkte im selben Volumen mit ausblenden und sind nach einer neuen
  Aufnahme oder Registrierung erneut zu prüfen. Tischflächen und die meisten
  flachen Tischobjekte bleiben durch die Höhenbegrenzung erhalten.
- Modul `scan_filter.py`, Aufruf einmal im Scan-Publisher nach der Skalierung;
  nur die Auswahl wird in Weltkoordinaten berechnet. Publizierte Punkte bleiben
  im bisherigen Scan-Frame. Roh-PLY und Importcache unverändert.
- Konfiguration und Validierung: `crop_radius`, `crop_center`, `exclude_boxes`
  unter `scan`; Radius `null` bzw. leere Maskenliste schalten die Filter ab.
- Ergebnis für die aktuelle Aufnahme: **200.000 → 154.458 Punkte**. Entfernt:
  **27.133** außerhalb des Radius und **18.409** innerhalb der Roboter-Masken.
- Liveprüfung: größter Radius **3,999784 m**, keine veröffentlichten Punkte in
  den Masken, endliche Koordinaten, genau ein Publisher. Rohcache-SHA256 und
  Simulations-/RViz-Dienst-PIDs unverändert. Nur `uwa-cell-scan` neu gestartet.
- RViz-Sichtprüfung: 154.458 Punkte, Transform und Anzeige „Ok“, keine doppelten
  aufgenommenen Arme mehr; Umgebungsgeometrie und Tische sichtbar.
- **44 Offline-Tests bestanden**, inklusive 11 neuer Filter-/Validierungsfälle:
  Weltkoordinaten und Radiusgrenze, Farberhalt, bewegte Tische, feste Masken,
  Überlappungen/leere Ausgabe und ungültige Konfiguration. Eine bestehende
  protobuf-Deprecation-Warnung bleibt.
- Belege im Workspace: `setup/logs/uwa-scan-cleanup-{counts,tests,verification}.*`,
  `uwa-scan-cleaned-rviz.{png,log}` und `uwa-scan-cleanup-regions.png`.
- Parallel aktive ChArUco-Arbeit über `work/` abgestimmt; keine Board-, Werkzeug-,
  Roboter- oder Simulationsstartänderungen durch diese Bereinigung.

## Behobene Probleme und Entscheidungen

| Datum | Beobachtung / Entscheidung | Ergebnis |
|---|---|---|
| 2026-11-06 | Gazebo-Wrapper und Clock-Bridge beendeten sich nicht sauber | Direkter GUI-Client; eigener kleiner Clock-Adapter; gezielte Dienststeuerung |
| 2026-11-06 | Nur diese RViz-Konfiguration erlaubte kein Drehen/Zoomen | Fehlende `Tools`-Liste ergänzt; echte Maus-/Mausrad-Ereignisse geprüft |
| 2026-11-06 | Weißer Außenrahmen am ansonsten gewünschten Icon | Mit Imagegen transparent gemacht; Motiv und dunkelblaues Feld erhalten |
| 2026-11-09 | App zeigte keine Wolke, manuell gestarteter Scan schon | Scan fehlte im normalen Desktop-Start; Start und RViz-Aktion laden ihn jetzt automatisch |
| 2026-11-09 | Nutzer wünscht dauerhaftes Festhalten der Gespräche | Workspace-/Projekt-AGENTS und diese Übergabe angelegt; fortlaufende Pflege vereinbart |
| 2026-11-09 | Icon-Klick scheint nichts zu starten, obwohl alle drei Dienste und Fenster laufen | Vorher nur „läuft schon“; nun Wiederherstellen/Aktivieren der vorhandenen Zell-Fenster ohne Neustart |
| 2026-11-09 | Punktewolke deutlich gegenüber dem Modell verdreht | Grober Ebenen-/Rechteck-Fit; Vorderseite über freie Fläche und hintere Profilrahmen-Zelle identifiziert; keine Kalibrierungsbehauptung |
| 2026-11-09 | Ferne Scanpunkte und doppelte aufgenommene Arme stören | 4-m-Weltradius und feste Scan-Roboter-Masken; nur Referenzpublisher neu geladen |

Ein früher Tracing-Schalter löste den Clock-Bridge-Absturz nicht vollständig;
ihn nicht als fertige Lösung wieder einführen. Zusätzlich wurde am 2026-11-06
ein einzelner RViz-Absturz beim Fensterbetrieb/-ende im Journal beobachtet.
Dessen Ursache ist nicht abschließend geklärt; bei erneutem Auftreten Journal
und Backtrace untersuchen, nicht automatisch mit dem behobenen Kamerafehler gleichsetzen.

Am **2026-11-09** wurde während dieser Prüfung zusätzlich ein neuer Simulationsstart
mit rückwärts springender Uhr beobachtet. Das noch geöffnete RViz brach anschließend
mit `tf2::LookupException: Static cache is empty` für `uwa_scan_reference` → `world`
ab. Die Desktop-Aktion konnte RViz erneut öffnen. Eine grundsätzliche Behebung dieses
Zeitsprung-/TF-Problems ist damit **nicht** nachgewiesen; bei weiteren Simulations-Resets
beachten. Die Zell-Simulation wurde für die Fensteraktivierung selbst nicht zurückgesetzt.

## Prüfstand und Belege

Historisch geprüfte Ergebnisse, keine Behauptung einer erneuten Gesamtprüfung
bei jeder Dokumentationsänderung:

- **2026-11-06:** Beide neuen Pakete gebaut, Systemabhängigkeiten vorhanden;
  **11 Offline-Tests** erfolgreich (Layout/TF-Topologie, Tischumpositionierung,
  Scan-Farben, Filter, ungültige Zahlen, Punktlimit und fehlerhafte PLY-Dateien).
- **2026-11-06:** Simulationszeit läuft, 24 endliche Gelenkzustände, fünf aktive
  Controller; tatsächliche Gazebo-Wurzel bleibt verankert.
- Alle vier Arme einzeln per Action am Handgelenk um 0,1 rad bewegt und zurückgestellt;
  Zielabweichung < 0,03 rad, Drift anderer Arme < 0,01 rad.
- Standard-rqt-Plugin: vier Controller auswählbar, sechs Gelenkeditoren je Arm,
  gültige Haltebefehle publiziert. Drei erfolgreiche Clock-Start-/Stopp-Zyklen.
- RViz: Mausdrehen und Zoom am realen Viewport geprüft; Gegenprobe ohne Tools-Liste
  reproduziert den Fehler. RViz meldete 200.000 Punkte und Transform „Ok“.
- **2026-11-09:** Tatsächlichen installierten App-Eintrag über `gio launch` geprüft:
  200.000 endliche Punkte, Welt-Transform vorhanden, genau ein Scan-Publisher;
  vorhandene Simulations-/RViz-Prozesse erhalten; wiederholtes Anklicken ohne Duplikat.
- **2026-11-09, Fensteraktivierung:** Installierter App-Aufruf fokussiert das vorhandene
  Gazebo-Fenster; Dienst-PIDs von Simulation, RViz und Scan bleiben gleich.
  Eine gezielt minimierte RViz-Ansicht wurde über die echte Desktop-Aktion wiederhergestellt
  und fokussiert. Es war kein Reset der laufenden Roboter nötig.

Belege unter `~/UWA_ws/setup/logs/`, insbesondere:

- `uwa-cell-tests.log`, `uwa-cell-build.log`
- `uwa-cell-motion-verification.json`, `uwa-cell-mount-orientation-verification.json`
- `uwa-cell-rqt-check.log`, `uwa-cell-python-clock-verification.log`
- `uwa-cell-rviz-interaction.log`, `uwa-cell-rviz-negative-check.log`
- `uwa-cell-rviz-interaction.png`, `uwa-cell-scan-verification.json`
- `uwa-cell-desktop-scan-verification.json`
- `uwa-cell-app-window-verification.json`

Temporäre RViz-C++-Testprogramme lagen unter `/tmp/uwa-rviz-check`; deren
Fortbestand nicht voraussetzen. Dauerhafte Prüfkommandos stehen in der README.

Momentaufnahme am 2026-11-09 bei Anlage dieser Datei: Zell-, RViz- und Scan-Dienst
aktiv; separate MuR-Simulation inaktiv. Vor weiterer Prozessarbeit neu prüfen.

## Umgebung und vorherige Workspace-Arbeit

- Workspace `~/UWA_ws`; ROS `/opt/ros/lyrical`; Gazebo Jetty (bei Einrichtung 10.5.0).
- Zell-Umgebung: `source scripts/env.bash` innerhalb dieses Repositories;
  Domain **64**, lokale Discovery, Partition **`uwa_cell_sim`**, `GZ_IP=127.0.0.1`.
- Allgemeines Setup: `~/UWA_ws/setup/lyrical_env.bash`, standardmäßig Domain **62**.
- Separate MuR-Simulation: `setup/start_mur_simulation.sh`, Benutzerdienst
  `uwa-mur620a-sim`, Domain **63**, Partition **`uwa_mur620a_sim`**.
  Nicht mit der Vierarm-Zelle oder echter Hardware vermischen.
- Weitere vom Nutzer gewünschte Repositories: `match_mur_gui`,
  `match_mobile_robotics_jazzy`, `match_mir_camera_calibration`,
  `match_cooperative_handling`, `oak_camera_calibration`, `match_software_utilities`
  (ursprünglich aus der GitHub-Organisation `match-ROS`).
- Bestehende Lyrical-Portierungen mit lokalen Änderungen auch in Submodulen:
  [Patch-Übersicht](../../setup/patches/lyrical-controllers/README.txt),
  [Manifest](../../setup/patches/lyrical-controllers/manifest.json).
  Laut Übersicht sind die Patches bereits angewendet; nicht erneut blind anwenden.
- Ursprüngliche Einrichtungshelfer: `setup/install_lyrical.sh`, `setup/check_lyrical.sh`,
  `setup/test_controllers_lyrical.sh`. Interaktive sudo-Anmeldung erfolgt lokal durch den Nutzer.
- Google Drive wurde via rclone unter `~/GoogleDrive` eingebunden. Setup-Hinweise
  liegen unter `setup/google-drive/`; Mount/Anmeldung bei Bedarf prüfen. Keine
  Zugangsdaten in Git oder in diese Übergabe kopieren.

## Statische OAK4-Übersichtskamera (2026-11-09)

- **Wichtige Nutzerpräzisierung:** später einen Tisch absichtlich verschieben;
  Tisch-zu-Tisch-Pose und tatsächliche Bewegung messen, Fehler kompensieren.
  Beide Tischboards bleiben fest montiert. Option: kleine OAK auf rechtem Tisch
  sieht nur das gegenüberliegende Board. Tischfeste Kameramontage und variable
  Tischpose unbedingt getrennt behandeln, Bewegung nicht in Kalibrierung absorbieren.
- Neuer [Kalibrier-/Messansatz](docs/table_tracking_calibration.md): OAK sieht
  beide Boards -> relative Boardpose durch inv(T_C_BL)@T_C_BR, Weltpose der
  Kamera fällt heraus. Tischmontagen der Boards für definierte Tischframes ergänzen.
  Für OAK auf rechtem Tisch Montage X einmal separat bestimmen; danach bleibt X
  bei Tischbewegung konstant. Unbekannte Montage plus unbekannte Tischrelation
  sind aus einer einzigen gegenüberliegenden Boardansicht nicht getrennt schätzbar.
- Nutzer schlägt bekannte stationäre Wrist-Kameras und ein zusätzliches mobiles
  Kalibrierboard im gemeinsamen Sichtfeld vor. Als bevorzugter erster Ansatz
  empfohlen: lokale Kamera-Kamera-Transformation über viele Halteposen, dann
  bekannten FK-/Hand-Auge-/Tischbezug nutzen; weder Tischboards noch Kameras
  müssen sich bewegen. Alternative: UR hält Board für automatisierte Eye-to-Hand-
  Schätzung inklusive unbekannter Werkzeug-Board-Montage. Empfehlungen, noch
  kein Implementierungs-/Messfahrtauftrag. Frühere Konzeptannahmen entsprechend
  als eingeschränkt markiert; keine Dienste/Hardware/Simulationsposen verändert.

- Beratungsfrage zur empfohlenen Kalibrierung statischer Kameras:
  [Konzeptvorschlag](docs/static_camera_calibration_plan.md) festgehalten.
  Factory-Intrinsics für Bildmodus/Fokus prüfen, feste Tischboards als Referenz
  und zur Verbindung beider Tischgruppen, Zusatzkameras über gemeinsame/registrierte
  Targets, anschließend räumlich vielfältige gemeinsame Schätzung und unabhängige
  Validierung. Referenzbeziehung zum realen `world` definieren/vermessen, keine
  angenommenen Gazebo-Posen als Hardware-Messwerte. Dies ist eine Empfehlung,
  noch kein genehmigter Implementierungs-/Messfahrtauftrag oder Kalibrierergebnis.

- Nutzerangabe: OAK4-D auf einem Stativ neben den Tischen, derzeit rechts,
  nach unten auf die Tischplatten; Montage noch offen. Gewünscht ist Überblick
  über die ganze Szene bei genügend ChArUco-Detail. Dafür Simulation zum
  Vergleichen von Position, Höhe, Blickrichtung und Auflösung verwenden.
- Umgesetzt als eigene statische Gazebo-Entität `uwa_oak_overview`, außerhalb
  der Zell-URDF. Bestehende Zell-/Wrist-/Greifer-/Controllerkonfiguration erhalten;
  keine Gelenkbefehle und kein Zellneustart durch diese Aufgabe.
- Nutzerkorrektur: reales Stativ maximal **2 m**. Zwei zusätzliche OAK-Kameras
  verfügbar, falls tote Winkel ergänzend abgedeckt werden müssen. Die erste
  unbeschriftete Kamera per USB identifiziert: EEPROM **OAK-D Pro AF**, SDK
  **OAK-D-PRO-AF**, RVC2/DM9098, IMX378-Autofokus + zwei OV9282. Zweite Kamera
  noch ungeprüft; frühere gemeinsame Bezeichnung OAK-D-S2-FF ist überholt.
  Keine konkreten Zusatzkameraposen festgelegt. Diagnose im OAK-Repo-Handover.
- Aktuelle zentrale Konfiguration `overview_camera` in `cell_layout.yaml`:
  optisches Zentrum Welt[1.8,-0.8,2.0]m, Ziel[0,-0.1,0.95]m, etwa28,5° nach unten,
  nominell67,3° horizontal,4000×3000@3Hz Simulationszeit. Nicht kalibriert.
- Neue2m-Pose live geprüft: alle Tisch-Ecken geometrisch im Bild, vier Arme und
  Tischplatten im geprüften Bild sichtbar,12/24 Ecken links/rechts erkannt,
  RMS0,691/0,042px. Links wenig Reserve; Zusatzkameras für tote Winkel/Details
  sind eine Erweiterungsoption. Keine Garantie für alle Armstellungen.
- Mehrere Kandidaten verglichen: mittig rechts zu wenig linke Erkennung,
  starke Frontdiagonalen durch Arme verdeckt.6k lieferte CameraInfo, aber kein
  erfolgreich empfangenes RGB im Zeitfenster;5k ebenfalls nicht erfolgreich.
  Daher bei4k geblieben. Keine Behauptung einer Hardwaregrenze daraus.
  Belege `setup/logs/uwa-oak-2m/`, finale JSON/Bilder dort unter `final/`;
  neue Pose und Höhenlimit mit13 Offline-Tests geprüft. Aktiver Layoutpfad
  wieder zentrale Quelldatei. Kein Zellneustart und keine Arme durch uns bewegt.
- Getrennt vom echten Kameratreiber/SDK. RGB-Pinhole-Näherung, primitive Gehäuse-
  und Stativdarstellung. Keine Tiefenkanäle, realistische Verzeichnung,
  Rolling-Shutter-Verzerrung, Rauschen oder Autofokus simuliert.
- Starter `scripts/overview.sh start|view|reload|coverage|check`. Neue Zellstarts
  starten den Kameraknoten; zur laufenden Zelle wurde er separat über
  `uwa-cell-overview` ergänzt. Sperre pro Benutzer/Partition verhindert zwei
  Besitzer. `cell.sh stop` beendet auch Kamera und separaten Bildbetrachter.
- Pose-/Optikänderungen über `reload` ersetzen nur die Kamera und aktualisieren
  TF/Marker. Nach Anpassung der YAML kein Roboterneustart nötig. Erfolgreich
  zunächst mit2,6m/3m geprüft; diese Versuche sind nach der Nutzerkorrektur
  historisch. Aktueller Stand ist die oben dokumentierte2m-Pose.
- Themen `/uwa_cell/oak_overview/rgb/image_raw` und `camera_info`, optischer TF
  `world -> oak_overview_rgb_optical_frame`. RViz-Config ergänzt um Gehäuse,
  Stativ und Frustum-Marker auf `/uwa_cell/oak_overview/markers` (latched).
  Marker/TF ursprünglich empfangen: zehn Marker, damalige Weltposition[1.8,0,3.0].
- Historischer3m-Prüfstand: bei4k Marker-Minimalseite links/rechts
  ca17,6/28,4px. Sichtfeldrechnung prüft keine Verdeckungen. Echte Erkennung:
  Ausgangspose18/24 Ecken, RMS0,069/0,061px; niedrigere Variante20/24 Ecken,
  RMS0,054/0,096px. Beide Boards jeweils im selben Bild erkannt. Zahlen sind
  Momentaufnahmen, keine Genauigkeits-/Sichtbarkeitsgarantie für alle Armposen.
- Gefundene Grenze: OpenCVs Standard-Minimum3% Bildkante verwirft kleine Marker
  im4k-Gesamtbild. Neuer optionaler Parameter an `detect_pose` belässt den
  Wrist-Standard0,03; Overview verwendet32px minimalen Umfang. Kein GT-ROI oder
  bekannte Kamerapose zum Fit verwendet. Bild-/CameraInfo-Frame und Größe geprüft.
- Build abgeschlossen,70 passende Offline-Tests bestanden; bisherige
  Beschreibungs-/Scan-/Wrist-/ChArUco- und Kalibrierkern-Tests eingeschlossen.
  Belege unter `setup/logs/uwa-oak-overview-*`, Anleitung in
  [docs/oak_overview.md](docs/oak_overview.md). Simulationslivebild geöffnet.
- Grenze: Stativ ist derzeit visuell, ohne Gazebo-/MoveIt-Kollision. Separate
  Gazebo-Modelle gelangen nicht automatisch in die bestehende PlanningScene.
  Kollisionskörper vor entsprechendem Planungs-/Hardwareeinsatz ergänzen.
- Parallele Aufgabe `handeye-diagonal` gesehen: keine Zell-/Scan-Neustarts oder
  Armtests durch OAK-Aufgabe. Automatische Wrist-Hand-Auge-Kalibrierung um die
  externe OAK zu erweitern und reale Welt-Extrinsics zu bestimmen ist Folgearbeit.

## Automatische Hand-Auge-Kalibrierung (2026-11-09)

- **Aktueller Folgeauftrag:** diagonale Paare statt ausschließlich eines Arms:
  links vorne + rechts hinten, danach links hinten + rechts vorne. Die jeweils
  anderen Arme zuvor seriell zur Seite parken. Die frühere Einzelarmreihenfolge
  bleibt in der GUI mit ausgeschalteter Option **Diagonalpaare** bzw. CLI
  `--sequential` verfügbar. Der folgende ursprüngliche Genauigkeitsnachweis
  wurde noch mit dem Einzelarmablauf aufgenommen.
- Paarmodus: gemeinsame zukünftige Startzeit und Dauer beider Trajektorien;
  volle MoveIt-Szene für die Wege plus getrennte Hüllräume aller Kollisionskörper
  über beide Wege, mit 80 mm zusätzlichem Puffer je Arm. Die Freigabe bleibt auch
  bei unterschiedlichem Fortschritt nominal getrennt; keine pauschale
  Reichweitenannahme ersetzt diese Prüfung. Einrichtung und Rückfahrt seriell.
- Anfangs-Boardansichten aus der zentralen YAML dienen zum Wiederanstellen
  geparkter Arme. Die gemessenen tatsächlichen Sitzungsstartstellungen werden
  erst nach Abschluss aller Gruppen wiederhergestellt; Stopp/Fehler halten
  sämtliche aktiven Ziele an der aktuellen Stelle und sperren folgende Fahrten.
- Neuer Paar-Nachweis: **79 aktuelle Offline-Tests bestanden**, vollständiger
  40×4-Lauf `setup/calibration/20261109_133357_7e1130` bestanden; echte parallele
  native Gelenkbewegung in beiden Diagonalpaaren beobachtet. Mindestens 0,307 m
  bzw. 0,372 m Abstand der konservativen nominalen Hüllräume. Wartearme stationär
  (< 1,4e−11 rad Abweichung); alle Rückkehrstellungen < 1,5e−11 rad Fehler.
  [Paar-Prüfbericht](docs/handeye_diagonal_validation_2026-11-09.json).
- Paarlauf: maximale Kameraextrinsics-Abweichung **0,078 mm / 0,030°**;
  relative Basispose links **0,092 mm / 0,0231°**, rechts **0,085 mm / 0,0247°**.
  Basisabstände links **1349,987 mm**, rechts **1349,987 mm**. Fit/Validierung
  bleiben pro Arm 32/8 und relative Posen weiterhin pro linkem/rechtem Tisch.
- Gemeinsames Pause/Fortsetzen und anschließender Stopp beider Controller in
  **0,46 s** bestätigt: `setup/logs/uwa-diagonal-pause-stop.json`.
  Paar-Profil aktiviert, rohe/kalibrierte TFs und Rückfall bei ungültiger Qualität
  sowie kollidierendem Kandidaten geprüft: `uwa-diagonal-profile-check.json` im
  gleichen Logverzeichnis. GUI-Lebenszeichenverlust während simultaner Fahrt
  stoppt beide nach **2,33 s** einschließlich Timeout, paralleler Aufnahmestopp
  bestätigt Stillstand nach **0,30 s**. Danach keine weitere Fahrt/Aufnahme.
  `uwa-diagonal-{disconnect,capture}.json`; alter Einzelarmmodus mit echtem
  GUI-Stopp ebenfalls bestanden (`uwa-diagonal-legacy-gui-stop.json`).
- Vier Pakete gebaut; Zellprüfung bestätigt neun aktive Controller, zum Layout
  passende ursprüngliche Basen und stabile physische Gazebo-Verankerung.
  Das Paarprofil wird beim Start automatisch wiederhergestellt. **Diagonalpaare**
  standardmäßig aktiviert; geänderte Auswahl/Messzahl/Modus nach Vorbereitung
  sperren den Start bis zur passenden erneuten Vorbereitung.

- Nutzerauftrag: genehmigten Plan vollständig in der Simulation umsetzen;
  eigene Qt-GUI, 30–50 verschiedene Stellungen pro Arm (Standard 40), links/rechts
  getrennte relative Basen, unbekannte Kameraextrinsics und explizite Übernahme.
- Neue Pakete `uwa_cell_calibration_msgs` und `uwa_cell_calibration`. Start neben
  der bestehenden Zelle: `ros2 launch uwa_cell_calibration calibration.launch.py`.
  Anleitung: [docs/automatic_handeye.md](docs/automatic_handeye.md).
- Vollständiges MoveIt-Modell mit vier Gruppen und allen Kollisionskörpern;
  lokale quintische Wege mit maximal 0,10 rad/s und 0,20 rad/s² werden vollständig
  gesampelt geprüft. Blockierte Wege werden verworfen, keine OMPL-Umwegsuche.
  Deterministische Kugelkappenansichten mit acht Reserveposen bei 40 Messungen.
- Datensatz: rohe und annotierte Bilder, CameraInfo, Bild-/Objektpunkte,
  zeitlich passende Gelenkwerte und `T_base_link_tool0` unter Workspace
  `setup/calibration/`. Keine Sitzungsdaten ins Repository übernehmen.
- Fit ausschließlich aus Bildern und Werkzeugkinematik: Park-Initialisierung,
  robuste gemeinsame Bildeckenverfeinerung von `X` und `Y` in `M_i X C_i=Y`.
  Bei 40 Stellungen 32 Fit + acht vorab bestimmte, unabhängige Validierungen.
  Keine nominellen Extrinsics / Ground Truth im Fit. Boardpose erst für die
  abgeleiteten absoluten Tischkoordinaten erforderlich.
- Backend und Qt6-GUI getrennt; nicht befehlsfähiger Planungs-/Fit-Prozess,
  eigener Walltime-Watchdog, Besitzer-Lebenszeichen, Controller-Abbruch mit
  Abbremsparametern, Stillstandsbestätigung und Gazebo-Pause als Rückfall.
  Kein automatisches Zurückfahren nach Stopp oder Fehler. Geprüfte Rückfahrt zur
  gemessenen Startstellung nach regulärem Abschluss (im Paarmodus nach allen Gruppen).
- Übernehmen erzeugt ein versioniertes Profil und `calibrated/`-TF-/MoveIt-Modell.
  Physische Gazebo-Montagen und der ursprüngliche TF-Baum bleiben erhalten.
  Kandidatenprüfung vor atomarer Profilaktivierung; altes Profil bei Fehler behalten.
- Prüfnachweise: vier Pakete gebaut, **57 Offline-Tests bestanden**
  (`setup/logs/uwa-handeye-all-tests-final.log`). Vollständige Sitzung
  `setup/calibration/20261109_122753_b901ad`: **40 Aufnahmen je Arm**, jeweils
  32 Fit + acht Validierung, alle Qualitäts- und Ground-Truth-Ziele bestanden.
  [Datierter Bericht](docs/handeye_validation_2026-11-09.json).
- Kameraextrinsics-Fehler: links vorne **0,130 mm / 0,0345°**, links hinten
  **0,049 mm / 0,0306°**, rechts vorne **0,073 mm / 0,0279°**, rechts hinten
  **0,047 mm / 0,0304°**. Validierungs-Reprojektion 0,075–0,122 px medianer RMS.
- Relative Basispose links **0,640 mm / 0,0533°** Fehler, Abstand **1350,012 mm**;
  rechts **0,128 mm / 0,0269°**, Abstand **1349,989 mm**. Park-Bootstrapintervalle
  des Abstands links 1349,736–1350,809 mm, rechts 1349,629–1350,664 mm.
- `setup/logs/uwa-handeye-profile-check.json`: Rückkehrfehler aller Armgelenke
  < 1,4e−11 rad; getrennte rohe/kalibrierte TFs stimmen mit ihrem jeweiligen Modell
  überein. Schlechte Qualität und ein absichtlich kollidierendes Kandidatenmodell
  behalten vorheriges Profil und Modell; gültige Reaktivierung erfolgreich.
  Gespeichertes Profil wird beim Backend-Neustart wieder geladen.
- Echte GUI-Knöpfe live geprüft: Stopp während Planung, tatsächlicher Fahrt und
  Aufnahme; Stillstand bei Fahrt/Aufnahme nach rund **0,30 / 0,29 s** bestätigt.
  Eingefrorenes GUI-Lebenszeichen trotz weiterlaufendem ROS-Thread stoppt nach
  rund **2,27 s** einschließlich Lease-Frist. Keine folgende Bewegung/Aufnahme.
  Direkte Gazebo-Pause bestätigt und anschließend Welt erfolgreich fortgesetzt.
  Logs/JSON: `setup/logs/uwa-handeye-gui-{planning,exercise,capture,freeze,world-pause}.*`.
- GUI zeigt Livebilder und die vollständige Ergebnistabelle in getrennten Tabs,
  bei unverändert erreichbaren Steuerknöpfen. Statusmeldungen verwenden eine
  Steady-Clock und bleiben auch bei pausierter Simulationszeit verfügbar.
- Nur die besitzende GUI fordert bei verlorener Backend-Verbindung automatisch
  die Weltpause an. Beobachterfenster dürfen eine laufende Sitzung nicht durch
  ihre eigene verzögerte Verbindung unterbrechen; Profilwiederherstellung hat
  noch keinen GUI-Besitzer und versendet keine Fahrbefehle.
- Beim ersten Freeze-Test trat erst nach erfolgreicher Stillstandsbestätigung
  ein Prozessabsturz beim Beenden auf. ROS-Executor-Threads werden nun vor der
  Node-/Kontextzerstörung beendet; wiederholter Freeze-Test beendet sich sauber.
- Behobene Simulationsbesonderheit: passive Robotiq-Mimic-Geschwindigkeiten
  können trotz Stillstand stark rauschen. Für den Bewegungsstopp alle
  angetriebenen Gelenke prüfen und zusätzlich unerwartete Gelenkpositionsänderungen
  überwachen; vor Fahrbefehlen ein stabiles Geschwindigkeitsfenster verlangen.
- Grenzen: Simulation mit idealen Intrinsics und angenäherter Kamerageometrie;
  keine reale Stoppsystem-/Hardwarefreigabe. Bootstrapwerte sind
  Wiederholungsstreuung, keine Garantie absoluter Genauigkeit.

## Offene Ziele / noch nicht freigegebene Genauigkeitsannahmen

1. Echte Tischhöhe und Montageposen messen, Basisorientierungen kalibrieren.
2. Individuelle UR-Kinematikdateien übernehmen, sobald verfügbar.
3. Vorhandene grobe Scan-Ausrichtung metrisch kalibrieren, insbesondere reale
   Tischhöhe und Bodenversatz klären. Keine unbestätigte Montagekalibrierung
   automatisch als wahr übernehmen.
4. MoveIt über die nun vorhandene Kalibrier-Kollisionsprüfung hinaus für allgemeine
   und kooperative Bewegungsplanung ergänzen.
5. Später explizit geplante Hardware-Anbindung und Synchronisation untersuchen.

Die Liste beschreibt offene Arbeitspakete, keinen Auftrag, sie ohne weitere
fachliche Abstimmung sofort alle umzusetzen. Aktuelle Konfigurationswerte und
Bedienung haben Vorrang vor überholten Gesprächsständen.
