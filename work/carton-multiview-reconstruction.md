# Großen Karton aus dem Fünfkamera-Scan rekonstruieren

- Status: **in Arbeit**, 2026-11-13, Hauptagent Rekonstruktion.
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
