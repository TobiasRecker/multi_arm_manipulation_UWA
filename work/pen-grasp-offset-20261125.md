# Seitlicher Stift-Fehlgriff und unnötige Handgelenksdrehung

Stand25.11.2026 (Australia/Perth). Nutzer meldet nach Stiftanfahrt mehrere
Zentimeter seitlichen Fehler bei plausibler Höhe und möglicherweise unnötige
~170° Handgelenksdrehung statt kurzer symmetrischer Orientierung.

## Tatsächlicher Lauf und aktueller Zustand

- Lauf `a49718ebcac64a849d218afb8c618704`, initial15:25:24AWST. Anfahrt-
  Review `743ee5361d9944d79515d9d588c19246` um15:30:40 angenommen;
  Anfahrt/Öffnen/Einfahrt erfolgreich. Einfahrfoto15:31:47,
  Kontaktreview `54d00141641748b1999da570e8b0fd28` um15:34:03 angenommen.
- Beim Eintreffen der Diagnose waren Schließen und Hub bereits beendet.
  N100-Workflow `PEN_LIFT_COMPLETED/success=true`, aber `close_result` meldet
  **contact_detected=false, OBJ3/POS227/PRE255/FOR0/SPE16**. Dies beweist
  ausgeführte Befehle, keinen erfolgreichen Stiftgriff. Nutzerbeobachtung
  und Einfahrbild zeigen den Zentrierfehler. Kein Nachgreifen/Öffnen gesendet.
- Neuester vorhandener Safety-Export vom24.11.,18:23 deckt diesen Lauf nicht
  ab. Aktuellen Schutz-/Reviewstatus und N100-Originalworkflow gelesen.
- Agenten-Pausenaufruf zunächst von automatischer Prüfung abgelehnt:
  ohne Kollisionsmeldung fehle ausdrückliche Nutzerfreigabe. Nicht ausgeführt.
  Nutzer bestätigt danach ausdrücklich „Ja, alle Arme jetzt pausieren“.
  Erster danach angefragter Aufruf scheiterte allein am Zeitlimit der
  automatischen Freigabeprüfung. Ein vom Reviewer ausdrücklich erlaubter
  erneuter Versuch mit `bash protection.sh pause` wurde ausgeführt.
- Abschließende Statusabfrage bestätigt PAUSED/OPERATOR PAUSE, alle vier
  Controller paused=true/confirmed=true/action_active=false. Greiferziel
  unverändert. Keine Safety-Quellen-/Grenzwertänderung, kein Resume.

## Drehung: numerischer Nachweis und Korrektur

Ursprüngliche Anfahrt q6 von−1,442778rad auf+1,604626rad = **+174,603°**.
Compiler iterierte symmetrische Orientierung sign+1 zuerst und brach beim
ersten gültigen vollständigen Plan ab, ohne sign−1 zu vergleichen.

`grasp_candidates()` erzeugt jetzt IK-Kandidaten für beide180°-äquivalenten
Greiforientierungen und ordnet die Suche nach Gelenkweg zum Kontaktziel.
Dies ist eine Vorreihung, kein behauptetes globales Pfadoptimum. Jeder
gewählte Kandidat muss weiterhin Anfahrt, Einfahrt und getragenen Stift
vollständig auf Kollisionen und Controllerzeitgesetz prüfen. Keine
Kollisionsausnahmen oder Tempogrenzen verändert.

Offline-Gegenprobe mit unveränderter alter Kamerareferenz und demselben
archivierten Start: vollständiger gültiger Plan mit q6-Anfahrt **−5,397°**,
17,759s insgesamt statt73,132s. Reduktion entsteht aus kürzerem Weg bei
unverändertem0,1rad/s, nicht aus höherem Tempo. Kein Hardwareauftrag.

## Seitlicher Fehler: rechter gegenüber linkem Boardbezug

Rein bildliche Gegenprüfung des tatsächlichen nativen Einfahrfotos mit
identischen USB-Optikdaten4056×3040/Fokus112 und vorhandenen Boarddefinitionen:

- Rechtes Board neu gefittet: Prüf-RMS0,616px; Projektion mit der benutzten
  rechten Sitzung RMS0,740px. Der rechte Bezug ist im Foto konsistent.
- Linkes Board:17 Marker, unabhängiger Prüf-RMS0,403px. Derselbe rechte
  Kamerabezug projiziert dessen bekannte Modelllage dagegen mit **83,817px**
  RMS daneben.
- Stiftpose mit lokalem linken statt rechtem Boardbezug aus demselben
  Einfahrbild: ΔWelt≈[−39,883,−3,978,+1,358]mm. Das passt zur gemeldeten
  seitlichen Abweichung bei plausibler Höhe. Es ist ein Referenzwiderspruch,
  keine unabhängige absolute Vermessung des TCP oder der Basis.
- Gegenprüfung aus den Anfangsbildern:24.11. Δ≈[−37,724,−3,923,+0,949]mm;
  25.11. Δ≈[−40,118,−4,348,+3,187]mm. Befund bereits im gestrigen Bild
  vorhanden. Keine spontane einzelne schlechte Pen-Markermessung belegt.
- Modellinterner Ist-Endpunkt gegen Soll-Tool0 am Einfahrende: Translation
  ≈[+0,002,−0,002,+0,048]mm, Rotation0,0056°. Das bestätigt die interne
  Zielnachführung, nicht die absolute physische Welt-/Kameraregistrierung.

Auf diesen Befund hin Nutzer gefragt, ob das linke feste Tischboard seit
der übernommenen Basiszuordnung unverändert ist. Antwort noch ausstehend.
Übernommene Basisanbindungen nicht geändert, keinen manuellen40-mm-Offset
oder Kamera-Mittelwert eingeführt.

## Vorbereitete lokale Aufgabenänderungen

- Optionaler `reference_board='left'`-Pfad im Stiftcompiler: linkes Board
  direkt im aktuellen nativen Stiftfoto fitten, mindestens12 korrekt
  zugeordnete Marker/Prüf-RMS<2px verlangen. Referenz und Rohbildhash pro
  Lauf sichern. Gemeinsame rechte12h-Sitzung und alle Basisbindungen bleiben
  unverändert. Bei fehlendem lokalen Nachweis kein stiller rechter Rückfall.
- **Aktive Programmdefinition bleibt bisher unverändert.** Nur gesonderte
  Offline-Entwurfsdefinition nutzt den linken Bezug. Aktivierung hängt von
  der noch offenen physischen Boardbestätigung ab.
- Offline-Entwurf mit linkem Bezug und kurzem Drehsinn: vollständige Folge
  20,155s, q6-Anfahrt−12,512°, Stiftziel gegenüber ursprünglichem Anfangsfit
  Δ≈[−40,118,−4,348,+3,187]mm. Ausgangspunkt ist der archivierte damalige
  Zustand; für reale Ausführung sind frisches Bild/Gelenke und neue Reviews
  erforderlich. Kein fertiger Fahrbefehl vom aktuellen Zustand abgeleitet.
- `execute_pen_grasp.py`: meldet vorhandener Schließresultat keinen
  Objektkontakt, endet die Aufgabe mit `NO_OBJECT_CONTACT` vor dem Hub.
  Keine zusätzliche Geräteabfrage, kein Kraft-/Greiferwächter und keine
  Stoppkaskade; nur endliche Aufgabenentscheidung aus vorhandenem Ergebnis.
-23 gezielte Stifttests bestanden, einschließlich tatsächlichem synthetischem
  linken Boardbild,4-cm-Widerspruch zur rechten Sitzung, fehlendem linken
  Board ohne Rückfall, Symmetrieauswahl und leerem Schließen ohne Hub.

## Nachweise / offene Fortsetzung

`setup/tasks/pen-debug-20261125/`:
`offset-analysis.json`, `entry-projection-crop.jpg`,
`reference-comparison-two-days.json`, `offset-current-workflow-and-gripper.txt`,
`offset-authorized-pause.txt`, `offset-pause-confirmed.json`,
`symmetry-offline-old-reference/`, `left-reference-offline-candidate/`,
`left-reference-offline-final/`, `left-reference-regression.log`.

Keine neue reale Stiftfahrt. Offene Reihenfolge: Boardbestätigung zuordnen,
gegebenenfalls Aufgabenreferenz aktivieren, frische komplette Planung vom
wirklichen aktuellen Zustand und getrennte normale Bewegungs-/Kontaktreviews.
Kein Resume aus der Diagnose ableiten.

## Board bestätigt, Aufgabenreferenz aktiviert

Nutzer bestätigt25.11. ausdrücklich, dass das linke Board weder bewegt noch
verändert wurde, und beauftragt die Fortsetzung. Damit ist die oben offene
physische Voraussetzung erfüllt. Aktive Definition `pen-left-rear-v1.json`
auf `reference_board=left` umgestellt, Bestätigungsprovenienz dort und in
AGENTS festgehalten. Keine gemeinsame rechte Kamera-/Basisbindung geändert.
Vorherige Abschnitte beschreiben den vorbereiteten Zustand vor dieser Antwort.
Nächster Versuch mit neuen Bildern, tatsächlichem Gelenkstart und den
normalen Motion-/Kontaktreviews; archivierten20,155-s-Entwurf nicht ausführen.

Nach Aktivierung erneut23 Stifttests bestanden
(`activated-left-reference-regression.log`). Gemeinsame Library zunächst
belegt durch Kartonlauf `1adaf627563c4e259db7f2352923bfb9`; unberührt gelassen.
Dieser endete vor seiner Fahrt ohne geprüften Hochanfahrweg. Danach neuer
Stiftlauf `52befffcfa974f6390b4658d081ae7d4` über aktiven Port45937 gestartet,
25.11.,16:23:41AWST. Er liest neue Gelenke und nimmt ein neues Stiftbild auf;
kein Archivplan wird gefahren. Vor Start bestätigt: PAUSED/OPERATOR PAUSE,
keine aktiven Arm-Actions und keine gemeldeten Kollisionen. Weitere Schritte
und aktuelle Reviews dieses Laufs verfolgen; keinen zweiten Lauf parallel
starten. Freigabe/Resume werden nicht aus der Boardbestätigung abgeleitet.

Neues Anfangsbild unabhängig angesehen: Stift weiterhin im Halter, Marker
sichtbar. Aktueller linker Boardfit17Marker/0,719805px Prüf-RMS; Penfit
1,592902px. Ganze neue Folge geprüft: Anfahrt2,300266s, Einfahrt8,033682s,
Lift8,033682s, insgesamt18,367631s. q6-Anfahrt vom wirklichen aktuellen
Start nur−7,029°. Controllerpolynomspitzen innerhalb0,1rad/s und0,2rad/s²,
neuer Ausführungshelfer einschließlich `NO_OBJECT_CONTACT` im übertragenen
SHA-Manifest bestätigt. Nachweis `current-left-reference-plan-validation.json`.

Seit16:24:18AWST Review `b0d81aa4580b48b0b8cc4a38e6e1ce1a` ausstehend.
Nutzer ausdrücklich um zunächst nur Anfahrt/Einfahrt plus RESUME gebeten;
Kontakt erst nach Prüfung des neuen tatsächlichen Einfahrbildes. Keine
Agentenentscheidung für diesen neuen hochriskanten Kontakt, keine Änderung
des Aufgabenvertrauens.
