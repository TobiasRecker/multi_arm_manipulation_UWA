# Großen Karton aus dem Fünfkamera-Scan rekonstruieren

- Status: **abgeschlossen – erster CAD-Entwurf, Genauigkeit offen**, 2026-11-13,
  Hauptagent Rekonstruktion.
- Nutzer beauftragt die 3D-Rekonstruktion aus den vorhandenen 25 Fotos.
  Offline, ausschließlich Bilder; keine neuen Fotos, Tiefendaten oder Armfahrt.
- Datensatz: setup/digitization/four_arm_scan_20261113/scan_dataset.json.
- Bereiche: datasetgebundene native Intrinsics/Board-Posen, Mehransichtsfit,
  sichtbare Wandkonturen, Mesh-/CAD-Export, Overlays/Validierung und Dokumentation.
- Globale Kalibrierprofile bleiben unverändert. Bestehende HD-Kalibrierungen
  nur passend zu physischer Kamera/Fokus/Auflösung mit Quellenhash verwenden.
- Maßstab aus Boards; unbekannte Stärke/verdeckte Geometrie als Annahmen kennzeichnen.
  Getrennte Fit- und Prüfansichten; keine behauptete absolute Genauigkeit ohne Gegenmaß.
- Eigene Daten unter setup/digitization/carton_multiview_20261113/; Quellbilder erhalten.
- Ergebnis404×342×163mm, offene Schachtel mit sichtbaren Oberkanten-/Griffkonturen,
  STEP/STL/GLB/SCAD und visuell geprüfter Textur-/CAD-Vorschau. Stärke2,5mm
  angenommen; keine mm-genaue Vermessung behauptet.
- Alle25Fotos geprüft,20metrisch genutzt; LF-Auswertung widersprüchlich, seine
  fünfFotos nur Diagnose. Passende native K/D separat eingefroren, Flags erhalten.
- Direktes rechtesBoard in jederKamera statt nicht vorhandener OAK-Brücke zum
  verdeckten linkenBoard. Relation beiderBoards aus Trainings-Wristbildern,
  Kameraposen und Karton gemeinsam robust bei festen Intrinsics angepasst.
- ZehnTrainings-/zehnPrüfbilder; MedianRMS14,05/13,68px bei1600px Breite.
  VierOAK-Prüfbilder wiederholen festenStandpunkt. Fehlerursachen/Kontrollmaß offen.
- Nachweise: STEP-/GLB-Rückimport, STL292Dreiecke geschlossen/einKörper,
  Transformationsrichtung, Kontur-Rückprojektion und explizite Prüfdatentrennung
  bestanden; Rohdaten/verification.json erhalten. Keine Dienstneustarts/Hardware.
- Dauerhafte Details docs/carton_multiview_2026-11-13.md; README/HANDOVER gepflegt.
