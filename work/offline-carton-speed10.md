# Zehnfache Geschwindigkeit der vier Eckanflüge

- Status: abgeschlossen – Offlinevergleich, 2026-11-17 (Australia/Perth), Hauptagent.
- Auftrag: vorhandene etwa220s-Eckanflüge auf10×Trajektoriengeschwindigkeit
  testen; reineOfflineplanung bleibt Kontext. Keine Hardware-/Kontaktfahrt.
- Quelle unverändert: offline-carton-paths-20261117/case03. Gemeinsame
  Zeitskalierung aller vier Arme, auch ihrer Halte-/Abschnittszeiten.
- Prüfen: Positionsgleichheit, Geschwindigkeits-/Beschleunigungs-/Ruckwerte,
  URDF-Geschwindigkeitslimits getrennt von bisherigen vorsichtigen Profilcaps;
  Geschwindigkeitsabhängigkeit der angenommenen Stopphüllen sichtbar halten.
- Bereiche: neue isolierte Auswertung/Tests/vergleichende HTML-Vorschau,
  eigener Forschungsordner und Dokumentation. Keine fremden Task-/Dienständerungen.
- Ergebnis:220,671→22,067s, exakt gleiche Stützstellen/Geometrie. Ableitungs-
  obergrenzen10×:0,454584rad/s,1,223044rad/s²,10,085925rad/s³. URDF-Speedcaps
  bestanden; ursprüngliches langsames Profil überschritten, keine Hardwareabnahme.
-2.208normierte Zeitpunkte: keineFCL-Kollision, minHüllabstand155,755mm inbeiden
  Fällen. Konservative Sollgeschwindigkeits-Reserve verletzt423→1.606Samples;
  reineDiagnose bei unveränderten Annahmen, keine realen Stoppmessungen.
- Build/16gezielteTests/ unabhängige dichte AbleitungsprüfungPASS.15Browserfälle,
 241identische GeometriepaarePASS;10×Trajektorie/1×Wiedergabe alsStandard.
- Daten offline-carton-speed10-20261117; docs/offline_carton_speed10.md.
  KeinePhysiksimulation/Hardware-/Kamera-/Dienstaktion.
