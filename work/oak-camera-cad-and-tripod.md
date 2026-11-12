# OAK-CAD und Stativ in Gazebo/RViz

- Status: **in Arbeit**,2026-11-12,Hauptagent Modellintegration.
- Nutzerauftrag: OAK-Kameramodell aus Downloads in Simulation und ROS-
  Visualisierung einbetten; zusätzlich ein geeignetes Stativmodell finden/erstellen.
- Quelle: Downloads/oak4-pro-3d-model.zip mit großem STEP-Modell. Modell in
  ROS/Gazebo-taugliches, reduziertes Visual-Mesh umwandeln; Einheiten/Orientierung
  prüfen. Eigene approximierte Stativgeometrie für die Anzeige, kein vermessenesCAD.
- Parallelaufgabe oak-preliminary-profile-adoption ändert overview.py/node,
  Standardprofil und Tests. Deren neue OAK-Optikpose/K-D vollständig erhalten;
  keine Kalibrier-/Roboter-/Tischparameter für die Visualisierung ändern.
- Bereiche: neueMesh-/Darstellungshelfer, gezielte overview-Visual/Marker-Anbindung,
  Tests,Doku. Kein OAK-Hardwarezugriff, keine Armfahrt/Hardwaretreiberneustarts.
  Bei Live-Prüfung ausschließlich eigene Übersichtskamera neu laden, Zellzustand
  und fremde Kalibrier-/Vorschauprozesse erhalten.
