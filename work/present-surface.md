# Offline-Baustein zum Präsentieren von Boxflächen

- Status: abgeschlossen, 2026-11-18 (Australia/Perth), Codex dieses Chats.
- Nutzerauftrag: aus der Gegenwand-Auswertung den wiederverwendbaren
  `present_surface`-Baustein umsetzen und im Boxzeichnungs-Piloten prüfen.
- Bereiche: Boxzeichnungsmodell, Offline-CLI, Audit, Bedienung und Übergabe.
- Der Pilottest verwendet gespeicherte Modelldaten und das 0,1-rad/s-Profil.
  Keine Dienste oder Neustarts vorgesehen.
- Ergebnis: Flächen, Radius und Suchgrenzen über die vorhandene CLI,
  lesbares Python-Programm und frühe HTML-Transfersichtung. Diagnosen
  bleiben bei Ablehnung erhalten und geprüfte Wege stehen im Ergebnis.
- Abnahme: Drei-Flächen-Referenz und veränderte Reihenfolge mit 20 mm,
  Einzelfläche ohne Transfer, Overlap-Regression und erzwungener Abbruch.
  Separate FK-/Zeitaudits, 23 Softwaretests und 18 Browserchecks bestanden.
  Übersicht `setup/tasks/present_surface_20261118/verification.json`.
