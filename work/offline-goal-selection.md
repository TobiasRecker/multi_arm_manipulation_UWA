# Gemeinsame Zielauswahl – Schritt 2

- Status: abgeschlossen, 2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Auftrag: nach anschaulicher Kandidatenvorschau mit Schritt 2 fortfahren.
- Umsetzung: gespeicherte Kandidaten modellgebunden prüfen, gemeinsame Ziele
  nach Gelenkweg, sechs Paarabständen und Gelenkgrenzenreserve bewerten;
  nachvollziehbare Pareto-Auswahl mit Alternativen für spätere Einzelwege.
- Bereiche: neues selection-Modul/CLI und Tests im uwa_cell_motion-Paket,
  tools/preview_goal_candidates*, eigene Beispieldaten, Dokumentation.
- Keine Hardware-, Kamera-, ROS-Knoten- oder Dienstaktionen. Andere Karton-/
  Live-Stopp-Aufträge und deren Dateien/Diffs erhalten. Offline-Modelle fest;
  bewegte Basen und verbindende Bahnen folgen in späteren Schritten.
- Umsetzung/installierteCLI abgeschlossen. Modell-/Provenienzbindung, sechs
  gecachte Paarprüfungen, volle Szenenprüfung, dreikriterielle Paretoauswahl.
- Neues synthetisches99,1cm-Beispiel:4.096Kombinationen,2.192gültig,28Pareto,
 3Vorauswahlziele. AlleEntscheidungen/Metriken unabhängig ohneCachePASS.
  Historisches90cm-Beispiel ebenfalls vollständig ausgewertet, nicht verändert.
- BuildPASS;81gezieltePythonfälle und nativerVorfilterPASS.18Auswahltests neu.
  Kein Vollpaketlauf: vorhandener alter Socketfehler imgesamtenTestarchiv.
- Viewer visuellgeprüft,38neue/48alteUI-AuswahlfällePASS. Daten/Logs und dauerhafte
  Ergebnisse inHANDOVER dokumentiert; Anleitung docs/offline_goal_selection.md.
- Nächster fachlicher Schritt: primitive Einzelwege und Alternativen, dann
  Zeitkoordination. Keine Roboter-/Dienst-/Kameraaktion durchgeführt.
