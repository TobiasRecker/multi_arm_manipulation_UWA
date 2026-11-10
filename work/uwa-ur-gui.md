# Lokale Vierarm-Vorbereitung und UWA-GUI

- Agent/Aufgabe: Codex, `uwa-ur-gui`.
- Status: **aktiv**.
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
