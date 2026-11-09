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
- Nächster Schritt: Parkstellungen und Paarwege offline prüfen, dann Ablauf und
  gemeinsame Stoppüberwachung umstellen und live validieren.
