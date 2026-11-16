# Erste gemeinsame OAK-RGB-D-Aufnahme

- Status: **abgeschlossen – Aufnahmemodus und erster Datensatz geprüft**,
  2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer beauftragt Beginn von Schritt1 und einfache Bedienerhinweise.
- Eigener RGB-D-Modus im bestehenden OAK-Fotopfad; gemeinsame Kamera-Lease,
  isolierter SDK-Worker, RGB entzerren/ImageAlign/Sync, keine Armaktionen.
- Bereiche: OAK-Tools/Tests/Anleitung/HANDOVER sowie kurze Zell-Übergabe.
  Fremde Diffs und aktive Hardware-Motion-Arbeit erhalten, keine UR-Abfragen.
- Bediener bereitet bekannten Karton, sichtbares festes Tischboard und
  ruhende Szene vor; eigene OAK-Vorschau pausieren. Bereitschaft abgefragt.
- Zunächst Software-/SDK-Prüfung ohne Gerät; Aufnahme erst bei vorbereitetem
  Aufbau und freier Kamera. Keine fremden Dienste stoppen, kein Firmwarewechsel.
- Nutzerkorrektur: studentischer Roboter steht statt Karton im Blickfeld.
  Für diesen Aufnahmetest geeignet; sein Mesh/Erkennung nicht vorausgesetzt.
-8Paare real PASS,1280×960/10fps, maxZeitabstand1,727ms. Vorschau: Roboter und
  Board sichtbar, Tiefe lückenhaft; noch keine vermessene Geometrieabnahme.
  Daten setup/oak4/rgbd/20261116-102913-rgbd-fa320e7a/, PNGs/Masken erneut
  dekodiert/geprüft, Kamera-Lease frei.31Tests/9Subtests bestanden.
- Dauerhafte Bedienung/Ergebnisse OAK4_RGBD.md und Übergaben ergänzt. Offen
  für nächsten Auftrag: K/Board/Tiefengeometrie, dann Mesh/Maske und GPU-Replay.
