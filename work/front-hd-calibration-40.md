# Reale Front-Kalibrierung mit40 HD-Messstellungen

- Status: **aktualisierte Durchführung – diagonalen Arm unabhängig zulassen**,2026-11-12.
- Nutzer beauftragt vollständigen Kalibrierlauf mit allen40 Posen und neuem
  HD-Dienst; aus Kontext right_front192.168.8.103. Neue eigene Sitzung
  right_front_hd_20261112, genau40 Gesamtstellungen(32Fit/8Prüfung), fester
  Fokus435 undHD2592×1944. Keine altenVGA-Daten überschreiben/aktivieren.
- Vor Fahrten frische reale Zustände, vollständige MoveIt-Zelle/Verbindungswege,
  native Safety/ExternalControl und konkrete Gesamtvorschau prüfen. Nutzerauftrag
  ist Durchführung der gesamten Reihe; keine unnötige neue Genehmigungsschleife.
- **Parallelkonflikt:** andere aktive Aufgabe left-rear-calibration-preparation
  hat gerade ebenfalls Serienauftrag erhalten. Nur eine realeArmfahrt zugleich;
  Front-Reihe nicht gleichzeitig starten, während Linksreihe noch aktiv ist.
  Eigene Vorbereitungen/HD-Erstaufnahme nur stationär; geplante Hindernisstellungen
  vor Start nach linksseitiger Reihe neu prüfen/ggf.neu planen.
- Bereiche: eigene Sitzungs-/Plan-/Bild-/Ergebnisdaten,gezielte Dokumentation;
  fremde Linksaufgabe/Prozesse und Profile erhalten. Kein pauschaler Neustart.

- Remote bestätigt; alter Front-Motioncontroller vorPower deaktiviert. ROS-
  SetMode-Action nicht verfügbar, deshalb nativeDashboardpower on/brake release/
  play mitNormal/Remote-Prüfung direkt verwendet. RUNNING/PLAYING, echter
  ExternalControlLinktrue/Safety1. Keine Fahrziele bisher.
- ErsteHD-Messung sample000 akzeptiert(2592×1944,24Ecken,435Manual),3
  verschiedeneFrames. Planung39 zusätzlicher wide-Posen läuft CPU-begrenzt.
  LinkeReihe aktiv; Front bleibt biszu derenEnde stationär. Rollen werden
  vor neuer Fahrt auf exakt32Fit/8Prüfung festgelegt.

- Nach linkem SafetyMode3 bei MOVING sample029: Nutzer entscheidet ausdrücklich
  **zuerst links fertigstellen**. Front bleibt stationär; kein Startmarker und
  keine neue Front-Fahrt. Nach linker Fortsetzung ist final_plan erneut aus
  dessen tatsächlicher Endpose zu binden und komplett nachzuprüfen.
- Derzeitiger40erPlan: sample000HD akzeptiert+39Zusatzstellungen,32Fit/8Prüfung.
  AchtPrüfrollen vor Aufnahme fixiert, zusätzlicher spatial holdout sample018;
  Ziele/Rollenfingerprint57b45386…; aktueller,nochmals später zu erneuernder
  Batchf124377a… hat --check-only bestanden. ReineBewegung535,5s.
- Isolierte Front-VorschauDomain69 und eigenes deutliches UWA-HD-STOP-Fenster
  geöffnet, GUI-Prozess besitzt nur künftigen Runner, keine Treiber. Kein
  preparation/start-run.json angelegt. Monitor zeigt1/40 undWAITING.
- Fehlenden Front-Dashboard-ROS-Client separat wieder verbunden, STOP-Service
  rein lesend alsverfügbar bestätigt; keine anderen Treiberneu gestartet.

- EigeneDomain69-Vorschau nach Nutzerpriorisierung geschlossen, UWA-WAITING-/STOP-Fenster bleibt offen. Keine Front-Serie gestartet; keine neuen Prüfungen/Ergebnisse der40er-Reihe behaupten. Fortsetzung nach tatsächlichemLinksabschluss undfrischemRebind/Check.

- Neueste Nutzerkorrektur: Front muss nicht auf links hinten warten; diagonale
  Roboter erreichen einander laut Nutzer physisch nicht. Diese Aussage als
  **Nutzerangabe**,nicht als gemessene Reichweitenkalibrierung dokumentieren.
  Neue Hardwarebatches erlauben genau den diagonalen Partner unabhängig:
  dessenPoseänderung blockiert/cancelt nicht; nurInter-Roboter-Kollisionen
  dieses Paares ausnehmen. Selbst-/Tisch-/Werkzeug-/Gleich-Tisch-Prüfungen und
  nativeUR-Sicherheit erhalten. Alte Prioritätsangaben oben sind überholt.

- Jetzt gestartet: Batch6c70b73a… mitindependent_diagonal_arm=left_rear,
  Vollcheckbestanden,Ziele/Rollenunverändert.26gezielteTestsundBuildpositiv.
  Startmarker/Operatoranweisungvorhanden,GUIrunningtrue. KeineWartepflichtmehr.
  RechteRear-Telemetrie währendfremdemRestartkurzweg,dannvorStartnachgeprüft.
