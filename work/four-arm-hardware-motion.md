# Vierarm-Kollisionswächter und PTP auf Hardware

- Status: **Implementierung und Mock-Abnahme abgeschlossen; physische Stoppabnahme offen**,
  2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer beauftragt Übertragung des Simulationswächters und der PTP-Planer auf
  reale Hardware. Implementierung und Mock-Prüfung, keine reale Bewegung oder
  Power-/Brake-/Play-Aktion aus diesem Auftrag. Reale Stoppreserve nicht aus
  Simulationsdaten ableiten.
- Bereiche: `uwa_cell_motion`, gezielte Integration vorhandener Hardwareprofile,
  Anleitung/AGENTS/HANDOVER. Parallele Arbeit `work/ur-bringup.md` erhalten: keine
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
- Aktueller Viermanager-Fake-Lauf vollständig PASS:
  setup/logs/uwa-hardware-mock-integration-current.json. Beide Planer erfolgreich
  ausgeführt; Paarstopp lässt unabhängigen Arm weiterfahren; Freeze, mehrere
  Paare, Fremdcontroller, falsches Plugin/Parameter und Prozessausfälle geprüft.
  Historische ACK-Testannahme und verfrühte Resetbeobachtung in Fehlversuchen
  erhalten; vor bewusstem Testreset stabiles Fenster statt Frischelockerung.
- Lyrical-Build PASS;89Paketprüfungen PASS(84pytest+5CTest), einschließlich
  vorhandener Simulation. Installierter Viernode-Monitorlaunch in Mock67 mit
  drei getrennten Guard-/Adapter-/Watchdogprozessen PASS; fehlende Messungen
  bleiben STALE, kein erfundener Gelenkzustand. Ergebnis
  setup/logs/uwa-hardware-monitor-launch-check.json; eigene Prozesse beendet.
- Anleitung docs/four_arm_hardware_motion.md und AGENTS/HANDOVER/README gepflegt.
  Keine reale Stoppreserve gemessen; nächste Arbeit physische Latenz-/Brems-
  und Fehlertests mit vorbereiteter Zelle. Kein eigener Hardwaredienst aktiv.
