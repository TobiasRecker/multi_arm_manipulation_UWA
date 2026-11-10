# Lokale Vierarm-Vorbereitung und UWA-GUI

- Agent/Aufgabe: Codex, `uwa-ur-gui`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-10, Australia/Perth.
- Auftrag: vorhandene UR-Start-/Bereitstellungs-/Admittanz-/Kollisionsbausteine
  im MATCH-Repo erhalten und für UWA referenzieren; schlankere eigene GUI mit
  vier Armauswahlen oben links, ohne SSH/rsync/mobile Roboter/Infrastruktur.
- Bereiche: neues generisches UR-Paket im MATCH-Repo, neue UWA-Bringup-/GUI-
  Pakete, Inventarergänzung, Tests/Bedienung/Handover. Bestehende Diffs erhalten.
- Umsetzung wird mit Mock-Hardware und Tests geprüft. Keine echten Treiber
  oder automatische Power-/Brake-/Programm-/Bewegungsbefehle in dieser Arbeit.
- Gefunden: `mur_control/IntegratedCartesianAdmittanceController`, J-PARSE,
  `collision_response.hpp`, `ur_startup_enable.py`, MuR-GUI-Helfer.
  MuR-Launch startet standardmäßig automatisch; Collision prüft einen Gegenarm.
  Diese Einschränkungen nicht als fertigen Vierarm-Kollisionsschutz ausgeben.
- Ergebnis: gemeinsamer lokaler Adapter `match_ur_hardware`, UWA-Paket
  `uwa_cell_control`, Inventar/Ports/Programmzuordnung und Startmenü-App
  **UWA Arme** umgesetzt. Mock-Standard, Domain 66, keine SSH-/rsync-Funktionen.
  Treiberstart und explizite Power/Brake/Play-Schritte getrennt; echte
  Bewegungsaktivierung bis zur vollständigen Szenenintegration gesperrt.
- Prüfnachweise: zwei Pakete gebaut; zehn Offline-Tests; Live-GUI-Mock-Test
  mit 24 eindeutigen endlichen Gelenken, vier aktivierten Admittanz-Plugins,
  GUI-Stopp aller Bewegungscontroller und sauberem eigenen Treiberabbau.
  `setup/logs/uwa-control/mock-gui-validation.json`, Screenshot daneben.
- Installierten Desktop-Eintrag validiert und via `gtk-launch uwa-control`
  gestartet, X11-Fenster registriert. VS-Code-Snap-GTK-Pfade werden im Starter
  entfernt; GUI im Mock-Modus zur Ansicht offen, keine Mock-Treiber mehr aktiv.
- Keine realen Treiber, Power-/Brake-/Play-/Bewegungsbefehle ausgeführt.
  Anleitung/Architektur/Grenzen in `docs/ur_control_gui.md`, Ergebnisse in
  HANDOVER und dauerhafte Nutzerwünsche in AGENTS übernommen.
