# Lokale UWA-Programmbibliothek, 19.11.2026

- Status: abgeschlossen, 19.11.2026 (Australia/Perth). Nutzer wünscht eine mit UWA Robot Power
  gestartete Programmbibliothek auf ROSmini mit Übersicht, Details und Start.
  Kartonprogramm soll OAK-Poseschätzung und Wrist-Prüfung selbst aufrufen.
- Bereiche: lokaler Server und Weboberfläche, Startanbindung im Power-Fenster,
  dateibasierter Kartonversuch und dokumentierter N100-Aufrufpfad.
- Die Entwicklung lief separat vom realen Motion-review-Piloten mit
  gespeicherten OAK- und Wrist-Aufnahmen.
- Qt-Mock startete den lokalen Server. Start, Status, Pose/Plan/Wrist-Diagnose
  und alle drei Preview-Endpunkte über HTTP geprüft. Der Archivlauf dauerte
  38,4 s und erstellte eine 44-s-Parallelplanung. 53 gezielte Tests bestanden.
- Vorderer Prüfpunkt im alten Wrist-Vorgriffbild außerhalb des Sichtfelds.
  Hinten war die gelbe Randlinie messbar. Modellprojektion der gemessenen
  offenen Einfahrt weist außerhalb beider Wrist-Sichtfelder. Kontakt bleibt
  Gegenstand der bestehenden Bedienprüfung mit aktuellem OAK-Einfahrbild.
- Nachweise `setup/tasks/uwa_program_library_check_20261119/`. Der Live-Pfad
  wurde simuliert und ist zur lokalen Konfiguration und N100-Übernahme
  dokumentiert. Kein N100-Update, keine reale Fahrt. Der Browserzugriff für
  die visuelle Kontrolle war nicht verfügbar. Testserver beendet.
