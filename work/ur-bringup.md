# Gemeinsame Vorbereitung der vier UR-Steuerungen

- Status: **abgeschlossen**, 2026-11-16 (Australia/Perth), Codex.
- Auftrag: Roboterzustand abfragen, explizite Vorbereitung für ROS und
  konkrete Bedienerschritte am Pendant melden.
- Bereiche: eigener CLI-Startpfad, Hardwareinventar und Agenten-Dokumentation.
  Keine Dienstneustarts; Tests mit simuliertem Dashboard und ggf. lesender Live-Abfrage.

- CLI und Bedienerhinweise umgesetzt; Einstieg in AGENTS/README/HANDOVER.
- Erster Versuch ohne Ethernet-Link, keine Schreibbefehle. Nach
  Wiederherstellung des Links am 16.11. real ausgeführt: Treiber gestartet,
  hinten links und rechts eingeschaltet und Bremsen gelöst; alle vier
  External-Control-Programme gestartet und Reverse-Verbindungen bestätigt.
- Fehlenden Treiberstart in `--apply` ergänzt. 22 Simulationstests bestanden.
  Reale Wiederholung meldet alle vier bereit, ohne weitere Schreibbefehle
  oder Treiberstarts. Anleitung: [UR Bringup](../docs/ur_bringup.md).
