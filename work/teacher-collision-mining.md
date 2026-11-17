# Kollidierende Referenzbahnen gezielt suchen

- Status: abgeschlossen (Screening und Diagnose), 2026-11-17, Hauptagent dieses Chats.
- Nutzerkritik: bisher zu langsame Datenerzeugung und zu viele bereits freie
  Referenzen. Primär Aufgaben suchen, bei denen ohne Planung Kollisionen auftreten.
- Umsetzung: Laufzeiten/Anteil tatsächlich kollidierender Referenzen auswerten;
  direkte SE(3)-Verbindungen zwischen gültigen Starts und Zielen vorprüfen,
  Kollisionszeugen speichern und erst Kandidaten an den Lehrer übergeben.
- Neue separate CLI/Tests/Dokumentation; bisherige gebundene Quellen erhalten.
  Vorhandenen eingefrorenen Zweiarm-Modellstand verwenden, keine Hardware,
  Kamera, ROS-Nodes oder Dienste. Maximal zwei CPU-Worker/BLAS1/niceness10.
- Geometrisch gültige Endpunkte/fortgesetzter IK-Zweig erforderlich. Scheitern
  nicht als Unlösbarkeitsbeweis; FCL-/Hüllen-/Abstandsfälle sauber trennen.

## Nachweise

- CLI mine_teacher_collisions.py, vier gezielte Tests und Build PASS.
- 184 direkte Bankverbindungen/29,61s ohne FCL-Fall bei gültigen Enden.
  Erweiterter Lauf920Kandidaten/80,74s: ein Arm/Tisch-FCL-Fall,107ohneTreffer,
 723IK-Fehler,89ungültigeEnden. Der184erSatz ist enthalten, nicht addieren.
- Gefundener echter Kontakt north-ik3-random-011 bleibt ungelöst:
  Lehrer hat keine eigene Arm/Umwelt-Optimierungsbedingung. Recheck mit
 2.108Zeitpunkten/266FCL-Fehlern, keinpositiverBC-Export.
- Minimaler Fortschrittsrundungsfehler im Mining-Adapter korrigiert und
  gegen echte Bereichsfehler getestet. Alte Quellen/Fehlberichte erhalten.
- Vier lokale Referenzproben: Hüllenüberlappung bis−16,7mm, kein FCL-Kontakt.
  Neue separate Kategorie ARM_HULL_OVERLAP, keine falsche Kontaktbehauptung.
- NegativeReferenzgalerie recheck01/viewer.html, acht Browserchecks PASS,
  Screenshot visuell geprüft. Auswertung/Bedienung in docs/teacher_collision_mining.md.
- Offene fachliche Arbeit ausdrücklich dokumentiert: Lehrer vervollständigen,
  gezielte Kontaktgrenzen-Suche, akzeptierte Demonstrationen pro Rechenzeit
  messen; noch keine große Trainingsproduktion oder neue positive Beispiele.
