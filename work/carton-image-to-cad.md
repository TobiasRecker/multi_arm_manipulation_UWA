# Karton aus drei Farbbildern als CAD rekonstruieren

- Status: **in Arbeit**,2026-11-12,Hauptagent Rekonstruktion.
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
