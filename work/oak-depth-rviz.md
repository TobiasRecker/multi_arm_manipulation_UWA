# HQ-Tiefendaten in RViz anzeigen

- Status: **abgeschlossen**,2026-11-12, Hauptagent OAK-RViz.
- Auftrag: vorhandene HQ-Tiefendaten sichtbar in RViz einblenden.
- Befund: nur vorhandene statische Design-Vorschau auf Domain70 läuft;
  keine Zell-RViz-/Gazebo-Dienste. Fremde Vorschau erhalten.
- Umsetzung: eigene RViz-Snapshotansicht auf Domain65, HQ/Standard als
  PointCloud2 und sichtbarem Aufnahmezeitpunkt, keine behauptete Weltregistrierung.
  Tatsächliche rektifizierte Projektionsmatrix direkt aus DepthAI-Frame sichern,
  keine unrektifizierte Factory-K ungeprüft als Ausgabe-K benutzen.
- Bereiche: OAK tools/oak4_depth_{capture,geometry,rviz}.py, eigener temporärer
  RViz-Benutzerdienst/Config/Prüfartefakte, Anleitungen/Agentenübergaben.
- Kamera nur einmal per vorhandenem HQ-Dienst öffnen, danach Datei-Publisher.
  Kein Kamera-Dauerstream, keine Roboter-/Simulations-/fremden RViz-Neustarts.
- Tests: bekannte synthetische Pixelprojektion, native Nachricht/Finitheit/Counts,
  abonnierte PointCloud2/TF und echte gerenderte RViz-Ansicht prüfen.

- Ergebnis: eigene RViz-Ansicht geöffnet,273323HQ-/429717Standardpunkte.
  TatsächlicheAusgabe-K gespeichert.17TestsPASS; PointCloud2/TF/RViz-Abonnent und
  GUI GlobalStatusOk geprüft. NativeScreenshot-Grabs aufWayland schwarz, keine
  visuelleScreenshotprüfung behaupten. VorhandeneZellvorschau unverändert.
