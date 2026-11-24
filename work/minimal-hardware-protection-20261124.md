# Neuer minimaler Hardware-Schutz, 24.11.2026

- Status: Umsetzung als inaktiver Kandidat, Hauptagent dieses Chats.
- Auftrag: beschlossenen C++-Kollisionskern und gemeinsame Arm-Pause mit
  ausdrücklicher Fortsetzung implementieren; Robot Power und Motion Review erhalten.
- Automatische Pause ausschließlich bei Geometriekonflikt. Fehlende Kollisionsdaten
  warnen nur. Greifer ausschließlich als Geometrie, keine Greifer-Schutzprüfungen.
- Bestehende 40-mm-Nachbararmmarge und sonstige FCL-Kontaktgrenzen erhalten.
  Keine zusätzliche Tischmarge und keine neue Geschwindigkeitsfreigabe.
- Bereiche: neues Paket uwa_cell_protection, Controller-Plugin, Ausführungsadapter,
  GUI/Bridge, getrennte Kandidatenwerkzeuge und Dokumentation. Vorhandene gestagte
  Motion-/Marker-/Dokumentationsänderungen bleiben erhalten.
- Keine echten Ziele, Power-/Brake-/Play-Aktionen oder Hardwaredienstneustarts.
  Keine Sicherheits-/Fehlertests in Gazebo. Softwareprüfung isoliert in Domain67.
- Nächste Schritte: Komponenten bauen, Verbraucher umstellen, Mock-/Dateiprüfung,
  verbleibende Grenzen und Kandidatenstart dokumentieren.
