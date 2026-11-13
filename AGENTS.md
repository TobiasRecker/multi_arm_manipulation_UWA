# Arbeitsregeln für die UWA-Roboterzelle

## Modulare Manipulation und starre Greifverbünde (2026-11-13)

- Nutzer möchte agentbedienbare wiederverwendbare Skills mit Voraussetzungen,
  Ergebnisprüfungen, Abbruchverhalten und versionsgebundenen Prüfnachweisen.
  Erste Anwendung: beide rechten URs greifen leeren Karton, heben kurz an und
  setzen ab; zuerst Simulation mit Kontaktphysik, Chat/CLI/RViz. Agent darf im
  konkreten Auftrag selbst prüfen/fortsetzen; keine pauschale Hardwarefreigabe.
- Ab bestätigtem Griff ausschließlich gemeinsames Objekt/virtuelles Objektframe
  kommandieren, feste Objekt→TCP-Transformationen der beteiligten Arme. Prinzip
  aus match_cooperative_handling wiederverwenden; keine getrennte Planung oder
  unabhängige Zeitparametrierung tragender Arme. Andere Arme bleiben außerhalb.
- Grenzen/Stopps auf gesamten Greifverbund übertragen; Greifkraft bei Armstopp
  erhalten. Keine automatische Öffnung, Rückfahrt oder Wiederaufnahme. Relative
  Greiftransformationen nicht nachführen, um Schlupf zu verdecken. Verbiegen/
  gezieltes Verspannen ist keine Aufgabe dieser ersten starren Betriebsart.
- Erfolg mit Kontaktphysik setzt echten getragenen Karton voraus; künstliches
  Anheften ist kein Haltekraftnachweis. Masse/Reibung und starres Kartonmodell
  als Simulationsannahmen kennzeichnen, keine Hardwaregenauigkeit daraus ableiten.

## Vierarm-Kollisionswächter und PTP-Vergleich (2026-11-13)

- Nutzerauftrag: unabhängiger10Hz-Kugelwächter für genau LF/RF, LF/LR,
  RF/RR, LR/RR; Diagonalen aus dieser Paarüberwachung ausnehmen. Greifer
  einschließlich offener Finger und Wrist-Gehäuse in die Kugelhüllen aufnehmen.
- Abstandsunterschreitung verriegelt das betroffene Paar, keine pauschale
  Vierarmabschaltung bei einer einzelnen Paarverletzung und keine automatische
  Wiederaufnahme. Datenverlust betrifft die zugehörigen Nachbarschaften;
  Gesamtausfall des Wächters hat keine überwachten freien Paare mehr.
- Erste Stufe ausschließlich Simulation64/uwa_cell_sim, alle PC-/ROS-Fahrquellen;
  Pendantprogramme und reale Stoppanbindung sind spätere Arbeit. Hardware-
  Not-Halt von gemessenem Softwarestopp unterscheiden.
- PTP vorab planen; zeitversetzte Starts/Warten sind erlaubt. RRTConnect und
  unabhängige zirkulare Felder mit derselben Zielauflösung/Endprüfung vergleichen,
  kein versteckter RRT-Fallback im Feldansatz. CDF zunächst zurückgestellt.
- Vergleich30Aufgaben×5Seeds×2Verfahren,10s Planungsbudget. Fehlschläge behalten;
  Planungszeit, Validierungszeit, geplante und tatsächlich gemessene Fahrzeit
  trennen. Anleitung docs/four_arm_motion.md, Paket uwa_cell_motion.
- Laufzeit-Stoppreserve auch bei Wächterausfall erhalten: Supervisor darf die
  letzte geometrische Abstandsreserve nicht durch unbedingtes Ausschöpfen des
  Heartbeat-Timeouts verbrauchen. Paarabhängige Lease/Transportalter prüfen.
  Sim-Nachweise unter normaler Physik(RTF≤1) führen; Beschleunigung separat
  nachweisen. Nicht ausgewählte PTP-Arme bleiben gemessen stationäre Hindernisse.
- Geometrische10Hz-Prüfung und Watchdog-Reserve auf dieselbe monotone Echtzeit
  beziehen; langsame/pausierte Gazebo-Zeit darf die Prüfungen nicht verlangsamen.
  Pausierte Quellzustände bleiben STATE STALE und erfordern bewussten Reset.
  Native/Python-Grenzprüfung gemeinsam mit1e-8rad numerischer Toleranz führen,
  echte Grenzüberschreitungen weiter ablehnen.

## Native HD-Intrinsics hinten links (2026-11-12)

- Jetzt 41Ansichten/33Fit/8Prüfung bestanden, eigene physische Kamera
  06561F1400090106 bei2592×1944/Fokus406 manuell. Empfohlener Export:
  `setup/calibration/hardware_handeye/left_rear_hd_20261112/result_v2/`;
  `selected_result.json` in der Sitzung verweist darauf.
- Hier Brown5 mit k3=0: unveränderter erster freier PASS-Fit in result_v1
  hat nicht monotone Extrapolation außerhalb der beobachteten Ecken. Beide
  Versionen erhalten, keine Flags umschreiben. Physikalisch plausiblere
  Extrapolation ist keine gemessene Genauigkeit der äußeren Bildränder.
- Keine automatische globale Aktivierung oder neuer Hand-Auge-Fit; bisheriges
  VGA406-/Hand-Auge-Profil bleibt erhalten. HD-/VGA-Bildquelle getrennt halten.
  [Nachweis](docs/left_rear_hd_intrinsics_2026-11-12.md).

## Native HD-Intrinsics hinten rechts (2026-11-12)

- Eigene 2592×1944-K/D bei Fokus388 manuell jetzt PASS: 41 Ansichten,
  33 Fit / 8 vorab ausgeschlossene Prüfung. Ergebnis und ROS-CameraInfo unter
  `setup/calibration/hardware_handeye/right_rear_hd_20261112/result_v1/`;
  Nachweis `docs/right_rear_hd_intrinsics_2026-11-12.md`.
- Nur für Kamera01D1111A00090912 / nativen HD-Modus / Fokus388 verwenden.
  Keine automatische globale Aktivierung oder neue Hand-Auge-Kalibrierung;
  bestehendes Rear-VGA404-Profil bleibt unverändert. VGA-/HD-K/D nicht mischen.
  Eckenabdeckung und unabhängige Reprojektion sind keine absolute Weltgenauigkeit.

## Wrist-Aufnahmezeit und Beleuchtung (Nutzerauftrag 2026-11-12)

- Wrist-LEDs aller vier Arme nur während Fotoaufnahme oder genutztem
  Videostream einschalten; im Leerlauf ausschalten. Parallele Kameranutzer
  berücksichtigen, aktive fremde Messreihen nicht durch LED-Wechsel stören.
- HD-Beschleunigung mit gemessenen Zeitanteilen und Bildvergleich begründen;
  native Auflösung, fokusgebundene Profile, Frische-/Kontrollnachweise und
  bestätigte Wiederherstellung erhalten. Qualitätsgleichheit nicht vermuten.
- Umsetzung: `WristCamera.activity()` um ganze Videonutzung legen; einzelne
  HTTP-Bilder, HD-Fotos und Kalibrier-Capture sind erfasst. Shared-Lock-Nutzung
  erhalten, fremde Viewer nicht beim Schließen eines Fensters ausschalten.
  Guardian `uwa-wrist-led-policy.service`, Profile unter setup/wrist_lighting/.
  Manueller Nutzungswert standard30%, idle0. Getter-/Setter-LED-Modi sind auf
  diesen UCC-Versionen verschieden; erfolgreiche manuelle Setterantwort und
  tatsächliche Intensität prüfen, Getter1 nicht als Setter1 zurückspielen.
- LR-Rollout ist abgeschlossen; alle vier Kameras sind in der LED-Nutzungsregel
  erfasst. Vor Kamera-Dienstwechseln weiterhin fremde Messreihen und freie
  Nutzungssperren prüfen. Keine Arm-/Treiber-/Programmaktion aus LED-Arbeit.
  Am13.11. im Leerlauf bei allen vier Kameras LED0 real bestätigt.
  Details docs/wrist_speed_led_2026-11-12.md. Fremde direkte HTTP-/Pendant-
  Clients sind ohne Nutzungsmeldung nicht durch diesen PC erfassbar.

## Ausdrücklich übernommene vorläufige OAK-Registrierung (2026-11-12)

- Gemeinsamer Standard jetzt **hardware_20261112_v3**. User akzeptiert die
  erklärte erste OAK↔Front-Wrist-Schätzung für erste Versuche; SHA-gebundene
  Annahme im Profil, Original-`passed:false` niemals umschreiben. Roboterfits
  ausv2 unverändert; neue Rear-HD388-Intrinsics separat geprüft, noch nicht aktiviert.
- OAK-Weltpose mit gemessenem Front-q, Werks-FK und übernommener Hand-Auge-
  Matrix abgeleitet, Welt-/Basisanker bleibt vorläufig. OAK-Stativ **raumfest**;
  spätere Tischverschiebung darf es nicht mitnehmen. Neue Weltbasisvermessung
  erfordert explizite Neuregistrierung. Anleitung docs/oak_preliminary_adoption_2026-11-12.md.
- Gazebo und TF/Marker verwenden dieselbe akzeptierte optische Pose; reale
  Referenz `real_oak4_rgb_optical_frame` ist kein LIVE-Bildnachweis. Jetty/Ogre2
  unterstützt hier Brown-Verzeichnung nicht: Sim-OAK-Pinhole und D=0 ehrlich
  deklarieren, physische Rational14-K/D separat erhalten. Stativ weiterhin
  visual-only, kein neu hinzugefügtes Kollisionshindernis. Nur Kamera neu laden,
  keine Arme zurücksetzen oder echte Hardwaredienste dafür neu starten.

## Neue Kalibrierung links vorne (2026-11-12)

- Abgeschlossen: 41 Ansichten, eigene VGA-Intrinsics und Hand-Auge bestanden
  (640×480, Fokus245 manuell). Relative Basislage zu hinten links über dasselbe
  feste Board bestimmt. [Nachweis](docs/left_front_calibration_2026-11-12.md).
  Ergebnisse separat; keine Übernahme ins aktive Profil oder neue Weltanker.

- Nutzer beauftragt eigene Kamerakalibrierung und Position des UR5left_front.
  Linkes40mm-A3-Board lautNutzer seitLeftRear-Kalibrierung unverändertbefestigt;
  relativeLF/LR-Basislage daraus bestimmbar, absoluteWeltankerweiterunvermessen.
- Vorbereitung/Status: work/left-front-calibration.md, Messdaten getrennt unter
  setup/calibration/hardware_handeye/left_front_20261112/. FremdeK/D undalte
  Links-Home-Annahmen nicht verwenden; alle4Arme liefern jetztLive-Gelenke.
- CB3links vorne i686/32bit ohnegcc: vorhandenernativerHD-Bootstrap scheitert
  vorKameramodusänderung; funktionierendeHTTP-VGA vonungeprüftemHD unterscheiden.

## Gemeinsame mobile Board-Aufnahme (2026-11-12)

- Nutzer bestätigt mobilesA4-Board IDs75–91 für rechteWristkameras+OAK4.
  App **UWA Camera Capture**, `scripts/camera_capture.sh`, Anleitung
  `docs/three_camera_capture.md`. Kamera-only, keine impliziteArmfahrt/Power/Play.
- Fotos über vorhandenenNative-Wrist-/OAK-Fotopfad, keineHQ-Mittelung eines
  beweglichenBoards. OAK-SDK-Vorschau vorFoto schließen UND gemeinsame
  Dateisperrefreigabe abwarten; `oakctl`-Wrapperende allein genügt nicht.
  Pause gibt nur eigeneVorschau frei, keinefremdenKameraprozesse stoppen.
- Fokusprofil `config/three_camera_capture.yaml`, Originalsicherung und
  vollständigerReadback beiWiederherstellung. NativeHD/VGA/Fokusprofiletrennen;
  RR-HD388 jetzt separat validiert, siehe obiger Ergebnisstand.
  Keine automatischenFits/Aktivierung aus der Aufnahme-GUI.
- Kontrast-/Textfeedback, Live-/Snapshot-/STALE-/Bildaltertrennung. Preview-
  ErkennungkeinGenauigkeitsnachweis, Dreierfotos nichtbelichtungssynchron.
  Bilder/Boardkorrespondenzen/Sitzungsberichte nurunter setup/calibration/.


## Vorhandener statischer HQ-Tiefenmodus (2026-11-12)

- HQ-Snapshot in RViz: `bash src/oak_camera_calibration/tools/oak4_photo.sh view-depth`
  aus Workspace. Eigene Domain65-Ansicht, Standardwolke optional; Datum/STATIC
  sichtbar, keine Kameraoffenhaltung und kein world-/Zelltransform. Nur Aufnahmen
  mit tatsächlicher rektifizierter `projection.K` anzeigen, keine Factory-K raten.

- Für statische Tiefenschnappschüsse den bestehenden Fotodienst verwenden:
  `bash src/oak_camera_calibration/tools/oak4_photo.sh capture --mode depth_hq`
  aus Workspace; ROS `/oak4/depth/capture_hq`, Trigger, Domain65/LOCALHOST.
- Native1280×800-Mono-Stereo,16Frames/Median mit Gültigkeits-/Stabilitätsmasken,
  keine Lochfüllung, Rohframes/Metadaten in `setup/oak4/depth/`. Belichtung/Gain
  beider Monos gehalten; RGB-ISO100 nicht als Tiefeneinstellung behaupten.
- Teilt Kamera-/Transaktionssperre und Dienst `uwa-oak4-photo.service` mit RGB.
  Kamera/Szene stillhalten, keine Roboterfahrten auslösen. Weniger Streuung ist
  kein Genauigkeitsnachweis; Maskierung kann die gültige Fläche verringern.
- Anleitung: OAK-Repo `OAK4_DEPTH.md` (Aufruf/Format/Grenzen/echte Prüfergebnisse).

## Vorhandener OAK4-HQ-Fotodienst

- Für physische OAK-Fotos den [wiederverwendbaren Fotodienst](../oak_camera_calibration/OAK4_PHOTOS.md)
  verwenden: aus Workspace `bash src/oak_camera_calibration/tools/oak4_photo.sh capture`.
  ROS-Domain65/LOCALHOST, `/oak4/photo/capture_hq` als Trigger; Standard/Vergleich
  und Status ebenfalls vorhanden. Installiert: `uwa-oak4-photo.service` (user).
- 48MP8000×6000, HQ ISO100/max90ms/achtFrames, gegateter10fps-Sensorbetrieb.
  Bilder und tatsächliche Frame-/Belichtungs-/Fokusdaten in `setup/oak4/photos/`.
  Kamera/Szene stillhalten; kein automatischer Robotermove/Stillstandsnachweis,
  kein RAW und kein Ersatz einer fokusgebundenen Kamerakalibrierung. Exklusiven
  Kamerazugriff beachten, keine fremden Live-/ROS-Dienste automatisch stoppen.

## Bildbasierte Objektdigitalisierung (2026-11-12)

- Nutzerwunsch13.11.: Digitalisierungsdurchlauf deutlich beschleunigen und
  geringeren Reasoning-Aufwand ermöglichen, geprüfte Qualität/Sicherheit
  erhalten. Wiederholbare Schritte in Runner/Formvorlagen/Prüfcode kapseln,
  schnelle Agentenausführung von neuer Geometrie-/Fehlerentwicklung trennen.
  Konzept docs/digitization_pipeline_plan.md; noch keine Modellumstellung oder
  Freigabe neuer Hardwarefahrten. Fehler/Tracking-LOST nicht zugunsten Tempo
  umdeuten; tatsächliche Durchlaufzeit und Qualität vergleichbar messen.

- NVIDIA-Compute seit13.11. ausdrücklich verfügbar: gemeinsame Workstation
  titanpc/192.168.2.137, aktuell WLAN. Vorhandene Nutzerumgebungen, Dienste,
  Systempakete und Treiber erhalten; keine Neustarts oder fremde Bereinigung.
  FoundationPose zunächst in eigenem Ordner/eigener Umgebung auf Datenlaufwerk
  prüfen, Last und freien Platz beachten. Keine Robotersteuerung über diesen
  Rechner. Stand und Bedienung in docs/foundationpose_titanpc.md nachführen.

- Weiteres Nutzerobjekt13.11.: L-Konstruktion aus PTFE und Aluminium, eigene
  Asset-ID ptfe_l_assembly_v1. Nutzerangaben20×20mm-Profile/10mm-Platten von
  geschätzten Außenmaßen300×177×181mm unterscheiden. Keine fremde Karton-
  Szeneinstanz ersetzen. Fotoasset fertig; Texturtracker auf diesem Objekt noch
  LOST, keine übertragene Karton-Trackingfreigabe. docs/ptfe_l_assembly.md.
- Kamera-only-Fünfersets können ausdrücklich --telemetry-source rtde nutzen,
  falls ROS-Treiber fehlen: nur Ausgabefelder timestamp/actual_q/actual_qd,
  unabhängiger Stillstandsprozess und unveränderte Prüfgrenzen. Kein Start von
  Treibern, Programmen oder Bewegung; ROS bleibt Standard. Fehlversuche erhalten.

- Nutzerziel13.11.: bekannte Assets mit6DoF-Pose wiederfinden; langsame möglichst
  genaue statische Lokalisierung vor Greifen und schnelle dynamische Verfolgung
  getrennt anbieten. CPU-Prototyp auf Mini-PC erhalten; zusätzlicher NVIDIA-
  Rechner seit13.11. für isolierte Versuche beauftragt (siehe oben). Backend
  austauschbar halten, keine FoundationPose-Funktionsfähigkeit auf Intel behaupten.
- CPU-Prototyp uwa_cell_tracking, docs/object_tracking.md: direkte Kamerapose
  im unveränderten Assetframe, keine bekannte Szenen-/Boardpose als Schätzprior.
  VALID ist visuelle Konsistenz, keine Manipulations-/Millimetergenauigkeitsfreigabe.
  Bildalter/LOST/Mehrdeutigkeit zeigen, bei Verlust keine alte Pose neu publizieren.
  StatischerBurst setzt Kamera-/Objektruhe voraus. Nur Kameraaktionen, keine
  automatische Armfahrt oder Wiederaufnahme pausierter Planungsarbeit.

- Nutzerauftrag13.11.: texturierten Karton als wiederverwendbares Asset in der
  virtuellen Zelle an seiner beobachteten Stelle darstellen. Versionierte
  Modell-/Texturdateien unter description/assets, Instanzen zentral in
  cell_layout.yaml/scene_objects; Pose aus rechterBoardreferenz ableiten,
  keine parallele Weltpose raten. Gazebo/TF/RViz teilen dieselbe Berechnung.
  Zunächst statisches Visual ohne automatische Kollisions-/Planungsaktivierung,
  laufenden Vergleich nicht ändern; Grenzen der Rekonstruktion erhalten.
  Anleitung docs/carton_scene_asset.md, Nachladen ohne Zell-/Armneustart.

- Reale automatische Scans: Kamera-/SDK-/Bildarbeit in eigenem Prozess halten,
  ROS-Stopp-/Zustandswächter davon unabhängig. Keine GIL-/Bildlast im Fahrprozess.
  GUI-Verlust verriegelt den Lauf auch während Fotos; keine automatische
  Wiederaufnahme nach diesem Stopp. Fehlgeschlagene Fünfersets nicht nachträglich
  als bestätigt ausgeben; einzelne gültige Wrist-Fotos getrennt erhalten.


- Nutzer beauftragt echten Scan mit allen vier Armen parallel und bleibt am
  Nothalt. Dafür neue besser getrennte Ziele prüfen; die zuvor ungeklärten
  hinteren Zusatzwege nicht ungeprüft gleichzeitig starten. Runner/GUI:
  docs/parallel_object_scan.md, scripts/object_scan.sh, keine implizite Power/Play.
- Nach beobachtetem Ethernet-Linkverlust lieferten Hardware-Broadcaster weiter
  JointStates aus Cache. Für automatische Hardwarefahrten zusätzlich echte
  Gerätekommunikation prüfen; ROS-Empfangsfrische allein genügt nicht.
  Alte/geänderte Originalsnapshots nicht zum Ausführen freigeben, neu planen.

- Nutzer möchte zur Beschleunigung virtuelle Trennebenen zwischen den Armen und
  maximale Überschreitungen über ganze Wege prüfen. Ganze Kollisionskörper und
  Zwischenbewegung einbeziehen; zeitunabhängige Bewegungsräume statt nur gleicher
  Fortschrittszeiten vergleichen. Ergebnis nur für die exakt geprüften Wege,
  keine allgemeine Arbeitsraum-/Hardwarefreigabe daraus ableiten.
- Offline-CLI scan_separation, docs/scan_separation.md: Mittellinienüberschreitung,
  zusätzliche räumliche Trennung und „nicht nachgewiesen“ unterscheiden. Bei
  ungeklärten Paaren ursprüngliche Reihenfolge/Stillstand erhalten; keine
  Kollisionsprüfung oder nativeUR-Sicherheit aus dieser Analyse heraus deaktivieren.

- Nutzer präzisiert den Ablauf: zuerst OAK-Foto, grobe Objektlage/-maße daraus,
  dann UR-Ansichten planen. Aktueller neuer Karton steht **zwischen beiden
  Tischen**, Unterseite auf Tischhöhe; alte rechte-Tisch-Kartonpläne sind dafür
  überholt. Nutzermaße40×30×20cm sind grobe Angaben, keine Messfreigabe.
- Erste Umsetzung docs/object_scan.md: OAK-Bootstrap noch mit explizit geprüften
  Objektecken; keine vollautomatische Segmentierung behaupten. Planungsreserve
  getrennt von Endmaßen/Unsicherheit behandeln. Planer erzeugt keine Armkommandos.
- Fünfkamera-Aufruf scripts/object_capture.sh nutzt beide40mm-Boardidentitäten und
  kontinuierlichen Stillstandsaudit. Unterschiedliche Boardframes nur über eine
  beobachtete gemeinsame Bildreferenz verbinden (OAK, falls beideBoards sichtbar,
  sonst expliziter Mehransichtsfit von Kameras, die beideBoards sehen), nicht über
  nominelle Tischabstände. Direkt dasselbe sichtbareBoard bevorzugen. Bilder ohne
  passende native K/D nicht metrisch verwenden. Bestehenden Dreikamera-Aufruf erhalten.
- Mehransichts-CAD seit13.11.: docs/carton_multiview_2026-11-13.md. Optik passend
  zu Identität/Fokus/nativeAuflösung mit Quellenhash datensatzlokal einfrieren;
  separate HD-Ergebnisse müssen dafür nicht global aktiviert werden. Widersprüche
  zwischen Kameras sichtbar behalten, problematische Ansichten nicht in ein
  vermeintlich genaueres Mittel zwingen. Zurückgehaltene Objektpixel dürfen weder
  Geometriefit noch ihre Prüfkamerapose beeinflussen; statische OAK-Wiederholungen
  nicht als unabhängige neue Blickrichtungen zählen. Kontur-Nachzeichnung und
  normierte/vereinfachte Details von mehransichtig vermessener Geometrie trennen.

- Nutzerwunsch vom 2026-11-12: vier Wrist-Kameras plus OAK auf einen gemeinsamen
  Objektbereich ausrichten, fünf Fotos pro Schritt und optional kleine zusätzliche
  Bewegungen. Literaturverfahren prüfen; Konzept docs/five_camera_reconstruction.md.
  Bestehende Posen auf jeweils eigene Boards beweisen keine gemeinsame Objektsicht.
  Kleine TCP-Verschiebungen ersetzen keine vollständige Kollisions-/Wegprüfung.
  Kameraextrinsics je Aufnahme bestimmen; bewegte Kameras sind kein starres Rig.

- Erste assistierte Pipeline `digitize_box`, Anleitung docs/object_digitization.md.
  Gespeicherte Dreier-Farbfotos, sichtbares metrischesTischboard, passendeK/D,
  explizite geprüfte Eckpunkte und parametrischer Geometriefit. KeineTiefe beim
  Auftrag „nur Bilder“ hinzunehmen, keineArmfahrt alleinfürDigitalisierung.
- Intrinsics müssen zu Kamera/Fokus/Bildgröße passen; aktuell Rear-HD388 im
  ersten Kartonversuch nur visuell geprüft. Boardpose jeBild neu schätzen;
  keine ungemessenen alten Roboter-/Weltposen als Aufnahmezustand verwenden.
- Verdeckte Details/Wandstärken alsAnnäherung kennzeichnen; Bildfitresiduen
  und reineAnnotationssensitivität nicht als absolute Genauigkeit ausgeben.
  STEPmm/STLm unterscheiden, Exportframe rechtshändig+Zoben. Keine automatische
  Kollisions-/Kalibrierprofilaktivierung; Rohbilder/Sitzungen nurunter setup/.

## Vor der Arbeit

- [ACTIVE_WORK.md](ACTIVE_WORK.md) und aktive Einträge unter `work/` lesen.
  Eigene Aufgabe dort vor Änderungen eintragen und laufend aktualisieren;
  Statusdatei je Aufgabe verwenden, fremde Einträge erhalten. Dienstneustarts
  und gemeinsame Dateibereiche nennen, bestehende Diffs vor Edits erneut prüfen.
- [HANDOVER.md](HANDOVER.md) enthält Ziele, Entscheidungen, bekannte Grenzen und
  Prüfnachweise; [README.md](README.md) enthält Bedienung und Build-Anweisungen.
- Die übergeordneten Workspace-Regeln gelten zusätzlich.
- `HANDOVER.md` bei relevanten Anforderungen, Korrekturen, Entscheidungen und
  Ergebnissen parallel aktualisieren; dauerhafte Arbeitsregeln hier ergänzen.
  Diese laufende Dokumentation ist ein ausdrücklicher Nutzerwunsch vom 2026-11-09.
- Neue Entscheidungen mit Datum festhalten und widersprechende alte Angaben
  bereinigen. Momentaufnahmen laufender Prozesse nicht als dauerhafte Fakten behandeln.

## Fachliche Leitplanken

- UR-konfigurierte Sicherheitsebenen zusätzlich zur MoveIt-Kollisionsgeometrie
  berücksichtigen. C400-Stopp der ersten realen Reihe wurde vom Nutzer als
  solche Ebene bestätigt. Keine Ebene/Schutzfunktion zum Durchfahren ändern
  oder Stopps automatisch quittieren. Aktueller ausdrücklich gewünschter
  Pausen-/Fortsetzungsstand steht in HANDOVER.md; neue Planung erst nach
  erneuter Nutzeranweisung und aktueller Zustandsprüfung.
  Native Protective/Safety Stops können `robot_program_running=true` behalten:
  automatische Fahrabläufe müssen zusätzlich tatsächliches `safety_mode`
  beobachten und wartende eigene Actions canceln/deaktivieren. Nicht auf einen
  langen Action-Timeout warten und keine automatische Quittierung/Weiterfahrt.
  NORMAL/REDUCED zulässig; manuelle GUI-Operationen bekommen dadurch keine
  neuen Dashboard-/Remote-/Armzahl-/Besitz-Freigabegates.

- Nutzerziel vom 2026-11-10: Simulation und die beiden rechten gemessenen URs
  gleichzeitig in RViz darstellen. `uwa_cell_visualization` überträgt nur die
  beiden JointState-Eingänge von Domain66 nach64, niemals Kommandos/Services/
  Actions. Reale Anzeigeframes/Gelenke ausschließlich mit `real_`-Präfix;
  Simulations-Topics/TFs nicht überschreiben. Zielzeitstempel auf die Anzeige-
  Simulationsuhr umsetzen, originale Hardware-Nachrichten unverändert lassen.
  Fehlende/veraltete Daten zeigen, keine erfundenen Null-/Initialposen anzeigen.
  Montageposen aus zentralem Zelllayout bleiben vorläufig, keine automatische
  Kalibrierung behaupten. Anzeige darf Hardware nicht einschalten/bewegen.
- Ziel ist der digitale Zwilling der echten UWA-Zelle mit vier UR-Armen auf
  zwei beweglich positionierbaren Tischen. Plattform: ROS 2 Lyrical / Gazebo Jetty.
- Geometrie, Tischposen, Montageposen und Anfangsstellungen kommen zentral aus
  `uwa_cell_description/config/cell_layout.yaml`; keine parallelen Zahlenkopien
  als zusätzliche Konfigurationsquelle einführen.
  Nutzerauftrag2026-11-11: gemessene gültige Teilkalibrierungen gemeinsam nutzen.
  Standard-Loader verwendet `cell_layout_calibrated.yaml` als dünne Referenz auf
  diese Geometrie plus `config/calibration/hardware_20261112_v3/profile.json`.
  Rohes Nominalmodell bleibt explizit ladbar. Drei Werkskinematiken sowie
  validierte VGA-Intrinsics/Hand-Auge beider Rear-Arme bleiben erhalten.
  Neuester Nutzerauftrag2026-11-12 nach erklärtem Qualitätsfehler: Front-HD-
  Intrinsics und Hand-Auge ausdrücklich übernehmen. Profilv2 verwendet sie mit
  `operator_accepted_below_threshold`, nativen2592×1944 und Fokus435Manual.
  Fehlgeschlagene `passed:false`-Ergebnisse niemals als PASS umschreiben.
  Ausnahme nur pro exakt SHA256-gebundenem Artefakt mit konkreter dokumentierter
  Nutzerentscheidung; ohne diese gelten die bisherigen Qualitätsgrenzen weiter.
  Integrität, endliche Werte, starre Transformationen und Beobachtungszahlen
  bleiben auch bei ausdrücklicher Übernahme geprüft. Keine neue Basis-/Weltpose.
  Posenreferenzen sind keine aktuellen Hinderniszustände/Fahrfreigaben. Keine
  absolute Basis-/Tischpose aus nur ungefähr bekannter Boardlage ableiten.
- Weltachsen: X rechts, Y hinten, Z oben. Montageposen beziehen sich auf
  **URDF `base_link`**, nicht auf den um 180° gedrehten UR-`base`-Frame.
- Die aktuellen Kabelrichtungen und Yaw-Werte aus der Übergabe erhalten.
  Sie ersetzen die ursprüngliche pauschale Front-/Heck-Ausrichtung.
- Tischhöhe und Montagewinkel bleiben Schätzungen bis zur Kalibrierung.
  Scan-Daten dürfen nicht stillschweigend zu kalibrierten Posen erklärt werden.
- 24 eindeutige Armgelenke, vier native Arm-Trajektoriencontroller und ein gemeinsamer
  Controller-Manager unter `/uwa_cell` beibehalten. Seit 2026-11-09 ergänzen vier
  Robotiq-2F-85-Greifer je einen eigenen Controller und fünf gekoppelte Fingergelenke.
- Wrist-Camera-Linse gegenüber dem UR-Werkzeug-I/O-Anschluss montieren:
  im UR-`tool0`-Frame auf +Y. Werkzeugparameter zentral in der Layout-YAML pflegen;
  primitive Kamerageometrie und nominelle Optik nicht als kalibriertes CAD ausgeben.
- Statische OAK4-D als Übersicht auf einem Stativ rechts neben der Zelle:
  `overview_camera` in derselben Layout-YAML verwenden, Pose/Look-at/FOV als
  Designannahmen behandeln. Ihre eigene Gazebo-Entität/TF lässt sich ohne
  Zellneustart neu laden. Keine Kamera-Designänderung darf Arme zurücksetzen.
  Nutzerkorrektur vom 2026-11-09: vorhandenes Stativ erreicht **höchstens 2 m**;
  aktuelle Montagevorschläge daran ausrichten. Die früheren 3-/2,6-m-Posen
  sind nur historische Designversuche, keine umsetzbare Standardmontage.
  Zwei zusätzliche OAK-Kameras sind laut Nutzer für tote Winkel verfügbar.
  Die erste wurde per USB als **OAK-D Pro AF (RVC2)** identifiziert (2026-11-09);
  die frühere Vermutung „beide OAK-D-S2-FF“ ist überholt. Zweites Modell noch
  ungeprüft. Montage/Einsatz offen; keine Kalibrierung der Zusatzkameras voraussetzen.
  Beide ChArUco-Boards aus echten Bildern prüfen; reine Sichtfeldprojektion
  beweist weder fehlende Verdeckung noch kalibrierte Genauigkeit. Das bisher
  nur visuelle Stativ ist kein Hindernis in der MoveIt-PlanningScene.
  Seit2026-11-12 Kamera-Visual aus Nutzerarchiv oak4-pro-3d-model.zip,
  reduzierte Meter-Meshes unter meshes/visual/oak4_pro; eigene Stativgeometrie.
  Beide Ansichten verwenden overview_visuals.py. Optische Pose/K-D bei reinem
  CAD-Wechsel erhalten; CAD-zu-Optik-Anker und Stativ bleiben visuelle Näherungen.
  Nur Übersichtsentität neu laden, keine Zelle/Armzustände dafür zurücksetzen.
- ChArUco-Boards zentral je Tisch und Kameras initial darauf ausrichten.
  Separates mobiles UR-Board seit2026-11-11: A4-Holzträger mit plan aufgeklebtem
  Papier, Definition `uwa_cell_description/config/mobile_charuco_a4.yaml`.
  7×5 Felder38mm/Marker28mm, DICT_4X4_100 IDs75–91. Nicht mit den40mm-
  Tischboards/IDs0–16 bzw.50–66 verwechseln; diese bleiben unverändert.
  Werkzeug-zu-Board-Montage ist unbekannt, Druckvorlage ist keine Kalibrierung.
  Präzisiertes Nutzerziel (2026-11-09): einen Tisch absichtlich bewegen und
  relative Tischpose/Bewegung messen und kompensieren. Boards bleiben starr
  an ihren Tischen; ihre weltfesten Posen dürfen nicht vorausgesetzt werden.
  Kameramontagen zu ihrem Träger getrennt von veränderlichen Tischposen schätzen.
  Option: OAK auf rechtem Tisch schaut auf linkes Board. Montage ist relativ zum
  rechten Tisch konstant, auch wenn dieser bewegt wird. Zur Einmessung ein
  separates bewegliches Board verwenden, Tischboards dafür nicht versetzen.
  Raumfeste Kamera, tischfeste Kamera und Tisch-zu-Tisch-Messung unterscheiden;
  Simulation-Ground-Truth bleibt unabhängig von der bildbasierten Schätzung.
  Referenzen für diese Kalibrierung sind `left_table_top` / `right_table_top`.
  OpenCV-Musterframe: Ursprung an der Musterecke ohne Rand, Z in die Platte.
  Bildschätzung und Ground-Truth-Vergleich getrennt halten; keine Ground Truth
  zur Auswahl/Initialisierung der PnP-Lösung verwenden. Bekannte Hand-Auge-
  Transformation nicht als aus einer Einzelansicht neu kalibriert bezeichnen.
- Simulation isoliert betreiben: Domain 64, lokale Discovery, Partition `uwa_cell_sim`.
  Physisches Inventar getrennt in `config/hardware_inventory.yaml`:
  `right_rear`=192.168.8.170, `right_front`=192.168.8.103,
  `left_rear`=192.168.8.169 (Nutzerzuordnung/Lesetest2026-11-11),
  `left_front`=192.168.8.2 (Nutzerzuordnung/UR5-Identität2026-11-12), OAK4=192.168.8.238.
  LinksFrontCB3/PolyScope3.15 hat keine e-Serie-Remote-Abfrage; ein unbekannter
  Dashboardbefehl ist kein Beleg fürLocal. FehlendeURCap/Programmkonfiguration
  undRTDE-Inputbelegung tatsächlich klären, nicht perUR-Sicherheitsänderung umgehen.
  Nutzerzählung „erster/zweiter“ ist zufällig; nur stabile Arm-IDs verwenden.
  Kabel laut Nutzer am2026-11-10 ersetzt. Roboterrouten geprüft über Ethernet
  enp87s0, PC192.168.8.209. Keine aktive Sonderbehandlung für die frühere
  Funkanbindung, historische Messwerte nicht in Ethernetwerte umdeuten.
  Nutzerziel vom 2026-11-10: reale Hand-Auge-Erprobung zuerst ausschließlich
  `right_rear`; Bildzugriff und manuell aufgenommene Messreihe vor automatischen
  Hardwarefahrten prüfen. Bestehender Kalibrierbackend bleibt Simulation-only;
  HTTP-Bildempfang ist kein Nachweis eines frischen Belichtungszeitpunkts.
  Nutzerpräferenz desselben Tages: Wrist-Fokus möglichst vom PC per Skript/
  Schieberegler steuern. Fehlende öffentliche API nicht als grundsätzliche
  Unmöglichkeit ausgeben; USB-Anwenderberichte von am Gerät geprüfter Funktion
  unterscheiden. Fokusstellwerte nicht ohne Kennlinie als Meter interpretieren.
  Seit demselben Tag Kamera-Schreibtest/Qt-Fokusfenster für right_rear genehmigt
  und umgesetzt: Kameraeinstellungen sichern, ausschließlich Fokus ändern,
  Bildwirkung/Readback prüfen; keine Robotermotion daraus ableiten.
  Folgeauftrag erlaubt zusätzlich Belichtungs-/Gain-/LED-Regler und begrenzte
  native Foto-Versuche. Helligkeitsänderungen dürfen den Benutzerfokus nicht
  überschreiben. Kameramoduswechsel können Fokus zurücksetzen; sichern und
  ausdrücklich wiederherstellen. Hochskalierung nie als native Auflösung ausgeben.
  Seit2026-11-12 nativer5MP-ROS-Bilddienst für right_front real geprüft:
  `docs/wrist_hd_service.md`. SSH bleibt auf diesen ausdrücklich beauftragten
  Kamerapfad begrenzt; Hardware-GUI/Armsteuerung bleibt SSH-frei. Keine Kennwörter
  speichern. HD/VGA-/physische Kamera-ID undFokus nicht innerhalb eines Fits
  mischen,HD-Intrinsics neu schätzen. Empfangszeiten nicht als Belichtungszeiten
  ausgeben. WährendHD-Transaktion Telemetrie weiterverarbeiten,Originalkamera-
  zustand/Normal vollständig bestätigen und bei Fehler kein Messbild akzeptieren.
  CB3 vorne links: nativen i686-Kameradienst gemäß `docs/wrist_hd_service.md`
  starten; tatsächliche Sensorwerte während der HD-Bursts verifizieren.

  Seit 2026-11-09 ist MoveIt-Kollisionsprüfung für die automatische Kalibrierung
  umgesetzt. Allgemeine kooperative Planung und Hardware-Anbindung bleiben Folgearbeit.
- Automatische Hand-Auge-Kalibrierung: unbekannte Kameraextrinsics aus mehreren
  Stellungen schätzen, nominelle Montagen ausschließlich zum Planen verwenden.
  Validierungsbilder vor Aufnahme festlegen und nie zum Fit verwenden. Ground
  Truth erst nach dem Fit getrennt vergleichen. Linkes/rechtes Tischpaar getrennt.
  Bildzahlvergleiche innerhalb derselben physischen Kamera bei konstantem
  Optikprofil und gleichen, vom Fit ausgeschlossenen Prüfbildern durchführen.
  Gleicher Kameratyp an verschiedenen Armen ist kein Nachweis gleicher
  individueller Intrinsics oder Montage; Arm-/Kamera-/Bildzahleffekte trennen.
  Hardware-CLI seit2026-11-12 für alle vier Arm-IDs; left_rear verwendet das
  linke40mm-Tischboard(IDs0–16), nicht das mobile38mm-A4-Board. Fokus und
  Intrinsics je physischer Kamera neu bestimmen, keine rechten Profile kopieren.
  Nutzer hat für die konkrete Vorbereitung links hinten ausdrücklich automatisches
  Einschalten/Bremsenlösen/Laden/Starten über vorhandenen MATCH-/Dashboard-Ablauf
  beauftragt. Dafür bei erreichbarem Remote-UR keinen unnötigen manuellen
  Pendantstart verlangen. Dies ist keine Freigabe neuer Arm-Fahrziele. Local-
  Umschaltung/fehlende aktive URCap-Konfiguration nicht vom PC umgehen.
- Nutzerkorrektur2026-11-12: diagonale reale Arme dürfen unabhängig parallel
  arbeiten; Front-HD muss nicht auf links hinten warten. Nutzerangabe zur
  physischen Zelle: diagonal reicht die Reichweite nicht zum Berühren. Dies
  ist eine Bedienerangabe, keine gemessene geometrische Kalibrierung. Neue
  Hardware-Messbatches benennen genau `independent_diagonal_arm` und nehmen
  nur dieses Roboterpaar aus MoveIt-Kollisions-/Stillstandsabhängigkeiten aus.
  Paare: left_rear↔right_front bzw.left_front↔right_rear. Selbst-,Tisch-,Greifer-,
  Kamera- und andereArmkollisionen bleiben geprüft, gleichseitiger Tischpartner
  bleibt stationär überwacht. NativeUR-Safety/STOP unverändert. Vorige pauschale
  Einarm-/„erstlinks fertig“-Reihenfolge ist für diagonalePaare damit überholt.
- Genehmigte Bedienung: eigene Qt-GUI für die Kalibrierung mit Vorbereitung,
  Start, Pause/Fortsetzen, jederzeit erreichbarem Stopp und explizitem Übernehmen.
  rqt bleibt die manuelle Zellsteuerung. Seit dem Folgeauftrag vom 2026-11-09
  standardmäßig links vorne + rechts hinten, danach links hinten + rechts vorne
  parallel kalibrieren; andere Arme vorher seriell zur Seite parken. Alle Wege
  gegen die vollständige MoveIt-Szene und getrennte gepufferte Bewegungsräume
  prüfen; blockierte Wege ablehnen. Stopp/Pause betreffen das gesamte aktive Paar.
  Einzelarmmodus bleibt als Auswahl erhalten; keine automatische Rückfahrt nach Stopp.
- Übernommene Kalibrierung ausschließlich als versioniertes Profil und separates
  `calibrated/`-TF-/Planungsmodell aktivieren. Physische Gazebo-Montagen und
  Ground-Truth-Modell erhalten. Ergänzung2026-11-11: Nutzer beauftragt explizit
  die gültigen real gemessenen Teilparameter auch als Simulationsstandard;
  dies erfolgt über obiges zusätzliches Profil, ohne das Nominalmodell zu ändern.
  Simulierte Nachkalibrierungen je Modellprofil getrennt speichern, frühere
  ideale Simulationsfits niemals als reale Messungen laden. Optikfit misst
  keinen Gehäusekörper: nominelle Kamera-Kollisionskörper nicht daraus versetzen.
  Keine automatische Rückfahrt nach Stopp/Fehler.
  Sitzungen/Rohbilder unter `$UWA_WS/setup/calibration/` nicht einchecken.

- Nutzerauftrag2026-11-12: Kamera-SSH ohne wiederholtePasswortdialoge, dedizierte
  Schlüssel unter~/.ssh; `wrist_hd.SSH` verbindet automatisch mitstriktemHostvertrauen.
  Drei e-SerieURsEd25519,CB3LinksFront eigenerRSA3072wegenOpenSSH6.0,kompatibler
  Signaturmodus nurfürdiesenHost. KeineKeys/PasswörterinsGitoderLogs. SSH bleibt
  aufbeauftragteKameraoperationenbegrenzt,HardwareGUI/ArmsteuerungSSH-frei.

## Verbindliche Bedienerwartungen

- Folgeauftrag2026-11-10: erste reale Bildpose und Intrinsics-/Hand-Auge-Test
  ausschließlich right_rear. Nutzer bestätigt rechtes A3-Board1:1 und100mm
  Kontrollstreifen, keine bekannte passende Wrist-Intrinsics-Kalibrierung.
  Separate Hardware-Aufnahme auf Domain66, Simulationsbackend nicht umbiegen.
  Reale Intrinsics aus tatsächlich verwendetem Bildmodus/festem Fokus fitten;
  nominelles K/optische Montage nur zur Planung. Vorab markierte Validierungs-
  bilder aus Intrinsics- und Hand-Auge-Fit ausschließen. Echte JPEGs, erkannte
  Punkte, Kamerazustand und gemessene Werkskinematik-Flanschpose speichern.
  HTTP-Empfang/wechselnde Payloads sind keine garantierten Belichtungszeitstempel.
  Nutzer hat nach Vorschau eine40-Ansichten-Hardwarefolge ausdrücklich freigegeben;
  diese Einzel-Erprobung nicht als generelle Bewegungsfreigabe verallgemeinern.
  Ergebnisse separat versionieren und nicht ungefragt als aktive TF übernehmen.

- Nutzerauftrag2026-11-10: vor Hardware-Kamerakalibrierung andere Arme seriell
  parken, zunächst nur right_front per generischem Skript testen. Linke Arme
  laut Nutzer bereits aufrecht in Default Home: nominell [0,-90,0,-90,0,0]°,
  als Nutzerangabe kennzeichnen, keine Encodermessung behaupten. Parkwerkzeug
  plan/preview/execute trennt konkrete Wegprüfung von Realfahrt; MoveIt-Szene
  und tatsächliche rechte JointStates verwenden. Fehlende Hinderniszustände
  niemals still aus Simulationsposen zu realen Messungen machen. Nur einen Arm
  bewegen, keine automatische Heim-/Rückfahrt nach Abbruch. Vorschau Domain68,
  keinerlei Kommandobrücke zu Hardware66/Mock67/Gazebo64. Kalibrierbackend
  selbst bleibt Simulation-only, bis separat beauftragt/integriert.

- Nutzerauftrag2026-11-10: MuR-artiges manuelles Jogging, zunächst right_rear,
  mit demselben IntegratedCartesianAdmittanceController/J-PARSE. Nachgiebigkeit
  standardmäßig AUS: admittance und wrench_twist_gain null, keine FT-Pflicht.
  Gainänderungen des on_init-Plugins durch inaktives Neuladen anwenden, nicht
  bloß als dynamische ROS-Parameter setzen. Hold-to-jog/Loslass-Stopp, Base-Frame,
  keine automatische Fahrt durch Öffnen des Dialogs oder Aktivieren des Reglers.

- Nutzerhinweis vom 2026-11-10: Monitor mit schwachem Kontrast. Klickannahme
  deutlich hervorheben, nicht nur durch subtile Standard-Buttonzustände.
  Dauerhafte Rückmeldung mit großen Textlabels RECEIVED/RUNNING/DONE/FAILED,
  Aktionsname, Verlauf/Fehlerdetail und Laufzeitanzeige. Automatische Statuspolls
  dürfen ein manuelles Fehlerergebnis nicht überschreiben. Bedienung auf Englisch.
- Nutzerwunsch vom 2026-11-10: UR-GUI vollständig **Englisch**, einschließlich
  Beschriftungen, Tooltips, eigener Meldungen und Startmenüeintrag **UWA Arms**.
  Gesprächssprache bleibt Deutsch. **Save logs** muss während laufender
  Operationen erreichbar bleiben und aktuelle Sitzung/Prozessausgaben/zugehörige
  ROS-Logs lokal mit Status-Snapshot exportieren. Eindeutige Sitzungsordner,
  keine bloß gekürzte Bildschirm-Logkopie; älteren übernommenen Treiberkontext
  kennzeichnen. Exporte unter `setup/logs/uwa-control/exports/`, neuester Pfad
  in `setup/logs/uwa-control/latest-export.txt`. Keine Roboterbefehle beim Export.
- Nutzerauftrag vom 2026-11-10: lokale Vierarm-Vorbereitung und vereinfachte
  eigene UWA-GUI mit Armauswahl oben links, ohne SSH/rsync/mobile Infrastruktur.
  Gemeinsamer UR-Start und Controller bleiben im MATCH-Repo (`match_ur_hardware`,
  `mur_control`, `mur_launch_hardware`); `uwa_cell_control` referenziert sie.
  Physische Konfiguration ausschließlich aus `config/hardware_inventory.yaml`.
  App **UWA Arms**: Mock als Standard in Domain67, Hardware in Domain66,
  jeweils lokale Discovery; Mock-Treiber/-Clients strikt von Hardware trennen; kein
  automatisches Power/Brake/Play beim Treiberstart. Vorhandene Ein-Gegenarm-
  Kollision nicht als vollständigen Vierarm-Kollisionsschutz darstellen.
  Neueste Nutzerkorrektur vom 2026-11-10: zusätzliche UWA-Sicherheitsgates
  entfernen. Keine Armzahl-, Dashboard-NORMAL/Remote/RUNNING/PLAYING-, exakte
  Programmpfad- oder GUI-Treiberbesitz-Sperre vor manuellen Operationen.
  Keine eigene Netzwerk-/Latenz-Sperre einführen. Native UR-/Treiber-
  Ablehnungen und vorhandene Kollisionsalgorithmen erhalten. Insbesondere keine
  UR-Sicherheitsfunktionen umgehen oder Stopps automatisch quittieren.
  Standardauswahl bleibt hinten rechts (`right_rear`). Automatische Regressionen
  verwenden Mock und senden keine realen Power/Brake/Play/Ziele. Davon getrennt
  hat der Nutzer am selben Tag den konkret in RViz geprüften Hardware-Parkweg
  für right_front ausdrücklich freigegeben; diese Einzel-Erprobung dokumentieren.
  Laufende andere Hardwaretreiber erhalten.
  Technische Profil-/Portprüfung, Schutz gegen doppelte Treiberinstanzen und
  Aufräumen eigener Prozesse erhalten. Bedienung: `docs/ur_control_gui.md`.
- Die App **UWA Cell Simulation** soll mit normalem Klick Gazebo, rqt, RViz
  **und den Scan-Publisher** starten. Auch ihre Aktion **RViz öffnen** lädt den Scan.
  Den früheren App-Standard ohne Scan nicht wieder einführen.
- Der direkte Terminal-Launch darf weiterhin ohne Scan starten; die Simulation
  muss auch bei fehlendem Drive/Scan funktionieren.
- Wiederholte App-Aufrufe sollen vorhandene Dienste weiterverwenden und weder
  doppelte Publisher erzeugen noch die laufende Simulation unnötig zurücksetzen.
  Bereits geöffnete Fenster wiederherstellen/nach vorne holen; „Dienst aktiv“
  allein erfüllt die sichtbare Bedienerwartung beim erneuten Icon-Klick nicht.
- RViz muss explizite Kamera-Werkzeuge enthalten: `MoveCamera` als erstes Tool,
  außerdem Interact, Select, FocusCamera und Measure. Orbit-Drehen und Zoom müssen funktionieren.
- Das App-Icon gefällt dem Nutzer. Außenrand transparent lassen, das dunkelblaue
  abgerundete Feld und das Vier-Roboter-Motiv erhalten. Den weißen Rand nicht zurückbringen.
- Originalscan auf Google Drive belassen; keine PLY-Dateien oder Scan-Caches einchecken.
- Scan-Bereinigung: 4 m Kugelradius in Weltmetern um den Mittelpunkt der vier
  Roboterbasen; die aufgenommenen Roboter durch feste Scan-Masken ausblenden.
  Masken nicht an die aktuellen bewegten Modell-TFs koppeln. Bei Änderung der
  Scanregistrierung die Masken neu prüfen; Rohdaten und Importcache erhalten.

## Prüfen und übergeben

- Build, Umgebungsvariablen und Prüfkommandos aus der README verwenden.
- Passend zur Änderung prüfen: bei Layoutänderungen Modell/TF, bei Controlleränderungen
  zusätzlich Simulation und gezielte Bewegungen, bei App-Änderungen den **installierten**
  Desktop-Eintrag statt nur einen manuell gestarteten ROS-Knoten testen.
- Eine aktivierte PointCloud-Anzeige oder „Status: Ok“ allein beweist keinen Scan-Empfang:
  Publisher, empfangene Punkte und den Transform zur Welt prüfen.
- Bei Änderungen an Setup/Startmenü die nötige Installation konkret durchführen
  und die Bedienung in der README mitpflegen. Bestehende lokale Änderungen erhalten.
- Dokumentation: belegte Erfolge mit Datum/Logpfad und offene Einschränkungen nennen;
  keine neuen Tests oder Hardware-Freigaben behaupten, die nicht erfolgt sind.
