# Stiftprogramm: Abbruch bei Greifervorbereitung

- Status: Diagnose25.11.2026 fortgesetzt, N100 wieder erreichbar;
  verbesserte Fehlerdiagnose installiert, freigegebener Greifertest bestanden;
  ursprünglicher Abbruch nicht reproduziert.
- Nutzer meldet nach erfolgreichem Bewegungsbeginn ein Problem. Lauf
  `7d8b308369e34fd28f14c7b31bca49d7`, Start19:08:30AWST, Freigabe19:10:30,
  Abbruch19:11:19 beim left_rear-Öffnen vor Einfahrt. Vorposition COMPLETE,
  keine Einfahrt, kein Schließen/Ausheben dieses Stiftlaufs.
- Lesen zuerst: neuester Export18:23AWST, danach aktueller Minimalstatus und
  Greiferstatus überN100. Bestehende Karton-/Wiege-Diffs erhalten.
- Drei GET-Statusabfragen vom24.11.: ACT1/STA3/FLT0/OBJ0/POS3/PRE0, aberFOR255/SPE255,
  trotz angeforderterFOR0/SPE16. Keine neue Öffnung/Reset/Setparameter gesendet.
  Timeout liegt damit wahrscheinlich schon in der Parameterbestätigung.
- Schutzstatus am24.11. nach dem Fehler RUNNING, keine Kollision/Warnung, keine aktive Arm-Action;
  vorhandene40mm-Marge getrennt. Schutzprogramm wird nicht geändert.
- Diagnoseartefakte: `setup/tasks/pen-debug-20261124/`. Fehlzeitfenster,
  tatsächliche Bewegung und verfügbare Messwerte von Grenzwerten unterscheiden.

## Auswertung25.11.

- Neuer lesender Safety-Bericht vom24.11.,19:14:43AWST ausgewertet:
  Reviewstore meldet den Greiferfehler19:11:12,066; Library-Fortschritt meldet
  Fehler19:11:19,798. Quellen getrennt; kein passender Kollisionsauslöser im
  Bericht. Minimaljournal war nicht zugänglich, daher keine vollständige
  historische Entwarnung behaupten. Der alte Export18:23 deckt den Vorfall
  nicht ab. Tatsächlich gemessene Geschwindigkeit beim Abbruch nicht vorhanden.
- Transport sendet und bestätigtFOR vorSPE, dann erstPOS/GTO. Dauerhaftes
  FOR255/SPE255 spricht für die erste Parameterbestätigung; mangels damaliger
  Action-Register bleibt die genaue fehlgeschlagene Unterphase eine Ableitung.
  Fehlermeldung enthält bisher nur einen generischen Timeout.
- Historische Gegenprobe17.11.: `left_rear-gripper-open.json` zeigt nach
  erfolgreichem Öffnen weiterhinFOR255/SPE255. Die damalige POS-/OBJ-
  Erfolgsmeldung allein belegt keine Parameterübernahme. Der korrigierte
  heutige Transport lässt POS/GTO erst nach Parameterbestätigung zu. Diesen
  Nachweis nicht umgehen oder Kraft-/Geschwindigkeitsvorgaben erhöhen.

## Lokale Korrektur der Fehlerdiagnose

- `execute_pen_grasp.py` protokolliert Aktivieren/Öffnen/Schließen getrennt,
  hält vorhandene Action-Rückmeldungen nur als letzten Wert im Speicher und
  schreibt an Aktionsgrenzen das Ergebnis. Fehlerphase z.B.
  `GRIPPER_OPEN_FAILED` statt unverändertem `PREPARED`. Keine zusätzlichen
  Geräteabfragen, automatische Wiederholung oder Bewegungsänderung.
- `robotiq_gripper.py` ergänzt im vorhandenen Timeout Schritt, Soll und
  zuletzt beobachtete Register. Bestätigungsbedingungen, Befehlsreihenfolge,
  Fristen und Pollabstand unverändert. Kein Eingriff ins Sicherheitsprogramm.
- Offline-Nachweis:30 Tests aus `test_robotiq_gripper.py` und
  `test_pen_program.py` bestanden, darunter nicht bestätigte Kraft/Tempo
  ohne POS/GTO sowie Aktivierungs-/Öffnungs-/Schließfehler ohne Folgebewegung.

## Unterbrechung und wiederhergestellter Zugang

- N100 am25.11. unter192.168.8.5 nicht erreichbar, mDNS-Name ebenfalls nicht
  auflösbar. Lesender Archivabruf scheiterte; keine lokalen Quelländerungen
  auf den Steuerhost übertragen, keine Dienste neu gestartet. Nutzer nach
  Strom-/Netzstatus gefragt; nicht als neue Bewegungsfreigabe behandeln.
- Herstellerbackup liegt aufN100:
  `/mnt/Daten1/UWA-Archiv/ROSmini-2026-11-18/originale/home/rosmatch/UWA_ws/setup/backups/robotiq-usb/20261111-before-ucc-update/files/Robotiq_Grippers-1.8.6.7016.urcap`.
  SHA256laut Archivmanifest:
  `e6bcab71e0bec83fa02a1ae177b4fd1f5680b164a805af0b96560e20b04d70da`.
  Sobald erreichbar zuerst Quellprotokoll/aktiven Greiferprozess und frische
  GET-Register prüfen. Keine vermutete Transportkorrektur ohne Nachweis und
  keine Parameterbestätigung durch ACK oder bloßes POS3 ersetzen.
- Ein erfolgreicher realer Stiftgriff und die eigentliche Ursache der
  fehlgeschlagenen Parameterübernahme bleiben offen.

## Erneute Fortsetzung25.11., ab15:04AWST

Nutzer meldet N100 bald wieder erreichbar und beauftragt Fortsetzung. SSH
192.168.8.5 wieder erfolgreich. Hersteller-URCap gezielt zurückgeholt;
SHA256 stimmt mit Archivmanifest überein. Kommunikationsskripte und
`drivergripper` lokal statisch gelesen. GETVER bestätigtDCU-2.0.0,
GETSID `[9]`. Servergetter FOR/SPE liefern angeforderte, serverseitige Werte;
kein Kraftsensor-/physischer Parametrierungsnachweis daraus ableiten.

Frischer left_rear-Status: ACT0/STA0/FLT0/OBJ0/POS3/PRE0/GTO0/FOR255/SPE255.
Zwei getrennte endliche Parameterproben, ohne Aktivierung oder Positionsziel:

1. Bei bestätigtem inaktivem Zustand einmal `SET FOR 0`; drei folgende
   Abfragen bestätigenFOR0, SPE255, ACT0/STA0/POS3/PRE0 unverändert.
2. Nach bestätigtemFOR0 und erneutem ACT0/STA0/GTO0 einmal `SET SPE 16`;
   drei folgende Abfragen bestätigenFOR0/SPE16, weitere Register unverändert.

Dies reproduziert den gestrigen Fehler nicht. Kein wiederholter Öffnungs-
oder Aktivierungsauftrag. Native Lesebefehle ergeben POWER_OFF,
SafetystatusNORMAL, Programmrunningfalse, geladen `/programs/<unnamed>.urp`.
Keine Power-/Brake-/Load-/Play-Aktion ausgeführt. Die Serverparametrierung
allein belegt bei diesem Betriebszustand keine Hardwareöffnung.

Aktueller Schutzstatus getrennt vom gestrigen Vorfall: PAUSED/COLLISION,
zwölf gemeldete Kontakte zwischen left_front-Handgelenk/Greifer/Kamera und
right_table_plate. `collision_data_available=false`, right_front nicht
verfügbar. Diese Pause unverändert gelassen; keine Fortsetzung oder
Kollisionsfreigabe abgeleitet. Kein neuer Armfahrbefehl.

## Installation der Diagnoseergänzung25.11.

- Erweiterte Offline-Regression:55 Tests bestanden (Stift, Robotiq,
  Gripper-API und nominale Einheiten). Keine Hardwarekontakte durch Tests.
- Laufender Transportpfad tatsächlich root-Runtime, kein separater
  Minimal-Safety-Kern: `~/uwa-ur-runtime/src/multi_arm_manipulation_UWA/uwa_cell_tasks/uwa_cell_tasks/robotiq_gripper.py`.
  Alte Datei seit19.11., Dienststart23.11.; Quelländerung nach Import als
  Erklärung damit nicht belegt. Vorheriger SHA256
  `da90e9945ef0204efdc2218c8aaea9662a6da9ecb80384b64c1bbbb22f483186`.
- Nur Timeout-Details atomar installiert, Rücksicherung
  `~/uwa-ur-runtime/setup/tasks/pen-debug-20261125/robotiq_gripper.previous.py`.
  Neuer SHA256 `b4edec5680b891c45e89d710f2510a9885af6c7ebcc79931d3c4a921b74a0534`.
  Keine geänderte Reihenfolge, Bedingung, Frist oder Pollrate.
- Alle vier ROS-Adapter unmittelbar vorher unbeschäftigt. Ausschließlich
  `uwa-grippers.service` neu geladen; Invocation
  `b9a65565d3b64b6782f7eaf663ea9447`, MainPID3829309.
  Danach alle neun Statusregister aller vier Greifer genau unverändert.
  Aktivierungs-/Bewegungs-/Schutzdienste nicht gestartet oder umgestellt.
- Neuer Stift-Ausführungshelfer liegt lokal und als separate Diagnosekopie
  aufN100. Nächster regulärer Library-Lauf transferiert ihn hashgebunden;
  den alten Lauf nicht verändert oder erneut gestartet.
- Nachweise: `setup/tasks/pen-debug-20261125/` einschließlich
  `force-zero-probe.json`, `speed-16-probe.json`, `installation.json`,
  `pre-install-status.json`, `post-reload-status.txt`,
  `left-rear-native-readonly.json`, `final-protection.json`,
  `offline-regression.log`.

Anschließend Nutzerfreigabe für einen einzelnen left_rear-Aktivierungs-/
Öffnungstest ohne Armfahrt angefragt und auf Bereitschaft gewartet; Ergebnis
im folgenden Abschnitt. Keine Beseitigung des ursprünglichen Fehlers oder
realen Stiftgriff allein aus der Diagnoseinstallation behaupten.

## Freigegebener einzelner Greifertest,25.11.,15:18AWST

Nutzer bestätigt „erledigt“ auf Bitte um Betriebsbereitschaft und Freigabe des
einzelnen Aktivierungs-/Öffnungstests. Native Vorabfrage RUNNING/NORMAL,
Programmrunningtrue, geladen `/programs/ros.urp`. Schutzstatus weiterhin
pausiert; zu diesem Zeitpunkt keine aktuellen Kontakte, right_front-Daten
noch nicht verfügbar. Keine Armfahrt oder Pausenänderung angefordert.

Test läuft genau einmal über `GripperClient("left_rear")`, kein direkter
zusätzlicher Aktortransport. Ergebnis15:18:51,172–15:18:54,649AWST:

- Vorher ACT0/STA0/FLT0/OBJ0/POS3/PRE0, FOR255/SPE255. Die früher im
  POWER_OFF-Zustand serverseitig gesetzten Werte waren also bei diesem
  erneuten Bereitschaftszustand nicht mehr vorhanden.
- Einmal `activate()`: erfolgreich, ACT1/STA3/FLT0/POS165/COU13; FOR255/SPE255.
 38 vorhandene Aktivierungsrückmeldungen gespeichert.
- Einmal `open(force_raw=0,speed_raw=16)`: erfolgreich. Erste Rückmeldung
  zeigtFOR0 bei nochSPE255; folgende bestätigenSPE16 und schließlich
  ACT1/STA3/FLT0/OBJ3/POS3/PRE0/SPE16/FOR0/COU0.15 Öffnungsrückmeldungen.
- Gesamtergebnis `success=true`, `OPEN_COMPLETED`. Bei einem Fehler wäre
  kein weiterer Aufruf erfolgt. Keine automatische Wiederholung, kein
  Schließauftrag, kein Stiftgriff/Hub und keine Armfahr-/Power-/Brake-/
  Load-/Play-/Resume-Befehle durch diese Diagnose.

Aktueller Abschluss: Greifer aktiviert und vollständig offen laut
Registerabschluss. Schutzstatus danach PAUSED/OPERATOR PAUSE, vollständige
Kollisionsdaten und keine aktuellen Kontakte. Pausenursache änderte sich
zwischen den Statusabfragen ohne einen Pausen-/Resumeaufruf dieses Tests;
keine unveränderte historische Kollisionsursache behaupten.

Nachweise `authorized-gripper-test.json` (lokal und N100),
`pre-test-native-and-protection.txt`, `post-test-protection.json` im
Diagnoseordner25.11. Der ursprüngliche Timeout wurde mit demselben regulären
API-Pfad nicht reproduziert. Keine spekulative Änderung der Befehlsfolge,
Fristen oder Parameterbestätigung umgesetzt. Diagnoseänderung ist geladen;
eine dauerhafte Ursachenbehebung ist damit nicht bewiesen. Der nächste
vollständige Stiftlauf benötigt wie bisher aktuelle Wahrnehmung/Planung
und normale Motion-/Kontaktfreigaben; kein automatisches Wiederanlaufen.

## Neuer vollständiger Stiftlauf,25.11.2026

Nutzer beauftragt ausdrücklich, das Stiftgreifen von vorne erneut zu probieren.
Aktiver GUI-Library-Endpunkt Port45937, PID50424, Backendminimal und explizit
`minimal.upWhPwQC` über Prozessumgebung bestätigt. Kein Oberflächenzugriff
verfügbar; normale Library-HTTP-Schnittstelle verwendet, keine GUI-Klicks
behauptet. USB-Referenz frisch vom25.11.,15:19:52AWST,12h gültig.

Erster neuer Lauf `707e121e75a444b286eb9c4a04f5c931`,15:23:21AWST, registriert
und vollständig geplant. Währenddessen änderte sich Arbeitsbereichssitzung
von `f6b9a18fe25a4f108420b9a5ce30df1a` zu
`465bb4cc216643a6a8f116b63ad4bf61`. Ausführungshelfer lehnt vor Review und
Gerätebefehlen ab. Kein Greiferfehler, keine ausgeführte Teilbahn. Der Runner
meldete zunächst irreführend fehlendes `execution/workflow.json`, weil der
leere Ausgabepfad existierte. Fehlerrückmeldung korrigiert, sodass die letzte
eigentliche N100-Exception erhalten bleibt; keine Änderung an Freigabeprüfung
oder Ausführung.20 Stift-Regressionstests einschließlich dieses Falls bestanden.

Vollständig neuer zweiter Lauf `a49718ebcac64a849d218afb8c618704`,
Start15:25:24AWST, mit neuer Aufnahme und aktueller Sitzung. OpenCV beide
Marker ohne Gemini-Fallback, RMS1,55583px. Vollständige Bahnprüfung bestanden,
73,13194s gesamt; genehmigte0,1rad/s und83,33mm/s TCP unverändert.
Anfangsfoto unabhängig angesehen: Stift im grünen Halter, beide Marker
sichtbar. Ganze Folge vor der Anfahrt vorhanden und geprüft.

Ab15:26:21 wartet normaler Review `743ee5361d9944d79515d9d588c19246` für
Anfahrt/Einfahrt. Aufgabenvertrauen0, Arbeitsbereich freigegeben. Keine
Agentenfreigabe gesetzt. Nutzer um Prüfung/Freigabe im Motion review und
ausdrückliches RESUME der bestehenden Bedienerpause gebeten. Fortsetzung
dieses laufenden Prozesses nach normalen UI-Entscheidungen beobachten;
keinen weiteren Lauf parallel starten.
