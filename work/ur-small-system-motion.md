# Bewegungsaktivierung für einen oder zwei Arme

- Status: **abgeschlossen**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzerauftrag: Hardware-Bewegungsaktivierung für ein/zwei Arme ermöglichen;
  zunächst ausschließlich `right_rear`, aktuelle GUI zum eigenen Treibertest öffnen.
- Bereiche: MATCH-Adapter/Tests, UWA-GUI/Tests/Bedienung/AGENTS/HANDOVER.
- Prüfungen ausschließlich Mock/offline; keine realen Bewegungsziele, Power,
  Brake oder Play durch den Agenten. Alte eigene GUI vor neuer Instanz prüfen;
  keine Simulationen/nebenläufigen Hardwaretreiber stoppen.
- Ergebnis: Trajektorien/Admittanz für ein/zwei Hardwarearme aktivierbar,
  bekannte schon aktive Arme mitzählen; Drittarm und Drei-/Vierarmauswahl
  abgelehnt. Aktivierungslock, Dashboard-NORMAL/Remote/RUNNING/korrektes Programm
  PLAYING als Voraussetzungen. Kein automatischer Programm-/Bewegungsstart.
- Native reale Trajektorien mit skaliertem UR-Controller; rqt danach verfügbar.
  Standardauswahl nur `right_rear`; CLI-Modus und Startmenü-Aktion Hardware hinten
  rechts ergänzt. Kollisionsvermeidung weiterhin deaktiviert, kein Zellenschutz.
- 16 Offline-Tests, Zwei-Paket-Build, Live-Mock-Test einschließlich Hardware-
  Aktivierungspfad mit lokal ersetztem Dashboard bestanden: ein/zwei aktiviert,
  dritter abgelehnt, anschließend vier Mock-Admittanzcontroller/Stopp/Abbau.
  Logs `setup/logs/uwa-control-small-system-*`, JSON unter `setup/logs/uwa-control/`.
- Installierten Desktop-Eintrag validiert, dessen Hardware-Aktion gestartet;
  Prozess mit `--mode hardware --arms right_rear` und X11-Fenster bestätigt.
  Vorherige eigene GUI ohne laufende Treiber geschlossen. Aktuelle GUI offen,
  keine echten Treiber/Power/Brake/Play/Ziele durch den Agenten gestartet.
- AGENTS/HANDOVER/README/Bedienung in beiden betroffenen Repos aktualisiert.
