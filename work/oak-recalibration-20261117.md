# OAK-Neukalibrierung und deutliche Fünfkamera-Aufnahme

- Status: **Montage fest und Bewegungsbereich vom Nutzer freigegeben;
  frische Vierarm-Wegprüfung und serielle Aufnahmeposen in Arbeit**,
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
