# RViz: Simulation und gemessene Hardware parallel

- Status: **aktiv**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzerziel: beide rechten echten URs zusätzlich zu simulierten Modellen in
  bestehender RViz-Zellansicht darstellen, klar unterscheidbar.
- Architektur: ausschließlich lesender JointState-Empfang auf Hardwaredomain66,
  eigene real_-Frames/Descriptions in Visualisierungsdomain64. Keine Befehls-
  Topics/Services/Actions überbrücken, keine Bewegungs-/Bremsenbefehle.
- Layout-Montagen zentral übernehmen und als vorläufig markieren; reale
  Gelenkstellungen nur bei tatsächlich empfangenen Daten, Ausfall sichtbar machen.
- Betroffen: neues Visualisierungspaket, RViz/Startintegration/Tests/Dokumentation.
  Bestehende Diffs und laufende Hardware-/Simulationsdienste erhalten.
