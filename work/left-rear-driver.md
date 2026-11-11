# Left rear in UWA-GUI und realen ROS-Treiber testen

- Status: **GUI/Treiber erfolgreich; wartet auf Pendantkonfiguration für Programmtest**,2026-11-11.
- Nutzer beauftragt Aufnahme in GUI und echten Treiber-/Starttest links hinten
 192.168.8.169. Keine Fahrziele für diesen Verbindungstest. Prepare/Programmstart
  werden als getrennte Schritte getestet, native UR-Sicherheit erhalten.
- Bestehende Hardware-GUI18120 besitzt rechte Treiber18238/18239. Diese nicht
  schließen/neustarten. Aktuelle Front-Kalibrierarbeit abgeschlossen; deren
  Halteregler/Logs erhalten. Inventar enthält left_rear bereits.
- Vor Treiberstart eigene Werkskinematik auslesen, individuelle Ports52001–52004,
  HardwareDomain66. Bewegungskontroller ausschließlich inaktiv laden.
- External-Control-Host192.168.8.209/Port52002 und Remote am Pendant erfragt.
- Bereiche: gezielte Inventar-/GUI-/Anleitungsänderungen falls nötig, eigene
  Prüfskripte/Logs, HANDOVER/README/AGENTS. Keine Simulation zurücksetzen.
- Eigene Werkskinematik ausgelesen, Inventarpfad hinterlegt. Echte GUI mit
  links hinten geöffnet;2592 Samples/sechs endliche Winkel/493,94Hz. Fünf
  Broadcaster aktiv, vier Bewegungscontroller inaktiv. GUI-Gelenklesen und
  Prepare UR erfolgreich; Prepare bei bereitsRUNNING, kein Kaltstarttest.
- Stand Local/STOPPED ros.urp; Remote/Host192.168.8.209/Port52002 beim Nutzer
  erfragt. Kein Fahrziel, keine Motioncontrolleraktivierung. Neues Fenster/
  linker Treiber bleiben offen; bestehende rechte Besitzer-GUI/Treiber erhalten.
- Eigene Nachweise setup/logs/uwa-left-rear-driver/, Factorylog
  setup/logs/uwa-left-rear-factory-kinematics.log. Anleitung/HANDOVER/README
  im selben Arbeitsgang aktualisiert. Programmstart/link ist noch nicht belegt.
