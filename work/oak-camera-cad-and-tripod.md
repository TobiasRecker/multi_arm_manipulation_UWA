# OAK-CAD und Stativ in Gazebo/RViz

- Status: **abgeschlossen – Modell und Stativ in Gazebo/RViz geladen**,2026-11-12,Hauptagent Modellintegration.
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

- Ergebnis: nativeCAD-Gehäuse+separatesFrontglas,52169Dreiecke/2,61MB,
  Meter/Koordinaten/Hashes dokumentiert. EigeneTeleskop-Stativgeometrie,
  gemeinsamerSDF-/Markerpfad, optischePose/K-D/aktivesProfilv3 erhalten.
- 21TestsPASS,2Paketegebaut. LiveGazeboScene enthält2Mesh-/27Stativvisuals,
  32Marker/RViz-Abonnent,4000×3000Bild/TF/K-D/9Controller geprüft; maxSim-
  Gelenkänderung0,00001064rad. NurOverviewdienstneu gestartet.
- StandaloneVorschau geprüft, nativeGUI-Screenshotswarz/nichtalsBeleggewertet.
  KeineHardwarekamera/Armaktionen. EigenesStativundCAD-Optik-Ankerbleiben
  Näherungen; keine neueMoveIt-Kollisionsgeometrie behaupten.
- Dokumente: README/HANDOVER/AGENTS/THIRD_PARTY/docs/oak_camera_cad.md,
  docs/oak_overview.md. Quelldaten lokal, runtimeMeshes/Provenienz imRepo.
