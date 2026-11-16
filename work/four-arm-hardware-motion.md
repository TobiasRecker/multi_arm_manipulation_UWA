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
- Zu klären im Code: unabhängige Gerätefrische gegen gecachte ROS-Joints,
  tatsächlicher Stop-/Verriegelungspfad je Manager, fehlende Greifertelemetrie,
  gemeinsame Hardware-PTP-Ausführung mit vollständiger Kollisionsprüfung.
