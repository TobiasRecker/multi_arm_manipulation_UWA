# Vierarm-Kollisionswächter und PTP auf Hardware

- Status: **in Arbeit**, 2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer beauftragt Übertragung des Simulationswächters und der PTP-Planer auf
  reale Hardware. Implementierung und Mock-Prüfung, keine reale Bewegung oder
  Power-/Brake-/Play-Aktion aus diesem Auftrag. Reale Stoppreserve nicht aus
  Simulationsdaten ableiten.
- Bereiche: `uwa_cell_motion`, gezielte Integration vorhandener Hardwareprofile,
  Anleitung/AGENTS/HANDOVER. Aktive Arbeit `work/ur-bringup.md` erhalten: keine
  Hardwaredienstneustarts und keine Geräteabfragen während dieser Vorbereitung.
- Bestehende Simulation64/uwa_cell_sim erhalten; Hardware66, Mock67 getrennt.
- Umgesetzt: Output-RTDE mit Gerätezeit-/Epochprüfung; konservative vollständige
  Öffnungshülle statt unbekannter Fingertelemetrie; sechs echte Positions-
  schnittstellen je Manager; Ressourcenhold/Actionabbruch/reaktivierte Fremd-
  controller, native STOP als Rückfall. Separater Supervisor/Watchdog, bewusster
  partieller Reset ohne Wiederaufnahme. Monitor bleibt ohne Stellaktionen.
- Gemeinsamer RRT-/Circular-Planungs- und Ausführungspfad, Modell-/Modusbindung,
  tatsächlicher Start und Fortschritt, keine automatische Startrepositionierung.
  Eigenes Hardware-RViz, getrennte echte24/virtuelle28JointState-Themen.
- Echte ros2_control-GenericSystem-Prüfung mit C++-Plugin bestanden:
  setup/logs/uwa-hardware-hold-plugin-check.json. Eigener privater Mockdienst
  uwa-hardware-motion-hold-mock danach beendet; reale Dienste unangetastet.
- Viermanager-Fakeintegration zuvor vollständig PASS, aktueller Wiederholungslauf
  nach letzter Änderung läuft. Build/Paketprüfung zunächst88/88PASS; Preview-
  Ergänzung wird noch nachgeprüft. Keine reale Stoppreserve gemessen.
- Anleitung docs/four_arm_hardware_motion.md, Abschlussnachweise/HANDOVER folgen
  nach aktuellem Testlauf. Kein weiterer Dienstneustart geplant.
