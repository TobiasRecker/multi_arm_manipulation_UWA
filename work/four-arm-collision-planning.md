# Vierarm-Kollisionswächter und PTP-Vergleich

- Status: **in Arbeit**, 2026-11-13, Hauptagent.
- Auftrag: unabhängiger 10-Hz-Kugelwächter, nur vier Nachbarpaare,
  verriegelter Paarstopp; RRTConnect und unabhängige zirkulare Felder offline
  planen und unter gleichen Bedingungen in Simulation vergleichen.
- Nutzerentscheidungen: Warten/zeitversetztes Fahren erlaubt, nur betroffenes
  Paar stoppen, zunächst PC-/ROS-Kommandos, Simulation zuerst, kein CDF in v1.
- Bereiche: neues Paket `uwa_cell_motion`, eigene Anleitung/Tests und
  AGENTS/HANDOVER. Lokale Scan-Diffs und reale Hardwarearbeit erhalten.
- Keine Hardwareaktionen. Gemeinsame Simulation vor Bewegungsprüfung auf
  Nutzung prüfen; eigene Testprozesse gezielt verwalten. Geplante Neustarts:
  zunächst keine vorhandenen Dienste; neuer Wächter erst nach Build/Test.
- Nachweise und Grenzen werden nach den tatsächlichen Prüfungen ergänzt.
