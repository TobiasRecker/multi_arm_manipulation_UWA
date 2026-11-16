# Vier URs in eine kompakte Homepose
- Status: **abgeschlossen**, 2026-11-16 (Australia/Perth), Codex.
- Livezustände lesen und vier serielle Homewege anhand der bestehenden MoveIt-Zelle prüfen.
- Kein Treiber- oder Sicherheitsdienstneustart. Andere Hardware-Arbeiten und
  ihre Dienste erhalten. Keine Fahrt aus einem reinen Planungsschritt.
- Serienfolge LF, LR, RF, RR; aufrechte Pose, nominell 0,19–0,23 m
  horizontaler Gelenkkettenradius, höchster modellierter Punkt knapp 2 m.
- Vier MoveIt-Pfade aus gelesenen RTDE-Stellungen; aktuelle ROS-Stände und
  inaktive Bewegungscontroller im Check-only bestätigt. Keine Fahrt gesendet.
- Manifest SHA-256 d6f3bf87d6ffbf6ee91ac7f82b4cb627ab26f4e842625bf2989c6d714cbde562.
- Nutzer bestätigte die freien Fahrbereiche einschließlich oben und die
  Bereitschaft am Not-Halt. Vier serielle Fahrten erfolgreich, als geplant.
  Alle UC-Treiber und ROS-Programme unverändert. Eigene Bewegungscontroller
  wieder inaktiv. Abschließender RTDE-Ausgabekanal: maximale Zielabweichung
  0,0035°, maximale Gelenkgeschwindigkeit 0,000023 rad/s.
