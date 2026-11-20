# Antigravity für die Kartonlokalisierung prüfen

- Status abgeschlossen, 20.11.2026, Australia/Perth. Nutzer beauftragt den
  kurzen Modellvergleich mit kleinem Prompt, schnellstem verfügbaren Modell
  und anfangs niedrigster Reasoning-Stufe.
- Ein Archivvergleich über isolierten Antigravity-Bildinput. Der Prompt
  beschreibt Kartonmerkmale und JSON-Koordinaten im Bild. Separat werden
  Antwortqualität, Latenz und der geometrische Posefit auf ROSmini geprüft.
- Ergebnisse unter `setup/tasks/carton_antigravity_20261120/`. Betrieb und
  Schutzdienste der realen Zelle sind ausserhalb des Versuchs. Kein Neustart.
- Flash Low war am schnellsten (4,43 s Median bis Bildantwort, zwei von drei
  Kartonposen). Hydrogen Low war mit 5,89 s die beste untersuchte Kombination
  aus Zeit und geometrischem Ergebnis (drei von drei). Dasselbe kritische
  Bild bestand auch die beiden Wiederholungen. Flash Medium hatte zwei
  Zeitüberschreitungen. Einzelwerte im [Zell-Handover](../HANDOVER.md).
