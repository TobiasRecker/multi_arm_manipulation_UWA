# Erster realer Scan mit vier parallelen Armen

- Status: **Software vorbereitet, wartet auf physische Roboternetzverbindung**, 2026-11-12, Hauptagent Digitalisierung.
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
