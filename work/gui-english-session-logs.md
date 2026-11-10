# English UR GUI and Save logs

- Status: **abgeschlossen**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzerauftrag: UWA-UR-GUI ins Englische übersetzen; Button Save logs exportiert
  aktuelle Sitzungslogs für spätere Diagnose.
- Bereiche: UWA-GUI/Logging/Tests/Desktop-Eintrag/Bedienung; englische Antworten
  eigener MATCH-Adapter-Operationen. Bestehende Diffs und laufende Treiber erhalten.
- Keine Hardwarebefehle, Treiber-/Simulationsneustarts oder neue Safety-Gates.
  Installierten Desktop-Eintrag testen, nur zusätzliche GUI öffnen falls nötig.
- Ergebnis: englische UR-GUI inkl. Tooltips/eigener Meldungen/Adapterantworten
  und Startmenü UWA Arms. Save logs bleibt während Operationen erreichbar;
  eindeutige Sitzungslogs, ungekürzte Prozessausgaben inkl. Status/Exitcodes,
  Hintergrundexport als tar.gz mit Manifest/Status/Profilen/Screenshot/ROS-Logs.
- Archivpfade setup/logs/uwa-control/exports/, neuester abgeschlossener Export
  via latest-export.txt, Sitzungen unter sessions/. Alter übernommener
  Treiberkontext ausdrücklich separat bezeichnet. Kein Upload/Roboterbefehl.
- 16 Offline-Tests, Zwei-Paket-Build und isolierter Live-Mock-Test bestanden:
  Save logs mit vier aktiven Mock-Controllern geprüft, ROS/Prozessdateien und
  Statusmanifest inspiziert, anschließend Stopp und Prozessabbau bestätigt.
  Logs setup/logs/uwa-english-log-{tests,build,live}.log; Archivpfad im JSON
  setup/logs/uwa-control/mock-gui-validation.json. Screenshot daneben geprüft.
- Installierten englischen Desktop-Eintrag validiert/gestartet. Nur treiberloses
  altes Fenster65911 geschlossen; Besitzer41062 mit Hardware-Launches41338/
  41339 beibehalten. Neue englische Hardware-GUI93931 geöffnet, nur rear right
  ausgewählt. Keine realen Power/Brake/Play/Ziele ausgeführt.
- README/Bedienung/AGENTS/HANDOVER parallel gepflegt; Gespräch bleibt Deutsch.
