# Reale erste Aufnahmepose und Hand-Auge-Messreihe

- Status: **aktiv**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzer möchte nach erfolgreichem Front-Parken right_rear in erste Bildpose
  bewegen und anschließend die entwickelte Hand-Auge-Routine real erproben.
- Zunächst echte Zustände/Bild und vorhandene Intrinsics/Frische des HTTP-
  Bildpfads prüfen. Rechte Front-Parkpose erhalten, linke Arme laut Nutzer
  nominell Home, kein anderer Arm wird bewegt.
- Bereiche: getrennte Hardware-Aufnahme/Planung in uwa_cell_control mit
  Wiederverwendung von MoveIt-Modell, MATCH-Ausführung und bildbasiertem Solver.
  Bestehenden Simulationsbackend nicht auf Domain66 umbiegen. Neue Profile/
  echte Messdaten nicht als Simulationsergebnisse aktivieren.
- Vorläufige optische Montagen nur für Design/Planung verwenden. Keine
  nominellen Simulations-Intrinsics als reale Kalibrierung behandeln.
- Dienste: zunächst keine Neustarts, kein Power/Brake/Play. Konkrete Pose/Weg
  vorbereiten und prüfen; vorhandene Hardwaretreiber/GUIs erhalten.
