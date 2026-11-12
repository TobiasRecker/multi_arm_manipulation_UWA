# Karton aus drei Farbbildern als CAD rekonstruieren

- Status: **abgeschlossen – erste assistierte Pipeline und Karton-CAD erstellt**,2026-11-12,Hauptagent Rekonstruktion.
- Nutzerauftrag: wiederverwendbare Digitalisierung einfacher Objekte erproben;
  Karton auf Tisch ausschließlich aus drei Kamerabildern rekonstruieren.
- Gemeint aus vorhandenem Aufbau: OAK4 plus beide rechten Wristkameras.
  Vorhandene Kalibrierungen und sichtbare metrische Boardreferenzen verwenden,
  keine OAK-Tiefenaufnahme. Keine Roboterfahrt/Power/Brake/Play.
- Aktive Fremdaufgabe right-rear-hd-intrinsics beachten; keine laufende Reihe
  oder Kameratransaktion unterbrechen. Aufnahme nur ohne konkurrierende Nutzung.
- Ziel: erste parametrisierte Box-/Karton-Näherung, STEP/STL und Bildprojektionen
  mit nachvollziehbaren Mess-/Annahmewerten. Verdeckte Geometrie nicht als gemessen
  ausgeben, vorläufige Kalibrierung/Skalen- und Maßunsicherheit nennen.
- Bereiche: neues Rekonstruktionsmodul/-CLI, Tests und eigene Daten unter
  setup/digitization/, Doku/README/HANDOVER. Keine aktive Kalibrierung ändern.

- NativeDreierfotos aufgenommen/all_captured:true. Szene: offeneSchachtel mit
 3Fächern. Maßstab durchrechtes40mmTischboard, jeBildPnP; OAK+Frontmetrisch,
  Rear-HD388nurvisuellohneMatchingK/D. KeineFK-/Welt-/Hand-AugewertefürGeometrie.
- Ergebnisca524×102×100mm,2Trennwände172/347mm,Wand2,5mmangenommen. Private
  Rohbilder/Modelle/Overlays/Sensitivität/CAD untersetup/digitization/carton_20261112/.
- WiederverwendbareCLI digitize_box +Export-/Vorschautools, expliziteLandmarkdatei.
  STEPmm/STLm/SCADeditierbar;Solid/Rückimport/geschlossenesMesh geprüft.
  RechtshändigerObjektframe+Zoben. KeineautomatischeObjektsegmentierungbehaupten.
- 6TestsPASS,Control-Paketgebaut/CLIgeprüft,Vorschauvisuellgeprüft. README,
  AGENTS,HANDOVER,docs/object_digitization.md gepflegt. KeineRobot-/Tiefen- oder
  aktiveProfil-/Simulationsänderung. AbsoluteGenauigkeitnochungeprüft.
