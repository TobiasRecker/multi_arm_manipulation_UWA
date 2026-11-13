# OAK-Verbindung stabilisieren

- Status: **abgeschlossen – OS1.47 installiert, Nachprüfung bestanden**, 2026-11-13, Hauptagent OAK/Scan.
- Nutzerentscheidung: zuerst OAK-Verbindung stabilisieren; **keine weiteren
  Armbewegungen**. Vierarm-Scan bleibt nach erster Anfahrt angehalten.
- Bereiche: OAK-Fotodienst/SDK-Worker, Netzwerk-/Geräte-/Prozessdiagnose,
  OAK- und Zell-HANDOVER, Fotodienst-Anleitung und passende Tests.
- Zuerst konkurrierende Clients, Link-/Paketfehler und SDK-Crashlogs prüfen.
  Keine pauschalen Prozesskills, kein ungefragter Flash/Reset, keine Arm-/
  Controller-/Bremsen-/Programmaktion. Fremde Simulation erhalten.
- Diagnose-/Testdaten unter setup/oak4/stability_20261113/; private Bilder nicht Git.

- Nutzer bestätigt eigenen OAK-Neustart unmittelbar vor Diagnose. Danach9native
 8K-Aufnahmen bestanden:4Baseline,2vollständige stationäreFünfkamera-Sätze und
 3neuerCLI-Check. KeinSDK-/OS-Wechsel, kein eigenerGeräte-Reset.
- NeuerAufruf: oak4_photo.sh check --count3 --focus116 (Optionen mitLeerzeichen).
 17gezielteTestsPASS, Werkskalibrierung exaktzurSicherungvom12.11. identisch.
- Diagnose: Crashdump meldetDiscovery-Bindfehler undinternbelegteRGB-Ressource;
  zurückgebliebenerSDK-Kontext plausibel, genaueUrsache weiterunbewiesen.
  KameraneustartdurchNutzer hataktuellenFehlerzustandgelöst; keineDauerfreigabe.
- NeuesteNutzeranweisung erlaubtFortsetzung desScans beiOAK-PASS. Nachweis/
  Wiederaufnahme wiederin work/four-arm-object-scan-run.md; frischerCheckläuft.

- NachweiterenFotos erneutSDK-Pipeline-Startfehler. NeunbestandeneAufnahmen
  warenZwischenstand,nichtdauerhafteFehlerbehebung. SDK3.11-Vergleichkonnte
  keineVerbindungherstellen; keinProduktivwechsel.
- OS1.47-OTA vollständigheruntergeladen, HerstellerMD5korrekt undZIPlesbar.
  update_plan.json/verified_update.jsonuntersetup/oak4/stability_20261113/ota/.
  Kalibrierungsbackupvorhanden, keinUpdatebisherausgeführt. Freigabefür
  dauerhafteOS-Änderung+Neustart anfragen; keineArmkommandosdafür.

- Nutzer bestätigt die angebotene dauerhafte Aktualisierung OS1.32.1→1.47.0
  ausdrücklich mit „ja bitte“. Lokale Paket-/Identitäts-/Sitzungsprüfung vor
  Installation, danach Factoryvergleich und native Fotos. Keine Armaktionen.

- Autorisiertes OTA erfolgreich: gleicheKamera1479883285, OS1.47.0/Agent0.28.0,
  UpdaterExit0. Werkskalibrierungvor/nachherexaktidentisch (SHAa07141cc...).
  Nachprüfung mit15nativenStartzyklen läuft; nochkeineabschließendeFreigabe.

- Autorisiertes OTA erfolgreich abgeschlossen und nachgeprüft: identische
  Werkskalibrierung,15native8K-Startzyklen plus vollständigerFünfkamera-SatzPASS.
 16OAK-Aufnahmen nachUpdate ohneFehler. KeineRobotermotion/Programmstarts.
- Vollständiger25-Bilder-Index scan_dataset.json erstellt und Bildhashes,
  Größen, Sollposen/Stillstand geprüft. UpdateplanstatusCOMPLETE mit
  update_validation.json. AlleArme stehen, Fahrcontrollerinaktiv.
