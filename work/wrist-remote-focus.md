# Fernbedienbarer Wrist-Camera-Fokus

- Agent/Aufgabe: Codex, `wrist-remote-focus`.
- Status: **abgeschlossen**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzerziel: Fokus möglichst vom PC per Skript/Schieberegler einstellen;
  Zusammenhang zwischen Fokus und Abstand klären.
- Umfang: öffentliche Primärquellen und vorhandene Skripte prüfen, dokumentierte
  Schnittstelle von experimentellem USB-/URCap-Zugriff unterscheiden. Keine
  Controllerprogramme, Kameraeinstellungen oder Roboterzustände verändern.
- Bereiche: Hardware-Kamera-Anleitung, HANDOVER/AGENTS; fremde aktive
  `rviz-hardware-twin`-Arbeit erhalten. Keine Dienstneustarts.
- Ergebnis: primärer OpenCV-/USB-Fokusbericht und V4L2-Einheit geprüft;
  öffentliches BeispielHTTP404. Keine lokale Kameraprogrammdatei gefunden,
  kein dokumentierter Controller-Netzwerksetter. Distanz/Stellwert/Kennlinie
  erläutert; frühere pauschale USB-Fokus-Aussage korrigiert. Anleitung,
  AGENTS/HANDOVER aktualisiert. Keine Setter oder Hardwareänderungen ausgeführt.
