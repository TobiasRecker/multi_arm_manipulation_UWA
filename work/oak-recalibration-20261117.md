# OAK-Neukalibrierung und deutliche Fünfkamera-Aufnahme

- Status: **Montage fest und Bewegungsbereich vom Nutzer freigegeben;
  erneuter ausdrücklicher Fahrwunsch nach bestandenem RT-Stopptest;
  LF tatsächlich angefahren und nach Messzeitvergleich gehalten;
  korrigierter Vergleich offline, im Prozess-Mock und real lesend geprüft;
  Restanfahrt wird frisch vorbereitet**,
  2026-11-17, Hauptagent.
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
