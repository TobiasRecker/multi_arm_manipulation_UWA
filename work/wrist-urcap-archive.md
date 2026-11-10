# Lokale URCap-Analyse UCC1.11.3

- Status: **abgeschlossen**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzer stellt `~/Downloads/UCC-1.11.3_20210913.zip` bereit und bittet um
  lokale Fokus-/Schnittstellenanalyse ohne unbekanntes Controller-Adminpasswort.
- Umfang: Archiv unverändert lesen, ausgewählte Dateien nach Workspace-setup
  extrahieren, Skripte/Java-Bytecode statisch untersuchen. Keine enthaltenen
  Installer/Programme starten, keine Controller-/Kameraänderungen ausführen.
- Bereiche: lokale Analyseartefakte unter `setup/logs/wrist-urcap-2026-11-10/`,
  eigene Ergebnisnotiz und HANDOVER/Hardwareanleitung. Paralleles UR-Jogging erhalten.
- SSH-Schlüsselimport benötigt normalerweise entsperrte Security-Einstellungen;
  kein Ersatz für unbekanntes Adminpasswort. Keine Zugangsdaten suchen/umgehen.
- Ergebnis: verschachtelten Java-Client mit javap statisch gelesen, konkrete
  POST-Kamera-/Fokusschnittstelle und invertierten0…1023-Regler rekonstruiert.
  GET-Einstellungen/Details am right_rear tatsächlichHTTP200/succeeded, ohneSSH.
  Keine Schreibtests oder enthaltenen Programme ausgeführt. Bericht
  `docs/wrist_urcap_analysis_2026-11-10.md`; Anleitung/README/HANDOVER aktualisiert.
