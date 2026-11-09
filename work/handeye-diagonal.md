# Diagonale parallele Kalibrierung

- Agent/Aufgabe: Codex, `handeye-diagonal`.
- Status: **aktiv**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Nutzerauftrag: links vorne + rechts hinten parallel, anschließend links hinten
  + rechts vorne; jeweils inaktive Arme zuvor zur Seite parken.
- Bereiche: Kalibrier-Planung, Ablauf/Mehrziel-Stopp, GUI/Status, Tests und
  zugehörige Dokumentation. Fremde OAK-Übersichtskamera-Änderungen erhalten.
- Planung: Parkwege seriell gegen die gesamte Zelle prüfen; aktive Diagonalpaare
  als gemeinsame zeitparametrierte Bewegung prüfen. Startzeitversatz und
  unabhängiges Abbremsen berücksichtigen; bei Stopp beide Controller stornieren.
- Gemeinsame Ressource: nur eigenen Kalibrierbackend neu laden, keine Zell-
  oder Scan-Neustarts. Autorisierte Simulationsfahrten zum Prüfen nötig.
- Implementiert: zwei kohortenweise parallele Messfahrten, serielle Park-/Anfahr-/
  Rückfahrfolge, gemeinsame Startzeit und Dauer, separate Hüllraumprüfung mit
  80 mm Puffer je Arm, Zwei-Controller-Stopp einschließlich später Bestätigungen.
- Nachweise: 79 aktuelle Offline-Tests bestanden. Echte simultane Gelenkbewegung
  im ersten Diagonalpaar, stationäre Wartearme sowie Pause/Fortsetzen und Stopp
  beider Controller nach 0,46 s live geprüft. Vollständiger 40×4-Lauf aktiv.
- Nächster Schritt: Volltest/Genauigkeit und Rückkehrstellungen abschließen,
  GUI-Verlust und Aufnahmestopp mit zwei Armen prüfen; endgültige GUI bereitstellen.
