# Vier Wrist-Kameras plus OAK für Objektrekonstruktion

- Status: **Recherche und Scan-Konzept abgeschlossen**, 2026-11-12.
- Nutzerziel: gemeinsamer Objektbereich, fünf Fotos und kleine Zusatzbewegungen;
  Literaturverfahren mit bestehendem parametrischem CAD-Fit verbinden.
- Ergebnis: docs/five_camera_reconstruction.md und nicht ausführbares Designprofil
  config/digitization/five_camera_scan_design.yaml. Fünf Grundansichten, danach
  13–21 verschiedene Perspektiven. YAML und Ansichtszähler geprüft.
- Primärquellen: COLMAP, OpenMVS, DUSt3R/MASt3R, VGGT, Nerfstudio.
  Empfehlung: Aufnahme unabhängig vom Backend; Geometrie/Lernverfahren, Mesh,
  CAD-Fit. Je Kamera passende Intrinsics, je Aufnahme aktualisierte Pose.
- Gemeinsame Sicht, IK und vollständige Wege sind noch zu prüfen. Wenige Zentimeter
  TCP-Bewegung beweisen keine Kollisionsfreiheit. Noch kein Fünfkamera-Capture.
- Keine Kameraaufnahme, Armfahrt oder Modellinstallation; laufende RR-/LF-Reihen
  unberührt. Intel-Grafik erkannt, kein CUDA-Gerät. Lernverfahren ungetestet.
- README, AGENTS und HANDOVER aktualisiert. Keine fremden Änderungen übernommen.
