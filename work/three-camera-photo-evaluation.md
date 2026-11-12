# Vorhandene Dreierfotos auswerten

- Status: **abgeschlossen**, 2026-11-12, Hauptagent; nach PC-Absturz fortgesetzt.
- Auftrag: bereits vom Nutzer aufgenommene Fotos auf Eignung für die externe
  OAK-/Mehrkamerakalibrierung prüfen; soweit belastbar erste Offline-Schätzung.
- Nur lokale Dateien lesen; keine Kamera belegen, keine Dienste neu starten,
  keine Roboterfahrt. Parallele LinksFront-Kalibrierung erhalten.
- Bereiche: separates Offline-Auswertewerkzeug/Tests/Bericht und HANDOVER.
  Rohbilder und Ergebnisse unter setup/calibration/, Originalsets unverändert.
- Fokus-/Auflösungsprofile getrennt behandeln; unabhängige Prüfansichten und
  beobachtete Güte von vorläufigen Schätzungen trennen. Kein Profil aktivieren.
- Ergebnis:6Sets/18Originale intakt,5gemeinsamebrauchbareSets,3vollständig.
  DreiTrainings-/zwei vorherreserviertePrüfansichten; relativer OAK↔Frontfit
  diagnostisch gespeichert. Prüf-Konsistenz5,85/7,40mm,0,361/0,576Grad,
  keinevalidierteHardwaregenauigkeit. Rear-HD388Intrinsics weiterhinfehlend.
- Bericht docs/three_camera_photo_evaluation_2026-11-12.md, Ergebnisse unter
  setup/calibration/three_camera_evaluation_20261112/diagnostic_v1/.
  Burstbewegung/Abdeckung/Hashes geprüft,5synthetischeTestsPASS. HANDOVER
  aktualisiert; keineDienstneustarts/Armfahrten/Profilaktivierungen.
