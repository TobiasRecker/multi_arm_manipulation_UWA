# Diagonale parallele Kalibrierung

- Agent/Aufgabe: Codex, `handeye-diagonal`.
- Status: **abgeschlossen**.
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
- Nachweise: 79 aktuelle Offline-Tests bestanden; vollständiger 40×4-Lauf mit
  simultaner nativer Bewegung in beiden Paaren bestanden. Maximal 0,078 mm /
  0,030° Kamerafehler, 0,092 mm / 0,025° relativer Basisfehler. Alle vier Arme
  kehren regulär zur gemessenen Startstellung zurück (< 1,5e−11 rad Abweichung).
- Stoppnachweise: Pause/Fortsetzen und Fahrtstopp beider Controller 0,46 s,
  Aufnahmestopp 0,30 s, GUI-Lebenszeichenverlust 2,33 s einschließlich Timeout.
  Keine weitere Bewegung; alter Einzelarmmodus ebenfalls geprüft.
- Profil-/TF-/Rückfallprüfung und Zellverankerung bestanden. Bericht unter
  `docs/handeye_diagonal_validation_2026-11-09.json`; Logs `setup/logs/uwa-diagonal-*`.
- README, AGENTS, HANDOVER und Anleitung aktualisiert. OAK-Änderungen erhalten;
  Simulation/Scan/RViz nicht neu gestartet, nur eigener Kalibrierbackend.
- Abschluss: GUI mit standardmäßig aktiven Diagonalpaaren bereitgestellt und
  zehn Ergebniszeilen sowie vier Livebilder nach Profilneuladen geprüft;
  keine weiteren Armfahrten oder Dienstneustarts durch diese Aufgabe geplant.
