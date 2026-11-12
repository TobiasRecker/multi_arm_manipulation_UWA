# Front-HD übernehmen und HD an beiden hinteren URs testen

- Status: **in Arbeit**,2026-11-12,Hauptagent Front-HD.
- Expliziter Nutzerauftrag nach Erläuterung der nicht bestandenen Qualität:
  Front-HD-Daten übernehmen,HD-Bilder an right_rear(.170) und left_rear(.169)
  auf gleichem nativen Kamerapfad testen. Keine Armbewegung.
- Übernahme mit sichtbarer Bedienerentscheidung und unverändertem quality=false,
  versioniertem Profil; ursprüngliche Ergebnisse und Qualitätsgrenzen erhalten.
- Parallel arbeitet global-calibration-oak-boards an hardware_20261112_v1.
  Diese Änderungen erhalten; Front-HD wird darauf als eigenes Nachfolgeprofil
  aufgebaut. Standardlayout vor Aktivierung erneut lesen; keine fremden Builds/
  Dienste stoppen. Keine Hardware-/Gazebo-Neustarts für diesen Auftrag.
- Bereiche: calibration_profileLoader/gezielteTests,neuesProfil,HD-Diensttestdaten,
  HANDOVER/Bedien-/Kalibrierbericht. SSH ausschließlich Kamerapfad; keine Passwörter
  in Dateien. Zugriff/Versionen zuerst lesen,Restore nach jedem Kameratest prüfen.
