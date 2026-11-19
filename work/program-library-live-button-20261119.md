# Live-Starttaste der Programmbibliothek, 19.11.2026

- Status: abgeschlossen, Australia/Perth. Nutzer meldet deaktivierten Webstart und
  fragt nach der Bedeutung von Play am UR.
- Der tatsächlich verwendete lokale Server auf Port 8780 wurde ohne
  `--live-config` gestartet. Sein Katalog meldet `live_available:false`
  trotz vorhandener Optikkonfiguration. Der einzige gespeicherte Lauf ist
  eine beendete Demo.
- Den eigenen Bibliotheksserver bei freier Laufsperre mit Optikdatei auf
  demselben Port starten und per Katalogabfrage prüfen. UWA Robot Power
  und den N100 für diese Webkorrektur in Betrieb lassen.
- Der Server auf `127.0.0.1:8780` wurde mit Optikkonfiguration als transiente
  Benutzereinheit `uwa-program-library.service` neu gestartet. Katalog meldet
  Live-Start verfügbar. Der Standalone-Befehl in der Bedienanleitung enthält
  jetzt `--live-config`. Nur HTTP GET geprüft, kein Kartonlauf ausgelöst.
  Der Browserzugriff war nicht verfügbar. Nachweis
  `setup/tasks/uwa_program_library_live_button_20261119/verified.json`.
