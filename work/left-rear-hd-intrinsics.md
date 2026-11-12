# Native HD-Intrinsics hinten links vorbereiten

- Status: **in Arbeit**,2026-11-12,Hauptagent LR-HD.
- Nutzer beauftragt Vorbereitung und anschließende eigene native HD-Reihe,
  sobald vorne links fertig ist. Vorhandene VGA-/Hand-Auge-Ergebnisse erhalten.
- Bereiche: eigene Sitzung unter setup/calibration/hardware_handeye/
  left_rear_hd_20261112/, vorhandener HD-Kameradienst, konkrete neue Wege und
  Vorschau. Keine fremden Kamera-Worker verändern, kein Treiberneustart.
- Links vorne läuft separat: bis dessen Abschluss keine LR-Armfahrt und keine
  Änderung seiner Hindernisstellung. Vorläufige Planung mit LF-Endpose nur als
  Prognose kennzeichnen, vor Ausführung echte Endstellungen erneut prüfen.
- Eigene Kamera-only-Prüfung auf left_rear geplant. Speed-/LED-Testaufgabe:
  bitte left_rear ab jetzt für diese Kalibrierung freihalten; RF bleibt frei.
  Vor Zugriff laufende native Kameratransaktionen prüfen, keine fremde beenden.
- Native2592×1944, eigener unveränderter manueller Fokus, rechtes/anderes K/D
  nicht kopieren. Festes linkes40mm-A3-Board IDs0–16. Keine automatische globale
  Aktivierung oder neue Weltanker. Ziel33Fit/8vorabPrüfung wie hinten rechts.

- Erstaufnahme sample_000 PASS:24Ecken/2592×1944, Fokus406Manual,
  Belichtung33333/Gain16;V4L2 währendBurst bestätigt,3verschiedeneFrames und
  vollständigerRestore. Kameraservice uwa-left-rear-wrist-hd mit eingefrorenen
  originalenC-/Workerressourcen, kein parallel veränderterFastpfad.
- Forecastplan:40Ansichten,33Fit/8Prüfunginsgesamt,535,57sFahrt/5418Punkte.
  LF-Endpose ausdrücklichPrognose,modeforecast/executablefalse. RVizDomain73,
  eigenerDienst uwa-left-rear-hd-preview. Kein LR-Bewegungsbefehl.
- Nutzerfreigabe gespeichert: "Vorschau passt, Fahrbereich und Kabel frei –
  nach vorne links starten". NachLF-Abschluss nurgleicheZielreihenfolge,
  echteLive-Stellungen neuprüfen und reviewed_after_left_front erzeugen.
  Skript preparation/recheck_after_left_front.py fährt nicht.
- LR meldetRUNNING/NORMAL/Remote,ros.urpSTOPPED. Trajektoriencontroller wird
  ausdrücklichinaktiv geladen; Play erstnachLF-Ende. FinaleReadiness prüfen.

- LF beendet41/41 und Controllerinaktiv bestätigt18:24:46AWST. NeuerLive-
  WegcheckPASS,40Ziele/Reihenfolge/Rollen exaktwieForecast. EchterBatch unter
  reviewed_after_left_front/, Fingerprint
  d0cb381a24345ef6327bb260417a8941d143893c3040e41c69dee06a154630ee.
  Freigabe an neuenBatch-SHA gebunden. Ein redundanterLF-Service-Lesetimeout
  durch tatsächlichen zeitlich passendenCompletionnachweis+neueLivewinkel
  ersetzt; keinerleiBewegung daraus. EigeneDomain73-Vorschau nachFreigabe aus.
- LRros.urp überbestehendenDashboardROS-Play gestartet,AntwortStartingprogram.
  ErsterReihenstart vorFahrziel wegenfehlenderfrischerRR-Gelenke abgebrochen,
  Controllerinaktiv bestätigt. Startup wartetnun begrenzt16s auf gleichzeitig
  frischeZustände (keineUnionalterSamples);13SequenztestsPASS.
- LÄUFT seit18:29:18AWST: Exec69707,PID85601/startticks791683,Runtime unter
  preparation/runtime.json. Log setup/logs/uwa-left-rear-hd-acquisition.log.
  Zuletzt31/41akzeptiert,20–24Ecken; MOVINGsample_031. KeineanderenArme kommandieren, keineWorkeränderung.
- Eigenes preparation/run_approved_series.py deaktiviert in finally nurLR-
  Bewegungscontroller überMATCH;Cleanupresultatprüfen. BeiAbbruch nurverifizierten
  PID mitSIGINT,keineautomatischeRückfahrt/Quittierung. NachkompletterReihe
  Intrinsics-onlyFit,Originalaudit/Export,Abschlussstatusnachweisen.
