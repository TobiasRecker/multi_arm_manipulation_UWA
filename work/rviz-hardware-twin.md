# RViz: Simulation und gemessene Hardware parallel

- Status: **abgeschlossen**.
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
- Implementiert: uwa_cell_visualization, Gold/Cyan-Modelle mit real_-Präfix,
  Domain66->64 nur JointState, Sim-Uhrretiming, Zustandsmarker/STALE-Ausblendung,
  keine künstlichen Nullposen, zentrale vorläufige Montage, separate Modellfarben.
- RViz-/Desktop-/Launch-Integration mit eigener idempotenter Overlay-Userunit;
  optionale visuelle Offsets, keine Hardwaretreiber durch Viewer gestartet.
- Beide echten Arme LIVE, je6 finite Winkel und Welt-TFs; parallel48 Simulations-
  Gelenke/Tools. Nur vorne rechts fehlenden Joint-State-Broadcaster geladen/
  aktiviert; keine Bewegungscontroller, Power/Brake/Play oder Ziele gesendet.
- Offline- und getrennte Cross-Domain-Prüfung inkl. pausierter Uhr, TF-Änderungen,
  Timeout/Recovery und fehlender Kommandopublisher bestanden. Native RViz-Ansicht
  über Compositor-Screenshot geprüft (normaler Qt-Screenshot war schwarz).
  Prüfdateien setup/logs/uwa-twin-*, Benutzeranleitung docs/rviz_digital_twin.md.
- Gemeinsame Visualisierungs-/Gazebo-Regressionssuite:61 Tests bestanden.
- Gazebo/RViz/Scan/Overlay zur Ansicht geöffnet; vorhandene Hardwareprozesse
  erhalten. AGENTS/HANDOVER/README parallel gepflegt. Basen bleiben unkalibriert.
