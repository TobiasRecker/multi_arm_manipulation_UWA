# Minimalbetrieb: realer Betriebswechsel und Funktionsprüfung

- Status: in Arbeit, 24.11.2026, Australia/Perth; Hauptagent dieses Chats.
- Nutzer beauftragt ausdrücklich den realen Betriebswechsel und die
  Funktionsprüfung des gebauten Minimalbetriebs.
- Geplante Dienständerungen ausschließlich auf N100: alten
  `uwa-hardware-motion.service` zuerst beenden, danach vier Treiber geordnet
  ersetzen; separaten C++-Schutzdienst ohne Watchdog/ExecStopPost starten.
  Der alte ExecStopPost sendet beim Beenden einmalig nativen Programm-STOP.
- Kandidat: `/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
  Dienstdefinitionen, Safety Log und Quellenbindung vor Änderung sichern.
- Vorbefund: alle vier URs RUNNING/Safety NORMAL, `ros.urp` STOPPED;
  alte Wächter aktiv. Reviewstore enthält Arbeitsbereichsfreigabe.
- Prüfung: zwei kleine, vorab vollständig geometrisch geprüfte gemeinsame
  Vierarm-Handgelenkfahrten, Software-Pause und ausdrückliches Resume unter
  Erhalt derselben Goals. Bestehende0,1rad/s-/0,2rad/s²-Planungsgrenzen.
  Keine Greiferaktionen, Kollisionen oder absichtlich erzeugten Datenfehler.
- Telemetrie dient ausschließlich dieser beauftragten Funktionsmessung;
  keine zusätzlichen Laufzeitwächter installieren.
- Bedienung: sichtbare Minimal-GUI und dauerhafte Launcherbindung; tatsächliche
  GUI-Klicks über vorhandene Accessibility-Schnittstelle bevorzugt.
- Nachweise: `setup/tasks/minimal-cutover-20261124/` im Workspace,
  auf N100 Kandidat `validation/`.
