# Kalibrierung links hinten vorbereiten

- Status: **abgeschlossen – 41 Bilder, Intrinsics und Hand-Auge PASS**,2026-11-12, Hauptagent.
- Nutzer hat left_rear eingerichtet; Auftrag: Erreichbarkeit prüfen und
  Kalibrierung vorbereiten. Keine neue reale Fahrfreigabe ableiten.
- Ziel192.168.8.169, External Control PC192.168.8.209/Port52002, Domain66.
  Bestehende drei Treiber und andere Aufgaben erhalten; keine pauschalen Kills.
- Bereiche: rein lesende Dashboard-/Kamera-/ROS-Diagnose, Linksarm-Fähigkeit
  des Hardware-Kalibrierwerkzeugs, getrennte Sitzungs-/Planartefakte und
  Bedienung/HANDOVER. Bisherige Kalibrierprofile erhalten.
- Prüfen: aktuelles Board/Format, Kamera/Fokus/Bildmodus, alle Armzustände,
  Kinematik/FK, vollständige MoveIt-Szene, ausführbare oder ausdrücklich
  unbestätigte Vorschau. Keine Power/Brake/Play/Controlleraktivierung/Fahrt.
- Folgeanweisung: Nutzer beauftragt ausdrücklich Einschalten/Bremsenlösen/
  Programmstart über vorhandenen MATCH-Ablauf; deshalb diese früher ausgeschlossenen
  Vorbereitungsschritte nun ausgeführt. Keine Freigabe für Fahrziele.
- left_rear erreichbar, RUNNING/NORMAL/Remote nach MATCH-Prepare, ros.urp
  nativ geladen/PLAYING mit tobias.installation. External-Control-Link bleibt
  false, keine Verbindung an52001–52004 trotz passender Listener undPC209.
  Nutzer um aktive URCap-/Programmknotenprüfung Host209/Port52002 gebeten.
- Hinten rechts Local/POWER_OFF liefert Nullwinkel; gültige aktuelle rechte
  Hindernisstellungen noch offen. Nutzer um Remote/Einschalten dort gebeten.
  Bestätigt: linkes40mm-A3-Tischboard und links vorne aufrechtes Home unverändert.
- Hardware-CLI auf alle vier Arm-IDs erweitert;25 Offline-Tests inkl. echter
  MoveIt-/IK-Sweeps rechts/links, CLI-Auswahl und zwei Lyrical-Startup-Warnpfaden.
  MATCH ur_startup_enable.py .warn→.warning repariert. Build UWA-Control erfolgt.
- Reine Entwurfsvorschau34,1s unter setup/calibration/hardware_handeye/
  left_rear_20261112/design_preview/, ausführbar=false, rechte Arme unbestätigt.
  Ablauf41 Gesamtbilder(33Fit/8Prüfung)/wide vorbereitet, noch keine Sitzung
  begonnen. Kamera640×480/3verschiedeneFrames,439Auto nur gelesen, kein Board
  im aktuellen Bild. Fokus/Boardbild nach erster freigegebener Pose prüfen.
- Daten/Diagnose unter .../preparation/, insbesondere preparation-plan.json und
  final-readiness.json. docs/left_rear_calibration_preparation_2026-11-12.md,
  README/AGENTS/HANDOVER aktualisiert. Keine Fahrziele/Schutzquittierung;
  alte Besitzer-GUIs/drei Treiber erhalten. Eigenes zusätzliches Beobachterfenster
  ohne Treiberbesitz beendet. Nach Klärung frische vollständige Planung, konkrete
  Vorschau und Fahrfreigabe erforderlich; Entwurf nicht einfach ausführen.
- Letzter Snapshot während der erbetenen Pendantprüfung: left_rear RUNNING/
  Local/STOPPED ros.urp, beide rechten POWER_OFF/Local. Keine erneuten
  Programmstartversuche, solange der Nutzer die aktive Konfiguration prüft.

- Nutzer bestätigt URCap-Einstellungen und bittet um Wiederholung. Recheck01:
  left_rear RUNNING/NORMAL/Remote/STOPPED ros.urp, rechte Rear jetztRUNNING/
  NORMAL/Remote mit plausiblen Winkeln. Front weiterPOWER_OFF/Local mit
  gemeldeten nicht-null Gelenken; separate front-wrist-hd-ssh-Arbeit erhalten,
  keine Kamera-/Power-/Programmänderungen vorne rechts.

- Recheck-Ursache im Treiberlog nachgewiesen: linker Manager260072 belegt8998
  FDs(davon8967Sockets); Scriptserver verwirft neu eintreffende Verbindungen
  wegen FD_SETSIZE1024. Kein erneuter URCap-Fehler behaupten. Geplant: nur
  verifizierten Links-Launcher260016 nach Inaktivprüfung sauber ersetzen,
  rechte Manager18298/18299 und parallele Front-Kameraarbeit unverändert.
- Erfolgreich: nur Links-Launcher sauber ersetzt, neuer Dienst
  uwa-left-rear-calibration-driver, Manager48FDs. MATCH-Start Exit0,
  ExternalControl=true/SafetyNORMAL/vier Motioncontroller inaktiv. Rechte
  Manageridentitäten identisch; Ursache FD-Wachstum selbst noch nicht bestimmt.
- Frischer approach_ready-Plan34,173s und --check-only bestanden, RViz Domain68
  offen. Rechtes Front-RTDE als Ausgabe unabhängig mitROS gegengeprüft, gleiche
  Winkel trotzPOWER_OFF, keine Frontzustände geändert. Keine Fahrziele.
- Als Nächstes konkrete erste Vorschau/Freiraum freigeben lassen, danach nur
  erste Ansicht und Bild-/Fokusprüfung. Ganze Reihe noch nicht geplant/gestartet.

- Nutzer gibt genau approach_ready/f6296105… für links hinten ausdrücklich frei:
  Vorschau passt, Fahrbereich frei, erste Pose anfahren. Keine Freigabe einer
  ganzen Reihe. approval unter preparation/first-view-approval.json gesichert.
- Erste34,173s-Fahrt erfolgreich, ActionResult0, unmittelbarer maxZielwinkel-
  Fehler0,0000158rad; späterer Snapshot0,0000513rad. NativeSafetyNORMAL,
  ExternalControltrue, velocities0; linker skalierterJTC hält. Front-Endvergleich
 0rad, Rear-Endvergleich0,0000246rad. Keine Rückfahrt oder weiteren Armziele.
- Echte erste Bilder: initialer Autofokus-Übergang unscharf, danach viermal
 17Marker/24Ecken links IDs0–16. Vollständiges unverdecktes Muster im geprüften
  Bild, fünf unterschiedliche Payloads, Fokus406Auto/33333µsAuto/Gain16 gelesen;
  keine Kamerawerte geschrieben und keine Kalibrieraufnahme als sample000 erzeugt.
- Folgeplan batch_plan/batch.json mit40 Zusatzansichten/8vorabPrüfrollen erzeugt,
 709,57s reine Bewegungszeit. Nur Planung, keine ganze Reihe freigegeben/gestartet.
  Nächste Stufe: feste passende Optik, sample000, Gesamtcheck/-vorschau und eigene
  konkrete Freigabe der neuen Folge. Erledigte eigene RViz-Animation geschlossen.

- Nutzer beauftragt jetzt ausdrücklich Durchführung der vorbereiteten Messreihe.
  Serienfreigabe für batch_plan-Fingerprint unter preparation/series-approval.json
  gesichert. Fokus/Belichtung fixieren, sample000, vollständiger Check und
  Gesamtvorschau vor realem Start; nur left_rear bewegen, native Stopps erhalten.

- Erste Messaufnahme sample000 mit24Ecken,640×480,406Manual/33333µsManual/
  Gain16 akzeptiert. Vollständiger --check-only für40 Zusatzsegmente bestanden,
  Gesamtvorschau geöffnet; Nutzerfreigabe für genau den vorbereiteten Batch
  bereits vorhanden. Keine weitere Bestätigung für denselben Plan verlangen.

- Optik406Manual/33333µsManual/Gain16 fixiert und viermal24Ecken geprüft.
  sample000 akzeptiert,40Segmente-Gesamtcheck bestanden, Gesamtvorschau offen.
  Genau der freigegebene Batch850765e9… läuft mit HTTP-VGA links hinten,
  explizites UWA-Arms-STOP-Fenster nurleft_rear geöffnet. Keine anderen Armziele,
  kein Auto-Reset oder Rückweg; danach unabhängige Intrinsics-/Hand-Auge-Auswertung.

- Unterbrechung bei sample029 durch nativen C159A5;29 Bilder(23Fit/6Prüfung)
  gesichert, Goal gecancelt und alle linken Motioncontroller inaktiv bestätigt.
  Rein lesendes RTDE bestätigte0kg/CoG[0,0,0]. Keine automatische Quittierung.
- Nutzer meldet Ursache behoben. Recheck:1kg/CoG[0,0,0],NORMAL/PLAYING/Linktrue,
  vollständige frische dreiArm-Telemetrie; Fokus406Manual/33333µs/Gain16 erhalten.
  Nur zwölf fehlende Originalziele neu verbinden/prüfen; rechte Front-HD-Reihe
  bleibt bis Linksabschluss stationär. Kein Dienstneustart vorgesehen.
- Separater29er-Diagnosefit: Intrinsics-Prüfung0,140px,Hand-Auge0,253px,
  Boardstreuung0,652mm/0,165°. Keine Aktivierung:29<30 Mindestansichten.

- Fortsetzungsstart vor jeder Bewegung abgelehnt: hinten rechte Live-Telemetrie
  verloren. Dessen ursprünglicherManager18298 stürzte nach PrimaryClient-Pipeline-
  Überlauf mitExit−11 ab; zwischenzeitlich auchDashboard nicht erreichbar, danach
  RUNNING/NORMAL/Remote/STOPPED. Nur rechten Rear-Treiber für Zustandsmessung
  wieder starten, keine Power-/Play-/Armziele; anschließend Vollcheck wiederholen.

- RechterRear-Treiber als uwa-right-rear-calibration-observer wieder aktiv,
  ohnePower/Play/Armziele; vollständigeTelemetrie und erneuter --check-only
  bestanden. Fortsetzung in resume-run-after-observer.log läuft;sample029
  mit24Ecken akzeptiert. Ausschließlich linkeBewegung.

-32 Bilder gesichert(sample000–031), Abbruch vor sample032 wegenFrontbewegung.
  AktuelleAGENTS-Nutzerkorrektur erlaubt unabhängigesDiagonalpaarLR↔RF.
  Neue Restplanung resume_diagonal mit denselben neunOriginalzielen/-rollen,
 102,51s Bewegung; neue Diagonaltests2/2 bestanden. Keine Fremdprozesse stoppen.

- DiagonaleAusnahme zunächst vonAutoReview abgelehnt: keine neueFahrt. Nutzer
  bestätigt anschließend hier ausdrücklich: „Ja, diagonale Arme erreichen sich
  nicht; Restreihe ausführen“. approval.json gespeichert, erneutFullcheck
  bestanden, Batchd913d5c2… gestartet. Nur gegenseitigeLR/RF-Kollisionen und
  derenStillstandsabhängigkeit ausgenommen; übrigePrüfungen/nativeSafety bleiben.

- Abschluss12:17AWST: alle41Bilder/33Fit/8Prüfung, je24Ecken/41unique,
  Originalrollen unverändert. Intrinsics-Prüfmedian0,1481px,Hand-Auge0,2496px,
  Boardstreuung0,7402mm/0,1671°. Ergebnis PASS, activated=false.
- Versionierter kompletter result_v1-Snapshot mitSHA256 gespeichert. NativeSafety
  NORMAL, vierlinkeMotioncontroller inaktiv, letztesZiel3,38e-5radFehler; keine
  Rückfahrt. EigenesSTOP-Beobachterfenster undTreiber bleiben bereit. Front-
  HD-Aufgabe bleibt unabhängig. Keine Aktivierung oder neueFahrziele offen.

- Folgeauftrag2026-11-12: gültige linkeRear-Kalibrierung jetzt ausdrücklich
  global als hardware_20261112_v1 aktiviert; siehework/global-calibration-oak-boards.md.
  Historisches result_v1 bleibt unverändert.
